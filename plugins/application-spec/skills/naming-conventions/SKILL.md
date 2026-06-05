---
name: naming-conventions
description: Cross-plugin naming and layout conventions for diagrams and spec artifacts. Defines the canonical aggregate stem, diagram filenames, and per-plugin sibling folder layout.
when_to_use: Use when scaffolding, reading, or writing any sibling spec file produced by domain-spec, application-spec, persistence-spec, rest-api-spec, or messaging-spec.
user-invocable: false
---

# Naming Conventions

## When to consult

Load this skill before deriving any sibling-artifact path or creating any diagram filename. Every cross-plugin agent reads from / writes to the layout defined here; reconstructing paths by ad-hoc string substitution will diverge from the contract.

## Purpose

- One canonical **aggregate stem** drives every diagram and every artifact for a single aggregate.
- Each plugin's outputs live in a dedicated **sibling folder** next to the diagrams, so artifact lists stay flat regardless of how many specs are generated.
- File names inside a plugin folder are short and generic — the parent folder already encodes which plugin owns the file.

This skill is the single source of truth for those rules. Agents and skills across `domain-spec`, `application-spec`, `persistence-spec`, `rest-api-spec`, and `messaging-spec` derive every input/output path from this convention.

## The aggregate stem

The **aggregate stem** is a kebab-case identifier matching the domain aggregate root (e.g. `order`, `purchase-order`, `product-catalog`). It must satisfy `^[a-z][a-z0-9-]*$`.

Given a domain diagram path `<dir>/<stem>.md`:

- `<dir>` is the **specs directory** — the directory holding every diagram and sibling folder for the aggregate.
- `<stem>` is the **aggregate stem** — the canonical identifier that every other artifact derives from.

Every plugin agent derives `<dir>` and `<stem>` by inspecting the domain-diagram path it receives. There is no second stem and no per-plugin alias.

## Diagram filenames

For an aggregate stem `<stem>`, the three Mermaid class diagrams have fixed names:

| Diagram | Path | Owner |
|---|---|---|
| Domain | `<dir>/<stem>.md` | hand-authored input |
| Commands application service | `<dir>/<stem>.commands.md` | hand-authored input |
| Queries application service | `<dir>/<stem>.queries.md` | hand-authored input |
| Ops application service | `<dir>/<stem>.ops.<op-name>.md` | hand-authored input |

`<op-name>` is a kebab-case discriminator matching `^[a-z][a-z0-9-]*$` and equals the kebab-case of the ops service class name (the unique braced class in the diagram), so `<dir>/order.ops.subject-tagging.md` declares `class SubjectTagging`. An aggregate may have any number of ops diagrams (zero, one, or many), each becoming one free-form orchestration application service. Both `<stem>` and `<op-name>` are dot-free, so the literal `.ops.` separator is unambiguous.

Examples for `<stem> = order`:

```
specs/
  order.md
  order.commands.md
  order.queries.md
  order.ops.subject-tagging.md
```

A plugin that needs a non-domain diagram (e.g. application-spec, messaging-spec) receives that path as an argument; it must not infer it by appending suffixes to the domain path.

## Per-plugin sibling folders

Each plugin owns one folder per aggregate, named `<stem>.<plugin-shortname>/`, sitting next to the diagrams:

| Plugin | Folder |
|---|---|
| domain-spec | `<dir>/<stem>.domain/` |
| application-spec | `<dir>/<stem>.application/` |
| persistence-spec | `<dir>/<stem>.persistence/` |
| rest-api-spec | `<dir>/<stem>.rest-api/` |
| messaging-spec | `<dir>/<stem>.messaging/` |

The folder name is the **plugin short name** without the `-spec` suffix. The folder must be created on first write by the plugin's scaffolder/initializer; subsequent agents in the same plugin assume it exists.

A plugin must never write outside its own folder. The only exceptions are:

- A plugin may **read** any other plugin's folder (cross-plugin reference is fine).
- A plugin may **append** an entry to the diagram file's `## Artifacts` index (which is the diagram itself, not another plugin's folder).

## File naming inside each plugin folder

### `<stem>.domain/` (domain-spec)

| File | Producer | Purpose |
|---|---|---|
| `specs.md` | `class-specifier` → `pattern-assigner` → `specs-merger` | Merged class specification (final) |
| `exceptions.md` | `specs-merger` (stub) → `exceptions-specifier` (enriched) | Domain exceptions |
| `test-plan.md` | `aggregate-tests-planner` | Aggregate unit-test plan |
| `updates.md` | `updates-detector` | Structured diff report (input to `update-specs`) |
| `.specs-tmp/<category>.md` | `class-specifier`, `pattern-assigner` | Transient per-category temp file (deleted by `specs-merger` / `spec-splicer`) |

