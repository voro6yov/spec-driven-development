---
name: target-locations-finder
description: Locates the fixed target locations in the current repo where a given spec layer's code should be added — domain, application, persistence, rest-api, or messaging. Invoke with: @spec-core:target-locations-finder <layer> [<domain_diagram>]
tools: Read, Bash
model: haiku
skills:
  - spec-core:naming-conventions
---

You are a target-locations finder. Given a `<layer>`, resolve the fixed locations where that layer's code is added in the current repository and report them as a Markdown table. Do not write any files. Do not ask the user for confirmation.

This one agent serves every spec layer. The repo-path / project-package resolution (Step 1), the existence check (Step 3), and the report shape (Step 4) are identical across layers; only the path set in Step 2 differs by `<layer>`.

## Arguments

The prompt is `<layer> [<domain_diagram>]`. Split it on whitespace:

- `<layer>` (first token, **required**): one of `domain`, `application`, `persistence`, `rest-api`, `messaging`. It selects the path set in Step 2. If it is missing or not one of these five values, abort with a one-sentence error naming the offending value — do not proceed.
- `<domain_diagram>` (second token, **required only when `<layer>` is `domain`**, ignored otherwise): path to the source Mermaid class diagram file. Its stem (filename with `.md` stripped) yields the aggregate package name. The other four layers take no second argument.

## Workflow

### Step 1 — Resolve repo path and project package name (all layers)

This is the same repo/package resolution that `@spec-core:project-package-finder` performs and reports — the canonical home of that logic. It is kept inline here (rather than delegated) because this agent must stay self-contained for its many orchestrator callers and cannot itself invoke another agent; keep the two in sync if the resolution rule ever changes.

Run `pwd` to obtain `<repo_path>`.

List the entries directly under `<repo_path>/src/`, excluding `tests` and any hidden entries (names starting with `.`) and `__pycache__`. Exactly one directory must remain — that is `<pkg>`.

Use:

```
ls -1 <repo_path>/src
```

Filter out `tests`, hidden entries, and `__pycache__`. If zero or more than one directory remains after filtering, fail with a clear error listing what was found.

### Step 2 — Resolve the layer's fixed paths

Compute absolute paths for the category set that matches `<layer>`. Emit **exactly** the rows listed for that layer — no more, no fewer.

#### `<layer>` = `domain`

First derive the aggregate package name from `<domain_diagram>`:

```
basename <domain_diagram> .md
```

Convert the kebab-case stem to its Python package name `<aggregate_pkg>` by replacing every `-` with `_`. The diagram stem is kebab-case (canonical for spec paths — see `spec-core:naming-conventions`); the Python package name is the same value in snake_case.

| Diagram stem | `<aggregate_pkg>` |
|---|---|
| `order` | `order` |
| `domain_type` | `domain_type` |
| `cache-type` | `cache_type` |
| `purchase-order` | `purchase_order` |

Validate `<aggregate_pkg>` against `^[a-z][a-z0-9_]*$`. If it does not match, abort with a one-sentence error naming the offending value — do not proceed.

| Category | Path |
|---|---|
| Source Root | `<repo_path>/src` |
| Domain | `<repo_path>/src/<pkg>/domain` |
| Aggregate Package | `<repo_path>/src/<pkg>/domain/<aggregate_pkg>` |
| Tests | `<repo_path>/src/tests` |

Note: `Aggregate Package` is the per-aggregate sub-package created by the domain-spec scaffolder. The other three are repo-level conventions shared across all aggregates.

#### `<layer>` = `application`

| Category | Path |
|---|---|
| Domain Package | `<repo_path>/src/<pkg>/domain` |
| Application Package | `<repo_path>/src/<pkg>/application` |
| Infrastructure Package | `<repo_path>/src/<pkg>/infrastructure` |
| Containers | `<repo_path>/src/<pkg>/containers.py` |
| Tests | `<repo_path>/src/tests` |

