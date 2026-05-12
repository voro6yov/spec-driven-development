# Messaging Spec Update Types

Analysis of how every kind of domain-diagram delta — as emitted by `domain-spec:updates-detector` into `<dir>/<stem>.domain/updates.md` — ripples into the **messaging consumer input specs** at `<dir>/<stem>.messaging/<consumer_name>.md` (Tables 1–3 per `messaging-spec:consumer-spec-template`, `event-tables-template`, `event-fields-template`).

The goal is to enumerate every distinct kind of change a messaging-spec updater would have to handle, so it can dispatch the right action per change rather than re-running the consumer-spec pipeline (`consumer-spec-initializer → event-tables-writer → event-fields-writer`) from scratch for every consumer.

This is the messaging-side analog of `plugins/persistence-spec/notes/update-types.md`, `plugins/application-spec/notes/update-types.md`, and `plugins/domain-spec/notes/update-types.md`. It assumes the domain `updates.md` is already produced; the messaging updater **consumes that report directly** (same as the persistence and application updaters) and never re-diffs the domain diagram. It does **not** consume the domain `specs.md` — `event-fields-writer` reads the domain *diagram* (`<<Domain Event>>` classes), not the domain spec, so the messaging updater can run before / independently of the domain spec being regenerated.

**Two structural facts dominate the design:**

1. **The consumer spec is overwhelmingly a function of the *commands* diagram, not the domain diagram.** See *The trigger surface* below. The domain-driven axis cataloged here is narrow — it touches exactly one column of one table.
2. **A domain diagram has *N* consumer specs, not one.** `<dir>/<stem>.messaging/` holds one `<consumer_name>.md` per consumer; `<stem>.domain/updates.md` knows nothing about which consumers exist (the consumer set lives in the *commands* diagram's `%% Messaging - <consumer_name>` markers). The updater must enumerate `<stem>.messaging/*.md` and, for each, decide whether the domain delta touches an event that consumer subscribes to.

---

## The trigger surface

Per `messaging-spec:naming-conventions`, the consumer input spec for one consumer is a pure function of:

| Input | What it determines | Diffed by | Diff artifact |
|---|---|---|---|
| `<dir>/<stem>.commands.md` — the commands diagram | **All of Table 1's identity** (via the consumer name), **all of Table 2** (the `%% Messaging - <consumer_name>` markers: Event Name · Type · Source Destination · Command Class · Command Method), **Table 3's `Command Parameter` column** (the `<AggregateRoot>Commands.on_<event>` handler signatures), and **Table 3's `Event Field` column for `external` events** (the foreign event classes are declared as `<<Domain Event>>` on *this* service's commands diagram) | — *(nothing today)* | — |
| `<dir>/<stem>.md` — the domain diagram | **Table 3's `Event Field` column for `internal` events only** — the bare attribute names of the local `<<Domain Event>>` classes the consumer subscribes to. *Indirectly:* the aggregate-root class name is the conventional `Source Destination` for internal events and the import root (`<pkg>.domain.<source_destination_snake>`) for the generated handler/dispatcher code. | `domain-spec:updates-detector` | `<dir>/<stem>.domain/updates.md` |
| The project's Python package name | Table 1's two queue names (the `<svc>` service prefix) | — | — |
| The user-supplied consumer name | Table 1's Consumer name; the `%% Messaging - <consumer_name>` block selector | — | — |

Which consumer-spec field is a function of the domain diagram:

| Spec artifact | Producer | Domain diagram | Commands diagram | Project package | User input |
|---|---|:-:|:-:|:-:|:-:|
| Table 1 — Consumer Basics | `consumer-spec-initializer` | — | — | ✅ (queue prefix) | ✅ (consumer name) |
| Table 2 — Events to Consume | `event-tables-writer` | — | ✅ (`%% Messaging` markers) | — | — |
| Table 3 — Event Parameter Mapping → `Command Parameter` col | `event-fields-writer` | — | ✅ (`on_<event>` signatures) | — | — |
| Table 3 — Event Parameter Mapping → `Event Field` col, **external** rows | `event-fields-writer` | — | ✅ (foreign `<<Domain Event>>` decls) | — | — |
| Table 3 — Event Parameter Mapping → `Event Field` col, **internal** rows | `event-fields-writer` | ✅ (local `<<Domain Event>>` attrs) | — | — | — |

The consequence: a domain-`updates.md`-only updater covers exactly **one of two trigger axes**, and within the domain axis it touches **one column of Table 3**. The most common messaging-spec changes in practice — a consumer added/removed, an event added/removed from a consumer's subscription, a handler binding (`on_<event>`) changed, an external event's wire shape changed — all originate in the *commands* diagram (the `%% Messaging` markers and the external `<<Domain Event>>` declarations) and never appear in `<stem>.domain/updates.md`.

So a complete messaging-spec updater needs one of:

