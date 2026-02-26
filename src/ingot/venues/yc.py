"""
YC Company data fetcher using the yc-oss community JSON API.

PRIMARY SOURCE: https://yc-oss.github.io/api/
- Refreshed daily via GitHub Actions from YC's Algolia index
- 5,690+ publicly launched companies in clean JSON
- NO scraping, NO JavaScript rendering, NO Playwright needed

DO NOT scrape ycombinator.com directly:
- Their company directory uses Algolia + infinite scroll JS rendering
- httpx GET returns <div id="__next"> with no company data (Pitfall 1 in 02-RESEARCH.md)
"""
import asyncio
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

YC_OSS_BASE_URL = "https://yc-oss.github.io/api"
YC_HEADERS = {"User-Agent": "INGOT/0.1 (outreach tool; github.com/ingot-app/ingot)"}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def fetch_yc_companies(
    http_client: httpx.AsyncClient,
    batch: str | None = None,
    industry: str | None = None,
) -> list[dict]:
    """
    Fetch YC company records from yc-oss GitHub Pages API.

    Args:
        http_client: Shared async httpx client (from ScoutDeps)
        batch: YC batch slug e.g. "winter-2025", "summer-2024". None = all companies.
        industry: Industry slug e.g. "b2b", "consumer". None = all industries.

    Returns:
        List of company dicts. Each has: id, name, slug, website, one_liner,
        long_description, team_size, industry, tags, batch, stage, isHiring.

    Raises:
        httpx.HTTPError on network failure (tenacity retries 3 times).
    """
    if batch:
        url = f"{YC_OSS_BASE_URL}/batches/{batch}.json"
    elif industry:
        url = f"{YC_OSS_BASE_URL}/industries/{industry}.json"
    else:
        url = f"{YC_OSS_BASE_URL}/companies/all.json"

    try:
        resp = await http_client.get(url, headers=YC_HEADERS, timeout=30.0)
        resp.raise_for_status()
        companies = resp.json()
    except httpx.HTTPStatusError:
        if batch or industry:
            # Batch/industry not found — fall back to all companies
            resp = await http_client.get(
                f"{YC_OSS_BASE_URL}/companies/all.json",
                headers=YC_HEADERS,
                timeout=30.0
            )
            resp.raise_for_status()
            companies = resp.json()
        else:
            raise

    assert isinstance(companies, list), f"Expected list, got {type(companies)}"
    assert len(companies) > 100, f"Suspiciously few companies: {len(companies)}"
    return companies
