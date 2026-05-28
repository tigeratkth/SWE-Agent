# Agent-Agnostic CAT Specification

Version: `v0.1`
Status: `Public draft`

This document defines the portable contract for implementing **Context as a Tool (CAT)** independently of any specific coding assistant runtime.

---

## 1) Scope

This spec standardizes:

- context state representation,
- compression decision interface,
- compressor input/output schema,
- context rebuild semantics,
- minimum observability requirements.

It intentionally does **not** prescribe model provider, prompting style, or UI.

---

## 2) Core abstractions

### 2.1 Context state

At step `t`:

```text
state(t) = {
  Q: fixed_context,
  M: memory_state,
  I_k: recent_interactions_window,
  step_id: integer,
  metadata: {...}
}
```

Where:

- `Q` is immutable during one task run except explicit, audited policy updates.
- `M` is mutable only via CAT compression operations.
- `I_k` is a rolling window over the latest high-fidelity steps.

### 2.2 Effective context

```text
C(t) = compose(Q, M(t), I^k(t))
```

`compose` must be deterministic given equal inputs.

---

## 3) Required interfaces

Implementations MUST expose these functions:

### 3.1 `observe`

```text
observe(state, step_event) -> state'
```

Responsibilities:

- append current step to trajectory log,
- roll `I_k` window,
- update non-memory metadata.

### 3.2 `should_compress`

```text
should_compress(state) -> {
  decision: bool,
  reason_code: string,
  confidence: float [0,1]
}
```

`reason_code` examples:

- `WINDOW_PRESSURE`
- `SUBTASK_COMPLETED`
- `MILESTONE_REACHED`
- `ERROR_REPETITION`

### 3.3 `compress`

```text
compress(state, slice_selector) -> {
  memory_delta,
  provenance,
  validation
}
```

`slice_selector` identifies source steps being summarized.

### 3.4 `rebuild_context`

```text
rebuild_context(Q, M, I_k) -> prompt_context
```

Must preserve precedence: `Q` > `M` > `I_k` formatting rules.

---

## 4) Canonical memory schema

`memory_delta` SHOULD use this structure:

```json
{
  "goals": ["..."],
  "decisions": [
    {
      "decision": "...",
      "rationale": "...",
      "evidence_step_ids": [12, 13]
    }
  ],
  "attempts": [
    {
      "action": "...",
      "result": "success|failure|partial",
      "evidence_step_ids": [14]
    }
  ],
  "constraints": ["..."],
  "open_issues": ["..."],
  "next_hypotheses": ["..."]
}
```

Implementations MAY extend with additional fields but MUST NOT remove the required semantic groups.

---

## 5) Merge semantics for `M(t)`

When applying `memory_delta`:

1. Deduplicate near-identical entries.
2. Preserve unresolved `open_issues` unless explicitly resolved by evidence.
3. Record provenance (`from_step`, `to_step`, compressor version).
4. Keep memory bounded with deterministic eviction policy (oldest resolved items first).

---

## 6) Safety and integrity rules

- No memory statement without trajectory evidence.
- Conflicting memory entries require explicit conflict note.
- Failed attempts should be retained if they prevent repeated dead ends.
- Compression must never mutate `Q`.

---

## 7) Trigger policy guidance

### 7.1 Rule-based baseline

Recommended initial policy:

- Compress if `|I_k|` exceeds threshold.
- Compress at subtask boundary markers.
- Compress after `n` repeated tool errors.

### 7.2 Learned policy (optional)

A learned policy may replace/augment rules, but it must emit the same `decision` object and remain auditable.

---

## 8) Observability requirements

Each run MUST emit machine-readable logs:

- `step_id`, action, observation hash,
- `should_compress` decision object,
- compressor input slice IDs,
- `memory_delta` hash and schema validation result,
- post-merge `M(t)` hash,
- token and latency metrics per step.

---

## 9) Compliance tests (minimum)

A runtime is spec-compliant if it passes:

1. **Deterministic compose test**
2. **No-unsupported-field-drop test** (canonical groups retained)
3. **Evidence-link test** (memory claims trace to steps)
4. **Trigger-log completeness test**
5. **Context-rebuild invariance test**

---

## 10) Versioning

- Breaking interface changes increment major version.
- Schema field additions increment minor version.
- Editorial clarifications increment patch version.
