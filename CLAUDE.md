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

`plugins/spec-core` is a base plugin that owns conventions shared across every spec plugin. Today it ships exactly one skill, `spec-core:naming-conventions` — the single source of truth for the aggregate stem, diagram filenames, per-plugin sibling-folder layout, path-resolution tables, and the numbered Path-hygiene rules. The five spec plugins (`domain-spec`, `application-spec`, `persistence-spec`, `rest-api-spec`, `messaging-spec`) and `model-diagrams` all reference it as `spec-core:naming-conventions` — in agent frontmatter `skills:` lists and in prose — rather than each carrying their own copy.

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
- **Pattern docs live under a per-plugin `patterns` umbrella skill (domain-spec, persistence-spec, application-spec, messaging-spec):** reference docs are supporting files at `skills/patterns/<name>/index.md` (+ `template.md`/`examples.md` companions where present), not standalone skills. Consumers frontmatter-load `<plugin>:patterns` and Read `<patterns_dir>/<name>/index.md`; never re-register a pattern as its own skill. Pattern identifiers in specs/briefs keep the `<plugin>:<name>` token form. Cross-plugin-consumed refs are **dual-homed** until Wave 3: the standalone skill stays registered (authoritative — foreign plugins load it); its umbrella copy must be re-synced byte-identically after any edit. Dual-homed sets: domain-spec — `aggregate-fixtures`, `collection-value-objects`, `constructor-guard-type-mapping`, `domain-exceptions`, `flat-constructor-arguments`, `optional-values`, `package-layout`, `updates-report-template`; persistence-spec — `persistence-fixtures`, `unit-of-work` (consumed by messaging-spec); application-spec — `application-updates-report-template`, `fake-implementations`, `fake-override-fixtures`, `ops-updates-report-template`, `services-report-template` (consumed by messaging-spec, rest-api-spec, and domain-spec). **messaging-spec has NO dual-homed twins** — it consumes other plugins' shared refs but owns no reference skill that another plugin consumes, so its Wave-1 demotion is pure intra-plugin: all 15 reference skills were *moved* into the umbrella (zero ✦ rows, no byte-sync obligation; the umbrella copies are the sole copies).
- **Bump `plugin.json` `version`** when changing user-visible behavior of a plugin.

## Common git workflow

The repo's main branch is `main`. There is no CI; changes are merged directly. Commit messages follow short conventional-style summaries (see `git log`).
