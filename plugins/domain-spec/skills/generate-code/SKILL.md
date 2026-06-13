---
name: generate-code
description: Implements a DDD domain package from its class spec. Resolves target locations from the current repo's `src/<pkg>/` layout, then runs the domain pipeline. Invoke with: /generate-code <domain_diagram>
argument-hint: <domain_diagram>
allowed-tools: Read, Bash, Agent
---

You are a DDD implementation orchestrator. Implement the aggregate described in `$ARGUMENTS` (a Mermaid domain class diagram file). All target locations are resolved from the current repo's `src/<pkg>/` layout via the `spec-core:target-locations-finder` agent — no other arguments are needed.

## Spec-input layout

This orchestrator chains agents (`scaffold-builder`, `aggregate-fixtures-writer`, `aggregate-tests-implementator`) that consume spec sibling artifacts produced by `/generate-specs`. Those artifacts live at `<dir>/<stem>.domain/specs.md`, `<dir>/<stem>.domain/exceptions.md`, and `<dir>/<stem>.domain/test-plan.md`. See `spec-core:naming-conventions` for the canonical layout. This skill does not read those paths directly — every chained agent derives them from `$ARGUMENTS`.

## Workflow

### Step 1 — Find target locations

Invoke `spec-core:target-locations-finder` with prompt `domain $ARGUMENTS` (the `domain` layer token followed by the diagram path). Wait for completion.

Capture the agent's full Markdown table output verbatim. Parse the `Absolute path` cell of each row and bind:

- `<source_root>` — `Source Root` row
- `<domain_dir>` — `Domain` row
- `<aggregate_pkg_dir>` — `Aggregate Package` row
- `<tests_dir>` — `Tests` row

Compute `<package_path>` as the path of `<aggregate_pkg_dir>` relative to `<domain_dir>`. With the standard layout this is just the diagram file's stem (e.g. `order`), but bind it from the report so it tracks the finder's output.

If any of the four rows is missing or its path cell is empty, output an `ERROR:` line explaining the failure and stop before any code generation.

### Step 2 — Prepare package

Invoke `domain-spec:package-preparer` with prompt `<domain_dir> <package_path>`. Wait for completion.

### Step 3 — Scaffold package

Invoke `domain-spec:scaffold-builder` with prompt `$ARGUMENTS <aggregate_pkg_dir>`. Wait for completion.

### Step 4 — Implement exceptions

Read `<aggregate_pkg_dir>/exceptions.py`. If the file contains at least one `class` definition (i.e. there are domain exception stubs), invoke `domain-spec:exceptions-implementer` with prompt `<aggregate_pkg_dir>`. Wait for completion. If the file is absent or contains no class definitions, skip this step silently.

### Step 5 — Implement other modules in parallel

Use Bash to list all `.py` files in `<aggregate_pkg_dir>` excluding `__init__.py` and `exceptions.py`, producing absolute paths:

```bash
ls -1 "<aggregate_pkg_dir>"/*.py | grep -v '__init__\.py' | grep -v 'exceptions\.py'
```

Because the glob is anchored at `<aggregate_pkg_dir>` (which is itself absolute per Step 1), every returned line is already an absolute path inside the aggregate package directory.

**Sanity check (Path hygiene rule 5 of `spec-core:naming-conventions`)** — before fanning out, verify every returned line:

- begins with `<aggregate_pkg_dir>/` (the file lives inside the expected ancestor), and
- ends in `.py`.

If any line fails either check, abort with `ERROR: unexpected file path '<line>' outside <aggregate_pkg_dir>` and stop before invoking the implementer — never relay a suspect path to a parallel writer.

For each validated absolute file path, invoke `domain-spec:code-implementer` with prompt `<file_path>`. Launch all invocations in parallel (do not wait for one before starting the next). Wait for all to complete.

### Step 6 — Generate fixtures

Invoke `domain-spec:aggregate-fixtures-writer` with prompt `$ARGUMENTS <tests_dir>`. Wait for completion.

### Step 7 — Implement tests

Invoke `domain-spec:aggregate-tests-implementator` with prompt `$ARGUMENTS <tests_dir>`. Wait for completion.

### Step 8 — Update diagram with implementation paths

Compute two values:

1. **Repo-root-relative package path** — path of `<aggregate_pkg_dir>` relative to the repository root. Use:

   ```bash
   python3 -c "import os,sys; print(os.path.relpath(os.path.abspath(sys.argv[1]), sys.argv[2]))" "<aggregate_pkg_dir>" "$(git -C "$(dirname "$ARGUMENTS")" rev-parse --show-toplevel)"
   ```

   If the diagram file is not inside a git repository, fall back to the absolute path of `<aggregate_pkg_dir>`.

2. **Dotted import path** — the full Python module path of the created package. Walk **upward** from `<aggregate_pkg_dir>` while each parent directory contains an `__init__.py`; the highest ancestor that still has `__init__.py` is the top-level package, and its parent is the source root. Build the dotted path by joining the directory names from that top-level package down to the aggregate package's last segment with `.`.

   Example: for package `src/stps_templates/domain/domain_type` where `src/` has no `__init__.py` but `stps_templates/`, `domain/`, and `domain_type/` each do, the import path is `stps_templates.domain.domain_type`.

   Use:

   ```bash
   python3 -c "
   import os, sys
   p = os.path.abspath(sys.argv[1])
   parts = []
   while os.path.isfile(os.path.join(p, '__init__.py')):
       parts.append(os.path.basename(p))
       p = os.path.dirname(p)
   print('.'.join(reversed(parts)))
   " "<aggregate_pkg_dir>"
   ```

Read `$ARGUMENTS`. Build the section text:

```markdown
## Implementation

- Package: `<rel_path>`
- Import path: `<dotted.path>`
```

Update the file as follows, then write it back with the Write tool:

- If a `## Implementation` section already exists (line beginning with `## Implementation`), replace its block — from that heading up to (but not including) the next top-level `## ` heading or end-of-file — with the new section text.
- Else if a `## Artifacts` section exists, insert the new section immediately before its `## Artifacts` heading, separated by a single blank line on each side.
- Else append the new section at the end of the file, ensuring exactly one blank line before it and a trailing newline.

### Step 9 — Report

Confirm with one sentence: "Implementation complete for `<aggregate_pkg_dir>`."
