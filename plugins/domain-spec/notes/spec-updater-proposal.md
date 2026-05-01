# Spec Updater Proposal

Design for automating updates to `<stem>.specs.md`, `<stem>.exceptions.md`, and `<stem>.test-plan.md` in response to a report produced by `updates-detector` (see `notes/update-types.md` for the change taxonomy).

---

## Goal

Given a fresh `<stem>.updates.md`, refresh the spec artifacts so they reflect the new diagram + prose, **without** re-running the full `generate-specs` pipeline across every category.

---

## Design principle

**Reuse the existing pipeline at category granularity. Do not invent a per-class patcher.**

The `class-specifier` and `pattern-assigner` agents are category-scoped: they operate on a whole category and emit a `.specs-tmp/<category>.md` file consumed by `specs-merger`. Splicing single class blocks into `<stem>.specs.md` would require either (a) running the category pipeline anyway and post-diffing, or (b) modifying both agents to accept single-class mode and reconstructing partial-dependency context per class. Both are more code, more divergence risk, and more bugs than the alternative.

The alternative: **the dispatcher reads the report, picks affected categories, and re-runs the existing category pipeline only for those categories.** The update-type taxonomy informs *which categories* and *which sidecars*, not how to patch.

---

## Agents

| Agent / skill | Owns | Trigger |
|---|---|---|
| `updates-dispatcher` (skill) | Reads report; fans out category re-runs and sidecar updaters | User runs `/update-specs <diagram_file>` |
| `specs-splitter` (new) | Pre-populates `.specs-tmp/` from existing `<stem>.specs.md` for unaffected categories | Before category re-runs |
| Existing `class-specifier` | Per-category temp file | Each category in `## Affected Categories` |
| Existing `pattern-assigner` | Annotates per-category temp file with patterns | Each category in `## Affected Categories` |
| Existing `specs-merger` | Consolidates temp files into `<stem>.specs.md` | After category re-runs complete |
| `test-plan-updater` (new) | `<stem>.test-plan.md` | M4, M5, R5, L1, L2 affecting an aggregate |
| `exceptions-updater` (new) | `<stem>.exceptions.md` | L1/L2 of exception classes; method changes implying new/removed raises |

That is **3 new agents + 1 orchestrator skill** (`specs-splitter`, `test-plan-updater`, `exceptions-updater`, plus the dispatcher). No new spec-body agents — `class-specifier`, `pattern-assigner`, and `specs-merger` are reused unchanged.

---

## Dispatcher logic

`specs-merger` consumes the full set of `.specs-tmp/<category>.md` files and any missing category is dropped from the final spec. So before running affected-category re-specs, the dispatcher must **pre-populate `.specs-tmp/` with the unchanged category sections extracted from the existing `<stem>.specs.md`**. After that, `class-specifier` + `pattern-assigner` overwrite only the affected temp files, and `specs-merger` runs unchanged.

`/update-specs <diagram_file>`:

1. Read `<stem>.updates.md`.
2. If `## Summary` is `No changes detected.` → exit.
3. If the warning line `_warning: HEAD version had ... Mermaid blocks ...` is present → fall back to full `/generate-specs`.
4. Parse `## Affected Categories` → set `A`. Compute the full category set `C` (the six canonical categories that have content in the existing `<stem>.specs.md`).
5. **Pre-populate temp files** — invoke `specs-splitter` (new helper agent or skill, see below) which reads the current `<stem>.specs.md`, splits it by category heading, and writes one `.specs-tmp/<category>.md` per category in `C \ A`. Affected categories are intentionally **not** pre-populated — their temp files will be produced by step 6.
6. For each category in `A`, fan out **in parallel**:
   - `@class-specifier <diagram_file> <category>` (overwrites any existing temp file for this category).
7. After all `class-specifier` runs complete, fan out **in parallel**:
   - `@pattern-assigner <diagram_file> <category>` per category in `A`.
8. Run `@specs-merger <diagram_file>` once. The merger sees a complete `.specs-tmp/` and produces a complete `<stem>.specs.md` — affected categories regenerated, others passed through verbatim.
9. In parallel with steps 5–8, fan out sidecars when triggered:
   - `test-plan-updater` if any aggregate-class member changes appear (M4/M5/L1/L2 with stereotype `<<Aggregate Root>>` or `<<Entity>>`).
   - `exceptions-updater` if any class-level changes touch declared exception classes, or any M4/M5 implies an exception delta.
