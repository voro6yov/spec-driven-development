---
name: update-specs
description: "Surgically updates the messaging consumer input specs (`<stem>.messaging/<consumer>.md`) after a domain diagram change — regenerates Tables 2–3 for every consumer whose `internal` subscriptions intersect a changed domain event, aborts-and-reconciles consumers that subscribe to a removed/renamed internal event, and emits the messaging updates report. Consumes the domain `updates.md`; never re-diffs the diagram. Invoke with: /messaging-spec:update-specs <domain_diagram>"
argument-hint: <domain_diagram>
allowed-tools: Read, Bash, Agent
---

You are a messaging consumer-spec **update** orchestrator. Given a domain diagram whose `<dir>/<stem>.domain/updates.md` report describes a change, refresh the existing per-consumer specs under `<dir>/<stem>.messaging/` in place — for every consumer whose `internal` Table 2 subscriptions intersect a changed domain event, re-run `event-tables-writer` then `event-fields-writer` to regenerate Tables 2–3 from the current diagrams; for every consumer that subscribes (as `internal`) to a domain event that was removed or renamed, abort that consumer with reconcile instructions and skip it; then emit `<dir>/<stem>.messaging/updates.md`. Do not rerun the full `/messaging-spec:generate-code` pipeline, do not touch the diagram files, and do not ask for confirmation before writing.

This skill is the messaging-side counterpart to `/update-specs` (domain), `/persistence-spec:update-specs`, and `/application-spec:update-specs`. Design rationale lives in `notes/spec-updater-approach.md`, `notes/update-types.md`, and `notes/updates-report.md`; the load-bearing idea is **a thin domain-chained dispatcher, not a surgical splicer** — every consumer-spec table is a pure snapshot, fully regeneratable from the diagrams, so "update Table 3 for consumer C" *is* "re-run `event-fields-writer <commands_diagram> C`". There are **no new agents** — this skill orchestrates the two existing writers (`event-tables-writer`, `event-fields-writer`) plus the existing `messaging-updates-writer`.

This skill **does not** detect domain-level deltas — it consumes the `<dir>/<stem>.domain/updates.md` report that `domain-spec:updates-detector` (Step 0 of domain `/update-specs`, or an explicit prior invocation) already wrote. It never re-diffs the diagram and never invokes `domain-spec:updates-detector`.

This skill covers only the **domain-driven axis**. Changes that originate in `<stem>.commands.md` (the commands application-service diagram — its `%% Messaging` markers, its external `<<Domain Event>>` declarations, the `<AggregateRoot>Commands.on_<event>` handler signatures) are out of scope here — see *What this skill deliberately does not do* below.

## Output path convention

Per `messaging-spec:naming-conventions`, given `<domain_diagram>` at `<dir>/<stem>.md`:

- `<dir>` = directory containing the diagrams.
- `<stem>` = the canonical aggregate stem (domain filename with `.md` stripped); must satisfy `^[a-z][a-z0-9-]*$`.
- `<plugin_dir>` = `<dir>/<stem>.messaging` — the per-plugin folder for messaging-spec.
- `<commands_diagram>` = `<dir>/<stem>.commands.md` — passed to the writer agents.

| File | Role | Touched by |
|---|---|---|
| `<dir>/<stem>.domain/updates.md` | input — domain delta report (must already exist) | not modified |
| `<dir>/<stem>.commands.md` | input — hand-authored commands diagram (must already exist) | not modified |
| `<plugin_dir>/<consumer>.md` × N | the consumer specs being updated (at least one must exist) | `event-tables-writer` + `event-fields-writer` (per affected consumer) |
| `<plugin_dir>/updates.md` | output — messaging delta report | `messaging-updates-writer` |

Every agent derives `<dir>` / `<stem>` from the path it receives per `messaging-spec:naming-conventions`. The writer agents (`event-tables-writer`, `event-fields-writer`) take `<commands_diagram> <consumer_name>`; `messaging-updates-writer` takes `<domain_diagram>` (= `$ARGUMENTS[0]`). Reconstruction by string substitution is forbidden — recover `<dir>` / `<stem>` per the naming-conventions recovery rule, then build sibling paths from it.

