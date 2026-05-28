# Canonical CAT Reference Implementation v2.0

This repository includes a runnable reference implementation of the canonical Context as a Tool (CAT) loop under `cat_core/`.

## What v2.0 adds

- Typed configuration through `CATConfig`.
- Deterministic JSON-based hashing through `stable_hash`.
- Evidence-aware `CompressionDecision` objects.
- Schema and provenance validation through `validate_memory_delta`.
- A single orchestration function, `run_cat_cycle`, for adapter authors.
- JSONL event logging for steps, compression decisions, memory deltas, and context rebuilds.

## Included interfaces

- `observe(state, step_event, window_size)`
- `should_compress(state, window_threshold, repeat_error_threshold)`
- `compress(state, slice_start, slice_end, compressor_version)`
- `validate_memory_delta(delta, known_step_ids)`
- `apply_memory_delta(state, delta, max_items_per_bucket)`
- `rebuild_context(q, m, i_k)`
- `run_cat_cycle(state, step_event, config, log_path)`

## Files

- `cat_core/models.py`: data models for state, events, decisions, validation results, memory deltas, composed contexts, logs, and configuration.
- `cat_core/core.py`: deterministic CAT control flow, trigger rules, validation, merge logic, context rebuild, and JSONL logging.
- `tests/test_cat_core.py`: baseline behavioral tests for the canonical implementation.

## Extension points

This implementation is intentionally rule-based. Replace `should_compress` with a learned trigger or replace `compress` with an LLM summarizer while preserving the same input/output contracts. Adapter implementations should prefer `run_cat_cycle` when they want a complete reference loop and the lower-level functions when they need more control.
