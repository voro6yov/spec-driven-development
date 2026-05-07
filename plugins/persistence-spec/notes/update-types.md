# Persistence Spec Update Types

Analysis of how every kind of domain-diagram delta — as emitted by `domain-spec:updates-detector` into `<stem>.updates.md` — ripples into the **command-repo-spec** sibling (`command-repo-spec-template` Sections 1 / 2 / 3).

The goal is to enumerate every distinct kind of change a persistence-spec updater would have to handle, so it can dispatch the right action per change rather than re-running `/persistence-spec:generate-specs` from scratch and clobbering hand-edits in pattern selection or schema notes.

This is the persistence-side analog of `plugins/domain-spec/notes/update-types.md`. It assumes the domain `<stem>.updates.md` is already produced; the persistence updater consumes it directly rather than re-diffing the diagram.

---

## Persistence spec sections and their sensitivity

The command-repo-spec has three sections, each with a different sensitivity to domain-side changes:

| Section | Owner agent | Sensitive to |
|---|---|---|
| **§1 Aggregate Analysis** — root name, has-children, multi-tenant flag, JSONB VOs, polymorphism flag | `command-repo-spec-pattern-selector` | Aggregate *shape* (which classes exist and how they relate) |
| **§2 Pattern Selection** — Tables, Migrations, Mappers, Repository, Alternative Lookups, Context Integration | `command-repo-spec-pattern-selector` | Aggregate shape **plus** repository finder set |
| **§3 Schema Specification** — ER diagram, column lists, indexes | `command-repo-spec-schema-writer` | Field-level changes on root, entities, and flat-column VOs |

Section ownership is already split across two writer agents, which makes section-scoped regeneration mechanically cheap — re-run the writer that owns the affected section.

The downstream persistence artifacts (`tables/`, `migrations/`, `mappers/`, `command_<aggregate>_repository.py`, repo tests) are owned by `/persistence-spec:generate-code`. They are *out of scope* for the spec updater — the spec is the source of truth and code regeneration is its own concern (analogous to `notes/code-updater-approach-c.md` on the domain side).

---

## Domain shape constraints

Load-bearing facts about how persistence relates to the domain diagram:

- **The domain diagram is the single source of truth.** The persistence spec is a derived artifact; there is no second diagram to diff. The trigger for a persistence update is therefore `<stem>.updates.md`, not a separate persistence diff.
- **Exactly one `<<Aggregate Root>>` per diagram.** The same invariant the domain updater leans on. Removal of the root is malformed; stereotype change of the root requires a full regen.
- **Domain `<<Event>>` and `<<Command>>` classes do not persist.** They are emitted / dispatched. A pure event-or-command change in the domain footer means the persistence spec is byte-stable — the updater can early-exit.
- **Repository ABCs are domain-owned.** The `<<Repository>>` interface lives in the domain diagram; the persistence spec selects an implementation pattern and lists alternative lookups that mirror its abstract finders. Finder churn on the ABC is a category that *does* affect the persistence spec.

---

## Mapping `affected_categories` → persistence impact

Per the canonical category order from `domain-spec:updates-report-template`:

### 1. `data-structures` (`<<TypedDict>>`)

Mostly a query-side concern. Command-side persistence impact is narrow but real:

- **TypedDict used as a repository finder return type** — column projection in §3, possibly an index on the projected columns.
- **TypedDict consumed by a flat-constructor / factory** that maps repository rows to aggregates — affects mapper hydration order in §2.
- Any other TypedDict change is byte-neutral for command-side persistence.

### 2. `value-objects` (`<<Value Object>>`)

The single highest-impact category for command-side persistence. Shape and field changes all land here:

- **VO added on the root** → new `<VO>Mapper` row in §2.Mappers (variant: Simple / Complex / Collection / Polymorphic), new flat columns *or* a JSONB column in §3, new "Add column" or "Add JSONB column" migration changeset in §2.
- **VO removed** → drop mapper row, drop columns, drop migration. Destructive on populated tables — see *Out-of-scope* below.
- **VO field added / removed / typed** → flat-column add/drop/alter (with migration) or JSONB shape note (no migration). Nullability flips when a field becomes optional.
- **VO becomes polymorphic** (subtype branches appear) → §1 polymorphism flag flips, mapper variant flips to *Polymorphic Value Object Mapper*, schema gains a discriminator column.
- **Collection VO added on the root** → may promote what was a flat column into a child table with FK. §2 repo pattern flips Simple → With Children. §3 gains a child table block.

### 3. `domain-events` (`<<Event>>`)

**No command-side persistence impact today.** Skip the category at dispatch time.

(If an event-store pattern is ever added, this row changes.)

### 4. `commands` (`<<Command>>`)

**No persistence impact.** Domain `Command` dataclasses are message-bus payloads. Skip.

### 5. `aggregates` (`<<Aggregate Root>>`, `<<Entity>>`)

The largest blast radius — touches every section:

