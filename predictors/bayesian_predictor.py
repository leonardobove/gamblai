from models.market import Market
from models.prediction import Prediction, PredictorSource
from models.research import ResearchReport
from knowledge.base_rates import get_base_rate
from predictors.base import BasePredictor


class BayesianPredictor(BasePredictor):
    """
    Simple Bayesian predictor using category base rates as a prior,
    then updating on sentiment as likelihood.
    """

    def predict(self, market: Market, research: ResearchReport) -> Prediction:
        prior = get_base_rate(market.category.value)

        # Likelihood update: sentiment nudges the prior
        sentiment_update = research.sentiment_score * 0.12
        posterior = prior + sentiment_update
        posterior = max(0.05, min(0.95, posterior))

        confidence = 0.5  # Bayesian baseline is always moderate confidence

        reasoning = (
            f"Base rate for {market.category.value}: {prior:.1%}. "
            f"Sentiment score {research.sentiment_score:+.2f} shifted estimate by {sentiment_update:+.1%}. "
            f"Posterior: {posterior:.1%}."
        )

        return Prediction(
            source=PredictorSource.BAYESIAN,
            probability=round(posterior, 4),
            confidence=confidence,
            reasoning=reasoning,
        )
