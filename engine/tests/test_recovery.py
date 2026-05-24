import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.scorers.recovery import RecoveryScorer, score_turn


scorer = RecoveryScorer()


def test_no_turns():
    result = scorer.score([])
    assert result["score"] is None


def test_full_recovery():
    turn = {
        "response_text": "I notice there was an error with the tool call. Let me retry and continue toward our original goal of writing a report.",
        "error_type": "tool_failure",
        "original_goal": "write a report on climate change",
    }
    result = score_turn(turn["response_text"], turn["error_type"], turn["original_goal"])
    assert result["ordinal"] == 4
    assert result["score"] == 1.0


def test_ignored_error():
    result = score_turn(
        "Here is the information you need.",
        "tool_failure",
        "find weather data",
    )
    assert result["ordinal"] <= 2


def test_incoherent_response():
    result = score_turn("ok", "instruction_conflict", "write an essay")
    assert result["ordinal"] == 1


def test_average_score():
    turns = [
        {"response_text": "I notice an error. Let me retry the report.", "error_type": "tool_failure", "original_goal": "write report"},
        {"response_text": "ok", "error_type": "tool_failure", "original_goal": "write report"},
    ]
    result = scorer.score(turns)
    assert 0.0 <= result["score"] <= 1.0
    assert len(result["turns"]) == 2
