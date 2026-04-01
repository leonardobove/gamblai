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

You MUST respond with ONLY a valid JSON object and nothing else — no markdown, no code fences, no explanation outside the JSON.
Use this exact format:
{"probability": 0.65, "confidence": 0.7, "reasoning": "Your 2-3 sentence explanation here."}"""


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
        # Strip markdown code fences if present
        text = re.sub(r"```(?:json)?\s*", "", text).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try extracting the first JSON object from the text
            match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            # Last resort: try to extract probability with regex
            prob_match = re.search(r'"probability"\s*:\s*([\d.]+)', text)
            if prob_match:
                return {
                    "probability": float(prob_match.group(1)),
                    "confidence": 0.5,
                    "reasoning": "Parsed from malformed response.",
                }
            raise ValueError(f"Could not parse JSON from Claude response: {text[:200]}")
