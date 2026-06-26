---
name: relationships
description: The typed, reciprocal relationship vocabulary that wires concepts together — the five verbs, their mirrors, the Dataview inline-field notation, and reciprocity enforcement (authoring + lint).
user-invocable: false
---

# Relationships

**Applies to:** `concepts/` (cross-cutting)

> Typed relationships are the **core value** of a {{DOMAIN}} KB — they encode the trade-offs and dependencies that "it depends" actually depends on. Every relationship is reciprocal: you wire **one** direction and `/lint` mirrors it. Use only the closed verb vocabulary below.

## Conventions

### The closed verb vocabulary

- **Rule:** Use exactly these five relationship verbs, recorded as Dataview inline fields in a concept's `## Relationships` section. Drop any row that doesn't apply; a row may list multiple targets.

  | Verb | Meaning | Mirror |
  |---|---|---|
  | `enables` | makes the other achievable | `enabled-by` |
  | `requires` | hard prerequisite | `required-by` |
  | `trades off against` | improving one degrades the other | *same* (symmetric) |
  | `alternative to` | competing choice for the same problem | *same* (symmetric) |
  | `specializes` | is-a more specific form of | `generalizes` |

- **Shape:**
  ```
  enables :: [[...]]
  requires :: [[...]]
  trades off against :: [[...]]
  alternative to :: [[...]]
  specializes :: [[...]]
  ```
- **Example:** `concepts/{{EXAMPLE_CONCEPT}}.md`.
- **Lint:** treat these five verbs (and the `:: ` inline-field syntax) as the closed, canonical vocabulary — do not flag them. Flag a relationship using a verb **outside** this set (e.g. `relates to`, `uses`) — normalize it to the closest canonical verb or surface it.

### Reciprocity

- **Rule:** Every relationship has its mirror on the target page. Symmetric verbs (`trades off against`, `alternative to`) use the **same verb** both sides. The inverse pairs are `enables`↔`enabled-by`, `requires`↔`required-by`, `specializes`↔`generalizes`. Wire only one direction during authoring; let `/lint` add the mirror.
- **Example:** `[[a]]` declares `enables :: [[b]]`; `[[b]]` carries the mirror `enabled-by :: [[a]]`. `[[a]]` and `[[c]]` each carry `alternative to` pointing at the other.
- **Lint (auto-fix):** for every relationship, add the missing mirror on the target page; if the target page doesn't exist yet, leave the one-directional link as a TODO and surface it (don't fabricate a page).

## Pitfalls

- **One-directional link.** `A enables B` with no `B enabled-by A`. The canonical state is reciprocal; `/lint` repairs it.
- **Wrong mirror verb.** Mirroring `requires` with `enables` instead of `required-by`. Use the inverse-pair table.
- **Freeform verbs.** Inventing `relates to`, `part of`, `uses`. Stay inside the five; if you genuinely need a new relationship type, propose it as a vocabulary change to this doc — don't smuggle it in.
- **Symmetric drift.** Writing a different verb on each side of a `trades off against` edge — symmetric verbs must read identically both ways.
