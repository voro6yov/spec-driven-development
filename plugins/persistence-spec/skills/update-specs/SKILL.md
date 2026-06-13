---
name: update-specs
description: "Surgically updates the command repository spec after a domain diagram change — regenerates the snapshot sections from the current diagram, appends delta-driven migration rows to §2.Migrations, and emits the persistence updates report. Invoke with: /persistence-spec:update-specs <domain_diagram>"
argument-hint: <domain_diagram>
allowed-tools: Read, Bash, Agent
---

You are a persistence spec **update** orchestrator. Given a domain diagram whose `<dir>/<stem>.domain/updates.md` report describes a change, refresh the existing `<dir>/<stem>.persistence/command-repo-spec.md` in place — regenerate its snapshot sections from the current diagram, append the delta-driven rows to its append-only migrations log, and emit `<dir>/<stem>.persistence/updates.md`. Do not rerun the full `@persistence-spec:specs-generator` pipeline, do not touch the diagram file, and do not ask for confirmation before writing.

This skill is the persistence-side counterpart to `/update-specs` (domain). It is the surgical analog of `@persistence-spec:specs-generator`. Design rationale lives in `notes/spec-updater-approaches.md`, `notes/update-types.md`, and `notes/updates-report.md`; the load-bearing idea is the **snapshot / append-only-log split** — §1, §2.{Tables, Mappers, Repository, Context Integration}, and §3 are *snapshot* sections (regenerated wholesale from the current diagram), while §2.Migrations is an *append-only log* (existing rows immutable; new rows derived from the domain delta and stacked on top).

This skill **does not** detect domain-level deltas — it consumes the `<dir>/<stem>.domain/updates.md` report that `domain-spec:updates-detector` (Step 0 of domain `/update-specs`, or an explicit prior invocation) already wrote. It never re-diffs the diagram and never invokes `domain-spec:updates-detector`.

## Output path convention

Per `spec-core:naming-conventions`, given `<domain_diagram>` at `<dir>/<stem>.md`:

| File | Role | Touched by |
|---|---|---|
| `<dir>/<stem>.domain/updates.md` | input — domain delta report (must already exist) | not modified |
| `<dir>/<stem>.persistence/command-repo-spec.md` | the spec being updated (must already exist) | `command-repo-spec-pattern-selector` (§1 + §2 snapshot sub-sections), `command-repo-spec-schema-writer` (§3), `command-repo-spec-migrations-appender` (§2.Migrations rows) |
| `<dir>/<stem>.persistence/updates.md` | output — persistence delta report | `command-repo-spec-updates-writer` |

`<domain_diagram>` itself is read only by the invoked agents (for shape/type resolution) and is never modified. Every agent derives `<dir>` / `<stem>` from `$ARGUMENTS` per `spec-core:naming-conventions` — pass `$ARGUMENTS` verbatim as the prompt to each.

This skill keeps no runtime state between agents. The updates-writer recovers the pre-update spec via `git show HEAD:<spec_file>` and the appended-row set via §2.Migrations row-ID set-difference, so there is nothing for the orchestrator to capture or hand along.

## Workflow

### Step 0 — Verify inputs

Derive `<dir>` and `<stem>` from `$ARGUMENTS` per `spec-core:naming-conventions`. Using `Bash` (`test -f`):

- **0a.** If `<dir>/<stem>.domain/updates.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.domain/updates.md not found. The persistence updater consumes the domain
  updates report; it is not the first-run pipeline. Run `/update-specs <domain_diagram>` (or
  `@updates-detector <domain_diagram>`) first, or run `@persistence-spec:specs-generator <domain_diagram>`
  to regenerate the persistence spec from scratch.
  ```

- **0b.** If `<dir>/<stem>.persistence/command-repo-spec.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.persistence/command-repo-spec.md not found. The persistence updater is not the
  first-run pipeline. Run `@persistence-spec:specs-generator <domain_diagram>` to create the spec.
  ```

