import ipaddress
import socket
from urllib.parse import urlsplit, urlunsplit

PRIVATE_NETWORKS = (
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)


class SsrfBlockedError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if not scheme or not host:
        raise SsrfBlockedError("invalid_url")
    port = parts.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        netloc = f"{host}:{port}"
    else:
        netloc = host
    path = parts.path or "/"
    return urlunsplit((scheme, netloc, path, parts.query, ""))


def ip_is_blocked(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved or addr.is_multicast:
        return True
    return any(addr in net for net in PRIVATE_NETWORKS)


def assert_public_url(url: str, resolved_ips: list[str] | None = None) -> str:
    canonical = canonicalize_url(url)
    parts = urlsplit(canonical)
    if parts.scheme not in {"http", "https"}:
        raise SsrfBlockedError("blocked_ssrf")
    host = parts.hostname or ""
    if host in {"localhost", "metadata.google.internal"} or host.endswith(".local"):
        raise SsrfBlockedError("blocked_ssrf")
    try:
        ipaddress.ip_address(host)
        if ip_is_blocked(host):
            raise SsrfBlockedError("blocked_ssrf")
    except ValueError:
        pass
    ips = resolved_ips if resolved_ips is not None else _resolve(host)
    if not ips or any(ip_is_blocked(ip) for ip in ips):
        raise SsrfBlockedError("blocked_ssrf")
    return canonical


def _resolve(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise SsrfBlockedError("blocked_ssrf") from exc
    return list({info[4][0] for info in infos})
