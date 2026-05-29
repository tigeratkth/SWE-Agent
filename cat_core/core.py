from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable

from .models import (
    CATConfig,
    CATCycleResult,
    CATLogEvent,
    CATState,
    ComposeContext,
    CompressionDecision,
    MEMORY_BUCKETS,
    MemoryDelta,
    StepEvent,
    ValidationResult,
)


def observe(state: CATState, step_event: StepEvent, window_size: int = 12) -> CATState:
    state.trajectory.append(step_event)
    state.step_id = step_event.step_id
    state.i_k.append(step_event)
    if len(state.i_k) > window_size:
        state.i_k = state.i_k[-window_size:]
    state.metadata["trajectory_hash"] = stable_hash([asdict(event) for event in state.trajectory])
    state.metadata["i_k_step_ids"] = [event.step_id for event in state.i_k]
    return state


def should_compress(
    state: CATState,
    window_threshold: int = 10,
    repeat_error_threshold: int = 3,
) -> CompressionDecision:
    if len(state.i_k) >= window_threshold:
        return CompressionDecision(
            True,
            "WINDOW_PRESSURE",
            0.9,
            evidence_step_ids=[event.step_id for event in state.i_k],
        )

    recent = state.i_k[-repeat_error_threshold:]
    if len(recent) == repeat_error_threshold and all(_is_error_event(event) for event in recent):
        return CompressionDecision(
            True,
            "ERROR_REPETITION",
            0.85,
            evidence_step_ids=[event.step_id for event in recent],
        )

    if recent and recent[-1].metadata.get("subtask_completed") is True:
        return CompressionDecision(
            True,
            "SUBTASK_COMPLETED",
            0.8,
            evidence_step_ids=[recent[-1].step_id],
        )

    return CompressionDecision(False, "NONE", 0.2, evidence_step_ids=[])


def compress(
    state: CATState,
    slice_start: int | None = None,
    slice_end: int | None = None,
    compressor_version: str = "canonical-cat-v2.1",
) -> MemoryDelta:
    events = state.trajectory[slice_start:slice_end]
    goals: list[str] = []
    decisions: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    constraints: list[str] = []
    open_issues: list[str] = []
    next_hypotheses: list[str] = []

    for event in events:
        if event.metadata.get("goal"):
            goals.append(str(event.metadata["goal"]))
        if event.metadata.get("decision"):
            decisions.append(
                {
                    "decision": str(event.metadata["decision"]),
                    "rationale": str(event.metadata.get("rationale", "recorded from step metadata")),
                    "evidence_step_ids": [event.step_id],
                }
            )
        if event.metadata.get("constraint"):
            constraints.append(str(event.metadata["constraint"]))
        if event.metadata.get("next_hypothesis"):
            next_hypotheses.append(str(event.metadata["next_hypothesis"]))

        attempts.append(
            {
                "action": event.action,
                "result": "failure" if _is_error_event(event) else "partial",
                "evidence_step_ids": [event.step_id],
            }
        )
        if _looks_like_open_issue(event):
            open_issues.append(_truncate(event.observation, 240))

    return MemoryDelta(
        goals=_unique_strings(goals),
        decisions=_dedupe_items(decisions),
        attempts=_dedupe_items(attempts),
        constraints=_unique_strings(constraints),
        open_issues=_unique_strings(open_issues),
        next_hypotheses=_unique_strings(next_hypotheses),
        provenance={
            "from_step": events[0].step_id if events else None,
            "to_step": events[-1].step_id if events else None,
            "source_step_ids": [event.step_id for event in events],
            "compressor_version": compressor_version,
            "source_hash": stable_hash([asdict(event) for event in events]),
        },
    )


