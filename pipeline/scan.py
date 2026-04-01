import structlog

from config import settings
from db.repositories import MarketRepository
from market_sim.generator import MarketGenerator
from models.market import Market

log = structlog.get_logger()


class ScanStep:
    def __init__(self):
        self._repo = MarketRepository()
        self._generator = MarketGenerator()

    def run(self) -> list[Market]:
        """Generate new markets and load existing unresolved ones."""
        new_markets = self._generator.generate(count=settings.markets_per_cycle)
        for m in new_markets:
            self._repo.save(m)
            log.info("market_generated", market_id=m.id, question=m.question[:60])

        existing = self._repo.find_unresolved()
        seen_ids = {m.id for m in new_markets}
        existing_new = [m for m in existing if m.id not in seen_ids]

        all_markets = new_markets + existing_new
        log.info("scan_complete", new=len(new_markets), existing=len(existing_new), total=len(all_markets))
        return all_markets
