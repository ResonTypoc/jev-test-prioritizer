# jev-test-prioritizer

An experimental CLI that uses Jev to evaluate whether an AI-generated candidate
test is worth **retaining as maintained source code**. It returns an advisory
`keep`, `review`, or `remove` recommendation.

Despite the project name, it does **not prioritize test execution** or decide which
tests should run for a change. It never executes tests, deletes files, or modifies
source code.

A typical coding-agent workflow is to implement production behavior, generate a
test, evaluate that test with this tool, then use the recommendation as an
additional review signal before committing. Humans can use the same workflow.

The implementation is language-, framework-, and test-runner-agnostic. Ruby/Rails,
JavaScript/TypeScript, Python, Go, Java, and other code are supplied as text; there
is no language-specific parsing or runner integration.

## Installation and configuration

Requires Python 3.10 or newer. From this repository:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
export TYPESAFE_API_KEY="your-api-key"
```

Use a key from TypeSafe. `.env.example` lists the expected variable; the CLI reads
the process environment and does not load `.env` files. Never commit credentials.

The only direct runtime dependency is the official
[TypeSafe Python SDK](https://github.com/typesafe-ai/typesafe-sdk-python).
The integration was checked against `typesafe-sdk` 0.7.2 and uses
`TypeSafeClient.system_one` with four `Score` questions and one `Choice` question.
The SDK's default model is `jev-latest`; its standard environment configuration
also applies. See the [official SDK documentation](https://docs.typesafe.ai/sdk/python).

**Supplied production source, candidate test, and context are sent to the Jev
service.** Consider that when choosing inputs.

## CLI usage

Evaluate one candidate test at a time using explicit UTF-8 file paths:

```sh
jev-test-prioritizer evaluate \
  --source examples/payment_service.rb \
  --test examples/payment_service_test.rb \
  --context "Invalid payments must be rejected before reaching the payment gateway."
```

`--source` and `--test` are required; `--context` is optional text describing the
intended behavior, requirement, bug, invariant, or implementation task. The tool
does not inspect the repository or discover related files.

Default output displays the four scores, their confidence, and the decision:

```text
Test retention evaluation

Behavioral value         2.7 / 3 (confidence 0.91)
Regression protection    3 / 3 (confidence 0.88)
Implementation coupling  0 / 3 (confidence 0.86)
Specification alignment  2.8 / 3 (confidence 0.90)

Decision                 KEEP
Confidence               0.93
```

This is illustrative output, not a recorded live evaluation. Use
`jev-test-prioritizer --help` or `jev-test-prioritizer evaluate --help` for help.

## Coding-agent JSON interface

```sh
jev-test-prioritizer evaluate \
  --source app/services/payment_service.rb \
  --test test/services/payment_service_test.rb \
  --context "This test was generated while implementing payment retry behavior." \
  --json
