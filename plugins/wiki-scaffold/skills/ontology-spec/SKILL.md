---
name: ontology-spec
description: The locked contract between the wiki-scaffold interview and the scaffolder — the YAML "ontology spec" the /wiki-scaffold:new-wiki interview emits and @wiki-scaffold:wiki-scaffolder consumes to write a new wiki. Defines every field, its type, defaults, and the validation invariants a well-formed spec must satisfy. Load when emitting or consuming the hand-off. Reference only.
user-invocable: false
disable-model-invocation: false
---

# Ontology spec (the interview → scaffolder contract)

**Type:** Reference (the single source of truth for the hand-off shape).

- **Produced by** `/wiki-scaffold:new-wiki` — assembled across interview stages 1–6, frozen
  at the Phase-2 ratify gate.
- **Consumed by** `@wiki-scaffold:wiki-scaffolder` — the contract it writes the wiki from.
  The scaffolder must not invent fields beyond it or drop any.

It is the prism's *logical realm* for the new wiki, captured declaratively. Keep it **small**
— the spec encodes a *minimal viable ontology* (see `prism-interview` Rule 1), not an
exhaustive one.

## Serialization

A single YAML document. The scaffolder receives it verbatim as `<ontology-spec>`. Unknown
top-level keys are an error (catch typos early). `spec_version` pins the shape.

## Fields

| Field | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `spec_version` | string | yes | `"1"` | This document's version. Bump on schema changes. |
| `wiki_name` | string | yes | — | kebab-case; directory name + title slug. |
| `one_liner` | string | yes | — | What this wiki is for. Goes in `CLAUDE.md` + `README.md`. |
| `raw_media` | list<string> | yes | — | ≥1 kebab tokens (`book`, `article`, `chat-log`, `adr`, `ticket`…). Each → `raw/<medium>/` (manual drop — no fetcher automation). |
| `page_types` | list<object> | yes | — | Must include `concept` and `source`. See *page_type*. |
| `kinds` | list<object> | yes | — | The open `kind` registry. **2–5** recommended; the scaffolder warns past 7. See *kind*. |
| `relationships` | list<object> | yes | — | The typed reciprocal vocabulary. ≥1. See *relationship*. |
| `frontmatter` | map<page_type → list<string>> | yes | — | Ordered frontmatter field names per page type. |
| `maturity_scheme` | list<string> | no | `[seedling, growing, evergreen]` | The `maturity`/status ladder (Stage 4 temporality/veracity). |
| `operations` | list<string> | yes | — | Subset of `[ingest, query, lint, unify]`. Must contain `ingest` and `query`. |
| `naming` | string | no | `kebab-slug` | Filename scheme: `kebab-slug` or `id-prefixed` (e.g. `ADR-007-...`). |
| `seed_concepts` | list<object> | no | `[]` | Pages to write on scaffold (Stage 2). See *seed_concept*. |
| `examples` | list<string> | no | `[]` | 1–2 `seed_concepts` names rendered as fuller worked examples in the conventions. |

### Object shapes

- **page_type** — `{name: string, location: string, role: string}`.
  `location` is a path pattern, e.g. `concepts/<kebab>.md`. `concept` is THE spine; `source`
  is provenance. Optional extras (`author`, `map`, or domain-specific) only when Stage 4
  agency/realm made them live.
- **kind** — `{name: string, when: string}`. `name` is a frontmatter value, never a folder.
  `when` is the one-line "use this when…" that goes in the registry table.
- **relationship** — exactly one of:
  - `{verb: string, symmetric: true}` — same verb both sides (`trades off against`,
    `alternative to`), or
  - `{verb: string, inverse: string}` — an inverse pair (`requires`/`required-by`,
    `enables`/`enabled-by`, `specializes`/`generalizes`).
- **seed_concept** — `{name: string, kind: string, definition: string}`. `kind` must be one
  of `kinds[].name`. `definition` is the one-sentence page lede.

## Validation invariants

The scaffolder aborts with a single `ERROR: ...` line if any fails:

