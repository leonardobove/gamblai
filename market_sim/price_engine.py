import random
import math

from models.market import Market


class PriceEngine:
    """Simulates small random price drift each cycle, optionally influenced by sentiment."""

    def drift(self, market: Market, sentiment_score: float = 0.0) -> Market:
        """Apply Brownian-motion-style drift, nudged by sentiment."""
        if market.resolved:
            return market

        # Base random walk: ±2% per cycle
        drift = random.gauss(0, 0.02)

        # Sentiment nudge: positive sentiment pushes price up, negative pushes down
        sentiment_nudge = sentiment_score * 0.015

        new_price = market.market_price + drift + sentiment_nudge
        new_price = max(0.02, min(0.98, new_price))

        return market.with_price(round(new_price, 4))
