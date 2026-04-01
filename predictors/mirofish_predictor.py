"""
MiroFish predictor adapter (optional).

MiroFish (https://github.com/666ghj/MiroFish) is a swarm intelligence engine
that simulates thousands of autonomous agents to predict outcomes.

Integration approach:
- Calls MiroFish via HTTP POST to its backend API (default: http://localhost:5001)
- Translates Market + ResearchReport into a MiroFish scenario
- Extracts consensus probability from the simulation result

Enable via: MIROFISH_ENABLED=true in .env
Requires MiroFish running locally: cd mirofish && npm run dev
"""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

from config import settings
from models.market import Market
from models.prediction import Prediction, PredictorSource
from models.research import ResearchReport
from predictors.base import BasePredictor

log = structlog.get_logger()


class MiroFishPredictor(BasePredictor):
    def __init__(self):
        self._base_url = settings.mirofish_url.rstrip("/")
        self._timeout = settings.mirofish_timeout

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=8))
    def predict(self, market: Market, research: ResearchReport) -> Prediction:
        scenario = self._build_scenario(market, research)
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(f"{self._base_url}/api/predict", json=scenario)
                response.raise_for_status()
                data = response.json()
            return self._parse_response(data)
        except Exception as e:
            log.warning("mirofish_unavailable", error=str(e))
            # Return a neutral prediction if MiroFish is unavailable
            return Prediction(
                source=PredictorSource.MIROFISH,
                probability=0.50,
                confidence=0.0,
                reasoning=f"MiroFish unavailable: {str(e)[:100]}. Using neutral 50%.",
            )

    def _build_scenario(self, market: Market, research: ResearchReport) -> dict:
        """Convert a Market + ResearchReport into the MiroFish scenario format."""
        news_context = "\n".join(
            f"- {item.title}: {item.snippet}" for item in research.news_items[:3]
        )
        return {
            "question": market.question,
            "context": f"{research.summary}\n\nRecent news:\n{news_context}",
            "category": market.category.value,
            "agent_count": 50,  # Keep low for speed
            "debate_rounds": 3,
        }

    def _parse_response(self, data: dict) -> Prediction:
        """Extract probability from MiroFish simulation result."""
        # MiroFish returns consensus as a ratio of agents that voted YES
        consensus = data.get("consensus_yes_ratio", data.get("probability", 0.5))
        probability = max(0.02, min(0.98, float(consensus)))
        confidence = float(data.get("confidence", 0.5))
        reasoning = data.get("summary", "MiroFish swarm simulation result.")

        return Prediction(
            source=PredictorSource.MIROFISH,
            probability=round(probability, 4),
            confidence=round(confidence, 4),
            reasoning=reasoning,
        )
