# Profile: concept graph (default)

**When to use:** a general-purpose wiki of *ideas and how they relate* — reading notes, a
research thread, a personal knowledge base — where you don't yet have a strong domain shape.
The thinnest useful ontology; let it grow via `/wiki-scaffold:evolve-schema`.

```yaml
spec_version: "1"
wiki_name: <your-wiki>
one_liner: A compounding graph of ideas in <domain> and how they relate.
raw_media: [note]
page_types:
  - {name: concept, location: concepts/<kebab>.md, role: one idea}
  - {name: source,  location: sources/<kebab>.md,  role: provenance for one note/article/talk}
kinds:
  - {name: concept,   when: a core idea or notion}
  - {name: principle, when: a rule of thumb or guideline}
  - {name: method,    when: a repeatable technique or practice}
relationships:
  - {verb: specializes, inverse: generalizes}
  - {verb: requires, inverse: required-by}
  - {verb: enables, inverse: enabled-by}
  - {verb: trades off against, symmetric: true}
frontmatter:
  concept: [type, kind, tags, sources, maturity]
  source:  [type, medium, title, year, tags]
operations: [ingest, query, lint]
seed_concepts: []
examples: []
```
