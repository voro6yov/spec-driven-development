---
name: sections-and-files
description: Diagram framing and the stem-keyed file set — mermaid front-matter (title + hideEmptyMembersBox), trailing ## Implementation/## Artifacts, the .md/.commands/.queries/.ops file set, and snake_case package derivation. Authoring + review.
user-invocable: false
---

# Sections & file layout

**Applies to:** all diagram kinds (`<stem>.md`, `<stem>.commands.md`, `<stem>.queries.md`, `<stem>.ops.<service>.md`) + the per-aggregate file set

> This theme governs the non-Mermaid scaffolding around a diagram: how each file is fenced and titled, which trailing prose sections each file kind carries, what set of stem-keyed files an aggregate owns, and how the on-disk Python package is derived from the stem. It is about file framing, not about the classes inside the diagram.

## Ground knowledge

*Why the file/package layout is shaped the way it is — the modeling principles behind it, and which mechanics are pure tooling. Names and sources let a reviewer cite the principle behind a suppression rather than assert it.*

- **Package-from-stem = Model-Driven Design** (Evans, *DDD* ch.5 "A Model Expressed in Software"; Vernon, *IDDD* ch.9). "Each domain concept is reflected in an element of implementation"; `src/<repo_pkg>/domain/<snake_stem>` matches Vernon's `<org>.<context>.domain.model.<concept>` module convention (`.domain` = the layer, the leaf segment = the aggregate concept). The `-`→`_` transform is the model-to-code binding, so a wrong/copy-pasted leaf segment is a model defect, not a typo.
- **Keying the whole file/package set off one aggregate stem = packaging by the model** (Evans/Vernon — Module): it keeps one conceptual object's code together and is the deliberate opposite of the warned "partition by pattern" anti-pattern (all-entities-here, all-values-there), where "the packages tell the story of what the developer was reading, not the story of the domain."
- **`.queries.md` is bare because reads are side-effect-free** (Meyer's CQS; Design by Contract): there is no state change to assert, so the absence of `## Invariants` on the query file is *derivable*, not an arbitrary house rule.
- **Coverage note:** the pure-tooling mechanics — the ` ```mermaid ` fence, YAML front-matter, `hideEmptyMembersBox: true`, the dot-vs-hyphen role separator, the sibling `## Implementation`/`## Artifacts` exclusion — have no DDD grounding and correctly remain file-framing conventions.

## Conventions

### Fenced mermaid block with YAML front-matter

- **Rule:** Wrap every diagram in a single ` ```mermaid ` fence. The first lines inside the fence are a YAML front-matter block (delimited by `---` … `---`) that sets a `title` and `config.class.hideEmptyMembersBox: true`. Follow the closing `---` immediately with the `classDiagram` keyword. Apply this identically to the domain file, the `.commands.md` / `.queries.md` siblings, and every `.ops.<service>.md` sibling.
- **Notation:**
  ```
  ```mermaid
  ---
  title: CacheType
  config:
    class:
      hideEmptyMembersBox: true
  ---
  classDiagram
    class CacheType {
      <<Aggregate Root>>
      ...
    }
  ```
  ```
- **Example:** `title: CacheType` with `hideEmptyMembersBox: true` — from `cache-type.md`. The ops file `ruleset.ops.mapping-rules-inference.md` carries the identical header shape with `title: MappingRulesInference`.
- **You may:** set the `title` to **either** the PascalCase class/service name (`CacheType`, `RulesetCommands`, `MappingsInference`) **or** a spaced human-readable prose phrase derived from it (`Domain Type Domain Model`, `Conversion Requirements Commands`) — both styles are sanctioned; pick one and keep it consistent across an aggregate's files. You may also leave a blank line between the closing front-matter `---` and `classDiagram` (cosmetic).
- **Review:** when reviewing a diagram, treat both `title` styles as canonical — do **not** flag a prose-phrase title as "should be the PascalCase class name", and do not flag a PascalCase title either. The load-bearing requirement is that the front-matter is present with `title` + `hideEmptyMembersBox: true` and is immediately inside the ` ```mermaid ` fence; only flag if the front-matter, the `title` key, or the `hideEmptyMembersBox: true` line is missing. Do not flag the optional blank line before `classDiagram`.

### Domain file closes with `## Implementation` then `## Artifacts`

- **Rule:** Close the domain `<stem>.md` (after the mermaid fence) with a `## Implementation` block giving the on-disk Package path `src/<repo_pkg>/domain/<snake_stem>` and the dotted Import path `<repo_pkg>.domain.<snake_stem>`, then a `## Artifacts` block of relative markdown links to the sibling spec files (`<stem>.domain/{specs,exceptions,test-plan}.md` and `<stem>.persistence/command-repo-spec.md`). Do not add these two sections to the `.commands.md` / `.queries.md` / `.ops.<service>.md` siblings — they omit both.
- **Notation:**
  ```
  ## Implementation

  - Package: `src/stps_templates/domain/cache_type`
  - Import path: `stps_templates.domain.cache_type`

  ## Artifacts

  - [Class Specification](cache-type.domain/specs.md)
  - [Domain Exceptions](cache-type.domain/exceptions.md)
  - [Test Plan](cache-type.domain/test-plan.md) *(generated by aggregate-tests-planner)*
  - [Command Repository Spec](cache-type.persistence/command-repo-spec.md)
  ```
- **Example:** `- Package: `src/stps_mappings/domain/ruleset`` with a 4-link `## Artifacts` block — from `ruleset.md`.
- **You may:** omit both sections entirely on a **structural-only, never-pipeline-run** domain diagram (the diagram ends right after the mermaid fence). These sections are normally written back by `/generate-code`, so an authored-but-not-yet-generated diagram legitimately lacks them.
- **Review:** treat the trailing `## Implementation` + `## Artifacts` pair as canonical on a pipeline-generated domain file — do not flag their presence, the Package/Import path shape, or the relative sibling-link Artifacts list. Equally, do **not** flag a structural-only domain file for *lacking* these sections; a bare diagram with no trailing prose is a valid not-yet-generated state, not a defect. Never propose adding `## Implementation`/`## Artifacts` to a `.commands`/`.queries`/`.ops` sibling — they correctly omit both.

### Three stem-keyed core files: `<stem>.md`, `<stem>.commands.md`, `<stem>.queries.md`

- **Rule:** Key the file set off a single kebab-case stem matching `^[a-z][a-z0-9-]*$` (derived from the aggregate root). Author three core files: the domain diagram `<stem>.md`, and the application-service siblings `<stem>.commands.md` and `<stem>.queries.md`. Use a **dot** before the role suffix, never a hyphen. The siblings carry `<<Application>>` `<Aggregate>Commands` / `<Aggregate>Queries` classes; keep all three files present even when a sibling is empty.
- **Notation:**
  ```
  cache-type.md            # <stem>.md           — domain diagram
  cache-type.commands.md   # <stem>.commands.md  — <<Application>> CacheTypeCommands
  cache-type.queries.md    # <stem>.queries.md   — <<Application>> CacheTypeQueries
  ```
- **Example:** `ruleset.md` + `ruleset.commands.md` (`<<Application>> RulesetCommands`) + `ruleset.queries.md` (`<<Application>> RulesetQueries`) — from the `ruleset/` doc folder.
- **You may:** leave the `.commands.md` / `.queries.md` siblings as bare stubs (front-matter + a lone `classDiagram` keyword, no classes) **only** for a never-generated aggregate — e.g. `mapping.commands.md` titled `MappingCommands` holding nothing but the header.
- **Review:** treat the dot-separated three-file set as canonical — do not flag `<stem>.commands.md` / `<stem>.queries.md` naming, and do not propose a hyphen (`<stem>-commands.md`) variant. Do not flag an empty `<<Application>>` sibling stub as "missing service definition" when the aggregate is structural-only; the stub-present state is the sanctioned not-yet-generated form.

### Ops files: `<stem>.ops.<service>.md` (N per aggregate)

- **Rule:** Model a free-form orchestration / inference application service — one that is neither a `Commands` nor a `Queries` service — as an **additional** sibling file named `<stem>.ops.<service>.md`, with the service name (kebab-case) embedded after the `.ops.` token. Author one file per ops service (N per aggregate). Each holds a single `<<Application>>` orchestration class that consumes domain events via `on_<event>` handlers and injects collaborator ports. These files carry their own front-matter and their own trailing `## Invariants` prose, but no `## Implementation` / `## Artifacts`.
- **Notation:**
  ```
  ruleset.ops.mapping-rules-inference.md   # <<Application>> MappingRulesInference
  ruleset.ops.mappings-inference.md        # <<Application>> MappingsInference
  ```
- **Example:** `ruleset.ops.mapping-rules-inference.md`, whose `MappingRulesInference` class draws `MappingRulesInference --() ICanManageRuleset : uses` and `MappingRulesInference --() RulesetFilesAdded : handles (Ruleset, on_ruleset_files_added)` — from `ruleset.ops.mapping-rules-inference.md`.
- **You may:** author zero ops files (most aggregates have none) or any number N — add a separate `<stem>.ops.<service>.md` per orchestration service rather than packing several into one file.
- **Review:** treat `<stem>.ops.<service>.md` as a canonical fourth file kind — do not flag it as a non-standard filename or as "should be folded into commands/queries". Recognize the ops `<<Application>>` class's heavier injected-collaborator surface (`<<Service>>` inferrers + `<<Interface>>` `ICan*` ports drawn via `--() : uses`) as expected. Note that ops `handles` edges use the lollipop form `--() <Event> : handles (<Context>, on_<event>)`, whereas the `.commands.md` sibling uses the association form `--> <Event> : handles (<Context>, on_<event>)` for the same conceptual edge — accept **both** arrow styles; do not flag the lollipop/association difference on a `handles` edge. Do not flag an ops file for lacking `## Implementation`/`## Artifacts`.

### snake_case package derivation from the kebab stem

- **Rule:** Derive the Python package mechanically from the kebab-case stem by replacing each `-` with `_`. The `## Implementation` Package path is `src/<repo_pkg>/domain/<snake_stem>` and the Import path is `<repo_pkg>.domain.<snake_stem>`, where `<repo_pkg>` is the owning repository's package.
- **Notation:**
  ```
  stem:    cache-type
  package: src/stps_templates/domain/cache_type
  import:  stps_templates.domain.cache_type
  ```
- **Example:** `mapping-rule` → Package `src/stps_mappings/domain/mapping_rule`, Import `stps_mappings.domain.mapping_rule` — from `mapping-rule.md`.
- **You may:** resolve `<repo_pkg>` to any owning-repo package (`stps_templates`, `stps_projects`, `stps_mappings`, …) — the segment is fixed by the repo the aggregate lives in, not by the stem. A structural-only diagram with no `## Implementation` block has no derived package and that is fine.
- **Review:** treat the literal `-`→`_` transform as canonical — do not flag `cache_type` as a mismatch against the `cache-type` stem; the divergence between kebab filename and snake package is intentional and mechanical. Do not flag the repo-package segment for differing across aggregates.

### Per-file trailing-prose placement: `## Invariants` on domain + commands; queries bare

- **Rule:** Place trailing `## Invariants` prose by file kind. The domain `<stem>.md` carries the aggregate-and-method invariants. The `.commands.md` sibling carries its own per-command `## Invariants` (the lookup-or-raise → call → save → publish flow). The `.queries.md` sibling ends at the mermaid fence with **no** trailing prose. Each `.ops.<service>.md` file carries its own `## Invariants`.
- **Notation:**
  ```
  <stem>.md            → mermaid fence + ## Invariants + ## Implementation + ## Artifacts
  <stem>.commands.md   → mermaid fence + ## Invariants
  <stem>.queries.md    → mermaid fence only (no trailing prose)
  <stem>.ops.<svc>.md  → mermaid fence + ## Invariants
  ```
- **Example:** `ruleset.md` carries a long `## Invariants` block (the `### Status` / `### Ruleset` / `### Files` method specs); `ruleset.queries.md` ends with its `RulesetQueries.find_ruleset_by_process` flow under `## Invariants` — note the queries file's per-method flow lives under that single `## Invariants` heading and the file otherwise carries no aggregate-level prose. The bare-queries norm holds across the corpus.
- **You may:** author a structural-only domain diagram with **no** `## Invariants` at all (and stub siblings) when the diagram alone is meant to carry the contract — this is the only form that legitimately omits invariant prose everywhere.
- **Review:** treat the placement as canonical — do not flag a `.queries.md` file for "missing invariants" when it ends at the fence (bare queries is the norm), and do not flag the domain + commands files for *carrying* `## Invariants`. Do not flag a structural-only diagram for carrying zero trailing prose anywhere.

## Pitfalls

- **Hyphen before the role suffix.** Write `cache-type.commands.md`, not `cache-type-commands.md`. The stem is kebab-case but the role/ops separator is always a dot.
- **Forgetting `hideEmptyMembersBox: true`.** The front-matter must set this under `config.class`; a diagram missing it (or missing the whole front-matter block) is non-conforming even if the `classDiagram` body is fine.
- **`classDiagram` outside the fence or before the front-matter.** The order is fixed: ` ```mermaid ` → front-matter `---`…`---` → `classDiagram` → classes. Do not place `classDiagram` above the front-matter.
- **Putting `## Implementation`/`## Artifacts` on a sibling.** Only `<stem>.md` gets those two sections. Never append them to `.commands.md`, `.queries.md`, or `.ops.<service>.md`.
- **Deriving the package without the `-`→`_` swap, or hand-typing a snake stem that drifts from the kebab filename.** The Package/Import paths are a literal transform of the stem; a copy-paste from a sibling aggregate (wrong `<snake_stem>` or wrong `<repo_pkg>`) is the classic error.
- **Adding trailing prose to `.queries.md` to "match" the domain/commands files.** Queries files are deliberately bare past the fence (aside from per-method query flows under a single `## Invariants` where present); do not pad them with aggregate-level invariant prose to mirror the other files.
- **Packing multiple ops services into one file.** Each orchestration service is its own `<stem>.ops.<service>.md`; do not co-locate two `<<Application>>` ops classes in a single ops file.
