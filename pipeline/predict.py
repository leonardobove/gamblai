import structlog

from config import settings
from models.market import Market
from models.prediction import EnsemblePrediction
from models.research import ResearchReport
from predictors.bayesian_predictor import BayesianPredictor
from predictors.claude_predictor import ClaudePredictor
from predictors.ensemble import EnsembleAggregator
from predictors.mirofish_predictor import MiroFishPredictor

log = structlog.get_logger()


class PredictStep:
    def __init__(self):
        self._bayesian = BayesianPredictor()
        self._ensemble = EnsembleAggregator()
        self._claude = ClaudePredictor() if settings.anthropic_api_key else None
        self._mirofish = MiroFishPredictor() if settings.mirofish_enabled else None

    def run(self, market: Market, research: ResearchReport) -> EnsemblePrediction:
        predictions = []

        # Bayesian always runs (no API needed)
        bayesian_pred = self._bayesian.predict(market, research)
        predictions.append(bayesian_pred)
        log.debug("bayesian_prediction", market_id=market.id, prob=bayesian_pred.probability)

        # Claude (primary predictor)
        if self._claude:
            try:
                claude_pred = self._claude.predict(market, research)
                predictions.append(claude_pred)
                log.debug("claude_prediction", market_id=market.id, prob=claude_pred.probability)
            except Exception as e:
                log.warning("claude_prediction_failed", market_id=market.id, error=str(e))

        # MiroFish (optional)
        if self._mirofish:
            try:
                mirofish_pred = self._mirofish.predict(market, research)
                predictions.append(mirofish_pred)
                log.debug("mirofish_prediction", market_id=market.id, prob=mirofish_pred.probability)
            except Exception as e:
                log.warning("mirofish_prediction_failed", market_id=market.id, error=str(e))

        ensemble = self._ensemble.aggregate(market.id, predictions)
        log.info(
            "ensemble_complete",
            market_id=market.id,
            final_prob=ensemble.final_probability,
            sources=[p.source.value for p in predictions],
        )
        return ensemble