Do not synthesize either file. Do not invoke any agent.

### Step 1 — Preflight

`Read` `<dir>/<stem>.domain/updates.md`. It is the orchestrator's single source of truth for this step — do not re-derive anything from the diagram. Use `Bash` (`grep`) and `Read` to extract:

- **`degraded_baseline`** — whether the `## Summary` block contains a line beginning `_warning: HEAD `.
- **`stereotype_changed`** — class names listed under `## Class Lifecycle → Stereotype Changed` (one bullet per class; the exact bullet format is owned by `domain-spec:updates-report-template`). Empty when the heading is absent or its body is `_None._`-style.
- **`removed_classes`** — bullets under `## Class Lifecycle → Removed`, each `` - `ClassName` `<<Stereotype>>` ``.
- **`affected_categories`** — bullets under `## Affected Categories`, in the order they appear. The literal body `_None._` means empty.
- **`orphan_prose`** — whether `## Orphan Prose Changes` is present with a non-empty body (the synthetic `### Preamble` block counts). Used only to colour the no-op message — orphan prose, including a possible bounded-context `title:` rename, is byte-neutral for the command-repo-spec at this granularity (a context rename's effect on UoW class names is picked up the next time a structural change triggers the snapshot regen).
- **`repo_class_lifecycle`** — whether any bullet under `## Class Lifecycle → Added` or `→ Removed` carries the stereotype `<<Repository>>`.

Apply the gates below **in order**. The first one that fires terminates Step 1.

#### 1a. Hard-fail: degraded baseline

If `degraded_baseline` is true:

```
ERROR: HEAD baseline is degraded (multiple or missing Mermaid blocks at HEAD per <stem>.domain/updates.md).
The surgical persistence updater cannot operate against a degraded baseline. Run
`@persistence-spec:specs-generator <domain_diagram>` to regenerate the spec from scratch.
```

#### 1b. Hard-fail: stereotype change

If `stereotype_changed` is non-empty:

```
ERROR: Class(es) <names> have stereotype changes in <stem>.domain/updates.md. A stereotype change moves a
class to a different pattern catalog (e.g. a value object becoming a child entity), which requires the
persistence spec — including its migration baseline — to be re-rendered. Run
`@persistence-spec:specs-generator <domain_diagram>` to regenerate from scratch.
```

Surface every offending name, not just the first.

#### 1c. Hard-fail: aggregate-root removal

If any bullet in `removed_classes` has stereotype `<<Aggregate Root>>`:

```
ERROR: Aggregate root `<ClassName>` is listed under `## Class Lifecycle → Removed` in
<stem>.domain/updates.md. The spec's anchor class is gone; the persistence spec is no longer valid. Run
`@persistence-spec:specs-generator <domain_diagram>`.
```

#### 1d. Hard-fail: `<<Repository>>` interface lifecycle change

If `repo_class_lifecycle` is true (a `<<Repository>>`-stereotyped class added or removed):

```
ERROR: A `<<Repository>>` interface was added or removed per <stem>.domain/updates.md. A domain aggregate
without its repository is not persistable, and a new repository requires a fresh pattern selection. Run
`@persistence-spec:specs-generator <domain_diagram>`.
```

#### 1e. No-op exit: nothing persistence-relevant

Early-exit (with success) when **any** of the following holds:

- `affected_categories` is empty (`_None._` body). By the report-template's footer contract this implies empty `## Class Lifecycle`, no `## Per-Class Changes` blocks, and no `## Orphan Relationship Changes` — so the only thing the report can carry on this path is orphan prose (including, possibly, a bounded-context `title:` rename), which is byte-neutral for the command-repo-spec at this granularity.
- `affected_categories` is non-empty but `⊆ {domain-events, commands}`. Domain `<<Event>>` and `<<Command>>` classes do not persist.
- `affected_categories == {repositories-services}` **and** there is no `<<Repository>>`-stereotyped class anywhere in `## Class Lifecycle` or `## Per-Class Changes` — i.e. the only contributor is a `<<Service>>` change, which is byte-neutral for the command-repo-spec.

On a no-op exit, still invoke `command-repo-spec-updates-writer` (Step 4) so a `<stem>.persistence/updates.md` exists after every successful run (the consumer's contract is "a report always exists") — it sees the working-tree spec unchanged versus HEAD and emits an all-`_no changes_` report. Then print:

- If `orphan_prose` is true: `No persistence spec updates required. Orphan prose changes detected — review <stem>.domain/updates.md (a bounded-context title rename, if any, is folded in the next time a structural change triggers the snapshot regen; run @persistence-spec:specs-generator to apply it now).`
- Otherwise: `No persistence spec updates required (no persistence-relevant domain changes).`

Then exit.

> Note: gates 1a–1d are the only failures `/persistence-spec:update-specs` cannot retry through — re-running hits the same gate. Each error directs the operator to `@persistence-spec:specs-generator`, which rebuilds the spec and re-establishes the migrations baseline; the next update then resumes from the new max migration ID.

### Step 2 — Regenerate the snapshot sections

Run these two agents **sequentially** (the schema writer reads the pattern choices the selector wrote). Pass `$ARGUMENTS` as the prompt to each.

1. Invoke `persistence-spec:command-repo-spec-pattern-selector` — replaces §1's `### Purpose` + `### Aggregate Summary` and §2's `### Tables` / `### Mappers` / `### Repository` / `### Context Integration` sub-sections from the current diagram, leaving §1's `### Implementation` table and §2's `### Migrations` sub-table untouched. (This agent is idempotent — it is designed to be re-run on a populated spec.)
2. Invoke `persistence-spec:command-repo-spec-schema-writer` — replaces the entire `## 3. Schema Specification` body (ER diagram + parent table + child-table blocks + Indexes) from the current diagram.

If either agent reports a failure, abort and emit a single `ERROR:` line repeating its message. Do not run downstream agents — the spec is left partially regenerated, and re-running `/persistence-spec:update-specs` on top of the corrected inputs idempotently completes it.

### Step 3 — Append delta migration rows

Invoke `persistence-spec:command-repo-spec-migrations-appender` with prompt `$ARGUMENTS`. It reads the existing §2.Migrations rows (for `max(ID)`), reads `<stem>.domain/updates.md`, applies the delta-to-changeset dispatch table, and appends new rows with fresh sequential IDs behind a `<!-- appended-from updates-hash:<hash> -->` sentinel. Existing rows are byte-stable. It is idempotent on unchanged inputs (it short-circuits when the updates-hash sentinel is already present, and de-duplicates by Changeset text otherwise). Finder-index rows carry an extra guard: each `Add Index` / `Drop Index` candidate is validated against a working-tree-vs-HEAD diff of §3 `### Indexes`, so an index the first-run baseline already created under its aggregating `Indexes for <table>` row is not re-added (this is why Step 2's snapshot regen must run before this step — the appender diffs the regenerated §3).

The appender **trusts this orchestrator's preflight** — it does not re-check for degraded baseline, root lifecycle changes, or repository-interface lifecycle changes (Step 1 hard-fails before reaching here in those cases). It may itself hard-fail on a malformed §2.Migrations table or an unmappable column type; if so, abort and emit a single `ERROR:` line repeating its message.

### Step 4 — Emit the persistence updates report

Invoke `persistence-spec:command-repo-spec-updates-writer` with prompt `$ARGUMENTS`. It diffs the working-tree spec against `git HEAD`, classifies the snapshot-section deltas and the appended migration rows, and writes `<dir>/<stem>.persistence/updates.md` (always — even on a no-op, where every section renders `_no changes_`). It recovers everything it needs from disk + git; the orchestrator passes nothing else.

If it reports a failure, abort and emit a single `ERROR:` line repeating its message. `<stem>.persistence/command-repo-spec.md` is already in its final post-update state by this point — re-running the orchestrator (or just the updates-writer agent standalone) idempotently produces the report.

### Step 5 — Report

Print one summary line:

```
Updated <stem>.persistence/command-repo-spec.md (snapshot sections regenerated; <migrations_clause>) and emitted <stem>.persistence/updates.md.
```

Where `<migrations_clause>` is `appended N migration row(s): <id1>, <id2>, …` when the appender added rows, or `no new migration rows` when it short-circuited / de-duplicated to zero. Derive N and the IDs from the appender's own confirmation line — do not re-parse the spec. Do not emit additional commentary; each invoked agent already printed its own per-step report.

## Failure semantics

- Every step that aborts emits exactly one `ERROR:` line and exits the workflow. Do not chain further agents on top of a failed step.
- The orchestrator does not roll back partial writes. **Re-running `/persistence-spec:update-specs` after fixing the trigger is the supported recovery path** — every step is idempotent on stable inputs:
  - **Step 2** (`command-repo-spec-pattern-selector`, `command-repo-spec-schema-writer`) regenerates its sections wholesale from the current diagram on every call.
  - **Step 3** (`command-repo-spec-migrations-appender`) short-circuits on the updates-hash sentinel and de-duplicates by Changeset text — re-runs append nothing.
  - **Step 4** (`command-repo-spec-updates-writer`) is a pure HEAD-vs-working-tree diff and overwrites `updates.md` from scratch.
- The only failures `/persistence-spec:update-specs` cannot retry through are the Step 0 missing-input cases (0a, 0b) and the Step 1 preflight hard-fails (1a–1d). Each error message directs the operator to the correct fix — `/update-specs` / `@updates-detector` for the missing report, `@persistence-spec:specs-generator` for everything else.

## What this skill deliberately does not do

- It does not regenerate `<stem>.persistence/command-repo-spec.md` end-to-end — that is `@persistence-spec:specs-generator`. In particular it never re-invokes `command-repo-spec-scaffolder` (the file already exists) or `command-repo-spec-migrations-writer` (the first-run baseline writer; updates go through the appender).
- It does not re-diff `<domain_diagram>` and does not invoke `domain-spec:updates-detector` — the domain `updates.md` is expected on disk before this skill runs.
- It does not touch the diagram file or its `## Artifacts` index — those were linked by the original `@persistence-spec:specs-generator` run.
- It does not modify pre-existing §2.Migrations rows — the immutability contract is load-bearing (each row maps to a deployed-or-pending `db/migrations/<id>_<slug>.yaml`).
- It does not write or modify any YAML under `db/migrations/` — those are owned by `@persistence-spec:code-generator` (`migrations-implementer`).
- It does not handle aggregate-root removal, stereotype changes, `<<Repository>>` interface lifecycle changes, or a degraded baseline — those route to `@persistence-spec:specs-generator` via the Step 1 hard-fails.
- It does not auto-update generated persistence code (`tables/`, `mappers/`, `migrations/`, repositories, repo tests) — that is the future `/persistence-spec:update-code` skill, which consumes the `<stem>.persistence/updates.md` this skill emits.
- It does not preserve hand-edits inside the spec — the operator's contract is that the spec is regenerated from the diagram, not curated.
- It is independently invocable, **and** is one of the two downstream skills fanned out in parallel at **Step 10** of domain `/update-specs` (alongside `/application-spec:update-specs`, which owns the rest-api / messaging sub-cascade). It is domain-driven and invokes no app-service detector, so it receives no `--detectors-fresh` flag. A `command-repo-spec.md`-missing hard-fail (Step 0b) when invoked from that fan-out does **not** abort its sibling — each runs to completion and prints its own report; run `@persistence-spec:specs-generator` (and `@persistence-spec:code-generator`) before relying on the domain-level cascade.
