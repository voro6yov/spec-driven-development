---
name: query
description: Answer a question from the knowledge base and file durable findings back. Searches concept and source pages, synthesizes a cited answer, and leans on typed relationships (trade-offs, alternatives). Use for "what trades off against X", "how do these relate", or any KB lookup.
---
# Query the knowledge base

`$ARGUMENTS` = the question.

1. **Search** `concepts/` then `sources/` for relevant pages; follow typed relationships (`trades off against`, `alternative to`, `requires`) to neighbours.
2. **Synthesize** a cited answer using `[[wikilinks]]`. Separate what sources claim from my own recorded takes.
3. **Gaps** — if the answer reveals something not yet captured (a missing concept, an un-wired relationship, a fresh tension), file it back per the ingest conventions in `CLAUDE.md`.
4. **Log** only if the query produced a durable change: append a terse two-line entry to `log.md` — the heading `## [YYYY-MM-DD] query | <question>`, then **one** plain line on what changed. No `[[wikilinks]]` in the log (keep refs in `index.md` / the concept pages).
