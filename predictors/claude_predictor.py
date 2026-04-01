import json
import re

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from models.market import Market
from models.prediction import Prediction, PredictorSource
from models.research import ResearchReport
from predictors.base import BasePredictor


_SYSTEM_PROMPT = """You are a superforecaster specializing in prediction markets.
Your task is to estimate the probability that a binary market resolves YES.

Think step by step:
1. Consider the base rate for this type of event
2. Update based on the research evidence provided
3. Account for the market's current implied probability as a reference signal (but don't anchor to it)
4. Produce a calibrated probability estimate

Respond ONLY with valid JSON in this exact format:
{
  "probability": <float 0.0-1.0>,
  "confidence": <float 0.0-1.0, your self-assessed confidence>,
  "reasoning": "<2-3 sentence explanation>"
}"""


class ClaudePredictor(BasePredictor):
    def __init__(self):
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

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

Estimate the probability this market resolves YES."""

        message = self._client.messages.create(
            model=settings.claude_model,
            max_tokens=300,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = message.content[0].text.strip()
        data = self._parse_json(raw)

        probability = max(0.02, min(0.98, float(data["probability"])))
        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.6))))
        reasoning = str(data.get("reasoning", "No reasoning provided."))

        return Prediction(
            source=PredictorSource.CLAUDE,
            probability=probability,
            confidence=confidence,
            reasoning=reasoning,
        )

    def _parse_json(self, text: str) -> dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ValueError(f"Could not parse JSON from Claude response: {text[:200]}")
