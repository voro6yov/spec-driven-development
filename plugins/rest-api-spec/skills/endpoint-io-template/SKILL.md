---
name: endpoint-io-template
description: Reference template for the Response Fields, Request Fields, and Parameter Mapping tables (Tables 4, 5, 6) of a REST API resource input spec — covers the shape of each table, type and source/validation conventions, nested type sub-tables, query-parameter sub-blocks under Table 4, italic placeholders for binary or empty bodies, the Wish List `(includable)` annotation, and the canonical Source vocabulary for parameter mapping.
when_to_use: Load when authoring or reviewing the per-endpoint I/O of a REST API resource input spec — populating Table 4 (Response Fields), Table 5 (Request Fields), or Table 6 (Parameter Mapping); validating the response/request shape of a query or command endpoint; or normalizing legacy Parameter Mapping tables.
user-invocable: false
paths:
  - "**/*resource*spec*.md"
  - "**/*resource*.md"
  - "**/REST API*Resource*.md"
  - "**/rest-api/**/*.md"
---

# Endpoint I/O Template — Response Fields, Request Fields, and Parameter Mapping

## Purpose

Defines the canonical shape of **Table 4: Response Fields**, **Table 5: Request Fields**, and **Table 6: Parameter Mapping** of a REST API resource input spec. Together these three tables specify, for every endpoint enumerated in Tables 2 and 3 of the enclosing Surface section, exactly what JSON it accepts, what JSON it returns, and how each field of the underlying application-service method is sourced from the HTTP request.

The three tables are filled together because they share the same per-endpoint dispatch:

- Table 4 is filled per **query** endpoint (Table 2). It describes the response body and any query-string inputs.
- Table 5 is filled per **command** endpoint (Table 3). It describes the request body.
- Table 6 is filled per **endpoint** that calls into the application service (both command and query). It maps each application-service method parameter to its HTTP source.

Each table is a **per-endpoint group** — repeat the sub-table once per endpoint, headed by an `**Endpoint:** <HTTP> <PATH>` line that matches a row in the enclosing Surface section's Table 2 or Table 3 verbatim. An optional ` (operation_name)` may follow the path to ease cross-referencing with Table 2/3.

## Per-surface scoping

