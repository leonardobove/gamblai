import structlog

from config import settings
from db.repositories import PortfolioRepository
from models.portfolio import Portfolio
from pipeline.scan import ScanStep
from pipeline.research import ResearchStep
from pipeline.predict import PredictStep
from pipeline.risk import RiskStep
from pipeline.compound import CompoundStep
from market_sim.price_engine import PriceEngine
from db.repositories import MarketRepository

log = structlog.get_logger()


def _load_portfolio(repo: PortfolioRepository) -> Portfolio:
    history = repo.get_history(limit=1)
    if history:
        snap = history[-1]
        return Portfolio(
            bankroll=snap.bankroll,
            total_trades=snap.total_trades,
            winning_trades=int(snap.win_rate * snap.total_trades),
            total_pnl=snap.total_pnl,
            open_positions=[],
            peak_bankroll=max(snap.bankroll, settings.starting_bankroll),
            current_drawdown=snap.current_drawdown,
        )
    return Portfolio(
        bankroll=settings.starting_bankroll,
        peak_bankroll=settings.starting_bankroll,
    )


class PipelineRunner:
    def __init__(self):
        self._scan = ScanStep()
        self._research = ResearchStep()
        self._predict = PredictStep()
        self._risk = RiskStep()
        self._compound = CompoundStep()
        self._portfolio_repo = PortfolioRepository()
        self._market_repo = MarketRepository()
        self._price_engine = PriceEngine()

    def run_cycle(self) -> Portfolio:
        log.info("pipeline_cycle_start")

        portfolio = _load_portfolio(self._portfolio_repo)
        log.info("portfolio_loaded", bankroll=portfolio.bankroll, trades=portfolio.total_trades)

        # Step 1: Scan
        markets = self._scan.run()

        # Step 5 (pre): Resolve any expired markets before processing new ones
        portfolio = self._compound.process_resolved_markets(portfolio)

        for market in markets:
            if market.resolved:
                continue

            # Step 2: Research
            try:
                research = self._research.run(market)
            except Exception as e:
                log.warning("research_failed", market_id=market.id, error=str(e))
                continue

            # Price drift influenced by research sentiment
            drifted_market = self._price_engine.drift(market, research.sentiment_score)
            if drifted_market.market_price != market.market_price:
                self._market_repo.save(drifted_market)

            # Step 3: Predict
            try:
                ensemble = self._predict.run(drifted_market, research)
            except Exception as e:
                log.warning("predict_failed", market_id=market.id, error=str(e))
                continue

            # Step 4: Risk
            assessment = self._risk.run(drifted_market, ensemble, portfolio)

            # Step 5: Compound — execute or skip
            if assessment.approved:
                trade = self._compound.record_trade(drifted_market, ensemble, assessment)
                portfolio = portfolio.add_position(market.id)
            else:
                self._compound.record_skip(drifted_market, assessment)

        # Save portfolio snapshot
        snapshot = self._compound.snapshot(portfolio)
        self._portfolio_repo.save_snapshot(snapshot)

        log.info(
            "pipeline_cycle_complete",
            bankroll=portfolio.bankroll,
            open_positions=len(portfolio.open_positions),
            win_rate=f"{portfolio.win_rate:.1%}",
        )
        return portfolio
