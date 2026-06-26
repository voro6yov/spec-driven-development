---
name: author
description: How to author an (optional) author page — frontmatter and the Works-in-KB list, with the co-author note convention (authoring + lint).
user-invocable: false
---

# Author pages

**Applies to:** `authors/<kebab>.md`

> Author pages are **optional** — create one only when tracking a person across multiple sources adds value (a recurring author, intellectual lineage, who-disagrees-with-whom). They are the first thing people stop maintaining; keep them thin.

## Conventions

### Frontmatter

- **Rule:** `type: author`, `tags []`, `sources []` (the `[[source]]` pages by this author).
- **Shape:**
  ```yaml
  ---
  type: author
  tags: [<topic>]
  sources: ["[[<source-slug>]]"]
  ---
  ```
- **Lint:** flag an author page with an empty `sources` (an orphan — no work attributed).

### Sections: Works in this KB

- **Rule:** `# <Full name>`; a one-line description of their focus; `## Works in this KB` listing each `[[source]]` with year and co-authors. Note co-authors inline and leave a `[[ ]]` TODO link for any not yet paged.
- **Shape:**
  ```markdown
  # <Full name>
  <one-line focus>

  ## Works in this KB
  - [[source]] (<year>, with <co-author>)
  ```
- **Example:** `authors/<author>.md` (notes a co-author inline with a `[[<co-author>]]` TODO).
- **Lint:** treat a `[[co-author]]` TODO link to a not-yet-written author page as canonical (not broken) — author pages are created lazily.

## Pitfalls

- **Premature author pages.** Don't create one for a one-off article author you'll never revisit — a plain `author:` string on the source is enough.
- **Drift from sources.** An author's `sources` list disagreeing with which source pages actually link back. `/lint` reconciles both directions.
