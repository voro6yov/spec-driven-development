---
name: surface-markers
description: Parsing rules for surface markers in Mermaid application-service class diagrams. Load when reading a `<Resource>Commands` or `<Resource>Queries` diagram that may group methods under per-surface markers like `%% v1` or `%% internal`.
user-invocable: false
disable-model-invocation: false
---

# Surface Markers

## Purpose

A single REST API resource may expose its methods through more than one URL surface — for example, a public `v1` API and an `internal` service-to-service API. Both surfaces share the same `<Resource>Commands` / `<Resource>Queries` application-service class, so the diagram needs an in-line way to declare which surface each method belongs to.

Surface markers are Mermaid line comments inside the class body that act as group delimiters. Every method declared after a marker, up to the next marker (or the closing `}`), belongs to the surface — or **surfaces** — that marker names. A marker may list several surfaces (e.g. `%% v1, internal`), exposing each following method on every listed surface from a single declaration. The set of surfaces discovered across the commands and queries diagrams drives the per-surface section layout of the resource spec (`## Surface: <name>`).

## Marker syntax

A surface marker is a Mermaid line comment that names one or more surfaces, matching exactly:

```
^\s*%%\s+([A-Za-z][A-Za-z0-9_-]*(?:\s*,\s*[A-Za-z][A-Za-z0-9_-]*)*)\s*$
```

The captured group is a **comma-separated list** of one or more surface names. Split it on commas, trim surrounding whitespace from each token, normalize each to **lowercase**, and deduplicate while preserving first-seen order. The result is the marker's **surface set** — the set of surfaces every method beneath the marker is exposed on. A marker with a single name (no comma) yields a one-element set, exactly as before.

Examples that match:

| Line | Surface set |
| --- | --- |
| `%% v1` | `{v1}` |
| `  %%   internal  ` | `{internal}` |
| `%% admin-v2` | `{admin-v2}` |
| `%% V1` | `{v1}` |
| `%% v1, internal` | `{v1, internal}` |
| `%% v1 , Internal , admin` | `{v1, internal, admin}` |

Examples that do **not** match (treated as regular comments and ignored — they are stripped during Mermaid parsing):

- `%%v1` — no whitespace between `%%` and the name
- `%% v1 (public)` — extra text after the name
- `%% TODO: rename this method` — extra words
- `%% surface: v1` — name token is `surface:`, which fails the `[A-Za-z][A-Za-z0-9_-]*` shape

The strict regex prevents stray comments from accidentally creating phantom surfaces. If the user wants a surface called `v1`, the line must be exactly `%% v1` (with optional surrounding whitespace). To expose the following methods on several surfaces at once, separate the names with commas — `%% v1, internal`. A trailing or empty entry (`%% v1,`) does not match and is ignored as a regular comment.

## Scoping

Markers are scoped **per class body**:

- Only markers that appear *inside* a `class <Name> { ... }` block apply.
- A marker outside a class body (between `classDiagram` and the first class block, or in the diagram preamble) is treated as a regular comment and ignored.
- Each class body starts with the **default surface set** `{v1}` as its current surface set. The first matching marker line replaces it with that marker's surface set; subsequent matching marker lines replace it again; and so on until the closing `}`. Replacement is wholesale — a marker never unions with the previous set.
- Multiple classes in the same diagram each carry their own current-surface-set state.

## Default surface

If a class body contains methods declared **before** any marker, or contains no markers at all, those methods belong to the default surface set **`{v1}`** (lowercase, no prefix). This makes pre-existing diagrams without surface markers continue to generate valid single-surface specs.

`v1` is also the surface name written into Table 1 of a freshly initialized resource spec. The `endpoint-tables-writer` updates Table 1's Surfaces row when it discovers additional surfaces in the diagrams.

## Method-to-surface mapping

After parsing, each public method declaration is associated with **one or more** surface names — every surface in the current surface set when the declaration is read. When building the per-class `{surface_name -> [methods]}` map, append the method to **each** surface in its set; a method under `%% v1, internal` therefore appears in both the `v1` and the `internal` lists from a single declaration. Consumers (writer agents) then emit one row per `(surface, method)` pair.

Prefer a multi-name marker over re-declaring a method. Declaring the same method twice (under two single-name markers) also lands it on both surfaces — the parser does not deduplicate — but the **same diagram also feeds the application layer**, where a repeated declaration becomes a redundant duplicate method. The comma-list marker is a single declaration and stays application-safe; it is the canonical way to put one method on multiple surfaces.

Ordering of methods within a surface is the order of declaration in the class body. A method shared across surfaces takes its position in each surface's list from that single declaration point.

## Surface set and ordering

The **surface set** for a resource is the union of surface names discovered across the commands diagram and the queries diagram. A surface that appears in only one of the two diagrams is still part of the set; it just has zero methods on the other side.

Render surfaces in this canonical order everywhere — the `Surfaces` row in Table 1, the sequence of `## Surface: <name>` sections, and any per-surface report counts:

1. **Versioned surfaces first**, sorted by numeric version. A surface name matches the versioned pattern when it equals `^v(\d+)$` (e.g., `v1`, `v2`, `v10`). Sort by the integer captured after `v`, ascending.
2. **Non-versioned surfaces afterwards**, sorted lexicographically (e.g., `admin`, `internal`).

Examples:

- `{v1}` → `v1`
- `{v1, v2}` → `v1, v2`
- `{v1, internal}` → `v1, internal`
- `{v2, v1, internal, admin}` → `v1, v2, admin, internal`

## Worked example

Input — `FileCommands` diagram:

```mermaid
classDiagram
class FileCommands {
    %% v1, internal
    +create(name: str, tenant_id: str) FileInfo

    %% v1
    +update_details(id: str, name: str, tenant_id: str) FileInfo

    %% internal
    +bulk_reprocess(ids: list[str], tenant_id: str) BulkResult
}
```

Parsed surface map for `FileCommands`:

| Surface | Methods |
| --- | --- |
| `v1` | `create`, `update_details` |
| `internal` | `create`, `bulk_reprocess` |

`create` sits under the `%% v1, internal` marker, so its single declaration lands it in **both** the `v1` and `internal` lists. `update_details` (under `%% v1`) is `v1`-only; `bulk_reprocess` (under `%% internal`) is `internal`-only.

Input — `FileQueries` diagram (no markers):

```mermaid
classDiagram
class FileQueries {
    +find_file(id: str, tenant_id: str) FileInfo
    +find_files(filtering: FileFiltering, pagination: Pagination, tenant_id: str) FileListResult
}
```

Parsed surface map for `FileQueries` (default surface fallback applies):

| Surface | Methods |
| --- | --- |
| `v1` | `find_file`, `find_files` |

Surface set (union): `{v1, internal}`. Canonical order: `v1, internal`. Table 1's `Surfaces` row: `v1, internal`. The resource spec then emits two `## Surface:` sections — `## Surface: v1` (both query methods, plus the `create` and `update_details` commands) and `## Surface: internal` (no query endpoints, the `create` and `bulk_reprocess` commands). `create` is emitted as an endpoint in **both** surfaces — `POST /v1/files` and `POST /internal/files` — from its one declaration; each surface's router supplies its own prefix, so the two are distinct routes with no collision.
