# Domain Spec Update Types

Analysis of the change shapes emitted by `updates-detector` (see `agents/updates-detector.md` and `skills/updates-report-template/SKILL.md`), grouped by the response a downstream **spec-updater** has to make.

The goal is to enumerate every distinct kind of change the report can carry, so a spec-updater can dispatch the right action per change rather than blindly re-running the full `generate-specs` pipeline.

---

## Update report structure

The report is **class-grouped**. Change axes:

| Axis | Sub-axes | Where it appears |
|---|---|---|
| Class lifecycle | added · removed · stereotype-changed | `## Class Lifecycle` |
| Members | attribute added/removed/changed (type, visibility) · method added/removed/changed (signature) | `## Per-Class Changes` → **Members** |
| Outgoing relationships | added · removed · multiplicity-changed · label-changed | `## Per-Class Changes` → **Relationships** |
| Class-keyed prose | section diff + summary, keyed by `Class` / `Class.method` heading | `## Per-Class Changes` → **Prose — `<heading>`** |
| Orphan relationships | added · removed · changed (source class has no `class` block) | `## Orphan Relationship Changes` |
| Orphan prose | `Preamble`, `Notes`, `Glossary`, free-form sections | `## Orphan Prose Changes` |
| Dispatch hint | category set derived from stereotypes | `## Affected Categories` |

---

## Update types

### 1. Lifecycle updates (whole-class)

- **L1. Class added** — generate a new spec entry from scratch using the assigned category's `class-specifier`.
- **L2. Class removed** — delete the corresponding spec section; sweep `<stem>.exceptions.md` and `<stem>.test-plan.md` for references.
- **L3. Stereotype changed** — spec must be regenerated under the *new* category's template (old block fully discarded). Footer lists *both* old and new categories — both pipelines must run.

### 2. Member updates (in-class, signature-affecting)

- **M1. Attribute added/removed** — patch attribute table; if `<<Aggregate Root>>` / `<<Entity>>`, also revisit Guards/Checks and constructor args.
- **M2. Attribute type changed** — refresh Guard type mapping; check value-object composition.
- **M3. Attribute visibility changed** — encapsulation rules shift; mostly a doc/spec text update.
- **M4. Method added/removed** — spec method list + test plan rows (`aggregate-tests-planner`) must regenerate for that class only.
- **M5. Method signature changed** — spec method entry rewritten; test plan State Keys may need re-derivation if mutation paths shift.

### 3. Relationship updates (cross-class topology)

- **R1. Composition added/removed** (`*--`) — ownership topology change; collection value objects, aggregate boundaries, and persistence mappers all shift. High blast radius.
- **R2. Dependency added/removed** (`-->`) — constructor wiring and DI surface; for `: emits ...` labels this also adds/removes a Domain Event.
- **R3. Realization added/removed** (`--()`) — command handler surface; affects `<<Command>>` dispatch.
- **R4. Inheritance added/removed** (`<|--`) — base class shift; rare but invalidates pattern selection.
- **R5. Multiplicity changed** — cardinality narrative + collection patterns (e.g. `1` → `0..*` flips a single child to a collection VO).
- **R6. Label changed** (e.g. `: emits OrderPlaced` → `: emits OrderConfirmed`) — event-name rename; cascades to event class, repositories, listeners.
- **R7. Orphan relationship change** — no class block to nest under; usually means an inferred `<<Event>>` or `<<Command>>` was added/renamed.

### 4. Prose updates (semantic, not structural)

- **P1. Class-keyed prose changed** (`### Class`) — invariants/responsibilities text updated for that class; refresh narrative section of spec, no structural regen needed.
- **P2. Method-keyed prose changed** (`### Class.method` / `### Class.method(...)`) — preconditions/flow/postconditions for that method; refresh method spec block, possibly regenerate that method's test rows.
- **P3. Orphan prose changed — `Preamble`** — bounded-context overview; refresh aggregate-level intro.
- **P4. Orphan prose changed — free-form** (`Notes`, `Glossary`, etc.) — propagate verbatim; no category dispatch.

### 5. Composite / derived signals

- **C1. Pure prose change, zero structural** — only narrative sections of the existing spec need updating; skip `pattern-assigner`, `scaffold-builder`, `code-implementer`.
- **C2. Pure structural, zero prose** — spec sections regenerate from diagram; existing prose-derived invariants are preserved.
- **C3. Affected Categories empty** — no-op for the spec pipeline (typically only orphan prose changed).
- **C4. Affected Categories spans multiple** (e.g. stereotype change, or new event added via relationship) — multiple specifiers fan out in parallel; merge step must reconcile.
- **C5. First-run / degraded baseline** (HEAD warning emitted) — treat as full generation, not update.

---

## Dispatch tiers for a spec-updater

Three natural tiers fall out of the type list:

1. **Regenerate-from-scratch** — L1, L3, C5
2. **Patch-in-place per class** — L2, M1–M5, P1, P2 (single class block in spec)
3. **Cross-class reconciliation** — R1–R7, C4 (touches multiple spec entries + exceptions + test plan)

Prose-only changes (C1, P3, P4) form a fourth, lighter path that bypasses pattern selection entirely.
