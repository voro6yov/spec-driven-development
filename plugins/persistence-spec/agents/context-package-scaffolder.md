---
name: context-package-scaffolder
description: "Copies a per-context package (`unit_of_work` or `query_context`) into the target context-integration directory, wires its provider into containers.py, and (query_context only) adds a pytest fixture to the integration conftest. Invoke with: @persistence-spec:context-package-scaffolder <context-package> <locations_report_text>"
tools: Read, Write, Edit, Bash, Skill
model: sonnet
skills:
  - spec-core:modules
---

You are a context-package scaffolder. Your job is to install a per-context package selected by the `<context-package>` axis — `unit_of_work` (command-side) or `query_context` (query-side) — into a context's infrastructure layer and wire its provider into the project's `containers.py`. For the `query_context` axis you additionally add a `query_context` pytest fixture into the integration conftest. Do not ask the user for confirmation. Be idempotent: skip anything that already exists; never overwrite copied files; treat already-wired containers (and an already-present fixture) as a no-op.

**Axis — `<context-package>` ∈ {unit_of_work, query_context}.** Steps 1–4 are byte-near across both axes; only the per-axis configuration below and the destination-derivation MODE differ. The `query_context` axis additionally runs a flag-guarded Step 5 (conftest fixture). Bind the axis configuration once at the top, then run the shared workflow.

**Caller-side skip.** Callers may skip invoking this agent entirely when the `Context Integration` row's `Status` in the locations report is `exists`. The agent itself remains fully idempotent, so re-runs are safe; the skip is purely an optimization.

## Inputs

1. `<context-package>` (first argument): one of `unit_of_work` or `query_context`. Selects the axis configuration. If it is any other value, fail with: `Error: <context-package> must be 'unit_of_work' or 'query_context'; got '<value>'.`
2. `<locations_report_text>` (second and only other argument): the Markdown table emitted by `@spec-core:target-locations-finder` — seven rows mapping `Category` to absolute `Path` and `Status`. Parse it as text; do not re-run the finder.

This agent does **not** take a spec file. It does not need the aggregate name or table list.

## Axis configuration

Bind the following per the `<context-package>` value before running the workflow:

| Variable | `unit_of_work` | `query_context` |
|---|---|---|
| `<source_pkg>` | `unit_of_work` | `query_context` |
| `<concrete_filename>` | `sql_alchemy_unit_of_work.py` | `sql_alchemy_query_context.py` |
| `<AbstractClass>` | `AbstractUnitOfWork` | `AbstractQueryContext` |
| `<ConcreteClass>` | `SqlAlchemyUnitOfWork` | `SqlAlchemyQueryContext` |
| `<provider_attr>` | `unit_of_work` | `query_context` |
| `<dest_mode>` | `install-at` | `derive-sibling` |
| `<emit_conftest_fixture>` | `false` | `true` |
| `<report_end_line>` | `Scaffolded unit of work.` | `Scaffolded query context.` |

The source modules are homed in the `spec-core:modules` umbrella skill, auto-loaded via this agent's frontmatter. Resolve `<modules_dir>` as the directory containing that skill's `SKILL.md` (its loaded context reveals its location); the source package is `<modules_dir>/<source_pkg>/`. Do not require it as input, and do not search `~/.claude/plugins`. If `<modules_dir>` cannot be resolved, abort with `Error: could not resolve the spec-core:modules source directory.` Each source package contains exactly three files: `__init__.py`, `abstract_<source_pkg>.py` (i.e. `abstract_unit_of_work.py` / `abstract_query_context.py`), and `<concrete_filename>`.

## Workflow

### Step 1 — Parse the locations report

From `<locations_report_text>`, extract the absolute `Path` value for each `Category` you need:

- `Context Integration` — the path that already points at `<...>/unit_of_work`. Its interpretation depends on `<dest_mode>` (see Step 2).
- `Database Session` — the directory housing the project's `DatabaseSession` class (e.g. `<repo>/src/<pkg>/extras/database_session`). Used in Step 3 to derive the `DatabaseSession` import inside the copied `<concrete_filename>`.
- `Containers` — a path to a `containers.py` file.
- `Tests` — a path to the project's tests directory (e.g. `<repo>/src/tests`). **`query_context` axis only:** used in Step 5 to add the `query_context` pytest fixture into `<tests_dir>/integration/conftest.py`. If the `Tests` row is absent from the report, skip Step 5 and record it as such. (Ignored on the `unit_of_work` axis.)

