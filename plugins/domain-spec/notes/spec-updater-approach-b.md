# Spec Updater — Approach B (class-keyed splicer over category-wide regen)

This note captures the design for a `spec-updater` that consumes `<stem>.updates.md` (produced by `updates-detector`) and surgically updates the three sibling spec artifacts:

- `<stem>.specs.md`
- `<stem>.exceptions.md`
- `<stem>.test-plan.md`

It is the chosen path among three approaches discussed:

- **A** — Category-scoped full re-run (cheapest to build; clobbers untouched class blocks).
- **B** — Class-keyed splicer over category-wide regen (chosen).
- **C** — Per-class surgical patcher (most code, most precise; duplicates category-specifier logic).

Approach B reuses the existing category-wide specifiers verbatim and adds a thin surgical layer at both ends: prune up front, splice at the end.

---

## Domain shape constraints

These shape the dispatch logic and are load-bearing:

- **At most one `<<Aggregate Root>>` per diagram.** A diagram may carry many `<<Entity>>`, `<<Value Object>>`, `<<TypedDict>>`, `<<Event>>`, `<<Command>>`, `<<Repository>>`, `<<Service>>` classes alongside it.
- **Tests are generated only for the aggregate root.** `aggregate-tests-planner` produces a single `## Aggregate: <Root>` block; entities and VOs are exercised transitively through the root's tests, never directly.
- **The aggregate's blast radius reaches across categories.** Test rows reference composed VO fields (`details.name`), entity state, emitted event names, and TypedDict return shapes. So a change inside any of {aggregates, value-objects, domain-events, data-structures} can invalidate test rows even when the aggregate root's own block is byte-stable.
- **Repositories, services, and commands are *outside* the blast radius.** They invoke the aggregate; the aggregate does not invoke them. Pure repo/service/command changes regenerate their own spec blocks but never trigger a test-plan replan.

---

## Pipeline

```
updates report ──┐
                 ├─► [0] preflight
                 │
diagram ─────────┤
                 ├─► [1] prune removed
                 │
                 ├─► [2] category regen (parallel, only affected categories)
                 │       class-specifier ◷ pattern-assigner per category → temp files
                 │
                 ├─► [3] spec-splicer
                 │       ↳ <stem>.specs.md (touched class blocks only)
                 │
                 ├─► [4] exceptions-specifier (full re-derivation)
                 │       ↳ <stem>.exceptions.md
                 │
                 ├─► [5] aggregate-tests-planner --only <touched aggregates>
                 │       ↳ <stem>.test-plan.md (touched aggregate blocks only)
                 │
                 └─► [6] report
```

---

## Step 0 — Preflight

Parse the report into a working set:

