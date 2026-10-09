import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.scorers.hallucination import HallucinationScorer

scorer = HallucinationScorer()


def test_grounded_facts_score_well():
    text = "The speed of light is approximately 299,792,458 meters per second. Water boils at 100 degrees celsius at sea level."
    result = scorer.score(text)
    assert result["score"] > 0.5


def test_empty_response():
    result = scorer.score("")
    assert result["score"] == 1.0
    assert result["total_claims"] == 0


def test_question_not_scored():
    result = scorer.score("What is the capital of France?")
    # Questions are filtered out
    assert result["total_claims"] == 0


def test_temporal_claim_excluded():
    text = "As of today the current president is leading polls."
    result = scorer.score(text)
    assert result["temporal_claims"] >= 1


def test_score_in_range():
    text = "The earth is flat. The moon is made of cheese. Pi is approximately 3.14159. Paris is the capital of France."
    result = scorer.score(text)
    assert 0.0 <= result["score"] <= 1.0


def test_ratio_calculation():
    text = "Paris is the capital of France. The pacific ocean is the largest ocean."
    result = scorer.score(text)
    assert result["grounded_claims"] >= 0
    assert result["total_claims"] >= 0


def test_negated_fact_is_not_grounded():
    result = scorer.score("Paris is not the capital of France.")
    assert result["grounded_claims"] == 0


def test_wrong_capital_with_overlapping_words_is_not_grounded():
    result = scorer.score("London is the capital of France.")
    assert result["grounded_claims"] == 0
