from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pathlib import Path
from fastapi.templating import Jinja2Templates

from api.auth import is_setup_complete
from config import settings
from db.repositories import PortfolioRepository, TradeRepository, MarketRepository, PipelineRunRepository
from knowledge.calibration import CalibrationTracker

router = APIRouter()
_templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    portfolio_repo = PortfolioRepository()
    trade_repo = TradeRepository()
    market_repo = MarketRepository()
    calibration = CalibrationTracker()

    history = portfolio_repo.get_history(limit=200)
    recent_trades = trade_repo.find_resolved(limit=20)
    active_markets = market_repo.find_unresolved()
    brier_score = calibration.brier_score()
    cal_curve = calibration.calibration_curve()

    pipeline_runs = PipelineRunRepository().get_recent(limit=10)
    latest = history[-1] if history else None

    equity_labels = [s.timestamp.strftime("%m/%d %H:%M") for s in history]
    equity_values = [round(s.bankroll, 2) for s in history]

    # Compute unrealized P&L on open positions using current market price as mark-to-market
    open_trades = trade_repo.find_open()
    unrealized_pnl = 0.0
    for trade in open_trades:
        market = market_repo.find_by_id(trade.market_id)
        if market and trade.position_size > 0:
            # Mark-to-market: difference between current price and entry price
            price_delta = market.market_price - trade.entry_price
            # BUY_YES profits when price rises; BUY_NO profits when price falls
            from models.trade import TradeAction
            direction = 1 if trade.action == TradeAction.BUY_YES else -1
            unrealized_pnl += direction * price_delta * trade.position_size

    current_bankroll = latest.bankroll if latest else settings.starting_bankroll
    total_equity = round(current_bankroll + unrealized_pnl, 2)

    return _templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "latest": latest,
            "equity_labels": equity_labels,
            "equity_values": equity_values,
            "recent_trades": recent_trades,
            "active_markets": active_markets,
            "brier_score": brier_score,
            "cal_curve": cal_curve,
            "open_trades": open_trades,
            "unrealized_pnl": round(unrealized_pnl, 2),
            "total_equity": total_equity,
            "fast_simulation": settings.fast_simulation,
            "pipeline_runs": pipeline_runs,
            "needs_setup": not is_setup_complete(),
        },
    )
