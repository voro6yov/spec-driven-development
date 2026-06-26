---
name: evolve-schema
description: Refine an existing LLM-maintained wiki's ontology as it grows — the day-N counterpart of new-wiki. Reads the accumulated raw/ + concepts/ + log.md, proposes schema deltas (new/retired kinds, new relationships, splits, concept↔tag/kind reclassification) as a ratifiable diff, and on approval re-stamps CLAUDE.md and migrates the affected pages. Use periodically, or when the kind registry / relationships no longer fit what the wiki has become.
---

# Evolve the wiki's ontology (day-N refinement)

`$ARGUMENTS` = path to an existing scaffolded wiki (default: the current directory). It must
contain a `CLAUDE.md` and a `concepts/` folder — abort otherwise (this skill *refines* an
existing ontology, it does not create one; use `/wiki-scaffold:new-wiki` for that).

The schema you bootstrapped on day 0 was a **hypothesis, not a contract**. The prism, the
LLM-wiki idea, and DDD all say the same thing: knowledge engineering is *iterative and
incremental*, "**knowledge grows at the edges**," and a fitting structure is **discovered** as
facts accumulate — "possibly changing into a completely different kind of structure along the
way" ([[evolving-order]]). This skill is that discovery loop. **Load `prism-interview`** (the
mechanisms — entity-resolution, modalities, the three standing rules) and **`ontology-spec`**
(the schema shape you mutate).

## Standing rules

- **You propose, the user ratifies** — every delta is a draft (the judgment firewall).
- **Grow at the edges, minimally** — propose only what the *current corpus* forces, at the
  [[last-responsible-moment]]. No speculative kinds. Refactor "when the design no longer
  expresses the team's current understanding" ([[refactoring-toward-deeper-insight]]), not on
  a schedule.
- **Never drop substance — relocate.** Merging kinds re-files pages; splitting a concept moves
  its text into the new page; demoting a concept to a tag preserves its content somewhere.
- **Reciprocity is sacred** — any relationship rename/add keeps both mirrored sides.

## Phase 1 — Read the wiki (read-only)

Build the picture of *ontology-as-declared* vs *ontology-as-used*:
1. `CLAUDE.md` — the declared `kind` registry, relationship vocabulary, frontmatter, page types.
2. `concepts/` — the **kinds actually in use** (count per kind), the **relationships actually
   used**, orphans, and any freeform/illegal verbs the wiki's lint would flag.
3. `log.md` / `index.md` — what's been ingested since the last schema change; growth hotspots.
4. `raw/` — unfiled or thinly-filed material hinting at concepts not yet captured.

## Phase 2 — Propose deltas (entity-resolution over the accumulated graph)

Surface only what the corpus now justifies:
- **New kind** — a cluster of ≥3 concepts that fit no existing kind cleanly (intrinsic-identity
  test). Mint it the way [[entity-resolution]] mints a bridging concept.
- **Retire / merge kind** — a kind with ≤1 use, or two that collapse into one.
- **New relationship** — a tie authors keep reaching for (freeform verbs lint flagged, or a
  recurring "see also / depends on" prose pattern). Add with its reciprocal.
- **Reclassify (the prism Rule-3 check)** — a `kind` that's really a standalone concept; a
  concept so thin it's really a tag; a concept that's two ideas → split.
- **Maturity / veracity** — the status ladder no longer matches how you reason about staleness.

Present a compact, ratifiable diff and **STOP**:
```
## Proposed schema changes — <wiki>

+ kind    `<k>` — <when>           (covers <a>, <b>, <c> — now mis-filed as <x>)
- kind    `<k>` — retire           (only <a> uses it; re-file as <y>)
+ rel     `<verb>` ↔ `<inverse>`   (authors wrote it freeform 6×)
~ split   `<concept>` → `<a>` + `<b>`   (two ideas on one page)
~ reclass `<page>`: kind→concept   (it has standalone identity)

Migrations: <n> pages re-tagged, <m> relationships rewired.
Reply `apply` to make these changes, or amend.
```
If the corpus forces nothing, say so plainly ("schema still fits — no changes") rather than
inventing churn.

## Phase 3 — Apply (on approval)

1. **`CLAUDE.md`** — update the kind registry / relationship vocabulary / frontmatter to match.
2. **Pages** — perform the migrations: re-tag kinds, rename relationship verbs (both mirrors),
   split/merge pages relocating *all* substance, fix `sources`/links. Touch only what the diff
   lists.
3. **Conventions** — usually untouched (the copied conventions reference `CLAUDE.md`); edit a
   theme only if a convention *rule itself* changed.
4. **Lint** — reconcile reciprocity and orphans after the migration (per the wiki's own lint).

## Phase 4 — Report & log

Append a terse entry to the wiki's `log.md`:
`## [YYYY-MM-DD] evolve | <one-line what changed>` + one line of counts. Report the deltas
applied and the migrations, and remind: `git add -A && git commit`.
