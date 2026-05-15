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

### Python package name derivation

`<stem>` is kebab-case for **spec paths and filenames only**. The Python package name that appears on disk inside `src/<pkg>/domain/` is the same value in **snake_case** — obtained by replacing every `-` with `_`. Every agent that materializes a Python directory (notably `target-locations-finder`, `package-preparer`, `scaffold-builder`, `code-implementer`) must perform this conversion before touching the filesystem.

| Diagram stem | Spec folder | Python package directory |
|---|---|---|
| `order` | `<dir>/order.domain/` | `src/<pkg>/domain/order/` |
| `cache-type` | `<dir>/cache-type.domain/` | `src/<pkg>/domain/cache_type/` |
| `purchase-order` | `<dir>/purchase-order.domain/` | `src/<pkg>/domain/purchase_order/` |

Validate the derived Python package name against `^[a-z][a-z0-9_]*$`. Agents must abort if validation fails; they must never emit a path segment containing `-` under `src/`.

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

Examples for `<stem> = order`:

```
specs/
  order.md
  order.commands.md
  order.queries.md
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
| `commands.deps.md` | `commands-deps-writer` | Transient — deleted by `specs-merger` |
| `commands.methods.md` | `commands-methods-writer` | Transient — deleted by `specs-merger` |
| `queries.deps.md` | `queries-deps-writer` | Transient — deleted by `specs-merger` |
| `queries.methods.md` | `queries-methods-writer` | Transient — deleted by `specs-merger` |

The per-side fragments (`commands.deps.md`, `commands.methods.md`, `queries.deps.md`, `queries.methods.md`) exist only between writer and merger. After a successful pipeline run, only `commands.specs.md`, `commands.exceptions.md`, `queries.specs.md`, `queries.exceptions.md`, and `services.md` remain.

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

For aggregate stem `order` with two messaging consumers `inventory-sync` and `shipping-events`, after running every pipeline:

```
specs/
  order.md
  order.commands.md
  order.queries.md

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
    services.md

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
| `<spec_file>` inside `<dir>/<stem>.<plugin>/...` | walk up two segments: the parent's parent is `<dir>`; the parent's basename minus `.<plugin>` is `<stem>` |

`<stem>` must satisfy `^[a-z][a-z0-9-]*$`. If the recovered stem fails this regex, abort with a one-sentence error rather than silently producing nonsense paths.

### Deriving sibling paths from `<stem>`

Once `<dir>` and `<stem>` are recovered, every other artifact path is built from this table:

| Artifact | Path |
|---|---|
| Domain diagram | `<dir>/<stem>.md` |
| Commands diagram | `<dir>/<stem>.commands.md` |
| Queries diagram | `<dir>/<stem>.queries.md` |
| Domain merged spec | `<dir>/<stem>.domain/specs.md` |
| Domain exceptions | `<dir>/<stem>.domain/exceptions.md` |
| Domain test plan | `<dir>/<stem>.domain/test-plan.md` |
| Domain updates report | `<dir>/<stem>.domain/updates.md` |
| Application commands spec | `<dir>/<stem>.application/commands.specs.md` |
| Application commands exceptions | `<dir>/<stem>.application/commands.exceptions.md` |
| Application queries spec | `<dir>/<stem>.application/queries.specs.md` |
| Application queries exceptions | `<dir>/<stem>.application/queries.exceptions.md` |
| Application services report | `<dir>/<stem>.application/services.md` |
| Persistence command-repo spec | `<dir>/<stem>.persistence/command-repo-spec.md` |
| REST API resource spec | `<dir>/<stem>.rest-api/spec.md` |
| Messaging consumer spec | `<dir>/<stem>.messaging/<consumer_name>.md` |

The messaging consumer spec is the only path that requires an additional discriminator (`<consumer_name>`); every other artifact is fully determined by `<stem>` plus the plugin's identity.

### Caller responsibilities

- **User-facing orchestrator skills** accept exactly `<domain_diagram>` plus non-derivable extras (`<consumer_name>`, `<service_identifier>`, `<tests_dir>`, free-text notes). They never require the caller to pre-resolve commands/queries diagrams or sibling spec files — derivation happens inside the orchestrator using the tables above.
- **Per-plugin agents** accept exactly the diagram they primarily read — `<domain_diagram>` for `domain-spec`, `application-spec`, `persistence-spec`, and `rest-api-spec`; `<commands_diagram>` for `messaging-spec` — plus non-derivable extras. Sibling spec files inside the agent's own plugin folder are derived internally.
- **Reconstruction by string substitution is forbidden** (e.g. `path.replace('.md', '.specs.md')`). Always recover `<stem>` and `<dir>` per the recovery table first, then build new paths from the artifact table.

## Path hygiene (shared rules for file-writing agents)

These rules apply to every agent that materializes files or directories under the project tree. They are the contract that prevents stray paths, shadow directories, and kebab-case Python imports.

1. **Reject relative paths.** Every `<path>` argument an agent writes to must be absolute. Abort with an explicit error rather than resolving against the current working directory.
2. **Reject hyphens in Python paths.** Any path segment that is (or descends into) a Python package — anything under `src/` or used as `<package_path>`, `<output_dir>`, `<aggregate_pkg_dir>`, `<module_path>` — must satisfy `^[a-z][a-z0-9_]*(/[a-z][a-z0-9_]*)*$` for its leaf segments. Treat a hyphen in any of those segments as a caller bug.
3. **Implementers never create new modules.** An agent whose contract is "read-modify-write a scaffolded file" must verify the file already exists at the supplied path before reading and again before writing. A missing file is a hard failure, not a signal to create one.
4. **Prefer locations-report paths over re-derivation.** When an orchestrator has a locations report (e.g. from `domain-spec:target-locations-finder`), it must pass each chained agent the exact path from the report rather than passing an ancestor and letting the agent re-derive. The report is the single source of truth for where things go.
5. **Contain side effects to an expected ancestor.** When an orchestrator fans out parallel writers across a known set of paths, each writer should sanity-check that its target is contained within the orchestrator-supplied root (e.g. every `<module_path>` must begin with `<aggregate_pkg_dir>`).

Agents that need to apply these rules cite this section by name (e.g. "Per `domain-spec:naming-conventions`, Path hygiene rule 3, abort if the file does not exist") instead of restating them.

## What NOT to do

- Do **not** put plugin artifacts at the same level as the diagrams (the old `<stem>.specs.md`, `<stem>.exceptions.md` flat layout is replaced by per-plugin folders).
- Do **not** use hyphenated diagram names like `order-commands.md` — the canonical separator between the aggregate stem and the role suffix is a dot (`order.commands.md`).
- Do **not** duplicate the plugin name inside an artifact filename (`order.persistence/persistence.command-repo-spec.md` is wrong; use `order.persistence/command-repo-spec.md`).
- Do **not** write into another plugin's folder. Cross-plugin references are read-only.
- Do **not** invent additional sibling files outside this convention. New artifact kinds must be added to this skill first, then to the producing agent.
