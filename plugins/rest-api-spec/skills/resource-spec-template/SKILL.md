---
name: resource-spec-template
description: Reference template for the Resource Basics table (Table 1) of a REST API resource input spec. Load when authoring or reviewing the input spec for a REST API resource — covers the four required fields, casing/format rules, derivation conventions, and worked examples.
user-invocable: false
disable-model-invocation: false
---

# Resource Spec Template — Resource Basics

## Purpose

Defines the canonical shape of **Table 1: Resource Basics** of a REST API resource input spec. Every REST API resource spec begins with this table. It anchors naming, routing, and versioning for every downstream artifact (serializers, endpoints, router registration).

## Table

| Field | Value |
| --- | --- |
| **Resource name** |  |
| **Plural** |  |
| **Router prefix** |  |
| **API version** |  |

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

### API version

- **Format:** `v<positive integer>` (regex: `v[1-9]\d*`)
- **Default:** `v1` when unspecified
- **Examples:** `v1`, `v2`, `v3`
- **Counter-examples:** `1`, `V1`, `v0`, `v1.0`, `v2-beta`

## Derivation summary

Given a Resource name, the rest of Table 1 is fully determined except for API version:

```
Resource name = <PascalCase singular>
Plural        = lowercase(pluralize_last_word(split_words(Resource name))) joined by "-"
Router prefix = "/" + Plural
API version   = v<int>   (default v1)
```

## Worked examples

**Example A — ProfileType**

| Field | Value |
| --- | --- |
| **Resource name** | ProfileType |
| **Plural** | profile-types |
| **Router prefix** | /profile-types |
| **API version** | v1 |

**Example B — File**

| Field | Value |
| --- | --- |
| **Resource name** | File |
| **Plural** | files |
| **Router prefix** | /files |
| **API version** | v1 |

## Validation checklist

- [ ] Resource name is PascalCase and singular
- [ ] Plural is kebab-case, lowercase, last word pluralized
- [ ] Router prefix equals `/` + Plural exactly
- [ ] API version matches `v<positive int>` (default `v1`)
