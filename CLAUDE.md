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

## How the domain-spec pipeline works

The pipeline runs in two user-facing slash commands. Both fan out work to subagents in parallel where possible.

**`/generate-specs <diagram_file>`** (`skills/generate-specs/SKILL.md`):
1. Parse the Mermaid `classDiagram` to detect non-empty categories (data-structures, value-objects, domain-events, commands, aggregates, repositories-services).
2. Spawn `class-specifier` agents per category in parallel → spawn `pattern-assigner` agents per category in parallel → run `specs-merger` → `exceptions-specifier` → `aggregate-tests-planner`.
3. Outputs are written to **sibling files** of `<diagram_file>`: `<stem>.specs.md`, `<stem>.exceptions.md`, `<stem>.test-plan.md`. The diagram itself gets an Artifacts index appended.

**`/generate-code <domain_dir> <package_path> <diagram_file>`** (`skills/generate-code/SKILL.md`):
1. `package-preparer` → `test-package-preparer` → `scaffold-builder` → `exceptions-implementer` → parallel `code-implementer` per module → `aggregate-fixtures-writer` → `aggregate-tests-implementator`.
2. The aggregate package is created at `<domain_dir>/<package_path>`. Tests live at `<domain_dir>/tests` (sibling of the aggregate package, **inside** `<domain_dir>` — not its parent).

## Conventions when editing skills/agents

- **Argument indexing in skills:** orchestrator skills reference positional args as `$ARGUMENTS[0]`, `$ARGUMENTS[1]`, … When deriving derived paths, prefer simple concatenation (`$ARGUMENTS[0]/tests`) over shelling out to `dirname` — past bugs came from misderiving the project root.
- **Sibling-file convention:** spec/test artifacts always live next to `<diagram_file>` with a `<stem>.<kind>.md` name. Agents derive `<stem>` by stripping `.md`.
- **Parallelism:** when an orchestrator says "in parallel", emit all `Agent` calls in a single message. Sequential steps must wait for completion.
- **Bump `plugin.json` `version`** when changing user-visible behavior of a plugin.

## Common git workflow

The repo's main branch is `main`. There is no CI; changes are merged directly. Commit messages follow short conventional-style summaries (see `git log`).