- **(A)** a `messaging-spec:updates-detector` analog that diffs `<stem>.commands.md` — its `%% Messaging` blocks, its `<<Domain Event>>` external-event nodes, and the `<AggregateRoot>Commands.on_<event>` method signatures — emitting `<stem>.messaging/updates.md`, invoked alongside the domain-`updates.md` consumption; **or**
- **(B)** accepting that commands-diagram changes are handled by re-running the consumer-spec pipeline (or `/messaging-spec:generate-code`), with the domain-driven updater handling only the ripple cataloged here.

This document catalogs the **domain-driven axis** — what an updater must do with `<stem>.domain/updates.md`. The commands-diagram axis is a parallel, larger concern; see *Out-of-scope but worth flagging*.

---

## Snapshot only — no append-only log

Like application-spec and unlike persistence-spec (whose `§2.Migrations` is a cumulative changeset history that must never be rewritten), **every consumer-spec table is a pure snapshot** — fully regeneratable from the commands diagram (Tables 1–2, Table 3's left column + external rows) plus the domain diagram (Table 3's internal rows). There is no migration-log equivalent, no row-immutability contract, no delta-driven appender.

So the messaging-spec updater is structurally simple. The only open design question is **granularity**, and it has an unusually clean answer: the domain-driven axis touches only Table 3, and the agent that produces Table 3 — `event-fields-writer` — already replaces the whole table in place from the current diagrams. So "update Table 3 for consumer C" = "re-run `event-fields-writer <commands_diagram> C`". No splicer needed. The only above-the-agent work is *which* consumers to re-run it for, and *which* domain deltas are hard-fails the updater shouldn't try to absorb.

As with persistence-spec and application-spec, hand-edits inside the consumer spec are **not a preservation goal** — the operator's contract is "the spec is regenerated from the diagrams, not curated." (`event-fields-writer` does preserve a flavour of hand-annotation: it flags low-confidence sub-blocks in *italic prose* around Table 3; a re-run reconsiders those flags from scratch.)

---

## Consumer-spec tables and their domain-sensitivity

| Table | Kind | Owner agent | Domain-diagram-sensitive to |
|---|---|---|---|
| **Table 1 — Consumer Basics** (Consumer name · Events queue name · Commands queue name) | snapshot | `consumer-spec-initializer` | **Nothing.** Consumer name is hand-supplied; the two queue names derive from it plus the project's `<svc>` prefix. No domain delta reaches it. |
| **Table 2 — Events to Consume** (Event Name · Type · Source Destination · Command Class · Command Method) | snapshot | `event-tables-writer` | **Nothing directly.** Every cell is parsed from a `<X>Commands <arrow> <Event> : handles (<Source>, <on_method>)` line inside a `%% Messaging - <consumer_name>` block in the *commands* diagram. A domain change can leave Table 2 *stale* (it still references an internal event that the domain diagram no longer declares / has renamed) but cannot *regenerate* it — that requires reconciling the commands diagram's marker first. |
| **Table 3 — Event Parameter Mapping** (`Command Parameter` ↔ `Event Field`, one per-event sub-block per Table 2 row) | snapshot | `event-fields-writer` | The **attribute lists of the local `<<Domain Event>>` classes** named in Table 2's `internal` rows — these drive the `Event Field` column for those sub-blocks (best-match by name similarity against the bound `on_<event>` handler's parameters). The `Command Parameter` column and the `external`-row `Event Field` values come from the commands diagram, not the domain diagram. |

The downstream artifacts — the per-consumer `messaging/<consumer>/` submodule (`events.py` external-event dataclasses, `handlers.py` `@inject` handlers, `dispatcher.py` factory), the `containers.py` / `entrypoint.py` / `__main__.py` wiring, the `constants.py` destination + queue constants, and the handler integration tests — are owned by `/messaging-spec:generate-code`. They are **out of scope** for the spec updater (analogous to `notes/code-updater-approach-c.md` on the domain side). One cross-boundary fact: `event-handlers-implementer` and `dispatcher-implementer` import internal event classes from `<pkg>.domain.<source_destination_snake>` (the aggregate-root subpackage), so an aggregate-root *rename* in the domain diagram ripples into generated messaging code even though it barely touches the consumer spec.

---

## Domain shape constraints

Load-bearing facts about how the consumer spec relates to the domain diagram:

- **The domain diagram is one of two inputs, and the lesser one.** The trigger for a domain-driven messaging update is `<stem>.domain/updates.md`. Commands-diagram changes are a separate, dominant axis (see above).
- **Exactly one `<<Aggregate Root>>` per domain diagram.** Removal, stereotype-demotion, or rename of the root is a hard-fail for the messaging updater — the same way it is for domain/persistence/application. The aggregate-root rename in particular cascades to the *commands* diagram's class names and filenames (`<stem>.commands.md`) and to the `<stem>.messaging/` folder path, plus to the `<pkg>.domain.<root_snake>` import root used by every generated dispatcher/handler — a coordinated multi-file rename the domain-`updates.md`-driven updater cannot perform.
- **`internal` events are domain `<<Domain Event>>` classes; `external` events are not.** `external` event classes are declared as `<<Domain Event>>` on *this* service's commands diagram and represent another service's published events — the domain diagram knows nothing about them. So **any domain delta is, by construction, irrelevant to every `external` row** of every consumer's Tables 2 and 3.
- **The handler binding `on_<event>` lives on `<AggregateRoot>Commands`, an application-service class, declared on the *commands* diagram — not the domain diagram.** A domain event's attribute change *should* ripple to that handler's signature (via an application-spec regen of `<AggregateRoot>Commands`), but that ripple surfaces in the commands-diagram axis, not in `<stem>.domain/updates.md`. So a domain-only event-attribute change updates Table 3's `Event Field` column (right side) but leaves the `Command Parameter` column (left side) untouched until the commands diagram is reconciled — which is exactly the situation `event-fields-writer` handles by emitting its best guess and flagging low-confidence sub-blocks in italic prose.
- **The consumer spec does not model the command side beyond Table 1's queue name.** Table 2 is explicitly events-only ("Commands the consumer dispatches or replies it emits are out of scope here"); there is no command-tables-writer and no Table-for-commands. So domain `<<Command>>` changes (a new `<<Command>>`, a renamed one, changed attributes) ripple into *generated* `command-handlers` / `command-replies` code but into **no consumer-spec artifact**. This is a known modeling gap, not a bug — see *Out-of-scope but worth flagging*.
- **Queue names come from the project's Python package name, not the domain diagram's `title:`.** A bounded-context rename (domain `title:` change) is byte-neutral for the consumer spec. (`Source Destination` for `internal` events is the aggregate-root *class name*, also not the `title:`.)
- **`event-fields-writer` matches structurally, not by prose.** It pairs `on_<event>` parameters against event attributes by name similarity — it does not read the domain diagram's surrounding prose. So domain prose changes are byte-neutral for the consumer spec (a deliberate divergence from application-spec, whose methods writers retain advisory prose).

---

## Mapping `affected_categories` → messaging-spec impact

Per the canonical category order from `domain-spec:updates-report-template`. Throughout: "subscribed internal event" = a `<<Domain Event>>` class named in some `<stem>.messaging/<consumer>.md` Table 2 row whose Type cell is `` `internal` ``.

### 1. `data-structures` (`<<TypedDict>>`)

**Byte-neutral for every consumer spec.** Domain `<<TypedDict>>` classes are query-side / internal-domain structures; they are not the payload of any domain event in this model, do not appear in Table 2, and never feed Table 3's `Event Field` column (which is "strictly the bare attribute name … no constructed expressions"). Skip this category at dispatch time.

### 2. `value-objects` (`<<Value Object>>`)

**Byte-neutral in practice.** A domain event may *carry* a value object as an attribute, but Table 3's `Event Field` column records the bare attribute name, not the VO's internal shape — so a VO field add/remove/retype does not change Table 3. The only way a VO change touches the consumer spec is if it forces a *domain event's attribute list* to change (e.g. a VO attribute is added to / removed from the event class), and that surfaces as a `domain-events` member change, handled there. A pure `value-objects`-only delta → **no-op**.

### 3. `domain-events` (`<<Event>>` / `<<Domain Event>>`)

**The only high-impact category for the consumer spec — and even here, only the subset that some consumer subscribes to as `internal` matters.**

- **Domain event added** → no consumer-spec change. A new `<<Domain Event>>` is a *candidate* for a new internal subscription, but the subscription is declared by a `%% Messaging - <consumer>` marker in the *commands* diagram — adding the event alone touches nothing in `<stem>.messaging/`. **Informational** (the updater may note "new domain event `X` available for subscription").
- **Domain event removed** → if it is a subscribed internal event: that consumer's Table 2 still has an `internal` row for it and Table 3 still has a sub-block for it — and so does the `%% Messaging` marker in the commands diagram. The consumer spec is now inconsistent with the domain. `event-fields-writer` cannot fix Table 2 (it owns Table 3 only), and a re-run against the orphaned Table 2 row would fail to resolve the event class. → **reconcile the commands diagram's `%% Messaging - <consumer>` marker (drop the line), then re-run `event-tables-writer` + `event-fields-writer` for that consumer** — surfaced as an abort-and-reconcile, not a silent prune. If it is *not* a subscribed internal event → byte-neutral.
- **Domain event renamed** (reported as `removed (old)` + `added (new)`) → if the old name is a subscribed internal event: same as "removed" for the old name (the marker still says the old name) — **reconcile the commands diagram marker (rename `<X>Commands --() OldEvent : handles (...)` → `... NewEvent : handles (...)`, and the handler method `on_old` → `on_new` on `<AggregateRoot>Commands`), then re-run `event-tables-writer` + `event-fields-writer`**. Otherwise byte-neutral.
- **Domain event attribute added** (on a subscribed internal event) → re-run `event-fields-writer` for that consumer; it re-derives the event's Table 3 sub-block. A *new row* appears only if the bound `on_<event>` handler actually consumes the new attribute — and the handler signature is a commands-diagram concern. If the handler wasn't reconciled, no new row appears (correct: Table 3 documents the projection the handler performs, not the full event payload); the updater may note the now-unmapped attribute. → **Table 3 regen for the affected consumer(s).**
- **Domain event attribute removed** (on a subscribed internal event) → re-run `event-fields-writer`. If Table 3's `Event Field` column referenced the removed attribute, that row's right side no longer resolves; the writer re-derives the sub-block against the new attribute set and, if the bound handler still passes a parameter that was sourced from the removed attribute, emits a best-guess row and flags the sub-block as low-confidence in italic prose. → **Table 3 regen for the affected consumer(s).**
- **Domain event attribute renamed** (remove + add, on a subscribed internal event) → same as "removed" then "added": re-run `event-fields-writer`; the `Event Field` value for the affected parameter moves to the new attribute name (best-match). → **Table 3 regen for the affected consumer(s).**
- **Domain event attribute type changed** (on a subscribed internal event) → **byte-neutral.** Table 3 records attribute *names*, not types. (The generated handler/dispatcher code may care; the spec does not.)
- **Method added/removed/changed on a domain event class** → **byte-neutral.** Domain events are dataclasses; their methods (if any) don't appear in the consumer spec.

