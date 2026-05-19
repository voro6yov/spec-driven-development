---
name: trim-descriptions
description: Discovers every agent and skill inside a plugin directory and dispatches the `description-trimmer` agent on each one to shrink overly verbose frontmatter descriptions. Use when the harness warns about large cumulative agent or skill descriptions, or when bulk-cleaning a plugin's metadata. Invoke with: /trim-descriptions <plugin_dir>
argument-hint: <plugin_dir>
user-invocable: true
allowed-tools: Bash, Agent
---

You orchestrate a bulk trim of every `description:` frontmatter field inside a plugin. You fan out one `description-trimmer` agent per file in parallel waves, then report results.

You **never** edit any file directly. All editing happens inside the spawned agents.

## Argument

- `$ARGUMENTS[0]`: path to a plugin directory (e.g. `plugins/persistence-spec`). Expected layout: `<plugin_dir>/agents/*.md` and `<plugin_dir>/skills/<name>/SKILL.md`. Either sub-directory may be absent — that's fine.

## Workflow

### Step 1 — Validate the plugin directory

Run:

```bash
test -d "$ARGUMENTS[0]" && echo OK || echo MISSING
```

If `MISSING`, emit one line `trim-descriptions: <path> does not exist` and stop.

### Step 2 — Discover targets

Discover all files in one pass:

```bash
{ find "$ARGUMENTS[0]/agents" -maxdepth 1 -name "*.md" 2>/dev/null;
  find "$ARGUMENTS[0]/skills" -mindepth 2 -maxdepth 2 -name "SKILL.md" 2>/dev/null; } | sort
```

Collect the resulting absolute (or repo-relative) paths into a list. If the list is empty, emit `trim-descriptions: no agents or skills found under <path>` and stop.

### Step 3 — Dispatch in parallel waves of 10

Process the file list in chunks of at most **10 files per wave**. For each wave:

- Send a **single message** containing one `Agent` tool call per file in that wave (max 10 calls per message). Use `subagent_type: "description-trimmer"`.
- The prompt for each agent is **only the file path** (one line). Example:

  ```
  plugins/persistence-spec/agents/command-repository-implementer.md
  ```

- Provide a one-clause `description` per call, e.g. `"Trim <basename>"`.
- Do **not** run in background; you need each wave's results before reporting.

Wait for the wave to fully complete (all spawned agents return) before dispatching the next wave. This keeps the per-message tool-call count bounded and prevents the harness from rejecting an oversized batch.

### Step 4 — Collect results

Each spawned trimmer returns one of these single-line statuses:

- `description-trimmer: <path>: trimmed <orig> → <new> chars`
- `description-trimmer: <path>: already concise (<N> chars)`
- `description-trimmer: <path>: no shorter form found`
- `description-trimmer: <path>: no frontmatter`
- `description-trimmer: <path>: no description field`

Aggregate counts across all waves into the report.

### Step 5 — Emit a summary

Print a Markdown summary, no extra prose around it:

```
# trim-descriptions: <plugin_dir>

Processed <N> files across <W> waves.

| Outcome | Count |
|---|---|
| trimmed | <n> |
| already concise | <n> |
| no shorter form found | <n> |
| no frontmatter / no description field | <n> |

## Trimmed
- <path> — <orig> → <new> chars
- ...

## Skipped (already concise)
- <path> (<N> chars)
- ...

## No shorter form found
- <path>
- ...

## Errors
- <path> — <reason>
- ...
```

Omit a section if its list is empty.

## Out of scope

- Do not bulk-edit files yourself — the trimmer agent is the only writer.
- Do not modify agent / skill bodies.
- Do not recurse into nested plugin directories; only the literal `<plugin_dir>/agents/` and `<plugin_dir>/skills/<name>/SKILL.md` are scanned.
- Do not retry failed files automatically — surface them in the Errors section so the user can investigate.
