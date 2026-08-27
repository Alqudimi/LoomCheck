# Troubleshooting

## The command exits with code 1

Code `1` means LoomCheck found a scenario failure, timeout, or step-budget exhaustion. For the demo, this is intentional. Inspect the `Failure` section or JSON `failure` object, then replay the reported schedule with `loomcheck run` or the Python API.

## A replay reports a divergence

A divergence means the requested task was not runnable at that exact step. This usually happens when the schedule was copied from a different scenario version or when a checkpoint was added or removed. LoomCheck records the divergence and uses a deterministic fallback; regenerate the witness against the current code rather than ignoring the message.

## The explorer finds no failure

LoomCheck only controls explicit checkpoints. Add boundaries before and after the shared state transition or awaitable operation that can interleave. Increase `max_runs` and `max_steps` gradually, and keep the timeout finite. The explorer is bounded and does not claim exhaustive coverage of arbitrary async programs.

## A run exceeds the step budget

A step is one released checkpoint request. Increase `max_steps` if the scenario is valid but has many transitions. If the task is unexpectedly looping, keep the budget small while diagnosing it; `StepBudgetExceeded` is designed to stop such runs safely.

## A run times out

Timeouts cover the complete local scenario and cleanup. Check for a checkpoint that no task can reach, a child task that is never started, or external I/O that is not modeled behind a deterministic adapter. LoomCheck does not virtualize network or filesystem operations.

## The report contains sensitive data

Labels, exception messages, and tracebacks are copied into reports. Treat them like test logs, redact sensitive values before sharing, and do not commit local report files. The default `.gitignore` excludes common report names.
