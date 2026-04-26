---
name: generate-code
description: Implements a DDD domain package from its class spec. Invoke with: /generate-code <domain_dir> <package_path> <diagram_file>
argument-hint: <domain_dir> <package_path> <diagram_file>
allowed-tools: Read, Bash, Agent
---

You are a DDD implementation orchestrator. Implement the domain package at `$ARGUMENTS[0]`, creating the aggregate root package at `$ARGUMENTS[0]/$ARGUMENTS[1]` from the spec in `$ARGUMENTS[2]`.

## Workflow

### Step 1 — Prepare package

Invoke `domain-spec:package-preparer` with prompt `$ARGUMENTS[0] $ARGUMENTS[1]`. Wait for completion.

### Step 2 — Prepare test package

Invoke `domain-spec:test-package-preparer` with prompt `$ARGUMENTS[0]`. Wait for completion.

### Step 3 — Scaffold package

Invoke `domain-spec:scaffold-builder` with prompt `$ARGUMENTS[2] $ARGUMENTS[0]/$ARGUMENTS[1]`. Wait for completion.

### Step 4 — Implement exceptions

Read `$ARGUMENTS[0]/$ARGUMENTS[1]/exceptions.py`. If the file contains at least one `class` definition (i.e. there are domain exception stubs), invoke `domain-spec:exceptions-implementer` with prompt `$ARGUMENTS[0]/$ARGUMENTS[1]`. Wait for completion. If the file is absent or contains no class definitions, skip this step silently.

### Step 5 — Implement other modules in parallel

Use Bash to list all `.py` files in `$ARGUMENTS[0]/$ARGUMENTS[1]` excluding `__init__.py` and `exceptions.py`:

```bash
ls "$ARGUMENTS[0]/$ARGUMENTS[1]"/*.py | grep -v '__init__\.py' | grep -v 'exceptions\.py'
```

For each file path returned, invoke `domain-spec:code-implementer` with prompt `<file_path>`. Launch all invocations in parallel (do not wait for one before starting the next). Wait for all to complete.

### Step 6 — Generate fixtures

Invoke `domain-spec:aggregate-fixtures-writer` with prompt `$ARGUMENTS[2] $ARGUMENTS[0]/tests`. Wait for completion.

### Step 7 — Implement tests

Invoke `domain-spec:aggregate-tests-implementator` with prompt `$ARGUMENTS[2] $ARGUMENTS[0]/tests`. Wait for completion.

### Step 8 — Update diagram with implementation paths

Compute two values:

1. **Repo-root-relative package path** — path of `$ARGUMENTS[0]/$ARGUMENTS[1]` relative to the repository root. Use:

   ```bash
   python3 -c "import os,sys; print(os.path.relpath(os.path.abspath(sys.argv[1]), sys.argv[2]))" "$ARGUMENTS[0]/$ARGUMENTS[1]" "$(git -C "$(dirname "$ARGUMENTS[2]")" rev-parse --show-toplevel)"
   ```

   If the diagram file is not inside a git repository, fall back to the absolute path of `$ARGUMENTS[0]/$ARGUMENTS[1]`.

2. **Dotted import path** — the full Python module path of the created package. Walk **upward** from `$ARGUMENTS[0]/$ARGUMENTS[1]` while each parent directory contains an `__init__.py`; the highest ancestor that still has `__init__.py` is the top-level package, and its parent is the source root. Build the dotted path by joining the directory names from that top-level package down to `$ARGUMENTS[1]`'s last segment with `.`.

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
   " "$ARGUMENTS[0]/$ARGUMENTS[1]"
   ```

Read `$ARGUMENTS[2]`. Build the section text:

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

Confirm with one sentence: "Implementation complete for `$ARGUMENTS[0]/$ARGUMENTS[1]`."
