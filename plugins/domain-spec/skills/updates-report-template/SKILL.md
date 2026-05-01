---
name: updates-report-template
description: Reference template for the updates report (`<stem>.updates.md`) emitted by `updates-detector`. Use when generating, parsing, or reviewing an updates report. Covers the rendered schema (class-grouped body), rendering rules, the `## Affected Categories` footer specification, the canonical stereotype→category mapping, and the Mermaid stereotype-inference rules.
user-invocable: false
---

# Updates Report Template

> **Consumers:**
> - `updates-detector` agent — renders the report; uses the stereotype→category mapping and inference rules to compute the `## Affected Categories` footer.
> - Orchestrators that decide which downstream specifiers / pattern-assigners / planners to re-run — parse the footer to dispatch by category.

> **Scope of this skill:** output format only. Workflow (loading both versions of the diagram, splitting the Mermaid block, structural diffing, prose-section diffing, summary writing voice) lives in the `updates-detector` agent body.

---

## Schema

The report is **class-grouped**: a slim header captures cross-cutting lifecycle events (added / removed / stereotype-changed classes), and the body emits one `### \`ClassName\`` block per touched class consolidating its member changes, its outgoing relationship changes, and its prose changes. Substitute every `<placeholder>` with the actual value when rendering.

````markdown
# Updates Report

_Baseline: git HEAD. Working tree compared against `HEAD:<diagram_file>`._

## Summary

- Classes: <N> added, <N> removed, <N> stereotype-changed
- Members: <N> changes across <N> classes
- Relationships: <N> added, <N> removed, <N> changed
- Description: <N> sections changed

## Class Lifecycle

### Added
- `ClassName` `<<Stereotype>>` — <N> attributes, <N> methods

### Removed
- `ClassName` `<<Stereotype>>`

### Stereotype Changed
- `ClassName`: `<<OldStereotype>>` → `<<NewStereotype>>`

## Per-Class Changes

### `ClassName` `<<Stereotype>>`

**Members:**
- Attribute added: `+name: Type`
- Attribute removed: `-name: Type`
- Attribute changed: `name`: type `OldType` → `NewType`, visibility `+` → `-`
- Method added: `signature(...)`
- Method removed: `signature(...)`
- Method changed: `name`: `old(...)` → `new(...)`

**Relationships (outgoing):**
- Added: `ClassName *-- "0..*" B : items`
- Removed: `ClassName --> B`
- Changed: `ClassName *-- B`: multiplicity `"1"` → `"0..*"`
- Changed: `ClassName --> B`: label `": emits Old"` → `": emits New"`

**Prose — `<section heading>`:**

Summary: One-paragraph natural-language description of what changed in this section.

Diff:
```diff
- old line
+ new line
```

## Orphan Relationship Changes

- Added: `A *-- "0..*" B : items`
- Removed: `A --> B`
- Changed: `A *-- B`: multiplicity `"1"` → `"0..*"`

## Orphan Prose Changes

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

### Top-level sections

- Every top-level section (`## Class Lifecycle`, `## Per-Class Changes`, `## Orphan Relationship Changes`, `## Orphan Prose Changes`, `## Affected Categories`) is always emitted, even when empty.
- An empty top-level section contains the literal line `_None._` and nothing else.

### `## Class Lifecycle`

- Sub-sections (`### Added`, `### Removed`, `### Stereotype Changed`) follow the same rule individually: emit the heading, then either the bullet list or `_None._`.

### `## Per-Class Changes`

- Emit one `### \`ClassName\` \`<<Stereotype>>\`` block per class that has at least one of: a member-level change, an outgoing relationship change, or a prose change keyed to it. Order classes alphabetically by name.
- A class may appear in **both** `## Class Lifecycle` and `## Per-Class Changes` — this is expected, not redundant. An added class's new outgoing relationships, a removed class's removed outgoing relationships, and any prose change attributable to a stereotype-changed class all surface in the per-class block. The lifecycle entry records the class-level event; the per-class block records its surrounding structural detail.
- Use the **working-tree** stereotype in the heading. For a class that exists only in HEAD (i.e. has prose or relationship changes attributable to it but was removed in the working tree), use the HEAD stereotype.
- Within a class block, emit only the sub-sections that have content. Sub-section order is fixed: **Members**, then **Relationships (outgoing)**, then one **Prose — `<heading>`** sub-section per changed prose section keyed to this class. Do not emit empty sub-sections, and do not emit `_None._` placeholders inside a class block.
- Sub-section labels (`**Members:**`, `**Relationships (outgoing):**`, `**Prose — \`<heading>\`:**`) are rendered in **bold** as shown in the schema.
- For attribute-changed bullets, only include the deltas that actually differ (drop `, visibility ... → ...` if visibility is unchanged; drop `type ... → ...` if type is unchanged).
- A relationship belongs to a class block when the class is the **source** of the relationship. Relationships whose source class has no other changes still pull that class into `## Per-Class Changes` (the block will contain only the **Relationships (outgoing)** sub-section).
- A prose section belongs to a class block when its heading parses to that class name (forms: `ClassName`, `ClassName.method_name`, or `ClassName.method_name(...)`). The full original heading text is preserved in the **Prose — `<heading>`** sub-section label.
- Inside a **Prose** sub-section, the `Summary:` and `Diff:` labels are rendered as plain `Summary:` / `Diff:` lines (not bolded) to keep the nested formatting flat. The diff fenced block uses ```` ```diff ````.

### `## Orphan Relationship Changes`

