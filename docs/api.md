# API Guide

## Scenario contract

A scenario is a callable receiving a `Loom` instance and returning an awaitable. A scenario normally creates child tasks with `start_soon`, places `checkpoint` calls around meaningful transitions, and awaits the children before returning.

```python
async def scenario(loom: Loom) -> None:
    task = loom.start_soon(worker(loom), name="worker")
    await task
```

## `Loom.start_soon`

`start_soon(awaitable, name=...)` starts a named child task owned by the current run. Names must be unique and have no outer whitespace. The name becomes the unit of a schedule decision and appears in reports.

## `Loom.checkpoint`

`await loom.checkpoint(label)` registers the current task as runnable. The coordinator releases exactly one waiting task at a time. Labels are descriptive strings and are recorded with the decision; they do not affect scheduling.

## `run`

`run(scenario, schedule=None, max_steps=100, timeout=5.0)` executes one fresh event loop. The optional schedule is a list or tuple of task names. If a requested name is not runnable at a particular step, LoomCheck records a divergence and falls back to the sorted first runnable task instead of silently producing an unexplained result.

The returned `RunResult` exposes `success`, `schedule`, `decisions`, `failure`, `divergences`, `steps`, and `duration_ms`.

## `explore`

`explore(scenario, max_runs=100, max_steps=100, timeout=5.0)` executes bounded alternative prefixes observed from prior runs. The search is intentionally finite. When it finds a failure, `minimized_failure` contains the result of a greedy replay-based shrinker.

## Failure handling

A task exception is captured with its type, message, task name, and formatted traceback. A timeout or step-budget exhaustion has a first-class failure kind. Remaining tasks are cancelled and awaited before the result is returned.

## Report formats

The `report` module exposes `run_json`, `exploration_json`, `run_markdown`, `exploration_markdown`, and `render`. These functions are pure serializers; they do not execute scenarios or touch the network.
