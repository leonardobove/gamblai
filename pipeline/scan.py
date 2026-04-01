import structlog

from config import settings
from db.repositories import MarketRepository
from market_sim.generator import MarketGenerator
from models.market import Market

log = structlog.get_logger()


def _make_kalshi_scanner():
    from kalshi.client import KalshiClient
    from kalshi.scanner import KalshiScanner

    base_url = (
        "https://demo-api.kalshi.co/trade-api/v2"
        if settings.kalshi_demo
        else "https://trading-api.kalshi.com/trade-api/v2"
    )
    client = KalshiClient(
        base_url=base_url,
        key_id=settings.kalshi_api_key_id,
        private_key_path=settings.kalshi_private_key_path,
    )
    return KalshiScanner(client)


class ScanStep:
    def __init__(self):
        self._repo = MarketRepository()
        self._generator = MarketGenerator()
        self._kalshi = _make_kalshi_scanner() if settings.kalshi_enabled else None

    def run(self) -> list[Market]:
        """Fetch/generate new markets and load existing unresolved ones."""
        if self._kalshi:
            new_markets = self._kalshi.scan()
            source = "kalshi"
        else:
            new_markets = self._generator.generate(count=settings.markets_per_cycle)
            source = "sim"

        for m in new_markets:
            self._repo.save(m)
            log.info("market_scanned", source=source, market_id=m.id, question=m.question[:60])

        existing = self._repo.find_unresolved()
        seen_ids = {m.id for m in new_markets}
        existing_unseen = [m for m in existing if m.id not in seen_ids]

        all_markets = new_markets + existing_unseen
        log.info(
            "scan_complete",
            source=source,
            new=len(new_markets),
            existing=len(existing_unseen),
            total=len(all_markets),
        )
        return all_markets
