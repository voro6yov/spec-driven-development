---
name: conventions
description: "Umbrella catalog of the knowledge base's page-authoring conventions (concept, source, author, map) plus the cross-cutting relationship and kind rules. Each theme lives in a sibling folder's index.md. Load when AUTHORING or editing any wiki page, or when LINTING — the docs give the canonical authoring rule and the matching lint lens (what is canonical and must not be flagged, what /lint must enforce or auto-fix)."
when_to_use: "Consult before writing, editing, or linting any page in concepts/, sources/, authors/, or maps/. For authoring, open the theme for the page type you're writing, then load relationships/ and kinds/ as needed when writing a concept. For linting, read the Lint bullets of the relevant theme(s) — anything documented here as a convention is canonical and must not be flagged."
user-invocable: false
---

# Knowledge base authoring conventions (umbrella)

This skill is the **single source of truth** for what a well-formed wiki page looks like in this knowledge base — across all page types (`concepts/<kebab>.md`, `sources/<kebab>.md`, `authors/<kebab>.md`, `maps/<domain>.md`). It is a **path-resolution anchor**: it registers one catalog entry; the convention docs themselves are **supporting files** in sibling folders and are never auto-loaded — `/ingest`, `/lint`, and you Read them on demand.

`CLAUDE.md` holds the always-loaded **quick reference** (the page-type table, the kind registry values, the relationship vocabulary, frontmatter one-liners). This umbrella holds the **depth**: section-by-section page specs, worked examples, and the reciprocity mechanics. Where the two overlap, **CLAUDE.md owns the lists/values; this umbrella owns the how-to and examples.**

It serves two lenses from one catalog:

- **Authoring (primary).** Each theme doc is an imperative spec — the canonical rule, the exact page section/notation, a worked example, and the sanctioned variations.
- **Lint (suppression + enforcement lens).** Each convention carries a **Lint** bullet stating what `/lint` must treat as canonical (and not flag) and what it must actively repair. The `/lint` skill reads these so it enforces real conventions instead of stylistic noise.

## Resolution rule

Every theme named `<theme>` resolves to the **folder** `<theme>/` sibling to this file; the doc is always `<theme>/index.md`. A theme name with no matching folder is an **error** — report it; never skip it silently.

## How to use

- **Authoring a page:** detect the page type, open that type's theme (`concept/`, `source/`, `author/`, `map/`), and follow its section spec. While writing a concept, also load `relationships/` (to wire edges) and `kinds/` (to pick `kind`).
- **Linting:** read the **Lint** bullets of every theme the audited pages touch. If a pattern is documented here as canonical, do not flag it; where a Lint bullet says "auto-fix", repair it; otherwise surface it.

## Catalog

| Theme | Folder | Applies to |
|---|---|---|
| Concept pages | [concept/](concept/) | `concepts/` |
| Source pages | [source/](source/) | `sources/` |
| Author pages | [author/](author/) | `authors/` |
| Map pages | [map/](map/) | `maps/` |
| Relationships (typed, reciprocal) | [relationships/](relationships/) | `concepts/` (cross-cutting) |
| Concept kinds (open registry) | [kinds/](kinds/) | `concepts/` (cross-cutting) |
| Raw book folders | [raw-books/](raw-books/) | `raw/books/` |

## Provenance & maintenance

- These docs are the operational source of truth for authoring and linting wiki pages.
- When you discover a new authoring rule or a `/lint` false positive, update the relevant theme doc here — not the `/ingest` or `/lint` procedure. Keep examples concrete and grounded in real pages in this KB (e.g. `concepts/{{EXAMPLE_CONCEPT}}.md`).
- The catalog is **open**: add a theme by creating `<theme>/index.md` and a catalog row. Adding a concept `kind` is documented in [kinds/](kinds/) and registered in `CLAUDE.md`.