All other rows are ignored.

### Step 2 — Scaffold the context package under the destination directory

Resolve the destination directory `<ctx_dir>` per `<dest_mode>`:

- **`<dest_mode> == install-at` (unit_of_work):** let `<ctx_dir>` = the `Context Integration` path from Step 1. This path is the destination `unit_of_work/` directory itself.
- **`<dest_mode> == derive-sibling` (query_context):** let `<uow_dir>` = the `Context Integration` path from Step 1. Assert that the leaf segment of `<uow_dir>` is exactly `unit_of_work`; if it is not, fail with a clear error explaining that the sibling-derivation assumes the `Context Integration` row points at a `.../unit_of_work` directory. Compute `<ctx_dir>` = `<parent_of(uow_dir)>/query_context`. This `<ctx_dir>` is the destination directory for the query_context package, installed as a **sibling** of `unit_of_work`.

The source package (per the axis configuration above) contains exactly three files: `__init__.py`, `abstract_<source_pkg>.py`, `<concrete_filename>`.

Workflow:

1. `mkdir -p <ctx_dir>` (idempotent).
2. For each of the three source files, check if `<ctx_dir>/<filename>` already exists.
   - If it exists, record it as skipped — never overwrite.
   - If it does not exist, copy the file's contents from the source into `<ctx_dir>/<filename>` using `Read` then `Write`. Preserve contents byte-for-byte.
3. Track which of the three files were freshly copied (vs skipped). The next step uses this set.

### Step 3 — Patch the `DatabaseSession` import in the copied `<concrete_filename>`

The source file `<concrete_filename>` ships with the placeholder comment line:

```python
# Add DatabaseSession import there
```

This step replaces that comment with the actual `DatabaseSession` import derived from the `Database Session` location.

**3a. Skip if the file was not freshly copied.** If `<concrete_filename>` was reported as skipped in Step 2 (i.e. it already existed at `<ctx_dir>`), skip this entire step and report `patch: skipped: file already present`. The destination file is treated as authoritative once it exists; never edit a file the agent did not just copy.

**3b. Derive the `DatabaseSession` import path.** Let `<db_session_dir>` = the `Database Session` path from Step 1. Walk up `<db_session_dir>`'s parent chain until you find a directory named `src`. Take the path segments *after* `src` **excluding** the trailing leaf (the directory `<db_session_dir>` itself), and join them with `.` to form `<db_session_module>`.

Example: `<db_session_dir>` = `<repo>/src/stps_templates/extras/database_session` → segments after `src` are `stps_templates`, `extras`, `database_session` → drop the leaf → `<db_session_module>` = `stps_templates.extras`.

The intent is to import from the parent package (which re-exports `DatabaseSession` via its `__init__.py`), not from the leaf module. If no `src` ancestor is found, fail with a clear error.

**3c. Replace the placeholder.** Read the freshly-copied `<ctx_dir>/<concrete_filename>`. Locate the exact line:

```
# Add DatabaseSession import there
```

If found, replace that single line in place with:

```
from <db_session_module> import DatabaseSession
```

Preserve all surrounding lines and whitespace verbatim. Record the patch as `applied`.

**3d. Missing placeholder is non-fatal.** If the placeholder line is not present in the freshly-copied file, do not fail. Record `patch: skipped: placeholder not found` in the report and continue with Step 4.

### Step 4 — Wire the `<provider_attr>` provider into `containers.py`

Let `<containers_file>` = the `Containers` path from Step 1.

If `<containers_file>` does not exist, skip this step entirely and record that fact in the report under a `Containers integration` section. Do not create the file.

This step is independent of any sibling-context wiring — do not require the other context package to be present, and do not fail if it is missing.

Otherwise:

**4a. Derive the import path.** Starting from `<ctx_dir>`, walk up parent directories until you find a directory named `src`. Take the path segments *after* `src` (inclusive of `<source_pkg>` itself) and join them with `.` to form `<ctx_module>` (e.g. `stps_templates.infrastructure.<source_pkg>`). If no `src` ancestor is found, fail with a clear error.

