from pydantic import BaseModel


class KellyResult(BaseModel):
    model_config = {"frozen": True}

    full_kelly: float
    quarter_kelly: float
    recommended_size: float  # In dollars
    edge: float
    expected_value: float


class VaRResult(BaseModel):
    model_config = {"frozen": True}

    var_95: float
    portfolio_mean_return: float
    portfolio_std: float
    passes: bool


class RiskAssessment(BaseModel):
    model_config = {"frozen": True}

    market_id: str
    kelly: KellyResult
    var: VaRResult
    drawdown_ok: bool
    max_position_ok: bool
    concurrent_positions_ok: bool
    approved: bool
    rejection_reasons: list[str]
