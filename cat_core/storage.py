from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from .models import CATState, StepEvent, empty_memory


def save_state(path: str | Path, state: CATState) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(_to_jsonable(state), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_state(path: str | Path) -> CATState:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return state_from_dict(payload)


def state_from_dict(payload: dict[str, Any]) -> CATState:
    memory = empty_memory()
    for bucket, values in payload.get("m", {}).items():
        memory[bucket] = list(values)

    return CATState(
        q=dict(payload.get("q", {})),
        m=memory,
        i_k=[_step_from_dict(item) for item in payload.get("i_k", [])],
        step_id=int(payload.get("step_id", 0)),
        trajectory=[_step_from_dict(item) for item in payload.get("trajectory", [])],
        metadata=dict(payload.get("metadata", {})),
    )


def append_jsonl(path: str | Path, event: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_to_jsonable(event), sort_keys=True) + "\n")


def _step_from_dict(payload: dict[str, Any]) -> StepEvent:
    return StepEvent(
        step_id=int(payload["step_id"]),
        action=str(payload["action"]),
        observation=str(payload.get("observation", "")),
        timestamp=str(payload.get("timestamp", "")),
        metadata=dict(payload.get("metadata", {})),
    )


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _to_jsonable(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    return value
