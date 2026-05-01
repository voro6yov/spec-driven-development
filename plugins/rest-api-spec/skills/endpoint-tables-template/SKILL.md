---
name: endpoint-tables-template
description: Reference template for the Query Endpoints and Command Endpoints tables (Tables 2 and 3) of a REST API resource input spec. Load when authoring or reviewing the endpoint inventory of a resource — covers column shape, path conventions, operation naming, HTTP verb mapping, Domain Ref traceability, special endpoint shapes (binary content, sub-resources, actions, bulk), and worked examples.
user-invocable: false
---

# Endpoint Tables Template — Query and Command Endpoints

## Purpose

Defines the canonical shape of **Table 2: Query Endpoints** and **Table 3: Command Endpoints** of a REST API resource input spec. Together these tables enumerate every HTTP endpoint the resource exposes and bind each one to a method on its application service (`<Resource>Queries` / `<Resource>Commands`). Status codes, request/response field details, and parameter mapping are the concern of later sections — these two tables are the endpoint *inventory*.

Both tables share the same five-column shape:

`HTTP | Path | Operation | Description | Domain Ref`

---

## Table 2: Query Endpoints

### Shape

| HTTP | Path | Operation | Description | Domain Ref |
| --- | --- | --- | --- | --- |
| GET | `/{id}` | find_<resource> | Retrieve a single <resource> by id | `<Resource>Queries.find_<resource>` |
| GET | `/` | find_<resources> | Retrieve a paginated list of <resources> | `<Resource>Queries.find_<resources>` |

### Column rules

