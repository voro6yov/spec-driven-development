# `messaging-updates-writer` — Commands-Axis Extension (X1/X2 + Source Attribution)

This note designs how `messaging-updates-writer` should consume the new commands-axis detector report (`<dir>/<stem>.application/commands-updates.md`) to surface **X1** (consumer-needs-init) and **X2** (orphaned-consumer) outcomes in `<dir>/<stem>.messaging/updates.md`, including the new per-consumer status vocabulary and the cross-axis `Source delta` attribution.

It is the writer-side complement to [`commands-queries-integration-approach.md`](commands-queries-integration-approach.md) — the orchestrator-side integration explicitly deferred this writer extension as a "v2 follow-up" (§ "What this DOES change" final two rows; § "Open questions" item 1; § "Step 6 — Emit the messaging updates report (extended scope)"). That note proposes only that X1/X2 be surfaced in the orchestrator's Step 7 WARNING lines; the writer keeps its existing `{updated, aborted, unaffected}` vocabulary and remains domain-axis only. **This note picks up where it left off.**

For the upstream report whose `## Messaging Markers` and `## External Domain Events` sections drive this design, see [`../../application-spec/notes/commands-queries-updates-report.md`](../../application-spec/notes/commands-queries-updates-report.md).
For the architectural pattern this design mirrors (three-axis source attribution + skip-on-missing-report semantics), see [`../../application-spec/agents/application-updates-writer.md`](../../application-spec/agents/application-updates-writer.md).
For the existing writer agent body and report schema this note extends, see [`../agents/messaging-updates-writer.md`](../agents/messaging-updates-writer.md) and [`../skills/updates-report-template/SKILL.md`](../skills/updates-report-template/SKILL.md).
For the report schema as a design artifact, see [`updates-report.md`](updates-report.md) — this note's schema deltas thread through there too.

The deliverable is **this design note**. The follow-up session implements the agent body changes and the skill-template extension proposed here.

---

## Scope

In scope:

- Per-consumer status vocabulary extension: add `needs-init` and `orphaned`; status precedence; render rules.
- Advisory block shape for `needs-init` and `orphaned` consumers (no spec-diff to render).
- Consumer enumeration rule: union of (a) on-disk specs and (b) commands-diagram `%% Messaging - <C>` blocks.
- Source attribution on `updated` blocks: tag each `Source delta` with `[domain]` or `[commands-diagram]`.
- Failure modes when `commands-updates.md` is absent.
- `## Affected Artifacts` footer policy for X1/X2 rows.
- Idempotency: byte-stable on stable inputs (three reports + working tree + HEAD).
- Companion `messaging-spec:updates-report-template` skill changes.

Out of scope:

- The orchestrator integration itself (covered by [`commands-queries-integration-approach.md`](commands-queries-integration-approach.md)).
- The detector that produces `commands-updates.md` (owned by application-spec).
- The future `/messaging-spec:update-code` consumer — it reads this report's `## Affected Artifacts` footer top-to-bottom and is informational about the rest; the new `needs-init` / `orphaned` rows are deliberately *not* in the footer (§ "Affected Artifacts footer policy" below), so the code updater's contract is unchanged.

---

## Decision summary

