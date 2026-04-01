import structlog

from db.repositories import TradeRepository
from models.market import Market
from models.portfolio import Portfolio
from models.prediction import EnsemblePrediction
from models.risk import RiskAssessment
from risk_engine.guardrails import Guardrails

log = structlog.get_logger()


class RiskStep:
    def __init__(self):
        self._guardrails = Guardrails()
        self._trade_repo = TradeRepository()

    def run(self, market: Market, ensemble: EnsemblePrediction, portfolio: Portfolio) -> RiskAssessment:
        recent_pnls = self._trade_repo.find_recent_pnls(limit=50)
        assessment = self._guardrails.assess(
            market=market,
            p_model=ensemble.final_probability,
            portfolio=portfolio,
            recent_pnls=recent_pnls,
        )

        if assessment.approved:
            log.info(
                "risk_approved",
                market_id=market.id,
                edge=assessment.kelly.edge,
                size=assessment.kelly.recommended_size,
            )
        else:
            log.info(
                "risk_rejected",
                market_id=market.id,
                reasons=assessment.rejection_reasons,
            )

        return assessment
