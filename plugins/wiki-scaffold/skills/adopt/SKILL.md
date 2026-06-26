---
name: adopt
description: Retrofit an existing pile of markdown notes (an Obsidian vault, a notes folder) into an LLM-maintained wiki — derive a fitting ontology from what is already written, then scaffold the schema + operating skills AROUND the existing content without modifying any of it. Use to bring an existing knowledge store under the wiki-scaffold loop.
---

# Adopt an existing markdown wiki

`$ARGUMENTS` = path to an existing folder of markdown notes (default: the current directory).

Same facts-first derivation as `/wiki-scaffold:new-wiki`, but the **facts are the notes that
already exist** — so it derives the ontology *from them* rather than from fresh samples, and it
**never rewrites your content**. **Load `prism-interview`** (the derivation mechanisms),
**`ontology-spec`** (the schema shape), and **`templates`** (the operating-skill payload).

## Hard guarantee — additive only

This skill **creates scaffolding** (`.claude/`, `CLAUDE.md`, `README.md`, `index.md`/`log.md`)
around your notes. It **never edits, moves, or deletes an existing content file.** If
`CLAUDE.md` or `.claude/` already exist, **stop and ask** before proceeding.

## Phase 1 — Survey the existing pile (read-only)

Treat the existing notes as the [[extensional-realm|facts]]. Detect, don't impose:
- the **folder/layout** already in use (a `concepts/`-like spine? flat? `pages/`?);
- recurring **frontmatter** keys and any existing `kind`/`type`/`tags`;
- the **link** convention (`[[wikilinks]]`? markdown links?) and which relationships are
  *implied* by how pages reference each other;
- recurring **page shapes** (definition + sections) → candidate page types;
- naming / identity (kebab slugs? titles?).

Sample broadly; for a large vault read a representative spread and **say what you sampled**.

## Phase 2 — Derive & ratify the ontology

Run `prism-interview` Stages 2–6 **seeded from the survey** (not blank): propose the
`page_types`, `kinds` (from existing tags/folders/patterns via [[entity-resolution]]),
`relationships` (from existing link patterns), and `frontmatter` that **best fit what is already
there** — the least-surprising schema, not an aspirational one. `seed_concepts: []` (content
already exists). Present the `ontology-spec` and **STOP for approval** (judgment firewall).

## Phase 3 — Scaffold additively

Generate `CLAUDE.md` from the ratified spec and apply the `templates` copy procedure — like
`wiki-scaffolder` Steps 3–5 — but in **additive** mode:
- create `.claude/` (skills + conventions + agents), `CLAUDE.md`, `README.md`, and
  `index.md`/`log.md` **only if absent**;
- write **no** `seed_concepts` (the pages exist) and **touch no content file**;
- if the existing layout differs from the conventions' expectation (notes in `pages/`, not
  `concepts/`), **record the mapping in `CLAUDE.md`** rather than moving files.

## Phase 4 — Reconcile & report

Offer (don't force) a first `/lint` pass to wire the existing pages to the new schema — kinds
to assign, relationships to mirror, orphans — as **proposals the user applies**, since this
touches content. Report what was created, the derived ontology, and the next steps (`/lint`,
then `/wiki-scaffold:evolve-schema` as the wiki grows).
