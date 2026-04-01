import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from db.repositories import KnowledgeRepository
from models.trade import Trade
from models.market import Market


class PostMortem:
    def __init__(self):
        self._repo = KnowledgeRepository()
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def analyze(self, trade: Trade, market: Market) -> str:
        """Use Claude to analyze a resolved trade and generate a lesson."""
        if not settings.anthropic_api_key:
            lesson = self._heuristic_lesson(trade, market)
            self._repo.save_insight(market.category.value, lesson, trade.id)
            return lesson

        outcome_desc = "WON" if (trade.pnl or 0) > 0 else "LOST"
        prompt = f"""Analyze this prediction market trade result and provide a concise lesson (2-3 sentences max).

Market: {market.question}
Category: {market.category.value}
Our predicted probability: {trade.predicted_probability:.1%}
Market price at entry: {trade.entry_price:.1%}
Edge we saw: {trade.edge:.1%}
Position: {trade.action.value}
Result: {outcome_desc} — PnL: ${trade.pnl:.2f}
Market outcome: {"YES" if market.outcome else "NO"}

What does this tell us about how to trade {market.category.value} markets? Be specific and actionable."""

        message = self._client.messages.create(
            model=settings.claude_model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        lesson = message.content[0].text.strip()
        self._repo.save_insight(market.category.value, lesson, trade.id)
        return lesson

    def _heuristic_lesson(self, trade: Trade, market: Market) -> str:
        won = (trade.pnl or 0) > 0
        if won:
            return (
                f"Correctly identified {trade.edge:.1%} edge in {market.category.value} market. "
                f"Prediction of {trade.predicted_probability:.1%} vs market {trade.entry_price:.1%} was accurate."
            )
        else:
            return (
                f"Edge estimate of {trade.edge:.1%} in {market.category.value} market was incorrect. "
                f"Consider tightening confidence thresholds for this category."
            )
