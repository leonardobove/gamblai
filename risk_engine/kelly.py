from config import settings
from models.risk import KellyResult


def calculate_kelly(p_model: float, market_price: float, bankroll: float) -> KellyResult:
    """
    Kelly Criterion position sizing.

    For BUY_YES:
      b = decimal odds - 1 = (1/market_price) - 1
      f* = (p*b - (1-p)) / b

    Uses quarter-Kelly by default for lower variance.
    """
    p = p_model
    q = 1 - p
    edge = p - market_price

    # Decimal odds for a YES contract at the given market price
    b = max(0.001, (1 / market_price) - 1)

    full_kelly = (p * b - q) / b
    full_kelly = max(0.0, full_kelly)  # Never bet negative fraction

    quarter_kelly = full_kelly * settings.kelly_fraction
    quarter_kelly = min(quarter_kelly, settings.max_position_pct)

    recommended_size = round(quarter_kelly * bankroll, 2)
    expected_value = p * b - q

    return KellyResult(
        full_kelly=round(full_kelly, 6),
        quarter_kelly=round(quarter_kelly, 6),
        recommended_size=recommended_size,
        edge=round(edge, 6),
        expected_value=round(expected_value, 6),
    )
