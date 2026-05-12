# Messaging Spec Updater — Design (Thin Domain-Chained Dispatcher)

This note documents the recommended design of `/messaging-spec:update-specs`, the update skill for the messaging consumer input specs at `<dir>/<stem>.messaging/<consumer_name>.md`. It is the messaging-side counterpart to `/update-specs` for `domain-spec`, `/persistence-spec:update-specs` for persistence, and the (designed-not-yet-built) application-spec updater.

For the catalog of update types and their per-table impact, see the sibling [`update-types.md`](update-types.md).
For the upstream domain updater design that this skill chains onto, see [`plugins/domain-spec/notes/spec-updater-approach-b.md`](../../domain-spec/notes/spec-updater-approach-b.md).
For the persistence updater that establishes the "chained tail step" pattern, see [`plugins/persistence-spec/notes/spec-updater-approaches.md`](../../persistence-spec/notes/spec-updater-approaches.md).
For the application updater's treatment of a multi-diagram trigger surface (the closest structural analog), see [`plugins/application-spec/notes/update-types.md`](../../application-spec/notes/update-types.md) and [`plugins/application-spec/notes/spec-updater-approach.md`](../../application-spec/notes/spec-updater-approach.md).

The chosen approach is **a thin, domain-chained dispatcher** — *not* a surgical splicer. The reasoning, the pipeline, and the deliberate scope cut (no commands-diagram detector) are below.

---

## Goal

Keep every `<stem>.messaging/<consumer_name>.md` aligned with the domain diagram after a domain change, **without requiring manual operator edits to the consumer specs**, and with proper guardrails when the change is too structural to absorb. The updater:

- Runs as **Step 13** (the last of the four downstream chain steps) at the tail of `/update-specs` (domain), invoked unconditionally on the domain updater's success path — but it is internally a no-op when `<stem>.messaging/` is empty or absent, so a missing messaging layer never aborts the cascade (unlike the persistence/application/rest-api chain steps, whose missing-artifact hard-fail does).
- May be invoked standalone for cases where the domain spec is up-to-date but a consumer spec drifted.
- Consumes the same `<stem>.domain/updates.md` report the domain and persistence updaters consume.
- Never re-diffs the domain diagram, never invokes `domain-spec:updates-detector` directly.
- Never reads `<stem>.domain/specs.md` — `event-fields-writer` reads the domain *diagram* (`<<Domain Event>>` classes), so the messaging updater can run before / independently of the domain spec being regenerated.
- Does not preserve hand-edits inside a consumer spec — the operator's contract is that the spec is regenerated from the diagrams, not curated. (`event-fields-writer` does re-derive its own italic low-confidence flags around Table 3 from scratch on each run; that is by design.)

---

## Inputs