This skill keeps no runtime state between agents. `messaging-updates-writer` recovers the pre-update consumer specs via `git show HEAD:<file>` per consumer and recomputes the per-consumer abort list itself from the domain `updates.md` ∩ each consumer's `internal` Table 2 rows — the same derivation this orchestrator uses in Step 3, with the same inputs and rule — so there is nothing for the orchestrator to capture or hand along.

## Workflow

### Step 0 — Verify inputs

Derive `<dir>` and `<stem>` from `$ARGUMENTS[0]` per `messaging-spec:naming-conventions`. `<stem>` must satisfy `^[a-z][a-z0-9-]*$`; if not, hard-fail with: `ERROR: <domain_diagram> path does not yield a valid aggregate stem (must match ^[a-z][a-z0-9-]*$).` Using `Bash` (`test -f`, `ls`):

- **0a.** If `<dir>/<stem>.domain/updates.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.domain/updates.md not found. The messaging updater consumes the domain
  updates report; it is not the first-run pipeline. Run `/update-specs <domain_diagram>` (or
  `@updates-detector <domain_diagram>`) first, or run `/messaging-spec:generate-code <domain_diagram> <consumer_name>`
  per consumer to regenerate the consumer specs and code from scratch.
  ```

- **0b.** If `<dir>/<stem>.commands.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.commands.md not found. The commands application-service diagram is a required
  hand-authored input — `event-tables-writer` and `event-fields-writer` both read it. Restore the file,
  or run `/messaging-spec:generate-code <domain_diagram> <consumer_name>` per consumer after authoring it.
  ```

- **0c.** Enumerate consumer specs: every `<dir>/<stem>.messaging/*.md` **except** `updates.md` (`ls "<dir>/<stem>.messaging"/*.md 2>/dev/null`, drop `updates.md`). If `<dir>/<stem>.messaging/` is absent or yields zero consumer specs → **true no-op**: print

  ```
  No messaging consumer specs under <stem>.messaging/ — nothing to update.
  ```

  and exit (success). Do not create the folder, do not invoke any agent, do not write `updates.md` — there is no consumer spec to update and no report to refresh. (This is the file-presence gate that makes the skill safe to wire unconditionally into the tail of domain `/update-specs` in a future change.)

Do not synthesize any input file. Do not invoke any agent in Step 0.

### Step 1 — Preflight

`Read` `<dir>/<stem>.domain/updates.md`. It is the orchestrator's single source of truth for this step — do not re-derive anything from the diagram. Use `Bash` (`grep`) and `Read` to extract (the exact bullet formats are owned by `domain-spec:updates-report-template`):

- **`degraded_baseline`** — whether the `## Summary` block contains a line beginning `_warning: HEAD `.
- **`stereotype_changed`** — class names listed under `## Class Lifecycle → Stereotype Changed` (one bullet per class). Empty when the heading is absent or its body is `_None._`-style.
- **`removed_classes`** — bullets under `## Class Lifecycle → Removed`, each `` - `ClassName` `<<Stereotype>>` ``; capture `(class_name, stereotype)` per bullet.
- **`added_classes`** — bullets under `## Class Lifecycle → Added`, each `` - `ClassName` `<<Stereotype>>` `` (the `— <N> attributes, <N> methods` suffix is informational; ignore for dispatch); capture `(class_name, stereotype)` per bullet.
- **`event_attr_deltas`** — for each `### `-style class block under `## Per-Class Changes` whose stereotype string contains `Event` (`<<Event>>` / `<<Domain Event>>`), the set of attributes its `**Members:**` bullets report as `Attribute added:` / `Attribute removed:`. Ignore `Attribute changed:` (a retype is byte-neutral for Table 3, which records names not types) and all method bullets.
- **`removed_or_renamed_events`** — `<<Event>>` / `<<Domain Event>>` names in `removed_classes` (a domain-event rename is reported as `removed (old) + added (new)`, so the old name lands here); plus, best-effort, any `<Old>` from a `: emits <Old>` → `: emits <New>` label-rename line anywhere in the report.
- **`added_events`** — `<<Event>>` / `<<Domain Event>>` names in `added_classes`.
- **`aggregate_root_touched`** — true iff a `<<Aggregate Root>>`-stereotyped class appears in `removed_classes`, or in `stereotype_changed` (either bucket), or in both `removed_classes` and `added_classes` (a rename).
- **`affected_categories`** — bullets under `## Affected Categories`, in the order they appear (a `_None._` body means empty); used only to colour the no-op message.
- **`orphan_prose`** — whether `## Orphan Prose Changes` is present with a non-empty body (the synthetic `### Preamble` block counts); used only to colour the no-op message — orphan prose, including a possible bounded-context `title:` rename, is byte-neutral for the consumer specs (queue names use the project package prefix; `Source Destination` uses the aggregate class name; nothing in a consumer spec reads the domain `title:`).

