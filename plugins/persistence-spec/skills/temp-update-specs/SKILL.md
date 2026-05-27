---
name: temp-update-specs
description: "Persistence-only variant of `update-specs` for testing. Refreshes `<stem>.persistence/command-repo-spec.md` from the current domain diagram + domain updates report and emits `<stem>.persistence/updates.md`. Invoke with: /persistence-spec:temp-update-specs <domain_diagram>"
argument-hint: <domain_diagram>
allowed-tools: Read, Bash, Agent
---

You are a persistence-spec **update** orchestrator running in testing mode. This is a thin variant of `/persistence-spec:update-specs` that exists for parity with the domain-side `/temp-update-specs` flow — invoke it when iterating on the persistence updater alone so the test cadence and slash-command namespace match the domain testing skills.

The behaviour is byte-identical to `/persistence-spec:update-specs`: refresh the existing `<dir>/<stem>.persistence/command-repo-spec.md` in place (regenerate snapshot sections, append delta-driven migration rows) and emit `<dir>/<stem>.persistence/updates.md`. Do not rerun the full `/persistence-spec:generate-specs` pipeline, do not touch the diagram file, and do not ask for confirmation before writing.

This skill **does not** detect domain-level deltas — it consumes the `<dir>/<stem>.domain/updates.md` report that `domain-spec:updates-detector` (Step 0 of domain `/update-specs` or `/temp-update-specs`, or an explicit prior invocation) already wrote. It never re-diffs the diagram and never invokes `domain-spec:updates-detector`.

## Output path convention

Per `persistence-spec:naming-conventions`, given `<domain_diagram>` at `<dir>/<stem>.md`:

| File | Role | Touched by |
|---|---|---|
| `<dir>/<stem>.domain/updates.md` | input — domain delta report (must already exist) | not modified |
| `<dir>/<stem>.persistence/command-repo-spec.md` | the spec being updated (must already exist) | `command-repo-spec-pattern-selector` (§1 + §2 snapshot sub-sections), `command-repo-spec-schema-writer` (§3), `command-repo-spec-migrations-appender` (§2.Migrations rows) |
| `<dir>/<stem>.persistence/updates.md` | output — persistence delta report | `command-repo-spec-updates-writer` |

Every agent derives `<dir>` / `<stem>` from `$ARGUMENTS` per `persistence-spec:naming-conventions` — pass `$ARGUMENTS` verbatim as the prompt to each.

## Workflow

### Step 0 — Verify inputs

Derive `<dir>` and `<stem>` from `$ARGUMENTS` per `persistence-spec:naming-conventions`. Using `Bash` (`test -f`):

- **0a.** If `<dir>/<stem>.domain/updates.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.domain/updates.md not found. The persistence updater consumes the domain
  updates report; it is not the first-run pipeline. Run `/update-specs <domain_diagram>` (or
  `/temp-update-specs <domain_diagram>` from domain-spec, or `@updates-detector <domain_diagram>`)
  first, or run `/persistence-spec:generate-specs <domain_diagram>` to regenerate the persistence
  spec from scratch.
  ```

- **0b.** If `<dir>/<stem>.persistence/command-repo-spec.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.persistence/command-repo-spec.md not found. The persistence updater is not the
  first-run pipeline. Run `/persistence-spec:generate-specs <domain_diagram>` to create the spec.
  ```

Do not synthesize either file. Do not invoke any agent.

### Step 1 — Preflight

`Read` `<dir>/<stem>.domain/updates.md`. It is the orchestrator's single source of truth for this step — do not re-derive anything from the diagram. Use `Bash` (`grep`) and `Read` to extract:

- **`degraded_baseline`** — whether the `## Summary` block contains a line beginning `_warning: HEAD `.
- **`stereotype_changed`** — class names listed under `## Class Lifecycle → Stereotype Changed`.
- **`removed_classes`** — bullets under `## Class Lifecycle → Removed`, each `` - `ClassName` `<<Stereotype>>` ``.
- **`affected_categories`** — bullets under `## Affected Categories`, in the order they appear. The literal body `_None._` means empty.
- **`orphan_prose`** — whether `## Orphan Prose Changes` is present with a non-empty body (the synthetic `### Preamble` block counts).
- **`repo_class_lifecycle`** — whether any bullet under `## Class Lifecycle → Added` or `→ Removed` carries the stereotype `<<Repository>>`.

Apply the gates below **in order**. The first one that fires terminates Step 1.

#### 1a. Hard-fail: degraded baseline

If `degraded_baseline` is true:

```
ERROR: HEAD baseline is degraded (multiple or missing Mermaid blocks at HEAD per <stem>.domain/updates.md).
The surgical persistence updater cannot operate against a degraded baseline. Run
`/persistence-spec:generate-specs <domain_diagram>` to regenerate the spec from scratch.
```

#### 1b. Hard-fail: stereotype change

If `stereotype_changed` is non-empty:

```
ERROR: Class(es) <names> have stereotype changes in <stem>.domain/updates.md. A stereotype change moves a
class to a different pattern catalog, which requires the persistence spec — including its migration
baseline — to be re-rendered. Run `/persistence-spec:generate-specs <domain_diagram>` to regenerate
from scratch.
```

Surface every offending name, not just the first.

