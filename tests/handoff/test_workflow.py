"""Guard against cross-platform path and workflow sequencing regressions."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import pytest

spec = spec_from_file_location("workflow", Path(__file__).resolve().parents[2] / "scripts/run_pipeline.py")
workflow = module_from_spec(spec)
spec.loader.exec_module(workflow)


@pytest.mark.parametrize("mode,sequence,full", [("smoke", "fixture", False),
                         ("research", "adfa", True), ("research", "fixture", False)])
def test_plan_is_ordered_and_routes_data(mode, sequence, full):
    plan = workflow.stages(mode, "local-example", 7, full, True, "cpu", sequence, True)
    visited = {}
    for name, prerequisites, argv in plan:
        assert name not in visited
        assert all(key in visited for key in prerequisites)
        visited[name] = argv
    expected = "research-full" if full else mode
    assert f"data/processed/{expected}/events.csv" in visited["detection"]
    assert "--resume" in visited["detection"]
    assert ("fusion" in visited) == (sequence == "adfa" and mode == "research")


def test_concurrent_resume_guard(tmp_path):
    with workflow.exclusive_run(tmp_path):
        with pytest.raises(SystemExit, match="Another workflow"):
            with workflow.exclusive_run(tmp_path):
                raise AssertionError("unexpected concurrent execution")
    with workflow.exclusive_run(tmp_path):
        assert (tmp_path / "workflow.lock").is_file()
