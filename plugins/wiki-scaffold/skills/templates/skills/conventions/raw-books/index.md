---
name: raw-books
description: Layout convention for book sources under raw/books/ — one folder per book, a reserved _meta.md metadata file, chapter content files, and how that folder maps onto a sources/ page and author pages (authoring + lint).
user-invocable: false
---

# Raw book folders

**Applies to:** `raw/books/`

> A book is a **folder**, not a file — it's read chapter by chapter over time, so it needs somewhere to keep its chapters and its metadata. Each book lives in `raw/books/<book-slug>/` with a reserved `_meta.md` and one file per chapter. `/ingest` reads `_meta.md` to populate the book's `sources/` page; the chapter files are the content it explodes into concepts.

## Conventions

### One folder per book; the slug is the identity

- **Rule:** Each book is `raw/books/<book-slug>/`, where `<book-slug>` is the kebab-case short title of the book. That same slug is the book's identity end-to-end: its source page is `sources/<book-slug>.md` (see [source/](../source/) → filename). Do **not** author-prefix the book slug.
- **Lint:** flag a `raw/books/<slug>/` folder whose `sources/<slug>.md` is missing once any chapter has been ingested; flag a `medium: book` source page whose slug has no matching `raw/books/` folder.

### `_meta.md` — the reserved metadata file

- **Rule:** Each book folder contains `_meta.md` (the underscore marks it as metadata, **never** ingested as a chapter). It uses plain `Key: Value` lines:

  | Key | Required | Maps to on `sources/<slug>.md` |
  |---|---|---|
  | `Title:` | yes | `title` |
  | `Authors:` | yes (comma-separated) | `authors` list + one `[[author]]` page each |
  | `Year:` | optional | `year` |
  | `SKILLS:` | optional | `tags` (normalize to kebab) |
  | `Description:` | optional (prose, may span lines) | *informs* the Thesis — synthesize, don't copy |

- **Shape:**
  ```
  Title: <Book Title>
  Authors: <First Author>, <Second Author>
  SKILLS: <topic>
  Description: <publisher blurb…>
  ```
- **Example:** `raw/books/<book-slug>/_meta.md`.
- **Lint:** flag a book folder with no `_meta.md`, or a `_meta.md` missing `Title:` or `Authors:`.

### Chapter / content files

- **Rule:** Chapters sit beside `_meta.md`, one file per chapter. Prefer a zero-padded numeric prefix so they sort (`03-modularity.md`); any name works. Files beginning with `_` are reserved (metadata/notes) and never ingested as content.
- **Lint:** none beyond the source's `## Coverage` reconciliation (see [source/](../source/) → incremental ingestion).

## Pitfalls

- **Metadata as a chapter.** Exploding `_meta.md` into concepts. `/ingest` reads it for the source page only.
- **Slug drift.** A `raw/books/<slug>/` folder and its `sources/` page using different slugs — keep them identical so the book is traceable end-to-end.
- **Copying the blurb.** Pasting `Description:` verbatim as the Thesis. The Thesis is your synthesized one-paragraph reading of the argument, not marketing copy.
