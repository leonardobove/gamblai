"""
Composite provider — calls multiple providers and merges results,
deduplicating by URL so the same article never appears twice.
"""

import structlog

from models.market import Market
from research_providers.base import BaseResearchProvider

log = structlog.get_logger()


class CompositeResearchProvider(BaseResearchProvider):
    def __init__(self, providers: list[BaseResearchProvider]):
        self._providers = providers

    def search(self, market: Market) -> list[dict]:
        seen_urls: set[str] = set()
        merged: list[dict] = []

        for provider in self._providers:
            try:
                items = provider.search(market)
            except Exception as e:
                log.warning("composite_provider_error",
                            provider=type(provider).__name__, error=str(e))
                items = []

            for item in items:
                url = item.get("url", "")
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)
                merged.append(item)

        return merged[:10]  # cap at 10 items to keep prompt size reasonable
