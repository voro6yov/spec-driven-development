# Code Updater — Approach C (per-member surgical patcher, hybrid with B)

This note captures the design for a `code-updater` that consumes `<stem>.updates.md` (produced by `updates-detector`) and the **already-updated** sibling spec artifacts (produced by `spec-updater`), and surgically updates the generated domain package and its tests.

It is the chosen path among three approaches discussed:

- **A** — Full `/generate-code` re-run (cheapest to build; clobbers every hand-edit anywhere in the package).
- **B** — Module-keyed splicer (whole-module regen for touched classes; preserves untouched modules).
- **C** — Per-member surgical patcher over **B** (chosen as a hybrid: C where hand-edit preservation matters, B everywhere else).

The chosen shape is **hybrid B+C**: B for the small, mechanical class types (value objects, entities, domain events, commands, repositories, services); C for the artifacts where hand-tuning happens at scale (aggregate root code, fixtures, tests). This caps new machinery to one CST parser plus a small family of per-member agents while paying the surgical-precision cost only where it matters.

This note is a parallel to `spec-updater-approach-b.md`. It assumes the spec-updater has already run and that `<stem>.specs.md`, `<stem>.exceptions.md`, and `<stem>.test-plan.md` reflect the current diagram; the code-updater's job is to propagate those onto disk.

---

## Domain shape constraints

The same shape constraints from spec-updater carry over (one aggregate root per diagram; tests target only the root; aggregate blast radius spans aggregates/value-objects/domain-events/data-structures; repos/services/commands are outside the blast radius). On top of those, code has its own structural facts:

- **One file per class is the dominant layout** (`/scaffold-builder` emits one `<snake>.py` per class). VO modules occasionally group multiple value objects per `domain-spec:package-layout`. The splicer must handle both: whole-module dispatch for single-class modules, class-block dispatch for grouped modules.
- **The aggregate root file is the largest and most hand-edited**. Many methods, often with hand-tuned event-emission ordering, validation order, or retry decoration. This is where C earns its keep.
- **Test files mirror the test-plan rows one-for-one.** Each row in the Tests table maps to one `def test_<name>(...)` function. Fixture names follow `<snake>_N` per State Keys table. Both anchors are stable enough for per-function surgery.
- **`__init__.py` exports are derivable, not hand-edited.** They get regenerated wholesale from the current class set. This is the analog of `### Dependencies` in spec-updater.
- **Cross-module imports can dangle even in untouched modules.** When a class is removed or renamed, every file that referenced it needs an import patch — even files whose own class spec was byte-stable. This requires a global wiring sweep, not just touched-module work.
- **`exceptions.py` is a single grouped module** (one file, N exception classes). It's regenerated end-to-end from the updated `<stem>.exceptions.md`, same as spec-updater Step 4.

---

## Pipeline

```
updates report ──┐
                 │
specs (updated) ─┤
                 ├─► [0] preflight
                 │
                 ├─► [1] code-pruner
                 │       (whole-module deletes for removed classes;
                 │        per-member deletes for removed methods/attributes)
                 │
                 ├─► [2] scaffold-builder --only <added_classes>
                 │
                 ├─► [3] per-class dispatch (parallel)
                 │       ├─ added class            → code-implementer (whole-module gen)
                 │       ├─ touched, B-eligible    → code-implementer (whole-module regen)
                 │       └─ touched, C-required    → code-method-splicer (per-member surgery)
                 │
                 ├─► [4] exceptions-implementer (full re-derivation)
                 │
                 ├─► [5] tests blast-radius gate
                 │       ├─ per-fixture splicer    (State Keys diff)
                 │       └─ per-test splicer       (Tests table diff)
                 │
                 ├─► [6] import-reconciler (global wiring sweep)
                 │
                 ├─► [7] formatter pass (ruff/black)
                 │
                 └─► [8] report
```

---

## Step 0 — Preflight

Parse the report into a working set:

| Variable | Source |
|---|---|
| `removed_classes: { name → stereotype }` | `## Class Lifecycle → Removed` |
| `added_classes: { name → stereotype }` | `## Class Lifecycle → Added` |
| `stereotype_changed: { name → (old, new) }` | `## Class Lifecycle → Stereotype Changed` |
| `touched_classes: set` | `## Per-Class Changes` headings ∪ all of the above |
| `touched_methods: { class → set(method) }` | Member rows + ``Class.method`` prose headings |
| `touched_attributes: { class → set(attr) }` | Member rows scoped to attribute kind |
| `affected_categories: set` | `## Affected Categories` |
| `imports_dirty: bool` | true iff any class added/removed/renamed, or any relationship change |
| `test_plan_dirty: bool` | true iff `affected_categories ∩ {aggregates, value-objects, domain-events, data-structures}` is non-empty |
| `aggregate_root_removed: bool` | as in spec-updater |
| `degraded_baseline: bool` | true iff Summary contains the `_warning: HEAD ..._` line |

