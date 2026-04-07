---
name: generate-code
description: Orchestrates DDD code generation from a class spec — scaffolds the package then implements classes in dependency order. Invoke with: /generate-code <diagram_file> <output_dir>
argument-hint: <diagram_file> <output_dir>
context: fork
agent: general-purpose
allowed-tools: Read, Bash, Agent
---

You are a DDD code generation orchestrator. Generate Python implementation files for all classes in the spec appended to `$ARGUMENTS[0]`, writing output to `$ARGUMENTS[1]`.

## Workflow

### Step 1 — Read and parse the spec

Read `$ARGUMENTS[0]`. Locate the last standalone `---` line (on its own line, not inside a code block). Everything after it is the **spec section**.

Collect all class blocks from the spec section. A class block starts at a `**\`ClassName\`** <<...>>` line. Map each class to its section category:

| Section heading | Category |
|---|---|
| `#### Data Structures` | `data-structures` |
| `#### Value Objects` | `value-objects` |
| `#### Domain Events` | `domain-events` |
| `#### Commands` | `commands` |
| `#### Aggregate Root / Entities` | `aggregates` |
| `#### Repositories / Services` | `repositories-services` |
| `#### Domain Exceptions` | handled by `exceptions-implementer` — do not extract individual class names |

Also parse the `### Dependencies` section. Each entry has the form `**A** <verb> **B** (...)`. Build a dependency map: class A depends on class B when the verb is `composes`, `depends on`, or similar (not `emits` — event emission does not mean the emitting class depends on the event for implementation order).

### Step 2 — Build implementation waves

From the dependency map, compute topological implementation order:

- **Wave 1**: classes with no inbound dependencies from other spec classes (TypedDicts, Events, Commands, leaf Value Objects). Include `exceptions-implementer` here if `#### Domain Exceptions` has content.
- **Wave N**: classes whose all dependencies appear in earlier waves.

If no dependency map entry covers a class, treat it as Wave 1.

### Step 3 — Create output directory

```bash
mkdir -p $ARGUMENTS[1]
```

### Step 4 — Scaffold

Invoke `domain-spec:scaffold-builder` with prompt `$ARGUMENTS[0] $ARGUMENTS[1]`. Wait for completion before proceeding.

### Step 5 — Implement in waves

Execute each wave sequentially. Within each wave, spawn all agents in a **single message** so they run in parallel.

**Wave 1 message** — spawn in parallel:
- One `domain-spec:code-implementer` per Wave 1 class, each with prompt `$ARGUMENTS[1] <class_name>`
- One `domain-spec:exceptions-implementer` (if domain exceptions exist), with prompt `$ARGUMENTS[1]`

**Wave N messages** — spawn in parallel:
- One `domain-spec:code-implementer` per Wave N class, each with prompt `$ARGUMENTS[1] <class_name>`

Wait for all agents in a wave to complete before starting the next.

### Step 6 — Report

Confirm with one sentence: "Code generation complete for `$ARGUMENTS[0]` → `$ARGUMENTS[1]`."
