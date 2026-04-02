import anthropic
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings, get_setting
from db.repositories import ResearchCacheRepository
from models.market import Market
from models.research import ResearchReport, NewsItem
from research_providers.base import BaseResearchProvider
from research_providers.mock_search import MockResearchProvider
from research_providers.web_search import TavilyResearchProvider

log = structlog.get_logger()


def _build_provider() -> BaseResearchProvider:
    if get_setting("tavily_api_key"):
        log.info("research_provider", type="tavily")
        return TavilyResearchProvider()
    log.info("research_provider", type="mock")
    return MockResearchProvider()


class ResearchStep:
    def __init__(self):
        self._cache = ResearchCacheRepository()
        self._provider = _build_provider()
        api_key = get_setting("anthropic_api_key")
        self._client = anthropic.Anthropic(api_key=api_key) if api_key else None

    def run(self, market: Market) -> ResearchReport:
        cached = self._cache.find_by_market(market.id, max_age_minutes=settings.research_cache_minutes)
        if cached:
            log.debug("research_cache_hit", market_id=market.id)
            return cached

        raw_items = self._provider.search(market)
        news_items = [
            NewsItem(
                title=r["title"],
                snippet=r["snippet"],
                source=r["source"],
                url=r["url"],
            )
            for r in raw_items
        ]

        summary, sentiment = self._summarize(market, news_items)

        report = ResearchReport(
            market_id=market.id,
            news_items=news_items,
            summary=summary,
            sentiment_score=round(sentiment, 3),
        )
        self._cache.save(report)
        log.info("research_complete", market_id=market.id, items=len(news_items), sentiment=sentiment)
        return report

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=8))
    def _summarize(self, market: Market, news_items: list[NewsItem]) -> tuple[str, float]:
        if not self._client:
            return self._heuristic_summary(market, news_items)

        news_text = "\n".join(f"- [{item.source}] {item.title}: {item.snippet}" for item in news_items)
        if not news_text:
            news_text = "No news available."

        prompt = f"""Market question: {market.question}

News gathered:
{news_text}

Provide:
1. A 2-sentence summary of what the news says about this market
2. A sentiment score from -1.0 (strongly bearish/NO) to +1.0 (strongly bullish/YES)

Format: SUMMARY: <text> | SENTIMENT: <float>"""

        message = self._client.messages.create(
            model=settings.claude_model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()
        return self._parse_summary(text)

    def _parse_summary(self, text: str) -> tuple[str, float]:
        import re
        summary_match = re.search(r"SUMMARY:\s*(.+?)(?:\||\Z)", text, re.DOTALL)
        sentiment_match = re.search(r"SENTIMENT:\s*([-\d.]+)", text)

        summary = summary_match.group(1).strip() if summary_match else text[:200]
        try:
            sentiment = float(sentiment_match.group(1)) if sentiment_match else 0.0
            sentiment = max(-1.0, min(1.0, sentiment))
        except ValueError:
            sentiment = 0.0
        return summary, sentiment

    def _heuristic_summary(self, market: Market, news_items: list[NewsItem]) -> tuple[str, float]:
        if not news_items:
            return "No news available for this market.", 0.0
        titles = " ".join(item.title for item in news_items[:3]).lower()
        bullish_words = ["up", "rise", "win", "strong", "positive", "gain", "high", "above", "beat"]
        bearish_words = ["down", "fall", "lose", "weak", "negative", "loss", "low", "below", "miss"]
        bull_count = sum(1 for w in bullish_words if w in titles)
        bear_count = sum(1 for w in bearish_words if w in titles)
        sentiment = (bull_count - bear_count) * 0.1
        sentiment = max(-1.0, min(1.0, sentiment))
        summary = f"Found {len(news_items)} news items for this market. Mixed signals observed."
        return summary, sentiment
