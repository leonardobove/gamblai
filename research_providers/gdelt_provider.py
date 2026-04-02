"""
GDELT 2.0 Doc API provider — completely free, no API key required.
Covers 65+ languages, millions of news articles updated every 15 minutes.
https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
"""

import httpx
import structlog

from models.market import Market
from research_providers.base import BaseResearchProvider

log = structlog.get_logger()

_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"
_TIMEOUT = 15.0


class GDELTProvider(BaseResearchProvider):
    """
    Uses the GDELT DOC 2.0 API to fetch recent news articles matching
    the market question. No API key needed — always available as fallback.

    Note: GDELT articles include titles and URLs but not full snippets.
    The sentiment analysis step will work on titles alone in this case.
    """

    def search(self, market: Market) -> list[dict]:
        query = _make_query(market.question)

        try:
            resp = httpx.get(
                _DOC_API,
                params={
                    "query": query,
                    "mode": "artlist",
                    "maxrecords": "10",
                    "timespan": "7d",       # last 7 days
                    "format": "json",
                    "sourcelang": "english",
                },
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            log.warning("gdelt_search_failed", error=str(e), query=query)
            return []

        articles = data.get("articles") or []
        results = []
        for article in articles[:5]:
            title = (article.get("title") or "").strip()
            url = article.get("url") or ""
            domain = article.get("domain") or _domain(url)

            if not title:
                continue

            results.append({
                "title": title,
                "snippet": title,   # GDELT doesn't return body text
                "source": domain,
                "url": url,
            })

        log.info("gdelt_search_complete", query=query, results=len(results))
        return results


def _make_query(question: str) -> str:
    """
    GDELT queries work best with 2-5 key nouns.
    Strip question words and common stop words.
    """
    stop = {"will", "the", "a", "an", "be", "is", "are", "was", "were",
            "in", "on", "at", "to", "of", "for", "by", "their", "its",
            "this", "that", "or", "and", "before", "after", "than",
            "between", "until", "have", "has", "it", "if", "not",
            "below", "above", "over", "under", "any", "all", "how",
            "much", "more", "per", "end", "week", "month", "year",
            "season", "next", "last", "upcoming", "latest"}
    words = []
    for word in question.split():
        clean = word.strip("?.,!\"'()")
        if clean.lower() not in stop and len(clean) > 2:
            words.append(clean)
        if len(words) == 5:
            break
    return " ".join(words) if words else question[:60]


def _domain(url: str) -> str:
    try:
        return url.split("/")[2]
    except IndexError:
        return "unknown"
