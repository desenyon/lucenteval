import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.scorers.composite import DEFAULT_WEIGHTS_V1, CompositeScorer

scorer = CompositeScorer()


def test_all_ones():
    result = scorer.score(
        {
            "adversarial": 1.0,
            "tool_misuse": 1.0,
            "hallucination": 1.0,
            "recovery": 1.0,
            "latency": 1.0,
            "cost": 1.0,
        }
    )
    assert result["score"] == 1.0


def test_all_zeros():
    result = scorer.score(
        {
            "adversarial": 0.0,
            "tool_misuse": 0.0,
            "hallucination": 0.0,
            "recovery": 0.0,
            "latency": 0.0,
            "cost": 0.0,
        }
    )
    assert result["score"] == 0.0


def test_none_excluded():
    result = scorer.score(
        {
            "adversarial": 1.0,
            "tool_misuse": None,
            "hallucination": None,
            "recovery": None,
            "latency": None,
            "cost": None,
        }
    )
    assert result["score"] == 1.0
    assert result["dimensions_used"] == ["adversarial"]


def test_all_none():
    result = scorer.score(
        {
            "adversarial": None,
            "tool_misuse": None,
        }
    )
    assert result["score"] is None


def test_weights_sum():
    total = sum(DEFAULT_WEIGHTS_V1.values())
    assert abs(total - 1.0) < 1e-9


def test_known_composite():
    # adversarial: 0.8 * 0.25 = 0.20
    # tool_misuse: 0.6 * 0.20 = 0.12
    # hallucination: 1.0 * 0.20 = 0.20
    # recovery: 0.4 * 0.15 = 0.06
    # latency: 0.9 * 0.10 = 0.09
    # cost: 0.7 * 0.10 = 0.07
    # sum = 0.74 / 1.0 = 0.74
    result = scorer.score(
        {
            "adversarial": 0.8,
            "tool_misuse": 0.6,
            "hallucination": 1.0,
            "recovery": 0.4,
            "latency": 0.9,
            "cost": 0.7,
        }
    )
    assert abs(result["score"] - 0.74) < 0.001


def test_custom_weights():
    custom_scorer = CompositeScorer({"adversarial": 1.0})
    result = custom_scorer.score({"adversarial": 0.5, "tool_misuse": 0.9})
    assert result["score"] == 0.5


def test_unknown_cost_is_excluded():
    from app.scorers.cost import CostScorer
    assert CostScorer().score(None, "unused", None)["score"] is None
