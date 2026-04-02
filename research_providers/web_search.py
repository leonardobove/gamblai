import structlog
from tavily import TavilyClient

from config import get_setting
from models.market import Market
from research_providers.base import BaseResearchProvider

log = structlog.get_logger()


class TavilyResearchProvider(BaseResearchProvider):
    def __init__(self):
        self._client = TavilyClient(api_key=get_setting("tavily_api_key"))

    def search(self, market: Market) -> list[dict]:
        try:
            response = self._client.search(
                query=market.question,
                search_depth="basic",
                max_results=5,
                include_raw_content=False,
            )
            results = []
            for r in response.get("results", []):
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("content", "")[:300],
                    "source": r.get("url", "").split("/")[2] if r.get("url") else "unknown",
                    "url": r.get("url", ""),
                })
            return results
        except Exception as e:
            log.warning("tavily_search_failed", error=str(e))
            return []