1. `wiki_name` is kebab-case (`^[a-z][a-z0-9]*(-[a-z0-9]+)*$`).
2. `page_types` includes both `concept` and `source`.
3. `operations` includes both `ingest` and `query`; every entry ∈ `{ingest,query,lint,unify}`.
4. `unify ∈ operations ⟹ maps/` is created and `map ∈ page_types` (interoperability needs a
   home) — else warn and add `map`.
5. Every `relationship` is exactly symmetric **xor** has an `inverse` (never both, never
   neither).
6. Every `seed_concept.kind` ∈ `kinds[].name`; every `examples[]` ∈ `seed_concepts[].name`.
7. `frontmatter` has an entry for each `page_types[].name`; the `concept` entry includes
   `kind` and `maturity`.
8. No unknown top-level keys; `spec_version` present.

Soft checks (warn, don't abort): `len(kinds) > 7` (over-engineering smell — see
`prism-interview` Rule 1); a `kind` with no `seed_concept` using it (unused category).

## Minimal example (the floor)

```yaml
spec_version: "1"
wiki_name: cooking-notes
one_liner: A compounding wiki of techniques, ingredients, and dishes I cook.
raw_media: [recipe]
page_types:
  - {name: concept, location: concepts/<kebab>.md, role: one idea — a technique/ingredient/dish}
  - {name: source,  location: sources/<kebab>.md,  role: provenance for one recipe/book}
kinds:
  - {name: technique,  when: a method (braising, emulsifying)}
  - {name: ingredient, when: a single ingredient and its behavior}
  - {name: dish,       when: a finished dish that composes techniques + ingredients}
relationships:
  - {verb: requires, inverse: required-by}
  - {verb: specializes, inverse: generalizes}
  - {verb: pairs with, symmetric: true}
frontmatter:
  concept: [type, kind, tags, sources, maturity]
  source:  [type, medium, title, year, rating, tags]
operations: [ingest, query, lint]
seed_concepts:
  - {name: braising, kind: technique, definition: Slow moist-heat cooking of seared food in a little liquid.}
  - {name: emulsification, kind: technique, definition: Forcing two immiscible liquids into a stable suspension.}
examples: [braising]
```

## Fuller example (architect-project profile — `NOTES.md` §9.4)

```yaml
spec_version: "1"
wiki_name: payments-platform-wiki
one_liner: The living design record for the payments platform — decisions, components, risks.
raw_media: [adr, meeting-note, diagram]
page_types:
  - {name: concept, location: concepts/<kebab>.md, role: a component / characteristic / risk}
  - {name: source,  location: sources/<kebab>.md,  role: an ADR / meeting / doc it was filed from}
  - {name: author,  location: authors/<kebab>.md,  role: a person or team (agency was live)}
kinds:
  - {name: component,      when: a deployable/logical part of the system}
  - {name: characteristic, when: an -ility the architecture must exhibit}
  - {name: decision,       when: an architectural decision (ADR-backed)}
  - {name: risk,           when: a tracked architectural risk}
relationships:
  - {verb: part-of, inverse: contains}
  - {verb: realizes, inverse: realized-by}
  - {verb: affects, inverse: affected-by}
  - {verb: mitigates, inverse: mitigated-by}
  - {verb: trades off against, symmetric: true}
frontmatter:
  concept: [type, kind, tags, sources, maturity]
  source:  [type, medium, title, date, tags]
  author:  [type, tags, sources]
maturity_scheme: [proposed, accepted, superseded]
operations: [ingest, query, lint, unify]
naming: kebab-slug
seed_concepts:
  - {name: ledger-service, kind: component, definition: Append-only record of money movements.}
  - {name: idempotency, kind: characteristic, definition: Repeated requests yield one effect.}
examples: [ledger-service]
```

## Versioning

`spec_version` is the only forward-compat lever. A breaking change to any field bumps it;
the scaffolder rejects a `spec_version` it doesn't know with
`ERROR: unsupported ontology-spec version <v>`.
