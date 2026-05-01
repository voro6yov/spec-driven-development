---
name: updates-report-template
description: Reference template for the updates report (`<stem>.updates.md`) emitted by `updates-detector`. Use when generating, parsing, or reviewing an updates report. Covers the rendered schema, rendering rules, the `## Affected Categories` footer specification, the canonical stereotype→category mapping, and the Mermaid stereotype-inference rules.
user-invocable: false
---

# Updates Report Template

> **Consumers:**
> - `updates-detector` agent — renders the report; uses the stereotype→category mapping and inference rules to compute the `## Affected Categories` footer.
> - Orchestrators that decide which downstream specifiers / pattern-assigners / planners to re-run — parse the footer to dispatch by category.

> **Scope of this skill:** output format only. Workflow (loading both versions of the diagram, splitting the Mermaid block, structural diffing, prose-section diffing, summary writing voice) lives in the `updates-detector` agent body.

---

## Schema

The report uses a fixed structure so consumers can parse it deterministically. Substitute every `<placeholder>` with the actual value when rendering.

````markdown
# Updates Report

_Baseline: git HEAD. Working tree compared against `HEAD:<diagram_file>`._

## Summary

- Classes: <N> added, <N> removed, <N> stereotype-changed
- Members: <N> changes across <N> classes
- Relationships: <N> added, <N> removed, <N> changed
- Description: <N> sections changed

## Class-Level Changes

### Added
- `ClassName` `<<Stereotype>>` — <N> attributes, <N> methods

### Removed
- `ClassName` `<<Stereotype>>`

### Stereotype Changed
- `ClassName`: `<<OldStereotype>>` → `<<NewStereotype>>`

## Member-Level Changes

### `ClassName`
- Attribute added: `+name: Type`
- Attribute removed: `-name: Type`
- Attribute changed: `name`: type `OldType` → `NewType`, visibility `+` → `-`
- Method added: `signature(...)`
- Method removed: `signature(...)`
- Method changed: `name`: `old(...)` → `new(...)`

## Relationship-Level Changes

### Added
- `A *-- "0..*" B : items`

### Removed
- `A --> B`

### Changed
- `A *-- B`: multiplicity `"1"` → `"0..*"`
- `A --> B`: label `": emits Old"` → `": emits New"`

## Description Prose Changes

### `<section heading>`

**Summary:** One-paragraph natural-language description of what changed in this section.

**Diff:**
```diff
- old line
+ new line
```

## Affected Categories

- `<category>`
````

---

## Rendering rules

- Every top-level section (`## Class-Level Changes`, `## Member-Level Changes`, `## Relationship-Level Changes`, `## Description Prose Changes`, `## Affected Categories`) is always emitted, even when empty.
- An empty top-level section contains the literal line `_None._` and nothing else.
- Sub-sections under `## Class-Level Changes` (`### Added`, `### Removed`, `### Stereotype Changed`) follow the same rule individually: emit the heading, then either the bullet list or `_None._`.
- Under `## Member-Level Changes`, only emit a `### \`ClassName\`` block for classes that have at least one member-level change. If no class has any member changes, the parent section contains `_None._`.
- Under `## Description Prose Changes`, only emit a `### \`<heading>\`` block for sections with a non-empty diff. The synthetic preamble section is rendered as `### Preamble` (no backticks). If no section changed, the parent contains `_None._`.
- The `Diff:` fenced block uses ```` ```diff ```` for syntax highlighting.
- For attribute-changed bullets, only include the deltas that actually differ (drop `, visibility ... → ...` if visibility is unchanged; drop `type ... → ...` if type is unchanged).
- If every count in the Summary bullet list is zero, replace the bullet list with the single literal line `No changes detected.`
- If HEAD had zero or >1 Mermaid blocks (degraded baseline), append the literal line `_warning: HEAD version had <count> Mermaid blocks; structural baseline treated as empty._` immediately after the Summary bullet list (or after the `No changes detected.` line).

---

## `## Affected Categories` computation

The footer lists every category that has at least one structural or prose change. It is the orchestrator's primary dispatch input — consumers should be able to skip parsing the rest of the report and still pick the right specifiers to re-run.

Compute as follows:

1. Start with an empty set of affected categories.
2. **Structural contributions** — for every class that appears in `## Class-Level Changes` (Added / Removed / Stereotype Changed) or has any entry under `## Member-Level Changes`:
   - For added classes, use the **new** stereotype.
   - For removed classes, use the **old** stereotype.
   - For stereotype-changed classes, use **both** the old and new stereotypes (a stereotype change implies both source and destination categories must regenerate).
   - For member-level changes, use the working-tree stereotype.
   - Apply the stereotype → category mapping below; if no explicit stereotype is present, apply the inference rules. Add the resulting category to the set.
3. **Relationship contributions** — for every entry under `## Relationship-Level Changes` (Added / Removed / Changed):
   - Look up the stereotype of the **source** class in the working-tree diagram (or HEAD diagram for removed-only relationships).
   - Apply the mapping; add the resulting category to the set.
4. **Prose contributions** — for every section heading under `## Description Prose Changes` (other than `Preamble`):
   - Parse the heading into a class name. Heading forms supported:
     - `ClassName` (whole-class invariants),
     - `ClassName.method_name` (method-level invariants),
     - `ClassName.method_name(...)` (with parameter list).
   - If the parsed class name matches a class in the working-tree diagram, look up its stereotype and apply the mapping.
   - If the heading does not parse to a known class (e.g. free-form sections like `Notes` or `Glossary`), skip — these do not contribute to category dispatch.
5. Render the affected categories as a bullet list in the **canonical category order** (see below). If the set is empty, render `_None._`.

### Canonical category order

When listing categories anywhere in the report, use this sequence — it matches the order `generate-specs` fans out specifiers in:

1. `data-structures`
2. `value-objects`
3. `domain-events`
4. `commands`
5. `aggregates`
6. `repositories-services`

---

## Stereotype → category mapping

| Stereotype | Category |
|---|---|
| `<<TypedDict>>` | `data-structures` |
| `<<Value Object>>` | `value-objects` |
| `<<Event>>` | `domain-events` |
| `<<Command>>` | `commands` |
| `<<Aggregate Root>>` | `aggregates` |
| `<<Entity>>` | `aggregates` |
| `<<Repository>>` | `repositories-services` |
| `<<Service>>` | `repositories-services` |

A class with no explicit stereotype contributes a category only if a stereotype-inference rule (below) applies; otherwise it is skipped from category dispatch (the class still appears in the structural diff sections, just not in the footer).

---

## Mermaid stereotype-inference rules

For classes referenced in the diagram that have no explicit `<<Stereotype>>` annotation:

- A class targeted by a `-->` relationship whose label contains `: emits ...` is inferred as `<<Event>>` (category: `domain-events`).
- A class targeted by a `--()` relationship whose label contains `: emits ...` is inferred as `<<Command>>` (category: `commands`).

These rules apply only to category dispatch and footer computation. They do not promote a class without an explicit `class` block in the diagram to receiving a class-spec entry — that decision is owned by `class-specifier`.
