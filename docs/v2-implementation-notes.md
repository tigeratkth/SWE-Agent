# Canonical CAT v2.0: What Changed and Why

This note explains what was added in Canonical CAT v2.0, why each design choice matters, and how the pieces fit together architecturally.

## Summary

v2.0 turns the earlier proof-of-concept CAT core into a practical reference loop that adapter authors can call directly. The earlier implementation exposed the right conceptual pieces, but it did not yet provide enough validation, logging, or orchestration to be safely reused across Codex, Cursor, and Claude Code integrations.

## What I added

| Area | Addition | Why |
|---|---|---|
| Versioning | `CANONICAL_CAT_VERSION = "2.0"` and `CATConfig` | Makes runtime behavior explicit and reproducible. |
| State models | Validation, log, cycle-result, and config dataclasses | Gives adapters structured objects instead of loose dictionaries. |
| Compression decisions | `evidence_step_ids` on `CompressionDecision` | Makes trigger decisions auditable. |
| Memory validation | `validate_memory_delta` | Prevents unsupported memory claims from entering long-term memory. |
| Deterministic hashing | JSON-based `stable_hash` | Makes logs, memory snapshots, and context rebuilds comparable across runs. |
| Orchestration | `run_cat_cycle` | Gives adapter authors a single canonical entry point. |
| Observability | JSONL logging via `CATLogEvent` | Produces shareable traces for debugging and benchmarking. |

## Why this design

The paper methodology depends on treating context management as an explicit tool-like action. For a public reproduction kit, that is not enough by itself: users also need to inspect when compression happened, what was compressed, what evidence supports memory entries, and what prompt context was rebuilt after the update.

v2.0 therefore focuses on three principles:

1. **Portability**: the core loop uses plain Python dataclasses and no vendor SDKs.
2. **Auditability**: decisions, memory deltas, provenance, and context rebuilds are loggable as JSONL.
3. **Replaceability**: learned triggers or LLM compressors can replace the rule-based defaults without changing adapter contracts.

## Architecture diagram

```mermaid
flowchart TD
    A[Agent Runtime\nCodex / Cursor / Claude Code] --> B[Adapter Normalizes StepEvent]
    B --> C[observe\nAppend trajectory + roll I^k]
    C --> D[should_compress\nRule or learned trigger]
    D -->|No| H[rebuild_context\nQ + M(t) + I^k(t)]
    D -->|Yes| E[compress\nCreate MemoryDelta]
    E --> F[validate_memory_delta\nEvidence + provenance checks]
    F --> G[apply_memory_delta\nMerge into M(t)]
    G --> H
    H --> I[Runtime Context Payload]
    C -. JSONL .-> J[CAT Logs]
    D -. JSONL .-> J
    E -. JSONL .-> J
    H -. JSONL .-> J
```

## End-to-end v2.0 cycle

1. The adapter converts raw runtime I/O into a `StepEvent`.
2. `observe` appends the step to the full trajectory and updates the rolling recent window `I^k`.
3. `should_compress` emits a decision and evidence step IDs.
4. If compression is triggered, `compress` creates a `MemoryDelta` from selected trajectory events.
5. `validate_memory_delta` verifies evidence links and provenance fields.
6. `apply_memory_delta` deduplicates and merges the delta into `M(t)`.
7. `rebuild_context` returns the canonical composed context for the next agent step.
8. `run_cat_cycle` performs the whole sequence and optionally writes JSONL logs.

## Why not make v2.0 fully learned yet?

The goal of v2.0 is a stable public contract, not model performance. A learned trigger or compressor can be added later, but first the community needs a deterministic baseline that everyone can run and inspect. That baseline is what lets future learned components be compared fairly.

## Next recommended milestone

v2.1 should add one concrete adapter implementation, preferably Codex first, using `run_cat_cycle` as the integration point. After that, v2.2 can add an LLM-backed compressor that still emits the same `MemoryDelta` schema.
