---
name: lint
description: Audit the knowledge base for bookkeeping problems and fix the mechanical ones — relationship reciprocity, orphan concepts, un-exploded sources, stale seedlings, contradictions, broken wikilinks; propose domain maps for dense clusters. Use periodically or after a batch of ingests.
---
# Lint the knowledge base

`$ARGUMENTS` = optional domain/tag to scope the audit (else the whole KB).

First load the **`conventions`** reference skill (`.claude/skills/conventions/`) and read each theme's **Lint** bullets — they define what is canonical (never flag) versus what to **auto-fix**. Then check, auto-fix mechanical issues, and surface judgment calls in a report:

- **Relationship reciprocity** (auto-fix) — every relationship must have its mirror. `trades off against` / `alternative to` are symmetric; enables↔enabled-by, requires↔required-by, specializes↔generalizes are inverse pairs. (`conventions/relationships/`)
- **Section structure** (surface) — a page missing a required section for its type (a concept with no `## Relationships`, a source with no thesis or `## Filed into`). (`conventions/<type>/`)
- **Kind validity** (surface) — a concept whose `kind` isn't in the `CLAUDE.md` registry; propose adding it or recategorizing. (`conventions/kinds/`)
- **Concept/category separation** (surface) — flag a page whose `kind` reads like a standalone idea that deserves its own `concept` page, or a `concept` so thin it's really a tag (the intrinsic-identity test: a real concept supports a one-sentence definition + at least one relationship). Keeping *meaning* (concepts) distinct from *filing* (kinds) is the prism's founding rule; this is where it drifts. (`conventions/kinds/`, `conventions/concept/`)
- **Orphans** (surface) — concept pages with no inbound links.
- **Un-exploded sources** (surface) — sources whose ideas were never filed into concepts (empty `## Filed into`).
- **Stale seedlings** (surface) — `maturity: seedling` pages untouched across many ingests.
- **Contradictions** (surface) — conflicting claims across concept pages.
- **Broken wikilinks** (auto-fix when unambiguous) — create stubs or fix obvious typos.
- **Map proposal** (surface) — a tag/domain cluster past ~10 concepts with no `maps/` page → propose one. (`conventions/map/`)

End with a summary: counts fixed vs flagged, and recommended next actions.
