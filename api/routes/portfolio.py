from fastapi import APIRouter
from db.repositories import PortfolioRepository
from knowledge.calibration import CalibrationTracker

router = APIRouter()


@router.get("/")
async def get_portfolio():
    repo = PortfolioRepository()
    history = repo.get_history(limit=1)
    if not history:
        return {"bankroll": 10000.0, "total_trades": 0, "win_rate": 0.0, "total_pnl": 0.0}
    snap = history[-1]
    return snap.model_dump()


@router.get("/history")
async def get_history(limit: int = 200):
    repo = PortfolioRepository()
    history = repo.get_history(limit=limit)
    return [s.model_dump() for s in history]


@router.get("/calibration")
async def get_calibration():
    tracker = CalibrationTracker()
    return {
        "brier_score": tracker.brier_score(),
        "calibration_curve": tracker.calibration_curve(),
    }
