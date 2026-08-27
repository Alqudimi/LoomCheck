# Contributing to LoomCheck

Thank you for helping make deterministic async testing more useful. LoomCheck is intentionally small: contributions should preserve a clear runtime contract and keep the boundary between scheduling, exploration, and reporting visible.

## Local setup

Use Python 3.10 or newer and install the optional development dependencies:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

Run the complete local quality gate before opening a pull request:

```bash
PYTHONPATH=src pytest --cov=loomcheck --cov-report=term-missing
PYTHONPATH=src ruff check src tests examples
PYTHONPATH=src mypy src
python scripts/benchmark.py
```

## Pull requests

Please describe the user-visible behavior, the design trade-off, and the failure mode or regression being addressed. Keep commits focused and use Conventional Commit-style subjects such as `feat: add schedule corpus export` or `fix: preserve timeout fingerprint`. Avoid unrelated formatting churn.

Behavior changes require a regression test. Public API changes require README or documentation updates. New dependencies need a concrete justification, an ownership/maintenance assessment, and a security review. Do not add telemetry, network access, secret material, or executable serialized state to the core runtime.

## Design principles

The runtime must remain deterministic for a given scenario and schedule. The explorer must remain bounded by explicit budgets. Reports must be stable and useful without a hosted service. Limitations must be documented rather than hidden behind broad claims.

## Reporting issues

Open a GitHub issue with the LoomCheck version, Python version, operating system, exact command, a minimal scenario, the report output, and whether the issue reproduces with a schedule replay. Do not include credentials or confidential report payloads.

## Code of conduct

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Security-sensitive issues should follow [SECURITY.md](SECURITY.md) instead of a public issue.
