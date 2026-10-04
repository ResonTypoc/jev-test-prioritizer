import pytest

from jev_test_prioritizer import analyzer
from jev_test_prioritizer.models import DecisionEvaluation, DimensionEvaluation, TestEvaluation


@pytest.fixture(autouse=True)
def no_live_api(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Tests must replace the Jev client; live calls are forbidden.")

    monkeypatch.setattr(analyzer, "TypeSafeClient", forbidden)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)


@pytest.fixture
def result():
    return TestEvaluation(
        behavioral_value=DimensionEvaluation(2.7, 0.91, {"0": 0.0, "1": 0.0, "2": 0.3, "3": 0.7}),
        regression_protection=DimensionEvaluation(3.0, 0.88, {"0": 0.0, "1": 0.0, "2": 0.0, "3": 1.0}),
        implementation_coupling=DimensionEvaluation(0.0, 0.86, {"0": 1.0, "1": 0.0, "2": 0.0, "3": 0.0}),
        specification_alignment=DimensionEvaluation(2.8, 0.9, {"0": 0.0, "1": 0.0, "2": 0.2, "3": 0.8}),
        decision=DecisionEvaluation("keep", 0.93, {"keep": 0.9, "review": 0.08, "remove": 0.02}),
    )