### `<stem>.application/` (application-spec)

| File | Producer | Purpose |
|---|---|---|
| `commands.specs.md` | `specs-merger` (commands side) | Merged commands spec (final) |
| `commands.exceptions.md` | `commands-methods-writer` (stub) → `application-exceptions-specifier` | Application exceptions raised by commands |
| `queries.specs.md` | `specs-merger` (queries side) | Merged queries spec (final) |
| `queries.exceptions.md` | `queries-methods-writer` (stub) → `application-exceptions-specifier` | Application exceptions raised by queries |
| `services.md` | `services-finder` | Reconciled list of services the application layer must implement |
| `updates.md` | `application-updates-writer` | Structured diff report (input to future `/application-spec:update-code`) |
| `commands.deps.md` | `commands-deps-writer` | Transient — deleted by `specs-merger` |
| `commands.methods.md` | `commands-methods-writer` | Transient — deleted by `specs-merger` |
| `queries.deps.md` | `queries-deps-writer` | Transient — deleted by `specs-merger` |
| `queries.methods.md` | `queries-methods-writer` | Transient — deleted by `specs-merger` |
| `ops.<op-name>.specs.md` | `specs-merger` (ops side) | Merged ops spec (final) — one per ops diagram |
| `ops.<op-name>.exceptions.md` | `ops-methods-writer` (stub) → `application-exceptions-specifier` | Application exceptions raised by this ops service's methods |
| `ops.<op-name>.deps.md` | `ops-deps-writer` | Transient — deleted by `specs-merger` |
| `ops.<op-name>.methods.md` | `ops-methods-writer` | Transient — deleted by `specs-merger` |

The per-side fragments (`commands.deps.md`, `commands.methods.md`, `queries.deps.md`, `queries.methods.md`, and each `ops.<op-name>.{deps,methods}.md`) exist only between writer and merger. After a successful pipeline run, only `commands.specs.md`, `commands.exceptions.md`, `queries.specs.md`, `queries.exceptions.md`, `services.md`, and each ops service's `ops.<op-name>.specs.md` / `ops.<op-name>.exceptions.md` remain.

`<op-name>` matches `^[a-z][a-z0-9-]*$` and equals the kebab-case of the ops service class. One pair of `ops.<op-name>.specs.md` / `ops.<op-name>.exceptions.md` per ops diagram; multiple ops services share the one flat `<stem>.application/` folder (no sub-folder), exactly as `commands`/`queries` artifacts do.

### `<stem>.persistence/` (persistence-spec)

| File | Producer | Purpose |
|---|---|---|
| `command-repo-spec.md` | `command-repo-spec-scaffolder` → `command-repo-spec-pattern-selector` → `command-repo-spec-schema-writer` | Command repository spec (Sections 1–3) |

### `<stem>.rest-api/` (rest-api-spec)

| File | Producer | Purpose |
|---|---|---|
| `spec.md` | `resource-spec-initializer` → `endpoint-tables-writer` → `response-fields-writer` → `request-fields-writer` → `parameter-mapping-writer` | REST API resource spec (Tables 1–6) |

### `<stem>.messaging/` (messaging-spec)

| File | Producer | Purpose |
|---|---|---|
| `<consumer-name>.md` | `consumer-spec-initializer` → `event-tables-writer` → `event-fields-writer` | Per-consumer messaging spec |

`<consumer-name>` is a kebab-case identifier matching `^[a-z][a-z0-9-]*$`, supplied by the user (e.g. `inventory-sync`, `shipping-events`). One file per consumer; multiple consumers may share `<stem>.messaging/`.

## Worked example

For aggregate stem `order` with two messaging consumers `inventory-sync` and `shipping-events`, plus one ops service `subject-tagging` (declaring `class SubjectTagging`), after running every pipeline:

```
specs/
  order.md
  order.commands.md
  order.queries.md
  order.ops.subject-tagging.md

  order.domain/
    specs.md
    exceptions.md
    test-plan.md
    updates.md

  order.application/
    commands.specs.md
    commands.exceptions.md
    queries.specs.md
    queries.exceptions.md
    ops.subject-tagging.specs.md
    ops.subject-tagging.exceptions.md
    services.md
    updates.md

  order.persistence/
    command-repo-spec.md

  order.rest-api/
    spec.md

  order.messaging/
    inventory-sync.md
    shipping-events.md
```

## Path resolution

Every agent and orchestrator receives a path argument and must derive sibling paths from the naming convention rather than asking the caller to pre-resolve them. This section is the single source of truth for that derivation.

### Recovering `<dir>` and `<stem>` from inputs

`<stem>` and `<dir>` are recovered from whichever path the caller supplied:

| Input | Recovery |
|---|---|
| `<domain_diagram>` = `<dir>/<stem>.md` | `<dir>` = directory of input; `<stem>` = basename with `.md` stripped |
| `<commands_diagram>` = `<dir>/<stem>.commands.md` | `<dir>` = directory of input; `<stem>` = basename with `.commands.md` stripped |
| `<queries_diagram>` = `<dir>/<stem>.queries.md` | `<dir>` = directory of input; `<stem>` = basename with `.queries.md` stripped |
| `<ops_diagram>` = `<dir>/<stem>.ops.<op-name>.md` | `<dir>` = directory of input; split the basename (with `.md` stripped) on the literal `.ops.` — both `<stem>` and `<op-name>` are dot-free kebab, so the split is unambiguous: the left part is `<stem>`, the right part is `<op-name>` |
| `<spec_file>` inside `<dir>/<stem>.<plugin>/...` | walk up two segments: the parent's parent is `<dir>`; the parent's basename minus `.<plugin>` is `<stem>` |

`<stem>` must satisfy `^[a-z][a-z0-9-]*$`. If the recovered stem fails this regex, abort with a one-sentence error rather than silently producing nonsense paths.

### Deriving sibling paths from `<stem>`

Once `<dir>` and `<stem>` are recovered, every other artifact path is built from this table:

| Artifact | Path |
|---|---|
| Domain diagram | `<dir>/<stem>.md` |
| Commands diagram | `<dir>/<stem>.commands.md` |
| Queries diagram | `<dir>/<stem>.queries.md` |
| Ops diagram | `<dir>/<stem>.ops.<op-name>.md` |
| Domain merged spec | `<dir>/<stem>.domain/specs.md` |
| Domain exceptions | `<dir>/<stem>.domain/exceptions.md` |
| Domain test plan | `<dir>/<stem>.domain/test-plan.md` |
| Domain updates report | `<dir>/<stem>.domain/updates.md` |
| Application commands spec | `<dir>/<stem>.application/commands.specs.md` |
| Application commands exceptions | `<dir>/<stem>.application/commands.exceptions.md` |
| Application queries spec | `<dir>/<stem>.application/queries.specs.md` |
| Application queries exceptions | `<dir>/<stem>.application/queries.exceptions.md` |
| Application ops spec | `<dir>/<stem>.application/ops.<op-name>.specs.md` |
| Application ops exceptions | `<dir>/<stem>.application/ops.<op-name>.exceptions.md` |
| Application services report | `<dir>/<stem>.application/services.md` |
| Application updates report | `<dir>/<stem>.application/updates.md` |
| Persistence command-repo spec | `<dir>/<stem>.persistence/command-repo-spec.md` |
| REST API resource spec | `<dir>/<stem>.rest-api/spec.md` |
| Messaging consumer spec | `<dir>/<stem>.messaging/<consumer_name>.md` |

The messaging consumer spec (`<consumer_name>`) and the ops artifacts (ops diagram, ops spec, ops exceptions — all keyed on `<op-name>`) are the only paths that require an additional discriminator; every other artifact is fully determined by `<stem>` plus the plugin's identity.

### Caller responsibilities

- **User-facing orchestrator skills** accept exactly `<domain_diagram>` plus non-derivable extras (`<consumer_name>`, `<op-name>`, `<service_identifier>`, `<tests_dir>`, free-text notes). They never require the caller to pre-resolve commands/queries/ops diagrams or sibling spec files — derivation happens inside the orchestrator using the tables above.
- **Per-plugin agents** accept exactly the diagram they primarily read — `<domain_diagram>` for `domain-spec`, `application-spec`, `persistence-spec`, and `rest-api-spec`; `<commands_diagram>` for `messaging-spec` — plus non-derivable extras. Sibling spec files inside the agent's own plugin folder are derived internally.
- **Reconstruction by string substitution is forbidden** (e.g. `path.replace('.md', '.specs.md')`). Always recover `<stem>` and `<dir>` per the recovery table first, then build new paths from the artifact table.

## What NOT to do

- Do **not** put plugin artifacts at the same level as the diagrams (the old `<stem>.specs.md`, `<stem>.exceptions.md` flat layout is replaced by per-plugin folders).
- Do **not** use hyphenated diagram names like `order-commands.md` — the canonical separator between the aggregate stem and the role suffix is a dot (`order.commands.md`).
- Do **not** duplicate the plugin name inside an artifact filename (`order.persistence/persistence.command-repo-spec.md` is wrong; use `order.persistence/command-repo-spec.md`).
- Do **not** write into another plugin's folder. Cross-plugin references are read-only.
- Do **not** invent additional sibling files outside this convention. New artifact kinds must be added to this skill first, then to the producing agent.