- **Root attribute add / remove / type** → §3 column row, §2 migration row, mapper row update.
- **Root gains / loses `tenant_id`** → §1 multi-tenant flag flips, §2 Table pattern flips Simple ↔ Composite PK, Migration flips, Repository pattern flips, every Alternative Lookup gains/loses a tenant arg.
- **Entity added (new child)** → §1 has-children flag flips on, §2 gains `<Child>Table` (with FK) / `Add Foreign Key` migration / `<Child>EntityMapper` rows, repository flips Simple → With Children, §3 gains a child table block + an FK index.
- **Entity removed** → mirror of "added"; the most destructive case, since it implies dropping a child table on a populated database. Strong candidate for hard-fail.
- **Multiplicity flip on a relationship** (`"1"` → `"0..*"` or vice versa) → restructures column-vs-child-table and shifts mapper variant.
- **Status / Statuses field change on the root** → status column add/alter, possibly a partial index for active rows.
- **Aggregate root removal** → hard-fail (mirror of `update-specs` 1c).
- **Aggregate root stereotype change** → hard-fail (mirror of `update-specs` 1b).

### 6. `repositories-services` (`<<Repository>>`, `<<Service>>`)

Narrow, targeted impact:

- **Finder added / removed / signature changed** on the abstract command repository → §2 *Alternative Lookups* bullet list updates; §3 Indexes table gains/drops a row; downstream repo tests (out of spec scope) need a regen.
- **Service interface change** → no command-side persistence impact (services are not persisted). Query-context wiring may need a re-run if it is a *query* interface — but that is a query-spec concern, not command-repo-spec.

---

## Cross-cutting shape-change detector

Independent of category, certain shape deltas should force a §1 + §2 regeneration even when only one domain category is in the footer. These are the *pattern-flipping* changes:

| Shape signal | Detection (from `<stem>.updates.md`) | Effect |
|---|---|---|
| Multi-tenancy gained | `+tenant_id: <Type>` attribute on the root | Re-run §1 + §2 (Table → Composite PK, Repository pattern flip, Alt Lookups gain tenant arg) |
| Multi-tenancy lost | `-tenant_id` attribute on the root | Re-run §1 + §2 (mirror); flag as destructive |
| Children gained | New `<<Entity>>` listed under `## Class Lifecycle → Added`, **or** new `*--` relationship from the root | Re-run §1 + §2; §3 gains a child table block |
| Children lost | `<<Entity>>` removed, **or** `*--` relationship removed | Mirror; flag as destructive |
| Polymorphism gained | New subtype branches in the diagram (additional classes inheriting from a VO/Entity) | Mapper variant flips Polymorphic; §1 polymorphism flag flips |
| JSONB VO added/removed | Non-trivial `<<Value Object>>` add/remove on the root | §1 JSONB cell, §2 mapper row, §3 column |

These could be a single "shape-change detector" pass that runs over the report and emits a `shape_changed: bool` plus a small `triggers: set[str]` used to gate which sections regenerate. The detector is small enough to live inside the orchestrator skill rather than its own agent.

---

## Three approaches for the persistence updater skill

Roughly increasing in surgical precision, decreasing in implementation cost. Same A/B/C framing used in `plugins/domain-spec/notes/spec-updater-approach-b.md`:

### Approach A — Whole-spec regen, gated

If `affected_categories ∩ {data-structures, value-objects, aggregates, repositories-services}` is non-empty, re-run `command-repo-spec-pattern-selector` and `command-repo-spec-schema-writer` against the existing scaffolded spec.

- **Pro:** trivial to implement; reuses existing agents verbatim.
- **Con:** clobbers any manual edits inside §2 (e.g. hand-tuned alternative lookups) or §3 (e.g. hand-authored index entries).
- **Pro:** zero new agents; the whole skill is ~30 lines of dispatch.

### Approach B — Section-scoped regen (recommended first cut)

Map each affected category to a subset of {§1, §2, §3} and re-run only the writer agent that owns that section. Splice section-by-section back into the existing spec file.

| Trigger | Sections to regenerate |
|---|---|
| `value-objects` (VO add/remove/typed) | §1, §2, §3 |
| `aggregates` (root attr / entity / multiplicity) | §1, §2, §3 |
| `repositories-services` (finder churn only) | §2 (Alt Lookups), §3 (Indexes) — **skip §1** |
| `data-structures` (finder return-type only) | §3 (column projections) — **skip §1, §2** |
| Shape-change detector signals | §1 + §2 always |

- **Pro:** preserves manual edits in untouched sections.
- **Pro:** mechanically cheap — three sections × two existing writer agents already exist; the splice is a heading-bounded `Edit` call per section.
- **Con:** still wholesale-replaces a section when any of its rows change; doesn't preserve hand-edits within a regenerated section.

### Approach C — Splicer-style surgical edits

Mirror the domain `update-specs` model exactly: add a `command-repo-spec-pruner` that strips rows for removed classes (mapper row for a removed VO, column row for a removed attribute, migration changeset for a dropped column, alt lookup for a removed finder) and a `command-repo-spec-splicer` that adds/replaces rows for added/changed ones.