Apply the gates below **in order**. The first one that fires terminates Step 1 — later gates are not evaluated. No writes occur and no agent is invoked on a hard-fail.

#### 1a. Hard-fail: degraded baseline

If `degraded_baseline` is true:

```
ERROR: HEAD baseline is degraded (multiple or missing Mermaid blocks at HEAD per <stem>.domain/updates.md).
The messaging consumer-spec updater cannot operate against a degraded baseline. Run
`/messaging-spec:generate-code <domain_diagram> <consumer_name>` per consumer to regenerate against a clean baseline.
```

#### 1b. Hard-fail: aggregate root removed or stereotype-demoted

If `aggregate_root_touched` and the aggregate root appears in `removed_classes` **without** a same-name entry in `added_classes` (a removal/stereotype-demotion), **or** the aggregate root appears in `stereotype_changed`:

```
ERROR: the aggregate root was removed or re-stereotyped in <stem>.domain/updates.md; the whole diagram set
(and every consumer under <stem>.messaging/) is invalid. Reconcile the diagrams, then re-run
`/messaging-spec:generate-code <domain_diagram> <consumer_name>` per consumer.
```

#### 1c. Hard-fail: aggregate root renamed

If `aggregate_root_touched` via a rename (the aggregate root appears in both `removed_classes` and `added_classes`):

```
ERROR: the aggregate root was renamed in <stem>.domain/updates.md; this cascades to <stem>.commands.md's
class names + filename, the <stem>.messaging/ folder, the %% Messaging markers' <Source> cells, and the
<pkg>.domain.<root_snake> import root in generated code. Rename the diagrams + folder, reconcile the markers,
then re-run `/messaging-spec:generate-code <domain_diagram> <consumer_name>` per consumer.
```

#### 1d. Hard-fail: any other stereotype change

If `stereotype_changed` is non-empty (the aggregate-root case is already handled by 1b; this covers `<<Domain Event>>` ⇄ other re-classifications that invalidate `internal` subscriptions):

```
ERROR: a class stereotype changed in <stem>.domain/updates.md; reconcile the diagrams, then re-run
`/messaging-spec:generate-code <domain_diagram> <consumer_name>` per affected consumer.
```

Surface every offending name, not just the first.

> Note: unlike `/persistence-spec:update-specs` and `/application-spec:update-specs`, this skill does **not** hard-fail on a `<<Repository>>` interface lifecycle change — repositories and domain services are byte-neutral for the consumer spec (Tables 1–3 model the *event* surface, not the persistence or service wiring). A `repositories-services`-only delta is a Tier-3 no-op here.

### Step 2 — Discover consumers and their internal subscriptions

For each consumer spec `<dir>/<stem>.messaging/<C>.md` (the `<C>` enumerated in Step 0c — the basename minus `.md`, a kebab-case identifier like `inventory-sync`):

- `Read` it and locate the `### Table 2: Events to Consume` section (shape owned by `messaging-spec:event-tables-template`). If the body is the empty-state placeholder (`*No events consumed by this consumer.*`), the row list is empty. Otherwise parse the `| Event Name | Type | Source Destination | Command Class | Command Method |` table into rows `{ event_name, type ∈ {external, internal}, source_destination, command_class, command_method }` (strip backticks from each cell).
- `internal_subs[C]` = the set of `event_name` for rows whose `type` is `internal`, each paired with its full row (so `command_class` / `source_destination` / `command_method` are available for the abort instructions). The on-disk Table 2 faithfully mirrors the commands diagram's `%% Messaging - <C>` markers — this orchestrator does **not** parse the commands diagram's Mermaid.

If a working-tree consumer spec is so malformed that its `### Table 2:` heading cannot be located, hard-fail with: `ERROR: <stem>.messaging/<C>.md is malformed; cannot locate the Table 2 heading. Re-generate it via /messaging-spec:generate-code <domain_diagram> <C>.`

### Step 3 — Abort-and-reconcile gate (per consumer)

Compute `dangling[C] := internal_subs[C] ∩ removed_or_renamed_events` for each consumer.