Net for `domain-events`: re-run `event-fields-writer` for every consumer with an `internal` Table 2 row whose Event Name matches a domain event that had an **attribute add/remove/rename**; **abort-and-reconcile-the-commands-diagram** for every consumer with an `internal` row whose Event Name matches a domain event that was **removed or renamed**; **informational / no-op** for a domain event that was merely **added** or whose only change is an **attribute retype** or a **method change**.

### 4. `commands` (`<<Command>>` — the *domain message dataclass*)

**Byte-neutral for the consumer spec.** Domain `<<Command>>` dataclasses are cross-context message-bus payloads; the consumer spec does not model the command-handler side at all (Table 1's *Commands queue name* is the only trace, and it derives from the consumer name, not from any `<<Command>>` class). A new / renamed / re-typed domain `<<Command>>` ripples into *generated* `command-handlers` and `command-replies` code only — out of scope for the spec updater. Skip.

> ⚠ **Modeling gap, not a no-op for code.** Unlike events, commands consumed by a consumer are not enumerated anywhere in the consumer input spec, so the updater is *correct* to skip the `commands` category — but the operator should know that command-side drift is invisible to this updater and is reconciled only by re-running `/messaging-spec:generate-code` (whose command-handler generation reads the commands diagram, not the consumer spec).

### 5. `aggregates` (`<<Aggregate Root>>`, `<<Entity>>`)

The category with the loudest *non-spec* ripple (generated-code import paths) but a near-silent *spec* ripple.

- **Aggregate-root attribute add / remove / type change** → **byte-neutral for the consumer spec.** The consumer spec models the *event* surface, not aggregate state; the `on_<event>` handler is an application-service method (commands diagram), and even *its* signature is mediated by domain events, not aggregate attributes.
- **Aggregate-root method add / remove / signature change** → **byte-neutral.** Aggregate methods don't appear in the consumer spec. (The `on_<event>` handler that *does* appear lives on `<AggregateRoot>Commands`, on the commands diagram.)
- **`<<Entity>>` added / removed; entity attribute or method change** → **byte-neutral for the consumer spec.** Child entities aren't modeled in Table 1/2/3. If a child entity (or a collection VO) starts/stops emitting a `<<Domain Event>>`, that surfaces as a `domain-events` lifecycle / a `: emits` relationship change — handled under `domain-events` / R2 — not as an `aggregates` concern here.
- **Aggregate-root renamed** → the *generated* dispatcher/handler imports (`<pkg>.domain.<root_snake>`), the conventional `Source Destination` cell of every `internal` Table 2 row, and the commands-diagram's class names + filenames all move. The domain-`updates.md`-driven updater cannot perform that cascade. → **hard-fail / route to: rename the diagrams + the `<stem>.messaging/` folder, reconcile the commands diagram's `%% Messaging` markers' `<Source>` cells, then re-run `/messaging-spec:generate-code` per consumer.**
- **Aggregate-root removed or stereotype-demoted** → **hard-fail.** The whole diagram set (and every consumer spec hanging off it) is invalid.

Net for `aggregates`: **byte-neutral for the consumer spec** for every change except aggregate-root rename / removal / stereotype-demotion, which are **hard-fails**. (Watch for an aggregate-root rename masquerading as `removed (old) + added (new)` under `## Class Lifecycle`.)

### 6. `repositories-services` (`<<Repository>>`, `<<Service>>`)

**Byte-neutral for the consumer spec.** Repositories and domain services appear nowhere in Tables 1–3. Repository-finder churn, domain-`<<Service>>` lifecycle, service-method changes — none of it reaches the consumer spec (it reaches the *application* spec, which the application-spec updater handles, and from there the commands diagram). Skip this category at dispatch time.

---

## Out-of-band signals (not a direct `affected_categories` entry)

- **`: emits <Event>` relationship change on the aggregate root / a child entity / a collection VO** (an `R2` dependency add/remove with an `emits` label, or an `R3` realization change, or an `R6` label rename) — this is how the *set of domain events* and their *names* actually move in a Mermaid diagram. The `domain-events` category fires alongside (the inferred `<<Domain Event>>` is added/removed/renamed), so dispatch on `domain-events` per the rules above. An `: emits` edge *removed* without removing the event class leaves a `<<Domain Event>>` that nothing emits — a consumer subscribed to it as `internal` would never receive it: **byte-stable spec, but worth an operator warning** ("internal event `X` is subscribed by consumer `C` but no longer emitted by `<AggregateRoot>`").
- **Multi-tenancy flip on the domain root** (`tenant_id` attribute added/removed on the aggregate root) — **not a domain-`updates.md`-driven signal for the consumer spec.** Domain events are independent classes; a `tenant_id` flip on the root does not auto-add/remove `tenant_id` on any `<<Domain Event>>`. If a specific subscribed internal event *also* gained/lost a `tenant_id` attribute, that is a `domain-events` member change (handled above); the root's flip on its own is byte-neutral here. (Contrast persistence-spec, where the root's `tenant_id` *is* the trigger.)
- **Bounded-context rename** (domain `title:` change) — **not applicable.** Queue names use the project package prefix; `Source Destination` uses aggregate class names; nothing in the consumer spec reads the domain `title:`. It surfaces in `## Orphan Prose Changes → Preamble` of the domain report; the messaging updater ignores it.
- **Aggregate-root rename** — surfaces as `removed (old) + added (new)` under `## Class Lifecycle`. Hard-fail (see `aggregates` above): it cascades to the commands-diagram class names + filenames, the `<stem>.messaging/` folder, and the generated-code import root.

