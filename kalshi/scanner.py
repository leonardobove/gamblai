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
_MIN_VOLUME = 50
# Minimum days until resolution (0 = allow same-day markets)
_MIN_DAYS = 0
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
    "commodities": MarketCategory.CRYPTO,  # oil, gold etc → closest bucket
    "entertainment": MarketCategory.ENTERTAINMENT,
    "culture": MarketCategory.ENTERTAINMENT,
    "pop culture": MarketCategory.ENTERTAINMENT,
}

# Ticker prefix → category (used when API doesn't supply a text category)
_TICKER_PREFIX_MAP: dict[str, MarketCategory] = {
    "KXWTI": MarketCategory.CRYPTO,    # WTI crude oil
    "KXBTC": MarketCategory.CRYPTO,
    "KXETH": MarketCategory.CRYPTO,
    "KXNQ":  MarketCategory.CRYPTO,    # Nasdaq
    "KXSP":  MarketCategory.CRYPTO,    # S&P 500
    "INX":   MarketCategory.CRYPTO,
    "FED":   MarketCategory.POLITICS,
    "PRES":  MarketCategory.POLITICS,
}


def _map_category(raw: str, ticker: str = "") -> MarketCategory:
    # Try text category first
    if raw:
        result = _CATEGORY_MAP.get(raw.lower())
        if result:
            return result
    # Fall back to ticker prefix
    for prefix, cat in _TICKER_PREFIX_MAP.items():
        if ticker.upper().startswith(prefix):
            return cat
    return MarketCategory.ENTERTAINMENT


def _cents_to_prob(cents: int) -> float:
    """Kalshi prices are integers 0-100 (cents). Convert to probability 0.0-1.0."""
    return max(0.02, min(0.98, cents / 100.0))


class KalshiScanner:
    def __init__(self, client: KalshiClient):
        self._client = client

    def scan(self, limit: int = 100) -> list[Market]:
        """Fetch active Kalshi markets and return filtered Market objects."""
        try:
            data = self._client.get("/markets", params={"limit": limit, "status": "open"})
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

        # Volume filter — API returns volume_fp (float) or legacy volume (int)
        volume = float(raw.get("volume_fp") or raw.get("volume") or 0)
        if volume < _MIN_VOLUME:
            return None

        # Price: API returns yes_bid_dollars / yes_ask_dollars as dollar fractions (0.0–1.0)
        # which directly map to probability. Fall back to legacy cent fields if absent.
        if "yes_bid_dollars" in raw:
            yes_bid = float(raw.get("yes_bid_dollars") or 0.5)
            yes_ask = float(raw.get("yes_ask_dollars") or 0.5)
            market_price = max(0.02, min(0.98, (yes_bid + yes_ask) / 2))
        else:
            yes_bid = raw.get("yes_bid", 50)
            yes_ask = raw.get("yes_ask", 50)
            market_price = _cents_to_prob((yes_bid + yes_ask) / 2)

        # Category
        category_raw = raw.get("category") or raw.get("event_category") or ""
        category = _map_category(category_raw, ticker)

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
                "open_interest": float(raw.get("open_interest_fp") or raw.get("open_interest") or 0),
            },
        )
