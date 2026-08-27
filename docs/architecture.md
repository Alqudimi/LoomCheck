# LoomCheck Architecture

## Product vision

LoomCheck is a local-first testing tool for asynchronous Python workflows. It makes a bounded set of cooperative scheduling decisions explicit, explores alternative interleavings, and preserves the smallest reproducible schedule for a failure. The product is intentionally honest: it does not claim to detect every race or preempt arbitrary Python instructions.

## Problem statement

`asyncio` applications can fail only under a particular order of task progress. A normal test run observes one schedule, while sleeps and random delays make failures flaky rather than explainable. Existing pytest integration helps run async tests, but does not itself provide a scheduler explorer. LoomCheck adds a small, explicit control plane at user-selected `await loom.checkpoint(...)` boundaries.

## Target users

The first users are Python engineers building API clients, background workers, orchestration code, async state machines, and libraries with shared mutable state. The secondary audience is maintainers who need a deterministic regression witness in CI without a service, database, or hosted observability product.

## MVP contract

| Capability | MVP behavior |
|---|---|
| Controlled runtime | Run named asyncio tasks that cooperate at explicit checkpoints. |
| Deterministic replay | Accept a schedule prefix containing task names and replay it. |
| Bounded exploration | Explore observed runnable alternatives up to run and step budgets. |
| Failure witness | Capture exception type/message, checkpoint trace, runnable sets, and chosen decisions. |
| Schedule shrinking | Greedily remove unnecessary decisions while preserving the same failure fingerprint. |
| CLI | `run`, `explore`, and `demo race` commands with JSON and Markdown reports. |
| Library API | Typed Python API with no mandatory runtime dependency beyond the standard library. |
| CI output | Stable exit codes and machine-readable JSON suitable for a GitHub Actions step. |

## Explicit non-goals

LoomCheck does not instrument arbitrary bytecode, replace the operating-system scheduler, prove data-race freedom, virtualize network or filesystem I/O, or guarantee exhaustive exploration of an unbounded state space. It is a bounded systematic tester for cooperative async code.

## Architecture

```text
User scenario callable
        |
        v
Loom public API ---- checkpoint() ----> Runtime coordinator
        |                                      |
        |                                      +--> runnable set
        |                                      +--> decision policy
        |                                      +--> event release
        v                                      v
asyncio Tasks <---- explicit gates ---- Scheduler trace
        |
        v
RunResult --> Explorer --> Shrinker --> Report writers (JSON/Markdown)
```

The runtime owns one event loop per run. A scenario factory registers coroutines through `Loom.start_soon`. Every checkpoint places the current task into a deterministic runnable set and waits until the coordinator releases it. The coordinator records the observed schedule and stops on the first task exception or timeout. The explorer treats the recorded runnable sets as a frontier of alternative prefixes; this is bounded DFS-style exploration rather than an unsound claim of exhaustive model checking.

## Module boundaries

| Module | Responsibility | Dependency direction |
|---|---|---|
| `model.py` | Immutable schedule, decision, failure, run, and exploration data models. | No project modules. |
| `runtime.py` | Asyncio coordination, task lifecycle, checkpoints, timeout and failure capture. | Imports `model`. |
| `explorer.py` | Frontier management, deterministic ordering, repeated runs, failure selection, shrinking. | Imports `model`, `runtime`. |
| `report.py` | JSON and Markdown serialization; no scheduling logic. | Imports `model`. |
| `cli.py` | Argument parsing, target loading, exit codes, demo scenario. | Imports public API and `report`. |
| `__init__.py` | Small stable public surface. | Re-exports selected symbols. |

## Failure flow

A task exception is captured as a failure fingerprint and causes all remaining tasks to be cancelled. Cancellation is awaited with `return_exceptions=True`. A timeout is represented as an explicit `TimeoutFailure` rather than a generic traceback. Invalid schedules are not silently accepted: the run records divergence when a requested task is not currently runnable, then uses the deterministic first runnable task so a shortened schedule remains executable.

## Security model

The library is local-first and has no network behavior. The CLI imports a user-selected `module:callable`, so executing a target is an explicit local-code operation, not a sandbox. Reports may contain exception messages and checkpoint labels; users should treat them as potentially sensitive. The project never stores secrets, sends telemetry, evaluates arbitrary shell commands, or deserializes executable objects. Schedule files use JSON only and are validated before use.

## Configuration and compatibility

The runtime accepts explicit budgets (`max_steps`, `timeout`), an optional schedule, and a deterministic fallback policy. The CLI uses command-line flags and JSON schedule/report files. Python 3.10+ is the initial support range. The core uses only the standard library; development tools are isolated in optional dependency groups.

## Extension strategy

The model separates schedule representation from policy so future versions can add random-seeded exploration, partial-order reduction, or a Trio/AnyIO adapter without changing report consumers. Report writers are format strategies. Runtime adapters can implement the same `ScenarioTarget` contract. Future storage backends can persist report artifacts, but the default remains filesystem-only.

## Performance strategy

The hot path performs a small lock/condition operation per explicit checkpoint and keeps traces in memory for one run. Exploration is bounded by `max_runs` and `max_steps`; no unbounded queue is created. The benchmark measures single-run throughput and exploration throughput separately. Users should place checkpoints around meaningful state transitions rather than every line.

## Roadmap

The next logical extensions are a pytest plugin, schedule corpus files, a seeded stochastic policy, optional state fingerprints for better deduplication, and adapters for AnyIO/Trio. These are deliberately not required for the MVP and do not change its core contract.