---

## Update types

Mirroring the domain-spec catalog (L / M / R / P / C codes), here is the messaging-spec response to each domain-side delta. "Affected consumer(s)" always means "the consumer specs under `<stem>.messaging/` with an `internal` Table 2 row naming the changed domain event"; if there are none, the entry is a no-op.

### L. Lifecycle updates (whole-class, in the domain diagram)

- **L1. Class added** — dispatch by stereotype:
  - `<<Aggregate Root>>` → impossible on an existing diagram; treat as malformed.
  - `<<Entity>>` / `<<Value Object>>` / `<<TypedDict>>` / `<<Command>>` / `<<Service>>` / `<<Repository>>` → **byte-neutral** for every consumer spec.
  - `<<Event>>` / `<<Domain Event>>` → **byte-neutral**; a new domain event becomes a *subscription candidate* but changes no consumer spec until a `%% Messaging` marker references it (a commands-diagram change). **Informational.**
- **L2. Class removed** — dispatch by stereotype:
  - `<<Aggregate Root>>` → **hard-fail**.
  - `<<Event>>` / `<<Domain Event>>` that is a subscribed internal event → **abort-and-reconcile-the-commands-diagram** (drop the `%% Messaging` marker line + the `on_<event>` handler, then re-run `event-tables-writer` + `event-fields-writer` for the affected consumer(s)). Not a subscribed internal event → byte-neutral.
  - `<<Entity>>` / `<<Value Object>>` / `<<TypedDict>>` / `<<Command>>` / `<<Service>>` / `<<Repository>>` → **byte-neutral**.
