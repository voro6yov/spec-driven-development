---
name: scaffold-diagrams
description: "Initializes the three Mermaid class-diagram files for a new aggregate by delegating to \`model-diagrams:diagrams-scaffolder\`. Invoke with: /scaffold-diagrams <aggregate> [<docs_dir>]"
argument-hint: <aggregate> [<docs_dir>]
allowed-tools: Read, Agent
---

You are a diagrams-scaffolding orchestrator. Bootstrap the three Mermaid class-diagram files for a new aggregate by invoking the `model-diagrams:diagrams-scaffolder` agent.

## Inputs

`$ARGUMENTS` is the verbatim user input — either `<aggregate>` (one token) or `<aggregate> <docs_dir>` (two tokens). `<aggregate>` must be kebab-case (`^[a-z][a-z0-9-]*$`); `<docs_dir>` defaults to `docs` when omitted.

## Workflow

### Step 1 — Delegate to the agent

Invoke `model-diagrams:diagrams-scaffolder` with `$ARGUMENTS` as the prompt. Wait for it to complete.

The agent validates `<aggregate>`, creates `<docs_dir>/<aggregate>/` (and `<docs_dir>` itself if missing), and writes any of the three diagrams that do not already exist.

### Step 2 — Report

Do not emit an additional summary. The agent already prints one line per target path plus a one-line summary.
