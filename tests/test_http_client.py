"""Tests for ingot.http_client singleton."""
import httpx

from ingot.http_client import HttpClientConfig, close_http_client, get_http_client


async def test_singleton_returns_same_instance():
    await close_http_client()
    c1 = get_http_client()
    c2 = get_http_client()
    assert c1 is c2
    await close_http_client()


async def test_close_resets_singleton():
    await close_http_client()
    c1 = get_http_client()
    await close_http_client()
    c2 = get_http_client()
    assert c1 is not c2
    await close_http_client()


async def test_custom_config_applied():
    await close_http_client()
    cfg = HttpClientConfig(max_connections=5, timeout_seconds=10.0)
    client = get_http_client(config=cfg)
    assert client.timeout.read == 10.0
    await close_http_client()