```

On success, stdout contains only a JSON object with these stable project-owned
fields (illustrative values):

```json
{
  "behavioral_value": {
    "score": 2.7,
    "confidence": 0.91,
    "probabilities": {"0": 0.0, "1": 0.0, "2": 0.3, "3": 0.7}
  },
  "regression_protection": {
    "score": 3.0,
    "confidence": 0.88,
    "probabilities": {"0": 0.0, "1": 0.0, "2": 0.0, "3": 1.0}
  },
  "implementation_coupling": {
    "score": 0.0,
    "confidence": 0.86,
    "probabilities": {"0": 1.0, "1": 0.0, "2": 0.0, "3": 0.0}
  },
  "specification_alignment": {
    "score": 2.8,
    "confidence": 0.9,
    "probabilities": {"0": 0.0, "1": 0.0, "2": 0.2, "3": 0.8}
  },
  "decision": {
    "value": "keep",
    "confidence": 0.93,
    "probabilities": {"keep": 0.9, "review": 0.08, "remove": 0.02}
  }
}
```

The four dimension fields are `behavioral_value`, `regression_protection`,
`implementation_coupling`, and `specification_alignment`. Each has a numeric
`score` in `[0, 3]`, a numeric `confidence` in `[0, 1]`,
and a `probabilities` object with exactly the string keys `"0"` through `"3"`.
The decision has a `value` of `keep`, `review`, or `remove`, its SDK `confidence`,
and probabilities for all three alternatives. Probability values are in `[0, 1]`
and the service documents their sum as approximately one.

SDK scores are **expected scores**, the probability-weighted average of the four
ordered rubric levels, and can be fractional. They are preserved without rounding
in JSON. SDK confidence is copied as provided, not calculated from the largest
probability and not treated as proof of correctness. No confidence is fabricated.
The human display rounds confidence to two decimal places for readability.

Exit status `0` means evaluation succeeded, including a `review` or `remove`
decision. Exit status `1` means input, configuration, or evaluation failure;
`2` means invalid CLI arguments. Errors go to stderr, with no result on stdout.
Missing or unreadable files, invalid UTF-8, whitespace-only source/test inputs,
missing `TYPESAFE_API_KEY`, and unrecoverable Jev errors fail clearly. Service
error bodies are not printed, to avoid exposing supplied code or credentials.

## Interpretation

| Dimension | 0 | 1 | 2 | 3 |
| --- | --- | --- | --- | --- |
| Behavioral value | Trivial or none | Weak | Meaningful | Important behavioral contract |
| Regression protection | Almost none | Limited | Useful | Strong |
| Implementation coupling (higher is worse) | Behavior-focused | Mild | Substantial | Primarily implementation details |
| Specification alignment | Contradicts stated intended behavior | Weakly, ambiguously, or questionably aligned | Substantially aligned with intended behavior | Clearly validates intended behavior |

Behavioral value concerns observable behavior, business rules, contracts,
invariants, edge cases, and failure modes that callers or users depend on.
Assertion count alone does not establish value. Regression protection considers
whether plausible incorrect implementations could still pass. Implementation
coupling considers brittle assertions about private methods, internal call counts,
object structure, or incidental sequences. Mocking itself is not considered bad.

Specification alignment uses supplied context as the primary source of intended
requirements when available. Production source is not ground truth: an AI-generated
implementation and its generated test can agree while both violate the requirement.
Their agreement alone is insufficient evidence for `keep`. A test that encodes
behavior contrary to the stated requirement must not be retained merely because
the implementation currently behaves that way.

Without enough independent requirement information, Jev is instructed to use the
weakly or ambiguously aligned level, reduce confidence, and prefer `review` rather
than assume the implementation is correct. Missing specification context represents
uncertainty, not a known contradiction. Confidence and probabilities still come
directly from Jev; the application does not fabricate or adjust them.

- **keep:** enough durable behavioral or regression value to justify maintenance,
  supported by independently established intended behavior and not contrary to the
  stated requirement.
- **review:** ambiguous value, missing context, or a test that may warrant improvement.
- **remove:** little durable value relative to maintenance cost, trivial implementation
  details, or another reason it does not justify retention.

Jev is instructed to prefer `review` when important context is missing. The
decision comes from Jev rather than a locally invented score threshold.
Every recommendation is advisory: **it is not proof that deleting a test is safe**.
The tool never acts on a `remove` recommendation.

## Examples

The examples use Ruby/Minitest only for readability; the CLI does not depend on Ruby.

- `examples/payment_service.rb` and `examples/payment_service_test.rb` protect
  rejection of zero and negative charges before they reach a gateway. With the
  stated invalid-payment requirement, this should reasonably tend toward `keep`.
- `examples/formatter.rb` and `examples/formatter_test.rb` check a private helper
  with an already clean string, without verifying public greeting behavior or
  normalization. This should reasonably tend toward `review` or `remove`.

```sh
jev-test-prioritizer evaluate \
  --source examples/formatter.rb \
  --test examples/formatter_test.rb \
  --context "The requirement is a public greeting with surrounding whitespace removed." \
  --json
```

These are suggested outcomes, not guaranteed classifications or live benchmarks.

## Programmatic use

```python
from jev_test_prioritizer import evaluate_test

result = evaluate_test(source_code, test_code, context="Intended behavior")
print(result.decision.value)
print(result.to_dict())
```

The public result types are `TestEvaluation`, `DimensionEvaluation`, and
`DecisionEvaluation`, owned by this project. Empty inputs raise `ValueError`;
missing configuration raises `ConfigurationError`; service failures or invalid
results raise `EvaluationError`. The latter two are exported from the package,
and `ConfigurationError` is a subclass of `EvaluationError`. SDK responses remain
inside the analyzer; the SDK client constructor is replaceable for testing.

## Limitations and development

Only supplied source, one candidate test, and optional context are available.
There is no awareness of all other tests, repository-wide coverage, duplicate
detection, or mutation testing. Existing coverage or redundancy must not be
assumed unless explicitly supplied in context, and the tool cannot establish that
other tests cover a behavior after removal. It does not execute candidate code.
AI judgments can be wrong and may vary across model versions or calls.
Specification alignment depends on the supplied requirement information; missing
or ambiguous context limits confidence in the recommendation.

Install and run this CLI project's own tests:

```sh
python -m pip install -e '.[dev]'
python -m pytest
```

Tests use deterministic mocks, including the actual SDK with a mock HTTP transport,
and never call the real Jev API. They verify serialization, requests and response
conversion, CLI output, file/configuration errors, error propagation, and installed
console-script behavior. No lint or type checker is currently configured.

## License

MIT. See [LICENSE](LICENSE).