Tables 4, 5, and 6 always live inside a `## Surface: <name>` H2 section (see `resource-spec-template`). A resource with N surfaces has N copies of each of Tables 4, 5, and 6 — one per surface — each describing only the endpoints exposed on that surface (i.e., the rows of that surface's Tables 2 and 3).

When a surface has zero query endpoints (its Table 2 is the `*No query endpoints in this surface.*` placeholder), its Table 4 is replaced with the placeholder line:

```
### Table 4: Response Fields

*No response fields in this surface — no query endpoints.*
```

When a surface has zero command endpoints (its Table 3 is the `*No command endpoints in this surface.*` placeholder), its Table 5 is replaced with:

```
### Table 5: Request Fields

*No request fields in this surface — no command endpoints.*
```

When a surface has both Tables 2 and 3 empty, its Table 6 is replaced with:

```
### Table 6: Parameter Mapping

*No parameter mapping in this surface — no endpoints.*
```

The italic line is the entire content of the affected table — never mix the placeholder with a real sub-block.

---

## Table 4: Response Fields

Filled once per query endpoint.

### Shape

```
**Endpoint:** GET <path>

| Field Name | Type | Source |
| --- | --- | --- |
| <field> | <type> | <DTO["key"]> |

**Nested:** <NestedTypeName>          ← optional, see Nested types

| Field Name | Type | Source |
| --- | --- | --- |

**Query Parameters:** GET <path>      ← optional, see Query parameters block

| Param Name | Type | Default | Description |
| --- | --- | --- | --- |
```

### Column rules

- **Field Name** — Snake-case JSON field name. For a list-shaped field, the field is the list itself (e.g., `files`, `documents`); per-item fields go in a separate **Nested:** sub-table.
- **Type** — Python type syntax in backticks. See [Type column rules](#type-column-rules).
- **Source** — DTO subscript form `TypedDict["key"]` referencing the return type of the corresponding `<Resource>Queries` method (e.g., `FileInfo["id"]`, `DocumentListResult["documents"]`). The subscript form is required: it makes the binding from response field to application-layer DTO mechanical and reviewable. The only allowed trailing annotation is `(includable)` — see [Wish List annotation](#wish-list-annotation).

### Nested types

When the Type column references a custom PascalCase type (e.g., `list[BriefFileInfo]`, `IndividualData | LegalEntityData`, `Reference | None`), declare each such type in a sibling **Nested:** sub-table directly below the parent endpoint:

```
**Nested:** BriefFileInfo

| Field Name | Type | Source |
| --- | --- | --- |
| id | `str` | `BriefFileInfo["id"]` |
```

Rules:

- One sub-table per nested type per endpoint group.
- The **Nested:** sub-table uses the same three columns as the parent.
- The Source column references the nested DTO's own subscript (`BriefFileInfo["id"]`), not a path through the parent.
- If the same nested type appears under multiple endpoints, repeat the sub-table — sub-tables are scoped per endpoint group, not deduplicated across the spec.

### Query parameters block

For GET endpoints that accept query-string inputs (filters, pagination, the `include` parameter for the Wish List pattern, etc.), append a **Query Parameters:** sub-block immediately after the response field table (and after any Nested sub-tables for that endpoint):

```
**Query Parameters:** GET <path>

| Param Name | Type | Default | Description |
| --- | --- | --- | --- |
| profile_id | `str` | — | Required. UUID of the profile to retrieve files for |
| limit | `int \| None` | `None` | Pagination limit (defaults to `20` from settings) |
```

Rules:

- **Param Name** — snake-case, matches the FastAPI handler's argument name verbatim.
- **Type** — same rules as Table 4 / Table 5.
- **Default** — `—` for required params; otherwise the literal default (`None`, `0`, `"asc"`, …) in backticks. If the default is filled later from settings, state `None` here and call it out in the Description.
- **Description** — One line. Lead with `Required.` for required params; for optional params describe purpose and any downstream defaulting.

When an endpoint has **no** query parameters, replace the table with a single italic line so the absence is intentional and reviewable:

```
**Query Parameters:** GET <path>

*No query parameters — tenant_id inherited from auth context.*
```

### Wish List annotation

For the Wish List pattern (heavy fields surfaced via an `include` query param), mark each optional heavy field with a trailing `(includable)` annotation in the Source column:

```
| preparation_result | `PreparationResult \| None` | `FileInfo["preparation_result"]` (includable) |
```

The matching `include` query param must appear in the Query Parameters block:

```
| include | `list[str] \| None` | `None` | Optional list of heavy fields to include: `preparation_result`, `text`, `classification_result` (Wish List pattern) |
```

`(includable)` is the **only** trailing annotation permitted in the Source column. Streaming or binary semantics are conveyed by the [Binary endpoint placeholder](#italic-placeholder-rules), not by an inline note.

### Italic placeholder rules

Italic single-line placeholders replace a sub-table when the table would otherwise be empty. They make the absence explicit instead of implicit.

- **Binary response.** When a query endpoint returns raw bytes, replace the response-field table with:
  ```
  *Binary response* — returns raw `bytes` (`application/octet-stream`). No JSON response body.
  ```
- **No query parameters.** See above.
- **No request body** (Table 5). See [Table 5](#table-5-request-fields).

The italic line must be the entire content of that sub-section — never mix italic placeholder with a real table.

---

## Table 5: Request Fields

Filled once per command endpoint.

### Shape

```
**Endpoint:** <HTTP> <path>

| Field Name | Type | Validation |
| --- | --- | --- |
| <field> | <type> | <validation> |

**Nested:** <NestedTypeName>          ← optional

| Field Name | Type | Validation |
| --- | --- | --- |
```

### Column rules

- **Field Name** — Snake-case JSON field name on the request body.
- **Type** — Python type syntax in backticks. Same rules as Table 4. Custom request types (e.g., `DocumentTypeRequest`, `IndividualData`) are declared in a **Nested:** sub-table.
- **Validation** — One line. Must satisfy:
    - **Required vs optional is explicit.** Every row begins with `Required` or `Optional` (alternatively, `Required;` followed by further constraints, or a `None` default in the type column with `Optional` in Validation).
    - **Lists state cardinality.** Any `list[T]` field must call out non-empty / min-items where it matters (e.g., `Required, non-empty list, …`).
    - Domain-rule references are permitted but not required (e.g., `must match document subject kind`, `validated against ExtractionSchema`).

### Empty-body placeholder

When a command endpoint takes no request body (typical for `POST /{id}/<verb>` action endpoints whose only inputs are the path id and auth context), replace the table with:

```
*No request body — uses path parameter only.*
```

Variants are allowed when the wording is more accurate (e.g., `*No request body — id and tenant_id are sourced from path and auth.*`), but the line must remain a single italic line.

### Nested types

Same rules as Table 4 nested types, except the third column is **Validation** instead of Source. One sub-table per nested type, scoped per endpoint group.

---

## Table 6: Parameter Mapping

Filled once per endpoint that calls into the application service — both command (Table 3) and query (Table 2). Table 6 is what proves every parameter of the underlying `Commands` / `Queries` method is sourced and what proves no client input is silently ignored.

### Shape (canonical 2-column)

```
**Endpoint:** <HTTP> <path> (<operation>)

| Command Parameter | Request Field / Path Param |
| --- | --- |
| <param> | <source> |
```

For query endpoints, the left column is named `Query Parameter` instead of `Command Parameter`:

```
**Endpoint:** GET <path> (<operation>)

| Query Parameter | Source |
| --- | --- |
| <param> | <source> |
```

> **Column-count rule.** Use **2 columns**. Some legacy specs render a 3-column variant with an empty trailing column — this is an accidental copy-paste artifact and should be normalized to 2 columns on next edit.

### Canonical Source vocabulary

The right-hand column must use one of the following forms:

| Source form | When | Examples |
| --- | --- | --- |
| `Path param {id}` (or `Path: {id}`) | Value sourced from a path placeholder | `Path param {id}`, `Path: {id}` |
| `Auth context` | Value sourced from the authenticated principal (e.g., `tenant_id`) and never accepted from request body or query | `Auth context` |
| `Request body \`<field>\`` (or `Request body (<fields>)`) | Single field on the JSON request body, or a tuple of body fields composed into a domain object | `Request body \`document_types\``, `Request body (kind, entity)` |
| `Query param \`<name>\`` | Direct pass-through of a single query string argument | `Query param \`include\``, `Query param \`profile_id\`` |
| `Constructed from query params \`<a>\`, \`<b>\` → <Type>` | Composite value built from multiple query params, optionally with settings defaults | `Constructed from query params \`status\`, \`name\` → FileFiltering`, `Constructed from query params \`offset\`, \`limit\` → Pagination (defaults from settings if None)` |

Rules:

- The Source column must match a row's underlying provenance exactly — never write "request" or "param" without naming which.
- Every parameter of the application-service method (as enumerated in the Domain Ref method signature) must appear as a row. Missing rows mean the mapping is incomplete.
- Conversely, every Path param in the path and every Field in Table 5 / Query Parameter in Table 4 should be referenced from at least one row, otherwise the input is dead.
- `Auth context` is the only acceptable provenance for `tenant_id` and any other principal-derived field. Do not accept these from body or query.

---

## Type column rules

Shared by Table 4 (Type), Table 4 Query Parameters (Type), Table 5 (Type), and any nested sub-tables.

- **Backticked Python types.** Bare Python type expressions wrapped in backticks: `` `str` ``, `` `int` ``, `` `datetime` ``, `` `list[BriefFileInfo]` ``, `` `dict[str, str]` ``.
- **Optional via `T | None`.** Use the union syntax `` `T \| None` `` (the pipe must be escaped as `\|` inside markdown table cells). Do **not** use `Optional[T]`.
- **Datetime is `datetime`, not `str`.** When the underlying source is a `datetime` value, the Type column says `` `datetime` `` even though JSON serialization produces a string. Document any deliberate deviation explicitly in the Description / Source.
- **Literal for closed enums.** Closed-set string fields use `` `Literal["A", "B"]` ``, not `` `str` `` (e.g., `` `Literal["Individual", "LegalEntity"]` `` for a discriminator field).
- **Custom classes are referenced by bare PascalCase name.** `BriefFileInfo`, `Reference`, `IndividualData` — declare them as **Nested:** sub-tables. Do not import-qualify (`schemas.BriefFileInfo`).

---

## Worked examples

Two condensed end-to-end examples — File and Document — covering responses with optional heavy fields, list endpoints with nested types, binary content, command actions with and without bodies, and parameter mapping variants — are kept in the sibling [`examples.md`](./examples.md). Load that file when a worked reference is needed; the rules in this `SKILL.md` are normative.

---

## Validation checklist

### Per-surface placement

- [ ] Tables 4, 5, and 6 appear inside a `## Surface: <name>` H2 section, not at the top level
- [ ] Each `**Endpoint:**` header matches a row of Table 2 or Table 3 within the *same* enclosing Surface section
- [ ] Surfaces with no query endpoints use `*No response fields in this surface — no query endpoints.*` for Table 4
- [ ] Surfaces with no command endpoints use `*No request fields in this surface — no command endpoints.*` for Table 5
- [ ] Surfaces with no endpoints at all use `*No parameter mapping in this surface — no endpoints.*` for Table 6

### Table 4 — Response Fields

- [ ] One sub-table per query endpoint, headed by `**Endpoint:** GET <path>` matching Table 2 verbatim
- [ ] Type column uses backticked Python types, `T \| None` for optional, `datetime` (not `str`) for datetimes, `Literal[...]` for closed enums
- [ ] Source column uses `TypedDict["key"]` form referencing the Queries method return type
- [ ] Every custom PascalCase type in a Type column has a `**Nested:** <Type>` sub-table directly below
- [ ] Every GET endpoint has a `**Query Parameters:**` sub-block (a real table or the italic `*No query parameters …*` line)
- [ ] Wish List heavy fields are marked `(includable)` in Source and accompanied by an `include` query param
- [ ] Binary endpoints use `*Binary response* — returns raw bytes …` instead of a response-field table

### Table 5 — Request Fields

- [ ] One sub-table per command endpoint, headed by `**Endpoint:** <HTTP> <path>` matching Table 3 verbatim
- [ ] Type column follows the same rules as Table 4
- [ ] Validation column starts with `Required` or `Optional` for every row
- [ ] List-typed fields call out non-empty / cardinality where it matters
- [ ] Custom request types are declared in `**Nested:**` sub-tables (Field Name / Type / Validation)
- [ ] Endpoints with no body use `*No request body — …*` instead of an empty table

### Table 6 — Parameter Mapping

- [ ] One sub-table per endpoint that calls into the application service (both query and command)
- [ ] Two columns exactly — no trailing empty third column
- [ ] Left column is `Command Parameter` for command endpoints and `Query Parameter` for query endpoints
- [ ] Right-column source values are drawn from the canonical vocabulary: `Path param {id}` / `Auth context` / `Request body \`<field>\`` / `Query param \`<name>\`` / `Constructed from query params … → <Type>`
- [ ] `tenant_id` (and any other principal-derived field) is sourced from `Auth context`, never from body or query
- [ ] Every parameter of the corresponding Domain Ref method appears as a row
- [ ] Every Path param, Table 5 field, and Table 4 query parameter is referenced from at least one row
