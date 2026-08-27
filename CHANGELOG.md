# Changelog

All notable changes to LoomCheck are documented here.

## [0.1.0] - 2026-08-27

### Added

- Deterministic cooperative `asyncio` runtime with named tasks and explicit checkpoints.
- Bounded schedule exploration using observed runnable task sets.
- Greedy failure-witness shrinking with stable failure fingerprints.
- JSON and Markdown report writers.
- CLI commands for `run`, `explore`, and the intentionally racy `demo race` scenario.
- Unit and integration tests for replay, failure capture, invalid input, budgets, and reports.
- Open Source governance, architecture documentation, and GitHub Actions quality workflow.