- **Pro:** highest fidelity; preserves hand-edits at row granularity.
- **Con:** requires duplicating the row-shape knowledge already encoded in the pattern-selector and schema-writer agents.
- **Con:** shape-flip cases (multi-tenancy gained, children gained) still demand whole-section regen, so the splicer handles only the easy cases anyway.

**Recommendation:** start with **B**. The three sections × two writer agents make section-scoped regeneration the cheapest precision-preserving option. Graduate to C for §3 column rows only if manual edits there start mattering in practice.

---

## Hard-fail conditions

Mirror the domain `update-specs` failure semantics:

- **Aggregate root removal** in `## Class Lifecycle → Removed` — hard-fail. Cannot prune the root from a persistence spec without invalidating the whole spec.
- **Aggregate root stereotype change** in `## Class Lifecycle → Stereotype Changed` — hard-fail. Whole pattern catalog re-applies; route to `/persistence-spec:generate-specs`.
- **Degraded baseline** (`_warning: HEAD ...` line in the report Summary) — hard-fail. Same reason as domain.
- **Multi-tenancy flip + children flip in the same diff** — *optional* hard-fail. The shape change is large enough that regeneration from scratch is safer than splicing two pattern flips simultaneously. Worth a flag, not necessarily a default.

Each failure should print exactly one `ERROR:` line and exit, with text directing the operator to `/persistence-spec:generate-specs <diagram_file>`.

---

## Out-of-scope but worth flagging to the operator

These belong in operator-facing warnings, not in the spec content itself:

- **Migration safety.** A "drop column" migration on a populated table is destructive; the updater should *propose* the changeset row but warn that the operator must hand-author the data-preserving migration. Same for column type changes and attribute renames (which today look like add+remove in the report).
- **Index churn.** Removing a finder removes a row from §3 Indexes, but the underlying index is real in the database; the migration list should grow a `Drop Index` changeset, not just shrink the §3 table.
- **Tenant column removal.** Going Composite PK → Simple Table is data-destructive even if every tenant has the same value. Flag it; do not silently flip the pattern.
- **Query-side ripple.** Today the command-repo-spec is the only persistence spec. If TypedDict / DTO shapes change and a query repository projects them, that is a separate concern — worth a future `/update-query-specs` rather than overloading this skill.
- **Code regen.** This skill stops at the spec. Downstream tables, migrations, mappers, and repos are owned by `/persistence-spec:generate-code` (or its eventual surgical updater).

---

## Pipeline sketch (Approach B)

```
<stem>.updates.md ──┐
                    ├─► [0] preflight (parse footer, lifecycle, summary)
                    │       ↳ hard-fail on degraded baseline
                    │       ↳ hard-fail on root removal / stereotype change
                    │       ↳ early-exit if affected_categories ⊆ {domain-events, commands}
                    │
<stem>.command-repo-spec.md ─┤
                    │
                    ├─► [1] shape-change detector
                    │       ↳ scan report for tenant flip / children flip / polymorphism flip
                    │       ↳ produce {triggers, shape_changed}
                    │
                    ├─► [2] dispatch matrix
                    │       categories + triggers → set of sections {§1, §2, §3}
                    │
                    ├─► [3] section-scoped regen
                    │       §1 + §2 → re-run command-repo-spec-pattern-selector
                    │       §3      → re-run command-repo-spec-schema-writer
                    │       (writers operate against the existing scaffold)
                    │
                    ├─► [4] splice
                    │       replace each regenerated section in <stem>.command-repo-spec.md
                    │       by H2-heading bounds; preserve all other content byte-identical
                    │
                    └─► [5] report
                            "Updated <stem>.command-repo-spec.md (sections: §1, §2)"
```

Steps 0–2 are pure parsing and live in the orchestrator skill body. Step 3 is the only step that fans out to existing agents (and only ever to two of them, so parallelism is not necessary). Step 4 is a heading-bounded `Edit` per regenerated section.

---

## Open questions

- **What is the actual filename of the persistence spec sibling?** Need to confirm whether `command-repo-spec-scaffolder` writes `<stem>.command-repo-spec.md`, `<stem>.persistence-spec.md`, or something else. The pipeline sketch assumes `<stem>.command-repo-spec.md`.
- **Should the updater touch the query-context spec too?** Today there is no query-context spec file; query repos are inferred from the command-repo-spec. If a query-spec file is ever introduced, this skill grows a second target.
- **Should shape-change detection live in `domain-spec:updates-detector` or in the persistence updater?** Today the report does not flag tenant-flip / children-flip explicitly — the persistence updater would have to derive them from member and relationship deltas. A small enrichment of the report (e.g. a `## Persistence-Relevant Shape Changes` section) might be worth it if a REST-API updater later needs the same signals.
- **Hand-edit preservation in §3 Indexes.** Indexes today are partly derived (one per finder) and partly hand-authored (operator-tuned indexes for known query patterns). A whole-section regen of §3 will lose hand-tuned index rows. This is the strongest argument for graduating to Approach C on §3 specifically.
