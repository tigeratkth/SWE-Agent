from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from adapters import CodexAdapter
from cat_core import CATConfig, CATState, run_cat_cycle
from cat_core.storage import load_state, save_state


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Canonical CAT over a Codex-like JSONL trace.")
    parser.add_argument("--input", required=True, help="Path to Codex-like input JSONL trace.")
    parser.add_argument("--output", required=True, help="Path to write CAT event JSONL logs.")
    parser.add_argument("--state", required=True, help="Path to persist final CAT state JSON.")
    parser.add_argument("--resume", action="store_true", help="Resume from --state if it already exists.")
    parser.add_argument("--window-size", type=int, default=12)
    parser.add_argument("--window-threshold", type=int, default=3)
    parser.add_argument("--repeat-error-threshold", type=int, default=3)
    args = parser.parse_args()

    adapter = CodexAdapter({"input": args.input, "output": args.output, "state": args.state})
    state_path = Path(args.state)
    if args.resume and state_path.exists():
        state = load_state(state_path)
    else:
        state = CATState(q={"task": "Run Canonical CAT over a Codex-like trace", "runtime": "codex"})

    output_path = Path(args.output)
    if output_path.exists() and not args.resume:
        output_path.unlink()

    config = CATConfig(
        window_size=args.window_size,
        window_threshold=args.window_threshold,
        repeat_error_threshold=args.repeat_error_threshold,
    )

    compression_count = 0
    for raw_event in _read_jsonl(Path(args.input)):
        step = adapter.capture_step(raw_event)
        result = run_cat_cycle(state, step, config=config, log_path=output_path)
        if result.decision.decision:
            compression_count += 1
        adapter.emit_logs(
            {
                "step_id": step.step_id,
                "decision": result.decision.reason_code,
                "compressed": result.decision.decision,
                "context_i_k": result.context.metadata["i_k_step_ids"],
            }
        )

    save_state(state_path, state)
    summary = {
        "steps": len(state.trajectory),
        "compressions": compression_count,
        "memory_hash": state.metadata.get("memory_hash"),
        "state_path": str(state_path),
        "log_path": str(output_path),
        "memory": state.m,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        event = json.loads(line)
        if not isinstance(event, dict):
            raise ValueError(f"Line {line_number} must be a JSON object")
        events.append(event)
    return events


if __name__ == "__main__":
    main()
