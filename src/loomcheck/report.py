"""Stable JSON and Markdown report writers."""

from __future__ import annotations

import json
from dataclasses import asdict

from .model import ExplorationResult, RunResult


def run_json(result: RunResult) -> str:
    return json.dumps(asdict(result), indent=2, sort_keys=True) + "\n"


def exploration_json(result: ExplorationResult) -> str:
    return json.dumps(asdict(result), indent=2, sort_keys=True) + "\n"


def run_markdown(result: RunResult) -> str:
    lines = [
        "# LoomCheck run",
        "",
        f"- **Status:** {'PASS' if result.success else 'FAIL'}",
        f"- **Steps:** {result.steps}",
        f"- **Duration:** {result.duration_ms:.3f} ms",
        f"- **Schedule:** `{list(result.schedule)}`",
    ]
    if result.requested_schedule:
        lines.append(f"- **Requested schedule:** `{list(result.requested_schedule)}`")
    if result.divergences:
        lines += ["", "## Schedule divergences", ""]
        lines.extend(f"- {item}" for item in result.divergences)
    if result.failure:
        lines += [
            "",
            "## Failure",
            "",
            f"- **Kind:** `{result.failure.kind}`",
            f"- **Task:** `{result.failure.task or 'unknown'}`",
            f"- **Message:** {result.failure.message}",
        ]
    lines += [
        "",
        "## Decisions",
        "",
        "| Step | Chosen task | Runnable tasks | Labels |",
        "|---:|---|---|---|",
    ]
    for decision in result.decisions:
        lines.append(
            f"| {decision.step} | `{decision.chosen}` | "
            f"`{list(decision.runnable)}` | `{list(decision.labels)}` |"
        )
    return "\n".join(lines) + "\n"


def exploration_markdown(result: ExplorationResult) -> str:
    failures = len(result.failures)
    lines = [
        "# LoomCheck exploration",
        "",
        f"- **Status:** {'PASS' if result.success else 'FAIL'}",
        f"- **Runs:** {len(result.runs)} / {result.max_runs}",
        f"- **Failures:** {failures}",
        f"- **Frontier exhausted:** `{result.exhausted}`",
        f"- **Metadata:** `{dict(result.metadata)}`",
    ]
    if result.minimized_failure:
        failure = result.minimized_failure
        lines += [
            "",
            "## Minimal failure witness",
            "",
            f"- **Fingerprint:** `{failure.failure.fingerprint if failure.failure else 'unknown'}`",
            f"- **Schedule:** `{list(failure.schedule)}`",
            f"- **Task:** `{failure.failure.task if failure.failure else 'unknown'}`",
            f"- **Message:** {failure.failure.message if failure.failure else 'unknown'}",
        ]
    lines += [
        "",
        "## Runs",
        "",
        "| # | Status | Steps | Schedule | Failure |",
        "|---:|---|---:|---|---|",
    ]
    for index, run in enumerate(result.runs, 1):
        failure_text = run.failure.fingerprint if run.failure else "-"
        lines.append(
            "| {} | {} | {} | `{}` | `{}` |".format(
                index,
                "PASS" if run.success else "FAIL",
                run.steps,
                list(run.schedule),
                failure_text,
            )
        )
    return "\n".join(lines) + "\n"


def render(value: RunResult | ExplorationResult, fmt: str) -> str:
    """Render either result using the requested format."""
    if fmt == "json":
        return run_json(value) if isinstance(value, RunResult) else exploration_json(value)
    if fmt == "markdown":
        return run_markdown(value) if isinstance(value, RunResult) else exploration_markdown(value)
    raise ValueError(f"unsupported report format: {fmt}")
