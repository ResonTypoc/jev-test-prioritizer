import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from jev_test_prioritizer import cli
from jev_test_prioritizer.analyzer import EvaluationError


@pytest.fixture
def inputs(tmp_path):
    source = tmp_path / "source.txt"
    test = tmp_path / "test.txt"
    source.write_text("production code", encoding="utf-8")
    test.write_text("candidate test", encoding="utf-8")
    return source, test


def args(inputs):
    return ["evaluate", "--source", str(inputs[0]), "--test", str(inputs[1])]


def test_json_output(monkeypatch, capsys, inputs, result):
    received = []

    def evaluate(source, test, context):
        received.append((source, test, context))
        return result

    monkeypatch.setattr(cli, "evaluate_test", evaluate)
    assert cli.main(args(inputs) + ["--json", "--context", "intended behavior"]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out) == result.to_dict()
    assert json.loads(output.out)["specification_alignment"]["score"] == 2.8
    assert output.err == ""
    assert received == [("production code", "candidate test", "intended behavior")]


def test_human_output(monkeypatch, capsys, inputs, result):
    monkeypatch.setattr(cli, "evaluate_test", lambda *args: result)
    assert cli.main(args(inputs)) == 0
    output = capsys.readouterr()
    assert output.out == (
        "Test retention evaluation\n\n"
        "Behavioral value         2.7 / 3 (confidence 0.91)\n"
        "Regression protection    3 / 3 (confidence 0.88)\n"
        "Implementation coupling  0 / 3 (confidence 0.86)\n"
        "Specification alignment  2.8 / 3 (confidence 0.90)\n\n"
        "Decision                 KEEP\n"
        "Confidence               0.93\n"
    )
    assert output.err == ""


@pytest.mark.parametrize("json_mode", [False, True])
@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize("fault,message", [
    ("missing", "does not exist"), ("empty", "input is empty"),
    ("directory", "Cannot read"), ("encoding", "Cannot read"),
])
def test_input_failures(capsys, inputs, index, fault, message, json_mode):
    if fault == "missing":
        inputs[index].unlink()
    elif fault == "empty":
        inputs[index].write_text("  \n\t", encoding="utf-8")
    elif fault == "directory":
        inputs[index].unlink()
        inputs[index].mkdir()
    else:
        inputs[index].write_bytes(b"\xff")
    assert cli.main(args(inputs) + (["--json"] if json_mode else [])) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert message in output.err


def test_permission_failure(monkeypatch, capsys, inputs):
    def denied(*args, **kwargs):
        raise PermissionError("unreadable")

    monkeypatch.setattr(Path, "read_text", denied)
    assert cli.main(args(inputs)) == 1
    assert "Cannot read" in capsys.readouterr().err


def test_missing_api_key(capsys, inputs):
    assert cli.main(args(inputs) + ["--json"]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "TYPESAFE_API_KEY" in output.err


def test_analyzer_failure(monkeypatch, capsys, inputs):
    def fail(*args):
        raise EvaluationError("Jev evaluation failed.")

    monkeypatch.setattr(cli, "evaluate_test", fail)
    assert cli.main(args(inputs) + ["--json"]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "Error: Jev evaluation failed.\n"


@pytest.mark.parametrize("arguments", [[], ["evaluate"], ["unknown"]])
def test_argument_errors(capsys, arguments):
    with pytest.raises(SystemExit) as caught:
        cli.main(arguments)
    assert caught.value.code == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "error:" in output.err


@pytest.mark.parametrize("arguments", [["--help"], ["evaluate", "--help"]])
def test_help(capsys, arguments):
    with pytest.raises(SystemExit) as caught:
        cli.main(arguments)
    assert caught.value.code == 0
    output = capsys.readouterr()
    assert "evaluate" in output.out
    assert output.err == ""


@pytest.mark.parametrize("decision", ["keep", "review", "remove"])
def test_decisions_are_successful(monkeypatch, capsys, inputs, result, decision):
    from dataclasses import replace

    result = replace(result, decision=replace(result.decision, value=decision))
    monkeypatch.setattr(cli, "evaluate_test", lambda *args: result)
    assert cli.main(args(inputs) + ["--json"]) == 0
    assert json.loads(capsys.readouterr().out)["decision"]["value"] == decision


@pytest.mark.parametrize("json_mode", [False, True])
def test_installed_console_script_with_mock(inputs, result, json_mode):
    # Run the installed entry point in a fresh process with a deterministic fake.
    script = Path(sys.executable).parent / "jev-test-prioritizer"
    code = """
import json, runpy, sys
from jev_test_prioritizer import cli
from jev_test_prioritizer.models import DecisionEvaluation, DimensionEvaluation, TestEvaluation
data = json.loads(sys.argv.pop(1))
result = TestEvaluation(**{
    key: DecisionEvaluation(**value) if key == 'decision' else DimensionEvaluation(**value)
    for key, value in data.items()
})
cli.evaluate_test = lambda *args: result
entry = sys.argv.pop(1)
sys.argv[0] = entry
runpy.run_path(entry, run_name='__main__')
"""
    completed = subprocess.run(
        [sys.executable, "-c", code, json.dumps(result.to_dict()), str(script),
         *args(inputs), *(["--json"] if json_mode else [])],
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0
    assert completed.stderr == ""
    if json_mode:
        assert json.loads(completed.stdout) == result.to_dict()
    else:
        assert completed.stdout == cli._human_output(result) + "\n"


@pytest.mark.parametrize("fault,exit_code,message", [
    ("file", 1, "does not exist"),
    ("key", 1, "TYPESAFE_API_KEY"),
    ("arguments", 2, "error:"),
])
def test_installed_console_errors(inputs, fault, exit_code, message):
    script = Path(sys.executable).parent / "jev-test-prioritizer"
    environment = os.environ.copy()
    environment.pop("TYPESAFE_API_KEY", None)
    if fault == "file":
        inputs[0].unlink()
    arguments = [] if fault == "arguments" else args(inputs) + ["--json"]
    completed = subprocess.run(
        [str(script), *arguments], env=environment,
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == exit_code
    assert completed.stdout == ""
    assert message in completed.stderr