- **L3. Stereotype changed** — **hard-fail** (route to reconciling the diagrams + re-running the consumer-spec pipeline), mirroring domain/persistence/application. The case that bites the messaging spec specifically: a `<<Domain Event>>` ⇄ anything-else re-classification — a subscribed internal event ceasing to be an event (its consumers' `internal` bindings become meaningless), or a class becoming an event (no automatic subscription, but the cross-category move means the diagram must be reconciled anyway).

### M. Member updates (in-class, signature-affecting)

- **M1. Attribute added/removed on a class** —
  - on a `<<Domain Event>>` that is a subscribed internal event → **Table 3 regen for the affected consumer(s)** (`event-fields-writer` re-run): a removed attribute drops/relocates a `Event Field` value (low-confidence sub-block flagged in italic prose if the handler still expects it); an added attribute gains a row only if the bound `on_<event>` handler consumes it (commands-diagram concern).
  - on the aggregate root, a child entity, a value object, a TypedDict, a command, a service, or a repository → **byte-neutral** for every consumer spec.
- **M2. Attribute type changed** — **byte-neutral** everywhere, including on a subscribed internal event (Table 3 records names, not types).
- **M3. Attribute visibility changed** — **byte-neutral.**
- **M4. Method added/removed** — **byte-neutral** everywhere (events are dataclasses; aggregate/entity/service/repository methods don't appear in the consumer spec; the `on_<event>` handler is a commands-diagram method).
- **M5. Method signature changed** — **byte-neutral** (same reasoning as M4).

### R. Relationship updates (cross-class topology, in the domain diagram)

- **R1. Composition added/removed** (`*--`) — **byte-neutral** (the consumer spec doesn't model aggregate composition / child-entity topology).
- **R2. Dependency added/removed** (`-->`) — `-->` with an `: emits <Event>` label adds/removes a domain `<<Domain Event>>`: dispatch on the `domain-events` rules (an *added* emit-edge ⇒ L1 event-added ⇒ informational; a *removed* emit-edge that also removes the event class ⇒ L2 ⇒ abort-and-reconcile if subscribed; a *removed* emit-edge that leaves the event class ⇒ byte-stable spec + "dead subscription" warning if subscribed). `-->` to a `<<Service>>` / external interface ⇒ domain-layer wiring, **byte-neutral**.
- **R3. Realization added/removed** (`--()`) — `--()` with an `: emits <Command>` label adds/removes a domain `<<Command>>` ⇒ **byte-neutral** (command side not spec-modeled). `--()` to a `<<Repository>>` ⇒ informational, byte-neutral.
- **R4. Inheritance added/removed** (`<|--`) — makes a `<<Value Object>>` / `<<Entity>>` (or, in principle, an event) polymorphic; the consumer spec doesn't model polymorphism. **Byte-neutral.**
- **R5. Multiplicity changed** — **byte-neutral** for the consumer spec.
- **R6. Label changed** (`: emits OrderPlaced` → `: emits OrderConfirmed`) — domain event rename. If the old name is a subscribed internal event ⇒ **abort-and-reconcile-the-commands-diagram** (the `%% Messaging` marker + the `on_<old>` handler still carry the old name) then re-run `event-tables-writer` + `event-fields-writer`. Otherwise byte-neutral.
- **R7. Orphan relationship change** — the unresolved source is typically an inferred `<<Event>>` / `<<Command>>` ⇒ byte-neutral; if it resolves to a `<<Domain Event>>` that is a subscribed internal event, treat per the `domain-events` / R6 rules.

### P. Prose updates (semantic, not structural)

**Domain prose is unconditionally byte-neutral for the consumer spec** — `event-fields-writer` matches handler parameters against event attributes structurally (by name similarity), without reading the domain diagram's surrounding prose. (Contrast application-spec, whose methods writers retain advisory prose.)

- **P1. Class-keyed prose changed** (`### ClassName`) — **byte-neutral.**
- **P2. Method-keyed prose changed** (`### ClassName.method`) — **byte-neutral.**
- **P3. Orphan prose changed — `Preamble`** (the domain title/overview) — **byte-neutral** (the consumer spec doesn't read the domain `title:`).
- **P4. Orphan prose changed — free-form** (`Notes`, `Glossary`, …) — **byte-neutral.**

### C. Composite / derived signals

- **C1. Pure prose change, zero structural** — **no-op** for every consumer spec.
- **C2. Pure structural, zero prose** — standard path; only `domain-events` lifecycle/member changes that touch a *subscribed internal event* do anything; everything else is byte-neutral.
- **C3. `Affected Categories` empty** — **no-op**.
- **C4. `Affected Categories` spans multiple** — only the `domain-events` entries (and, as hard-fails, an aggregate-root rename/removal/stereotype-change in `aggregates` / `## Class Lifecycle`) matter; fan out to the affected consumer specs. The rest of the category set (`data-structures`, `value-objects`, `commands`, `repositories-services`, plus non-root `aggregates` changes) is byte-neutral and ignored.
- **C5. First-run / degraded baseline** (HEAD warning in the domain report Summary) — **hard-fail** (route to the consumer-spec pipeline / `/messaging-spec:generate-code`).

---

## Section-affected matrix

Quick lookup for "given a domain-side update, what happens in each consumer-spec table". Table 1 and Table 2 are always `—` for any domain-driven change — Table 1 is hand/prefix-derived, Table 2 is a pure function of the commands diagram's `%% Messaging` markers.

| Domain update | Table 1 — Consumer Basics | Table 2 — Events to Consume | Table 3 — Event Parameter Mapping |
|---|:-:|:-:|---|
| Aggregate root removal / stereotype-demotion / rename | hard-fail |
| Stereotype changed (any class) | hard-fail |
| Degraded baseline (HEAD warning) | hard-fail |
| Subscribed internal `<<Domain Event>>` removed | — | **stale** — reconcile the commands diagram's `%% Messaging` marker first | regen after reconcile |
| Subscribed internal `<<Domain Event>>` renamed (R6 / remove+add) | — | **stale** — reconcile the commands diagram's marker + `on_<event>` handler first | regen after reconcile |
| Subscribed internal `<<Domain Event>>` attribute add / remove / rename | — | — | **regen** for the affected consumer(s) (`event-fields-writer`; low-confidence sub-blocks flagged in italic prose) |
| Subscribed internal `<<Domain Event>>` attribute type change | — | — | — (Table 3 records names, not types) |
| Subscribed internal `<<Domain Event>>` method change | — | — | — |
| Non-subscribed `<<Domain Event>>` lifecycle/member change | — | — | — |
| New `<<Domain Event>>` added | — | — | — (subscription candidate; no spec change until a `%% Messaging` marker references it) |
| `: emits <Event>` edge removed but the event class survives (event is subscribed) | — | — | — (byte-stable; "dead subscription" operator warning) |
| Aggregate-root / entity / VO attribute or method change (no event involved) | — | — | — |
| Entity / VO / TypedDict / Command / Service / Repository lifecycle change | — | — | — |
| Domain `<<Command>>` lifecycle/member change | — | — | — (command side not modeled in the consumer spec) |
| Domain prose change (P1–P4), including the bounded-context `title:` | — | — | — |
| Multi-tenancy flip on the domain root (no event gained/lost `tenant_id`) | — | — | — |

Legend:
- **regen** — `event-fields-writer` re-runs for the affected consumer(s) and replaces Table 3 in place from the current commands + domain diagrams; existing content (including italic low-confidence flags) is discarded and re-derived.
- **stale / reconcile** — Table 2 references a domain event the domain diagram no longer declares (or has renamed); the commands diagram's `%% Messaging - <consumer>` marker (and the `<AggregateRoot>Commands.on_<event>` handler) must be reconciled first, then `event-tables-writer` + `event-fields-writer` re-run for that consumer.
- **— (byte-stable)** — table is not touched.
- **hard-fail** — the updater bails out with a clear operator instruction (see *Hard-fail conditions*).

Because the only domain-sensitive table is Table 3 and `event-fields-writer` always replaces it wholesale, there is no per-row/per-sub-block splice and no exceptions/test-plan analog to refresh. The consumer-spec pipeline's three agents are independent: a domain-driven update re-runs `event-fields-writer` alone (Table 3) except in the stale-Table-2 case, which additionally re-runs `event-tables-writer` (Table 2) after the operator reconciles the commands diagram. `consumer-spec-initializer` (Table 1) never re-runs for a domain-driven change.

---

## Hard-fail conditions

Mirror the domain / persistence / application `update-specs` failure semantics. Each prints exactly one `ERROR:` line and exits, directing the operator to reconcile the diagrams and re-run the consumer-spec pipeline (or `/messaging-spec:generate-code <domain_diagram> <consumer_name>`):

- **Aggregate root removal** in `## Class Lifecycle → Removed` — the whole diagram set, and every consumer spec under `<stem>.messaging/`, is invalid.
- **Aggregate root stereotype change** in `## Class Lifecycle → Stereotype Changed` (old or new bucket = `<<Aggregate Root>>`).
- **Aggregate root rename** (reported as `removed (old)` + `added (new)`) — cascades to the commands diagram's class names + filenames (`old-name.commands.md` → `new-name.commands.md`), the `<stem>.messaging/` folder name, the `%% Messaging` markers' `<Source>` cells, and the `<pkg>.domain.<root_snake>` import root used by every generated dispatcher/handler. Route to: rename the diagrams + folder, reconcile the markers, then re-run `/messaging-spec:generate-code` per consumer.
- **Any stereotype change** in the domain report — `## Class Lifecycle → Stereotype Changed` non-empty (subsumes the aggregate-root case; also covers `<<Domain Event>>` ⇄ other re-classifications that invalidate `internal` subscriptions).
- **Degraded baseline** — `_warning: HEAD ..._` line in the domain report Summary.

A subscribed internal `<<Domain Event>>` being **removed or renamed** is *not* a true hard-fail (the rest of every consumer spec is fine), but it is an **abort-and-reconcile-the-commands-diagram** case: the updater should detect it from `updates.md`, identify the affected consumer(s), and surface "reconcile the `%% Messaging - <consumer>` marker (and the `on_<event>` handler on `<AggregateRoot>Commands`) in `<stem>.commands.md`, then re-run `event-tables-writer` + `event-fields-writer` for `<consumer>`" rather than running `event-fields-writer` blind against an orphaned Table 2 row.

---

## Out-of-scope but worth flagging to the operator

These belong in operator-facing warnings, not in the spec content itself:

- **The commands diagram is the dominant trigger surface.** Most consumer-spec changes — a consumer added/removed, an event added/removed from a consumer's `%% Messaging` block, the `Type` / `Source Destination` / `Command Class` / `Command Method` of a row changed, an `<AggregateRoot>Commands.on_<event>` handler signature changed, an `external` event's wire shape changed — originate in `<stem>.commands.md`, not the domain diagram, and `<stem>.domain/updates.md` does not capture them. A complete messaging-spec updater needs a `messaging-spec:updates-detector` analog that diffs the commands diagram (its `%% Messaging` blocks, its external `<<Domain Event>>` nodes, and the `on_<event>` signatures), **or** must accept that those changes are handled by re-running the consumer-spec pipeline / `/messaging-spec:generate-code`. This is *the* central design decision for the updater.
- **`external` events are wholly outside the domain axis.** Their classes are declared on *this* service's commands diagram (the foreign service's published-event contracts). A domain change can never touch an `external` Table 2 or Table 3 row. Their drift is a commands-diagram concern.
- **The command-handler side of a consumer is not spec-modeled.** Table 1's *Commands queue name* is the only consumer-spec trace of the command side; there is no command inventory table. Domain `<<Command>>` changes (and the `command-handlers` / `command-replies` / `command-dispatchers` code they drive) are reconciled by re-running `/messaging-spec:generate-code` (which reads the commands diagram), not by any consumer-spec update. Consider this a known modeling gap.
- **Aggregate-root rename cascades to filenames, folders, and import roots.** Per `messaging-spec:naming-conventions`, the aggregate stem drives `<stem>.commands.md` and `<stem>.messaging/`; the root class name drives the `<pkg>.domain.<root_snake>` import path baked into every generated dispatcher/handler. A domain-`updates.md`-driven updater cannot perform that cascade.
- **No append-only history.** Unlike persistence's `§2.Migrations`, every consumer-spec table is a pure snapshot. The updater carries no row-immutability contract and no delta-driven appender; "update" = "re-run `event-fields-writer` (and, in the stale-Table-2 case, `event-tables-writer`) for the affected consumer(s)".
- **The updater must enumerate consumers itself.** `<stem>.domain/updates.md` does not list consumers — they live in the commands diagram's `%% Messaging - <consumer_name>` markers (and on disk as `<stem>.messaging/*.md`). The updater scans `<stem>.messaging/` (and/or the commands-diagram markers) and, for each consumer, intersects its `internal` Table 2 rows with the changed-domain-event set from `updates.md`.
- **Code regen.** This concern stops at the consumer spec. The per-consumer `messaging/<consumer>/` submodule, the `containers.py` / `entrypoint.py` / `__main__.py` wiring, the `constants.py` constants, and the handler integration tests are owned by `/messaging-spec:generate-code` — a separate updater concern (analogous to `notes/code-updater-approach-c.md` on the domain side).
- **Concurrent updaters.** Two operators on parallel branches both re-running the updater produce a normal Git merge conflict on a consumer's `<consumer>.md`, resolved by standard merge tooling. Not an updater bug.

---

## Dispatch tiers for a messaging-spec updater

Three natural tiers fall out of the type list, mirroring the domain / persistence / application dispatch tiers:

1. **Hard-fail** — aggregate-root lifecycle / stereotype-demotion / rename, any stereotype change, degraded baseline. Operator reconciles the diagrams + folders and re-runs the consumer-spec pipeline / `/messaging-spec:generate-code`. *(Adjacent sub-case — abort-and-reconcile, not a true hard-fail:* a subscribed internal `<<Domain Event>>` removed/renamed ⇒ reconcile the affected consumer's `%% Messaging` marker + `on_<event>` handler in the commands diagram, then re-run `event-tables-writer` + `event-fields-writer` for that consumer.*)*
2. **Regen Table 3 per affected consumer** — `domain-events` member changes (attribute add/remove/rename) on a `<<Domain Event>>` that one or more consumers subscribe to as `internal`: for each such consumer, re-run `event-fields-writer <commands_diagram> <consumer_name>`. (`event-fields-writer` reads the current commands diagram for the `Command Parameter` column + `external` rows and the current domain diagram for the `internal`-row `Event Field` values, so it self-reconciles as far as the diagrams allow; low-confidence sub-blocks are re-flagged in italic prose.) Per-consumer scoped — untouched consumers are not re-run.
3. **No-op** — `affected_categories` empty; or `⊆ {data-structures, value-objects, commands, repositories-services}`; or `aggregates` changes that don't touch the root's lifecycle/stereotype/name; or pure prose changes (P1–P4, including the bounded-context `title:`); or `domain-events` changes that touch only events no consumer subscribes to as `internal`; or a `domain-events` change that is only an event *addition*, an attribute *retype*, or a *method* change. Also no-op: a multi-tenancy flip on the domain root that doesn't itself add/remove a `tenant_id` attribute on a subscribed internal event.

Tier 2 is the only "real work" tier, and it is unusually contained: re-run one agent (`event-fields-writer`) for the subset of consumers whose `internal` subscriptions intersect the changed-domain-event set. The persistence-spec design (`spec-updater-approaches.md`) anticipates a chain of these updaters as opt-in tail steps of domain `/update-specs`; a messaging-spec step would be opt-in by the presence of any `<stem>.messaging/*.md` file and would cover only the domain-driven (Tier 2 + the Tier-1 hard-fails) axis above — the commands-diagram axis remains a separate trigger (a `messaging-spec:updates-detector` invocation, or a fresh `/messaging-spec:generate-code` run per consumer).
