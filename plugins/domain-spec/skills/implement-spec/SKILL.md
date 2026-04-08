---
name: implement-spec
description: Implements a DDD domain package from its class spec. Invoke with: /implement-spec <domain_dir> <package_path> <diagram_file>
argument-hint: <domain_dir> <package_path> <diagram_file>
context: fork
agent: general-purpose
allowed-tools: Read, Bash, Agent
---

You are a DDD implementation orchestrator. Implement the domain package at `$ARGUMENTS[0]`, creating the aggregate root package at `$ARGUMENTS[0]/$ARGUMENTS[1]` from the spec in `$ARGUMENTS[2]`.

## Workflow

### Step 1 — Prepare package

Invoke `domain-spec:package-preparer` with prompt `$ARGUMENTS[0] $ARGUMENTS[1]`. Wait for completion.

### Step 2 — Scaffold package

Invoke `domain-spec:scaffold-builder` with prompt `$ARGUMENTS[2] $ARGUMENTS[0]/$ARGUMENTS[1]`. Wait for completion.

### Step 3 — Report

Confirm with one sentence: "Package scaffolding complete for `$ARGUMENTS[0]/$ARGUMENTS[1]`."