**4b. Detect existing wiring.** Read `<containers_file>`. The wiring is considered already present if **both** of the following hold:

- The file contains a line importing `<AbstractClass>` and `<ConcreteClass>` from `<ctx_module>` (any whitespace/grouping). If only one of the two names is imported, treat as not-present and proceed to insert (the insertion will fail-fast in 4d if it would duplicate).
- The `Containers` class body contains a `<provider_attr>` attribute assignment.

If both are present, record the file as already-wired and skip 4c/4d.

**4c. Insert the import.** If the import block is missing, insert the line:

```python
from <ctx_module> import <AbstractClass>, <ConcreteClass>
```

immediately after the last existing top-level `from ... import ...` statement at the top of the file. Preserve existing import grouping (do not reformat).

**4d. Insert the provider.** Locate the line `class Containers(containers.DeclarativeContainer):`. If exactly one such class is found, append the following block at the end of its body, indented with four spaces, separated from the previous attribute by one blank line:

```python
    <provider_attr>: providers.Singleton[<AbstractClass>] = providers.Singleton(
        <ConcreteClass>,
        database_session=datasources.postgres_session,
    )
```

The body's end is the last consecutive indented line belonging to the `Containers` class (next non-indented line, EOF, or next top-level `class`/`def`).

**4e. Fail-fast on ambiguity.** Fail with a clear error and do not modify `<containers_file>` if any of the following is true:

- No `class Containers(containers.DeclarativeContainer):` is found, or more than one match is found.
- The `Containers` class does not reference `datasources` (i.e. no `datasources` attribute or `providers.DependenciesContainer()` / `providers.Container(Datasources, ...)` inside the class body).
- A `<provider_attr>` attribute is already present in the `Containers` class body but the import is missing (or vice versa) — the file is in an inconsistent state.

### Step 5 — Add `query_context` fixture to integration conftest

**Skip this step entirely when `<emit_conftest_fixture>` is `false` (the `unit_of_work` axis).** It runs only on the `query_context` axis.

Let `<tests_dir>` = the `Tests` path from Step 1. If the `Tests` row was not present in the locations report, skip this step entirely and record `skipped: Tests row not in report` for the conftest fixture.

Target file: `<tests_dir>/integration/conftest.py`.

**5a. Require the conftest to exist.** If the file does not exist, fail with a clear error directing the user to run `/persistence-spec:init-persistence` (which prepares the integration test package) first. Do not create the file. Do not silently skip.

**5b. Idempotency check.** Read the conftest. If it already contains a line matching `def query_context(`, record `already present — skipped` and do not modify the file.

**5c. Ensure `import pytest`.** If the file lacks an `import pytest` line, insert it before the first non-import line (or at the top of the file).

**5d. Build the fixture block.** The fixture text is fixed and aggregate-agnostic:

```python
@pytest.fixture
def query_context(containers):
    return containers.query_context()
```

**5e. Insert the fixture.**

- **If the file contains a `def unit_of_work(` fixture:** insert the `query_context` fixture immediately after the end of the `unit_of_work` fixture body, separated by exactly one blank line on each side. The fixture's end is the last consecutive non-empty line indented under `def unit_of_work(` (next blank-then-top-level-construct, next `@pytest.fixture` decorator, or EOF).
- **Otherwise:** insert the fixture after the last top-level `from ... import ...` / `import ...` line, separated by exactly one blank line on each side. Do not require `unit_of_work` to be present — the two fixtures are independent.

Use Edit with enough surrounding context in `old_string` to make the anchor unique. Preserve all surrounding whitespace and blank-line groupings verbatim.

Trust prior steps — do not re-read `containers.py` to verify the `query_context` provider is present; Steps 1–4 already wired it.

### Step 6 — Report

Emit a concise Markdown report listing:

- Context package (`<source_pkg>`): copied / skipped files under `<ctx_dir>`
- DatabaseSession import patch: one of `applied` (placeholder replaced), `skipped: file already present`, or `skipped: placeholder not found`
- Containers integration: one of `wired` (provider + import inserted), `already wired` (no change), or `skipped: containers.py missing`
- **`query_context` axis only** — Conftest fixture: one of `added` (fixture inserted), `already present — skipped`, or `skipped: Tests row not in report`

Do not emit anything beyond the report. End with: `<report_end_line>`.
