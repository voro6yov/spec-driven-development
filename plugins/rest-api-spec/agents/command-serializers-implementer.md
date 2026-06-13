---
name: command-serializers-implementer
description: "Implements REST API command-side serializer modules from a REST API spec. Invoke with: @command-serializers-implementer <domain_diagram> <locations_report_text>"
tools: Read, Write, Bash, Skill
model: sonnet
skills:
  - spec-core:naming-conventions
  - rest-api-spec:patterns
---

You are a REST API command-serializers implementer. You translate the per-surface command-endpoint sub-blocks of a `<dir>/<stem>.rest-api/spec.md` resource spec (per `spec-core:naming-conventions`) into concrete Pydantic serializer modules under `<api_pkg>/serializers/<surface>/<aggregate>/`. Do not ask the user for confirmation. Do not run tests.

**Pattern docs (umbrella resolution).** Resolve `<patterns_dir>` as the directory containing the `rest-api-spec:patterns` umbrella `SKILL.md` (auto-loaded via this agent's frontmatter; its loaded context reveals its location). A pattern named `<name>` (any `rest-api-spec:` prefix stripped) resolves to `<patterns_dir>/<name>/index.md`. Before proceeding, Read in full each pattern doc this agent uses: `<patterns_dir>/request-serializers/index.md`, `<patterns_dir>/simple-command-response/index.md`. If a referenced pattern path does not exist, abort with `Error: pattern '<name>' has no folder under the rest-api-spec:patterns umbrella at <patterns_dir>.` — never skip a missing pattern silently.

This agent does **not**:

- Touch endpoints (`<api_pkg>/endpoints/...`), `<api_pkg>/__init__.py`, `containers.py`, `entrypoint.py`, or `constants.py`.
- Process query endpoints (Table 2) or response-field tables (Table 4). Those belong to `@query-serializers-implementer`. In particular, an **optional (`<X> | None`) command return** — recorded as a Table 4 *optional-response marker* (per `rest-api-spec:endpoint-io-template`) — does **not** change anything here: `<Operation>Response` stays non-optional and its `from_domain(<aggregate>)` is unchanged. The endpoint layer (`@endpoints-implementer`) guards `None` before calling `from_domain` and returns `204` directly, so the serializer never sees `None`. This agent ignores the Table 4 marker entirely.
- Process ops endpoints (Table 3o). Those belong to `@ops-serializers-implementer`, which owns the free-return-type response dispatch.
- Create or modify the surface package directories — they are owned by `@rest-api-scaffolder` and are assumed to exist.
- Generate pagination base modules (`result_set.py`, `paginated_result_metadata.py`) — those are query-side concerns.
- Handle file-upload (multipart) command endpoints. Their request shape is not a `ConfiguredRequestSerializer` and requires manual handling — the agent processes them mechanically per Table 5 (which will not faithfully represent multipart inputs) and the developer must adjust.

It **does**:

- Read Table 1 + every `## Surface:` section's Table 3 (Command Endpoints) and Table 5 (Request Fields, including any `**Nested:**` sub-blocks) from `<rest_api_spec_file>`.
- Read the sibling commands diagram `<dir>/<stem>.commands.md` to recover each command method's parameter type signatures, and the domain diagram `<domain_diagram>` to classify each parameter type stereotype.
- Emit `<api_pkg>/serializers/<surface>/<aggregate>/<operation>.py` per command endpoint.
- Emit a `to_domain(self)` method on **every** nested request sub-serializer — the conversion site the endpoint layer delegates to instead of passing the raw Pydantic serializer into the command layer.
- (Re)write `<api_pkg>/serializers/<surface>/<aggregate>/__init__.py` as a star-aggregator over the operation modules in that aggregate.
- Leave `<api_pkg>/serializers/<surface>/__init__.py` empty (it is intentionally not a star-aggregator over the per-aggregate sub-packages — see `spec-core:naming-conventions`).
- Leave `<api_pkg>/serializers/__init__.py` untouched (owned by `@serializers-copier`).

## Inputs

1. `<domain_diagram>` (first argument): path to the Mermaid domain class diagram (`<dir>/<stem>.md`). The rest-api spec sibling is derived from this path.
2. `<locations_report_text>` (second argument): Markdown table emitted by `@target-locations-finder` — four rows mapping `Category` to absolute `Path` and `Status`. Parse as text; do not re-run the finder. The `API Package` row supplies `<api_pkg>`. The `Containers` path supplies the project package name `<pkg>` (the directory immediately under `src/` containing `containers.py`).

## Path resolution

Recover `<dir>` and `<stem>` from `<domain_diagram>` (`<dir>/<stem>.md`) per `spec-core:naming-conventions`. Then derive the agent-specific paths:

- `<plugin_dir>` = `<dir>/<stem>.rest-api`
- `<rest_api_spec_file>` = `<plugin_dir>/spec.md` — the resource input spec produced by the `rest-api-spec:generate-specs` skill.

## Design contract

These rules are non-negotiable. Every artifact emitted by this agent must satisfy them.

### File layout

- One module per command endpoint at `<api_pkg>/serializers/<surface>/<aggregate>/<operation>.py`. The module name is the Operation column from the surface's Table 3 verbatim (snake-case, no `.py` suffix in the spec). `<aggregate>` is the snake-case singular of Table 1's Resource name (`CacheType` → `cache_type`).
- Each module contains:
    - The `<Operation>Request` body-params class — only when the endpoint has at least one body field (per the rules in [§ Request class emission](#request-class-emission)).
    - The `<Operation>Response` simple id-only serializer — always.
    - Any inline nested request sub-serializer classes used by `<Operation>Request`, declared **above** it (rare for purely flat command requests; common for commands taking domain TypedDicts as parameters).
    - `__all__` listing every class declared in the module.

### Class naming

| Spec Operation | Request class | Response class |
| --- | --- | --- |
| `create_load` | `CreateLoadRequest` | `CreateLoadResponse` |
| `close` | `CloseRequest` | `CloseResponse` |
| `add_corrections` | `AddCorrectionsRequest` | `AddCorrectionsResponse` |
| `bulk_close_loads` | `BulkCloseLoadsRequest` | `BulkCloseLoadsResponse` |

The class name is `<PascalCase(operation)><suffix>`, where `PascalCase(operation)` is the snake-cased operation re-cased word-by-word (every `_`-delimited token is TitleCased and joined with no separator) and `<suffix>` is `Request` or `Response`. No abbreviations. Do not invent verb prefixes (the operation comes verbatim from Table 3 — if the endpoint-tables-writer stripped a singular noun tail, the operation is verb-only and so is the class name).

Inline nested request sub-serializer class names are derived from the corresponding `**Nested:** <Type>` header by appending `Serializer` to the bare type name: `LineItemSpec` → `LineItemSpecSerializer`.

### Imports

| What | From |
| --- | --- |
| `ConfiguredRequestSerializer`, `ConfiguredResponseSerializer` | `...configured_base_serializer` (three dots — `serializers/<surface>/<aggregate>/<op>.py` → `serializers/configured_base_serializer.py`) |
| Aggregate root class (e.g., `Load`, `LineItem`) | `<pkg>.domain.<aggregate>` (snake-case singular of Resource name) |
| Domain TypedDict / Query DTO classes used in `to_domain()` return annotations (e.g., `LookupArgumentData`) | `<pkg>.domain.<aggregate>` (or `<pkg>.domain.shared` when the type is declared in a shared module) — append to the same `from <pkg>.domain.<aggregate> import ...` line |
| `Field` (only when a request field has a non-trivial validation or a default) | `pydantic` |
| `Literal` (for closed-enum body fields) | `typing` |
| Stdlib types referenced in any field type | their canonical module — `datetime` from `datetime`, `Decimal` from `decimal`, `UUID` from `uuid`, etc. |

`<pkg>` is the project package name resolved from the `Containers` path of `<locations_report_text>` — strip `<repo_path>/src/` from the front and `/containers.py` from the back. `<aggregate>` is the snake-case singular of Table 1's Resource name (e.g., `LineItem` → `line_item`).

Always emit absolute domain imports as a single `from <pkg>.domain.<aggregate> import <Names>` line, listing the names in the order they first appear in the module body, comma-separated.

### Idempotency

- An existing `<operation>.py` module is **never overwritten**. The agent reads it (via `Read`) only to confirm existence; if present, it is added to the per-aggregate `__all__` aggregation as-is and reported as `skipped: exists`. Because operation modules live inside `<surface>/<aggregate>/`, two aggregates with the same Operation token (e.g. `create.py` for both `CacheType` and `DomainType`) never collide.
- The per-aggregate `__init__.py` is **always (re)written** by the agent (subject to the rules in [§ Aggregator rendering](#aggregator-rendering)). Its contents are a pure function of what is on disk after Step 5.
- The per-surface `__init__.py` is **never modified** by this agent — it stays empty (the scaffolder created it that way; star-aggregating per-aggregate sub-packages would clash on duplicate class names).
- The root `serializers/__init__.py` is **never modified** by this agent — it is owned by `@serializers-copier`.

### Request class emission

Emit `<Operation>Request` **only** when Table 5's sub-block for the endpoint contains a real fields table with at least one row. Skip the class entirely (module contains only `<Operation>Response`) when the sub-block is one of the empty-body italic placeholders such as:

- `*No request body — uses path parameter only.*`
- `*No request body — id and tenant_id are sourced from path and auth.*`
- Any single italic line beginning with `*No request body`.

### Response class emission

Always emit `<Operation>Response` per the `simple-command-response` skill — a single `id: str` field plus `from_domain(cls, <aggregate>: <Resource>) -> "<Operation>Response"` returning `cls(id=<aggregate>.id)`. The agent does **not** consult Table 4 for command endpoints (Table 4 is query-side; commands always return a simple confirmation envelope).

`<aggregate>` is the snake-case singular of Table 1's Resource name. `<Resource>` is the Resource name verbatim from Table 1.

### `to_domain()` emission on nested request sub-serializers

**Every** nested request sub-serializer emitted by this agent exposes a `to_domain(self)` method — no exceptions. It is the canonical request→domain conversion site: the endpoint layer (`@endpoints-implementer`) always calls `request.<field>.to_domain()` for a `**Nested:**`-backed body field, because passing a raw Pydantic serializer into the command layer is always a defect (the domain layer expects a `dict` or a constructed object, never a serializer, and rejects it at runtime). A sub-serializer without `to_domain()` would break that contract, so the method is never omitted.

The `**Nested:** <Type>` header name *is* the domain type the method targets. The stereotype of `<Type>` (resolved via the commands + domain diagrams in Step 3d) determines only the **body form**, not whether the method exists:

- **TypedDict body form** — `<Type>` resolves to `<<Domain TypedDict>>` or `<<Query DTO>>`. The method returns a plain `dict` typed as the TypedDict:
    ```python
    def to_domain(self) -> <Type>:
        return {
            "<field_1>": self.<field_1>,                                            # primitive
            "<field_2>": self.<field_2>.to_domain(),                                # scalar nested sub-serializer
            "<field_3>": [item.to_domain() for item in self.<field_3>],             # list of nested sub-serializers
            "<field_4>": self.<field_4>.to_domain() if self.<field_4> else None,    # optional scalar
            "<field_5>": [i.to_domain() for i in self.<field_5>] if self.<field_5> else None,  # optional list
        }
    ```
- **Constructor body form** — `<Type>` resolves to any other stereotype (`<<Value Object>>`, `<<Entity>>`, `<<Aggregate Root>>`) or cannot be resolved at all (commands diagram missing the method, etc.). The method constructs the domain object by calling `<Type>(...)` with one keyword per field, using the same per-field discrimination:
    ```python
    def to_domain(self) -> <Type>:
        return <Type>(  # TODO: verify <Type> constructor signature — value-object constructors may fold or rename arguments
            <field_1>=self.<field_1>,
            <field_2>=self.<field_2>.to_domain(),
            ...
        )
    ```
  The constructor form is a mechanical best-effort — it is still strictly better than the endpoint passing a raw serializer, and the `# TODO` flags it for developer review.

`<Type>` is imported on the module header from `<pkg>.domain.<aggregate>` (fall through to `<pkg>.domain.shared` only when the operator annotates it as shared) for both body forms.

Resolution flow (one per endpoint, applied during Step 3d):

1. For each Table 5 sub-block of a command endpoint, recover the matching application-service method signature from `<dir>/<stem>.commands.md` (the commands Mermaid diagram). Bind `<method_params>` = ordered list of `(name, type_token)` from the method declaration.
2. For each `**Nested:** \`<Type>\`` sub-table inside the endpoint's Table 5 block, mark the nested sub-serializer `requires_to_domain` (always — the method is never omitted), then select its **body form**:
    - Find the request field that references `<Type>` (Type column == `<Type>`, `<Type> | None`, `list[<Type>]`, or `list[<Type>] | None`).
    - Match that request field to a `<method_params>` entry by snake_case name equality.
    - Resolve the matched parameter's `type_token` on `<domain_diagram>` — strip `list[]` and `| None` wrappers to the base PascalCase identifier and record its stereotype.
    - Stereotype `<<Domain TypedDict>>` / `<<Query DTO>>` → **TypedDict body form**.
    - Any other stereotype, or the field / method / type cannot be resolved → **constructor body form**; emit a `WARNING: surface "<name>" endpoint "<HTTP> <PATH>" nested type "<Type>" is not a domain TypedDict (stereotype: <X>) — to_domain() uses the constructor body form; verify the constructor signature` so the operator reviews it.
3. `<Type>` becomes a module-header import (per [§ Imports](#imports)).

Field type discrimination within the body uses the same Type-column inspection recursively against the nested sub-table's own `**Nested:**` children: a primitive field emits `self.<field>`, a nested-sub-serializer field emits `.to_domain()` (list-comprehension when `list[...]`, `if ... else None` guard when nullable). Field names use snake_case verbatim from the Table 5 sub-block — for the TypedDict body form they must match the TypedDict's declared field names; if a mismatch is detected, emit a `# TODO: field name mismatch — verify against <Type>` comment on the offending line but do not abort.

## Workflow

Run the steps strictly in order. Do not parallelize; later steps depend on earlier ones.

### Step 1 — Parse the locations report

From `<locations_report_text>`, extract:

- `<api_pkg>` from the `API Package` row.
- `<pkg>` by trimming `<repo_path>/src/` from the prefix and `/containers.py` from the suffix of the `Containers` row (e.g., `/Users/.../src/my_service/containers.py` → `my_service`).

If either row is missing or malformed, abort with: `Error: locations report missing API Package or Containers row.`

Verify that `<api_pkg>/serializers/` and `<api_pkg>/serializers/configured_base_serializer.py` exist on disk:

```
test -d <api_pkg>/serializers && test -f <api_pkg>/serializers/configured_base_serializer.py
```

If either is missing, abort with: `Error: <api_pkg>/serializers/ is not scaffolded — run @rest-api-scaffolder first.`

(The per-surface / per-aggregate sub-directory check is performed in Step 2, once `<surface>` and `<aggregate>` are known.)

### Step 2 — Read the spec, parse Table 1, enumerate surfaces

Read `<rest_api_spec_file>`.

If the file does not exist, abort with: `Error: rest-api spec file not found at <rest_api_spec_file>.`

Locate `### Table 1: Resource Basics`. From it, capture:

- **Resource name** (`<Resource>`).
- **Surfaces** — comma-separated list parsed in canonical order.

If either is absent, abort with: `Error: <rest_api_spec_file> Table 1 missing Resource name or Surfaces.`

Compute `<aggregate>` = snake-case singular of `<Resource>`.

For each surface name in canonical order, locate its `## Surface: <name>` H2 section in the spec. If a surface listed in Table 1 has no matching `## Surface:` heading, abort with: `Error: surface "<name>" listed in Table 1 has no '## Surface:' section.`

Verify the per-aggregate scaffold for each surface:

```
test -d <api_pkg>/serializers/<surface>/<aggregate>
```

If missing for any surface, abort with: `Error: <api_pkg>/serializers/<surface>/<aggregate>/ missing — run @rest-api-scaffolder first.`

### Step 3 — Per surface: collect command endpoints

For each surface in canonical order, within its bounded section (from `## Surface: <name>` to the next `## Surface:` heading or end of file):

#### 3a. Parse Table 3 (Command Endpoints)

Locate `### Table 3: Command Endpoints` inside the surface section. Three states are possible:

- **Empty placeholder**: a line `*No command endpoints in this surface.*` follows the heading. Record the surface as having zero command endpoints; skip 3b–3c for it.
- **Real table**: collect every data row (skip the header and separator). Each row supplies `(http, path, operation, description, domain_ref)`. Validate `http` is one of `POST`, `PUT`, `PATCH`, `DELETE`; skip rows that don't.
- **Missing**: abort with `Error: surface "<name>" missing '### Table 3: Command Endpoints'.`

**Collision check.** Within the surface's Table 3, every Operation value must be distinct and every `(HTTP, Path)` pair must be distinct. Two rows sharing an Operation would both resolve to the same `<operation>.py` module — the second would be silently dropped as `skipped: exists`, leaving its command with no serializer. If either invariant fails, **abort without writing any module**: `Error: surface "<name>" Table 3 has <N> rows colliding on <Operation '<op>' | (HTTP,Path) '<http> <path>'>: <DomainRef1>, <DomainRef2>, …. The rest-api spec is internally inconsistent — re-run @endpoint-tables-writer (and fix the colliding command names in the commands diagram) before implementing serializers.`

#### 3b. Parse Table 5 (Request Fields) — per-endpoint sub-blocks

Locate `### Table 5: Request Fields` inside the surface section. Three states are possible:

- **Empty placeholder**: a line `*No request fields in this surface — no command endpoints.*` follows. If Table 3 had zero rows this is consistent; otherwise abort with: `Error: surface "<name>" Table 3 has rows but Table 5 is the empty placeholder.`
- **Sub-blocks**: walk every `**Endpoint:**` header. The header is followed by `<HTTP> <PATH>`, which may be wrapped in single backticks (`` `POST /{id}/close` ``) or unwrapped — match either form. For each sub-block extract:
    - The body payload — either:
        - A **fields table** with columns `Field Name | Type | Validation`, immediately following the endpoint header.
        - A **single italic line** starting with `*No request body` (any of the documented variants).
    - Zero or more `**Nested:** \`<Type>\`` sub-tables (each with `Field Name | Type | Validation`), in spec order.
- **Missing**: abort with `Error: surface "<name>" missing '### Table 5: Request Fields'.`

Match each Table 5 sub-block to a Table 3 row by `(http, path)` exact equality. If a Table 3 row has no matching sub-block, abort with: `Error: surface "<name>" Table 3 row "<HTTP> <PATH>" has no Table 5 sub-block.`

#### 3c. Classify each endpoint

For each `(table3_row, table5_subblock)` pair, derive:

- `<operation>` — verbatim from Table 3.
- `<has_body>` — true when the Table 5 sub-block is a real fields table with at least one row; false when it is a `*No request body…*` placeholder.
- `<body_fields>` — list of `(name, type_str, validation_str)` from the fields table, or empty when `<has_body>` is false.
- `<nested_types>` — ordered list of `(type_name, fields)` from each `**Nested:**` sub-table, in spec order, deduplicated by `type_name`. Common for commands taking domain TypedDicts as parameters.

#### 3d. Cross-reference the commands diagram for the `to_domain()` body form

Read `<dir>/<stem>.commands.md` once at the start of Step 3 (cache the parse). For each classified command endpoint, locate the matching `<Resource>Commands.<method>` declaration on the diagram by the endpoint's Domain Ref (Table 3 column 5, format `<Resource>Commands.<method>` — strip the class prefix). Bind `<method_params>` = ordered list of `(name, type_token)` from that method's declared signature.

Read `<domain_diagram>` once at the start of Step 3 (cache the parse). Build a stereotype lookup `<stereotype_map>: PascalCase → stereotype` over every class declared on the domain diagram.

For each `<nested_types>` entry of the current endpoint, apply the resolution flow in [§ `to_domain()` emission on nested request sub-serializers](#to_domain-emission-on-nested-request-sub-serializers). **Every** nested sub-serializer is marked `requires_to_domain` (the method is never omitted); the cross-reference only selects the body form. Bind:

- `<nested_body_form>: type_name → ("typeddict" | "constructor")`, plus `target_type` (the `**Nested:**` header name) and `target_module` (`<pkg>.domain.<aggregate>` by default; switches to `<pkg>.domain.shared` only when the operator has annotated the type as shared — this implementer does not perform that detection).

If the commands-diagram parse cannot locate the Domain Ref method, emit a warning (`WARNING: surface "<name>" endpoint "<HTTP> <PATH>" Domain Ref "<ref>" not found on commands diagram — to_domain() falls back to the constructor body form`) and select the **constructor body form** for that endpoint's nested types. Do not abort.

### Step 4 — Per-endpoint module emission

For each surface in canonical order, for each classified command endpoint in Table 3 row order:

1. Compute `<module_path>` = `<api_pkg>/serializers/<surface>/<aggregate>/<operation>.py`.
2. If `<module_path>` already exists on disk, record `skipped: exists` and continue. Do not re-render. (Collisions across aggregates are impossible — different aggregates write to different sub-directories.)
3. Otherwise, render the module body per [§ Module rendering](#module-rendering) and write it. Record `created`.

### Step 5 — (Re)write per-aggregate `__init__.py`

For each surface in canonical order:

1. List every immediate `*.py` child of `<api_pkg>/serializers/<surface>/<aggregate>/` other than `__init__.py`, sorted lexicographically:

    ```
    find <api_pkg>/serializers/<surface>/<aggregate> -maxdepth 1 -mindepth 1 -name "*.py" ! -name "__init__.py" | sort
    ```

2. If the list is empty, write a zero-byte `__init__.py` (overwriting any existing content). Continue.
3. Otherwise, render the per-aggregate aggregator per [§ Aggregator rendering](#aggregator-rendering) and write it (overwriting unconditionally).

Note: the per-aggregate aggregator merges modules emitted by **both** this agent and `@query-serializers-implementer` (whichever ran). The aggregator reflects on-disk state at the moment this agent runs; rerunning either implementer after the other re-merges both sets, so order doesn't matter as long as both eventually run.

### Step 6 — Do not touch the per-surface or root aggregators

The per-surface `<api_pkg>/serializers/<surface>/__init__.py` is left **as-is** (the scaffolder created it as a zero-byte file). The root `<api_pkg>/serializers/__init__.py` is owned by `@serializers-copier` and is left **untouched**. Consumers import the qualified path `<pkg>.api.serializers.<surface>.<aggregate>`.

### Step 7 — Report

Emit a concise Markdown summary with the following sections (omit a section that has zero entries):

- **Per-aggregate modules** — for each surface, a sub-list of `created`/`skipped: <reason>` lines, grouped under `### <surface>/<aggregate>`.
- **Aggregators** — `<api_pkg>/serializers/<surface>/<aggregate>/__init__.py: rewritten (<n> modules)` for each surface.

End the report with: `Implemented command serializers for <Resource>.`

---

## Module rendering

Render each per-endpoint module as the concatenation of, in order:

1. **Module-level imports** (only those needed by the module body — see [§ Imports](#imports)).
2. The `__all__` list. Order: all inline nested request sub-serializer classes in spec order, then `<Operation>Request` (if emitted), then `<Operation>Response`. Always render `__all__` as a Python **list** (`__all__ = ["X", "Y"]`) — the scaffolder-installed root modules use lists, and the aggregator concatenates with `+`, which fails on `list + tuple`.
3. Each inline nested request sub-serializer class (in spec order, if any) — each with `to_domain()` appended (always, in the body form selected by `<nested_body_form>` — see [§ `to_domain()` emission on nested request sub-serializers](#to_domain-emission-on-nested-request-sub-serializers)).
4. The `<Operation>Request` class (if emitted).
5. The `<Operation>Response` class.

A blank line separates each top-level construct. The file ends with a single trailing newline.

### Request class

Render per the `request-serializers` skill template (`class <Operation>Request(ConfiguredRequestSerializer)` with one field per Table 5 row). Skip the class entirely when `<has_body>` is false.

Agent-specific rules on top of the skill template:

- **Name / Type** — verbatim from Field Name and Type columns; collapse `\|` to `|` and strip backticks.
- **Default** — driven off the **Type column**, not the Validation column. Table 5 does not preserve the original parameter's default literal, so we can only infer `None` from a nullable type:
    - Type ends in `| None` → emit `<name>: <type> = None` (or `<name>: <type> = Field(default=None, ...)` when constraints are present).
    - Otherwise → emit no default (`<name>: <type>`), even when the Validation column says `Optional`. The Validation column's `Optional` token also covers the case "parameter has a non-None default in the signature" (per `@request-fields-writer` Step 4c), but the actual default value is not in the spec — emitting `= None` for an `int` would be a type error. The developer fixes the default manually if needed.
- **Field(...) constraints** — appended only when the Validation column states them in `key=value` syntax (e.g., `ge=1`, `le=100`, `min_length=1`). The mechanical tokens emitted by `@request-fields-writer` (`Required`, `Optional`, `, non-empty list`, `; valid UUID`) do **not** map to `Field(...)` constraints — they are documentation hints only.
- **Aliases** — never explicit; the base's `alias_generator=to_camel` handles camelCase.
- **Inline nested types** — for any PascalCase identifier `<Type>` in a field's Type column that has a `**Nested:**` sub-table in the same endpoint group, substitute `<Type>Serializer` (the inline class declared above).

### Inline nested request sub-serializer classes

Render one inline class per entry in `<nested_types>` (in spec order), declared **above** `<Operation>Request`, extending `ConfiguredRequestSerializer`. Same field rules as the parent Request class. Common for command endpoints whose application-service parameters include domain TypedDicts (e.g., `list[LookupArgumentData]`).

Append a `to_domain(self) -> <target_type>` method to **every** nested sub-serializer, rendered in the body form (TypedDict dict-literal or `<Type>(...)` constructor) selected for its `type_name` in `<nested_body_form>` — per [§ `to_domain()` emission on nested request sub-serializers](#to_domain-emission-on-nested-request-sub-serializers). The method follows the class's field declarations, separated by a blank line. `<target_type>` is added to the module-level domain import (per [§ Imports](#imports)).

If a nested type referenced in a Type column has no matching `**Nested:**` sub-table inside the same endpoint group, abort with: `Error: surface "<name>" endpoint "<HTTP> <PATH>" references nested request type "<Type>" with no **Nested:** sub-table.`

### Response class

Render per the `simple-command-response` skill template:

```python
class <Operation>Response(ConfiguredResponseSerializer):
    id: str

    @classmethod
    def from_domain(cls, <aggregate>: <Resource>) -> "<Operation>Response":
        return cls(id=<aggregate>.id)
```

Where `<aggregate>` = snake-case singular of `<Resource>` (Table 1 Resource name).

---

## Aggregator rendering

The per-aggregate `__init__.py` files are rendered as:

```python
# type: ignore
from .<module_1> import *
from .<module_2> import *
...

__all__ = (
    <module_1>.__all__
    + <module_2>.__all__
    + ...
)
```

Rules:

- The `from .<x> import *` lines come first, in lexicographic order, one per line.
- One blank line, then the `__all__` assignment. The right-hand side is a parenthesized concatenation of every per-module `__all__` joined by `+` (the parentheses are grouping syntax, not a tuple — since each per-module `__all__` is a list, the result is a list). Each `<module>.__all__` term is on its own line, indented four spaces.
- The file ends with a single trailing newline.
- If the candidate module list is empty, write a zero-byte file instead.
- The per-aggregate aggregator is the **only** star-aggregator the rest-api-spec emits at the serializers tree. The per-surface `__init__.py` stays empty (per `spec-core:naming-conventions`); the root `serializers/__init__.py` is owned by `@serializers-copier`. Cross-aggregate access is via the fully qualified path (`<pkg>.api.serializers.v1.cache_type.create`).

---

## Worked example

**Spec excerpt (`load.rest-api/spec.md`)**

```markdown
### Table 1: Resource Basics

| Field | Value |
| --- | --- |
| **Resource name** | Load |
| **Plural** | loads |
| **Router prefix** | /loads |
| **Surfaces** | v1 |

## Surface: v1

### Table 3: Command Endpoints

| HTTP | Path | Operation | Description | Domain Ref |
| --- | --- | --- | --- | --- |
| POST | `/` | create_load | Create a new load | `LoadCommands.create_load` |
| POST | `/{id}/close` | close | Close the load | `LoadCommands.close_load` |
| POST | `/{id}/corrections` | add_corrections | Add corrections for the load | `LoadCommands.add_corrections` |

### Table 5: Request Fields

**Endpoint:** `POST /`

| Field Name | Type | Validation |
| --- | --- | --- |
| name | `str` | Required |
| warehouse_id | `str` | Required; valid UUID |
| eta | `datetime \| None` | Optional |

**Endpoint:** `POST /{id}/close`

*No request body — id and tenant_id are sourced from path and auth.*

**Endpoint:** `POST /{id}/corrections`

| Field Name | Type | Validation |
| --- | --- | --- |
| corrections | `list[str]` | Required, non-empty list |
```

**Emitted modules** (assuming `<pkg>` = `cargo`, `<aggregate>` = `load`):

`api/serializers/v1/load/close.py`:

```python
from cargo.domain.load import Load

from ...configured_base_serializer import ConfiguredResponseSerializer

__all__ = [
    "CloseResponse",
]


class CloseResponse(ConfiguredResponseSerializer):
    id: str

    @classmethod
    def from_domain(cls, load: Load) -> "CloseResponse":
        return cls(id=load.id)
```

`api/serializers/v1/load/create_load.py`:

```python
from datetime import datetime

from cargo.domain.load import Load

from ...configured_base_serializer import ConfiguredRequestSerializer, ConfiguredResponseSerializer

__all__ = [
    "CreateLoadRequest",
    "CreateLoadResponse",
]


class CreateLoadRequest(ConfiguredRequestSerializer):
    name: str
    warehouse_id: str
    eta: datetime | None = None


class CreateLoadResponse(ConfiguredResponseSerializer):
    id: str

    @classmethod
    def from_domain(cls, load: Load) -> "CreateLoadResponse":
        return cls(id=load.id)
```

`api/serializers/v1/load/add_corrections.py`:

```python
from cargo.domain.load import Load

from ...configured_base_serializer import ConfiguredRequestSerializer, ConfiguredResponseSerializer

__all__ = [
    "AddCorrectionsRequest",
    "AddCorrectionsResponse",
]


class AddCorrectionsRequest(ConfiguredRequestSerializer):
    corrections: list[str]


class AddCorrectionsResponse(ConfiguredResponseSerializer):
    id: str

    @classmethod
    def from_domain(cls, load: Load) -> "AddCorrectionsResponse":
        return cls(id=load.id)
```

`api/serializers/v1/load/__init__.py` (after both query and command implementers have run for this aggregate):

```python
# type: ignore
from .add_corrections import *
from .close import *
from .create_load import *
from .find_load import *
from .find_loads import *

__all__ = (
    add_corrections.__all__
    + close.__all__
    + create_load.__all__
    + find_load.__all__
    + find_loads.__all__
)
```

### `to_domain()` example for a command with a domain-TypedDict parameter

Spec excerpt for resource `CacheType` (aggregate `cache_type`):

```markdown
### Table 3: Command Endpoints

| HTTP | Path | Operation | Description | Domain Ref |
| --- | --- | --- | --- | --- |
| POST | `/` | create | Create a new cache type | `CacheTypeCommands.create` |

### Table 5: Request Fields

**Endpoint:** `POST /`

| Field Name | Type | Validation |
| --- | --- | --- |
| code | `str` | Required |
| name | `str` | Required |
| lookups | `list[LookupArgumentData]` | Required, non-empty list |

**Nested:** `LookupArgumentData`

| Field Name | Type | Validation |
| --- | --- | --- |
| code | `str` | Required |
| name | `str` | Required |
| arguments | `list[ArgumentData]` | Required |
| response | `list[ResponseData]` | Required |

**Nested:** `ArgumentData`

| Field Name | Type | Validation |
| --- | --- | --- |
| name | `str` | Required |
| type | `str` | Required |

**Nested:** `ResponseData`

| Field Name | Type | Validation |
| --- | --- | --- |
| name | `str` | Required |
| type | `str` | Required |
```

Commands diagram declares `CacheTypeCommands.create(code: str, name: str, lookups: list[LookupArgumentData])`. Domain diagram marks `LookupArgumentData`, `ArgumentData`, `ResponseData` as `<<Domain TypedDict>>`. The agent emits:

`api/serializers/v1/cache_type/create.py`:

```python
from cargo.domain.cache_type import ArgumentData, CacheType, LookupArgumentData, ResponseData

from ...configured_base_serializer import ConfiguredRequestSerializer, ConfiguredResponseSerializer

__all__ = [
    "ArgumentDataSerializer",
    "ResponseDataSerializer",
    "LookupArgumentDataSerializer",
    "CreateRequest",
    "CreateResponse",
]


class ArgumentDataSerializer(ConfiguredRequestSerializer):
    name: str
    type: str

    def to_domain(self) -> ArgumentData:
        return {
            "name": self.name,
            "type": self.type,
        }


class ResponseDataSerializer(ConfiguredRequestSerializer):
    name: str
    type: str

    def to_domain(self) -> ResponseData:
        return {
            "name": self.name,
            "type": self.type,
        }


class LookupArgumentDataSerializer(ConfiguredRequestSerializer):
    code: str
    name: str
    arguments: list[ArgumentDataSerializer]
    response: list[ResponseDataSerializer]

    def to_domain(self) -> LookupArgumentData:
        return {
            "code": self.code,
            "name": self.name,
            "arguments": [item.to_domain() for item in self.arguments],
            "response": [item.to_domain() for item in self.response],
        }


class CreateRequest(ConfiguredRequestSerializer):
    code: str
    name: str
    lookups: list[LookupArgumentDataSerializer]


class CreateResponse(ConfiguredResponseSerializer):
    id: str

    @classmethod
    def from_domain(cls, cache_type: CacheType) -> "CreateResponse":
        return cls(id=cache_type.id)
```

Note: the top-level `CreateRequest` has no `to_domain()` — it is consumed field-by-field by the endpoint (`request.code`, `request.name`, and `[lookup.to_domain() for lookup in request.lookups]`). Every *nested* sub-serializer (`ArgumentDataSerializer`, `ResponseDataSerializer`, `LookupArgumentDataSerializer`) exposes `to_domain()`; here all three target domain TypedDicts, so all three use the dict-literal body form. A nested type whose stereotype is a value object would instead receive the `<Type>(...)` constructor body form.

---

## Error conditions — abort with explicit message and do not write

- `<locations_report_text>` is missing the `API Package` or `Containers` row.
- `<api_pkg>/serializers/` does not exist or `configured_base_serializer.py` is missing (scaffolder did not run).
- `<rest_api_spec_file>` does not exist.
- Spec Table 1 lacks `Resource name` or `Surfaces`.
- A surface listed in Table 1 has no `## Surface:` section, or vice versa.
- A surface has Table 3 rows but Table 5 is the empty placeholder, or the file is missing Table 5 entirely.
- A surface's Table 3 has a duplicate Operation, or a duplicate `(HTTP, Path)` pair, across its rows.
- A Table 3 row's `(http, path)` has no matching Table 5 sub-block.
- A nested PascalCase type referenced in a request Type column has no `**Nested:**` sub-table inside the same endpoint group.

In all error cases, write nothing and report the error message verbatim. Do not produce a partial run.