10. Wait for all agents. Report which artifacts changed.

---

## `specs-splitter` (new helper)

The inverse of `specs-merger`. A small new agent (or skill if simple enough to inline in the dispatcher) that:

1. Reads `<stem>.specs.md`.
2. Splits it into per-category sections using the same heading conventions `specs-merger` produces.
3. Writes each section to `.specs-tmp/<category>.md`, preserving the exact format `pattern-assigner` and `specs-merger` expect (including any `### Partial Dependencies` subsections, if those are still required by `specs-merger` post-merge — verify).
4. Skips categories listed in the dispatcher's "do not pre-populate" set (i.e. affected categories).

This is purely mechanical — no LLM reasoning required. A Bash + Python or pure-skill implementation is sufficient.

---

## Sidecar updater contracts

### `test-plan-updater`

1. Read `<stem>.updates.md`; collect aggregate-class member changes (M4/M5/L1/L2).
2. Read `<stem>.test-plan.md`.
3. Apply per-type rules:
   - **M4 method added** → add test rows for the new method; if it mutates state, derive new State Keys.
   - **M4 method removed** → delete corresponding test rows and State Keys.
   - **M5 method signature changed** → re-derive State Keys for that method's mutation paths; rewrite test rows.
   - **L1 aggregate added** → invoke `aggregate-tests-planner` for the new class only; splice in.
   - **L2 aggregate removed** → delete its block.
4. Write back.

### `exceptions-updater`

1. Read `<stem>.updates.md`; collect entries that imply exception changes.
2. Read `<stem>.exceptions.md`.
3. Apply per-type rules:
   - **L1 exception class added** → add a new entry, invoke `exceptions-specifier` for it.
   - **L2 exception class removed** → delete its entry.
   - **M4/M5 on aggregates/entities** → re-derive method-to-exception mappings for that class; patch in place.
4. Write back.

---

## Escape hatches

Cases where patching is more brittle than re-generation:

- **C5. First-run / degraded baseline** (HEAD warning) → run full `/generate-specs`.
- **L3. Stereotype changed** (rare) → the changed class appears in the report under both old and new stereotypes; `## Affected Categories` already lists both, and the dispatcher will re-run both category pipelines automatically. No special branch needed.
- **R6. Event rename** with cascade across events + aggregates + repositories → footer already lists all affected categories; dispatcher's normal fan-out handles it.

Most "tricky" cases self-heal because the updates report's footer is designed for exactly this dispatch.

---

## Cost / determinism notes

- Re-running `class-specifier` for an affected category re-specifies all classes in that category, even unchanged ones. LLM nondeterminism could produce trivial wording drift in untouched class blocks.
- Mitigation: pass the *previous* category section of `<stem>.specs.md` to `class-specifier` as a context anchor with the instruction "preserve wording for classes whose structural inputs are unchanged." This requires a small extension to `class-specifier`'s prompt — not a new agent.
- Most reports affect 1–2 categories of typically 3–8 classes each. Cost is comparable to a partial `generate-specs` run.

---

## Implementation order

1. **`specs-splitter` agent** — inverse of `specs-merger`; splits `<stem>.specs.md` back into per-category temp files. Verify it round-trips through `specs-merger` byte-for-byte before relying on it.
2. **`updates-dispatcher` skill** — implement the routing in steps 4–10 above.
3. **`test-plan-updater` agent.**
4. **`exceptions-updater` agent.**
5. **`class-specifier` context-anchor option** — pass previous spec to reduce wording drift on unchanged classes within an affected category.
6. **`/update-specs` slash command** — wires dispatcher into Claude Code.

---

## Open questions

- Does `specs-splitter` need to preserve `### Partial Dependencies` subsections in the temp files, or does `specs-merger` discard them after producing the final `### Dependencies`? If discarded, splitter only needs to emit the class blocks.
- Does `pattern-assigner` need to re-run on pre-populated (unaffected) temp files? It shouldn't — patterns were already assigned in the previous spec — but verify `specs-merger` doesn't require a fresh pattern pass.
- Should the dispatcher write the report to a known location for sidecars to consume, or pass the path as an argument? Argument is simpler.
- Where do prose-only changes to a class fit? Today, `class-specifier` reads prose and bakes invariants into the spec — so re-running the category pipeline already covers prose updates. No separate prose updater needed.
