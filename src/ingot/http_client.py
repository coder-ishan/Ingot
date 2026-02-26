"""
Shared async HTTP client with connection pooling.

All agents use this — never create httpx.AsyncClient() inline.
One client per process; reused across requests to avoid TCP handshake overhead.
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

_client: httpx.AsyncClient | None = None
_config_snapshot: "HttpClientConfig | None" = None

_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; INGOT/0.1; +https://github.com/ingot)"
)


@dataclass
class HttpClientConfig:
    """Configuration for the shared async HTTP client."""
    max_keepalive_connections: int = 5
    max_connections: int = 10
    timeout_seconds: float = 30.0
    request_delay_seconds: float = 1.0  # Polite scraping delay


def get_http_client(config: HttpClientConfig | None = None) -> httpx.AsyncClient:
    """
    Return the shared AsyncClient. Creates it on first call.

    Pass ``config`` to override defaults; only applied on first creation or after
    close_http_client(). In tests, call close_http_client() in teardown to reset.
    """
    global _client, _config_snapshot

    if config is not None:
        _config_snapshot = config

    effective = _config_snapshot or HttpClientConfig()

    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_keepalive_connections=effective.max_keepalive_connections,
                max_connections=effective.max_connections,
            ),
            timeout=httpx.Timeout(effective.timeout_seconds),
            headers={
                "User-Agent": _DEFAULT_USER_AGENT,
                "Accept": "text/html,application/json,*/*",
            },
            follow_redirects=True,
        )
    return _client


async def close_http_client() -> None:
    """Close and reset the shared client. Call in test teardown or on shutdown."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None
