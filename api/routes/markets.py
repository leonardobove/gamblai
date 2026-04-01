from fastapi import APIRouter
from db.repositories import MarketRepository

router = APIRouter()


@router.get("/")
async def list_markets(resolved: bool | None = None):
    repo = MarketRepository()
    if resolved is False or resolved is None:
        markets = repo.find_unresolved()
    else:
        # Return all from DB — simplified for now
        markets = repo.find_unresolved()
    return [m.model_dump() for m in markets]


@router.get("/{market_id}")
async def get_market(market_id: str):
    repo = MarketRepository()
    m = repo.find_by_id(market_id)
    if not m:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Market not found")
    return m.model_dump()
