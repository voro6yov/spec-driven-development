---
name: templates
description: The portable operating skills and agents that wiki-scaffold copies into a freshly scaffolded wiki's .claude/ — the domain-agnostic core (ingest, query, lint, unify, the conventions umbrella, and the books-ingester/concept-unifier agents) lifted from the reference KB and parameterized with slots the scaffolder fills. Reference/resource group: the scaffolder resolves this skill's directory, copies the payload, renames, and substitutes. Not a user command.
user-invocable: false
disable-model-invocation: true
---

# Wiki templates (copy-in payload)

**Type:** Reference / resource group (the `spec-core:modules` pattern).

This skill registers one catalog entry; the real content is the **payload** in sibling
folders — operating skills and agents that are **copied verbatim (then slot-filled) into a
scaffolded wiki's `.claude/`**, never loaded as this plugin's own skills. They are the
*foundational ontology* layer: the domain-agnostic mechanism shared by every wiki this
plugin mints (the per-wiki domain ontology lives in the generated `CLAUDE.md`).

Provenance: lifted from the reference KB at `~/dev/wiki/knowledge-base/.claude/`. The
reference copies are software-architecture-specific; these are the **generic** version and
are **free to diverge** — no byte-sync obligation back to the reference (it's an instance,
this is the template).

## Resolution rule

The scaffolder cannot rely on `${CLAUDE_PLUGIN_ROOT}` in agent Bash. Instead it resolves
`<templates_dir>` as **the directory containing this `SKILL.md`** (loading the skill reveals
its own path), then copies from `<templates_dir>/skills` and `<templates_dir>/agents`.

## Payload layout

```
<templates_dir>/
├── skills/
│   ├── ingest/index.md          (operating skill)
│   ├── query/index.md
│   ├── lint/index.md
│   ├── unify/index.md
│   └── conventions/
│       ├── index.md             (umbrella)
│       ├── concept/index.md     (themes — copied verbatim)
│       ├── source/index.md
│       ├── author/index.md
│       ├── map/index.md
│       ├── kinds/index.md
│       ├── relationships/index.md
│       └── raw-books/index.md
└── agents/
    ├── books-ingester.md
    └── concept-unifier.md
```

Entry-file bodies are stored as `index.md` (not `SKILL.md`) so this plugin's loader never
registers them. They become `SKILL.md` on copy (see rename rule).

## Copy procedure (the scaffolder runs this)

1. **Select** by the spec's `operations`:
   - `ingest`, `query` — always.
   - `lint` — iff `lint ∈ operations`.
   - `unify` — iff `unify ∈ operations` (and copy the `concept-unifier` agent with it).
   - `conventions/` (umbrella + all themes) — always, **in full** (the umbrella's catalog
     requires every theme folder to resolve; `raw-books/` is harmless if the wiki has no books).
   - `books-ingester` agent — always (it just drives `/ingest`).
2. **Copy** the selected `skills/<name>/` dirs → `<wiki>/.claude/skills/<name>/`, and the
   selected `agents/*.md` → `<wiki>/.claude/agents/`.
3. **Rename entry files** `index.md → SKILL.md` for exactly these top-level skill dirs:
   `ingest/`, `query/`, `lint/`, `unify/`, `conventions/`. Theme files
   (`conventions/<theme>/index.md`) **stay `index.md`** — that is already their target name.
4. **Substitute slots** (below) across every copied file.

## Slot registry

Minimal by design — most payload text is verbatim mechanism, and the per-wiki kind registry
+ relationship vocabulary live in the generated `CLAUDE.md` that the copied skills already
reference ("from the registry — see CLAUDE.md"). Only four slots:

| Slot | Filled from (ontology spec) | Replaces |
| --- | --- | --- |
| `{{WIKI_NAME}}` | `wiki_name` | the KB's name in prose |
| `{{ONE_LINER}}` | `one_liner` | the "what this KB is" line |
| `{{DOMAIN}}` | `one_liner` (noun phrase) | "software architecture & engineering" |
| `{{EXAMPLE_CONCEPT}}` | `examples[0]` (else `seed_concepts[0].name`) | the worked-example page name (was `microservices.md`) |

After substitution there must be **no `{{…}}` left**; the scaffolder greps for residual
slots and aborts if any remain.

## Divergence policy

- These templates are the canonical *portable* operating skills; evolve them here.
- They intentionally do **not** track the reference KB. If a genuinely generic improvement
  lands in the reference, port it deliberately; never auto-sync.
- Adding a new portable skill: add `skills/<name>/index.md`, list it in the payload layout
  and the copy procedure's selection rule.
