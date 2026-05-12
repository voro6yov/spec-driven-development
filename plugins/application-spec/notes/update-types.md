# Application Spec Update Types

Analysis of how every kind of domain-diagram delta — as emitted by `domain-spec:updates-detector` into `<dir>/<stem>.domain/updates.md` — ripples into the **application service specs** at `<dir>/<stem>.application/`: `commands.specs.md`, `queries.specs.md`, and `services.md`.

The goal is to enumerate every distinct kind of change an application-spec updater would have to handle, so it can dispatch the right action per change rather than re-running `/application-spec:generate-specs` from scratch.

This is the application-side analog of `plugins/persistence-spec/notes/update-types.md` and `plugins/domain-spec/notes/update-types.md`. It assumes the domain `updates.md` is already produced; the application updater **consumes that report directly** (same as the persistence updater) and never re-diffs the domain diagram. It does **not** consume the domain `specs.md` — the application-spec writers read the domain *diagram*, not the domain spec, so the application updater can run before / independently of the domain spec being regenerated.

**One structural difference from persistence-spec dominates the design:** the application spec is derived from *three* hand-authored diagrams, not one. See *The three-diagram trigger surface* below — the rest of this catalog covers only the domain-driven axis.

---

## The three-diagram trigger surface

Per `application-spec:naming-conventions`, three hand-authored Mermaid diagrams feed the application spec for one aggregate:

| Diagram | Path | Diffed by | Diff artifact |
|---|---|---|---|
| Domain | `<dir>/<stem>.md` | `domain-spec:updates-detector` | `<dir>/<stem>.domain/updates.md` |
| Commands application service | `<dir>/<stem>.commands.md` | — *(nothing today)* | — |
| Queries application service | `<dir>/<stem>.queries.md` | — *(nothing today)* | — |

Which application-spec artifact reads which diagram:

| Artifact | Producer | Domain diagram | Commands diagram | Queries diagram |
|---|---|:-:|:-:|:-:|
| `commands.specs.md` → `## Dependencies` | `commands-deps-writer` | — | ✅ | — |
| `commands.specs.md` → `## Method Specifications` | `commands-methods-writer` | ✅ | ✅ | — |
| `commands.specs.md` → `## Application Exceptions` | `commands-methods-writer` (stub) → `application-exceptions-specifier` (enriched) | — *(reads the methods section)* | — | — |
| `queries.specs.md` → `## Dependencies` | `queries-deps-writer` | — | — | ✅ |
| `queries.specs.md` → `## Method Specifications` | `queries-methods-writer` | ✅ | — | ✅ |
| `queries.specs.md` → `## Application Exceptions` | `queries-methods-writer` (stub) → `application-exceptions-specifier` (enriched) | — *(reads the methods section)* | — | — |
| `services.md` | `services-finder` | ✅ *(validation only)* | ✅ *(validation only)* | ✅ *(validation only)* |

The consequence: a domain-`updates.md`-only updater covers exactly **one of three trigger axes**. The two `## Dependencies` sections are *pure functions of the commands/queries diagrams* — no domain delta can ever touch them. And the most common application-spec changes in practice — a command/query method added/removed, a method signature changed, a collaborator added/dropped, multi-tenancy added — all originate in the *application-service* diagrams and never appear in `<stem>.domain/updates.md`.

So a complete application-spec updater needs one of:

- **(A)** an `application-spec:updates-detector` analog that diffs `<stem>.commands.md` / `<stem>.queries.md` (emitting `<stem>.application/updates.md`), invoked alongside the domain-`updates.md` consumption; **or**
- **(B)** accepting that commands/queries-diagram changes are handled by re-running `/application-spec:generate-specs`, with the domain-driven updater handling only the ripple cataloged here.

This document catalogs the **domain-driven axis** — what an updater must do with `<stem>.domain/updates.md`. The app-diagram axis is a parallel, larger concern; see *Out-of-scope but worth flagging*.

---

## Snapshot only — no append-only log

Unlike persistence-spec, where `§2.Migrations` is a cumulative changeset history that must never be rewritten, **every application-spec section is a pure snapshot** — fully regeneratable from the three diagrams (plus, for `## Application Exceptions`, the method flows the methods writer just produced). There is no migration-log equivalent, no row-immutability contract, no delta-driven appender.

So the application-spec updater is structurally simpler than the persistence one. The only open design question is **granularity**:

