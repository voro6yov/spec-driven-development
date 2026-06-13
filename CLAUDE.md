# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository purpose

This is a **Claude Code plugin marketplace** (`.claude-plugin/marketplace.json`) that ships two plugins:

- `plugins/domain-spec` — generates DDD class specs from a Mermaid class diagram, then implements the domain package and its unit tests
- `plugins/adr-log` — guides creation of ADRs through the advice process

There is no application code, no build step, and no test suite. Artifacts are Markdown — skills, agent definitions, and plugin manifests — that are loaded by Claude Code at runtime.

## Plugin layout

Each plugin under `plugins/<name>/` has:

- `.claude-plugin/plugin.json` — plugin manifest with `version` (bump on user-visible changes)
- `agents/*.md` — single-purpose subagents with frontmatter (`name`, `description`, `tools`, optional `model`)
- `skills/<skill>/SKILL.md` — reusable skills; orchestrator skills (e.g. `generate-specs`, `generate-code`) coordinate multiple agents

`plugins/domain-spec/modules/shared/` contains Python reference modules (Entity, ValueObject, guards, etc.) that the generated domain code imports — not source for this repo to test, but the runtime contract that `code-implementer` targets.

## Shared conventions (`spec-core`)

`plugins/spec-core` is a base plugin that owns conventions and agents shared across every spec plugin. It ships:

- **One skill, `spec-core:naming-conventions`** — the single source of truth for the aggregate stem, diagram filenames, per-plugin sibling-folder layout, path-resolution tables, and the numbered Path-hygiene rules. The five spec plugins (`domain-spec`, `application-spec`, `persistence-spec`, `rest-api-spec`, `messaging-spec`) and `model-diagrams` all reference it as `spec-core:naming-conventions` — in agent frontmatter `skills:` lists and in prose — rather than each carrying their own copy.
- **One agent, `spec-core:target-locations-finder`** — the single shared resolver of where each layer's code lives in the target repo. It takes `<layer> [<domain_diagram>]` (`layer` ∈ `domain`/`application`/`persistence`/`rest-api`/`messaging`; the `domain` layer also takes the diagram, to derive the aggregate sub-package) and emits the layer's category→path→status table. It replaced five near-identical per-plugin `target-locations-finder` agents (the skeleton — repo/package resolution, existence check, report shape — was byte-identical; only the per-layer path set and the domain diagram-derivation branch differed). Every orchestrator (each plugin's `code-generator`, the `init-*`/`generate-*` skills, and `domain-spec:update-code`'s five-way parallel fan-out) invokes it with the layer token; downstream worker agents still receive the report verbatim as `<locations_report_text>` and must not re-run it. When consolidating another per-plugin agent clone, home it here the same way.

**Dependency caveat:** there is no manifest-level dependency mechanism in `plugin.json`/`marketplace.json`, so this is an unenforced runtime assumption — every spec plugin requires `spec-core` to be enabled. The marketplace ships them together, but a subset install that omits `spec-core` will leave `spec-core:naming-conventions` unresolved: frontmatter auto-load fails silently, and an explicit Skill/agent invocation fails hard. When adding a new shared, cross-plugin convention, home its skill in `spec-core` and reference it by that namespace; do not re-duplicate it per plugin.

## How the domain-spec pipeline works

The pipeline runs in two user-facing slash commands. Both fan out work to subagents in parallel where possible.

**`/generate-specs <diagram_file>`** (`skills/generate-specs/SKILL.md`):
1. Parse the Mermaid `classDiagram` to detect non-empty categories (data-structures, value-objects, domain-events, commands, aggregates, repositories-services).
2. Spawn `class-specifier` agents per category in parallel → spawn `pattern-assigner` agents per category in parallel → run `specs-merger` → `exceptions-specifier` → `aggregate-tests-planner`.
3. Outputs are written to **sibling files** of `<diagram_file>`: `<stem>.specs.md`, `<stem>.exceptions.md`, `<stem>.test-plan.md`. The diagram itself gets an Artifacts index appended.

**`/generate-code <domain_dir> <package_path> <diagram_file>`** (`skills/generate-code/SKILL.md`):
1. `package-preparer` → `test-package-preparer` → `scaffold-builder` → `exceptions-implementer` → parallel `code-implementer` per module → `aggregate-fixtures-writer` → `aggregate-tests-implementator`.
2. The aggregate package is created at `<domain_dir>/<package_path>`. Tests live at `<source_root>/tests`, where `<source_root>` is computed by walking upward from the aggregate package while each parent has an `__init__.py`; the parent of the topmost `__init__.py`-bearing directory is the source root.

## Conventions when editing skills/agents

- **Argument indexing in skills:** orchestrator skills reference positional args as `$ARGUMENTS[0]`, `$ARGUMENTS[1]`, … When deriving derived paths, prefer simple concatenation (`$ARGUMENTS[0]/tests`) over shelling out to `dirname` — past bugs came from misderiving the project root.
- **Sibling-file convention:** spec/test artifacts always live next to `<diagram_file>` with a `<stem>.<kind>.md` name. Agents derive `<stem>` by stripping `.md`.
- **Parallelism:** when an orchestrator says "in parallel", emit all `Agent` calls in a single message. Sequential steps must wait for completion.
- **Pattern docs live under a per-plugin `patterns` umbrella skill (domain-spec, persistence-spec, application-spec, messaging-spec, rest-api-spec):** reference docs are supporting files at `skills/patterns/<name>/index.md` (+ `template.md`/`examples.md` companions where present), not standalone skills. Consumers frontmatter-load `<plugin>:patterns` and Read `<patterns_dir>/<name>/index.md`; never re-register a pattern as its own skill. Pattern identifiers in specs/briefs keep the `<plugin>:<name>` token form. Cross-plugin-consumed refs were **dual-homed** during Wave 1; **Wave 3-A (2026-06-14) deregistered the 14 twins that foreign plugins only *cite in prose/table cells*** — a 16-agent usage audit proved those are never frontmatter- or dynamically-loaded across plugins, so their foreign tokens are provenance vocabulary that resolves to the surviving umbrella copy (exactly like a Wave-1-demoted intra token). For those 14 the umbrella copy (`skills/patterns/<name>/index.md`) is now the **sole** copy — no byte-sync obligation. **Two dual-homed twins remain, both domain-spec:** `domain-exceptions` (foreign **frontmatter-load** by application-spec's `application-exceptions-specifier` + `exceptions-implementer`, plus a dynamic `Skill`-load in `code-change-writer`) and `updates-report-template` (foreign **frontmatter-load** by persistence-spec's `query-code-change-writer` + `command-repo-spec-migrations-appender`). These two stay registered (authoritative; umbrella copy re-synced byte-identically on edit) until **Wave 3-B** rewires those four loaders to `domain-spec:patterns` + an explicit Read, then deregisters them. persistence-spec, application-spec, and **messaging-spec now carry NO dual-homed twins**; rest-api-spec's former twin `surface-markers` was among the 14 deregistered, but rest-api-spec still owns the **only multi-file reference outside domain-spec** (`endpoint-io-template` + its `examples.md` companion — an intact directory under its umbrella).
- **Bump `plugin.json` `version`** when changing user-visible behavior of a plugin.

## Common git workflow

The repo's main branch is `main`. There is no CI; changes are merged directly. Commit messages follow short conventional-style summaries (see `git log`).
