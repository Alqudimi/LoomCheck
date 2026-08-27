from __future__ import annotations

import asyncio
import json

import pytest

from loomcheck import Loom, Schedule, explore, run
from loomcheck.report import exploration_json, exploration_markdown, run_json, run_markdown


async def lost_update_scenario(loom: Loom) -> None:
    state = {"value": 0}

    async def worker(name: str) -> None:
        await loom.checkpoint(f"{name}:read")
        current = state["value"]
        await loom.checkpoint(f"{name}:write")
        state["value"] = current + 1

    tasks = [loom.start_soon(worker(name), name=name) for name in ("alpha", "beta")]
    await asyncio.gather(*tasks)
    if state["value"] != 2:
        raise AssertionError(f"lost update: expected 2, got {state['value']}")


async def safe_scenario(loom: Loom) -> None:
    async def worker(name: str) -> None:
        await loom.checkpoint(f"{name}:work")

    await asyncio.gather(
        loom.start_soon(worker("alpha"), name="alpha"),
        loom.start_soon(worker("beta"), name="beta"),
    )


async def infinite_scenario(loom: Loom) -> None:
    while True:
        await loom.checkpoint("loop")


def test_explorer_finds_and_shrinks_lost_update() -> None:
    result = explore(lost_update_scenario, max_runs=20, max_steps=20)

    assert not result.success
    assert result.failures
    assert result.minimized_failure is not None
    assert result.minimized_failure.failure is not None
    assert result.minimized_failure.failure.kind == "AssertionError"
    assert len(result.minimized_failure.schedule) <= 4
    assert result.minimized_failure.failure.fingerprint == result.failures[0].failure.fingerprint


def test_replay_is_deterministic_and_records_decisions() -> None:
    first = run(lost_update_scenario, schedule=["alpha", "beta", "alpha", "beta"])
    second = run(lost_update_scenario, schedule=first.schedule)

    assert first.success is False
    assert second.success is False
    assert second.schedule == first.schedule
    assert second.failure is not None
    assert first.failure is not None
    assert second.failure.fingerprint == first.failure.fingerprint
    assert [item.chosen for item in second.decisions] == list(first.schedule)


def test_invalid_requested_choice_is_reported_but_does_not_silently_change_result() -> None:
    result = run(safe_scenario, schedule=["not-runnable"])

    assert result.success
    assert result.divergences
    assert "not-runnable" in result.divergences[0]


def test_step_budget_is_a_first_class_failure() -> None:
    result = run(infinite_scenario, max_steps=3, timeout=1)

    assert not result.success
    assert result.failure is not None
    assert result.failure.kind == "StepBudgetExceeded"
    assert result.steps == 3


def test_failures_in_scenario_are_captured_with_task_name() -> None:
    async def scenario(loom: Loom) -> None:
        async def boom() -> None:
            await loom.checkpoint("before boom")
            raise RuntimeError("broken")

        await asyncio.gather(loom.start_soon(boom(), name="worker"))

    result = run(scenario)

    assert not result.success
    assert result.failure is not None
    assert result.failure.kind == "RuntimeError"
    assert result.failure.task == "worker"
    assert "broken" in (result.failure.traceback or "")


def test_report_writers_are_machine_and_human_readable() -> None:
    result = explore(safe_scenario, max_runs=4)

    parsed = json.loads(exploration_json(result))
    assert parsed["success"] if "success" in parsed else True
    assert "runs" in parsed
    assert "# LoomCheck exploration" in exploration_markdown(result)
    assert "# LoomCheck run" in run_markdown(result.runs[0])


def test_validation_rejects_bad_api_values() -> None:
    with pytest.raises(ValueError):
        Schedule.from_value(["ok", 1])
    with pytest.raises(TypeError):
        Schedule.from_value("alpha")
    with pytest.raises(ValueError):
        Loom(max_steps=0)
    with pytest.raises(TypeError):
        Loom().run(lambda _: "not awaitable")  # type: ignore[arg-type]


def test_model_serialization_and_properties() -> None:
    result = run(safe_scenario)
    assert result.failed is False
    assert result.to_dict()["success"] is True
    assert Schedule.from_value(["alpha"]).to_list() == ["alpha"]
    assert result.decisions
    assert result.decisions[0].step == 0


def test_report_json_for_one_run_and_failure_markdown() -> None:
    result = run(lost_update_scenario, schedule=["alpha", "beta", "alpha", "beta"])
    assert '"success": false' in run_json(result)
    markdown = run_markdown(result)
    assert "## Failure" in markdown
    assert "AssertionError" in markdown


def test_cli_demo_writes_report_and_uses_failure_exit_code(tmp_path) -> None:
    from loomcheck.cli import main

    output = tmp_path / "demo.json"
    assert main(["demo", "race", "--format", "json", "--output", str(output)]) == 1
    payload = json.loads(output.read_text())
    assert payload["minimized_failure"]["failure"]["kind"] == "AssertionError"


def test_cli_run_imports_module_target_and_supports_markdown(tmp_path) -> None:
    from loomcheck.cli import main

    output = tmp_path / "safe.md"
    assert main([
        "run",
        "loomcheck.cli:_demo_target",
        "--format",
        "markdown",
        "--output",
        str(output),
    ]) == 0
    assert "PASS" in output.read_text()


def test_cli_rejects_invalid_target_and_schedule() -> None:
    from loomcheck.cli import main

    assert main(["run", "not-a-target"]) == 2
    assert main(["explore", "examples.race_scenario:safe", "--schedule", "not-json"]) == 2


def test_runtime_rejects_bad_task_names_and_duplicate_tasks() -> None:
    async def scenario(loom: Loom) -> None:
        invalid_name = asyncio.sleep(0)
        with pytest.raises(ValueError):
            loom.start_soon(invalid_name, name=" bad")
        invalid_name.close()
        loom.start_soon(asyncio.sleep(0), name="worker")
        duplicate = asyncio.sleep(0)
        with pytest.raises(ValueError):
            loom.start_soon(duplicate, name="worker")
        duplicate.close()

    result = run(scenario)
    assert result.success
