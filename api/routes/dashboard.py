from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pathlib import Path
from fastapi.templating import Jinja2Templates

from db.repositories import PortfolioRepository, TradeRepository, MarketRepository
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

    latest = history[-1] if history else None

    equity_labels = [s.timestamp.strftime("%m/%d %H:%M") for s in history]
    equity_values = [round(s.bankroll, 2) for s in history]

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
        },
    )
