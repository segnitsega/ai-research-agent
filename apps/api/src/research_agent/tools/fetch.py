import asyncio
from collections import defaultdict
from dataclasses import dataclass
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from research_agent.config import Settings
from research_agent.tools.safety import SsrfBlockedError, assert_public_url

ALLOWED_TYPES = ("text/html", "text/plain", "application/pdf", "application/xhtml+xml")
FAIL_REASONS = (
    "blocked_ssrf",
    "timeout",
    "http_error",
    "too_large",
    "unsupported_type",
    "robots",
)


@dataclass(frozen=True)
class FetchResult:
    url: str
    final_url: str
    content_type: str
    body: bytes
    from_cache: bool = False


class FetchFailed(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class GuardedFetcher:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self.settings = settings
        self._client = client
        self._domain_locks: dict[str, asyncio.Semaphore] = defaultdict(lambda: asyncio.Semaphore(2))

    async def fetch(self, url: str) -> FetchResult:
        owns = self._client is None
        client = self._client or httpx.AsyncClient(
            timeout=self.settings.fetch_timeout_s,
            follow_redirects=False,
        )
        try:
            current = url
            for _ in range(5):
                canonical = self._guard(current)
                parts = urlsplit(canonical)
                host = parts.hostname or ""
                async with self._domain_locks[host]:
                    if self.settings.respect_robots and not await self._allowed(client, canonical):
                        raise FetchFailed("robots")
                    self._pin(canonical)
                    try:
                        response = await client.get(
                            canonical,
                            headers={"User-Agent": self.settings.user_agent},
                        )
                    except httpx.TimeoutException as exc:
                        raise FetchFailed("timeout") from exc
                    except httpx.HTTPError as exc:
                        raise FetchFailed("http_error") from exc
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise FetchFailed("http_error")
                    current = location if "://" in location else f"{parts.scheme}://{host}{location}"
                    continue
                if response.status_code >= 400:
                    raise FetchFailed("http_error")
                content_type = response.headers.get("content-type", "text/plain").split(";")[0].strip().lower()
                if content_type not in ALLOWED_TYPES:
                    raise FetchFailed("unsupported_type")
                body = response.content
                limit = self.settings.fetch_max_bytes_pdf if content_type == "application/pdf" else self.settings.fetch_max_bytes
                if len(body) > limit:
                    raise FetchFailed("too_large")
                return FetchResult(url=url, final_url=canonical, content_type=content_type, body=body)
            raise FetchFailed("http_error")
        finally:
            if owns:
                await client.aclose()

    def _guard(self, url: str) -> str:
        try:
            canonical = assert_public_url(url)
        except SsrfBlockedError as exc:
            raise FetchFailed("blocked_ssrf") from exc
        host = (urlsplit(canonical).hostname or "").lower()
        blocked = self.settings.blocked_domain_set()
        allowed = self.settings.allowed_domain_set()
        if host in blocked or (allowed and host not in allowed):
            raise FetchFailed("blocked_ssrf")
        return canonical

    def _pin(self, url: str) -> None:
        parts = urlsplit(url)
        host = parts.hostname or ""
        try:
            import socket

            infos = socket.getaddrinfo(host, parts.port or (443 if parts.scheme == "https" else 80))
            ips = [str(item[4][0]) for item in infos]
        except OSError as exc:
            raise FetchFailed("blocked_ssrf") from exc
        try:
            assert_public_url(url, resolved_ips=ips)
        except SsrfBlockedError as exc:
            raise FetchFailed("blocked_ssrf") from exc

    async def _allowed(self, client: httpx.AsyncClient, url: str) -> bool:
        parts = urlsplit(url)
        robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
        try:
            response = await client.get(robots_url, headers={"User-Agent": self.settings.user_agent})
        except httpx.HTTPError:
            return True
        if response.status_code >= 400:
            return True
        parser = RobotFileParser()
        parser.parse(response.text.splitlines())
        return parser.can_fetch(self.settings.user_agent, url)
