---
name: concept
description: How to author a concept page — the spine of the KB. Frontmatter, the canonical section order (What it is / Relationships / Across sources / Tensions / My take), voice separation, granularity, and the maturity lifecycle (authoring + lint).
user-invocable: false
---

# Concept pages

**Applies to:** `concepts/<kebab>.md`

> A concept page captures exactly **one idea** and is the unit the whole KB compounds around. Sources come and go; concepts accrete angles. Keep each page about a single idea, in source-voice, with your own opinions fenced into a `> My take:` callout, and wire it to its neighbours via typed relationships.

## Conventions

### One idea per page, kebab-case filename

- **Rule:** Each concept page is one idea — a single concept of one `kind` (from the registry in `CLAUDE.md`). Filename is the kebab-case concept name (`{{EXAMPLE_CONCEPT}}.md`). If a page starts covering two ideas, split it and link the halves.
- **Lint:** flag a concept page whose body clearly describes two distinct ideas (two unrelated `## What it is` paragraphs) — propose a split.

### Frontmatter

- **Rule:** Required keys: `type: concept`, `kind` (from the registry — see [kinds/](../kinds/)), `tags []`, `sources []` (the `[[source]]` pages it was filed from), `maturity` (`seedling|growing|evergreen`).
- **Shape:**
  ```yaml
  ---
  type: concept
  kind: <kind>
  tags: [<topic>, <topic>]
  sources: ["[[<source-slug>]]"]
  maturity: growing
  ---
  ```
- **Example:** `concepts/{{EXAMPLE_CONCEPT}}.md`.
- **Lint:** flag a missing `kind` or `maturity`; flag a `sources` entry pointing at a nonexistent source page.

### Canonical section order

- **Rule:** Sections, in this order: `# <Name>` + a one-sentence plain-language definition; `## What it is` (the synthesized core — 2–4 sentences for a seedling, growing into a fuller *idea-organized* treatment as sources accrue; source-voice; **all** cross-source synthesis lives here); `## Relationships` (typed, reciprocal — see [relationships/](../relationships/)); `## Across sources` (**thin provenance** — one bullet per source, each its distinct angle in ≤2 sentences; never a per-chapter ledger or a home for synthesis); `## Tensions & open questions`; a closing `> My take:` callout. Omit `## Tensions` only if there genuinely are none; never omit `## Relationships` or `## Across sources`.
- **Shape:**
  ```markdown
  # <Concept>
  <one-sentence definition>

  ## What it is
  <2–4 sentences, neutral>

  ## Relationships
  - trades off against :: [[...]]

  ## Across sources
  - [[source]] — <angle>

  ## Tensions & open questions
  - <unresolved>

  > My take: <opinion>
  ```
- **Example:** `concepts/{{EXAMPLE_CONCEPT}}.md` follows this exactly.
- **Lint:** flag a concept missing `## Relationships` or `## Across sources`; treat the `> My take:` callout as canonical (do not flag it as informal).

### Voice separation

- **Rule:** `## What it is` and `## Across sources` are **source-voice** — neutral, attributable. All opinion, heuristics, and war stories go in the `> My take:` callout. Never blend them.
- **Lint:** flag first-person opinion ("I think", "in my experience") appearing outside a `> My take:` callout — move it in.

### Synthesis in the body, provenance in `## Across sources`

- **Rule:** As a concept gains sources, the synthesis of what they jointly say belongs in **`## What it is`** — which may grow past the seedling's 2–4 sentences into a fuller, *idea-organized* treatment (organized by sub-idea, **never** source-by-source). **`## Across sources` stays thin provenance**: one bullet per source (matching the frontmatter `sources`), each naming that source's distinct contribution in ≤2 sentences. It is **not** a per-chapter ledger, and cross-source comparison ("X frames it as A, Y as B") is *synthesis* — it lives in the body, not in a bullet. Three page shapes scale this, and unification compresses by **fusion and delegation, never by dropping substance** (relocate named examples, numbers, and distinctions — up into the body, or down into a child — don't delete them):
  - **cohesive** — one big idea, usually one source; its links are inputs/relations, not sub-parts. The long body is **earned** — don't cut it; `## Across sources` is a one-line pointer.
  - **cluster** — several sources, no specialization children; fuse their angles into the body, keep one provenance line per source.
  - **hub** — several sources *and* it re-explains child concepts that have their own pages; additionally **delegate** that detail to the child (link + one synthesizing clause), after confirming the detail lives there.
- **Lint:** flag an `## Across sources` bullet that runs to a paragraph, recaps a source chapter-by-chapter, or carries cross-source comparison — that's accretion drift; the repair is to lift the synthesis into `## What it is` and reduce the bullet to provenance. Flag `#bullets > #sources` (per-chapter ledger). Do **not** flag a long `## What it is` on a `growing`/`evergreen` page — a fuller synthesized body is canonical. This repair is exactly what `/unify` and the `concept-unifier` agent perform.

### Granularity: explode, don't summarize

- **Rule:** A source is filed by exploding it into 5–15 concept pages, not summarized on one. Prefer a real concept over a thin stub: if you can't write a `## What it is` and at least one relationship, it's probably a tag, not a concept.
- **Lint:** surface concept pages with an empty `## Relationships` and a one-line body as candidate stubs to merge or enrich.

### Maturity lifecycle

- **Rule:** `seedling` = just captured, usually one source, thin body. `growing` = the concept has accreted real substance. `evergreen` = stable, well-linked, you'd defend it. Maturity tracks **how developed a page is, not its source count** — there are two paths to `growing`:
  - **source-accretion** (the automatic path): bump during `/ingest` when a concept gains its 2nd+ source or a fuller relationship set.
  - **development** (an editorial path): a *single-source* page may be `growing` when it has grown into a substantial, well-wired page on its own — a fuller `## What it is`, several wired relationships, and meaningful inbound links (a hub like `{{EXAMPLE_CONCEPT}}`, referenced by many neighbours, qualifies even with a concise body). This is a curator's judgment call, not something `/ingest` triggers.

  Promotion past `growing` to `evergreen` is always the editorial "you'd defend it" call — never automatic, regardless of source count.
- **Lint:** surface `seedling` pages untouched across many ingests (stalled) — *and*, separately, dense single-source seedlings (high inbound + several edges + a developed body) as **development-promotion candidates**. Do **not** flag a single-source `growing`/`evergreen` page as over-promoted on source count alone (maturity is development, not a source tally); only flag a high-maturity page that is genuinely thin and sparsely linked (a real over-promotion).

## Pitfalls

- **Stub concepts.** A page with a title and nothing else. Either enrich (definition + one relationship) or fold into a richer concept.
- **Two ideas, one page.** Split on the seam and link.
- **Opinion leakage.** Editorializing in `## What it is`. Move it to `> My take:`.
- **Orphan concept.** No inbound links — wire it from a source's `## Filed into` or a neighbour's relationships, or it's invisible.
- **Accretion ledger.** `## Across sources` swollen into per-chapter walls while `## What it is` stayed thin — the synthesis leaked into the provenance section. Lift it into the body; reduce `## Across sources` to one provenance line per source. (`/unify` automates this.)
