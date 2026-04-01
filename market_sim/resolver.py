import random
from datetime import datetime

from models.market import Market


class MarketResolver:
    """
    Resolves markets that have passed their resolution date.

    Outcome probability is weighted by:
    - The market's base_prob from metadata (ground truth)
    - Plus any accumulated sentiment from research
    """

    def should_resolve(self, market: Market) -> bool:
        return not market.resolved and datetime.utcnow() >= market.resolution_date

    def resolve(self, market: Market, sentiment_score: float = 0.0) -> Market:
        """Determine the outcome and return a resolved copy of the market."""
        base_prob = market.metadata.get("base_prob", market.market_price)

        # Sentiment shifts outcome probability slightly
        outcome_prob = base_prob + sentiment_score * 0.10
        outcome_prob = max(0.05, min(0.95, outcome_prob))

        outcome = random.random() < outcome_prob
        return market.resolve(outcome)
