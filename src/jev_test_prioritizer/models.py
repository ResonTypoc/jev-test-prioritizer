"""Application-owned results; no SDK response objects escape the analyzer."""

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Literal

RetentionDecision = Literal["keep", "review", "remove"]


def _probability(value: float) -> None:
    if not isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Confidence and probabilities must be finite values in [0, 1].")


def _distribution(probabilities: dict[str, float], keys: set[str]) -> None:
    if set(probabilities) != keys:
        raise ValueError("Unexpected probability labels.")
    for probability in probabilities.values():
        _probability(probability)


@dataclass(frozen=True)
class DimensionEvaluation:
    """SDK expected score on the 0–3 rubric, with unmodified uncertainty."""

    score: float
    confidence: float
    probabilities: dict[str, float]

    def __post_init__(self) -> None:
        if not isfinite(self.score) or not 0 <= self.score <= 3:
            raise ValueError("Score must be finite and in [0, 3].")
        _probability(self.confidence)
        _distribution(self.probabilities, {"0", "1", "2", "3"})


@dataclass(frozen=True)
class DecisionEvaluation:
    value: RetentionDecision
    confidence: float
    probabilities: dict[str, float]

    def __post_init__(self) -> None:
        if self.value not in {"keep", "review", "remove"}:
            raise ValueError("Unexpected retention decision.")
        _probability(self.confidence)
        _distribution(self.probabilities, {"keep", "review", "remove"})


@dataclass(frozen=True)
class TestEvaluation:
    behavioral_value: DimensionEvaluation
    regression_protection: DimensionEvaluation
    implementation_coupling: DimensionEvaluation
    specification_alignment: DimensionEvaluation
    decision: DecisionEvaluation

    def to_dict(self) -> dict:
        """Return a JSON-compatible copy using stable application field names."""
        return asdict(self)
