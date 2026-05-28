import json

import pytest

from cat_core.core import (
    apply_memory_delta,
    compress,
    observe,
    rebuild_context,
    run_cat_cycle,
    should_compress,
    stable_hash,
    validate_memory_delta,
)
from cat_core.models import CATConfig, CATState, MemoryDelta, StepEvent


def test_observe_and_window_rolls() -> None:
    state = CATState(q={"task": "x"})
    for i in range(1, 6):
        observe(state, StepEvent(step_id=i, action="run", observation="ok"), window_size=3)
    assert state.step_id == 5
    assert len(state.i_k) == 3
    assert [e.step_id for e in state.i_k] == [3, 4, 5]
    assert state.metadata["i_k_step_ids"] == [3, 4, 5]


def test_should_compress_window_pressure() -> None:
    state = CATState(q={"task": "x"})
    for i in range(1, 5):
        observe(state, StepEvent(step_id=i, action="run", observation="ok"), window_size=10)
    decision = should_compress(state, window_threshold=4)
    assert decision.decision is True
    assert decision.reason_code == "WINDOW_PRESSURE"
    assert decision.evidence_step_ids == [1, 2, 3, 4]


def test_compress_validate_and_apply_memory_delta() -> None:
    state = CATState(q={"task": "x"})
    observe(state, StepEvent(step_id=1, action="search", observation="todo: fix parser", metadata={"goal": "fix parser"}))
    observe(state, StepEvent(step_id=2, action="test", observation="error: failed tests", metadata={"exit_code": 1}))
    delta = compress(state)
    validation = validate_memory_delta(delta, [event.step_id for event in state.trajectory])
    assert validation.valid is True
    apply_memory_delta(state, delta)
    assert "fix parser" in state.m["goals"]
    assert len(state.m["attempts"]) == 2
    assert state.metadata.get("memory_hash")


def test_apply_memory_delta_rejects_unknown_evidence() -> None:
    state = CATState(q={"task": "x"})
    observe(state, StepEvent(step_id=1, action="run", observation="ok"))
    delta = MemoryDelta(
        attempts=[{"action": "run", "result": "partial", "evidence_step_ids": [999]}],
        provenance={"from_step": 999, "to_step": 999, "compressor_version": "x", "source_hash": "abc"},
    )
    with pytest.raises(ValueError, match="unknown step ids"):
        apply_memory_delta(state, delta)


def test_rebuild_context_shape_and_hashes() -> None:
    state = CATState(q={"task": "x"})
    observe(state, StepEvent(step_id=1, action="run", observation="ok"))
    ctx = rebuild_context(state.q, state.m, state.i_k)
    assert ctx.q["task"] == "x"
    assert isinstance(ctx.i_k, list)
    assert ctx.i_k[0]["step_id"] == 1
    assert ctx.metadata["i_k_step_ids"] == [1]
    assert ctx.metadata["q_hash"] == stable_hash({"task": "x"})


def test_run_cat_cycle_emits_jsonl(tmp_path) -> None:
    log_path = tmp_path / "cat.jsonl"
    state = CATState(q={"task": "x"})
    result = run_cat_cycle(
        state,
        StepEvent(step_id=1, action="run", observation="todo: fix parser", metadata={"goal": "fix parser"}),
        CATConfig(window_size=4, window_threshold=1),
        log_path=log_path,
    )
    assert result.decision.decision is True
    assert result.validation is not None and result.validation.valid is True
    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert [record["event_type"] for record in records] == [
        "step",
        "compression_decision",
        "memory_delta",
        "context_rebuild",
    ]