- Houses relationship changes whose **source** class is not present in either version's class map (e.g. classes referenced only via relationships, or `emits` targets without an explicit `class` block). Such changes have no class block to nest under.
- Emit as a flat bullet list using the same `Added: ...` / `Removed: ...` / `Changed: ...` prefixes used inside class blocks.

### `## Orphan Prose Changes`

- Houses prose section changes whose heading does not parse to a known class — including the synthetic `Preamble` section and free-form sections like `Notes` or `Glossary`.
- The synthetic preamble section is rendered as `### Preamble` (no backticks). Other orphan headings are rendered as `### \`<heading>\`` verbatim.
- Inside an orphan prose block, use the bolded `**Summary:**` / `**Diff:**` labels (top-level form) since these blocks are not nested inside a class.

### Summary section

- If every count in the Summary bullet list is zero, replace the bullet list with the single literal line `No changes detected.`
- If HEAD had zero or >1 Mermaid blocks (degraded baseline), append the literal line `_warning: HEAD version had <count> Mermaid blocks; structural baseline treated as empty._` immediately after the Summary bullet list (or after the `No changes detected.` line).

---

## `## Affected Categories` computation

The footer lists every category that has at least one structural or prose change. It is the orchestrator's primary dispatch input — consumers should be able to skip parsing the rest of the report and still pick the right specifiers to re-run.

Compute as follows:

1. Start with an empty set of affected categories.
2. **Lifecycle contributions** — for every class listed under `## Class Lifecycle`:
   - For added classes, use the **new** stereotype.
   - For removed classes, use the **old** stereotype.
   - For stereotype-changed classes, use **both** the old and new stereotypes (a stereotype change implies both source and destination categories must regenerate).
   - Apply the stereotype → category mapping below; if no explicit stereotype is present, apply the inference rules. Add the resulting category to the set.
3. **Per-class contributions** — for every class block under `## Per-Class Changes`:
   - Use the working-tree stereotype (or HEAD stereotype if the class exists only in HEAD).
   - Apply the mapping; add the resulting category.
   - This single rule covers member-level changes, outgoing relationship changes attributable to the class, and prose changes keyed to the class.
4. **Orphan relationship contributions** — for every entry under `## Orphan Relationship Changes`:
   - Look up the stereotype of the **source** class in the working-tree diagram (or HEAD diagram for removed-only relationships) if a class entry exists for it; otherwise apply the stereotype-inference rules below.
   - Apply the mapping; add the resulting category.
5. **Orphan prose contributions** — entries under `## Orphan Prose Changes` (including `Preamble`) do **not** contribute to category dispatch — they are by definition not attributable to a known class.
6. Render the affected categories as a bullet list in the **canonical category order** (see below). If the set is empty, render `_None._`.

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

A class with no explicit stereotype contributes a category only if a stereotype-inference rule (below) applies; otherwise it is skipped from category dispatch (the class still appears in the structural sections, just not in the footer).

---

## Mermaid stereotype-inference rules

For classes referenced in the diagram that have no explicit `<<Stereotype>>` annotation:

- A class targeted by a `-->` relationship whose label contains `: emits ...` is inferred as `<<Event>>` (category: `domain-events`).
- A class targeted by a `--()` relationship whose label contains `: emits ...` is inferred as `<<Command>>` (category: `commands`).

These rules apply only to category dispatch and footer computation. They do not promote a class without an explicit `class` block in the diagram to receiving a class-spec entry — that decision is owned by `class-specifier`.
