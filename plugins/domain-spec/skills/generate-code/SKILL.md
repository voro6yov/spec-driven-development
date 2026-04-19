---
name: generate-code
description: Implements a DDD domain package from its class spec. Invoke with: /generate-code <domain_dir> <package_path> <diagram_file>
argument-hint: <domain_dir> <package_path> <diagram_file>
context: fork
agent: general-purpose
allowed-tools: Read, Bash, Agent
---

You are a DDD implementation orchestrator. Implement the domain package at `$ARGUMENTS[0]`, creating the aggregate root package at `$ARGUMENTS[0]/$ARGUMENTS[1]` from the spec in `$ARGUMENTS[2]`.

## Workflow

### Step 1 — Prepare package

Invoke `domain-spec:package-preparer` with prompt `$ARGUMENTS[0] $ARGUMENTS[1]`. Wait for completion.

### Step 2 — Prepare test package

Use Bash to derive the project root:

```bash
dirname "$ARGUMENTS[0]"
```

Invoke `domain-spec:test-package-preparer` with the resulting path. Wait for completion.

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

### Step 6 — Report

Confirm with one sentence: "Implementation complete for `$ARGUMENTS[0]/$ARGUMENTS[1]`."