Three early exits / fallbacks:

- `affected_categories` empty *and* no orphan relationship/prose entries → no-op (handles **C3**).
- `degraded_baseline` true → fall back to a full `/generate-code` run (handles **C5**).
- `stereotype_changed` non-empty → fall back to `/generate-code` (handles **L3**, same rationale as spec-updater).

A fourth gate — the **hand-edit policy gate** — runs per touched module. Each generated file carries (or has had attached) a `last-generated` baseline; if the on-disk content diverges from it for a class that's about to be regenerated wholesale (B-eligible touch), surface a warning and *skip* the rewrite of its body, rather than clobbering. Per-member surgery (C-required touch) is exempt from this gate at the file level — it only touches the specific members marked dirty, and it preserves all other members verbatim by construction.

---

## Step 1 — Prune

A `code-pruner` agent removes traces of removed entities. Two granularities:

**Whole-class removal** (class in `removed_classes`):

- Single-class module → delete the `.py` file.
- Grouped module → delete that class's class block (anchored by `class <Name>`/the next `class ` or EOF).
- `exceptions.py` → delete subclasses owned by that class.
- `tests/conftest.py` → delete all `<snake>_N` fixtures and any data fixtures owned by the class.
- Test file → delete the entire `test_<class>.py` (or class's test-function group inside a grouped test file).
- `__init__.py` → drop the symbol from `__all__` and from any `from .module import Name` line.

**Per-member removal** (method/attribute in `removed_methods` / `removed_attributes`, class itself surviving):

- Use `code-block-analyzer` (see Step 3) to find the AST node.
- Delete the node + its decorator stack + the trailing blank line that separates it from the next member.
- For attributes implemented as Guard descriptors, also remove the corresponding `__init__` validation line (named anchor: the parameter name).

Pruning *first* lets the per-class dispatch in Step 3 treat the rest of disk content as the authoritative baseline.

---

## Step 2 — Scaffold added classes

For each class in `added_classes`, run `scaffold-builder` scoped to just that class. Emits the spec docstring stub (with the freshly written class spec embedded) plus skeleton imports for declared collaborators. Step 3 then implements it like a normal `/generate-code` run.

Touched classes do **not** re-scaffold; their existing module already has the embedded spec docstring (which was either updated at scaffold time or is now stale — the docstring is informational only and Step 3 reads from the sibling `<stem>.specs.md` directly).

---

## Step 3 — Per-class dispatch

Triage rule for each class in `touched_classes`:

| Class type | Approach | Why |
|---|---|---|
| Aggregate root | **C** (method-splicer) | Many methods; hand-tuning is common; whole-module regen would be destructive. |
| Value object, entity, domain event, command, TypedDict, repository ABC, service ABC | **B** (whole-module regen via `code-implementer`) | Small files, mostly mechanical bodies, low hand-edit surface. |

Added classes always run via `code-implementer` (whole-module gen, since there's nothing to preserve).

### B-eligible: whole-module regen

Identical to the existing `code-implementer` invocation per module. Reads the scaffolded module + the class's spec block from `<stem>.specs.md`, emits a complete implementation, writes the file. Hand-edits in the body are lost — same contract as the spec-updater's "touched class block is wholesale-replaced" rule.

### C-required: per-member surgery (`code-method-splicer`)

The new agent. Inputs: the touched class's spec block, the existing module file on disk, `touched_methods[C]`, `touched_attributes[C]`.

**Per-member dispatch table** (the heart of C):

| Member is in… | Action |
|---|---|
| `added_methods[C]` / `added_attributes[C]` | **Insert** at the deterministic anchor (see ordering rule below) |
| `touched_methods[C]` / `touched_attributes[C]` | **Replace** the existing AST node with freshly generated code |
| Already removed by Step 1 | n/a |
| Member present on disk, not in any of the above | **Skip** — preserve byte-stable, including any hand edits |

The fresh code for a single member comes from a new `method-implementer` agent that reads:

- The method's `### Method:` block from `<stem>.specs.md` (or the attribute's row in the class spec).
- The class-level context visible in the rest of the module (so it knows which guards/collaborators are already imported).
- The same pattern skills as `code-implementer`, but scoped to one-method output (`aggregate-root`, `delegation-and-event-propagation`, etc.).

**`__init__` is special.** Whenever any attribute changes (added, removed, type changed), `__init__` is treated as touched and regenerated whole-method. Per-line surgery inside `__init__` is too fragile — humans tune validation order, but the regen-on-attr-change contract is unavoidable to keep guards consistent with the spec.

**Anchor ordering rule for inserts:** members appear in the order they're declared in the class spec block. New methods land at the position implied by the spec's order. Decorator stacks (`@property`, `@classmethod`, `@retry_on_transaction_error`, etc.) are part of the inserted block.

**CST dependency.** Block detection and round-trip must use a concrete-syntax-tree library (LibCST or parso). Regex doesn't survive decorators, multi-line signatures, or nested f-strings; `ast.unparse` discards formatting and breaks idempotency on untouched files.

---

## Step 4 — Exceptions

Re-run `exceptions-implementer` end-to-end against the updated `<stem>.exceptions.md`. Idempotent on stable input, so this is the safe wholesale path. Catches: methods that newly raise, classes added/removed, exception cascades from new validation paths.

(Identical pattern to spec-updater Step 4.)

---

## Step 5 — Tests blast-radius gate

Three cases, mirroring spec-updater Step 5 but with surgical sub-steps:

1. **Aggregate root removed and not replaced.** Delete the test file and wipe the aggregate's fixtures from `tests/conftest.py`.
2. **`test_plan_dirty` is true.** Run two surgical splicers in sequence:
   - **Per-fixture splicer.** Diff the State Keys table in `<stem>.test-plan.md` against the current `tests/conftest.py`. Insert/replace/delete fixtures keyed by `<snake>_N` function name. Untouched fixtures preserve hand edits (e.g. tweaked test data). Same dispatch table as the per-member rule.
   - **Per-test splicer.** Diff the Tests table against the current test file. Insert/replace/delete `def test_<name>(...)` functions keyed by name. Untouched test functions preserve hand-tuned assertions.
3. **`test_plan_dirty` is false.** Leave fixtures and tests alone — change was confined to repos/services/commands.

Why per-test surgery is required (whereas spec-updater Step 5 just regenerates the whole test plan): the test-plan markdown is templated and predictable, but generated test *bodies* tend to be hand-tuned with extra assertions, comments narrating the test, or temporary `print`s that are surprisingly hard to recreate. Whole-file regen is too destructive in practice.

---

## Step 6 — Import reconciler (global)

Walk every `.py` module in the package. For each module:

- Compute the canonical import set from the updated spec (collaborator references in the class block + exceptions raised + Guard types).
- Remove imports referencing classes that no longer exist (orphans from removals/renames).
- Add imports for collaborators that the spec now references but the module doesn't import.
- Re-derive `<package>/__init__.py` exports (`__all__` and `from .module import Name` lines) from the current class set.

This is the global pass — analog of spec-updater's `### Dependencies` rebuild. It runs after Step 3 because Step 3's surgical splices may emit code that uses a new collaborator without yet importing it.

Idempotent. Untouched modules whose imports are still correct are read but not written.

---

## Step 7 — Formatter pass

Run `ruff format` (or `black`) over the package. Surgical splices and per-member inserts can leave inconsistent blank-line counts even when each splice is locally clean; the formatter normalizes them. This step is **not optional** — without it the diff between two consecutive idempotent runs may show whitespace-only changes, which breaks the "rerunning on top of unchanged report → diagram is idempotent" invariant.

---

## Step 8 — Report

One paragraph naming the modified files. Manual-review notes for:

- **Hand-edit conflicts:** any B-eligible touched module whose body diverged from baseline and was therefore *skipped* in Step 3. The user must reconcile manually.
- **Orphan prose** (P3/P4 from updates report): same as spec-updater — surfaced, not silently swallowed.
- **Import reconciler patches** to untouched modules — call them out so a reviewer can spot accidental over-reach.

---

## C1 vs. C2 — sub-choice within C

There are two ways to actually perform the per-member surgery:

- **C1 — AST extract + targeted regen.** Find the LibCST node for the touched member, generate a fresh body via `method-implementer`, replace the node. No baseline needed. Cheaper. **Choice for v1.**
- **C2 — Whole-class regen + 3-way merge.** Regenerate the whole class as if from scratch, then merge against the on-disk version using the *previous generated* version as base. Conflicts surface as `<<<<<<<` markers. Cleaner conceptually, but requires a stable baseline that doesn't reliably exist after humans edit files. Footnote.

C1 is the realistic shape of "approach C". C2 is recorded here for completeness only.

---

## Hybrid B+C boundary — what falls where

| Artifact | Approach | Reason |
|---|---|---|
| Aggregate root module | **C** (per-method surgery) | Many methods, frequent hand-tuning |
| Value object module | B (whole-module regen) | Small, mechanical |
| Entity module | B | Small, mechanical |
| Domain event module | B | Tiny, near-pure data |
| Command module | B | Tiny, near-pure data |
| TypedDict / data structure | B | Tiny, near-pure data |
| Repository ABC | B | Mostly signatures |
| Service ABC | B | Mostly signatures |
| `exceptions.py` | B (full re-derivation) | Trivially deterministic |
| `__init__.py` exports | B (re-derived globally in Step 6) | Pure projection of class set |
| Aggregate fixtures (`<snake>_N`) | **C** (per-fixture surgery) | Hand-tuned test data |
| Aggregate tests (`test_<name>`) | **C** (per-test surgery) | Hand-tuned assertions |

This hybrid caps the new machinery: one CST anchor parser, one `method-implementer` agent, one `code-method-splicer`, two test-side splicers (per-fixture, per-test), one global `import-reconciler`. Adopt full C across the whole package later only if the contract proves itself.

---

## Mapping back to `update-types.md`

| Type | Handled by |
|---|---|
| L1 added | Step 2 scaffold + Step 3 whole-module gen + Step 5 (if test-plan changed) |
| L2 removed | Step 1 prune (whole-class) + Step 5 (wipe if root) |
| L3 stereotype-changed | Step 0 fallback to full `/generate-code` |
| M1–M3 attribute | Step 3 (B: whole-module regen; C: `__init__` whole-method + per-attribute Guard splice) + Step 5 |
| M4–M5 method | Step 3 (B: whole-module regen; C: per-method splice) + Step 5 |
| R1–R6 relationships | `imports_dirty` → Step 6 import sweep; source class block also rewritten in Step 3 |
| R7 orphan relationship | Inferred event/command surfaces in `affected_categories`; Step 3 regenerates. Step 5 fires for events; not for commands |
| P1 class prose | Step 3 (B regenerates the file; C may skip if prose-only and no member changed — see edge cases) |
| P2 method prose | Step 3 (C: per-method splice if method's prose says behavior changed; otherwise skip) |
| P3/P4 orphan prose | Step 8 manual-review note |
| C1 pure prose | Same as P1/P2 |
| C2 pure structural | Same machinery; prose summaries simply absent |
| C3 empty footer | Step 0 early exit |
| C4 multi-category | Step 3 parallel fan-out; Step 5 fires once if blast-radius hit |
| C5 degraded baseline | Step 0 fallback to `/generate-code` |

---

## Five load-bearing invariants

1. **Pre-prune before regen.** Removals run before per-class dispatch so the splicer never has to reconcile a class that exists on disk but not in the updated spec.
2. **Untouched members survive verbatim.** The C splicer reads `touched_methods` / `touched_attributes` from the report; members in a touched class but absent from those sets are *skipped*, not rewritten. This is the load-bearing rule that protects hand-tuned method bodies.
3. **Untouched B-eligible modules with hand-edits are skipped, not clobbered.** The Step 0 hand-edit gate gives B-eligible modules an opt-out when the on-disk content has diverged from baseline. The user resolves manually.
4. **Imports are the single global re-derivation.** Cross-module wiring lives in Step 6; everything else is module-local or member-local.
5. **CST round-trip preserves formatting.** Block detection uses LibCST so that splicing one method doesn't perturb the whitespace or comments of any other member in the same file.

---

## What it deliberately doesn't do

- Doesn't touch the diagram or the spec siblings — those are inputs (already updated by `spec-updater`).
- Doesn't track or roll back partial failures across the package — each step is its own write, and a failure mid-run leaves a clean partial state that is idempotent under re-run.
- Doesn't preserve hand edits *inside* a member that was actually touched (that member is wholesale-replaced). Only untouched members are protected.
- Doesn't try to detect renames; the report emits them as remove + add and the pipeline handles them that way (Step 1 prunes the old, Step 2 scaffolds the new, Step 6 patches all incoming references).
- Doesn't enforce a baseline tracking scheme beyond "compare the on-disk file content to the most recent generated content". A `last-generated` cache file or git-blame heuristic is fine; the spec is intentionally loose here.
- Doesn't run pytest or any verifier — out of scope. The orchestrator emits a report; the user runs tests.

---

## Build order

1. **`code-block-analyzer`** (LibCST-based) — the foundation. Returns a structured anchor table for any Python module: `(name, kind, decorators, line_start, line_end)` per method/attribute/class. Reused by pruner, splicer, and import-reconciler.
2. **`code-pruner`** — small, mechanical, drives whole-class deletes and (via the analyzer) per-member deletes.
3. **`method-implementer`** — single-method generation agent. Mirrors `code-implementer` but scoped to one method body.
4. **`code-method-splicer`** — drives the per-member dispatch table for C-required classes.
5. **`fixture-splicer`** and **`test-splicer`** — analogs for `tests/conftest.py` and the test files. Same per-named-block surgery, different anchors.
6. **`import-reconciler`** — global module sweep + `__init__.py` re-derivation.
7. **`update-code` orchestrator skill** — Steps 0–8 wiring, including the test blast-radius gate. Companion to the spec-side `update-specs` orchestrator.

---

## Complexity hot-spots

1. **CST round-trip preserving formatting.** LibCST is the right tool but has a learning curve; preserve trivia (whitespace and comments attached to nodes) carefully.
2. **Decorator-aware block boundaries.** A method's "block" includes its decorator stack. The analyzer must attribute decorators to the function below, not the function above.
3. **Anchor rule for new method inserts.** Spec-order is the chosen rule; the analyzer must surface the existing on-disk order so the splicer can interleave correctly. Edge case: the spec adds a method between two existing ones — splicer must insert at the right position rather than appending.
4. **Per-test / per-fixture anchor stability.** Test function names should not be silently renamed in the test plan, because the splicer keys off them. If a Tests row's name changes, the diff looks like remove-old + add-new — acceptable, but hand-tuned assertions in the old test are lost. Document this contract.
5. **`__init__` whole-method regen on attribute change.** No way around it — guards must stay consistent with the spec — but it's the one place where C still loses hand-tuned validation order. Document it.

---

## Edge cases

- **Empty class body.** A class added to the diagram with no members yet — scaffold-builder emits a `pass` placeholder; subsequent runs add members via the per-member dispatch.
- **Class renamed (rename = remove + add).** Pruner deletes old module/fixtures/tests; scaffolder + code-implementer create new; import-reconciler patches references in untouched modules. If the renamed class is the aggregate root, an entity, a composed VO, or an emitted event, the test-plan blast-radius gate fires and the test file regenerates wholesale via the per-test splicer (most rows new, old rows removed).
- **Aggregate root rename.** Step 1 wipes the test file + fixtures, Step 5 rebuilds them from the new test plan.
- **Pure-prose-only class diff.** Class is in `touched_classes` because of P1 prose, but no member changed. Step 3 contract: skip the file entirely. Spec text isn't load-bearing for code. (For B-eligible classes, this means we'd otherwise re-run `code-implementer` and clobber for nothing — explicit early-skip avoids that.)
- **Two-class change involving both endpoints of a relationship.** Both classes appear in `touched_classes`; both modules processed by Step 3 (B or C as appropriate); Step 6 fixes any imports.
- **Stereotype changed *and* members changed.** Subsumed by the L3 fallback to `/generate-code`.
- **Pure repo/service/command change.** Affected categories sit entirely outside the blast radius. Step 3 regenerates those modules (B-eligible), Step 4 re-derives exceptions, Step 5 leaves tests alone, Step 6 patches imports. This is the common-case efficiency win.
- **Hand-edited test body that the diff says is untouched.** Preserved verbatim by per-test splicer.
- **Hand-edited test body that the diff says IS touched.** Lost on regen — consistent with the touched-member contract. Document this in the test-splicer contract.
- **Hand-edited B-eligible module body when its class is touched.** Step 0 hand-edit gate skips the file and surfaces a manual-review note in Step 8. The user reconciles.
- **Module-level helper functions.** Rare but possible (e.g. a free-floating `_validate_x` helper). Treated as named blocks by the analyzer with kind `function`; per-member surgery applies the same way.
