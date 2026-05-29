from __future__ import annotations

from typing import Any, Protocol

from cat_core import ComposeContext, MemoryDelta, StepEvent


class CATAdapter(Protocol):
    """Protocol every runtime adapter should implement."""

    def init(self, run_config: dict[str, Any]) -> None:
        """Initialize adapter-level configuration."""

    def capture_step(self, raw_step_io: dict[str, Any]) -> StepEvent:
        """Normalize a raw runtime event into a CAT StepEvent."""

    def build_prompt_context(self, context: ComposeContext) -> dict[str, Any]:
        """Convert canonical CAT context into a runtime-specific prompt payload."""

    def invoke_compressor(self, compression_input: dict[str, Any]) -> MemoryDelta:
        """Invoke runtime-specific compression when an adapter owns compression."""

    def emit_logs(self, event: dict[str, Any]) -> None:
        """Emit adapter-specific logs."""