- **Whole-pipeline regen** — re-run `/application-spec:generate-specs` end-to-end. Correct, simplest, but produces a noisy `git diff` (regenerates both sides, both exception sets, the services report) for a one-line change.
- **Per-side regen** — re-run only the affected side's writer + the exceptions enricher + that side's merger + `services-finder`. Tighter, but the merger needs all three fragments (`.deps.md`, `.methods.md`, `.exceptions.md`) on disk, so it implies re-running that side's deps writer too (byte-stable on a domain-only change).
- **Per-section / per-method-block splice** — splice only the regenerated `## Method Specifications` and `## Application Exceptions` sections into the existing `<side>.specs.md`, leaving `## Dependencies` byte-identical; optionally splice only the touched `### Method:` blocks (the application-side analog of domain-spec's per-class splice in `notes/spec-updater-approach-b.md`). Tightest diff; most updater code.

The per-method-block splice is the closest analog to the chosen domain-spec design, but the application-spec writers regenerate a whole side's methods section in one pass (they have no "regenerate method X only" mode), so a splicer would need to diff the writer's fresh output against the live file at `### Method:` granularity. As with persistence-spec, hand-edits inside the spec are **not a preservation goal** — the operator's contract is "the spec is regenerated from the diagrams, not curated."

---

## Application spec sections and their domain-sensitivity

| Section | Kind | Owner agent | Domain-diagram-sensitive to |
|---|---|---|---|
| **`<side>.specs.md` → `## Dependencies`** (Repositories / Domain Services / External Interfaces / Message Publishers for commands; Query Repositories / External Interfaces for queries) | snapshot | `commands-deps-writer` / `queries-deps-writer` | **Nothing.** Pure function of the `<AggregateRoot><Side>` class node + its links in the commands/queries diagram. No domain delta reaches it. |
| **`<side>.specs.md` → `## Method Specifications`** (one `### Method:` block per public method: Purpose, Requires Aggregate State *(commands only)*, Method Flow, Postconditions *(commands)* / Returns *(queries)*) | snapshot | `commands-methods-writer` / `queries-methods-writer` | The aggregate root's public API + constructor signature (commands); the `Command/Query<AggregateRoot>Repository` finder set; domain `<<Service>>` / external-interface method signatures; the aggregate's child-entity collection structure (commands, drives `Requires Aggregate State`); the domain diagram's advisory prose (collaborator hints, status-gating, defaulting, postcondition invariants, External-Interface hints). |
| **`<side>.specs.md` → `## Application Exceptions`** (full class spec per exception: Base, Code, Pattern, Constructor, Message) | snapshot | `commands-methods-writer` / `queries-methods-writer` (stub) → `application-exceptions-specifier` (enriched) | Indirect only — a function of the `## Method Specifications` section's `raise <X>Error` lines, the raising methods' parameter lists, and the preceding `Call <repo>.<finder>(<args>)` flow steps. Domain repository-finder churn ripples here because the chosen load-step finder + args drive the exception constructor's parameter list (the pair-derived rule). |
| **`services.md`** (`# Services` + one `## <ServiceIdentifier>` block per collaborator: Attr name, Classification, Interfaces, Consumers) | snapshot | `services-finder` | The set of `<<Service>>`-stereotyped classes in the domain diagram (validation: a service named in a `## Dependencies → Domain Services` bullet *must* exist with the `<<Service>>` stereotype). The bullet set itself comes from the commands/queries diagrams, so the *content* of `services.md` is app-diagram-derived; the domain diagram only gates whether the regen succeeds. |

The downstream artifacts — the `<aggregate>_commands.py` / `<aggregate>_queries.py` implementations, infrastructure stubs, test fakes, DI providers, conftest fixtures, the application exception classes appended to the domain aggregate's `exceptions.py`, and the integration tests — are owned by `/application-spec:generate-code`. They are **out of scope** for the spec updater (analogous to `notes/code-updater-approach-c.md` on the domain side).

---

## Domain shape constraints

Load-bearing facts about how the application spec relates to the domain diagram:

- **The domain diagram is one of three inputs.** The trigger for a domain-driven application update is `<stem>.domain/updates.md`. Commands/queries-diagram changes are a separate axis (see above).
- **Exactly one `<<Aggregate Root>>` per domain diagram.** The same invariant the domain and persistence updaters lean on. Removal, stereotype demotion, or rename of the root is a hard-fail for the application updater (the `<AggregateRoot>Commands` / `<AggregateRoot>Queries` services lose their anchor — and a rename also moves the diagram filenames).
- **Domain `<<Event>>` and `<<Command>>` classes never appear in the application method specs.** The commands-side publish step is generic (`Extract events from the aggregate and publish via event_publisher` / `Publish any pending commands via command_producer`) — it names no specific event or command class. So a pure `<<Event>>`-or-`<<Command>>` change in the domain footer leaves the application spec byte-stable.
- **The `Command<AggregateRoot>Repository` / `Query<AggregateRoot>Repository` ABCs are domain-owned**, and the application methods writers consume their finder sets: `commands-methods-writer` picks the load-step finder from the command repo's domain-diagram finders (Step 5d); `queries-methods-writer` requires a *same-name* finder on the query repo for every non-external-interface query method (Step 5e). Finder churn on these ABCs is a category that *does* affect the application spec — and can break the regen (abort) if a needed finder is renamed/removed.
- **Domain `<<Service>>` classes are referenced from the *commands* diagram and validated against the domain diagram.** A `<AggregateRoot>Commands --() SubjectDetection : uses` link in the commands diagram requires `SubjectDetection` to exist as a `<<Service>>` in the domain diagram. Removing / renaming / re-stereotyping that domain class — without first reconciling the commands diagram — makes `commands-methods-writer` (Step 4) and `services-finder` (Step 4 validation) abort.
- **The `<AggregateRoot>Commands` / `<AggregateRoot>Queries` class names come from the commands/queries diagrams**, not from any domain class and not from the domain diagram's `title:` directive. A bounded-context rename (domain `title:` change) is byte-neutral for the application spec.
- **Application-spec multi-tenancy is an application-diagram property.** Whether the application exceptions get a `tenant_id` constructor param depends on whether the *application-service method signatures* declare `tenant_id: str` (the `application-exceptions-specifier`'s `<has_tenant>` detection scans the methods' parameter lists). A domain-only `tenant_id` flip on the aggregate root does **not** change the application spec until the commands/queries diagrams' method signatures are updated to add/drop the parameter — see *Out-of-band signals*.
- **Command methods always return `<AggregateRoot>`** (hard invariant). The return type is never a signal and never carries a domain delta. Query methods return DTOs/value-objects/primitives, declared verbatim in the *queries* diagram — `queries-methods-writer` re-emits the token unchanged and never validates it against a domain registry, so a domain `<<TypedDict>>` rename does not change `queries.methods.md` (the queries diagram still declares the old token until the operator reconciles it).

---

## Mapping `affected_categories` → application-spec impact

Per the canonical category order from `domain-spec:updates-report-template`:

### 1. `data-structures` (`<<TypedDict>>`)

Near-byte-neutral for the application spec.

- **Commands side** — command methods always return `<AggregateRoot>`; no TypedDict appears in a command return type or flow step. **Byte-neutral.**
- **Queries side** — query methods return DTOs/TypedDicts, but the queries *diagram* declares the return token and `queries-methods-writer` re-emits it verbatim. A TypedDict **rename** doesn't change `queries.methods.md` (until the operator fixes the queries diagram — and then it's a queries-diagram change). A TypedDict **field add/remove/retype** doesn't change the return token either. The only ripple: `queries-methods-writer`'s optional Returns shape-hint prose (`<Aggregate>Info` → `TypedDict with the entity's fields`) — a field change *may* nudge that one clause. So: **at most a Returns-line prose tweak on the queries side.**
- **`## Application Exceptions`, `services.md`** — byte-neutral.
- **Net:** `data-structures` alone → **no-op** (or trivial queries-side Returns prose drift).

