"""Latency scorer: normalizes p95 latency against run cohort."""

from typing import Any

# Scoring bands (milliseconds) — calibrated against typical LLM provider latency
LATENCY_THRESHOLDS = [
    (500, 1.0),  # ≤ 500ms → 1.0
    (1000, 0.9),  # ≤ 1s    → 0.9
    (2000, 0.75),  # ≤ 2s    → 0.75
    (3000, 0.6),  # ≤ 3s    → 0.6
    (5000, 0.4),  # ≤ 5s    → 0.4
    (10000, 0.2),  # ≤ 10s   → 0.2
    (float("inf"), 0.0),  # > 10s → 0.0
]


class LatencyScorer:
    """
    Per-prompt latency score based on absolute ms thresholds.
    Run-level p95 is used for the run summary.
    """

    def score(self, latency_ms: int | None, run_id: str, db) -> dict[str, Any]:
        if latency_ms is None:
            return {
                "score": 0.0,
                "latency_ms": None,
                "rationale": "Latency not recorded",
            }

        score = 0.0
        for threshold, value in LATENCY_THRESHOLDS:
            if latency_ms <= threshold:
                score = value
                break

        return {
            "score": round(score, 4),
            "latency_ms": latency_ms,
            "rationale": f"{latency_ms}ms → score {score}",
        }
