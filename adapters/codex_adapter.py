from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from cat_core import ComposeContext, MemoryDelta, StepEvent


class CodexAdapter:
    """Normalize Codex-like tool/action records for the Canonical CAT loop.

    The adapter intentionally accepts plain dictionaries so it can be used with
    exported traces, hand-written fixtures, or a live runtime integration.
    """

    def __init__(self, run_config: dict[str, Any] | None = None) -> None:
        self.run_config: dict[str, Any] = {}
        self.events: list[dict[str, Any]] = []
        if run_config is not None:
            self.init(run_config)

    def init(self, run_config: dict[str, Any]) -> None:
        self.run_config = dict(run_config)

    def capture_step(self, raw_step_io: dict[str, Any]) -> StepEvent:
        step_id = int(raw_step_io["step_id"])
        tool = str(raw_step_io.get("tool", raw_step_io.get("type", "action")))
        command = raw_step_io.get("command") or raw_step_io.get("path") or raw_step_io.get("action") or ""
        action = f"{tool}: {command}" if command else tool
        observation = str(raw_step_io.get("output", raw_step_io.get("observation", "")))
        timestamp = str(raw_step_io.get("timestamp") or datetime.now(timezone.utc).isoformat())

        metadata = {
            "runtime": "codex",
            "tool": tool,
            "command": raw_step_io.get("command"),
            "path": raw_step_io.get("path"),
            "exit_code": raw_step_io.get("exit_code", 0),
            "changed_files": list(raw_step_io.get("changed_files", [])),
            "repo_state_fingerprint": raw_step_io.get("repo_state_fingerprint"),
        }
        for field in ("goal", "decision", "rationale", "constraint", "next_hypothesis", "subtask_completed"):
            if field in raw_step_io:
                metadata[field] = raw_step_io[field]

        return StepEvent(step_id=step_id, action=action, observation=observation, timestamp=timestamp, metadata=metadata)

    def build_prompt_context(self, context: ComposeContext) -> dict[str, Any]:
        return {
            "runtime": "codex",
            "system_context": context.q,
            "long_term_memory": context.m,
            "recent_interactions": context.i_k,
            "context_metadata": context.metadata,
        }

    def invoke_compressor(self, compression_input: dict[str, Any]) -> MemoryDelta:
        delta = compression_input.get("memory_delta")
        if isinstance(delta, MemoryDelta):
            return delta
        if isinstance(delta, dict):
            return MemoryDelta(**delta)
        raise ValueError("CodexAdapter.invoke_compressor requires a memory_delta object or dict")

    def emit_logs(self, event: dict[str, Any]) -> None:
        self.events.append(dict(event))

    def serialize_step(self, step: StepEvent) -> dict[str, Any]:
        return asdict(step)
