---
name: ingest
description: File a source (book, article, talk, paper, note) into the knowledge base. By default plans and applies in one pass; pass `--review` to insert an approval gate that PRESENTS a reviewable, numbered diff of the concepts/sources/authors before writing. Supports ingesting a book chapter by chapter across repeated invocations. Use when adding new material or asked to "file"/"ingest"/"add" something to the KB.
---
# Ingest a source (interactive)

`$ARGUMENTS` = the source to ingest — a path under `raw/`, an attached/pasted excerpt, a URL, or a single book chapter. If empty, use the content I provided in this message / most recent upload.

**Flag — `--review`.** If `--review` appears anywhere in `$ARGUMENTS`, strip it out (the remainder is the source reference) and run with the approval gate **on**; otherwise run straight through.
- **Default (no `--review`)** — plan, then apply in one pass. Do **not** stop for approval. The idempotency check (Phase 1 step 3) and scope guard (step 6) remain safety valves that may still interrupt.
- **`--review`** — after planning, present the numbered diff and **STOP**; create or modify a **wiki** page (`concepts/`, `sources/`, `authors/`, `maps/`, `index.md`, `log.md`) only after I approve or amend.

Either way, **Phase 2 (Apply) is the only phase that writes wiki pages** — planning is analysis, not writing. Persisting the raw input under `raw/` is always allowed (it's the source cache, not the graph).

Before planning, load the `conventions` skill — `concept/`, `source/`, `relationships/`, `kinds/`, and `author/`/`map/` as needed.

## Phase 1 — Plan (read-only for the wiki)

1. **Capture the input.** Save the source/chapter as a markdown copy under `raw/<medium>/` now, so Phase 2 has an authoritative copy even if I approve later or context is trimmed. (`raw/` is a synced cache, not git-tracked — this doesn't touch the graph.)
2. **Identify the source** and check `sources/` for it. For a **book**, the folder is `raw/books/<slug>/`; read its `_meta.md` for title/authors/year/tags (`conventions/raw-books/`), and use `<slug>` as the `sources/<slug>.md` page name. For a book ingested chapter-by-chapter, the page is created on the first chapter and **updated** on later ones (`conventions/source/` → incremental ingestion).
3. **Idempotency check.** Read the source page's `## Coverage` and the `log.md` ingest entries for this source. If this chapter/section looks already ingested, **say so and ask whether to re-run** before planning anything else.
4. **Resolve against the existing graph — match before you mint.** Search `concepts/`, and for each idea in the chapter decide whether it is:
   - an **existing concept** (same idea, possibly under a different name — e.g. a chapter term that's a synonym of existing `[[{{EXAMPLE_CONCEPT}}]]`) → plan an UPDATE or a new relationship, **not** a new page;
   - a **genuinely new** concept → plan a CREATE;
   - a **near-synonym you're unsure about** → do **not** silently create; list it under Open questions for me to decide.
   Prefer enriching or relating an existing concept over minting a near-duplicate — duplicate near-synonyms are the main way this KB rots.
5. **Build the diff.** Decide: source CREATE/UPDATE (+ how `## Coverage` advances); authors CREATE/UPDATE/none; concepts to create (kind + one-line def + its relationships); concepts to update (the specific angle this chapter adds — planned as a **fold-up into `## What it is`**, not a new `## Across sources` bullet; + any maturity bump); relationships to wire (with reciprocal target); new kinds proposed (with rationale); contradictions/tensions.
6. **Scope guard.** If the chapter yields more than ~15 concepts, it's probably too big to review well — say so and offer to split it (e.g. by section) rather than dumping a giant plan.
7. **Gate on the mode.**
   - **`--review`:** present the plan in the numbered format below, then **STOP**. Touch no wiki file. Invite me to reply `apply`, or to amend by item id (e.g. "drop C3, recategorize C7 as principle, skip A1").
   - **Default:** skip the presentation and the stop — carry the plan you just built straight into Phase 2 as the contract. (You may still emit a one-line summary of what you're about to write.)

### Plan format  (`--review` only)
```
## Review — <Title>, <chapter or section>

S    CREATE|UPDATE  sources/<kebab>.md   — <note, e.g. "append ch.3; Coverage → chs.1–3">
A1   CREATE authors/<kebab>.md           — <focus>            (omit if none)

Concepts to create
C1   <name> (<kind>) — <one-line definition>
       rels: <verb> [[x]], <verb> [[y]]
Concepts to update
C2   <name> — <what this chapter adds>   [maturity: seedling→growing]
       new rels: <verb> [[z]]

Relationships to wire   (→ directed, ↔ symmetric; reciprocal mirror added on apply)
R1   [[a]] —enables→ [[b]]
R2   [[c]] ↔ trades off against ↔ [[d]]

K1   new kind: <kind> — <why>                                  (omit if none)
X1   tension: <claim> vs [[existing]] → record on [[existing]] (omit if none)

Open questions (decide before apply)
Q1   "<chapter term>" — same as existing [[concept]], or a new concept?
```
If the chapter adds nothing new, say so plainly ("ch.4 adds no new concepts — proposes R1, R2 only") rather than padding the plan. End with: **"Reply `apply` to write this, or amend by item id."**

## Phase 2 — Apply

In `--review` mode, apply only after I approve; by default, apply directly using the plan from Phase 1. Treat the plan (with my edits folded in, if I reviewed) as the contract. **Re-read the source from `raw/`** so you work from the saved copy, not remembered context. Then, per the `conventions`:

1. **Source page** — create, or update its `## Filed into` and `## Coverage`.
2. **Concepts** — create/update each; set `kind` + `maturity`. When **updating** an existing concept, fold this chapter's angle into the synthesized `## What it is` body and keep `## Across sources` to one thin provenance line per source — do **not** append a per-chapter bullet (`conventions/concept/` → *Synthesis in the body, provenance in `## Across sources`*). Wire each relationship and add its reciprocal mirror **on the other page if that page exists**. If the target isn't created yet, leave the one-directional link as a TODO for `/lint` (per `conventions/relationships/`).
3. **Authors** — create/update if planned.
4. **Bookkeeping** — update `index.md`; append a **terse two-line entry** to `log.md`: the heading `## [YYYY-MM-DD] ingest | <title> — ch.N`, then **one** plain line — the chapter's topic + bare counts (`+N concepts[, M updated][, K rels][, new kind: X]`; add a short clause only for something notable like a resolved TODO). **No `[[wikilinks]]` and no per-concept/relationship lists in the log** — refs live in `index.md` and the concept pages; the log is a lean audit trail, not a content dump. (`index.md` is where the full wikilinked detail goes.)
5. **Report** what was actually written: created vs updated counts, relationships wired (and any TODO mirrors left for `/lint`), kinds added, contradictions recorded. Then remind me to `git add -A && git commit && git push`.

If I reviewed and my edits change the plan's shape materially, **re-present the revised plan** (back to Phase 1 step 7) instead of applying.
