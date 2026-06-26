# Profile: architect project

**When to use:** a *living design record* for one system/project — not a knowledge-distillation
wiki but a decision/component/risk graph an architect maintains. Reuses the vocabulary the
reference KB already developed (ADRs, characteristics, risk-storming). Has `author` pages
(agency is live) and `unify`/`maps` on (a project spans heterogeneous concerns).

```yaml
spec_version: "1"
wiki_name: <project>-wiki
one_liner: The living design record for <project> — decisions, components, characteristics, risks.
raw_media: [adr, meeting-note, diagram]
page_types:
  - {name: concept, location: concepts/<kebab>.md, role: a component / characteristic / decision / risk}
  - {name: source,  location: sources/<kebab>.md,  role: an ADR / meeting / doc it was filed from}
  - {name: author,  location: authors/<kebab>.md,  role: a person or team}
kinds:
  - {name: component,      when: a deployable or logical part of the system}
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
seed_concepts: []
examples: []
```
