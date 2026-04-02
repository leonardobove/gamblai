import math
from models.risk import VaRResult


_Z_95 = 1.645  # z-score for 95% confidence


def calculate_var(returns: list[float], position_size: float) -> VaRResult:
    """
    Parametric Value at Risk at 95% confidence.

    If there aren't enough data points, return a permissive default.
    """
    if len(returns) < 20:
        return VaRResult(
            var_95=position_size,
            portfolio_mean_return=0.0,
            portfolio_std=0.0,
            passes=True,
        )

    n = len(returns)
    mean = sum(returns) / n
    variance = sum((r - mean) ** 2 for r in returns) / n
    std = math.sqrt(variance)

    # If all historical returns are identical (e.g. all $0 before first resolution),
    # std=0 would produce a degenerate VaR of 0 and block all trades. Treat as permissive.
    if std == 0.0:
        return VaRResult(
            var_95=position_size,
            portfolio_mean_return=round(mean, 4),
            portfolio_std=0.0,
            passes=True,
        )

    var_95 = -(mean - _Z_95 * std)

    # Trade passes if its size doesn't exceed 3x the historical 95% VaR of prior trades
    passes = position_size <= max(10.0, var_95 * 3)

    return VaRResult(
        var_95=round(var_95, 4),
        portfolio_mean_return=round(mean, 4),
        portfolio_std=round(std, 4),
        passes=passes,
    )
