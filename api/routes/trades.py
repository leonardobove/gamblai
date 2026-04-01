from fastapi import APIRouter
from db.repositories import TradeRepository

router = APIRouter()


@router.get("/")
async def list_trades(limit: int = 50):
    repo = TradeRepository()
    trades = repo.find_resolved(limit=limit)
    return [t.model_dump() for t in trades]


@router.get("/open")
async def list_open_trades():
    repo = TradeRepository()
    trades = repo.find_open()
    return [t.model_dump() for t in trades]