#### 1c. Hard-fail: aggregate-root removal

If any bullet in `removed_classes` has stereotype `<<Aggregate Root>>`:

```
ERROR: Aggregate root `<ClassName>` is listed under `## Class Lifecycle → Removed` in
<stem>.domain/updates.md. The spec's anchor class is gone; the persistence spec is no longer valid. Run
`/persistence-spec:generate-specs <domain_diagram>`.
```

#### 1d. Hard-fail: `<<Repository>>` interface lifecycle change

If `repo_class_lifecycle` is true:

```
ERROR: A `<<Repository>>` interface was added or removed per <stem>.domain/updates.md. A domain aggregate
without its repository is not persistable, and a new repository requires a fresh pattern selection. Run
`/persistence-spec:generate-specs <domain_diagram>`.
```

#### 1e. No-op exit: nothing persistence-relevant

Early-exit (with success) when **any** of the following holds:

- `affected_categories` is empty (`_None._` body).
- `affected_categories` is non-empty but `⊆ {domain-events, commands}`.
- `affected_categories == {repositories-services}` **and** there is no `<<Repository>>`-stereotyped class anywhere in `## Class Lifecycle` or `## Per-Class Changes` — only a `<<Service>>` change.

On a no-op exit, still invoke `command-repo-spec-updates-writer` (Step 4) so a `<stem>.persistence/updates.md` exists after every successful run. Then print:

- If `orphan_prose` is true: `No persistence spec updates required. Orphan prose changes detected — review <stem>.domain/updates.md.`
- Otherwise: `No persistence spec updates required (no persistence-relevant domain changes).`

Then exit.

### Step 2 — Regenerate the snapshot sections

Run these two agents **sequentially** (the schema writer reads the pattern choices the selector wrote). Pass `$ARGUMENTS` as the prompt to each.

1. Invoke `persistence-spec:command-repo-spec-pattern-selector` — replaces §1's `### Purpose` + `### Aggregate Summary` and §2's `### Tables` / `### Mappers` / `### Repository` / `### Context Integration` sub-sections from the current diagram, leaving §1's `### Implementation` table and §2's `### Migrations` sub-table untouched.
2. Invoke `persistence-spec:command-repo-spec-schema-writer` — replaces the entire `## 3. Schema Specification` body (ER diagram + parent table + child-table blocks + Indexes) from the current diagram.

If either agent reports a failure, abort and emit a single `ERROR:` line repeating its message.

### Step 3 — Append delta migration rows

Invoke `persistence-spec:command-repo-spec-migrations-appender` with prompt `$ARGUMENTS`. It reads the existing §2.Migrations rows (for `max(ID)`), reads `<stem>.domain/updates.md`, applies the delta-to-changeset dispatch table, and appends new rows with fresh sequential IDs behind a `<!-- appended-from updates-hash:<hash> -->` sentinel. Existing rows are byte-stable. Idempotent on unchanged inputs.

If it hard-fails (malformed §2.Migrations table, unmappable column type), abort and emit a single `ERROR:` line repeating its message.

### Step 4 — Emit the persistence updates report

Invoke `persistence-spec:command-repo-spec-updates-writer` with prompt `$ARGUMENTS`. It diffs the working-tree spec against `git HEAD`, classifies the snapshot-section deltas and the appended migration rows, and writes `<dir>/<stem>.persistence/updates.md` (always — even on a no-op).

If it reports a failure, abort and emit a single `ERROR:` line repeating its message.

### Step 5 — Report

Print one summary line:

```
Updated <stem>.persistence/command-repo-spec.md (snapshot sections regenerated; <migrations_clause>) and emitted <stem>.persistence/updates.md.
```

Where `<migrations_clause>` is `appended N migration row(s): <id1>, <id2>, …` when the appender added rows, or `no new migration rows` when it short-circuited / de-duplicated to zero.

## Failure semantics

- Every step that aborts emits exactly one `ERROR:` line and exits the workflow.
- Re-running `/persistence-spec:temp-update-specs` after fixing the trigger is the supported recovery path — every step is idempotent on stable inputs.
- The only failures this skill cannot retry through are the Step 0 missing-input cases (0a, 0b) and the Step 1 preflight hard-fails (1a–1d). Each error message directs the operator to the correct fix.

## What this skill deliberately does not do

- It does not chain to `/application-spec:update-specs`, `/rest-api-spec:update-specs`, or `/messaging-spec:update-specs`. The persistence layer's `update-specs` never cascaded, so the "temp" prefix here is purely for testing-namespace symmetry with `domain-spec:temp-update-specs`.
- It does not regenerate `<stem>.persistence/command-repo-spec.md` end-to-end — that is `/persistence-spec:generate-specs`.
- It does not re-diff `<domain_diagram>` and does not invoke `domain-spec:updates-detector` — the domain `updates.md` is expected on disk before this skill runs.
- It does not modify pre-existing §2.Migrations rows — the immutability contract is load-bearing.
- It does not write or modify any YAML under `db/migrations/` — those are owned by `/persistence-spec:generate-code` (`migrations-implementer`).
- It does not auto-update generated persistence code (`tables/`, `mappers/`, `migrations/`, repositories, repo tests) — pair this skill with `/persistence-spec:temp-update-code <domain_diagram>` for the persistence-only code-update analog.
