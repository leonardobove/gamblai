from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class PredictorSource(str, Enum):
    CLAUDE = "claude"
    BAYESIAN = "bayesian"
    MIROFISH = "mirofish"


class Prediction(BaseModel):
    model_config = {"frozen": True}

    source: PredictorSource
    probability: float  # 0.0-1.0
    confidence: float  # 0.0-1.0
    reasoning: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EnsemblePrediction(BaseModel):
    model_config = {"frozen": True}

    market_id: str
    final_probability: float  # Weighted average
    predictions: list[Prediction]
    weights: dict[str, float]  # PredictorSource value -> weight
