from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

CANONICAL_CAT_VERSION = "2.0"
MEMORY_BUCKETS = (
    "goals",
    "decisions",
    "attempts",
    "constraints",
    "open_issues",
    "next_hypotheses",
)


def empty_memory() -> dict[str, list[Any]]:
    return {bucket: [] for bucket in MEMORY_BUCKETS}


@dataclass
class CATConfig:
    window_size: int = 12
    window_threshold: int = 10
    repeat_error_threshold: int = 3
    max_items_per_bucket: int = 128
    compressor_version: str = f"canonical-cat-v{CANONICAL_CAT_VERSION}"


@dataclass
class StepEvent:
    step_id: int
    action: str
    observation: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CompressionDecision:
    decision: bool
    reason_code: str
    confidence: float
    evidence_step_ids: list[int] = field(default_factory=list)


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


@dataclass
class MemoryDelta:
    goals: list[str] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    attempts: list[dict[str, Any]] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    open_issues: list[str] = field(default_factory=list)
    next_hypotheses: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass
class CATState:
    q: dict[str, Any]
    m: dict[str, list[Any]] = field(default_factory=empty_memory)
    i_k: list[StepEvent] = field(default_factory=list)
    step_id: int = 0
    trajectory: list[StepEvent] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=lambda: {"cat_version": CANONICAL_CAT_VERSION})


@dataclass
class ComposeContext:
    q: dict[str, Any]
    m: dict[str, list[Any]]
    i_k: list[dict[str, Any]]
    metadata: dict[str, Any]


@dataclass
class CATCycleResult:
    state: CATState
    decision: CompressionDecision
    memory_delta: MemoryDelta | None
    validation: ValidationResult | None
    context: ComposeContext


LogEventType = Literal["step", "compression_decision", "memory_delta", "context_rebuild"]


@dataclass
class CATLogEvent:
    event_type: LogEventType
    step_id: int
    payload: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
