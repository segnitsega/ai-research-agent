from typing import Protocol

import httpx

from research_agent.schemas.agents import SearchHit


class SearchProvider(Protocol):
    name: str

    async def search(self, query: str, *, limit: int = 5) -> list[SearchHit]: ...


class FakeSearchProvider:
    name = "fake"

    def __init__(self, hits: list[SearchHit] | None = None) -> None:
        self.hits = hits or []

    async def search(self, query: str, *, limit: int = 5) -> list[SearchHit]:
        return self.hits[:limit]


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
