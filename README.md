# LoomCheck

[![CI](https://github.com/Alqudimi/LoomCheck/actions/workflows/ci.yml/badge.svg)](https://github.com/Alqudimi/LoomCheck/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-0f766e.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-f59e0b.svg)](CHANGELOG.md)

**Bounded deterministic schedule exploration for cooperative `asyncio` code.**

LoomCheck turns scheduler-dependent async failures into small, replayable witnesses. Add explicit checkpoints around meaningful state transitions, explore bounded task interleavings, and receive a JSON or Markdown report that can run locally or in GitHub Actions.

> LoomCheck is intentionally honest: it is a bounded cooperative scheduler for instrumented code. It does not claim to prove race freedom or preempt arbitrary Python bytecode.

## Why it exists

A normal async test observes one event-loop schedule. A rare order of task progress can therefore become a flaky test, an incident that cannot be reproduced, or a regression that nobody can encode. Existing async test runners execute coroutines; LoomCheck adds a deterministic control plane at user-selected boundaries so developers can search alternative interleavings and preserve the failing schedule.

## What makes it different

LoomCheck is a small library rather than a hosted observability platform. It is local-first, dependency-free at runtime, explicit about its instrumentation boundary, and focused on the shortest useful artifact: **the choices required to reproduce a failure**. The explorer uses only runnable task names observed during previous executions and applies a bounded search budget, making the result understandable in a code review.

## Features

| Capability | What you get |
|---|---|
| Deterministic checkpoints | `await loom.checkpoint("label")` pauses a task at a named boundary. |
| Named tasks | `loom.start_soon(awaitable, name="worker")` makes choices readable. |
| Bounded exploration | Explore alternative runnable tasks with `max_runs` and `max_steps`. |
| Replay | Pass a schedule such as `["alpha", "beta", "alpha"]`. |
| Failure witnesses | Stable fingerprint, task, message, traceback, decisions, and divergences. |
| Schedule shrinking | Greedily remove decisions while preserving the same failure fingerprint. |
| CI-friendly output | JSON and Markdown reports plus stable exit codes. |
| Zero runtime dependencies | Python standard library only. |

## Quick start

Requires Python 3.10 or newer.

```bash
git clone https://github.com/Alqudimi/LoomCheck.git
cd LoomCheck
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
loomcheck demo race --format markdown
```

The demo intentionally finds a lost update and exits with code `1`, because a failure was discovered. This is a successful demonstration of the tool, not a failed installation. To inspect machine-readable output:

```bash
loomcheck demo race --format json --output loomcheck-report.json
cat loomcheck-report.json
```

## Use it in your scenario

A scenario is a callable that accepts a `Loom` instance and returns an awaitable. Put checkpoints around state transitions where alternate task order matters.

```python
# examples/race_scenario.py
import asyncio
from loomcheck import Loom

async def lost_update(loom: Loom) -> None:
    state = {"value": 0}

    async def worker(name: str) -> None:
        await loom.checkpoint(f"{name}:read")
        current = state["value"]
        await loom.checkpoint(f"{name}:write")
        state["value"] = current + 1

    tasks = [loom.start_soon(worker(name), name=name)
             for name in ("alpha", "beta")]
    await asyncio.gather(*tasks)
    assert state["value"] == 2
```

Run one deterministic execution or explore alternatives:

```bash
PYTHONPATH=src python -m loomcheck.cli run examples.race_scenario:lost_update
PYTHONPATH=src python -m loomcheck.cli explore examples.race_scenario:lost_update \
  --max-runs 20 --max-steps 20 --format markdown
```

The CLI accepts `module:callable` targets and imports them from the current Python path. Reports are filesystem-only; no network or telemetry is used.

## Python API

```python
from loomcheck import explore, run

one_run = run(scenario, schedule=["alpha", "beta", "alpha", "beta"])
if one_run.failure:
    print(one_run.failure.fingerprint)

campaign = explore(scenario, max_runs=50, max_steps=100)
if campaign.minimized_failure:
    print(campaign.minimized_failure.schedule)
```

`run()` returns a `RunResult`. `explore()` returns an `ExplorationResult` whose `minimized_failure` is the smallest witness found by the current greedy shrinker. The schedule is a tuple of task names, so it is safe to serialize as JSON.

## Exit codes

| Code | Meaning |
|---:|---|
| `0` | Scenario completed without a captured failure. |
| `1` | A scenario failure, timeout, or step-budget failure was found. |
| `2` | Invalid CLI usage, target, or schedule input. |

## Architecture

```text
Scenario callable
      |
      v
Loom API -- checkpoint() --> Runtime coordinator
      |                           |
      v                           +--> runnable set
asyncio Tasks <-------------------+--> chosen decision
      |
      v
RunResult --> Explorer --> Shrinker --> JSON / Markdown
```

The runtime owns one event loop per run. At each checkpoint, the current task registers a request and waits. The coordinator chooses a task deterministically from the requested schedule or the sorted runnable set. The explorer records alternative choices as bounded prefixes and never invents an unobserved task. See [the architecture guide](docs/architecture.md) for failure flow, security boundaries, compatibility, and extension points.

## Performance and scope

The hot path is one in-memory coordination operation per explicit checkpoint. Exploration is bounded by `max_runs`, `max_steps`, and `timeout`; no service, database, or background worker is required. Place checkpoints at meaningful transitions rather than every line. Run the benchmark with:

```bash
python scripts/benchmark.py
```

The benchmark reports measurements from the current machine; LoomCheck does not publish unmeasured performance claims.

## Security model

LoomCheck has no network behavior and does not persist data by default. The CLI imports and executes a target selected by the user, so it is not a sandbox. Exception messages, labels, and schedules may contain sensitive values; treat generated reports accordingly. Schedule files are JSON and validated as strings. Read [SECURITY.md](SECURITY.md) before reporting a vulnerability.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
PYTHONPATH=src pytest
PYTHONPATH=src pytest --cov=loomcheck --cov-report=term-missing
PYTHONPATH=src ruff check src tests examples
PYTHONPATH=src mypy src
python scripts/benchmark.py
```

The project keeps runtime dependencies at zero and development dependencies optional. Tests cover successful execution, real lost-update discovery, replay determinism, invalid schedules, task failures, budgets, validation, and report serialization.

## Roadmap

The next extensions are a pytest plugin, persisted schedule corpora, seeded stochastic exploration, better partial-order reduction, state fingerprints, and adapters for AnyIO/Trio. They are intentionally outside the MVP so the current contract remains small and testable.

## Contributing

Bug reports and focused pull requests are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md), follow the Code of Conduct, add a regression test for behavior changes, and keep public API changes documented.

## License

LoomCheck is released under the [MIT License](LICENSE).
