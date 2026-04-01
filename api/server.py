from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from api.routes.dashboard import router as dashboard_router
from api.routes.markets import router as markets_router
from api.routes.trades import router as trades_router
from api.routes.portfolio import router as portfolio_router

app = FastAPI(title="GamblAI", description="AI Prediction Market Trading Simulator")

_base = Path(__file__).parent
templates = Jinja2Templates(directory=str(_base / "templates"))
app.mount("/static", StaticFiles(directory=str(_base / "static")), name="static")

app.include_router(dashboard_router)
app.include_router(markets_router, prefix="/api/markets")
app.include_router(trades_router, prefix="/api/trades")
app.include_router(portfolio_router, prefix="/api/portfolio")
