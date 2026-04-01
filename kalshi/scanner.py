"""
Fetches and filters real markets from Kalshi, converting them into
the project's internal Market model so the rest of the pipeline
(research → predict → risk → compound) works unchanged.
"""

from datetime import datetime, timezone

import structlog

from kalshi.client import KalshiClient
from models.market import Market, MarketCategory

log = structlog.get_logger()

# Minimum volume (contracts) to consider a market liquid enough
_MIN_VOLUME = 200
# Minimum days until resolution (too-fast markets are hard to research)
_MIN_DAYS = 1
# Maximum days until resolution (PDF: 30 days)
_MAX_DAYS = 30

_CATEGORY_MAP: dict[str, MarketCategory] = {
    "politics": MarketCategory.POLITICS,
    "elections": MarketCategory.POLITICS,
    "economics": MarketCategory.POLITICS,
    "weather": MarketCategory.WEATHER,
    "climate": MarketCategory.WEATHER,
    "sports": MarketCategory.SPORTS,
    "crypto": MarketCategory.CRYPTO,
    "financials": MarketCategory.CRYPTO,
    "entertainment": MarketCategory.ENTERTAINMENT,
    "culture": MarketCategory.ENTERTAINMENT,
}


def _map_category(raw: str) -> MarketCategory:
    return _CATEGORY_MAP.get(raw.lower(), MarketCategory.ENTERTAINMENT)


def _cents_to_prob(cents: int) -> float:
    """Kalshi prices are integers 0-100 (cents). Convert to probability 0.0-1.0."""
    return max(0.02, min(0.98, cents / 100.0))


class KalshiScanner:
    def __init__(self, client: KalshiClient):
        self._client = client

    def scan(self, limit: int = 100) -> list[Market]:
        """Fetch active Kalshi markets and return filtered Market objects."""
        try:
            data = self._client.get("/markets", params={"limit": limit, "status": "active"})
        except Exception as e:
            log.error("kalshi_scan_failed", error=str(e))
            return []

        markets = []
        now = datetime.now(timezone.utc)

        for raw in data.get("markets", []):
            try:
                market = self._parse_market(raw, now)
                if market:
                    markets.append(market)
            except Exception as e:
                log.debug("kalshi_market_parse_error", ticker=raw.get("ticker"), error=str(e))

        log.info("kalshi_scan_complete", total_fetched=len(data.get("markets", [])), passed_filters=len(markets))
        return markets

    def _parse_market(self, raw: dict, now: datetime) -> Market | None:
        ticker = raw.get("ticker", "")
        title = raw.get("title", "")
        if not ticker or not title:
            return None

        # Parse resolution date
        close_time_str = raw.get("close_time")
        if not close_time_str:
            return None
        close_time = datetime.fromisoformat(close_time_str.replace("Z", "+00:00"))
        close_time_naive = close_time.replace(tzinfo=None)
        days_left = (close_time - now).days

        if days_left < _MIN_DAYS or days_left > _MAX_DAYS:
            return None

        # Volume filter
        volume = raw.get("volume", 0)
        if volume < _MIN_VOLUME:
            return None

        # Price: use mid of yes_bid / yes_ask as market implied probability
        yes_bid = raw.get("yes_bid", 50)
        yes_ask = raw.get("yes_ask", 50)
        mid_cents = (yes_bid + yes_ask) / 2
        market_price = _cents_to_prob(mid_cents)

        # Category
        category_raw = raw.get("category", raw.get("event_category", "entertainment"))
        category = _map_category(category_raw)

        return Market(
            id=ticker,  # Use Kalshi ticker as ID for easy order placement
            question=title,
            category=category,
            market_price=market_price,
            resolution_date=close_time_naive,
            metadata={
                "source": "kalshi",
                "ticker": ticker,
                "yes_bid": yes_bid,
                "yes_ask": yes_ask,
                "volume": volume,
                "open_interest": raw.get("open_interest", 0),
            },
        )
