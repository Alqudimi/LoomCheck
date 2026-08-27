"""Bounded schedule exploration and failure shrinking."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from .model import ExplorationResult, RunResult, Schedule
from .runtime import Scenario, run


class Explorer:
    """Explore alternative choices observed at explicit checkpoints.

    This is a bounded, replay-based search. It never invents a task name that
    was not observed as runnable in a previous execution.
    """

    def __init__(
        self,
        scenario: Scenario,
        *,
        max_runs: int = 100,
        max_steps: int = 100,
        timeout: float = 5.0,
    ) -> None:
        if max_runs < 1:
            raise ValueError("max_runs must be at least 1")
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        self.scenario = scenario
        self.max_runs = max_runs
        self.max_steps = max_steps
        self.timeout = timeout

    def explore(self, initial_schedule: Iterable[str] = ()) -> ExplorationResult:
        """Run a deterministic frontier search and shrink the first failure."""
        first = Schedule.from_value(list(initial_schedule))
        frontier = deque([first.choices])
        queued = {first.choices}
        runs: list[RunResult] = []
        minimized: RunResult | None = None

        while frontier and len(runs) < self.max_runs:
            prefix = frontier.popleft()
            result = run(
                self.scenario,
                schedule=prefix,
                max_steps=self.max_steps,
                timeout=self.timeout,
            )
            runs.append(result)

            if result.failed and minimized is None:
                minimized = self._shrink(result)

            for decision in result.decisions:
                for choice in decision.runnable:
                    if choice == decision.chosen:
                        continue
                    candidate = result.schedule[: decision.step] + (choice,)
                    if candidate not in queued:
                        queued.add(candidate)
                        frontier.append(candidate)

        return ExplorationResult(
            runs=tuple(runs),
            exhausted=not frontier,
            max_runs=self.max_runs,
            max_steps=self.max_steps,
            minimized_failure=minimized,
            metadata={
                "frontier_size": len(frontier),
                "unique_prefixes": len(queued),
            },
        )

    def _shrink(self, failing: RunResult) -> RunResult:
        """Greedily delete schedule decisions while preserving the fingerprint."""
        if failing.failure is None:
            return failing
        target = failing.failure.fingerprint
        choices = list(failing.schedule)
        index = 0
        while index < len(choices):
            candidate = choices[:index] + choices[index + 1 :]
            trial = run(
                self.scenario,
                schedule=candidate,
                max_steps=self.max_steps,
                timeout=self.timeout,
            )
            if trial.failure is not None and trial.failure.fingerprint == target:
                choices = candidate
            else:
                index += 1
        return run(
            self.scenario,
            schedule=choices,
            max_steps=self.max_steps,
            timeout=self.timeout,
        )


def explore(
    scenario: Scenario,
    *,
    max_runs: int = 100,
    max_steps: int = 100,
    timeout: float = 5.0,
    initial_schedule: Iterable[str] = (),
) -> ExplorationResult:
    """Convenience wrapper for bounded exploration."""
    return Explorer(
        scenario,
        max_runs=max_runs,
        max_steps=max_steps,
        timeout=timeout,
    ).explore(initial_schedule)
