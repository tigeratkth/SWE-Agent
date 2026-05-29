import json
import subprocess
import sys

from adapters import CodexAdapter
from cat_core import CATState, StepEvent, load_state, save_state


def test_codex_adapter_captures_step_event() -> None:
    adapter = CodexAdapter()
    step = adapter.capture_step(
        {
            "step_id": 7,
            "tool": "shell",
            "command": "pytest",
            "output": "error: failed",
            "exit_code": 1,
            "changed_files": ["src/parser.py"],
            "goal": "fix tests",
        }
    )
    assert step.step_id == 7
    assert step.action == "shell: pytest"
    assert step.observation == "error: failed"
    assert step.metadata["runtime"] == "codex"
    assert step.metadata["exit_code"] == 1
    assert step.metadata["goal"] == "fix tests"


def test_state_persistence_roundtrip(tmp_path) -> None:
    state = CATState(q={"task": "persist"})
    state.trajectory.append(StepEvent(step_id=1, action="run", observation="ok"))
    state.i_k.append(StepEvent(step_id=1, action="run", observation="ok"))
    state.step_id = 1
    path = tmp_path / "state.json"
    save_state(path, state)
    loaded = load_state(path)
    assert loaded.q == state.q
    assert loaded.step_id == 1
    assert loaded.trajectory[0].action == "run"
    assert loaded.i_k[0].observation == "ok"


def test_cat_demo_cli_creates_logs_and_state(tmp_path) -> None:
    output = tmp_path / "demo.cat.jsonl"
    state_path = tmp_path / "demo.state.json"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/cat_demo.py",
            "--input",
            "examples/codex_trace_sample.jsonl",
            "--output",
            str(output),
            "--state",
            str(state_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    summary = json.loads(completed.stdout)
    assert summary["steps"] == 4
    assert summary["compressions"] >= 1
    assert output.exists()
    assert state_path.exists()
    events = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert "compression_decision" in {event["event_type"] for event in events}
    loaded = load_state(state_path)
    assert loaded.step_id == 4
    assert loaded.m["goals"] == ["fix parser tests"]
