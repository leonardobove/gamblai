from config import settings
from models.market import Market
from models.portfolio import Portfolio
from models.risk import RiskAssessment
from risk_engine.kelly import calculate_kelly
from risk_engine.var import calculate_var
from risk_engine.drawdown import check_drawdown


class Guardrails:
    def assess(
        self,
        market: Market,
        p_model: float,
        portfolio: Portfolio,
        recent_pnls: list[float],
    ) -> RiskAssessment:
        rejection_reasons: list[str] = []

        kelly = calculate_kelly(p_model, market.market_price, portfolio.bankroll)
        var = calculate_var(recent_pnls, kelly.recommended_size)

        edge_ok = kelly.edge >= settings.edge_threshold
        if not edge_ok:
            rejection_reasons.append(
                f"Edge {kelly.edge:.3f} below threshold {settings.edge_threshold}"
            )

        drawdown_ok = check_drawdown(portfolio.bankroll, portfolio.peak_bankroll)
        if not drawdown_ok:
            rejection_reasons.append(
                f"Drawdown circuit breaker triggered (>{settings.max_drawdown_pct:.0%})"
            )

        max_position_ok = kelly.recommended_size >= 1.0
        if not max_position_ok:
            rejection_reasons.append("Recommended position size too small (<$1)")

        if not var.passes:
            rejection_reasons.append(f"VaR check failed: position ${kelly.recommended_size:.2f} too large")

        concurrent_ok = len(portfolio.open_positions) < settings.max_concurrent_positions
        if not concurrent_ok:
            rejection_reasons.append(
                f"Max concurrent positions reached ({settings.max_concurrent_positions})"
            )

        bankroll_ok = portfolio.bankroll >= 10.0
        if not bankroll_ok:
            rejection_reasons.append("Bankroll too low (<$10)")

        approved = edge_ok and drawdown_ok and max_position_ok and var.passes and concurrent_ok and bankroll_ok

        return RiskAssessment(
            market_id=market.id,
            kelly=kelly,
            var=var,
            drawdown_ok=drawdown_ok,
            max_position_ok=max_position_ok,
            concurrent_positions_ok=concurrent_ok,
            approved=approved,
            rejection_reasons=rejection_reasons,
        )
