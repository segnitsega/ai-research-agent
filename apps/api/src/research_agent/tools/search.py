import re
from html import unescape
from typing import Protocol
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from research_agent.schemas.agents import SearchHit

_RESULT_RE = re.compile(
    r'<a\b(?=[^>]*\bclass="[^"]*\bresult__a\b[^"]*")(?=[^>]*\bhref="(?P<href>[^"]+)")[^>]*>(?P<title>.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
_SNIPPET_RE = re.compile(
    r'class="[^"]*\bresult__snippet\b[^"]*"[^>]*>(?P<body>.*?)</(?:a|td|div)>',
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")
_BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_WIKI_UA = "ResearchAgent/0.1 (local-dev; +https://example.com/bot)"


class SearchProvider(Protocol):
    name: str

    async def search(self, query: str, *, limit: int = 5) -> list[SearchHit]: ...


class FakeSearchProvider:
    name = "fake"

    def __init__(self, hits: list[SearchHit] | None = None) -> None:
        self.hits = hits or []

    async def search(self, query: str, *, limit: int = 5) -> list[SearchHit]:
        return self.hits[:limit]


class DuckDuckGoProvider:
    """Live web search via DuckDuckGo HTML results. No API key required."""

    name = "duckduckgo"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def search(self, query: str, *, limit: int = 5) -> list[SearchHit]:
        owns = self._client is None
        client = self._client or httpx.AsyncClient(timeout=20, follow_redirects=True)
        try:
            hits = await self._html_search(client, query, limit)
            if hits:
                return hits
            return await self._wikipedia_fallback(client, query, limit)
        finally:
            if owns:
                await client.aclose()

    async def _html_search(self, client: httpx.AsyncClient, query: str, limit: int) -> list[SearchHit]:
        response = await client.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers={
                "User-Agent": _BROWSER_UA,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        response.raise_for_status()
        return _parse_ddg_html(response.text, limit)

    async def _wikipedia_fallback(self, client: httpx.AsyncClient, query: str, limit: int) -> list[SearchHit]:
        response = await client.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "opensearch",
                "search": query,
                "limit": limit,
                "namespace": 0,
                "format": "json",
            },
            headers={"User-Agent": _WIKI_UA},
        )
        response.raise_for_status()
        payload = response.json()
        titles = payload[1] if len(payload) > 1 else []
        snippets = payload[2] if len(payload) > 2 else []
        urls = payload[3] if len(payload) > 3 else []
        hits: list[SearchHit] = []
        for index, url in enumerate(urls):
            hits.append(
                SearchHit(
                    url=url,
                    title=titles[index] if index < len(titles) else url,
                    snippet=snippets[index] if index < len(snippets) else "",
                    provider=self.name,
                )
            )
        return hits[:limit]


class TavilyProvider:
    name = "tavily"

    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None) -> None:
        self.api_key = api_key
        self._client = client

    async def search(self, query: str, *, limit: int = 5) -> list[SearchHit]:
        owns = self._client is None
        client = self._client or httpx.AsyncClient(timeout=20)
        try:
            response = await client.post(
                "https://api.tavily.com/search",
                json={"api_key": self.api_key, "query": query, "max_results": limit},
            )
            response.raise_for_status()
            payload = response.json()
            hits: list[SearchHit] = []
            for item in payload.get("results", []):
                hits.append(
                    SearchHit(
                        url=item["url"],
                        title=item.get("title") or item["url"],
                        snippet=item.get("content") or "",
                        provider=self.name,
                    )
                )
            return hits
        finally:
            if owns:
                await client.aclose()


class ArxivProvider:
    name = "arxiv"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def search(self, query: str, *, limit: int = 5) -> list[SearchHit]:
        owns = self._client is None
        client = self._client or httpx.AsyncClient(timeout=20)
        try:
            response = await client.get(
                "https://export.arxiv.org/api/query",
                params={"search_query": f"all:{query}", "max_results": limit},
            )
            response.raise_for_status()
            return []
        finally:
            if owns:
                await client.aclose()


def _parse_ddg_html(html: str, limit: int) -> list[SearchHit]:
    hits: list[SearchHit] = []
    snippets = [_clean_html(match.group("body")) for match in _SNIPPET_RE.finditer(html)]
    for index, match in enumerate(_RESULT_RE.finditer(html)):
        url = _unwrap_ddg_url(unescape(match.group("href")))
        if not url or not url.startswith("http"):
            continue
        hits.append(
            SearchHit(
                url=url,
                title=_clean_html(match.group("title")) or url,
                snippet=snippets[index] if index < len(snippets) else "",
                provider="duckduckgo",
            )
        )
        if len(hits) >= limit:
            break
    return hits


def _clean_html(value: str) -> str:
    return " ".join(_TAG_RE.sub(" ", unescape(value)).split())


def _unwrap_ddg_url(url: str) -> str:
    parsed = urlparse(url)
    if "duckduckgo.com" in (parsed.netloc or "") and parsed.path.startswith("/l/"):
        uddg = parse_qs(parsed.query).get("uddg", [])
        if uddg:
            return unquote(uddg[0])
    return url