def validate_memory_delta(delta: MemoryDelta, known_step_ids: Iterable[int]) -> ValidationResult:
    errors: list[str] = []
    known = set(known_step_ids)

    for bucket in MEMORY_BUCKETS:
        value = getattr(delta, bucket, None)
        if not isinstance(value, list):
            errors.append(f"{bucket} must be a list")

    for bucket in ("decisions", "attempts"):
        for index, item in enumerate(getattr(delta, bucket)):
            if not isinstance(item, dict):
                errors.append(f"{bucket}[{index}] must be an object")
                continue
            evidence = item.get("evidence_step_ids")
            if not isinstance(evidence, list) or not evidence:
                errors.append(f"{bucket}[{index}] must include non-empty evidence_step_ids")
                continue
            missing = [step_id for step_id in evidence if step_id not in known]
            if missing:
                errors.append(f"{bucket}[{index}] references unknown step ids: {missing}")

    provenance = delta.provenance
    if not isinstance(provenance, dict):
        errors.append("provenance must be an object")
    else:
        for field in ("from_step", "to_step", "compressor_version", "source_hash"):
            if field not in provenance:
                errors.append(f"provenance.{field} is required")

    return ValidationResult(valid=not errors, errors=errors)


def apply_memory_delta(state: CATState, delta: MemoryDelta, max_items_per_bucket: int = 128) -> CATState:
    validation = validate_memory_delta(delta, [event.step_id for event in state.trajectory])
    if not validation.valid:
        raise ValueError("Invalid memory_delta: " + "; ".join(validation.errors))

    memory = state.m
    for field in MEMORY_BUCKETS:
        merged = memory.get(field, []) + list(getattr(delta, field))
        memory[field] = _dedupe_items(merged)[-max_items_per_bucket:]
    state.metadata["last_memory_provenance"] = delta.provenance
    state.metadata["memory_hash"] = stable_hash(memory)
    return state


def rebuild_context(q: dict[str, Any], m: dict[str, list[Any]], i_k: list[StepEvent]) -> ComposeContext:
    return ComposeContext(
        q=q,
        m={bucket: list(m.get(bucket, [])) for bucket in MEMORY_BUCKETS},
        i_k=[asdict(step) for step in i_k],
        metadata={
            "q_hash": stable_hash(q),
            "m_hash": stable_hash(m),
            "i_k_step_ids": [step.step_id for step in i_k],
        },
    )


def run_cat_cycle(
    state: CATState,
    step_event: StepEvent,
    config: CATConfig | None = None,
    log_path: str | Path | None = None,
) -> CATCycleResult:
    config = config or CATConfig()
    observe(state, step_event, config.window_size)
    _emit(log_path, CATLogEvent("step", state.step_id, asdict(step_event)))

    decision = should_compress(state, config.window_threshold, config.repeat_error_threshold)
    _emit(log_path, CATLogEvent("compression_decision", state.step_id, asdict(decision)))

    delta: MemoryDelta | None = None
    validation: ValidationResult | None = None
    if decision.decision:
        delta = compress(state, compressor_version=config.compressor_version)
        validation = validate_memory_delta(delta, [event.step_id for event in state.trajectory])
        _emit(
            log_path,
            CATLogEvent(
                "memory_delta",
                state.step_id,
                {"delta": asdict(delta), "validation": asdict(validation)},
            ),
        )
        apply_memory_delta(state, delta, config.max_items_per_bucket)

    context = rebuild_context(state.q, state.m, state.i_k)
    _emit(log_path, CATLogEvent("context_rebuild", state.step_id, asdict(context)))
    return CATCycleResult(state, decision, delta, validation, context)


def stable_hash(value: Any) -> str:
    normalized = _to_jsonable(value)
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(payload).hexdigest()


def _emit(log_path: str | Path | None, event: CATLogEvent) -> None:
    if log_path is None:
        return
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(event), sort_keys=True) + "\n")


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _to_jsonable(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, set):
        return sorted(_to_jsonable(item) for item in value)
    return value


def _is_error_event(event: StepEvent) -> bool:
    return "error" in event.observation.lower() or event.metadata.get("exit_code", 0) != 0


def _looks_like_open_issue(event: StepEvent) -> bool:
    lowered = event.observation.lower()
    return any(marker in lowered for marker in ("todo", "fix", "failing", "failed", "blocked"))


def _truncate(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _unique_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out


def _dedupe_items(items: list[Any]) -> list[Any]:
    seen: set[str] = set()
    deduped: list[Any] = []
    for item in items:
        key = stable_hash(item)
        if key not in seen:
            deduped.append(item)
            seen.add(key)
    return deduped
