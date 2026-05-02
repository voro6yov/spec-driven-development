---
name: resource-spec-template
description: Reference template for the Resource Basics table (Table 1) and the per-surface section convention of a REST API resource input spec. Load when authoring or reviewing the input spec for a REST API resource — covers the four required fields of Table 1, casing/format rules, derivation conventions, the `## Surface: <name>` section layout that scopes Tables 2–6, and worked examples.
user-invocable: false
disable-model-invocation: false
---

# Resource Spec Template — Resource Basics and Surface sections

## Purpose

Defines the canonical shape of **Table 1: Resource Basics** of a REST API resource input spec, plus the **`## Surface: <name>`** H2 section convention that scopes Tables 2 through 6. Every REST API resource spec begins with Table 1 and is followed by one or more Surface sections. Table 1 anchors naming, routing, and the surface inventory. Each Surface section anchors all per-endpoint detail (Tables 2–6) for a single URL surface (e.g., `v1`, `v2`, `internal`).

## Table 1 layout

| Field | Value |
| --- | --- |
| **Resource name** |  |
| **Plural** |  |
| **Router prefix** |  |
| **Surfaces** |  |

## Fields

### Resource name

- **Format:** `PascalCase`
- **Cardinality:** Singular noun — never plural, never a verb
- **Examples:** `ProfileType`, `File`, `InventoryItem`, `Order`
- **Counter-examples:** `profileType` (wrong case), `Files` (plural), `CreateFile` (verb)

### Plural

- **Format:** `kebab-case`
- **Pluralization rule:** Pluralize the **last word only** of the Resource name; lowercase every word; join with `-`
    - `ProfileType` → `profile-types`
    - `InventoryItem` → `inventory-items`
    - `File` → `files`
- **No leading slash.** The leading `/` belongs to Router prefix, not Plural.

### Router prefix

- **Format:** `/<plural>` — a leading slash followed by the Plural value verbatim
- **Derivation:** Always equal to `/` + Plural. Never deviates.
    - Plural `profile-types` → Router prefix `/profile-types`
    - Plural `files` → Router prefix `/files`
- **Note.** The Router prefix is the resource-level prefix. The full URL path of an endpoint is `/<surface>/<plural>/<endpoint-path>` — the surface segment (e.g., `/v1`, `/internal`) is owned by the version-router / internal-router and is not duplicated here.

### Surfaces

- **Format:** comma-separated list of surface names in canonical order (versioned surfaces first by numeric version, then non-versioned alphabetically — see `surface-markers` skill).
- **Default:** `v1` when the spec is freshly initialized.
- **Source of truth:** The set of surface markers (`%% <name>`) discovered across the commands and queries diagrams, parsed per the `surface-markers` skill. The `endpoint-tables-writer` updates this row when it discovers additional surfaces.
- **Examples:** `v1`; `v1, v2`; `v1, internal`; `v1, v2, admin, internal`.
- **Counter-examples:** `V1` (must be lowercase); `v1; v2` (semicolon — must be comma+space); `v1,v2` (missing space).

## Per-surface section layout

After Table 1, the spec contains **one `## Surface: <name>` H2 section per surface in the Surfaces list**, in the same canonical order. Each Surface section is self-contained and holds Tables 2 through 6 scoped to that surface:

```markdown
### Table 1: Resource Basics

| Field | Value |
| --- | --- |
| **Resource name** | <ResourceName> |
| **Plural** | <plural> |
| **Router prefix** | /<plural> |
| **Surfaces** | <surface_1>, <surface_2>, ... |

## Surface: <surface_1>

### Table 2: Query Endpoints
...

### Table 3: Command Endpoints
...

### Table 4: Response Fields
...

### Table 5: Request Fields
...

### Table 6: Parameter Mapping
...

## Surface: <surface_2>

### Table 2: Query Endpoints
...
```

### Surface section heading rules

- The H2 heading is exactly `## Surface: <name>` — `Surface:` (capital S, colon, single space) followed by the surface name verbatim from the Surfaces list.
- Surface names are lowercase and follow the `surface-markers` regex `[A-Za-z][A-Za-z0-9_-]*` (canonicalized to lowercase).
- One `## Surface:` heading per surface. Never repeat a surface name. Never split a surface across multiple `## Surface:` blocks.
- The order of `## Surface:` sections in the file matches the order of the Surfaces row in Table 1.

### What lives inside a Surface section

Tables 2 through 6 — and only those tables — live inside `## Surface:` sections. Their internal layout is governed by `endpoint-tables-template` (Tables 2/3) and `endpoint-io-template` (Tables 4/5/6). Empty surfaces (e.g., a surface with zero command endpoints) emit italic placeholders for the affected tables — see the per-table templates.

### What does NOT live inside a Surface section

- Table 1 itself.
- Any prose preamble or trailing notes that apply to the whole resource.

## Derivation summary

Given a Resource name, the rest of Table 1 is fully determined except for Surfaces:

```
Resource name = <PascalCase singular>
Plural        = lowercase(pluralize_last_word(split_words(Resource name))) joined by "-"
Router prefix = "/" + Plural
Surfaces      = canonical-order(union(commands_diagram_markers, queries_diagram_markers))
                (defaults to "v1" when no markers are present, per the surface-markers skill)
```

## Worked examples

**Example A — ProfileType (single surface, fresh init)**

```markdown
### Table 1: Resource Basics

| Field | Value |
| --- | --- |
| **Resource name** | ProfileType |
| **Plural** | profile-types |
| **Router prefix** | /profile-types |
| **Surfaces** | v1 |

## Surface: v1

### Table 2: Query Endpoints
...
```

**Example B — File (multi-surface)**

```markdown
### Table 1: Resource Basics

| Field | Value |
| --- | --- |
| **Resource name** | File |
| **Plural** | files |
| **Router prefix** | /files |
| **Surfaces** | v1, internal |

## Surface: v1

### Table 2: Query Endpoints
...

### Table 6: Parameter Mapping
...

## Surface: internal

### Table 2: Query Endpoints

*No query endpoints in this surface.*

### Table 3: Command Endpoints
...
```

## Validation checklist

### Table 1

- [ ] Resource name is PascalCase and singular
- [ ] Plural is kebab-case, lowercase, last word pluralized
- [ ] Router prefix equals `/` + Plural exactly
- [ ] Surfaces is a comma-separated lowercase list in canonical order (versioned by integer, then non-versioned alphabetically)

### Surface sections

- [ ] One `## Surface: <name>` H2 heading per surface listed in Table 1's Surfaces row
- [ ] H2 heading text is exactly `Surface: <name>` (capital S, colon, single space)
- [ ] Section order matches Surfaces row order
- [ ] Tables 2–6 live only inside `## Surface:` sections; Table 1 lives outside
- [ ] No surface heading is repeated and no surface listed in Table 1 is missing a section
