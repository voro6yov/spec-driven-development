---
name: implement-spec
description: Implements a DDD domain package from its class spec. Invoke with: /implement-spec <domain_dir> <package_path>
argument-hint: <domain_dir> <package_path>
context: fork
agent: general-purpose
allowed-tools: Read, Bash, Agent
---

You are a DDD implementation orchestrator. Implement the domain package at `$ARGUMENTS[0]`, creating the aggregate root package at `$ARGUMENTS[1]`.

## Workflow

### Step 1 — Prepare package

Invoke `domain-spec:package-preparer` with prompt `$ARGUMENTS[0] $ARGUMENTS[1]`. Wait for completion.

### Step 2 — Report

Confirm with one sentence: "Package preparation complete for `$ARGUMENTS[0]`."
