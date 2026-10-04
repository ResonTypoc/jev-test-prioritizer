"""CLI input and output; evaluation lives in analyzer.py."""

import argparse
import json
from pathlib import Path
import sys
from collections.abc import Sequence

from .analyzer import EvaluationError, evaluate_test
from .models import TestEvaluation


def _read_input(path: Path, label: str) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ValueError(f"{label} file does not exist: {path}") from error
    except (OSError, UnicodeError) as error:
        raise ValueError(f"Cannot read {label.lower()} file as UTF-8: {path}") from error
    if not text.strip():
        raise ValueError(f"{label} input is empty: {path}")
    return text


def _human_output(result: TestEvaluation) -> str:
    rows = ["Test retention evaluation", ""]
    for label, dimension in (
        ("Behavioral value", result.behavioral_value),
        ("Regression protection", result.regression_protection),
        ("Implementation coupling", result.implementation_coupling),
    ):
        rows.append(f"{label:<24} {dimension.score:g} / 3 (confidence {dimension.confidence:.2f})")
    rows.extend([
        "",
        f"{'Decision':<24} {result.decision.value.upper()}",
        f"{'Confidence':<24} {result.decision.confidence:.2f}",
    ])
    return "\n".join(rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="jev-test-prioritizer",
        description="Evaluate whether a candidate test is worth retaining as source code.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    evaluate = subcommands.add_parser("evaluate", help="Evaluate one candidate test")
    evaluate.add_argument("--source", type=Path, required=True, help="Production source file (UTF-8)")
    evaluate.add_argument("--test", type=Path, required=True, help="Candidate test file (UTF-8)")
    evaluate.add_argument("--context", help="Intended behavior, requirement, bug, or task as text")
    evaluate.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)
    try:
        source = _read_input(args.source, "Source")
        test = _read_input(args.test, "Test")
        result = evaluate_test(source, test, args.context)
    except (ValueError, EvaluationError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, allow_nan=False))
    else:
        print(_human_output(result))
    return 0