- `<domain_diagram>` — `<dir>/<stem>.md`, the same first-positional argument every spec-updater orchestrator takes. `<dir>`, `<stem>`, and the derived `<commands_diagram>` = `<dir>/<stem>.commands.md` are recovered per `messaging-spec:naming-conventions`.
- `<dir>/<stem>.domain/updates.md` — already on disk (produced by `domain-spec:updates-detector`, either as Step 0 of `/update-specs` or by an explicit prior invocation).
- `<dir>/<stem>.messaging/<consumer_name>.md` × N — the consumer specs the updater may modify. The updater discovers the consumer set by scanning `<dir>/<stem>.messaging/*.md` (the domain report knows nothing about consumers — they are declared in the commands diagram's `%% Messaging - <consumer_name>` markers).
- `<dir>/<stem>.commands.md` — read-only, by `event-tables-writer` / `event-fields-writer` when they re-run (for Table 2's markers, Table 3's `Command Parameter` column, and `external`-row `Event Field` values).

If `<stem>.domain/updates.md` is missing the updater hard-fails with operator instructions. If `<stem>.messaging/` is empty or absent, the updater is a no-op (nothing to update) — this is the file-presence gate that makes it safe to wire unconditionally into the tail of domain `/update-specs`.

---

## Output

Zero or more `<dir>/<stem>.messaging/<consumer_name>.md` files, modified in place:

- Table 3 (Event Parameter Mapping) of each *affected* consumer is wholesale-regenerated from the current commands + domain diagrams by `event-fields-writer`. Existing content (including italic low-confidence flags) is discarded and re-derived.
- Table 1 and Table 2 are not touched by a domain-driven update in the clean case. (Table 2 may be re-refreshed from the commands diagram as a cheap idempotent side effect — see *Step 4* — but a domain-only change never changes its content; a domain change that *would* change it is a Tier-1 abort-and-reconcile, not a write.)
- The domain diagram is untouched; no other plugin's folder is touched; no backup or rollback file is produced.
- Optionally, a per-update report at `<dir>/<stem>.messaging/updates.md` (see *Optional: the update report*).

---

## Why a thin dispatcher, not a surgical splicer

The domain-spec updater (`spec-updater-approach-b.md`) and the persistence-spec updater (`spec-updater-approaches.md`) are surgical because regen is *destructive* in their world:

- domain-spec regen clobbers hand-edited class-prose blocks across many classes → needs a class-keyed splicer that protects untouched blocks.
- persistence-spec regen would wipe the append-only `§2.Migrations` changeset history → needs a delta-driven appender that never rewrites a committed row.

**Neither hazard exists for the messaging consumer spec:**

- **No append-only history**, no row-immutability contract — every table is a pure snapshot, fully regeneratable from the diagrams.
- **No cross-artifact ripple** — there is no `exceptions.md` / `test-plan.md` derived from the consumer spec, so nothing downstream to refresh after a table change.
- **A tiny surface** — three tables; Table 1 is hand/prefix-derived and never regenerated post-init; Table 2 is a pure function of the commands diagram; only Table 3's `Event Field` column for `internal` rows is domain-sensitive (see `update-types.md` § *The trigger surface*).
- **Wholesale-regenerating agents already exist** — `event-fields-writer` replaces all of Table 3 in place from the current diagrams, and `event-tables-writer` does the same for Table 2. There is no "regenerate sub-block X only" mode, and crucially there is no need for one: "update Table 3 for consumer C" *is* "re-run `event-fields-writer <commands_diagram> C`".

So a splicer agent would be pure overhead. What a dedicated updater *does* buy — and what this design delivers — is **dispatch + guardrails + chaining**:

1. **Hard-fail guards** — catch aggregate-root removal/rename/stereotype-change and stop with operator instructions, instead of letting `event-fields-writer` (or `/messaging-spec:generate-code`) emit garbage. The root rename is especially dangerous: it silently breaks the `<pkg>.domain.<root_snake>` import root baked into every generated dispatcher/handler, and it cascades to `<stem>.commands.md`'s filename and the `<stem>.messaging/` folder name.
2. **Scoping** — re-run `event-fields-writer` only for the consumers whose `internal` Table 2 rows intersect the changed-domain-event set, not all N consumer files.
3. **Abort-and-reconcile detection** — a subscribed internal `<<Domain Event>>` that was removed or renamed leaves the commands diagram's `%% Messaging - <consumer>` marker (and the `<AggregateRoot>Commands.on_<event>` handler) dangling; detect that from `updates.md` and instruct the operator to reconcile the commands diagram first, rather than running `event-fields-writer` blind against an orphaned Table 2 row.
4. **Chaining** — be an opt-in tail step of domain `/update-specs`, exactly as `/persistence-spec:update-specs` is, so "one command updates everything" stays true.

New artifacts for the whole feature: **one skill** (`messaging-spec:update-specs`), optionally **one report file** (`<stem>.messaging/updates.md`). **No new agents** — the skill orchestrates the two existing writers (`event-tables-writer`, `event-fields-writer`) plus the existing `target-locations-finder` only if a downstream agent needs it (the spec writers don't).

---

## Pipeline

```
domain updates.md ──┐
                    ├─► [0] preflight + consumer discovery
domain diagram ─────┤
                    ├─► [1] hard-fail gate
                    │
                    ├─► [2] abort-and-reconcile gate
                    │
                    ├─► [3] compute affected consumers
                    │       (changed-domain-event set ∩ each consumer's `internal` Table 2 rows)
                    │
                    ├─► [4] per affected consumer (parallel):
                    │       event-tables-writer  <commands_diagram> <consumer>   (optional refresh)
                    │       event-fields-writer  <commands_diagram> <consumer>   (regen Table 3)
                    │
                    └─► [5] report
```

---

## Step 0 — Preflight + consumer discovery

Recover `<dir>`, `<stem>`, `<commands_diagram>` per `messaging-spec:naming-conventions`. Parse `<stem>.domain/updates.md` into a working set:

| Variable | Source |
|---|---|
| `removed_classes: { name → stereotype }` | `## Class Lifecycle → Removed` |
| `added_classes: { name → stereotype }` | `## Class Lifecycle → Added` |
| `stereotype_changed: { name → (old, new) }` | `## Class Lifecycle → Stereotype Changed` |
| `event_attr_deltas: { event_name → set(attr added/removed) }` | `## Per-Class Changes` Members rows, restricted to classes whose (post-change) stereotype is `<<Domain Event>>` / `<<Event>>` |
| `removed_or_renamed_events: set` | `<<Domain Event>>` names in `removed_classes` (a rename is `removed (old) + added (new)`, so the old name lands here) |
| `added_events: set` | `<<Domain Event>>` names in `added_classes` |
| `aggregate_root_touched: bool` | true iff an `<<Aggregate Root>>` appears in `removed_classes`, or in `stereotype_changed` (either bucket), or in both `removed_classes`+`added_classes` (a rename) |
| `degraded_baseline: bool` | true iff Summary contains the `_warning: HEAD ..._` line |

Discover consumers and their subscriptions:

| Variable | Source |
|---|---|
| `consumers: [path]` | `<dir>/<stem>.messaging/*.md` (excluding `updates.md`) |
| `internal_subs: { consumer → set(event_name) }` | each consumer's Table 2 rows with Type `` `internal` ``, collected from the `%% Messaging - <consumer>` blocks in `<commands_diagram>` (authoritative) or parsed from the consumer spec's Table 2 (cheaper; the spec mirrors the markers) |

Early exits:

- `consumers` empty → **no-op** (the file-presence gate; nothing to update).
- `degraded_baseline` true → **hard-fail** — route to re-running the consumer-spec pipeline / `/messaging-spec:generate-code` against a clean baseline (mirrors domain/persistence C5).

---

## Step 1 — Hard-fail gate

If `aggregate_root_touched` or `stereotype_changed` is non-empty, **hard-fail**: print exactly one `ERROR:` line and exit.

- **Aggregate root removed / stereotype-demoted** → `ERROR: the aggregate root was removed or re-stereotyped in <stem>.domain/updates.md; the whole diagram set (and every consumer under <stem>.messaging/) is invalid. Reconcile the diagrams, then re-run /messaging-spec:generate-code per consumer.`
- **Aggregate root renamed** → `ERROR: the aggregate root was renamed in <stem>.domain/updates.md; this cascades to <stem>.commands.md's class names + filename, the <stem>.messaging/ folder, the %% Messaging markers' <Source> cells, and the <pkg>.domain.<root_snake> import root in generated code. Rename the diagrams + folder, reconcile the markers, then re-run /messaging-spec:generate-code per consumer.`
- **Any other stereotype change** → `ERROR: a class stereotype changed in <stem>.domain/updates.md; reconcile the diagrams, then re-run /messaging-spec:generate-code per affected consumer.` (Covers `<<Domain Event>>` ⇄ other re-classifications that invalidate `internal` subscriptions.)

No writes occur on a hard-fail.

---

## Step 2 — Abort-and-reconcile gate

Compute `dangling := { (consumer, event) : event ∈ removed_or_renamed_events ∧ event ∈ internal_subs[consumer] }`.

If `dangling` is non-empty, **abort the consumer specs it names** with operator instructions and **do not run Step 4 for those consumers** (other, non-dangling consumers still proceed through Steps 3–4):

```
ERROR: consumer <C> subscribes to internal event <E>, which was removed/renamed in <stem>.domain/updates.md.
Reconcile the `%% Messaging - <C>` block in <stem>.commands.md
  (drop or rename the `<X>Commands --() <E> : handles (...)` line, and the on_<E> handler on <AggregateRoot>Commands),
then re-run `event-tables-writer <commands_diagram> <C>` and `event-fields-writer <commands_diagram> <C>`
  (or `/messaging-spec:generate-code <domain_diagram> <C>`).
```

This is *not* a whole-skill hard-fail — it is a per-consumer abort. The updater still processes every consumer whose subscriptions are clean. The report (Step 5) lists which consumers were aborted-and-skipped and which were updated.

Rationale: `event-fields-writer` would fail to resolve the dangling event class and could not produce a sensible Table 3 sub-block; and even if it could, Table 2 would still reference an event that no longer exists in the domain — only reconciling the commands-diagram marker fixes that, and the marker is hand-authored.

---

## Step 3 — Compute affected consumers

`affected := { consumer ∉ aborted : internal_subs[consumer] ∩ keys(event_attr_deltas) ≠ ∅ }`

i.e. a consumer is affected iff it subscribes (as `internal`) to at least one domain event that had an **attribute add/remove/rename** in `updates.md`. Note that:

- A domain event that was merely **added** (`added_events`) affects no consumer — a new event is a subscription *candidate*, but the subscription is declared by a `%% Messaging` marker in the commands diagram, which is a separate trigger axis. The updater records it as informational in the report and moves on.
- A domain event whose only change is an **attribute type change** or a **method change** affects no consumer (Table 3 records attribute *names*, not types; events have no spec-visible methods).
- A `tenant_id` flip on the aggregate root affects no consumer unless a subscribed internal event *also* gained/lost a `tenant_id` attribute (which would land in `event_attr_deltas`).

If `affected` is empty (and `dangling` was empty), the updater is a **no-op** beyond the report.

---

## Step 4 — Regenerate Table 3 per affected consumer

For each `consumer ∈ affected`, in parallel (independent files):

1. *(Optional refresh — recommended)* Re-run `event-tables-writer <commands_diagram> <consumer>`. This re-parses the `%% Messaging - <consumer>` markers and re-renders Table 2 in place. It is a no-op for a domain-only change (markers unchanged), but it catches the case where the operator already reconciled the commands diagram before invoking the updater (so a renamed marker is picked up). It is cheap and idempotent. *Skip this sub-step if you prefer the updater to touch strictly the minimum — Step 2 already guarantees no consumer in `affected` has a dangling subscription, so `event-fields-writer` will resolve every event either way.*
2. Re-run `event-fields-writer <commands_diagram> <consumer>`. This rebuilds Table 3 wholesale: the `Command Parameter` column from `<AggregateRoot>Commands.on_<event>` signatures in the commands diagram, the `external`-row `Event Field` values from the foreign `<<Domain Event>>` decls in the commands diagram, and the `internal`-row `Event Field` values by best-match against the current `<<Domain Event>>` attribute lists in the domain diagram — re-flagging any low-confidence sub-block in italic prose. A new attribute gains a row only if the bound `on_<event>` handler consumes it (a commands-diagram concern); a removed attribute drops/relocates a row; a renamed attribute moves the `Event Field` value to the new name.

Neither writer needs a `target-locations-finder` report (that is a code-gen concern; the spec writers operate purely on the diagrams and the consumer-spec file).

If a writer aborts on a given consumer, record it in the report and continue with the rest — the updater does not roll back already-processed consumers.

---

## Step 5 — Report

Emit a short Markdown summary:

- **Hard-fail** (Step 1) — the single `ERROR:` line, nothing else.
- Otherwise, one section listing, per consumer under `<stem>.messaging/`:
  - **updated** — Table 3 regenerated; name the triggering domain event(s); note "Table 2 also refreshed" if Step 4.1 ran.
  - **aborted (reconcile the commands diagram)** — name the dangling internal event(s) and the exact reconcile instruction from Step 2.
  - **unaffected** — no `internal` subscription intersected the changed-domain-event set.
- **Informational** — domain events added (subscription candidates), and any subscribed internal event whose `: emits` edge was removed but whose class survives (a "dead subscription" — byte-stable spec, but the consumer will never receive the event).

End with: `Messaging spec update complete for <domain_diagram> (<k> consumer(s) updated, <m> aborted, <n> unaffected).`

### Optional: the update report file

For symmetry with persistence's `<stem>.persistence/updates.md`, the skill may also write `<stem>.messaging/updates.md` capturing the same content in a structured form. This is *optional* — unlike persistence, no downstream consumer of a messaging updates report exists today, so the inline Step-5 summary is sufficient. If added, follow the shape of `persistence-spec:updates-report-template` (a per-consumer delta block + an "Affected Consumers" footer) and add it to `messaging-spec:naming-conventions` first.

---

## Dispatch tiers

Three tiers, matching `update-types.md`:

1. **Hard-fail** (Step 1, Step 0 degraded baseline) — aggregate-root lifecycle / stereotype-demotion / rename, any stereotype change, degraded baseline. One `ERROR:` line, no writes. Operator reconciles the diagrams + folders and re-runs the consumer-spec pipeline / `/messaging-spec:generate-code`.
   - *Adjacent sub-case (Step 2, per-consumer abort, not a whole-skill hard-fail):* a subscribed internal `<<Domain Event>>` removed/renamed → reconcile that consumer's `%% Messaging` marker + `on_<event>` handler in the commands diagram, then re-run `event-tables-writer` + `event-fields-writer` for that consumer. Other consumers still proceed.
2. **Regen Table 3 per affected consumer** (Steps 3–4) — `domain-events` member changes (attribute add/remove/rename) on a `<<Domain Event>>` that one or more consumers subscribe to as `internal`: for each such consumer, re-run `event-fields-writer` (and, optionally, `event-tables-writer` first). Per-consumer scoped — untouched consumers are not re-run.
3. **No-op** — `affected_categories` empty; or `⊆ {data-structures, value-objects, commands, repositories-services}`; or `aggregates` changes that don't touch the root's lifecycle/stereotype/name; or pure prose (P1–P4, including the bounded-context `title:`); or multi-tenancy flips that don't add/remove a `tenant_id` attribute on a subscribed internal event; or `domain-events` changes that touch only events no consumer subscribes to as `internal`, or that are only an event *addition* / attribute *retype* / *method* change. The updater writes nothing (beyond the optional report) and exits cleanly.

Tier 2 is the only "real work" tier, and it is unusually contained: re-run one (or two) existing agents for the subset of consumers whose `internal` subscriptions intersect the changed-domain-event set.

---

## Hard-fail conditions (summary)

Each prints exactly one `ERROR:` line and exits, directing the operator to reconcile the diagrams + folders and re-run the consumer-spec pipeline / `/messaging-spec:generate-code`:

- **Aggregate root removal** in `## Class Lifecycle → Removed`.
- **Aggregate root stereotype change** in `## Class Lifecycle → Stereotype Changed` (old or new bucket = `<<Aggregate Root>>`).
- **Aggregate root rename** (reported as `removed (old)` + `added (new)`) — cascades to `<stem>.commands.md`'s class names + filename, the `<stem>.messaging/` folder name, the `%% Messaging` markers' `<Source>` cells, and the `<pkg>.domain.<root_snake>` import root in generated code.
- **Any stereotype change** in the domain report (subsumes the aggregate-root case; also covers `<<Domain Event>>` ⇄ other re-classifications).
- **Degraded baseline** — `_warning: HEAD ..._` in the domain report Summary.
- **Missing `<stem>.domain/updates.md`** — the updater is not the first-run pipeline; that is the consumer-spec pipeline's job.

A subscribed internal `<<Domain Event>>` removed/renamed is handled as a *per-consumer abort-and-reconcile* (Step 2), not a whole-skill hard-fail — the rest of every clean consumer still updates.

---

## Out of scope (deliberate cuts)

- **The commands-diagram trigger axis.** Most consumer-spec churn — a consumer added/removed, an event added/removed from a `%% Messaging` block, a row's `Type` / `Source Destination` / `Command Class` / `Command Method` changed, an `<AggregateRoot>Commands.on_<event>` signature changed, an `external` event's wire shape changed — originates in `<stem>.commands.md`, not the domain diagram, and `<stem>.domain/updates.md` does not capture it. A "complete" messaging updater would need a `messaging-spec:updates-detector` that diffs the commands diagram (its `%% Messaging` blocks, its external `<<Domain Event>>` nodes, and the `on_<event>` signatures) → `<stem>.messaging/updates.md`. **This is intentionally not built now:** it is a whole new detector for a second, hand-authored diagram type that changes less often than the domain diagram, and the interim answer is already adequate — when the commands diagram changes, re-run `/messaging-spec:generate-code <domain_diagram> <consumer>` per consumer (that pipeline is idempotent/additive and regenerates Tables 2–3 from the current diagram). This mirrors the call `application-spec/notes/update-types.md` makes for *its* commands/queries-diagram axis. When/if the commands-diagram detector is built, `/messaging-spec:update-specs` should be extended to consume *both* `<stem>.domain/updates.md` and `<stem>.messaging/updates.md` in one pass.
- **The command-handler side of a consumer.** Table 1's *Commands queue name* is the only consumer-spec trace of the command side; there is no command-inventory table and no command-tables-writer. So this updater is *correct* to ignore the `commands` (`<<Command>>`) category — but command-side drift (a new/renamed/retyped domain `<<Command>>`, and the `command-handlers` / `command-replies` / `command-dispatchers` code it drives) is invisible to this updater and is reconciled only by re-running `/messaging-spec:generate-code` (whose command-handler generation reads the commands diagram). This is a known modeling gap, not a bug.
- **Code regeneration.** This skill stops at the consumer spec. The per-consumer `messaging/<consumer>/` submodule, the `containers.py` / `entrypoint.py` / `__main__.py` wiring, the `constants.py` constants, and the handler integration tests are owned by `/messaging-spec:generate-code` — a separate updater concern (analogous to `notes/code-updater-approach-c.md` on the domain side). In particular, an aggregate-root rename (a Tier-1 hard-fail here) needs `/messaging-spec:generate-code` re-run because the `<pkg>.domain.<root_snake>` import path moved.
- **Hand-edit preservation inside a consumer spec.** Touched consumers' Table 3 is wholesale-replaced; the operator's contract is "the spec is regenerated from the diagrams, not curated."
- **Partial-failure rollback.** Each consumer's regen is its own write; a mid-run failure leaves a clean partial state, and re-running the updater on top of the unchanged report → diagrams is idempotent.

---

## Build order

1. **`messaging-spec:update-specs` skill** — Steps 0–5 wiring: recover paths, parse `<stem>.domain/updates.md`, discover consumers + `internal` subscriptions, run the hard-fail / abort-and-reconcile gates, compute `affected`, fan out `event-tables-writer` (optional) + `event-fields-writer` per affected consumer in parallel, emit the report. **No new agents.** The only contract touch on existing agents is confirming `event-tables-writer` and `event-fields-writer` are safely re-runnable on an already-populated consumer spec (they are — both replace their table in place).
2. *(Optional)* **`<stem>.messaging/updates.md` report** + a `messaging-spec:updates-report-template` skill + a `naming-conventions` entry — only if a structured report is wanted for symmetry with persistence.
3. **Wire as Step 13 of domain `/update-specs`** — invoked unconditionally after the persistence (Step 10) / application (Step 11) / rest-api (Step 12) chain steps; the skill's own Step 0c "no consumer specs" path keeps it a graceful no-op when there is no messaging layer. *(Done — domain-spec ≥ 0.29.0. The as-built cascade contract lives in `persistence-spec/notes/spec-updater-approaches.md`.)*
4. *(Future, separate change)* **`messaging-spec:updates-detector`** for the commands-diagram axis — see *Out of scope*.

---

## Mapping back to `update-types.md`

| Update type | Handled by |
|---|---|
| L1 added — `<<Domain Event>>` | Step 3 records it as informational (subscription candidate); no write |
| L1 added — anything else | no-op |
| L2 removed — `<<Aggregate Root>>` | Step 1 hard-fail |
| L2 removed — subscribed internal `<<Domain Event>>` | Step 2 per-consumer abort-and-reconcile |
| L2 removed — anything else | no-op |
| L3 stereotype changed | Step 1 hard-fail |
| M1 attribute add/remove on a subscribed internal event | Step 3 → Step 4 (`event-fields-writer` regen of Table 3) |
| M1 attribute add/remove elsewhere; M2 retype; M3 visibility; M4/M5 methods | no-op |
| R2 `: emits <Event>` added | = L1 event-added → informational |
| R2 `: emits <Event>` removed + event class also removed | = L2 → Step 2 abort if subscribed, else no-op |
| R2 `: emits <Event>` removed + event class survives | no-op + "dead subscription" informational note if subscribed |
| R3 `: emits <Command>` add/remove; R1/R4/R5/R7 | no-op |
| R6 label change (`: emits Old` → `: emits New`) on a subscribed internal event | Step 2 per-consumer abort-and-reconcile (the marker + `on_Old` handler still carry the old name) |
| P1–P4 prose; bounded-context `title:` rename | no-op |
| C1 pure prose | no-op |
| C2 pure structural | only the `domain-events` slice reaches Steps 3–4; rest no-op |
| C3 affected-categories empty | no-op |
| C4 multi-category | fan out: Step 1/2 gates fire on the `aggregates`/lifecycle slice; Steps 3–4 fire on the `domain-events` slice; other categories ignored |
| C5 degraded baseline | Step 0 hard-fail |
| Aggregate-root rename | Step 1 hard-fail (cascades to commands-diagram filename, `<stem>.messaging/` folder, import root) |
| Multi-tenancy flip on the root (no event gained/lost `tenant_id`) | no-op |