### 2. `value-objects` (`<<Value Object>>`)

Mostly a commands-side concern, and mostly postcondition prose.

- **VO added / removed on the root** → the aggregate's constructor signature (`<AggregateRoot>.new(...)` / `<aggregate>_of_*`) changes, so `commands-methods-writer` Step 6 re-enumerates the **factory postconditions' seeded-fields list**; non-factory postcondition bullets that name the VO attribute (`<vo_attr>` overwritten with new `<VO>`) regen. → `commands.methods.md` regen.
- **VO added / removed on a child entity** → postcondition prose for command methods that mutate that child; → `commands.methods.md` regen.
- **VO field added / removed / retyped** → the postcondition names the VO, not its fields, so no postcondition-text change; **byte-neutral** unless the change forces the corresponding aggregate method's signature to change *and* the command method's signature was reconciled too (then it's a commands-diagram change).
- **VO becomes polymorphic** (subtype branches appear) → a persistence/mapper concern; the application spec doesn't model VO polymorphism. **Byte-neutral.**
- **Status-field VO presence flip on the root or a child** (`status: <<Value Object>>` added/removed) → the valid `Requires Aggregate State` `<status>` vocabulary changes; status-gating itself is detected from prose, so this usually rides along with a P1/P2 prose change. → `commands.methods.md` regen on the gated methods.
- **Collection-of-VO multiplicity flip on the root** → if the inner item gets re-stereotyped to `<<Entity>>`, this is a children flip (see `aggregates`).
- **Queries side** — queries go through DTOs, not the aggregate; VO changes don't touch the query-repo finder signatures. **Near-byte-neutral** (optional Returns shape-hint prose at most).
- **`## Application Exceptions`, `services.md`** — byte-neutral.
- **Net:** `value-objects` → `commands.methods.md` regen (factory seeded-fields, postcondition VO names, possibly `Requires Aggregate State`); transitively `## Application Exceptions` re-derive (usually byte-stable); near-no-op for the queries side.

### 3. `domain-events` (`<<Event>>`)

**No command- or query-side method-spec impact.** The publish step is generic. Postconditions *may* name a specific event if the description prose names it — but an event rename rides along with a P1/P2 prose change, not as a `domain-events`-only delta. Skip this category at dispatch time.

### 4. `commands` (`<<Command>>` — the *domain message dataclass*, not the application `Commands` service)

**No persistence-of-state to update, and no naming in the spec.** Domain `<<Command>>` dataclasses are cross-context message payloads dispatched via `command_producer` — the application command method's publish step handles them generically (`Publish any pending commands via command_producer`), naming no specific class. **Byte-neutral.** Skip.

> ⚠ **Naming-collision warning.** The `commands` *category* (domain `<<Command>>` dataclasses) is unrelated to the `commands` *side* of the application spec (`<AggregateRoot>Commands`). `affected_categories: [commands]` is a no-op for the application spec.

### 5. `aggregates` (`<<Aggregate Root>>`, `<<Entity>>`)

The largest blast radius — but concentrated on the commands side.

- **Aggregate-root method renamed / removed** → if the commands diagram still declares a command method that resolved to it via the canonical shape (Step 5c), `commands-methods-writer` **ABORTS** (`Command method <name> on <AggregateRoot>Commands has no same-named public method on <AggregateRoot>`). The commands diagram must be reconciled first. When it has been (the operator already renamed the command method too), the change shows up in the commands-diagram axis, not in `<stem>.domain/updates.md`.
- **Aggregate-root method signature changed** (params added/removed) → the flow's aggregate-call args are sourced from the *command* method's params, not the aggregate's, so the flow step doesn't change; a postcondition derived from the method name doesn't change either. **Near-byte-neutral.**
- **Aggregate-root method added** → byte-neutral unless the commands diagram adds a corresponding command method (a commands-diagram change).
- **Aggregate constructor (`new` / `<aggregate>_of_*`) signature changed** → factory-shape command methods' postconditions regen (the seeded-fields enumeration).
- **Aggregate-root attribute add / remove / type change** → factory-postcondition prose (`a new <Aggregate> exists with ... empty <collections>`) and, if the attribute is a child-entity collection, the `Requires Aggregate State` vocabulary. → `commands.methods.md` regen. *Type* changes alone are near-byte-neutral (the application service calls methods, not attributes).
- **Entity added** (new child-entity collection on the root) → `commands-methods-writer` Step 5e re-indexes child collections; a new `has_<child_plural>:n` key becomes valid; any command method whose flow targets the new child (a `<child>_id` param, or an `add_<child>_*` / `update_<child>` / `remove_<child>` / `on_<child>_*` aggregate call) gets a `Requires Aggregate State` value. → `commands.methods.md` regen.
- **Entity removed** → mirror; the `has_<removed_child>` key stops being valid; a command method that targeted it falls back to `empty`. → regen.
- **Entity attribute add / remove / type change** → postcondition prose for command methods mutating that child. → regen.
- **Queries side** — queries don't go through the aggregate root (it need not even be declared in the domain diagram for `queries-methods-writer`); an aggregate-API change is **byte-neutral** for the queries side unless it rides along with a query-repo finder change (see `repositories-services`).
- **`## Application Exceptions`** — exception constructors are derived from the raising method's identity params or the preceding repo-call's args; an aggregate-API/attribute change touches neither. **Byte-neutral** unless a repo finder change rides along.
- **`services.md`** — byte-neutral.
- **Hard-fails:** aggregate root **removed** (`commands-methods-writer` Step 4 aborts on `<AggregateRoot> not declared in the domain diagram`); root **stereotype-demoted** (same); root **renamed** (the commands/queries diagrams still say `OldNameCommands` *and* their filenames `old-name.commands.md` no longer match the renamed stem — a coordinated multi-file rename).
- **Net:** `aggregates` → `commands.methods.md` regen (factory seeded-fields, postcondition prose, `Requires Aggregate State`, child-collection re-index); transitively `## Application Exceptions` re-derive (usually byte-stable); byte-neutral for the queries side; potential **ABORT** if the aggregate API no longer supports a command method the commands diagram still declares; **hard-fail** on root removal / stereotype-demotion / rename.

### 6. `repositories-services` (`<<Repository>>`, `<<Service>>`)

Repository-finder churn and domain-service method changes both land here; pure `<<Service>>` lifecycle is filtered by whether the application diagrams reference the service.

- **`Command<AggregateRoot>Repository` finder added / removed / signature-changed** → `commands-methods-writer` Step 5d picks the load-step finder from the command repo's domain-diagram finders. A finder *added* → the writer may switch to it (tiebreak: most params → `_of_` in name → earliest declared) → the load step's finder + args change. A finder *removed* that was the chosen load-step finder → the writer falls to the next-best subset → the load step changes. A finder *removed* with no remaining subset finder → **ABORTS** (`no suitable finder exists for the load step of <method>`). A finder *signature change* → the chosen-finder match may shift. → `commands.methods.md` regen (load step) **and** `## Application Exceptions` re-derive (the pair-derived exception ctor follows the chosen finder's args).
- **`Query<AggregateRoot>Repository` finder renamed / removed** → `queries-methods-writer` Step 5e requires a *same-name* finder for every non-external-interface query method. A finder *renamed* or *removed* that a query method needs → **ABORTS** (`a non-External-Interface-shape query method has no same-named finder method on the primary Query Repository`). The queries diagram must be reconciled first. A finder *signature change* → the query method's own params are passed through verbatim, so the flow step doesn't change → **near-byte-neutral**. A finder *return-type change* → may nudge the Step-6 Returns shape-hint prose.
- **`Command<AggregateRoot>Repository` / `Query<AggregateRoot>Repository` interface removed** → `commands-methods-writer` / `queries-methods-writer` (Step 4) **ABORT** (`a Command<X>Repository / Query<X>Repository referenced from the <side> diagram is missing from the domain diagram`). Hard-fail / malformed-report.
- **`Command<AggregateRoot>Repository` loses `save(...)`** → `commands-methods-writer` Step 4 **ABORTS** (`the repository must declare save(<aggregate>) and at least one finder`). Hard-fail.
- **Domain `<<Service>>` referenced by the commands diagram, removed / stereotype-changed / renamed** → `commands-methods-writer` Step 4 **ABORTS** (`a Domain Service referenced from the commands diagram is missing from the domain diagram`) **and** `services-finder` Step 4 **ABORTS** (`InterfaceClass must exist as a class declaration in <domain_diagram> with the <<Service>> stereotype`). The commands diagram must be reconciled first. Hard-fail.
- **Domain `<<Service>>` method signature changed** → `commands-methods-writer` Step 5b (collaborator-call shape) checks whether the service declares a method taking `<AggregateRoot>` as a parameter; a signature change can flip a command method between collaborator-call (5b) and canonical (5c). → `commands.methods.md` regen.
- **Query-side external interface (the `I<Interface>` an External-Interface-shape query method's hint references) — operation removed / renamed, or interface removed** → `queries-methods-writer` Step 5a validates the hint's `<operation>` against the interface's domain-diagram methods → **ABORTS** if it no longer resolves. The queries diagram (the hint prose) must be reconciled.
- **Domain `<<Service>>` added** → only matters if the commands diagram references it (a commands-diagram change). Domain-only addition: byte-neutral. (If the commands diagram *already* references it — meaning the prior `generate-specs` run would have aborted — then once added, it surfaces as a new `## Dependencies → Domain Services` bullet → `services.md` regen.)
- **`<<Repository>>` interface added** (a *new* repository ABC, not the established command/query ones) → only matters if a command/query method references it (a commands/queries-diagram change). Treat a bare domain-side repository addition as informational.
- **Net:** `repositories-services` → `commands.methods.md` regen on `Command<AggregateRoot>Repository` finder churn or a referenced domain `<<Service>>`'s method-signature change; `queries.methods.md` regen / **ABORT** on `Query<AggregateRoot>Repository` finder churn or query-side external-interface operation churn; transitively `## Application Exceptions` re-derive; `services.md` re-validate; **hard-fail / malformed-report** on repository-interface removal, `save` removal, or domain-`<<Service>>` removal/stereotype-change/rename that the application diagrams still reference. Skip the category entirely when its only contributor is a `<<Service>>` change to a service the application diagrams do **not** reference.

---

## Out-of-band signals (not a direct `affected_categories` entry)

These are derived from member/relationship deltas in `## Per-Class Changes` (or are explicitly *not* derivable from the domain report at all):

- **Repository-finder churn** — technically a `repositories-services` member change (it surfaces under the repository class's `## Per-Class Changes → Members` block as `Method added/removed/changed`), but it is the single highest-impact `repositories-services` sub-type for the application spec: it drives the load-step finder choice (commands, Step 5d) and the same-name-finder requirement (queries, Step 5e). Worth dispatching on directly.
- **Aggregate constructor signature change** — surfaces as a `Method changed: new(...)` (or `<aggregate>_of_*(...)`) entry inside the aggregate root's Members block; the `aggregates` category fires. Drives the factory-postcondition seeded-fields enumeration. Worth naming as a sub-type.
- **Children flip** — derive from any `<<Entity>>` lifecycle entry under `## Class Lifecycle` **or** a composition-multiplicity flip on the root that crosses the "single inline → collection" boundary. The `aggregates` category fires anyway; this signal determines *what* `commands-methods-writer` Step 5e re-indexes (the `has_<child_plural>` vocabulary) and which methods get a new `Requires Aggregate State` value.
- **Multi-tenancy flip** — **NOT a domain-`updates.md`-driven signal for the application spec.** Application-spec multi-tenancy is a property of the *application-service method signatures* (`tenant_id: str` parameters), which is the commands/queries diagrams' concern. A domain-only `tenant_id` add/remove on the aggregate root is byte-neutral for the application spec; it takes effect only once the commands/queries diagrams' method signatures are updated (a commands/queries-diagram change). This is a deliberate divergence from the persistence-spec model, where `tenant_id` on the root *is* the trigger.
- **Bounded-context rename** — **not applicable.** The `<AggregateRoot>Commands` / `<AggregateRoot>Queries` class names come from the commands/queries diagrams' class nodes, not the domain diagram's `title:`. A domain-`title:` change is byte-neutral for the application spec. (It surfaces in `## Orphan Prose Changes → Preamble` of the domain report; the application updater simply ignores it.)

---

## Update types

Mirroring the domain-spec catalog (L / M / R / P / C codes), here is the application-spec response to each domain-side delta:

### L. Lifecycle updates (whole-class, in the domain diagram)

- **L1. Class added** — dispatch by stereotype:
  - `<<Aggregate Root>>` → impossible on an existing spec; treat as malformed.
  - `<<Entity>>` → children flip → `commands-methods-writer` Step 5e re-index → `commands.methods.md` regen (`Requires Aggregate State` for command methods targeting the new child).
  - `<<Value Object>>` → if composed on the root → factory postconditions regen (seeded-fields list) + `commands.methods.md` regen; otherwise mostly postcondition prose.
  - `<<TypedDict>>` → near-byte-neutral (queries-side Returns shape-hint prose at most).
  - `<<Event>>` / `<<Command>>` → byte-neutral.
  - `<<Service>>` → byte-neutral unless the commands diagram already references it (in which case the prior `generate-specs` would have aborted); once added it surfaces as a new `## Dependencies → Domain Services` bullet → `services.md` regen.
  - `<<Repository>>` → a *new* repository ABC matters only if a command/query method references it (a commands/queries-diagram change); the established `Command/Query<AggregateRoot>Repository` cannot be re-added. Informational.
- **L2. Class removed** — symmetric to L1:
  - `<<Aggregate Root>>` → **hard-fail**.
  - `<<Entity>>` → children flip → `commands.methods.md` regen (the `has_<removed_child>` key stops being valid).
  - `<<Value Object>>` → on the root → factory postconditions regen; otherwise postcondition prose.
  - `<<TypedDict>>` → if it is a query method's return token, the queries diagram still declares it (stale) — the operator must reconcile the queries diagram. Domain-side removal alone: near-byte-neutral.
  - `<<Event>>` / `<<Command>>` → byte-neutral.
  - `<<Service>>` referenced by the commands diagram → `commands-methods-writer` + `services-finder` **ABORT** → **hard-fail / route to reconcile the commands diagram**.
  - `<<Repository>>` (`Command/Query<AggregateRoot>Repository`) → `commands-methods-writer` / `queries-methods-writer` **ABORT** → **hard-fail / malformed-report**.
- **L3. Stereotype changed** — **hard-fail** (route to `/application-spec:generate-specs`), mirroring domain/persistence. The cross-category move means the class is no longer the kind of thing the application spec assumed (e.g. a `<<Service>>` → `<<Entity>>` re-classification breaks `commands-deps-writer`'s and `services-finder`'s validation).

### M. Member updates (in-class, signature-affecting)

- **M1. Attribute added/removed on root or entity** — root: factory-postcondition prose + (if a child collection) `Requires Aggregate State` vocabulary; entity: postcondition prose for command methods mutating that child. → `commands.methods.md` regen. Queries side byte-neutral. May ride along with a children flip (see *Out-of-band signals*). Note: an `id` / `tenant_id` attribute flip on the root does **not** by itself change the application spec (multi-tenancy is an app-diagram property).
- **M2. Attribute type changed** — near-byte-neutral for the application spec (it calls methods, not attributes). Possible postcondition-prose nuance.
- **M3. Attribute visibility changed** — **byte-neutral** (encapsulation is a domain concern; the application service goes through methods).
- **M4. Method added/removed** — on the aggregate root: a *removed* method that a command method resolved to → `commands-methods-writer` **ABORTS** (reconcile the commands diagram first); an *added* method → byte-neutral unless the commands diagram adds a corresponding command method. On a `<<Service>>`: a method add/remove can flip a command method's collaborator-call vs canonical shape → `commands.methods.md` regen. On an entity: postcondition-prose changes for command methods mutating that child. (Repository-method changes are M5.)
- **M5. Method signature changed** — by owner class:
  - **Aggregate root** → the flow's aggregate-call args come from the *command* method, so the flow doesn't change; near-byte-neutral (postcondition prose if a rename, which is really L2+L1).
  - **`Command<AggregateRoot>Repository`** (a finder) → load-step finder choice may shift → `commands.methods.md` regen **+** `## Application Exceptions` re-derive (the pair-derived ctor follows the finder's args). A finder removed with no subset replacement → **ABORT**.
  - **`Query<AggregateRoot>Repository`** (a finder) → if a rename breaks the same-name match for a query method → `queries-methods-writer` **ABORTS**; a pure param/return-type change → near-byte-neutral (modulo Returns prose hint).
  - **Aggregate constructor** (`new` / `<aggregate>_of_*`) → factory postconditions regen.
  - **Domain `<<Service>>`** → collaborator-call vs canonical shape may flip → `commands.methods.md` regen.

### R. Relationship updates (cross-class topology, in the domain diagram)

- **R1. Composition added/removed** (`*--`) — root → `<<Entity>>` = children flip (L1/L2 entity path). Root → `<<Value Object>>` = VO-on-root path (factory postconditions). Entity → nested child = nested-collection structure → `Requires Aggregate State` re-index.
- **R2. Dependency added/removed** (`-->`) — in the *domain* diagram: `-->` with `: emits ...` adds/removes a domain `<<Event>>` (byte-neutral); `-->` to a `<<Service>>` / external interface is service-injection wiring *inside the domain layer* — the application service's collaborators are declared in the *commands/queries* diagrams, not the domain diagram, so this is byte-neutral for the application spec.
- **R3. Realization added/removed** (`--()`) — in the *domain* diagram: `--()` with `: emits ...` adds/removes a domain `<<Command>>` (byte-neutral); `--()` to a `<<Repository>>` is the repository-realizes-aggregate edge (informational). Byte-neutral.
- **R4. Inheritance added/removed** (`<|--`) — the only structural effect is making a `<<Value Object>>` or `<<Entity>>` polymorphic, which the application spec doesn't model. **Byte-neutral.**
- **R5. Multiplicity changed** — the boundary that matters is "single inline → collection": if the inner item is `<<Entity>>`, this is a children flip → `Requires Aggregate State` re-index; otherwise byte-neutral.
- **R6. Label changed** (`: emits OrderPlaced` → `: emits OrderConfirmed`) — event-name rename; the publish step is generic → byte-neutral; possible postcondition-prose drift if the prose names the event (which surfaces as a P1/P2 change).
- **R7. Orphan relationship change** — the unresolved source is typically an inferred `<<Event>>` or `<<Command>>` → byte-neutral. If it resolves to a `<<Repository>>` or `<<Service>>` the application diagrams reference, treat per the `repositories-services` rules.

### P. Prose updates (semantic, not structural)

**Domain prose is not unconditionally byte-neutral for the application spec.** Both methods writers retain the domain diagram's surrounding prose as `<domain_description>` advisory text and scan it for: per-method Purpose one-liners, postcondition invariants, collaborator hints (which can force the collaborator-call shape, commands), status-gating (which sets `Requires Aggregate State`, commands), parameter-defaulting steps (commands), and External-Interface hints (which can force the external-interface shape, queries). A domain prose change *can* therefore re-shape a method spec.

- **P1. Class-keyed prose changed** (`### ClassName`) — re-run the affected side's methods writer; it re-reads the advisory description. Output **may** be byte-stable if the change didn't touch any advisory channel (Purpose / postconditions / collaborator hint / status-gating / defaulting / External-Interface hint). Note: the methods writers' *labelled-block* lookup keys on bare `### <method>` headings, not the domain report's `### ClassName.method` convention — so the labelled channel rarely fires from domain prose; the free-text advisory channel is the realistic one.
- **P2. Method-keyed prose changed** (`### ClassName.method` / `### ClassName.method(...)`) — same as P1.
- **P3. Orphan prose changed — `Preamble`** — the domain title/overview; the application spec doesn't use the domain title. **Byte-neutral** in practice (the preamble is part of the advisory description, so a far-fetched edit could nudge a hint — treat as byte-neutral).
- **P4. Orphan prose changed — free-form** (`Notes`, `Glossary`, …) — advisory description only; **byte-neutral** in practice.

### C. Composite / derived signals

- **C1. Pure prose change, zero structural** — re-run the methods writer(s); output usually byte-stable. Not a *guaranteed* no-op for the application spec (unlike persistence), but a no-op in practice unless the prose touched an advisory channel.
- **C2. Pure structural, zero prose** — standard regen path; the methods writers don't consume prose for the structural bits, so they produce identical output regardless of prose.
- **C3. `Affected Categories` empty** — **no-op**. By the report-template footer contract this implies empty `## Class Lifecycle`, no `## Per-Class Changes`, and no `## Orphan Relationship Changes`, so the only content is orphan prose — advisory-only for the application spec.
- **C4. `Affected Categories` spans multiple** — fan out to the affected sides; `commands.methods.md` regenerates whenever `aggregates` or a `Command<AggregateRoot>Repository`-touching `repositories-services` change is present; `queries.methods.md` whenever a `Query<AggregateRoot>Repository`-touching `repositories-services` change (or a queries-return-token-affecting `data-structures` change) is present; the exceptions enricher + the affected side's merger + `services-finder` always re-run downstream of any methods change.
- **C5. First-run / degraded baseline** (HEAD warning in the domain report Summary) — **hard-fail** (route to `/application-spec:generate-specs`).

---

## Section-affected matrix

Quick lookup for "given a domain-side update, what happens in each application-spec section". The `## Dependencies` columns are always `—` for any domain-driven change — `## Dependencies` is a pure function of the commands/queries diagrams.

| Domain update | `commands.specs.md` Dependencies | `commands.specs.md` Method Specifications | `commands.specs.md` / `queries.specs.md` Application Exceptions | `queries.specs.md` Dependencies | `queries.specs.md` Method Specifications | `services.md` |
|---|:-:|---|---|:-:|---|---|
| Aggregate root removal / stereotype-demotion / rename | hard-fail |
| `Command/Query<AggregateRoot>Repository` interface removal, or `Command<AggregateRoot>Repository` loses `save` | hard-fail |
| Domain `<<Service>>` removed / stereotype-changed / renamed (referenced by the app diagrams) | hard-fail |
| Stereotype changed (any class) | hard-fail |
| Degraded baseline (HEAD warning) | hard-fail |
| Entity added/removed (children flip) | — | regen (`Requires Aggregate State` re-index) | re-derive (usually stable) | — | — | — |
| Entity attribute add/remove/type | — | regen (postcondition prose) | re-derive (usually stable) | — | — | — |
| Root attribute add/remove/type (non-identity, non-tenant) | — | regen (postcondition prose; `Requires Aggregate State` if a child collection) | re-derive (usually stable) | — | — | — |
| Aggregate constructor signature change | — | regen (factory seeded-fields) | re-derive (usually stable) | — | — | — |
| Aggregate-root method renamed/removed (command method resolves to it) | — | **ABORT** — reconcile commands diagram first | — | — | — | — |
| Aggregate-root method signature change (params) | — | — (args sourced from the command method) | — | — | — | — |
| `Command<AggregateRoot>Repository` finder add/remove/change | — | regen (load-step finder choice) | re-derive (ctor follows finder args) | — | — | — |
| `Query<AggregateRoot>Repository` finder renamed/removed (query method needs it) | — | — | — | — | **ABORT** — reconcile queries diagram first | — |
| `Query<AggregateRoot>Repository` finder signature/return-type change | — | — | — | — | regen (Returns shape-hint prose) | — |
| Domain `<<Service>>` method signature change | — | regen (collaborator-call vs canonical shape) | re-derive (usually stable) | — | — | — |
| Query-side external-interface operation removed/renamed (hint references it) | — | — | — | — | **ABORT** — reconcile queries diagram (hint) first | — |
| VO added/removed on the root | — | regen (factory seeded-fields, postcondition VO names) | re-derive (usually stable) | — | — | — |
| VO field add/remove/retype | — | — (postcondition names the VO, not its fields) | — | — | — | — |
| Status-VO presence flip on root or entity | — | regen (`Requires Aggregate State` vocabulary on gated methods) | re-derive (usually stable) | — | — | — |
| Domain prose keyed to the aggregate root / a command method (P1/P2) | — | re-run writer (advisory description re-read; may be byte-stable) | re-derive (usually stable) | — | — | — |
| Domain prose keyed to a query method (P1/P2) | — | — | re-derive (usually stable) | — | re-run writer (may be byte-stable) | — |
| Domain `<<TypedDict>>` lifecycle/member change | — | — | — | — | — (queries diagram declares the return token; possible Returns shape-hint prose) | — |
| Domain `<<Event>>` / `<<Command>>` lifecycle/member change | — | — | — | — | — | — |
| Domain `<<Service>>` added (commands diagram already references it) | — | regen if it changes a method's shape | re-derive | — | — | regen (new Domain Services bullet) |
| Bounded-context (domain `title:`) rename | — | — | — | — | — | — |
| Multi-tenancy flip on the domain root (not yet mirrored in the app-diagram method signatures) | — | — | — | — | — | — |

Legend:
- **regen** — the snapshot writer re-runs and replaces the section/sub-block from the current diagrams; existing content is discarded.
- **re-derive** — `application-exceptions-specifier` re-runs over the freshly-regenerated method flows; usually byte-stable because Base / Code / Constructor / Message are deterministic from the exception name + the raising method's identity params.
- **— (byte-stable)** — section is not touched.
- **ABORT** — the writer agent aborts; the operator must reconcile the commands/queries diagram before the updater can run.
- **hard-fail** — the updater bails out with a clear operator instruction (see *Hard-fail conditions*).

Because `commands-methods-writer` owns `commands.specs.md`'s `## Method Specifications` *and* the `commands.exceptions.md` stub, and `application-exceptions-specifier` processes **both** sides in one call, any methods change on either side re-runs the exceptions enricher (rewriting both exceptions sets — idempotent on the unchanged side). `commands.specs.md` and `queries.specs.md` are otherwise independent and regenerate per side.

---

## Hard-fail conditions

Mirror the domain `update-specs` / persistence `update-specs` failure semantics. Each prints exactly one `ERROR:` line and exits, directing the operator to `/application-spec:generate-specs <domain_diagram>` (after reconciling the commands/queries diagrams where the message says so):

- **Aggregate root removal** in `## Class Lifecycle → Removed` — `<AggregateRoot>Commands` / `<AggregateRoot>Queries` lose their anchor.
- **Aggregate root stereotype change** in `## Class Lifecycle → Stereotype Changed` (old or new bucket = `<<Aggregate Root>>`).
- **Aggregate root rename** (reported as `removed (old)` + `added (new)`) — cascades to the commands/queries diagram *class names* **and filenames** (`old-name.commands.md` → `new-name.commands.md`) and the `<stem>.application/` folder name; a coordinated multi-file rename the domain-`updates.md`-driven updater cannot perform. Route to: rename the diagrams, then `/application-spec:generate-specs`.
- **`Command<AggregateRoot>Repository` or `Query<AggregateRoot>Repository` interface lifecycle change** (added or removed) — `commands-methods-writer` / `queries-methods-writer` abort; a domain aggregate without its repositories cannot back an application service.
- **`Command<AggregateRoot>Repository` loses `save(...)`** — `commands-methods-writer` Step 4 aborts.
- **Domain `<<Service>>` removed / stereotype-changed / renamed while still referenced by the commands diagram** — `commands-methods-writer` and `services-finder` abort. Route to: reconcile the commands diagram, then `/application-spec:generate-specs` (or, if the service truly went away, drop the collaborator from the commands diagram first).
- **Any stereotype change** in the domain report — `## Class Lifecycle → Stereotype Changed` non-empty (subsumes the aggregate-root case above).
- **Degraded baseline** — `_warning: HEAD ..._` line in the domain report Summary.
- *(Optional)* **Children flip + aggregate-API churn + repository-finder churn in the same diff** — the shape change may be large enough that regeneration from scratch is safer than three concurrent splices. Worth a flag, not necessarily a default.

A `Query<AggregateRoot>Repository` finder rename/removal that breaks a query method, or a query-side external-interface operation rename/removal, makes `queries-methods-writer` abort — these are *abort-and-reconcile-the-queries-diagram* cases rather than full hard-fails (the rest of the spec is fine), but the updater should surface the same "reconcile the queries diagram, then re-run" instruction.

---

## Out-of-scope but worth flagging to the operator

These belong in operator-facing warnings, not in the spec content itself:

- **The commands/queries diagrams are the second and third trigger surfaces.** Most application-spec changes — a command/query method added/removed, a method signature changed, a collaborator added/dropped, multi-tenancy added — originate in the *application-service* diagrams, not the domain diagram, and `<stem>.domain/updates.md` does not capture them. A complete application-spec updater needs an `application-spec:updates-detector` analog that diffs `<stem>.commands.md` / `<stem>.queries.md` (emitting `<stem>.application/updates.md`), **or** must accept that those changes are handled by re-running `/application-spec:generate-specs`. This is *the* central design decision for the updater.
- **Aggregate-root rename cascades to diagram filenames.** Per `application-spec:naming-conventions`, the aggregate stem drives `<stem>.commands.md`, `<stem>.queries.md`, and `<stem>.application/`. A domain-`updates.md`-driven updater cannot perform that cascade; the operator renames the diagrams, then re-runs `/application-spec:generate-specs`.
- **Multi-tenancy is an application-diagram property.** A domain-only `tenant_id` flip on the aggregate root does not change the application spec; the application-service method signatures must add/drop the `tenant_id` parameter (in the commands/queries diagrams). The `application-exceptions-specifier`'s `<has_tenant>` detection keys off the *method* parameter lists, not the domain root — so a domain-only flip leaves the exception constructors (and the spec generally) byte-stable.
- **Commands/queries diagram reconciliation precedes domain-API and domain-service removals.** Removing/renaming an aggregate-root method that a command method resolves to, removing/renaming/re-stereotyping a domain `<<Service>>` the commands diagram references, removing a `Command/Query<AggregateRoot>Repository` finder a query method needs, or renaming the aggregate root all make the methods writers / `services-finder` abort. The updater should detect the pending abort from `updates.md` and route to "reconcile the commands/queries diagram, then re-run" rather than running the writers blind.
- **No append-only history.** Unlike persistence's `§2.Migrations`, every application-spec section is a pure snapshot — fully regeneratable. The updater carries no row-immutability contract and no delta-driven appender; "update" = "re-run the affected writers" (or splice their fresh output).
- **The standalone `<side>.exceptions.md` fragments are consumed by the merger.** `specs-merger` deletes `<side>.deps.md`, `<side>.methods.md`, and `<side>.exceptions.md` after inlining them into `<side>.specs.md`. The durable application-spec artifacts after a `generate-specs` run are `commands.specs.md`, `queries.specs.md`, and `services.md`; the `## Application Exceptions` *content* lives inside `<side>.specs.md`. (The `naming-conventions` table currently also lists `commands.exceptions.md` / `queries.exceptions.md` as surviving artifacts — a documentation inconsistency in the plugin; for updater purposes, treat the inlined `## Application Exceptions` section as the source of truth.)
- **Code regen.** This concern stops at the spec. The `<aggregate>_commands.py` / `<aggregate>_queries.py` implementations, infrastructure stubs, test fakes, DI providers, conftest fixtures, the application exception classes appended to the domain aggregate's `exceptions.py`, and the integration tests are owned by `/application-spec:generate-code` — a separate updater concern.
- **Concurrent updaters.** Two operators on parallel branches both re-running the updater produce a normal Git merge conflict on `<side>.specs.md`, resolved by standard merge tooling. Not an updater bug.

---

## Dispatch tiers for an application-spec updater

Four natural tiers fall out of the type list, mirroring the domain-spec and persistence-spec dispatch tiers:

1. **Hard-fail** — aggregate-root lifecycle / stereotype / rename, any stereotype change, `Command/Query<AggregateRoot>Repository` interface lifecycle, `Command<AggregateRoot>Repository` `save` removal, domain-`<<Service>>` removal/stereotype-change/rename (when referenced by the app diagrams), degraded baseline. Operator runs `/application-spec:generate-specs` (after reconciling the commands/queries diagrams where the message says so).
2. **Regen the commands side** — `aggregates` (aggregate-API / constructor / child-collection / attribute / on-root VO / status-VO changes), `repositories-services` touching `Command<AggregateRoot>Repository` finders or a referenced domain `<<Service>>`'s methods, or domain prose keyed to the aggregate root / a command method: re-run `commands-methods-writer` (also recreate `commands.deps.md` via `commands-deps-writer` if the merger is re-run — byte-stable on a domain-only change — *or* splice only the regenerated `## Method Specifications` + `## Application Exceptions` into the live `commands.specs.md`) → `application-exceptions-specifier` → `specs-merger commands` → `services-finder`. Abort-and-reconcile if `updates.md` shows a pending `commands-methods-writer` abort condition.
3. **Regen the queries side** — `repositories-services` touching `Query<AggregateRoot>Repository` finders or query-side external interfaces, `data-structures` that affects a queries return token, or domain prose keyed to a query method: re-run `queries-methods-writer` (+ `queries-deps-writer` if the merger is re-run) → `application-exceptions-specifier` → `specs-merger queries` → `services-finder`. Abort-and-reconcile if `updates.md` shows a pending `queries-methods-writer` abort condition.
4. **No-op** — `affected_categories` empty; or `⊆ {data-structures (with no queries-return-token impact), domain-events, commands}`; or `repositories-services` whose only contributor is a domain `<<Service>>` not referenced by the application diagrams; or pure prose changes that don't touch any advisory channel the methods writers consume. (When the change is only a `<<Service>>` lifecycle/stereotype change that *is* already reconciled in the commands diagram and changes no method shape, run only `services-finder` — a degenerate sub-case of tier 2.)

Tiers 2 and 3 are not mutually exclusive — a multi-category domain change (`C4`) fans out to both. Both downstream tails (exceptions enricher + the affected side's merger + `services-finder`) run once each.

This updater runs as **Step 11 of domain `/update-specs`** (wired, domain-spec ≥ 0.29.0) — after the persistence Step 10 chain, reading the same `<stem>.domain/updates.md`; see the as-built "Chaining contract" in `persistence-spec/notes/spec-updater-approaches.md` (the cascade is unconditional, and a missing application spec file is a hard-fail that aborts the rest of the chain). That chained step covers only the domain-driven axis above; the commands/queries-diagram axis remains a separate trigger (an `application-spec:updates-detector` invocation, or a fresh `/application-spec:generate-specs` run).
