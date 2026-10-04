import json

import pytest

from jev_test_prioritizer.models import DecisionEvaluation, DimensionEvaluation


def test_serialization(result):
    data = json.loads(json.dumps(result.to_dict(), allow_nan=False))
    assert set(data) == {
        "behavioral_value", "regression_protection", "implementation_coupling",
        "specification_alignment", "decision",
    }
    assert data["specification_alignment"] == {
        "score": 2.8, "confidence": 0.9,
        "probabilities": {"0": 0.0, "1": 0.0, "2": 0.2, "3": 0.8},
    }
    assert data["behavioral_value"] == {
        "score": 2.7, "confidence": 0.91,
        "probabilities": {"0": 0.0, "1": 0.0, "2": 0.3, "3": 0.7},
    }
    assert data["decision"] == {
        "value": "keep", "confidence": 0.93,
        "probabilities": {"keep": 0.9, "review": 0.08, "remove": 0.02},
    }
    data["decision"]["probabilities"]["keep"] = 0.0
    assert result.decision.probabilities["keep"] == 0.9


@pytest.mark.parametrize("score", [-1, 4, float("nan"), float("inf")])
def test_invalid_score(score):
    with pytest.raises(ValueError):
        DimensionEvaluation(score, 0.8, {"0": 1.0, "1": 0.0, "2": 0.0, "3": 0.0})


@pytest.mark.parametrize("confidence", [-0.1, 1.1, float("nan")])
def test_invalid_confidence(confidence):
    with pytest.raises(ValueError):
        DecisionEvaluation("review", confidence, {"keep": 0.0, "review": 1.0, "remove": 0.0})


def test_invalid_decision_and_distribution():
    with pytest.raises(ValueError):
        DecisionEvaluation("skip", 0.8, {"keep": 0.0, "review": 1.0, "remove": 0.0})
    with pytest.raises(ValueError):
        DimensionEvaluation(1, 0.8, {"0": 1.0})
    with pytest.raises(ValueError):
        DecisionEvaluation("keep", 0.8, {"keep": float("inf"), "review": 0.0, "remove": 0.0})
