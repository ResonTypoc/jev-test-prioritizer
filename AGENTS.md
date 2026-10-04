# Contributor instructions

- Keep this tool intentionally CLI-focused: evaluate test retention, not test execution prioritization.
- Remain language-, framework-, and test-runner-agnostic; treat supplied code as text.
- Keep dependencies minimal.
- Preserve the stable JSON interface for coding-agent integration.
- Keep Jev SDK details behind project-owned models.
- Never commit secrets or expose API credentials.
- Automated tests must not call the real Jev API; replace the SDK boundary.
- Run validation before completing changes: install locally, run the complete pytest suite,
  check both CLI help commands and mocked output/error behavior, and inspect the full diff.
  Run lint/type checks when configured.
