import structlog

from config import settings, get_setting, get_bool_setting, get_kalshi_private_key_path
from db.repositories import TradeRepository, MarketRepository, KnowledgeRepository
from knowledge.calibration import CalibrationTracker
from knowledge.post_mortem import PostMortem
from models.market import Market
from models.portfolio import Portfolio, PortfolioSnapshot
from models.prediction import EnsemblePrediction
from models.risk import RiskAssessment
from models.trade import Trade, TradeAction

log = structlog.get_logger()


def _make_kalshi_executor():
    from kalshi.client import KalshiClient
    from kalshi.executor import KalshiExecutor

    base_url = (
        "https://demo-api.kalshi.co/trade-api/v2"
        if settings.kalshi_demo
        else "https://trading-api.kalshi.com/trade-api/v2"
    )
    client = KalshiClient(
        base_url=base_url,
        key_id=get_setting("kalshi_api_key_id"),
        private_key_path=get_kalshi_private_key_path(),
    )
    return KalshiExecutor(client)


class CompoundStep:
    def __init__(self):
        self._trade_repo = TradeRepository()
        self._market_repo = MarketRepository()
        self._calibration = CalibrationTracker()
        self._post_mortem = PostMortem()
        self._kalshi_executor = (
            _make_kalshi_executor()
            if get_bool_setting("kalshi_enabled") and get_bool_setting("kalshi_execute_trades")
            else None
        )

    def record_trade(
        self,
        market: Market,
        ensemble: EnsemblePrediction,
        assessment: RiskAssessment,
    ) -> Trade:
        """Create and persist a trade based on the risk assessment."""
        p_model = ensemble.final_probability

        # Decide direction: if p_model > market_price, bet YES; else bet NO
        if p_model > market.market_price:
            action = TradeAction.BUY_YES
        else:
            action = TradeAction.BUY_NO

        # Execute on Kalshi if enabled (market.id == Kalshi ticker when using real markets)
        kalshi_order_id = None
        if self._kalshi_executor and market.metadata.get("source") == "kalshi":
            order = self._kalshi_executor.place_order(
                ticker=market.metadata["ticker"],
                action=action,
                position_size_dollars=assessment.kelly.recommended_size,
                entry_price=market.market_price,
            )
            if order:
                kalshi_order_id = order.get("order_id")
                log.info("kalshi_order_submitted", order_id=kalshi_order_id, market_id=market.id)
            else:
                log.warning("kalshi_order_rejected_skipping", market_id=market.id)
                return self.record_skip(market, assessment)

        trade = Trade(
            market_id=market.id,
            action=action,
            entry_price=market.market_price,
            position_size=assessment.kelly.recommended_size,
            predicted_probability=p_model,
            edge=assessment.kelly.edge,
            kelly_fraction=assessment.kelly.quarter_kelly,
        )
        self._trade_repo.save(trade)
        log.info(
            "trade_recorded",
            trade_id=trade.id,
            market_id=market.id,
            action=action.value,
            size=trade.position_size,
            edge=trade.edge,
        )
        return trade

    def record_skip(self, market: Market, assessment: RiskAssessment) -> Trade:
        """Record a skipped trade for auditability."""
        trade = Trade(
            market_id=market.id,
            action=TradeAction.SKIP,
            entry_price=market.market_price,
            position_size=0.0,
            predicted_probability=0.0,
            edge=assessment.kelly.edge,
            kelly_fraction=0.0,
            resolved=True,
            pnl=0.0,
        )
        self._trade_repo.save(trade)
        return trade

    def process_resolved_markets(self, portfolio: Portfolio) -> Portfolio:
        """Find markets that expired, resolve them, update portfolio."""
        from market_sim.resolver import MarketResolver
        from db.repositories import ResearchCacheRepository

        resolver = MarketResolver()
        expired = self._market_repo.find_expired_unresolved()

        for market in expired:
            # Get accumulated sentiment from cache to influence resolution
            cache_repo = ResearchCacheRepository()
            cached = cache_repo.find_by_market(market.id)
            sentiment = cached.sentiment_score if cached else 0.0

            resolved_market = resolver.resolve(market, sentiment)
            self._market_repo.save(resolved_market)
            log.info(
                "market_resolved",
                market_id=market.id,
                outcome=resolved_market.outcome,
                question=market.question[:60],
            )

            # Resolve all open trades for this market
            open_trades = [t for t in self._trade_repo.find_by_market(market.id) if not t.resolved]
            for trade in open_trades:
                resolved_trade = trade.resolve(resolved_market.outcome)
                self._trade_repo.save(resolved_trade)
                portfolio = portfolio.apply_trade_result(resolved_trade.pnl, market.id)

                # Record calibration
                self._calibration.record(
                    trade.predicted_probability,
                    resolved_market.outcome,
                    trade.id,
                )

                # Post-mortem analysis
                try:
                    lesson = self._post_mortem.analyze(resolved_trade, resolved_market)
                    log.info("post_mortem_complete", trade_id=trade.id, lesson=lesson[:80])
                except Exception as e:
                    log.warning("post_mortem_failed", trade_id=trade.id, error=str(e))

                log.info(
                    "trade_resolved",
                    trade_id=trade.id,
                    pnl=resolved_trade.pnl,
                    bankroll=portfolio.bankroll,
                )

        return portfolio

    def snapshot(self, portfolio: Portfolio) -> PortfolioSnapshot:
        return PortfolioSnapshot(
            bankroll=portfolio.bankroll,
            open_position_count=len(portfolio.open_positions),
            total_trades=portfolio.total_trades,
            win_rate=portfolio.win_rate,
            total_pnl=portfolio.total_pnl,
            current_drawdown=portfolio.current_drawdown,
        )
