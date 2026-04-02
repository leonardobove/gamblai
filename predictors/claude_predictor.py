import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings, get_setting
from models.market import Market
from models.prediction import Prediction, PredictorSource
from models.research import ResearchReport
from predictors.base import BasePredictor


_SYSTEM_PROMPT = """You are a superforecaster specializing in prediction markets.
Estimate the probability that a binary market resolves YES.

Think step by step:
1. Consider the base rate for this type of event
2. Update based on the research evidence provided
3. Account for the market's current implied probability as a reference signal (but don't anchor to it)
4. Produce a calibrated probability estimate

You MUST call the submit_prediction tool with your answer."""

# Tool definition forces Claude to return structured output — no JSON parsing needed
_PREDICTION_TOOL = {
    "name": "submit_prediction",
    "description": "Submit a calibrated probability estimate for a prediction market.",
    "input_schema": {
        "type": "object",
        "properties": {
            "probability": {
                "type": "number",
                "description": "Probability the market resolves YES, between 0.0 and 1.0",
            },
            "confidence": {
                "type": "number",
                "description": "Your self-assessed confidence in this estimate, between 0.0 and 1.0",
            },
            "reasoning": {
                "type": "string",
                "description": "2-3 sentence explanation of your reasoning",
            },
        },
        "required": ["probability", "confidence", "reasoning"],
    },
}


class ClaudePredictor(BasePredictor):
    def __init__(self):
        self._client = anthropic.Anthropic(api_key=get_setting("anthropic_api_key"))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def predict(self, market: Market, research: ResearchReport) -> Prediction:
        news_block = "\n".join(
            f"- [{item.source}] {item.title}: {item.snippet}"
            for item in research.news_items[:5]
        ) or "No news found."

        user_prompt = f"""Market question: {market.question}
Category: {market.category.value}
Current market price (implied probability): {market.market_price:.1%}
Research summary: {research.summary}
Sentiment score: {research.sentiment_score:+.2f} (-1=bearish, +1=bullish)

Recent news:
{news_block}

Estimate the probability this market resolves YES, then call submit_prediction."""

        message = self._client.messages.create(
            model=settings.claude_model,
            max_tokens=500,
            system=_SYSTEM_PROMPT,
            tools=[_PREDICTION_TOOL],
            tool_choice={"type": "tool", "name": "submit_prediction"},
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Extract structured input from the tool call — always valid, no parsing needed
        tool_block = next(b for b in message.content if b.type == "tool_use")
        data = tool_block.input

        probability = max(0.02, min(0.98, float(data["probability"])))
        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.6))))
        reasoning = str(data.get("reasoning", "No reasoning provided."))

        return Prediction(
            source=PredictorSource.CLAUDE,
            probability=probability,
            confidence=confidence,
            reasoning=reasoning,
        )
