---
name: new-wiki
description: Bootstrap a new LLM-maintained knowledge base via a prism-driven interview. Reads 2–3 sample raw inputs, derives the right page types / kinds / relationships / frontmatter (separating concepts from categories the prism way), ratifies them with you, then scaffolds the wiki and dogfoods it on your samples. Use to start a new wiki/KB from scratch, or when asked to "set up a wiki", "bootstrap a knowledge base", or "make a project wiki".
---

# New wiki (prism-driven interview)

`$ARGUMENTS` = optional target directory for the new wiki (default: `./<wiki-name>` once
the name is known). If `$ARGUMENTS` names an existing non-empty directory, stop and ask
before touching it — never clobber.

You are running a **conversational interview** that derives a new knowledge base's
representation from the user's own sample inputs, then scaffolds it. This is a lightweight
KEOPS run: facts first, modalities as the questionnaire, the ontology as a commitment
proven on contact. **Load the `prism-interview` reference skill now** — it holds the
seven-stage playbook (the questions, mechanisms, and defaults) and the three standing
rules. Follow it; this skill is just the driver.

## Operating rules (from `prism-interview`, restated because they're load-bearing)

- **Minimal viable ontology.** Floor: `concept` + `source`, ~3–5 kinds, ~4 relationships.
  Refuse anything richer unless a sampled fact demands it.
- **You propose, the user ratifies.** Every derived element is a draft to confirm or edit.
- **Separate meaning (concept) from filing (kind).** Never let a category masquerade as a
  concept or vice-versa.
- **No fact, no structure.** Don't design for a domain the user can't show you a sample of.

## Phase 1 — Interview (read-only)

Run stages 1–6 of `prism-interview` as a conversation. Use `AskUserQuestion` for the
discrete choices (kinds grouping, relationship set, operations) and free prose for the
open ones (what recurs, what it's for). Keep it tight — fold follow-ups in, take the
default and move on whenever a sample doesn't force a richer answer. Do **not** write any
wiki files in this phase (saving the pasted samples under a scratch path is fine).

As you go, assemble the **ontology spec** — the YAML hand-off whose exact fields, defaults,
and validation invariants are the `ontology-spec` reference skill (load it). Each stage in
`prism-interview` names what it emits into the spec: `wiki_name`, `one_liner`, `raw_media`,
`page_types`, `kinds`, `frontmatter`, `relationships`, `operations`,
`seed_concepts`, `examples`.

## Phase 2 — Ratify (the gate)

Present the assembled ontology spec compactly and **STOP for approval** — this is the
prism's judgment firewall and the one hard gate in the flow:

```
## Proposed wiki — <wiki_name>

Page types   concept, source[, …]
Kinds        <k1> — <when>; <k2> — <when>; …            (≤5; cut if richer than the samples)
Relations    specializes↔generalizes, requires↔required-by, trades off against, …
Frontmatter  concept: type, kind, tags[], sources[], maturity
Operations   ingest, query, lint[, unify]
Seed pages   <n> concepts from your samples: <a>, <b>, …

Reply `scaffold` to build this, or amend (e.g. "drop kind X, add relation Y, rename Z").
```

If the user amends, fold the edits in and re-present. Only proceed on explicit approval.

## Phase 3 — Scaffold

Hand the ratified ontology spec to the scaffolder agent:

> `@wiki-scaffold:wiki-scaffolder <target-dir> <ontology-spec>`

It writes the directory skeleton, the **generated `CLAUDE.md`** (page types, kind registry,
relationship vocabulary, frontmatter schema, operations), the copied-and-injected operating
skills + conventions, `README.md`, `index.md`/`log.md`, `.gitignore`, and `git init`. It
returns a tree + summary. Relay that summary.

## Phase 4 — Dogfood (Stage 7)

Prove the ontology on contact before declaring done:

1. File the Phase-1 **samples** into the fresh wiki **directly**, per the generated
   `CLAUDE.md` + conventions. (The copied `/ingest` is not a live command in this session —
   it belongs to the new wiki, which the user runs from inside `<wiki>` afterwards.)
2. Inspect the result against the spec: a `kind` that never gets used, a missing
   relationship, a concept that should have been a tag (or vice-versa).
3. If anything drifted, **adjust the spec and re-stamp** the `CLAUDE.md`/conventions, then
   re-check. The day-one ontology is a seed — refine it now while it's cheap.
4. Report: the final shape, what changed after first ingest, and the next steps
   (`cd <wiki> && /ingest <next source>` + `git add -A && git commit`; and
   `/wiki-scaffold:evolve-schema <wiki>` periodically, to let the ontology grow with the corpus).

## Scope (v1)

Steer to a **bounded-homogeneous** wiki — one subject area, one kind of input. Multi-domain
wikis and cross-wiki linking are later phases (see `NOTES.md`).
If the user clearly needs multi-domain, scaffold the first domain well and note the rest as
a follow-up rather than over-building now.