- **HTTP** — Always `GET` for query endpoints. Any non-GET row belongs in Table 3.
- **Path** — See [Path conventions](#path-conventions) below. Wrap in backticks; do not escape braces (`/{id}`, not `/\{id\}`).
- **Operation** — `find_<resource>` (singular fetch) or `find_<resources>` (collection / projection). Snake case. The operation name *is* the method name on `<Resource>Queries`.
- **Description** — One-line human description. State *what* is returned and any notable variant (e.g., "with optional heavy fields", "returns raw bytes for streaming response").
- **Domain Ref** — Required. Format: `<Resource>Queries.<operation>`. Mirrors the Operation column verbatim after the dot.

### Operation naming

- **Singular fetch by id:** `find_<resource>` — e.g., `find_file`, `find_document`.
- **Collection (paginated):** `find_<resources>` — e.g., `find_files`, `find_documents`.
- **Sub-resource / projection:** `find_<resource>_<segment>` — e.g., `find_file_content`, `find_file_redacted_content`.
- Always `find_*` for query endpoints. Do not use `get_*` — that prefix is reserved for serializer class names.

---

## Table 3: Command Endpoints

### Shape

| HTTP | Path | Operation | Description | Domain Ref |
| --- | --- | --- | --- | --- |
| POST | `/` | create | Create a new <resource> | `<Resource>Commands.create` |
| POST | `/{id}/<verb>` | <verb> | <action description> | `<Resource>Commands.<verb>` |

### Column rules

- **HTTP** — One of `POST`, `PUT`, `PATCH`, `DELETE`. See [HTTP verb mapping](#http-verb-mapping).
- **Path** — See [Path conventions](#path-conventions). Wrap in backticks; do not escape braces.
- **Operation** — Mirrors the method name on `<Resource>Commands`. Snake case. Domain-driven verbs are preferred over generic REST verbs (e.g., `retry`, `skip`, `assign_document_types`, not `update`).
- **Description** — One-line human description. State the business effect, not the HTTP mechanic.
- **Domain Ref** — **Required for every row.** Format: `<AggregateRoot>Commands.<snake_case_method>`. Every command endpoint must trace to an existing application-service method; if the method does not exist yet, the row is not ready.

### HTTP verb mapping

| Verb | Use for | Path shape |
| --- | --- | --- |
| `POST` | Create at collection root, or named action on an instance/collection | `/`, `/{id}/<verb>`, `/bulk-<verb>` |
| `PUT` | Full replacement of an existing resource | `/{id}` |
| `PATCH` | Partial update of an existing resource | `/{id}` |
| `DELETE` | Remove an existing resource | `/{id}` |

`POST` is the default for action endpoints with domain-specific verbs. Reserve `PUT`/`PATCH`/`DELETE` for canonical CRUD.

---

## Path conventions

Paths are relative to the resource's Router prefix (Table 1). A leading `/` is required on every row.

### Canonical shapes

| Shape | When | Example |
| --- | --- | --- |
| `/` | Collection root (paginated list, create, bulk action) | `GET /`, `POST /`, `POST /bulk-retry` |
| `/{id}` | Single instance by id (read, replace, patch, delete) | `GET /{id}`, `PUT /{id}`, `DELETE /{id}` |
| `/{id}/<segment>` | Sub-resource or projection of a single instance | `GET /{id}/content`, `GET /{id}/redacted-content` |
| `/{id}/<verb>` | Named action on a single instance | `POST /{id}/retry`, `POST /{id}/skip` |
| `/bulk-<verb>` | Collection-level action that batches per-item | `POST /bulk-retry`, `POST /bulk-skip` |

### Rules

- **Path id placeholder is always `{id}`** — singular, lowercase, in backticks, never escaped (`/{id}`, not `/\{id\}` and not `/{fileId}`).
- **Sub-resource segments are kebab-case nouns** — `redacted-content`, not `redactedContent` or `redacted_content`.
- **Action verbs are snake-case verbs** — `assign_document_types`, mirroring the domain method. Path verbs that mirror methods stay snake-case; standalone path nouns stay kebab-case.
- **No trailing slash** on action or sub-resource paths.
- **No version segment** — versioning is handled by the router prefix, not the path column here.

### Special shapes

- **Binary content endpoints.** `GET /{id}/<segment>` returning raw bytes. The Description column should call out the streaming response shape, e.g., "returns raw bytes for streaming response". Operation is `find_<resource>_<segment>`.
- **Sub-resource projections.** `GET /{id}/<segment>` returning a serialized projection of related data. Treat the segment as a noun (`/{id}/content`, `/{id}/permissions`).
- **Action endpoints.** `POST /{id}/<verb>`. The verb is the domain command method name; Domain Ref points to the same name on `<Resource>Commands`.
- **Bulk endpoints.** `POST /bulk-<verb>`. The action applies to a list of ids (or a filter) supplied in the request body. Operation is `bulk_<verb>`; Domain Ref is `<Resource>Commands.bulk_<verb>`.

---

## Worked examples

### Example A — File

**Table 2: Query Endpoints**

| HTTP | Path | Operation | Description | Domain Ref |
| --- | --- | --- | --- | --- |
| GET | `/{id}` | find_file | Retrieve a single File with optional heavy fields (Wish List pattern) | `FileQueries.find_file` |
| GET | `/` | find_files | Retrieve a paginated list of files for a profile with optional filtering | `FileQueries.find_files` |
| GET | `/{id}/content` | find_file_content | Download binary content of a file (returns raw bytes for streaming response) | `FileQueries.find_file_content` |
| GET | `/{id}/redacted-content` | find_file_redacted_content | Download binary content of a file's redacted version (returns raw bytes for streaming response) | `FileQueries.find_file_redacted_content` |

**Table 3: Command Endpoints**

| HTTP | Path | Operation | Description | Domain Ref |
| --- | --- | --- | --- | --- |
| POST | `/{id}/retry` | retry | Retry processing of a failed file from the failed stage | `FileCommands.retry_processing` |
| POST | `/{id}/skip` | skip | Mark a file as skipped, excluding it from profile completion | `FileCommands.skip` |
| POST | `/{id}/document-types` | assign_document_types | Manually assign or correct document types for a file | `FileCommands.assign_document_types` |

### Example B — Document

**Table 2: Query Endpoints**

| HTTP | Path | Operation | Description | Domain Ref |
| --- | --- | --- | --- | --- |
| GET | `/{id}` | find_document | Retrieve a single document by id | `DocumentQueries.find_document` |
| GET | `/` | find_documents | Retrieve a paginated list of documents for a profile with optional filtering | `DocumentQueries.find_documents` |

**Table 3: Command Endpoints**

| HTTP | Path | Operation | Description | Domain Ref |
| --- | --- | --- | --- | --- |
| POST | `/{id}/corrections` | add_corrections | Apply user corrections to extracted document data | `DocumentCommands.add_corrections` |
| POST | `/{id}/retry` | retry | Retry processing of a failed document | `DocumentCommands.retry` |
| POST | `/{id}/skip` | skip | Mark document as skipped, excluding from profile completion | `DocumentCommands.skip` |

---

## Validation checklist

### Table 2 — Query Endpoints

- [ ] Every row has `GET` in the HTTP column
- [ ] Every Path is wrapped in backticks, has a leading `/`, and uses `{id}` (not `{fooId}`) for the instance placeholder
- [ ] Sub-resource segments are kebab-case nouns
- [ ] Operation column uses `find_<resource>` / `find_<resources>` / `find_<resource>_<segment>` (snake case)
- [ ] Description states what is returned and any notable variant (heavy fields, streaming bytes, etc.)
- [ ] Domain Ref equals `<Resource>Queries.<operation>` for every row

### Table 3 — Command Endpoints

- [ ] HTTP column is one of `POST`, `PUT`, `PATCH`, `DELETE`
- [ ] `PUT` / `PATCH` / `DELETE` rows use the `/{id}` shape; non-CRUD actions use `POST`
- [ ] Action paths follow `/{id}/<verb>`, bulk paths follow `/bulk-<verb>`, create uses `POST /`
- [ ] Operation mirrors a snake-case method name on `<Resource>Commands` (domain-driven verbs preferred over generic REST verbs)
- [ ] Domain Ref is present on **every** row, formatted `<AggregateRoot>Commands.<snake_case_method>`
- [ ] Description states the business effect, not the HTTP mechanic
