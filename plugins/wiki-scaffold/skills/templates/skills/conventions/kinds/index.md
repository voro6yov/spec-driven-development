---
name: kinds
description: The open registry of concept kinds — how to pick a kind, how to choose an existing one vs propose a new one, and how to extend the registry (authoring + lint).
user-invocable: false
---

# Concept kinds

**Applies to:** `concepts/` (cross-cutting)

> Every concept carries a `kind` — what *sort* of thing it is. Kinds are frontmatter **values, never folders**, so the set extends freely without restructuring. The canonical list of valid values for this wiki lives in `CLAUDE.md`; this doc is how to **choose** among them and how to **add** a new one.

## Conventions

### Pick the kind by what the concept *is*

- **Rule:** Assign exactly one `kind`, drawn from the registry in `CLAUDE.md`. Read that registry's one-line definition for each value and pick the one matching what the concept fundamentally *is* — not merely what it's about. If two seem to fit, prefer the more specific; if none fits cleanly, don't force it — propose a new kind (see below). The registry is the source of truth for *valid values*; this doc only governs *how to choose*.
- **Lint:** flag a `kind` value not in the `CLAUDE.md` registry — either recategorize to an existing kind or (if genuinely new) propose a registry addition.

### Extending the registry

- **Rule:** When a concept fits none of the kinds cleanly, **propose a new kind in the `/ingest` report** rather than forcing a bad fit. Once accepted, add a row (value + one-line definition) to the registry in `CLAUDE.md`. The registry is **open**, and kinds are values rather than folders, so adding one never restructures anything — nothing moves.
- **Lint:** treat any kind present in the `CLAUDE.md` registry as canonical, including ones added after this doc was written — the registry, not this doc, is the source of truth for *valid values*.

## Pitfalls

- **Forcing a fit.** Tagging a concept with the nearest available kind because the registry lacks the right one. Propose the new kind instead.
- **Two homes for the list.** The valid values live in `CLAUDE.md`; keep this doc to *how to choose*, not a second copy of the list. If the two ever disagree, `CLAUDE.md` wins.
- **`technology` vs `source`.** A tool you only *reference* (you read its docs) is often better captured as a `source`/`doc`; reserve a `technology`-style concept kind for tools whose design ideas you actually wire into the graph.
