import json

import httpx2
import pytest
from typesafe_sdk import RetryPolicy, TypeSafeClient, TypeSafeError

from jev_test_prioritizer import analyzer


def payload(result):
    answers = {}
    for name, value in result.to_dict().items():
        if name == "decision":
            answers[name] = {"type": "choice", "choice": value.pop("value"), **value}
        else:
            answers[name] = {
                "type": "score", **value,
                "legend": {str(i): f"Level {i}" for i in range(4)},
            }
    return {"model": "jev-test", "answers": answers, "usage": {"input_tokens": 100, "output_tokens": 0}}


def install_transport(monkeypatch, handler):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-placeholder")
    monkeypatch.setattr(
        analyzer, "TypeSafeClient",
        lambda **kwargs: TypeSafeClient(
            **kwargs, transport=httpx2.MockTransport(handler),
            base_url="https://example.invalid/v1", model="jev-latest",
            retry=RetryPolicy(max_retries=0),
        ),
    )


def test_real_sdk_with_mock_transport(monkeypatch, result):
    requests = []

    def handler(request):
        requests.append(request)
        body = json.loads(request.content)
        assert body["state"] == {"source_code": "source", "test_code": "test", "context": "requirement"}
        assert body["model"] == "jev-latest"
        questions = body["questions"]
        assert set(questions) == set(result.to_dict())
        assert all(len(questions[name]["criteria"]) == 4 for name in questions if name != "decision")
        assert set(questions["decision"]["criteria"]) == {"keep", "review", "remove"}
        assert "Higher is worse" in questions["implementation_coupling"]["instructions"]
        assert "assertion count" in questions["behavioral_value"]["instructions"]
        for question in questions.values():
            assert "Prefer review" in question["instructions"]
            assert "Do not assume repository-wide coverage" in question["instructions"]
        return httpx2.Response(200, json=payload(result))

    install_transport(monkeypatch, handler)
    actual = analyzer.evaluate_test("source", "test", "requirement")
    assert actual.to_dict() == result.to_dict()
    assert len(requests) == 1


@pytest.mark.parametrize("source,test,message", [(" \n", "test", "Source"), ("source", "\t", "Test")])
def test_empty_inputs(source, test, message):
    with pytest.raises(ValueError, match=message):
        analyzer.evaluate_test(source, test)


@pytest.mark.parametrize("key", [None, "", "  \n"])
def test_missing_configuration(monkeypatch, key):
    if key is not None:
        monkeypatch.setenv("TYPESAFE_API_KEY", key)
    with pytest.raises(analyzer.ConfigurationError, match="TYPESAFE_API_KEY"):
        analyzer.evaluate_test("source", "test")


def test_client_creation_error_propagates_safely(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-placeholder")
    cause = TypeSafeError("Sensitive service detail")

    def failing_client(**kwargs):
        raise cause

    monkeypatch.setattr(analyzer, "TypeSafeClient", failing_client)
    with pytest.raises(analyzer.EvaluationError) as caught:
        analyzer.evaluate_test("source", "test")
    assert caught.value.__cause__ is cause
    assert "Sensitive" not in str(caught.value)


def test_service_failure(monkeypatch):
    install_transport(monkeypatch, lambda request: httpx2.Response(401, json={"message": "private detail"}))
    with pytest.raises(analyzer.EvaluationError, match="TypeSafeAuthenticationError") as caught:
        analyzer.evaluate_test("source", "test")
    assert "private detail" not in str(caught.value)


def test_connection_failure(monkeypatch):
    def offline(request):
        raise httpx2.ConnectError("offline", request=request)

    install_transport(monkeypatch, offline)
    with pytest.raises(analyzer.EvaluationError, match="TypeSafeAPIConnectionError"):
        analyzer.evaluate_test("source", "test")


@pytest.mark.parametrize("fault", ["missing", "wrong_type", "score", "confidence", "decision", "probabilities", "invalid_json"])
def test_invalid_service_results(monkeypatch, result, fault):
    data = payload(result)
    if fault == "missing":
        del data["answers"]["behavioral_value"]
    elif fault == "wrong_type":
        data["answers"]["behavioral_value"] = {"type": "noul", "noul": 0.5}
    elif fault == "score":
        data["answers"]["behavioral_value"]["score"] = 4.0
    elif fault == "confidence":
        data["answers"]["decision"]["confidence"] = 2.0
    elif fault == "decision":
        data["answers"]["decision"]["choice"] = "skip"
    elif fault == "probabilities":
        data["answers"]["decision"]["probabilities"] = {"skip": 1.0}
    else:
        data = {"answers": "invalid"}
    install_transport(monkeypatch, lambda request: httpx2.Response(200, json=data))
    with pytest.raises(analyzer.EvaluationError):
        analyzer.evaluate_test("source", "test")