| Variable | Source |
|---|---|
| `removed_classes: { name → stereotype }` | `## Class Lifecycle → Removed` |
| `added_classes: { name → stereotype }` | `## Class Lifecycle → Added` |
| `stereotype_changed: { name → (old, new) }` | `## Class Lifecycle → Stereotype Changed` |
| `touched_classes: set` | headings under `## Per-Class Changes` ∪ all of the above |
| `touched_methods: { class → set(method) }` | Member rows + any `Prose — `Class.method`` headings |
| `affected_categories: set` | `## Affected Categories` |
| `dependencies_dirty: bool` | true iff any relationship change exists (per-class or orphan) or any added/removed class |
| `test_plan_dirty: bool` | true iff `affected_categories ∩ {aggregates, value-objects, domain-events, data-structures}` is non-empty (the aggregate root's blast radius). False for pure repo/service/command-side changes |
| `aggregate_root_removed: bool` | true iff a class with stereotype `<<Aggregate Root>>` appears under `## Class Lifecycle → Removed`, or under `Stereotype Changed` with old stereotype `<<Aggregate Root>>` |
| `degraded_baseline: bool` | true iff Summary contains the `_warning: HEAD ..._` line |

Two early exits and one fallback:

- `affected_categories` empty *and* no orphan relationship/prose entries → no-op (handles update-types **C3**).
- `degraded_baseline` true → fall back to a full `generate-specs` run rather than splicing into a stale baseline (handles **C5**).
- **`stereotype_changed` non-empty → fall back to a full `generate-specs` run** (handles **L3**). Stereotype changes are rare in practice and require the spec body to be rewritten under the new category's template anyway, so the surgical cross-category move isn't worth the complexity. Reusing the C5 fallback machinery costs zero new code in the splicer.

---

## Step 1 — Prune

A `spec-pruner` agent removes traces of `removed_classes` from all three sibling files:

- `<stem>.specs.md`:
  1. The bold `**`ClassName`**` block under its `#### <Category>` header (block runs from the `**` line until the next `**`/`####`/`###`).
  2. Any `### Method: …` block whose method belongs to a removed aggregate (block runs until next `### Method:` or `####`/EOF).
  3. Any line in `### Dependencies` mentioning the class.
- `<stem>.exceptions.md`: any per-class exception block.
- `<stem>.test-plan.md`: if `aggregate_root_removed`, wipe the body (drop the entire `# Test Plan` content). No per-aggregate sweep is needed because the file holds rows for exactly one aggregate root. If the aggregate root was *replaced* (the new root is in `added_classes` or in the new bucket of `stereotype_changed`), Step 5 will rebuild the body from scratch.

Pruning *first* lets the splicer treat the freshly generated category output as authoritative for what survives. Handles **L2**.

---

## Step 2 — Category regen (parallel)

For each `category in affected_categories`, fan out exactly as `generate-specs` does: spawn `class-specifier <diagram> <category>` for all categories in one message, wait, then spawn `pattern-assigner <diagram> <category>` for each in one message.

These already write per-category temp files (`/tmp/...` per the existing agents). The splicer reads from there.

Stereotype-changed classes show up in *both* old and new category temp files (absent from old, present in new) because `affected_categories` lists both — that's the standard footer behavior. Handles **L3**.

---

## Step 3 — Splice (the new agent: `spec-splicer`)

The only nontrivial new piece. Inputs: report, the per-category temp files, current `<stem>.specs.md`.

### Per-class block dispatch

Walk each category temp file in canonical order. For each class block in it, look the class up in the report:

| Class is in… | Action |
|---|---|
| `added_classes` | **Insert** into the matching `#### <Category>` section in `<stem>.specs.md` (alphabetical or temp-file order). |
| `touched_classes` (member/relationship/prose change) | **Replace** the existing block in `<stem>.specs.md`. |
| Not in any of the above | **Skip** — keep the existing block byte-identical. This is the load-bearing rule that protects untouched class spec text from regen drift. |

Stereotype changes are not handled here — Step 0 routes them to the full `generate-specs` fallback before this step runs.

### Per-method block dispatch (aggregate root + entities)

The `#### Aggregate Root / Entities` category section is mixed: it contains the bold class block for the (single) `<<Aggregate Root>>` and one bold class block per `<<Entity>>`. Both kinds of class can declare methods, so the spec also carries `### Method: <signature>` blocks scattered between `### Class Specification` and `### Dependencies`. Each `### Method:` block belongs to whichever owner class declared it (root or entity) — the splicer treats them as part of their owner's "extended block".

For each owner class `C` (root or entity):

- If `C` was **replaced** above → also replace all its `### Method:` blocks with the freshly generated ones. (V1: whole-class method swap, not per-method. Cheaper to implement; the class block already changed, so wholesale method-block refresh is consistent.)
- If `C` is **untouched** → leave its method blocks alone.
- If `C` was **inserted** (new root or new entity) → append its method blocks immediately after its class block, before the next class block or `### Dependencies`.

Optional v2 refinement: per-method swap using `touched_methods[C]` so unchanged methods preserve manual edits.

### `### Dependencies` section

If `dependencies_dirty`, regenerate the entire `### Dependencies` numbered list from scratch by re-parsing the diagram (or by harvesting it from one of the category temp files — they all carry it identically). Otherwise leave it.

This fully handles **R1–R7** and **C2**: relationship changes flow through `dependencies_dirty` and through the touched class blocks of their source classes, but don't unnecessarily re-render unrelated class spec bodies.

---

## Step 4 — Exceptions

Re-run `exceptions-specifier` against the spliced `<stem>.specs.md`. It already operates as pure derivation from the spec — no filter needed, and idempotent on a stable input.

This catches: methods that were added/removed/changed, classes that were added/removed, exception cascades from relationship changes (e.g. a new composition implying new validation paths). The agent will rewrite `<stem>.exceptions.md` end-to-end, but since the input is the surgically-spliced `specs.md`, the output is itself surgically scoped.

---

## Step 5 — Test-plan replan (binary)

Because there is only ever one `<<Aggregate Root>>`, this step has no filter contract — `aggregate-tests-planner` either runs end-to-end or doesn't run at all.

Decision tree:

1. **Aggregate root removed and not replaced.** Step 1 already wiped the body. Skip the planner.
2. **`test_plan_dirty` is true** (i.e. `affected_categories ∩ {aggregates, value-objects, domain-events, data-structures}` is non-empty). Re-run `aggregate-tests-planner` against the spliced `<stem>.specs.md`. It rewrites the whole `# Test Plan` from scratch.
3. **`test_plan_dirty` is false.** Leave `<stem>.test-plan.md` alone — the change was confined to repos/services/commands, which are outside the aggregate's blast radius and cannot affect its unit-test rows.

Why no filter is needed: the planner already regenerates the whole file, and "the whole file" *is* one aggregate. The blast-radius gate (case 3) is what prevents unnecessary churn for repo/service/command-only changes; it replaces the per-aggregate filter that a multi-aggregate world would have needed.

Handles **M4/M5** (root signature changes invalidate rows), **M1–M3** (root attribute changes shift state keys), **R5/R6** (multiplicity / event-name labels appear in `then.events` and state references), **L1/L3** (new or promoted aggregate root gets a fresh plan), and the cross-class blast-radius cases — VO field rename, entity method change, event rename, TypedDict return-shape change — all of which surface in the affected-categories gate without needing per-class bookkeeping.

---

## Step 6 — Report

One sentence: which sibling files were modified, and a one-line "manual review" note if any **P3/P4** orphan prose changes (Preamble, Notes, Glossary) were detected — the spec doesn't currently consume them, so they get surfaced rather than silently swallowed.

---

## Mapping back to `update-types.md`

| Type | Handled by |
|---|---|
| L1 added | Step 2 regen + Step 3 insert + Step 5 (if class lands in blast-radius categories) |
| L2 removed | Step 1 prune + Step 5 (replan if removed class was root or in blast-radius categories; wipe if root removed) |
| L3 stereotype-changed | Step 0 fallback to full `generate-specs` (rare; not worth surgical handling) |
| M1–M3 attribute | Step 2 + Step 3 (replace class block) + Step 5 (if class is in blast-radius categories) |
| M4–M5 method | Step 2 + Step 3 (replace class + method blocks) + Step 5 (if class is in blast-radius categories — root/entity method changes always trigger replan) |
| R1–R6 relationships | `dependencies_dirty` → Step 3 rewrites `### Dependencies`; source class block also rewritten. Step 5 fires only if any endpoint sits in blast-radius categories |
| R7 orphan relationship | Inferred event/command surfaces in `affected_categories`; Step 2+3 regenerate it. Step 5 fires for events; not for commands. Unresolvable orphans surfaced in Step 6 |
| P1 class prose | Step 2 + Step 3 + Step 5 (if class is in blast-radius categories) |
| P2 method prose | Step 2 + Step 3 (method blocks) + Step 5 (if owner class is in blast-radius categories) |
| P3/P4 orphan prose | Step 6 manual-review note |
| C1 pure prose | Same as P1/P2; pattern-assigner re-runs but splicer drops its output for untouched classes |
| C2 pure structural | Same machinery; prose summaries simply absent |
| C3 empty footer | Step 0 early exit |
| C4 multi-category | Step 2 parallel fan-out; Step 5 fires once if *any* affected category is in the blast radius |
| C5 degraded baseline | Step 0 fallback to full `generate-specs` |

---

## Three load-bearing invariants

1. **Pre-prune before regen.** Removals run before category regen so the splicer never has to reconcile a class that exists in `<stem>.specs.md` but not in the temp output.
2. **Untouched classes survive verbatim.** The splicer reads `touched_classes` from the report; classes in a regenerated category but absent from `touched_classes` are *skipped*, not re-written. Without this, every multi-category run would clobber pattern overrides and any human prose edits.
3. **`### Dependencies` is the single global re-derivation.** Cross-class topology lives there; everything else is class-local.

---

## What it deliberately doesn't do

- Doesn't touch the diagram file (Artifacts index already points at stable sibling paths).
- Doesn't track or roll back partial failures across the three sibling files — each step is its own write, and a failure mid-run leaves a clean partial state that re-running the updater on top of unchanged report → diagram is idempotent.
- Doesn't preserve manual edits *inside* a touched class block (that block is wholesale-replaced). Only untouched class blocks are protected.
- Doesn't try to detect renames; the report emits them as remove + add and B handles them that way.

---

## Build order

1. `spec-pruner` agent (Step 1) — small, mechanical, regex-friendly.
2. `spec-splicer` agent (Step 3) — the meaty one; needs the block-detection state machine for class blocks, method blocks, and the `### Dependencies` footer.
3. `update-specs` orchestrator skill — Steps 0–6 wiring, including the blast-radius gate that conditionally re-invokes the existing `aggregate-tests-planner`. No contract change to existing agents.

---

## Complexity hot-spots (for the splicer)

1. **Splice anchor parsing.** Class blocks in `<stem>.specs.md` aren't terminated by an explicit fence — they end where the next `**`ClassName`**` line or next `####`/`###` heading starts. The splicer must implement that block-detection state machine carefully, especially for aggregates where `### Method:` blocks live *between* the class spec and the next class. The `### Method:` blocks for class X belong to X's "extended block" — they end where the next non-Method `###` or `####` starts.

2. **Untouched-class detection.** The splicer needs the `touched_classes` set from the report; for any class in that category's temp output not in the set, it skips the rewrite. Without this, every category re-run would clobber pattern overrides.

3. **`### Dependencies` is global.** It enumerates relationships across all classes. Today it lives at the bottom of `<stem>.specs.md`. If `dependencies_dirty`, regenerate by re-parsing the diagram (the splicer can do this directly, or pull from any one of the temp files since `class-specifier` produces it). Untouched-class skipping doesn't apply here.

(Stereotype-change cleanup is intentionally not on this list — Step 0 routes those rare cases to the full `generate-specs` fallback, so the splicer never has to handle a class that moves between categories.)

---

## Edge cases

- **Manually edited spec body.** If a human added prose that's not in the diagram, the splicer preserves it because it splices at class-block granularity — touched classes are rewritten (manual edits in their block are lost), untouched ones are kept (manual edits preserved). Document this contract.
- **Class renamed.** Updates-detector emits `removed (old) + added (new)` per its rules. Pruner removes old, splicer inserts new. If the renamed class is the aggregate root, an entity, a composed VO, or an emitted event, the blast-radius gate fires and the test plan regenerates from scratch — old test names disappear and new ones replace them. If the rename is in repos/services/commands, no test impact.
- **Aggregate root rename.** Old root in `removed_classes`, new root in `added_classes`. Step 1 wipes the test-plan body, blast-radius gate fires (`aggregates` is affected), `aggregate-tests-planner` rebuilds. Aggregate root *stereotype* demotion (a different scenario — same class, new stereotype) is rare and handled by the L3 fallback to `generate-specs`.
- **Aggregate root unchanged but a composed VO field renamed.** Aggregate root's class block in `<stem>.specs.md` is byte-stable (no member changes there), so the splicer leaves it alone. But `value-objects` is in `affected_categories` → blast-radius gate fires → test plan regenerates because rows referencing `details.<old_name>` are now stale.
- **Two-class change involving both endpoints of a relationship.** Both classes appear in `touched_classes`; both blocks rewrite; no special case.
- **Stereotype changed *and* members changed.** Subsumed by the L3 fallback — Step 0 routes any report with non-empty `stereotype_changed` to a full `generate-specs` re-run, so member changes on the same class are picked up there.
- **Pure repo/service/command change.** Affected categories sit entirely outside the blast radius, so the splicer rewrites their class blocks in `<stem>.specs.md`, exceptions re-derives, and the test plan is left untouched. This is the common-case efficiency win over Approach A.
