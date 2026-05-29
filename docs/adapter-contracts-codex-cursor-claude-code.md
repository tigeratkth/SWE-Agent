# CAT Adapter Contracts: Codex, Cursor, Claude Code

Version: `v2.1`

This document maps the agent-agnostic CAT spec to three coding-agent environments using a shared contract and runtime-specific adapter responsibilities.

---

## 1) Shared adapter contract

Each adapter MUST implement these functions:

```text
init(run_config) -> adapter_handle
capture_step(adapter_handle, raw_step_io) -> normalized_step_event
build_prompt_context(adapter_handle, Q, M, I_k) -> runtime_context_payload
invoke_compressor(adapter_handle, compression_input) -> memory_delta
emit_logs(adapter_handle, event) -> void
```

### Input normalization requirements

`normalized_step_event` MUST include:

- `step_id`
- `agent_thought_summary` (if available)
- `tool_calls[]`
- `tool_outputs[]`
- `repo_state_fingerprint` (e.g., changed files hash)
- `timestamp`

---

## 2) Codex adapter contract

A first reference implementation exists at `adapters/codex_adapter.py`, and the runnable demo is documented in `docs/v2.1-productization.md`.

### Responsibilities

- Convert Codex tool/action events into `normalized_step_event`.
- Maintain CAT state externally (sidecar JSON or in-memory service).
- Inject `build_prompt_context` payload before each decision step.

### Notes

- Preserve tool provenance for shell/edit actions.
- Keep compressor calls explicit as first-class actions in run logs.

### Suggested artifacts

- `codex_run_log.jsonl`
- `codex_memory_log.jsonl`

---

## 3) Cursor adapter contract

### Responsibilities

- Extract turn-level context from Cursor interaction timeline.
- Map editor actions + terminal outputs into canonical event schema.
- Rehydrate CAT-composed context into prompt/instruction region consistently.

### Notes

- Ensure stable step IDs when users intervene manually.
- Mark user-edited steps distinctly in provenance metadata.

### Suggested artifacts

- `cursor_run_log.jsonl`
- `cursor_memory_log.jsonl`

---

## 4) Claude Code adapter contract

### Responsibilities

- Normalize Claude Code tool invocations and observations.
- Preserve ordering of command/edit/read operations for evidence linkage.
- Apply CAT context rebuild before each assistant action cycle.

### Notes

- Capture environment constraints (sandbox/network) in run metadata.
- Record command exit codes for failure-pattern triggers.

### Suggested artifacts

- `claude_code_run_log.jsonl`
- `claude_code_memory_log.jsonl`

---

## 5) Side-by-side mapping table

| Contract item | Codex | Cursor | Claude Code |
|---|---|---|---|
| Step source | tool/action stream | timeline + terminal/editor events | tool invocation stream |
| Step ID strategy | monotonic runtime counter | timeline index + user-intervention markers | monotonic action-cycle counter |
| Context injection point | pre-decision system/instruction payload | instruction region before generation | pre-action cycle prompt build |
| Compression invocation | explicit CAT tool call | explicit CAT middleware call | explicit CAT tool/action |
| Provenance minimum | command + file deltas | editor + terminal deltas | command/edit/read + exit codes |

---

## 6) Conformance checklist

An adapter is ready to publish when all are true:

- [ ] Produces canonical `normalized_step_event`.
- [ ] Emits auditable `should_compress` decisions.
- [ ] Persists `memory_delta` with evidence step IDs.
- [ ] Rebuilds context via deterministic `compose` path.
- [ ] Exports per-step token/latency/cost metrics (when available).

---

## 7) Publication recommendations

For public sharing, include for each adapter:

1. 1-page architecture diagram
2. minimal runnable example command
3. sample logs (10-20 steps)
4. known limitations
5. compatibility matrix (runtime version, model family)
