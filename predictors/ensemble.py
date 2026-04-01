from config import settings
from models.market import Market
from models.prediction import Prediction, EnsemblePrediction, PredictorSource
from models.research import ResearchReport


_DEFAULT_WEIGHTS_WITH_MIROFISH = {
    PredictorSource.CLAUDE: 0.60,
    PredictorSource.BAYESIAN: 0.30,
    PredictorSource.MIROFISH: 0.10,
}

_DEFAULT_WEIGHTS_WITHOUT_MIROFISH = {
    PredictorSource.CLAUDE: 0.65,
    PredictorSource.BAYESIAN: 0.35,
}


class EnsembleAggregator:
    def aggregate(self, market_id: str, predictions: list[Prediction]) -> EnsemblePrediction:
        weights = (
            _DEFAULT_WEIGHTS_WITH_MIROFISH
            if settings.mirofish_enabled
            else _DEFAULT_WEIGHTS_WITHOUT_MIROFISH
        )

        total_weight = 0.0
        weighted_sum = 0.0
        used_weights: dict[str, float] = {}

        for pred in predictions:
            w = weights.get(pred.source, 0.0)
            weighted_sum += pred.probability * w
            total_weight += w
            used_weights[pred.source.value] = w

        if total_weight == 0:
            # Fallback: simple average
            final_prob = sum(p.probability for p in predictions) / len(predictions)
        else:
            final_prob = weighted_sum / total_weight

        final_prob = round(max(0.02, min(0.98, final_prob)), 4)

        return EnsemblePrediction(
            market_id=market_id,
            final_probability=final_prob,
            predictions=predictions,
            weights=used_weights,
        )
