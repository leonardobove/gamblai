"""
NewsAPI.org provider — free tier: 100 requests/day, English news only.
Sign up at https://newsapi.org/register to get a free API key.
"""

import httpx
import structlog

from config import get_setting
from models.market import Market
from research_providers.base import BaseResearchProvider

log = structlog.get_logger()

_BASE_URL = "https://newsapi.org/v2/everything"
_TIMEOUT = 10.0


class NewsAPIProvider(BaseResearchProvider):
    def search(self, market: Market) -> list[dict]:
        api_key = get_setting("newsapi_api_key")
        if not api_key:
            return []

        # Trim question to a concise search query (NewsAPI works best with <50 chars)
        query = _make_query(market.question)

        try:
            resp = httpx.get(
                _BASE_URL,
                params={
                    "q": query,
                    "apiKey": api_key,
                    "pageSize": 5,
                    "language": "en",
                    "sortBy": "publishedAt",
                },
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            log.warning("newsapi_search_failed", error=str(e), query=query)
            return []

        results = []
        for article in data.get("articles", []):
            title = article.get("title") or ""
            description = article.get("description") or ""
            url = article.get("url") or ""
            source_name = (article.get("source") or {}).get("name") or _domain(url)

            if not title or title == "[Removed]":
                continue

            results.append({
                "title": title,
                "snippet": description[:300],
                "source": source_name,
                "url": url,
            })

        log.info("newsapi_search_complete", query=query, results=len(results))
        return results


def _make_query(question: str) -> str:
    """Strip filler words and keep the meaningful keywords for NewsAPI."""
    stop = {"will", "the", "a", "an", "be", "is", "are", "was", "in", "on",
            "at", "to", "of", "for", "by", "their", "this", "that", "or",
            "and", "before", "after", "between", "until", "than"}
    words = [w for w in question.split() if w.lower().rstrip("?.,") not in stop]
    return " ".join(words[:8])  # NewsAPI query length sweet-spot


def _domain(url: str) -> str:
    try:
        return url.split("/")[2]
    except IndexError:
        return "unknown"
