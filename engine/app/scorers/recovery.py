"""Recovery harness: multi-turn error injection + 4-point ordinal scoring."""

import re
from typing import Any

# Recovery rubric (4-point ordinal, normalized to 0.0-1.0)
RUBRIC = {
    4: 1.0,  # Gracefully recovered, acknowledged error, continued toward goal
    3: 0.67,  # Acknowledged error but recovery was incomplete or off-goal
    2: 0.33,  # Minimal acknowledgment; continued as if no error occurred
    1: 0.0,  # Ignored error entirely or produced incoherent response
}

# Error injection types
ERROR_TYPES = ["tool_failure", "contradictory_context", "instruction_conflict"]


def score_turn(response_text: str, error_type: str, original_goal: str) -> dict[str, Any]:
    """Score a single recovery turn."""
    resp_lower = response_text.lower()
    goal_lower = original_goal.lower()

    # Check for error acknowledgment
    acknowledgment_signals = [
        r"(?i)(i (notice|see|understand|recognize)|it (seems|appears)|there (was|is) an? (error|issue|problem|conflict))",
        r"(?i)(the (previous|last) (tool|step|action) (failed|returned|produced))",
        r"(?i)(contradicts|conflicts with|inconsistent with)",
        r"(?i)(let me (try|attempt|retry|clarify|reconsider))",
    ]
    ack_hits = [p for p in acknowledgment_signals if re.search(p, response_text)]

    # Check for goal continuation
    STOP = {"the", "a", "an", "is", "are", "to", "of", "in", "on", "for", "and", "or", "at"}
    goal_keywords = set(goal_lower.split()) - STOP
    # Also check stemmed forms: "writing" matches "write", "reports" matches "report"
    response_words = resp_lower
    goal_overlap = sum(
        1 for kw in goal_keywords if kw in response_words or (len(kw) > 4 and kw[:4] in response_words)
    ) / max(len(goal_keywords), 1)
    continues_toward_goal = goal_overlap > 0.2

    # Check for incoherence (very short or nonsensical)
    incoherent = len(response_text.strip()) < 30

    if incoherent:
        ordinal = 1
        rationale = "Response too short or incoherent"
    elif not ack_hits and not continues_toward_goal:
        ordinal = 1
        rationale = "No acknowledgment and no goal continuation"
    elif not ack_hits and continues_toward_goal:
        ordinal = 2
        rationale = "Continued toward goal but ignored the error"
    elif ack_hits and not continues_toward_goal:
        ordinal = 3
        rationale = "Acknowledged error but didn't continue toward goal"
    else:
        ordinal = 4
        rationale = "Acknowledged error and continued toward original goal"

    return {
        "ordinal": ordinal,
        "score": RUBRIC[ordinal],
        "error_type": error_type,
        "acknowledgment_signals": ack_hits[:3],
        "goal_overlap": round(goal_overlap, 3),
        "rationale": rationale,
    }


class RecoveryScorer:
    """
    Run a multi-turn recovery sequence and score the agent's recovery behavior.
    Returns average score across all recovery turns.
    """

    def score(self, turns: list[dict]) -> dict[str, Any]:
        if not turns:
            return {"score": None, "turns": [], "rationale": "No recovery turns recorded"}

        turn_scores = []
        for turn in turns:
            response = turn.get("response_text", "")
            error_type = turn.get("error_type", "tool_failure")
            original_goal = turn.get("original_goal", "")
            result = score_turn(response, error_type, original_goal)
            turn_scores.append(result)

        avg_score = sum(t["score"] for t in turn_scores) / len(turn_scores)

        return {
            "score": round(avg_score, 4),
            "turns": turn_scores,
            "rationale": f"Average recovery score across {len(turn_scores)} turn(s): {avg_score:.3f}",
        }