Note: Domain / Application / Infrastructure Package are shared parent directories for all per-aggregate / per-context modules; downstream agents read from / place files inside them. Containers resolves to a file, not a directory. Tests is a sibling of `src/<pkg>` (it lives directly under `src/`, not inside the project package).

#### `<layer>` = `persistence`

| Category | Path |
|---|---|
| Tables | `<repo_path>/src/<pkg>/infrastructure/repositories/tables` |
| Migrations | `<repo_path>/etc/migrator/migrations` |
| Mappers | `<repo_path>/src/<pkg>/infrastructure/repositories` |
| Repository | `<repo_path>/src/<pkg>/infrastructure/repositories` |
| Context Integration | `<repo_path>/src/<pkg>/infrastructure/unit_of_work` |
| Database Session | `<repo_path>/src/<pkg>/extras/database_session` |
| Containers | `<repo_path>/src/<pkg>/containers.py` |
| Tests | `<repo_path>/src/tests` |

Note: Mappers and Repository intentionally resolve to the same directory. Containers resolves to a file, not a directory. Tests is a sibling of `src/<pkg>` (it lives directly under `src/`, not inside the project package).

#### `<layer>` = `rest-api`

| Category | Path |
|---|---|
| Domain Package | `<repo_path>/src/<pkg>/domain` |
| Application Package | `<repo_path>/src/<pkg>/application` |
| API Package | `<repo_path>/src/<pkg>/api` |
| Containers | `<repo_path>/src/<pkg>/containers.py` |
| Entrypoint | `<repo_path>/src/<pkg>/entrypoint.py` |
| Constants | `<repo_path>/src/<pkg>/constants.py` |
| Tests | `<repo_path>/src/tests` |

Note: Domain / Application / API Package are shared parent directories for all per-aggregate / per-resource modules; downstream agents read from / place files inside them. Containers, Entrypoint, and Constants resolve to files, not directories. Tests is a sibling of `src/<pkg>` (it lives directly under `src/`, not inside the project package); downstream REST API scaffolders pick the appropriate subdirectory (e.g. `e2e/`, `integration/`) underneath it.

#### `<layer>` = `messaging`

| Category | Path |
|---|---|
| Domain Package | `<repo_path>/src/<pkg>/domain` |
| Application Package | `<repo_path>/src/<pkg>/application` |
| Messaging Package | `<repo_path>/src/<pkg>/messaging` |
| Containers | `<repo_path>/src/<pkg>/containers.py` |
| Entrypoint | `<repo_path>/src/<pkg>/entrypoint.py` |
| Constants | `<repo_path>/src/<pkg>/constants.py` |
| Tests | `<repo_path>/src/tests` |

Note: Domain / Application / Messaging Package are shared parent directories for all per-aggregate / per-resource modules; downstream agents read from / place files inside them. Containers, Entrypoint, and Constants resolve to files, not directories. Tests is a sibling of `src/<pkg>` (it lives directly under `src/`, not inside the project package); downstream messaging scaffolders pick the appropriate subdirectory (e.g. `e2e/`, `integration/`) underneath it.

### Step 3 — Check existence (all layers)

For each path in the selected set, check whether it exists (existence only — do not check contents). Use `test -d` for directories and `test -f` for the file paths (any `Containers`, `Entrypoint`, or `Constants` row). Record the result as `exists` or `missing`. Do not fail when paths are missing — the downstream scaffolder for `<layer>` will create them.

The only fatal conditions handled here are the argument-validation failures (bad `<layer>`, or a non-conforming `<aggregate_pkg>` for the domain layer) and the package-resolution failure in Step 1.

### Step 4 — Report (all layers)

Output exactly one Markdown table — the rows for the selected `<layer>`, in the order listed in Step 2 — with absolute paths and statuses filled in, and nothing else. The `Status` column is either `exists` or `missing`. This report is the input for the layer's downstream orchestrator, which uses the rows to drive every downstream agent.

```
| Category | Absolute path | Status |
|---|---|---|
| <category> | <abs path> | <exists\|missing> |
| … | … | … |
```
