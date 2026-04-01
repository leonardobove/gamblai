from config import settings


def check_drawdown(current_bankroll: float, peak_bankroll: float) -> bool:
    """Return True if drawdown is within acceptable limits."""
    if peak_bankroll <= 0:
        return True
    drawdown = (peak_bankroll - current_bankroll) / peak_bankroll
    return drawdown <= settings.max_drawdown_pct
