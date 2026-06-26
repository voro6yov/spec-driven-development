---
name: source
description: How to author a source page — a thin provenance anchor for one book/article/talk/paper/note. Filename/slug, frontmatter (incl. plural authors and book _meta.md derivation), the Thesis / Filed into / My verdict sections, chapter-by-chapter ingestion, and the "never dump content" rule (authoring + lint).
user-invocable: false
---

# Source pages

**Applies to:** `sources/<kebab>.md`

> A source page records **where knowledge came from**, not the knowledge itself. The ideas belong on concept pages; the source page is a thin anchor — provenance, a one-paragraph thesis, and your verdict. If a source page is getting long, you're filing content in the wrong place.

## Conventions

### Filename matches the raw source slug

- **Rule:** A source page's slug matches its raw counterpart. For a **book**, that's the `raw/books/<book-slug>/` folder name (e.g. `sources/<book-slug>.md`), per [raw-books/](../raw-books/). For a single-file source (article/paper), use the kebab short title. Don't author-prefix. If two sources genuinely collide, disambiguate with a trailing `-<year>`.
- **Lint:** flag a `medium: book` source whose slug has no matching `raw/books/` folder.

### Frontmatter

- **Rule:** Required: `type: source`, `medium` (`book|article|talk|paper|doc|experience`), `title`, `authors` (a **list** of `[[author]]` links, or plain strings when no author page exists), `year`, `consumed` (`YYYY-MM`), `rating` (1–5), `tags []`. For books these are derived from the folder's `_meta.md` (see [raw-books/](../raw-books/)).
- **Shape:**
  ```yaml
  ---
  type: source
  medium: book
  title: "<Source Title>"
  authors: ["[[author-one]]", "[[author-two]]"]
  year: 2025
  consumed: 2026-02
  rating: 5
  tags: [<topic>]
  ---
  ```
- **Example:** `sources/<book-slug>.md`.
- **Lint:** flag a missing `medium` or `consumed`; treat plain-string entries in `authors` (no `[[ ]]`) as canonical when no author page exists.

### Sections: Thesis / Filed into / My verdict

- **Rule:** `# <Title>`; a bold **Thesis:** of one paragraph capturing the central argument; `## Filed into` listing the `[[concepts]]` this source contributed to; a closing `> My verdict:` callout (rating rationale, who it's for, what to pair it with).
- **Shape:**
  ```markdown
  # <Title>
  **Thesis:** <one paragraph>

  ## Filed into
  [[concept-a]] · [[concept-b]] · [[concept-c]]

  > My verdict: <opinion>
  ```
- **Lint:** flag a source with no `## Filed into` links (an un-exploded source — its ideas were never captured). This is the highest-value source-lint finding.

### Incremental (chapter-by-chapter) ingestion

- **Rule:** A long source (a book read chapter by chapter) is ingested across several `/ingest` runs. Create the source page on the first run; **update** it on each later one — `## Filed into` accretes new concept links, and an optional `## Coverage` line records how far you've read. Never spawn a separate source page per chapter.
- **Shape:**
  ```markdown
  ## Filed into
  [[concept-a]] · [[concept-b]]   <!-- grows each chapter -->

  ## Coverage
  chs. 1–3 ingested (2026-06-21)
  ```
- **Lint:** treat `## Coverage` as canonical (don't flag it); surface a `## Coverage` that lags the `log.md` ingest entries for that source (a chapter was ingested but coverage wasn't bumped).

### Thin anchor, never a content dump

- **Rule:** Do not summarize the source chapter-by-chapter here. Each load-bearing idea becomes (or updates) a concept page; the source page only points at them via `## Filed into`, and each concept's `## Across sources` bullet carries this source's angle.
- **Lint:** surface a source page whose body is long-form notes rather than thesis + links — its content should be redistributed into concepts.

## Pitfalls

- **The content sink.** Treating the source page as a book report. The value lives in concepts; the source is an anchor.
- **Un-exploded source.** A source page with an empty `## Filed into` — you logged that you read it but captured nothing. Explode it.
- **Broken provenance.** A concept's `sources` lists a source whose page doesn't exist, or a source's `## Filed into` names a concept that doesn't exist — keep both ends real.
