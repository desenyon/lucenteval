"""Cost scorer: normalizes USD cost per prompt against absolute scale."""
from typing import Any


# Score bands based on cost per prompt in USD
COST_THRESHOLDS = [
    (0.0001, 1.0),    # ≤ $0.0001 → 1.0
    (0.001, 0.9),     # ≤ $0.001  → 0.9
    (0.005, 0.75),    # ≤ $0.005  → 0.75
    (0.01, 0.6),      # ≤ $0.01   → 0.6
    (0.05, 0.4),      # ≤ $0.05   → 0.4
    (0.10, 0.2),      # ≤ $0.10   → 0.2
    (float("inf"), 0.0),  # > $0.10 → 0.0
]


class CostScorer:
    """
    Per-prompt cost score normalized against absolute USD thresholds.
    """

    def score(self, cost_usd: float | None, run_id: str, db) -> dict[str, Any]:
        if cost_usd is None:
            return {
                "score": 0.5,
                "cost_usd": None,
                "rationale": "Cost not recorded; neutral score",
            }

        score = 0.0
        for threshold, value in COST_THRESHOLDS:
            if cost_usd <= threshold:
                score = value
                break

        return {
            "score": round(score, 4),
            "cost_usd": cost_usd,
            "rationale": f"${cost_usd:.8f} per prompt → score {score}",
        }
