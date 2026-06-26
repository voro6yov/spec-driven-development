---
name: map
description: How to author a map page — a curated, opinionated per-domain entry point (not an exhaustive catalog). Sections, the "load-bearing concepts only" rule, and when a map should exist (authoring + lint).
user-invocable: false
---

# Map pages

**Applies to:** `maps/<domain>.md`

> A map is a **curated hub** for one domain — the syllabus you'd hand a newcomer, not the card catalog. It contrasts with `index.md` (exhaustive, auto-maintained) and the Obsidian graph (raw topology): a map is opinionated, ordered, and selective. Only load-bearing concepts, each with a sentence on *why* it matters.

## Conventions

### When a map should exist

- **Rule:** Create a map only once a domain (a tag cluster) passes ~10 concepts. Below that, `index.md` is enough and a map is just a second thing to maintain. `/lint` proposes a map when a cluster crosses the threshold.
- **Lint:** surface (do not auto-create) a domain past ~10 concepts with no map; never propose a map for a sparse cluster.

### Curated, not exhaustive

- **Rule:** A map lists only the **load-bearing** concepts of its domain, in a deliberate reading order, each with a one-sentence "why". It is allowed — expected — to omit minor concepts. Lead with the domain's central tension when there is one.
- **Shape:**
  ```markdown
  ---
  type: map
  tags: [<domain>]
  ---
  # <Domain> — map
  <one-line "start here">

  ## The core tension
  <the trade-off everything else hangs off, with [[links]]>

  ## <Grouping>
  - [[concept]] — <why it matters / when to reach for it>

  ## Open questions I'm chewing on
  - <unresolved>
  ```
- **Lint:** do not flag a map for being incomplete relative to `index.md` — selectivity is the point. Flag only `[[links]]` whose target concept doesn't exist.

## Pitfalls

- **Catalog cosplay.** Re-listing every concept in the domain — that's `index.md`'s job. A map curates.
- **Premature map.** Standing one up for a 3-concept domain. Wait for density.
- **Stale ordering.** A map's reading order or "core tension" going out of date as the domain evolves — revisit on major ingests.
