# CAT Reproduction Kit

Agent-agnostic, production-ready starter kit to reproduce and share the **Context as a Tool (CAT)** methodology for long-horizon software engineering agents across **Codex, Cursor, and Claude Code**.

> Reference paper: https://arxiv.org/pdf/2512.22087

---

## Why this repository exists

Most context-management implementations are tied to one agent runtime. This project provides:

- A **portable CAT specification** (same core behavior across agent stacks).
- A **thin adapter contract** for Codex, Cursor, and Claude Code.
- A reproducible project shape suitable for public benchmarking and collaboration.

If you are publishing your methodology, this repository is designed so others can implement it without reverse engineering your setup.

---

## What CAT means here

At each step `t`, runtime context is represented as:

- `Q`: fixed, task-defining context (system policy, user intent, constraints)
- `M(t)`: compressed long-term memory
- `I^k(t)`: most recent `k` high-fidelity interaction steps

The effective prompt context is:

`C(t) = (Q, M(t), I^k(t))`

The agent can explicitly call a **compressor tool** to update `M(t)` instead of relying only on implicit truncation.

---

## Repository layout

```text
.
├── README.md
├── LICENSE
└── docs/
    ├── agent-agnostic-cat-spec.md
    └── adapter-contracts-codex-cursor-claude-code.md
```

---

## Quickstart (5 minutes)

1. Clone your fork.
2. Read the CAT core spec:
   - `docs/agent-agnostic-cat-spec.md`
3. Pick your runtime and implement the adapter:
   - `docs/adapter-contracts-codex-cursor-claude-code.md`
4. Run one end-to-end task with:
   - logging of `should_compress` decisions
   - emitted `memory_delta`
   - rebuilt context snapshots

---

## Deliverables expected from an implementation

A compliant implementation should produce:

1. **Context state logs**
   - `Q` (versioned hash)
   - `M(t)` snapshots
   - `I^k(t)` rolling window boundaries
2. **Compression event logs**
   - trigger reason
   - input slice IDs
   - compressor output (`memory_delta`)
3. **Evaluation report**
   - task success metrics
   - token/cost deltas vs baseline (no CAT)
   - ablations on trigger policy and compressor schema

---

## Minimal reproducibility checklist

- [ ] Uses canonical state: `Q`, `M(t)`, `I^k(t)`.
- [ ] Explicit `should_compress` decision at every step.
- [ ] Compressor output validated against schema.
- [ ] Context rebuilt only through the canonical merge rules.
- [ ] Baseline and CAT runs share identical task set and stopping criteria.
- [ ] Results include both performance and cost/latency.

---

## Supported adapters

- Codex adapter contract (defined)
- Cursor adapter contract (defined)
- Claude Code adapter contract (defined)

See: `docs/adapter-contracts-codex-cursor-claude-code.md`

---

## Evaluation guidance

Use at least two tracks:

1. **Small deterministic tasks** (for debugging memory logic)
2. **Long-horizon repo tasks** (where context pressure is real)

Recommended core comparisons:

- Baseline agent (no explicit CAT)
- CAT + rule-based triggers
- CAT + learned triggers (if available)

---

## Common failure modes

- Over-compression that removes unresolved TODOs.
- Summary drift (memory claims unsupported by trajectory).
- Trigger oscillation (compressing too frequently).
- Cross-adapter schema mismatch.

Mitigations are specified in the CAT spec and adapter contract docs.

---

## Contributing

Contributions are welcome for:

- Additional runtime adapters
- Better compression schemas
- Evaluation harness templates

Please include:

- a short design note,
- a reproducible command list,
- before/after metrics on at least one shared task.

---

## Citation

If this repo helps your work, cite the originating CAT paper and link this implementation spec in your methodology section.