1. **Status vocabulary** grows from `{updated, aborted, unaffected}` to **`{updated, aborted, unaffected, needs-init, orphaned}`**. The two new statuses are **advisory** — they describe a state mismatch between the commands diagram and the on-disk consumer-spec set, not a transition of any single file.
2. **Status precedence** (first match wins, scanning per-consumer): `orphaned` → `aborted` → `needs-init` → `updated` → `unaffected`. `orphaned` and `needs-init` are *terminal* — never simultaneous with `updated` or `aborted` because they describe consumers that have no current spec-diff to report.
3. **Consumer enumeration** becomes a **set union** of (a) on-disk specs (`<dir>/<stem>.messaging/*.md` minus `updates.md`) and (b) consumer names declared by `%% Messaging - <C>` blocks in the commands diagram (read from `commands-updates.md`'s `## Messaging Markers` block when the consumer is *changing* this run; otherwise irrelevant to enumeration). Consumers in (b)−(a) are `needs-init`; consumers in (a)−(b) **with a removed marker block** are `orphaned`; consumers in (a)∩(b) follow the existing domain-axis rules.
4. **`Source delta` attribution on `updated` blocks** mirrors `application-updates-writer`: tag each sub-block's source phrase with `[domain]` or `[commands-diagram]`, with `(unknown source)` as the literal fallback when no probe matches.
5. **Missing `commands-updates.md` is non-fatal** — same posture as the existing missing-`domain/updates.md` rule. X1/X2 detection is silently skipped, `[commands-diagram]` probes are skipped, and a warning is appended.
6. **`## Affected Artifacts` footer is unchanged** — only `updated` consumers contribute rows. `needs-init` and `orphaned` rows are deliberately **not** in the footer (X1 has no on-disk artifact yet; X2's artifact is unchanged this run). They surface only in `## Summary` counts, the `## Consumer Changes` body, and a new `## Operator Actions` H2 in the report body.
7. **Idempotency** is preserved: byte-stable inputs (the three reports + working tree + HEAD) → byte-stable report.

---

## Status vocabulary

### The five terminal statuses

The H3 heading form `### \`<consumer_name>\` — <status>` stays. The `<status>` token is one of this closed set:

| Status | Drives | When (post-precedence, first match wins) |
|---|---|---|
| `orphaned` | X2 advisory | The consumer has an on-disk spec (`<dir>/<stem>.messaging/<C>.md`) but no `%% Messaging - <C>` block in the commands diagram. Authoritative signal: `commands-updates.md`'s `## Messaging Markers → ### \`<C>\` (consumer removed)` row. The spec file is **unchanged this run**. Operator action: delete the spec file + reconcile the code side via `/messaging-spec:generate-code`. |
| `aborted (reconcile commands diagram)` | (existing) dangling internal subscription | The consumer subscribes (as `internal`, per its Table 2) to a domain event the domain `updates.md` reports as removed or renamed **and** the commands diagram still declares the subscription. (When the diagram already reconciled the marker, the deduction rule in [`commands-queries-integration-approach.md`](commands-queries-integration-approach.md) § "Step 3" removes the consumer from the aborted set — it may then surface as `orphaned` or `updated` instead.) |
| `needs-init` | X1 advisory | The commands diagram declares a `%% Messaging - <C>` block for a consumer with **no on-disk spec**. Authoritative signal: `commands-updates.md`'s `## Messaging Markers → ### \`<C>\` (consumer added)` row. There is **no spec to diff**. Operator action: `/messaging-spec:generate-code <domain_diagram> <C>`. |
| `updated` | (existing) Table 3 regenerated | At least one `internal`-event sub-block's row set or italic-flag text differs between HEAD and the working tree, **and** at least one probe (domain attr delta, commands marker change, external-event attr delta) explains the change. |
| `unaffected` | (existing) no actionable change | None of the above. Includes: (a) `internal` subscriptions but no matching changed-event probe; (b) byte-stable spec hash; (c) newly-tracked-this-run consumer (first-run consumer warning still emitted). |

### Precedence

First match wins, scanning in this order per consumer:

```
orphaned → aborted → needs-init → updated → unaffected
```

Edge cases the precedence resolves:

- **Orphaned-and-aborted**: a consumer subscribes to a removed domain event *and* its commands-diagram block was deleted in the same operator edit. The block-deletion already reconciles the dangling subscription, so the consumer is no longer "aborted" — it is `orphaned`, and the operator's action is to delete the spec file (not to re-edit the commands diagram, which is already correct). The Step-3 deduction rule from [`commands-queries-integration-approach.md`](commands-queries-integration-approach.md) drops the consumer from the aborted set first; this precedence row is the safety net if the deduction is conservative.
- **Aborted-and-needs-init**: structurally impossible — `needs-init` requires no on-disk spec, but `aborted` requires reading the on-disk spec's Table 2.
- **Orphaned-but-otherwise-changed**: when a consumer is `orphaned`, the writer skips spec-diff entirely — the spec is unchanged this run by definition. Any working-tree-vs-HEAD hash drift on an `orphaned` consumer's spec would be a *prior* hand-edit, irrelevant to this run's signal. The writer reports `orphaned` and stops; it does not race the existing `updated`-vs-`aborted` ladder for the same consumer.
- **Needs-init-and-affected**: structurally impossible — `needs-init` is sourced from the commands-axis report; no on-disk spec means no Table 2 to compute `affected[C]` from.
- **Unaffected-but-orphaned**: never — the orphan check fires first.

### Why `needs-init` and `orphaned` are advisory, not transitional

`updated` and `aborted` describe *transitions of a spec file* between HEAD and the working tree. `needs-init` and `orphaned` describe a *state mismatch* between the commands diagram and the spec-file set — there is nothing for the writer (or the future code updater) to surgically edit:

- `needs-init`: no spec exists; the operator must run a creation pipeline (`/messaging-spec:generate-code`) that the update pipeline cannot reuse safely (see [`commands-queries-integration-approach.md`](commands-queries-integration-approach.md) § "Reconsidering the Step 0c …" — option A wins precisely because consumer-spec init is interview-driven and code-side).
- `orphaned`: a spec exists; the operator must *decide* what to do with it (preserve hand-authored notes? rename? delete and re-init under a new name?) — automating deletion would violate the operator-controls-the-file-system principle ([`commands-queries-integration-approach.md`](commands-queries-integration-approach.md) § "Alternatives considered" row 4).

Both are escalations from the existing `Warnings:` mechanism into first-class per-consumer rows, because they each warrant a per-consumer block (with specific reconcile data) rather than a single Summary bullet.

---

## Advisory block shapes

The existing per-consumer block has three forms (`updated`, `aborted`, `unaffected`). The two new forms below replace the equivalent `Warnings:` lines proposed in [`commands-queries-integration-approach.md`](commands-queries-integration-approach.md) § "Step 7" with full H3 blocks alphabetized into the consumer list.

### `needs-init` block

Bullets, in this fixed order:

- **`Spec:`** — `_not yet created_` (literal italic) — there is no path to render.
- **`Commands diagram declaration:`** — `\`%% Messaging - <C>\` in \`<dir>/<stem>.commands.md\``.
- **`Subscriptions declared in commands diagram:`** — a sub-bullet list, one per `Row added` line in the commands-updates report's `### \`<C>\` (consumer added)` block, copied verbatim (e.g. `` `OrderCommands --() ItemReserved : handles (Inventory, on_item_reserved)` ``).
- **`Operator action:`** — exactly one sub-bullet: `Run \`/messaging-spec:generate-code <domain_diagram> <C>\` to initialize the consumer spec and scaffold its submodule.`

Rationale:

- No pre/post hashes — there is no file.
- The full subscription list is copied from the commands-updates report (not re-parsed from the commands diagram) so this writer never opens the diagram itself — the writer's "no commands-diagram parsing" property from [`../agents/messaging-updates-writer.md`](../agents/messaging-updates-writer.md) § "What this agent deliberately does NOT do" stays intact.
- A single, exact operator action — the same one [`commands-queries-integration-approach.md`](commands-queries-integration-approach.md) § "Step 7" prescribes.

### `orphaned` block

Bullets, in this fixed order:

- **`Spec:`** — `<dir>/<stem>.messaging/<C>.md` with the literal suffix ` (unchanged this run)` (mirroring the `aborted` block's existing convention).
- **`Commands diagram declaration:`** — `_no \`%% Messaging - <C>\` block in \`<dir>/<stem>.commands.md\`_` (literal italic).
- **`Stale subscriptions on the spec:`** — a sub-bullet list, one per internal Table 2 row currently on the spec, rendered as `` `<EventName>` (internal · source `<SourceDestination>`) — bound to `<CommandClass>.<command_method>` ``. External rows are listed analogously but with `external · source` (the source destination on an external row points to the external publisher). When the spec's Table 2 is empty, render the single sub-bullet `_no subscriptions on the spec_`.
- **`Operator action:`** — two sub-bullets:
  - `Decide whether to preserve the spec file (e.g. hand-authored notes) or delete it; the commands diagram no longer declares this consumer.`
  - `After deciding, run \`/messaging-spec:generate-code <domain_diagram>\` (without a consumer arg) to reconcile the messaging submodule's code side; the orphaned consumer's submodule will be flagged for removal.`

Rationale:

- The spec is still there — render its path, mark it unchanged-this-run.
- Listing the stale subscriptions makes the operator's "preserve or delete" decision actionable: they see what semantic content is at stake before deleting.
- Two actions, not one — the spec file is operator-owned (manual decision), the code side is `/messaging-spec:generate-code`'s reconcile job. The orchestrator's Step-7 WARNING text from [`commands-queries-integration-approach.md`](commands-queries-integration-approach.md) is a one-liner; the block expands on it.

### Summary bullet additions

`## Summary` grows two new count lines, after the existing four (`discovered`/`updated`/`aborted`/`unaffected`):

- `Consumers needing init: <i>`
- `Consumers orphaned (commands diagram dropped marker): <o>`

The identity `updated + aborted + unaffected + needs-init + orphaned = discovered` holds (`discovered` now counts the union of on-disk + commands-declared consumers — see *Consumer enumeration* below).

### Operator Actions section

Add a new H2 between `## Consumer Changes` and `## Affected Artifacts`:

```markdown
## Operator Actions

<one bullet per needs-init consumer, in alphabetical order>
- `<C>` — run `/messaging-spec:generate-code <domain_diagram> <C>` to initialize the consumer.

<one bullet per orphaned consumer, in alphabetical order>
- `<C>` — preserve or delete `<dir>/<stem>.messaging/<C>.md`, then run `/messaging-spec:generate-code <domain_diagram>` to reconcile the submodule.
```

When the lists are both empty, omit the section entirely (no `_no actions_` placeholder). This section is the *consolidated* operator-action list — easy to scan; mirrors the `## Affected Artifacts` footer's "flat dispatch list" ergonomics but for human actions rather than machine ones.

Rejected alternative: a single combined `## Affected Artifacts` table with an `Action` value of `init` or `delete-or-preserve`. Three problems: (a) `## Affected Artifacts` is the machine-parseable dispatch input for the future code updater, and its action vocabulary is `{add, modify, remove}` ([`updates-report.md`](updates-report.md) § "Section: Affected Artifacts"); (b) the operator's `orphaned` action is not deterministic (preserve vs delete is a judgment call), violating the table's "code updater walks top-to-bottom" contract; (c) X1's "init" is a *creation pipeline*, not an edit to an existing file — `/messaging-spec:generate-code`'s entry point is `/messaging-spec:generate-code`, not the code updater. A separate H2 cleanly separates operator-decision items from code-updater dispatch.

---

## Consumer enumeration

Today the writer enumerates from the file system: every `<dir>/<stem>.messaging/*.md` except `updates.md` itself ([`../agents/messaging-updates-writer.md`](../agents/messaging-updates-writer.md) § "Step 1"). For X1 this misses consumers that exist only in the commands diagram. For X2 it under-classifies — a consumer is present on disk but flagged as `unaffected` even though its commands-diagram block is gone.

### New rule

```
consumers_on_disk        := set of basenames in <dir>/<stem>.messaging/*.md (minus updates.md)
consumers_added_by_cmd   := from commands-updates.md, the set of consumers with a `(consumer added)` heading
consumers_removed_by_cmd := from commands-updates.md, the set of consumers with a `(consumer removed)` heading
consumers_changed_by_cmd := from commands-updates.md, the set of consumers with a `### \`<C>\`` heading and no lifecycle marker (X3/X4/X5)

discovered := consumers_on_disk ∪ consumers_added_by_cmd
```

Per-consumer status assignment (after precedence resolution):

- `<C> ∈ consumers_added_by_cmd \ consumers_on_disk` → `needs-init`
- `<C> ∈ consumers_removed_by_cmd ∩ consumers_on_disk` → `orphaned`
- `<C> ∈ consumers_on_disk ∩ (consumers_added_by_cmd ∪ consumers_removed_by_cmd)` → degenerate but possible (operator added then removed the marker in different commits before running updates) — apply precedence: orphaned wins, so `<C>` is `orphaned`. The "added then removed" case is rare; the precedence keeps the report deterministic.
- All other `<C> ∈ consumers_on_disk` → existing domain-axis pipeline (`aborted` / `updated` / `unaffected`).

### Source of truth for the commands-axis consumer set

The writer reads `commands-updates.md`'s `## Messaging Markers` H2 only — it does **not** parse the commands diagram itself. Reasons:

- Same architectural property as today (the writer never opens the Mermaid diagram). Preserves the per-consumer Table 2 as the authoritative on-disk mirror of the diagram for `updated`/`aborted`/`unaffected` consumers; for `needs-init`/`orphaned` consumers, the commands-updates report is the authoritative source.
- The detector already handles the parsing (the `## Messaging Markers` section ships exactly the lifecycle markers needed). Re-parsing in the writer duplicates work and risks drift.
- When `commands-updates.md` is absent, X1/X2 detection is impossible *by construction* — the writer cannot infer "consumer added in the diagram but no spec on disk" without the diagram delta; today's behaviour (file-system enumeration only) is the safe degraded mode.

### Consumer ordering

H3 blocks remain alphabetical by consumer name, regardless of status — `needs-init`, `orphaned`, `updated`, `aborted`, and `unaffected` interleave by name (no status grouping). Same convention as today (cf. [`../skills/updates-report-template/SKILL.md`](../skills/updates-report-template/SKILL.md) § "Consumer ordering").

---

## Source attribution on `updated` consumers

Today an `updated` block's sub-block `Source delta:` is always a `domain-events: ...` phrase (cf. [`../skills/updates-report-template/SKILL.md`](../skills/updates-report-template/SKILL.md) § "`updated` block body"). With the commands-axis integrated, two more origins are possible:

- **`messaging-markers` (X3/X4/X5)** — the consumer's `%% Messaging` block changed a row inside the existing consumer.
- **`external-domain-events` (M7)** — an `external` event the consumer subscribes to had an attribute add/remove/rename.

Mirror [`../../application-spec/agents/application-updates-writer.md`](../../application-spec/agents/application-updates-writer.md) § "Step 5 — Source-delta enrichment (best-effort, three-axis)": tag each `Source delta` with the axis that produced it. The two messaging axes are `[domain]` and `[commands-diagram]`. (There is no queries axis here — messaging is command-side only.)

### Probe order per sub-block

For each regenerated `internal`-event sub-block on an `updated` consumer:

1. **Commands-diagram axis** — probe `commands-updates.md`:
   - `## Messaging Markers → ### \`<C>\`` — find a `Row added` / `Row removed` / `Row changed` line whose event name matches the sub-block's event. If present, build `[commands-diagram] messaging-markers: row <verb> (<verbatim row text>)`. This is the most specific signal.
   - When the sub-block's event is `external`, additionally probe `## External Domain Events → ### \`<EventName>\``. If present with an `Attribute added` / `Attribute removed` / `Attribute changed` bullet, build `[commands-diagram] external-domain-events: <EventName> attribute <attr> <verb>`.
2. **Domain axis** — probe `<dir>/<stem>.domain/updates.md`:
   - For an `internal` sub-block whose event is in `event_attr_deltas`, build `[domain] domain-events: <EventName> attribute <attr> <verb>` (the existing behaviour; just gain the `[domain]` prefix).
3. **Fallback** — literal `(unknown source)`.

When multiple probes match (e.g. an internal-event attr delta on the domain side *and* a row-change on the commands side touching the same event), prefer the **commands-diagram axis** — the operator's most specific edit. Mirrors the application-spec precedence rule ([`../../application-spec/agents/application-updates-writer.md`](../../application-spec/agents/application-updates-writer.md) § "5.3 Tie-breaking and idempotency").

### Why tag every sub-block, not the consumer block

A single `updated` consumer's Table 3 can carry sub-blocks driven by *different* axes (one `internal`-event attr change ⊕ one `external`-event attr change). Per-sub-block tagging is the only way to attribute correctly without losing detail; mirrors the application writer's per-entry tagging.

### Rename collapsing

When the commands-axis report shows `Row changed: ... DomainTypeUpdated : handles (Old, on_x) → ... : handles (ConversionReqs, on_domain_type_updated)` — a handler-binding rename — collapse the source-delta phrase to `[commands-diagram] messaging-markers: row changed (handler binding renamed)` rather than dumping the full verbatim row. Same rationale as the existing attribute-renamed collapse rule ([`../agents/messaging-updates-writer.md`](../agents/messaging-updates-writer.md) § "Step 5.5").

---

## Failure modes when `commands-updates.md` is missing

Mirror the existing missing-`domain/updates.md` posture exactly. The writer is **standalone-invocable** and **non-orchestrator-coupled** — both upstream detectors are independent and either may be absent.

| Condition | Behaviour |
|---|---|
| `<dir>/<stem>.application/commands-updates.md` not on disk | Record `commands_updates_present = false`. X1/X2 detection is silently skipped (`consumers_added_by_cmd` and `consumers_removed_by_cmd` are both empty). `Source delta` probes against the commands axis are silently skipped — phrases fall back to `[domain]` or `(unknown source)`. Append a warning per `## Summary`'s warning rule: `commands-diagram updates source not found; commands-axis source-delta probes skipped and X1/X2 advisory blocks could not be computed.` |
| `<dir>/<stem>.application/commands-updates.md` present but missing the `## Messaging Markers` heading (e.g. queries-side report mis-symlinked, or commands report with zero messaging deltas — section omitted per the empty-section rule) | Treat as "no messaging-marker deltas". Bind `consumers_added_by_cmd = consumers_removed_by_cmd = ∅`. The `Source delta` probe against `## External Domain Events` is still attempted. No warning is emitted — the absent section is a valid no-op signal. |
| `<dir>/<stem>.application/commands-updates.md` present but malformed (no recognisable H2 sections at all) | Hard-fail with: `ERROR: <commands_updates_file> is malformed; cannot locate expected headings. Re-run /application-spec:commands-updates-detector <domain_diagram> to rebuild it.` Same posture as the existing malformed-domain-updates hard-fail. |
| `<dir>/<stem>.application/commands-updates.md` reports `_warning: HEAD ..._` (degraded commands baseline) | Non-fatal; pass through. The detector already absorbed the degradation; the writer trusts its signal. No special handling beyond reading the report normally. (The orchestrator's per-axis preflight gate handles degradation upstream — by the time this writer runs, the orchestrator has either disabled the commands axis or proceeded; the writer doesn't second-guess.) |
| Both `<domain_updates_file>` AND `<commands_updates_file>` missing | Every `Source delta` falls back to `(unknown source)`. The existing "domain updates source missing" warning fires; the new "commands-diagram updates source missing" warning also fires. The writer still emits a report (the contract that `updates.md` always exists after a successful run holds). |

The X1/X2 silent-skip rule is the load-bearing operator-experience property: a writer run with only the domain detector's output (e.g. the operator only edited the domain diagram, never touched the commands diagram, so no `commands-updates.md` was produced) **still produces a valid report** — it just describes the domain-axis transitions only. This matches the existing behaviour for missing `domain/updates.md`.

---

## `## Affected Artifacts` footer policy

Today only `updated` consumers contribute rows ([`../skills/updates-report-template/SKILL.md`](../skills/updates-report-template/SKILL.md) § "`## Affected Artifacts` computation"). The new statuses contribute **zero rows**:

- **`needs-init` consumers** — there is no on-disk artifact yet. The code updater cannot dispatch against a path that does not exist; the operator-driven `/messaging-spec:generate-code` pipeline creates the artifacts. Including a synthetic `messaging/<C_snake>/handlers.py | add | <C>` row would be misleading (the path doesn't exist; the code updater would have nothing to read from disk to compute an "add"; and the create pipeline owns the structure, not the updater). They surface only in `## Operator Actions`.
- **`orphaned` consumers** — the spec is unchanged this run; the existing handler/test artifacts are byte-stable on the messaging-update axis. Cleanup is operator-decision-gated (preserve vs delete); a synthetic `messaging/<C_snake>/handlers.py | remove | <C>` row would commit the code updater to a destructive action before the operator decided. Surface only in `## Operator Actions`.

Action vocabulary stays closed at `{add, modify, remove}` (existing rule). Driving-consumer column stays the consumer name in backticks.

The future `/messaging-spec:update-code` consumer is therefore **unchanged** — it walks the same footer top-to-bottom; the new advisory rows live in a separate section it can either ignore or render to the operator (a small UX enhancement, but not a breaking change). This is exactly the cross-axis-friendly contract the application-updates-writer's design tooled for ([`../../application-spec/agents/application-updates-writer.md`](../../application-spec/agents/application-updates-writer.md) § "What this agent deliberately does NOT do" — second-to-last bullet on "It does not detect orphan tests …").

### Open: should we surface the X1/X2 rows in a second footer?

Considered: a `## Operator Action Artifacts` footer table mirroring `## Affected Artifacts`'s shape (`| Path | Action | Driving consumer |`) so machine consumers (a future tooling pass that wants to generate per-consumer Slack messages, e.g.) can dispatch operator-actions without re-parsing prose.

**Rejected** for v1. The `## Operator Actions` H2 (above) is structured enough — one bullet per consumer, each ending in a backticked path or command. A second table is over-structuring for a pair of human-decision items. Re-evaluate when a machine consumer materializes.

---

## Idempotency

Byte-stable inputs → byte-identical report. Inputs:

1. Working-tree consumer specs.
2. HEAD blobs of consumer specs.
3. `<dir>/<stem>.domain/updates.md` (or its absence).
4. `<dir>/<stem>.application/commands-updates.md` (or its absence).
5. Consumer set from the file system + from `commands-updates.md`'s `## Messaging Markers` lifecycle markers.

All five are deterministic functions of the working tree + git HEAD. No timestamps, no LLM-creative phrasing inside this writer (the commands-updates-detector's LLM prose summary lives in its own report, not here). The writer reads them, parses them with byte-deterministic rules, and renders.

Per-axis idempotency:

- A re-run with no changes since the last commit yields a report whose every consumer is `unaffected` (or the appropriate advisory if the commands diagram declared/dropped a marker) and whose `## Affected Artifacts` table has the header row only.
- Re-running after committing the prior writer's output diffs the *current* working tree against HEAD; the report describes what changed since the new commit, which is "nothing" — same `unaffected` shape.

Two new sentinels join the existing `<!-- domain-updates-hash:<sha256> -->`:

```
<!-- domain-updates-hash:<sha256> -->
<!-- commands-updates-hash:<sha256> -->
```

Order matches the application-updates-writer's sentinel order (domain first, then commands). Each sentinel is `(none)` when its source file is missing. The future `/messaging-spec:update-code` consumer can early-exit when *all* sentinels match a previously-applied report.

(No `queries-updates-hash` sentinel — messaging is command-side only; the queries detector report is never consulted by this writer.)

---

## Companion `messaging-spec:updates-report-template` skill changes

The skill is the single source of truth for the output schema. The writer's design above implies the following skill edits — to apply when implementing this design.

### Top-of-file sentinel block

Replace the single-line sentinel form with a two-line block:

```
<!-- domain-updates-hash:<sha256> -->
<!-- commands-updates-hash:<sha256> -->
```

Both lines always emitted; either is `(none)` when its source file is missing. Rendering rule: emit `domain-updates-hash` first, then `commands-updates-hash`, then one blank line, then the `# Messaging Updates Report` heading. Same convention as the application-updates-writer's three-line block, scaled to two.

### `## Summary` section

Add two count lines after the existing four:

```markdown
- Consumers needing init: <N>
- Consumers orphaned (commands diagram dropped marker): <N>
```

Update the count identity to: `updated + aborted + unaffected + needs-init + orphaned = discovered`.

Add a new line listing the second updates source:

```markdown
- Commands-diagram updates source: `<dir>/<stem>.application/commands-updates.md` (hash: <sha256>) | _none_
```

Emitted between the existing `Domain updates source` line and the consumer count lines.

Extend the Warnings vocabulary with:

- `commands-diagram updates source not found; commands-axis source-delta probes skipped and X1/X2 advisory blocks could not be computed` — when `<commands_updates_file>` is missing.

### Status vocabulary table

Extend the existing table in § "H3 heading form and the status vocabulary" with two new rows:

| Status | When |
|---|---|
| `needs-init` | The commands diagram declares a `%% Messaging - <C>` block for which no consumer spec exists on disk. The commands-updates report lists `<C>` as `(consumer added)` under `## Messaging Markers`. The spec must be initialized via `/messaging-spec:generate-code <domain_diagram> <C>` before this consumer can participate in updates. |
| `orphaned` | A consumer spec exists on disk but the commands diagram no longer declares its `%% Messaging - <C>` block. The commands-updates report lists `<C>` as `(consumer removed)` under `## Messaging Markers`. The spec is unchanged this run. Operator action: preserve or delete the spec file, then re-run `/messaging-spec:generate-code <domain_diagram>` to reconcile the code side. |

Update the existing precedence note: "A consumer is never simultaneously `updated` and `aborted` …" → extend to "Status precedence is `orphaned → aborted → needs-init → updated → unaffected` (first match wins). `orphaned` and `needs-init` are advisory — they describe a state mismatch between the commands diagram and the on-disk spec set, not a transition of a single file."

### Two new block-body sub-sections

Add `### \`needs-init\` block body` and `### \`orphaned\` block body` sections, each with the bullet list shape from § "Advisory block shapes" above.

### `## Operator Actions` section

Add a new H2 between `## Consumer Changes` and `## Affected Artifacts` in the canonical section order. Document:

- Always-emitted when at least one `needs-init` or `orphaned` consumer exists; otherwise omitted entirely.
- One bullet per advisory consumer, in alphabetical order (interleaving `needs-init` and `orphaned`).
- Bullet shape (verbatim, per status): see § "Operator Actions section" above.

Update the canonical top-level section ordering:

```
1. ## Summary
2. ## Consumer Changes
3. ## Operator Actions       (NEW — omit when empty)
4. ## Affected Artifacts
```

### `## Affected Artifacts` footer

No change. Add a single sentence to § "`## Affected Artifacts` computation": "`needs-init` and `orphaned` consumers contribute **zero rows** — they surface in `## Operator Actions` only. The footer's action vocabulary remains `{add, modify, remove}`; `init` and `delete-or-preserve` are operator-decisions, not code-updater dispatch entries."

### Source delta phrase grammar

Extend the existing rendering rule to accept the axis-tagged form (mirroring the application-updates-writer):

```
Source delta: [<axis>] <category>: <human_phrase>
```

Where `<axis>` ∈ `{domain, commands-diagram}` and `<category>` is `domain-events` (for the `[domain]` axis) or one of `messaging-markers` / `external-domain-events` (for the `[commands-diagram]` axis). Add the literal `(unknown source)` fallback rule.

Add a worked example showing a single `updated` consumer with one `[domain] domain-events: …` sub-block and one `[commands-diagram] messaging-markers: …` sub-block, demonstrating mixed-axis attribution within a consumer.

### Determinism contract

Extend the list of byte-stable inputs to include `<dir>/<stem>.application/commands-updates.md`. Update the determinism contract to: "Byte-stable inputs (working-tree consumer specs, HEAD consumer specs, sibling `<dir>/<stem>.domain/updates.md`, sibling `<dir>/<stem>.application/commands-updates.md`, sibling `<dir>/<stem>.commands.md`) → byte-stable report."

---

## What this design does NOT change

- **The agent's first positional argument** — still `<domain_diagram>`. The writer derives `<commands_updates_file>` by sibling-path resolution (`<dir>/<stem>.application/commands-updates.md`), same as it derives `<domain_updates_file>` today.
- **The "writer never opens the commands diagram" property** — preserved. The writer reads `commands-updates.md`'s `## Messaging Markers` block; the detector did the Mermaid parsing.
- **The `## Consumer Changes` block ordering** — alphabetical by consumer name across all five statuses, no status grouping.
- **The existing `updated` / `aborted` / `unaffected` block bodies** — unchanged (modulo `Source delta`'s new axis tag).
- **The existing `Warnings:` mechanism** — retained for the warning categories already in the skill (`Dead subscription`, `Subscription candidate`, `First-run consumer`, `Domain updates source missing`); add one new category (`Commands-diagram updates source missing`). X1/X2 are *no longer* warnings — they are first-class statuses with their own H3 blocks.
- **The future `/messaging-spec:update-code` consumer contract** — the footer is unchanged. The new advisory blocks are informational; the code updater can ignore the `## Operator Actions` H2 entirely if it wants to.
- **The `<dir>/<stem>.messaging/<consumer>.md` schema** — unchanged. The advisory statuses are about the *absence* (X1) or *staleness* (X2) of a spec, not its contents.

---

## What this design DOES change

| File | Change |
|---|---|
| [`plugins/messaging-spec/agents/messaging-updates-writer.md`](../agents/messaging-updates-writer.md) | Extend Step 1 to also resolve `<commands_updates_file>` and treat its absence as non-fatal. Add Step 2.5 (or fold into Step 2): parse `commands-updates.md`'s `## Messaging Markers` for `consumers_added_by_cmd` + `consumers_removed_by_cmd`. Extend Step 4 enumeration to the union rule. Extend Step 5 with the precedence ladder (orphaned → aborted → needs-init → updated → unaffected) and the new sub-block render rules. Extend Step 5's `Source delta` derivation with the commands-axis probes + axis-tagged phrases. Extend Step 6's warnings vocabulary. Extend Step 7's render to include the `commands-updates-hash` sentinel, the new Summary lines, the new H3 block bodies, and the new `## Operator Actions` H2. Update the agent's frontmatter `description` to mention the commands-axis input. |
| [`plugins/messaging-spec/skills/updates-report-template/SKILL.md`](../skills/updates-report-template/SKILL.md) | Apply the changes catalogued in § "Companion `messaging-spec:updates-report-template` skill changes" above (sentinel block, status vocabulary, advisory block bodies, Operator Actions section, axis-tagged Source delta grammar, determinism contract). Bump the skill's stated section ordering. |
| [`plugins/messaging-spec/notes/updates-report.md`](updates-report.md) | Cross-reference this note from § "Open questions" item 2 (the Table 2 regen-folding note already anticipates the commands axis); update the *Status vocabulary* discussion in § "Section: Consumer Changes" to reflect the five-status set. |
| [`plugins/messaging-spec/.claude-plugin/plugin.json`](../.claude-plugin/plugin.json) | Bump `version` — the writer's contract (report schema) changes visibly. |

No new agent. No new skill. The detector agent already exists in application-spec.

---

## Alternatives considered

| Approach | Status | Why not |
|---|---|---|
| **Keep `needs-init`/`orphaned` as Warnings only** (the simplest v1 from [`commands-queries-integration-approach.md`](commands-queries-integration-approach.md) § "Step 6") | rejected | A Warnings line cannot carry the per-consumer reconcile data (subscription list for orphaned; subscription list to be created for needs-init) without bloating the Summary unreasonably. A per-consumer H3 block is the natural unit for "all the information the operator needs to act on this consumer's mismatch". |
| **Synthetic rows in `## Affected Artifacts`** (e.g. `messaging/<C_snake>/ | init | <C>` for needs-init, `messaging/<C_snake>/ | remove | <C>` for orphaned) | rejected | Three reasons: (a) breaks the closed `{add, modify, remove}` action vocabulary; (b) lies to the code updater (the path doesn't exist for X1; deletion is operator-decision-gated for X2); (c) misuses the footer as an operator-action surface, when it is a code-updater dispatch surface. The new `## Operator Actions` H2 is the clean separation. |
| **Single status `mismatched` with a `direction` field** (commands-added vs commands-removed) | rejected | The operator-action shapes are different (`/messaging-spec:generate-code <consumer>` vs preserve-or-delete), the reconcile data is different (declared subscriptions vs stale subscriptions), and the H3 block bodies are different. Collapsing them obscures both. |
| **Have the writer parse the commands diagram directly** for X1/X2 | rejected | Duplicates the detector's Mermaid parsing; risks drift between two parsers; violates the writer's "no diagram opens" property. The commands-updates report is the right interface for the writer to consume. |
| **Auto-init X1 consumers** (writer invokes `consumer-spec-initializer` + `consumer-scaffolder` itself) | rejected | Same reasons [`commands-queries-integration-approach.md`](commands-queries-integration-approach.md) § "Alternatives considered" rejects it at the orchestrator level. The writer is a report generator, not a code-modifying agent — making it modify the spec set would break the layer separation. |
| **Auto-delete X2 orphaned consumer specs** | rejected | Violates the operator-controls-the-file-system principle. The orphaned spec may carry hand-authored notes; the operator may want to rename it; auto-delete forecloses both. |
| **Have the writer's footer include `## Operator Actions` rows in the same table** | rejected | See § "`## Affected Artifacts` footer policy" → "Open: should we surface the X1/X2 rows in a second footer?". A separate H2 keeps `## Affected Artifacts` clean as the code updater's dispatch input. |
| **Promote `[domain]` / `[commands-diagram]` to a per-block bullet** instead of a per-sub-block prefix on `Source delta` | rejected | A single `updated` consumer can have sub-blocks driven by different axes (see § "Why tag every sub-block, not the consumer block"). Per-sub-block tagging is the only correct granularity. |

---

## Open questions

1. **Should the writer hard-fail if the commands diagram declares two consumers with the same name?** The detector already hard-fails on duplicate `%% Messaging - <C>` blocks ([`commands-queries-updates-report.md`](../../application-spec/notes/commands-queries-updates-report.md) § "Hard-fail conditions" — implicit in the "consumer added" / "consumer removed" disjointness). The writer trusts that; double-checking would duplicate detector logic. **Lean: trust the detector.**

2. **What about a consumer that appears as both `(consumer added)` and `(consumer removed)` in the same commands-updates report?** Structurally impossible — the detector compares HEAD to working tree; the same name cannot have appeared in HEAD only and in working tree only at once. If a future detector revision relaxes that, the writer should hard-fail with an explicit error. Defer; not a current concern.

3. **Should the X2 `Operator action:` include a `git rm` suggestion?** Considered. **Rejected** — `git rm` mixes file-system action with VCS staging; the operator may want to keep the file unstaged. The recommendation stays "preserve or delete" — the operator picks the tool.

4. **Should we offer a `--auto-orphan-cleanup` flag** that runs `git rm <orphaned-spec>` for the operator? Considered. **Rejected for the writer** — a flag belongs on `/messaging-spec:generate-code`, not on a report producer. The writer's job is to report; the cleanup is a code-action.

5. **The X1 block lists subscriptions but cannot describe Table 3.** The detector report shows `Row added: <CommandClass> --() <Event> : handles (<Source>, <on_method>)` for an X1 consumer — that's the subscription, not the parameter mapping (Table 3 would require running `event-fields-writer` against a spec that doesn't exist yet). The X1 block's subscription list is therefore *what will be subscribed*, not *what is subscribed*. The block body language should make this distinction explicit ("Subscriptions declared in commands diagram:" — note the *declared*; the actual Table 3 is computed during init).

6. **`## Operator Actions` ordering: by status or by name?** Two alternatives: (a) alphabetical by name (matches `## Consumer Changes` ordering); (b) grouped by status (all `needs-init` first, then all `orphaned`). **Lean: alphabetical by name.** Operator scans the report for "what's broken about my favorite consumer" — finding it in the same alphabetical slot in both sections is cognitively cheaper than two sort orders to track.

7. **What if `<commands_updates_file>` exists but is older than `<domain_updates_file>` (stale detector run)?** The writer doesn't compare timestamps — it trusts the file on disk. Stale reports are an operator-workflow issue (re-run the detector). The hash sentinel records what *this* writer run saw; the future `/messaging-spec:update-code` consumer can compare. **No staleness check in the writer.**

---

## Failure semantics (terminal summary)

- **Missing `<commands_updates_file>`** — non-fatal; X1/X2 silently skipped; commands-axis source-delta probes skipped; warning emitted in `## Summary`. Same posture as missing `<domain_updates_file>`.
- **Malformed `<commands_updates_file>`** — hard-fail with `ERROR: <commands_updates_file> is malformed; cannot locate expected headings. Re-run /application-spec:commands-updates-detector <domain_diagram> to rebuild it.` Mirrors the existing malformed-domain-updates hard-fail.
- **`commands-updates.md` claims a consumer was added that already exists on disk** — silently degrade to `updated`/`unaffected` per the existing pipeline; do **not** hard-fail (the detector's lifecycle classification could be momentarily out of sync with the operator's working tree, e.g. an operator committed the consumer spec after the detector ran but before the writer ran). Emit a warning: `consumer <C> reported as added by commands-updates.md but spec exists on disk; treating as on-disk-only.`
- **`commands-updates.md` claims a consumer was removed that does not exist on disk** — silently degrade to "ignore the signal"; do **not** hard-fail. Same operator-race rationale. Emit a warning: `consumer <C> reported as removed by commands-updates.md but spec does not exist on disk; treating as absent.`

Both silent-degrade rules are *consistent* with the writer's standing posture: it reports state, doesn't enforce it; the operator owns the file system.

---

## Worked example

Operator edits the commands diagram for an `order` aggregate to: (a) add a new `%% Messaging - inventory-sync` block subscribing to two new external events `ItemReserved` and `ItemReleased`; (b) delete the existing `%% Messaging - shipping-events` block entirely; (c) add a row inside the existing `%% Messaging - profile-reconciliation` block subscribing to a new internal event. They also edit the domain diagram to add an attribute to the existing internal event `ProfileSubmitted`.

After the orchestrator's pipeline, `<dir>/order.application/commands-updates.md` exists with `## Messaging Markers` containing:

```markdown
### `inventory-sync` (consumer added)
- Row added: `OrderCommands --() ItemReserved : handles (Inventory, on_item_reserved)`
- Row added: `OrderCommands --() ItemReleased : handles (Inventory, on_item_released)`

### `profile-reconciliation`
- Row added: `OrderCommands --() ProfileUpdated : handles (Profiles, on_profile_updated)`

### `shipping-events` (consumer removed)
```

And `<dir>/order.domain/updates.md`'s `event_attr_deltas` reports `ProfileSubmitted` got `region: str` added.

The on-disk `<dir>/order.messaging/` contains `audit-log.md`, `profile-reconciliation.md`, `shipping-events.md` (three pre-existing specs).

The writer's output `<dir>/order.messaging/updates.md`:

```markdown
<!-- domain-updates-hash:abcd... -->
<!-- commands-updates-hash:1234... -->

# Messaging Updates Report

## Summary

- Messaging folder: `dir/order.messaging/`
- Commands diagram: `dir/order.commands.md`
- Domain updates source: `dir/order.domain/updates.md` (hash: abcd...)
- Commands-diagram updates source: `dir/order.application/commands-updates.md` (hash: 1234...)
- Consumers discovered: 4
- Consumers updated: 1
- Consumers aborted (reconcile commands diagram): 0
- Consumers unaffected: 1
- Consumers needing init: 1
- Consumers orphaned (commands diagram dropped marker): 1

## Consumer Changes

### `audit-log` — unaffected

_No internal subscription intersects the changed-domain-event set._

### `inventory-sync` — needs-init

- Spec: _not yet created_
- Commands diagram declaration: `%% Messaging - inventory-sync` in `dir/order.commands.md`
- Subscriptions declared in commands diagram:
  - `OrderCommands --() ItemReserved : handles (Inventory, on_item_reserved)`
  - `OrderCommands --() ItemReleased : handles (Inventory, on_item_released)`
- Operator action:
  - Run `/messaging-spec:generate-code dir/order.md inventory-sync` to initialize the consumer spec and scaffold its submodule.

### `profile-reconciliation` — updated

- Spec: `dir/order.messaging/profile-reconciliation.md`
- Pre-update hash: a1b2c3...
- Post-update hash: d4e5f6...
- Table 2 refreshed: added: `ProfileUpdated`
- Table 3 sub-blocks regenerated:
  - `**Event:** ProfileSubmitted` (internal · source `Profiles`)
    - Source delta: [domain] domain-events: ProfileSubmitted attribute region added
    - Event Field mappings changed:
      - row `region` ↦ `region` added
    - Low-confidence flags: _none_
  - `**Event:** ProfileUpdated` (internal · source `Profiles`)
    - Source delta: [commands-diagram] messaging-markers: row added (`OrderCommands --() ProfileUpdated : handles (Profiles, on_profile_updated)`)
    - Event Field mappings changed:
      - row `profile_id` ↦ `profile_id` added
      - row `updated_at` ↦ `updated_at` added
    - Low-confidence flags: _none_

### `shipping-events` — orphaned

- Spec: `dir/order.messaging/shipping-events.md` (unchanged this run)
- Commands diagram declaration: _no `%% Messaging - shipping-events` block in `dir/order.commands.md`_
- Stale subscriptions on the spec:
  - `OrderShipped` (internal · source `Order`) — bound to `OrderCommands.on_order_shipped`
- Operator action:
  - Decide whether to preserve the spec file (e.g. hand-authored notes) or delete it; the commands diagram no longer declares this consumer.
  - After deciding, run `/messaging-spec:generate-code dir/order.md` (without a consumer arg) to reconcile the messaging submodule's code side; the orphaned consumer's submodule will be flagged for removal.

## Operator Actions

- `inventory-sync` — run `/messaging-spec:generate-code dir/order.md inventory-sync` to initialize the consumer.
- `shipping-events` — preserve or delete `dir/order.messaging/shipping-events.md`, then run `/messaging-spec:generate-code dir/order.md` to reconcile the submodule.

## Affected Artifacts

| Path | Action | Driving consumer |
|---|---|---|
| `messaging/profile_reconciliation/handlers.py` | modify | `profile-reconciliation` |
| `tests/integration/messaging/profile_reconciliation/test_profile_reconciliation_handlers.py` | modify | `profile-reconciliation` |
```

Notice:

- Four consumers `discovered` — union of three on-disk and `inventory-sync` from the commands-updates report.
- `profile-reconciliation` is `updated` with two sub-blocks tagged with *different* axes — `[domain]` for the attribute-add, `[commands-diagram]` for the row-add.
- `inventory-sync` carries no pre/post hash because its spec doesn't exist; its declared subscriptions come straight from the commands-updates report.
- `shipping-events` carries its stale subscription (read from its own on-disk Table 2) so the operator sees what semantic content is at stake before deciding.
- `## Operator Actions` consolidates the two human-action items into one easy-to-scan list, alphabetical by consumer name.
- `## Affected Artifacts` lists only the `updated` consumer's two artifacts. No `add` row for `inventory-sync`. No `remove` row for `shipping-events`. The footer stays a strict code-updater dispatch list.

---

## Implementation order (for the follow-up session)

1. **Apply the skill changes** to `plugins/messaging-spec/skills/updates-report-template/SKILL.md` per § "Companion `messaging-spec:updates-report-template` skill changes". The skill is the contract; the agent body should follow.
2. **Extend the agent body** in `plugins/messaging-spec/agents/messaging-updates-writer.md` per § "What this design DOES change" → first row. Specific changes:
   - Step 1 path derivation + presence check for `<commands_updates_file>`.
   - Step 2 extended: parse `commands-updates.md`'s `## Messaging Markers` (and `## External Domain Events` for sub-block source-delta probes) into structured form.
   - Step 4 / Step 5 (consumer enumeration + bucketing) extended with the union rule + precedence ladder.
   - Step 5 (source delta) extended with the axis-tagged form + commands-axis probes.
   - Step 6 (warnings) extended with the new categories.
   - Step 7 (render) extended with the new sentinel, summary lines, advisory block bodies, and Operator Actions section.
   - Hard-fail table extended with the malformed-commands-updates entry.
   - Idempotency contract restated to include the commands-updates input.
   - Frontmatter `description` updated.
3. **Update the design note** `plugins/messaging-spec/notes/updates-report.md` per § "What this design DOES change" → third row.
4. **Bump** `plugins/messaging-spec/.claude-plugin/plugin.json` `version`.
5. **Cross-reference** from [`commands-queries-integration-approach.md`](commands-queries-integration-approach.md): mark § "Open questions" item 1 (the v2 writer extension) as resolved by this note, and update § "What this DOES change" → final two rows from "(optional v1, recommended v2)" to "v2 — see [messaging-updates-writer-commands-axis.md](messaging-updates-writer-commands-axis.md)".

No new files beyond this note. No agent additions. No skill additions. The detector agent already exists in application-spec.
