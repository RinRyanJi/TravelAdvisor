"""Shared HTTP client configuration for the provider adapters."""

from __future__ import annotations

import httpx

# A descriptive User-Agent is required by OSM/Nominatim's usage policy and is
# good manners for the other open services too.
USER_AGENT = "TravelAdvisor/0.1 (+https://github.com/RinRyanJi/TravelAdvisor)"

DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def new_client(base_url: str = "", timeout: httpx.Timeout | None = None) -> httpx.Client:
    """Create an httpx client with the project's defaults applied."""
    return httpx.Client(
        base_url=base_url,
        timeout=timeout or DEFAULT_TIMEOUT,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        follow_redirects=True,
    )
