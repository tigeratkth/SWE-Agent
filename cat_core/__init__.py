"""Canonical CAT core interfaces and reference implementation."""

from .core import (
    apply_memory_delta,
    compress,
    observe,
    rebuild_context,
    run_cat_cycle,
    should_compress,
    stable_hash,
    validate_memory_delta,
)
from .storage import load_state, save_state, state_from_dict
from .models import (
    CANONICAL_CAT_VERSION,
    CATConfig,
    CATCycleResult,
    CATLogEvent,
    CATState,
    ComposeContext,
    CompressionDecision,
    MemoryDelta,
    StepEvent,
    ValidationResult,
)

__all__ = [
    "CANONICAL_CAT_VERSION",
    "CATConfig",
    "CATCycleResult",
    "CATLogEvent",
    "CATState",
    "ComposeContext",
    "CompressionDecision",
    "MemoryDelta",
    "StepEvent",
    "ValidationResult",
    "observe",
    "should_compress",
    "compress",
    "validate_memory_delta",
    "apply_memory_delta",
    "rebuild_context",
    "run_cat_cycle",
    "stable_hash",
    "save_state",
    "load_state",
    "state_from_dict",
]
