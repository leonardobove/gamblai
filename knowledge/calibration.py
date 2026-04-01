import math
from db.repositories import KnowledgeRepository


class CalibrationTracker:
    def __init__(self):
        self._repo = KnowledgeRepository()

    def record(self, predicted_prob: float, actual_outcome: bool, trade_id: str | None = None) -> None:
        self._repo.save_calibration(predicted_prob, actual_outcome, trade_id)

    def brier_score(self) -> float | None:
        data = self._repo.get_calibration_data()
        if len(data) < 5:
            return None
        total = sum((row["predicted_probability"] - row["actual_outcome"]) ** 2 for row in data)
        return round(total / len(data), 4)

    def calibration_curve(self) -> list[dict]:
        """Return binned calibration data for the dashboard chart."""
        data = self._repo.get_calibration_data()
        if len(data) < 10:
            return []

        bins: dict[int, list] = {i: [] for i in range(10)}
        for row in data:
            bucket = min(9, int(row["predicted_probability"] * 10))
            bins[bucket].append(row["actual_outcome"])

        result = []
        for i, outcomes in bins.items():
            if outcomes:
                midpoint = (i + 0.5) / 10
                actual_freq = sum(outcomes) / len(outcomes)
                result.append({
                    "predicted": round(midpoint, 2),
                    "actual": round(actual_freq, 3),
                    "count": len(outcomes),
                })
        return result