For every consumer with `dangling[C] ≠ ∅`, add `<C>` to the **aborted** set and hold the per-consumer reconcile text. This is **not** a whole-skill hard-fail — every non-dangling consumer still proceeds through Steps 4–5. `event-fields-writer` would fail to resolve a removed/renamed internal event class; and even if it didn't, the consumer's Table 2 (and the commands diagram's `%% Messaging` marker) would still name an event the domain diagram no longer declares — only reconciling the hand-authored marker fixes that.

Per-consumer reconcile text (one per dangling event `<E>`, using that row's `<CommandClass>` / `<Source>` / `<on_method>` cells; surfaced in Step 7's closing summary; `messaging-updates-writer` also renders it in `updates.md`):

```
consumer <C> subscribes to internal event <E>, which was removed/renamed in <stem>.domain/updates.md.
Reconcile the `%% Messaging - <C>` block in <stem>.commands.md (drop or rename the
`<CommandClass> --() <E> : handles (<Source>, <on_method>)` line, and the on_<E> handler on <AggregateRoot>Commands),
then re-run `@event-tables-writer <commands_diagram> <C>` and `@event-fields-writer <commands_diagram> <C>`
(or `/messaging-spec:generate-code <domain_diagram> <C>`).
```

### Step 4 — Compute affected consumers

`affected := { <C> ∉ aborted : internal_subs[C] ∩ keys(event_attr_deltas) ≠ ∅ }` — a consumer is affected iff it subscribes (as `internal`) to at least one domain event that had an **attribute add/remove/rename** in `updates.md`. Note:

- A domain event that was merely **added** (`added_events`) affects no consumer — a new event is a subscription *candidate*, declared by a `%% Messaging` marker in the commands diagram (a separate axis). Informational only; `messaging-updates-writer` records it as a warning in `updates.md`.
- A domain event whose only change is an **attribute type change** or a **method change** affects no consumer (Table 3 records attribute *names*, not types; events have no spec-visible methods).
- A `tenant_id` flip on the aggregate root affects no consumer unless a subscribed internal event *also* gained/lost a `tenant_id` attribute (which would land in `event_attr_deltas`).
- `external`-event rows are wholly outside the domain axis — their classes are declared on the commands diagram, not the domain diagram — so they never enter `affected`.

If `affected` is empty **and** `aborted` is empty → **Tier-3 no-op**: skip Step 5, go straight to Step 6 (emit the report so `<stem>.messaging/updates.md` always exists after a successful run), then Step 7 with the no-op summary line, and exit.

### Step 5 — Regenerate Tables 2–3 per affected consumer

Process the consumers in `affected` (the `aborted` ones are skipped — Step 3 already recorded them). Within a consumer the work is two **sequential** agents (Table 2 first, since Table 3 references Table 2's rows); across consumers the work is **parallel** (independent files). Run two rounds:

1. **Round 1 — `event-tables-writer` (Table 2 refresh).** Emit one `Agent` call per affected consumer **in a single message** — `messaging-spec:event-tables-writer` with prompt `<commands_diagram> <C>`. It re-parses the `%% Messaging - <C>` markers and re-renders Table 2 in place; it is a no-op for a domain-only change (markers unchanged) but catches the case where the operator already reconciled the commands diagram before invoking this skill. Cheap and idempotent. Wait for every call to complete.

2. **Round 2 — `event-fields-writer` (Table 3 regen).** Emit one `Agent` call per affected consumer **in a single message** — `messaging-spec:event-fields-writer` with prompt `<commands_diagram> <C>`. It rebuilds Table 3 wholesale: the `Command Parameter` column from `<AggregateRoot>Commands.on_<event>` signatures in the commands diagram, the `external`-row `Event Field` values from the foreign `<<Domain Event>>` decls in the commands diagram, and the `internal`-row `Event Field` values by best-match against the current `<<Domain Event>>` attribute lists in the domain diagram — re-flagging low-confidence sub-blocks in italic prose. Wait for every call to complete.

Neither writer needs a `target-locations-finder` report — that is a code-gen concern; the spec writers operate purely on the diagrams and the consumer-spec file.

If a writer aborts on a given consumer, record it (its consumer spec is left in whatever partial state the writer reached) and continue with the remaining consumers — the updater does not roll back already-processed consumers, and re-running `/messaging-spec:update-specs` after the operator reconciles the indicated diagram idempotently completes the update. Do **not** abort the whole skill for a per-consumer writer failure; surface it as a `WARNING:` line in Step 7.

### Step 6 — Emit the messaging updates report

Invoke `messaging-spec:messaging-updates-writer` with prompt `$ARGUMENTS[0]` (the domain diagram path). It diffs every working-tree consumer spec against `git HEAD`, cross-references the sibling domain `updates.md`, classifies each consumer (`updated` | `aborted` | `unaffected`), derives the `## Affected Artifacts` footer mechanically, and writes `<dir>/<stem>.messaging/updates.md` (always — even on the Tier-3 no-op, where every consumer renders `unaffected` and the footer is the header row only). It recovers everything it needs from disk + git + the sibling domain `updates.md`; the orchestrator passes nothing else (the writer recomputes the same abort list this skill computed in Step 3 — same inputs, same rule, byte-identical).

This step runs **on every successful run that got past Step 0** (i.e. at least one consumer spec exists) — including the Tier-3 no-op. It does **not** run on the Step 0c "no consumers" no-op (there is no folder to write into and nothing to report), nor on any Step 0 / Step 1 hard-fail (there is no transition to describe; the operator gets only the `ERROR:` line).

If the writer reports a failure, abort and emit a single `ERROR:` line repeating its message. The consumer specs are already in their final post-update state by this point — re-running the orchestrator (or just `@messaging-updates-writer` standalone) idempotently produces the report.

### Step 7 — Report

Print **one** summary line (each invoked agent already printed its own per-step report; add no commentary beyond this line, except the `WARNING:` lines below).

- **Tier-3 no-op** (`affected` and `aborted` both empty):
  - If `orphan_prose` is true: `No messaging consumer-spec updates required. Orphan prose changes detected — review <stem>.domain/updates.md. Emitted <stem>.messaging/updates.md.`
  - Otherwise: `No messaging consumer-spec updates required (no subscribed internal domain event changed; see <stem>.messaging/updates.md for any informational warnings). Emitted <stem>.messaging/updates.md.`

- **At least one consumer affected and/or aborted**:
  ```
  Processed <stem>.messaging/ — <k> consumer(s) regenerated (<names>), <f> failed (<names>), <m> aborted (<names>), <n> unaffected; emitted <stem>.messaging/updates.md.
  ```
  Drop any clause whose count is zero. `<k>` = consumers that completed Step 5 (Tables 2–3 regenerated), `<f>` = consumers a Step-5 writer aborted on, `<m>` = `len(aborted)` (Step 3), `<n>` = discovered − `<k>` − `<f>` − `<m>` (consumers untouched this run). Then:
  - For each aborted (Step 3) consumer, append one line: `WARNING: <reconcile text>` — the Step 3 text with `<C>` / `<E>` / `<CommandClass>` / `<Source>` / `<on_method>` filled from that consumer's dangling Table 2 row and `<stem>` / `<commands_diagram>` from the path derivation; leave `<AggregateRoot>` literal (the operator knows their aggregate root — the orchestrator does not parse the domain diagram for the root *name*).
  - For each consumer a Step-5 writer failed on, append one line: `WARNING: <agent> failed on consumer <C>: <message> — reconcile the indicated diagram and re-run /messaging-spec:update-specs.`

## Failure semantics

- Every step that hard-fails emits exactly one `ERROR:` line and exits the workflow. Do not chain further agents on top of a hard-failed step.
- A per-consumer abort (Step 3) or a per-consumer writer failure (Step 5) is **not** a whole-skill failure — the run continues for the clean consumers, the report records the outcome (`aborted` status / a still-stale Table 3), and Step 7 surfaces a `WARNING:` line per affected consumer.
- The orchestrator does not roll back partial writes. **Re-running `/messaging-spec:update-specs` after fixing the trigger is the supported recovery path** — every step is idempotent on stable inputs:
  - **Step 5** (`event-tables-writer`, `event-fields-writer`) regenerates Tables 2–3 wholesale from the current diagrams on every call (output stable modulo LLM nondeterminism in `event-fields-writer`'s best-match prose).
  - **Step 6** (`messaging-updates-writer`) is a pure HEAD-vs-working-tree diff and overwrites `updates.md` from scratch.
- The only failures `/messaging-spec:update-specs` cannot retry through are the Step 0 missing-input cases (0a, 0b) and the Step 1 preflight hard-fails (1a–1d). Each error message directs the operator to the correct fix — `/update-specs` / `@updates-detector` for the missing domain report, diagram-restore for the missing commands diagram, `/messaging-spec:generate-code <domain_diagram> <consumer_name>` per consumer for everything else.

## Idempotency

Re-running `/messaging-spec:update-specs` against unchanged inputs (working-tree consumer specs unchanged versus HEAD, same domain `updates.md`) produces:

- A no-op early-exit through Step 4 when no consumer's `internal` subscriptions intersect the changed-domain-event set and nothing is dangling.
- Otherwise, byte-identical consumer specs and report — modulo LLM prose drift in `event-fields-writer`'s best-match flags (`git diff` noise, not a correctness failure).

There are no sentinel comments — every consumer-spec table is a snapshot; re-running over an unchanged domain `updates.md` simply reproduces the same content. (Unlike `/persistence-spec:update-specs`'s `<!-- appended-from updates-hash:<hash> -->`, there is no append-only log to guard.)

## What this skill deliberately does not do

- It does not regenerate a consumer spec end-to-end (Tables 1–3) — that is `/messaging-spec:generate-code`. In particular it never re-runs `consumer-spec-initializer`; Table 1 is hand/prefix-derived and a domain change never touches it.
- It does not re-diff `<domain_diagram>` and does not invoke `domain-spec:updates-detector` — the domain `updates.md` is expected on disk before this skill runs.
- It does not touch the diagram files (`<stem>.md`, `<stem>.commands.md`, `<stem>.queries.md`) or any `## Artifacts` index — those siblings are linked from the original pipeline runs.
- It does not handle commands-diagram-driven changes (a consumer added/removed, an event added/removed from a `%% Messaging` block, a row's `Type` / `Source Destination` / `Command Class` / `Command Method` changed, an `<AggregateRoot>Commands.on_<event>` signature changed, an `external` event's wire shape changed). Those originate in `<stem>.commands.md`, are not captured by `<stem>.domain/updates.md`, and are reconciled by re-running `/messaging-spec:generate-code <domain_diagram> <consumer_name>` per consumer (idempotent/additive — it regenerates Tables 2–3 from the current commands diagram), or by a future `messaging-spec:updates-detector` for the commands-diagram axis (out of scope here).
- It does not model the command-handler side of a consumer — Table 1's *Commands queue name* is the only consumer-spec trace of the command side, and it derives from the consumer name, not from any domain `<<Command>>` class. Domain `<<Command>>` changes ripple into *generated* `command-handlers` / `command-replies` / `command-dispatchers` code only, reconciled by `/messaging-spec:generate-code`, not by this updater. (A known modeling gap, not a bug.)
- It does not handle aggregate-root removal/rename, stereotype changes, or a degraded baseline — those route to `/messaging-spec:generate-code` (per consumer) via the Step 1 hard-fails. It does **not** hard-fail on `<<Repository>>` / `<<Service>>` lifecycle changes — those are byte-neutral for the consumer spec (Tier-3 no-op).
- It does not silently prune a dangling internal subscription — a subscribed internal `<<Domain Event>>` removed/renamed leaves the commands-diagram `%% Messaging` marker (and the `on_<event>` handler) dangling, which only the operator can reconcile; the skill surfaces an abort-and-reconcile instruction (Step 3) and skips that consumer for this run.
- It does not preserve hand-edits inside a consumer spec — touched consumers' Tables 2–3 are wholesale-replaced; the operator's contract is "the spec is regenerated from the diagrams, not curated". (`event-fields-writer` does re-derive its own italic low-confidence flags around Table 3 from scratch on each run; that is by design.) Untouched consumers' specs are preserved byte-identically.
- It does not auto-update generated messaging code (`messaging/<consumer>/events.py`, `handlers.py`, `dispatcher.py`, the `containers.py` / `entrypoint.py` / `__main__.py` wiring, the `constants.py` constants, the handler integration tests) — that is the future `/messaging-spec:update-code` skill, which consumes the `<stem>.messaging/updates.md` this skill emits.
- It does not chain into domain `/update-specs` — it is independently invocable; the opt-in chained-step integration (gated by `<stem>.messaging/` being non-empty, after the persistence/application tail steps) is a separate, later change.
