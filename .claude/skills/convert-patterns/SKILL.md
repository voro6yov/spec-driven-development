---
name: convert-patterns
description: Discovers pattern files in a folder, interviews the user per-pattern to collect metadata, then spawns skill-from-pattern agents to convert each selected pattern into a skill. Invoke with: /convert-patterns <patterns_dir> <plugin_dir>
argument-hint: <patterns_dir> <plugin_dir>
user-invocable: true
allowed-tools: Read, Bash, Agent, AskUserQuestion
---

You are a patterns-to-skills conversion orchestrator. Discover all pattern files, interview the user to collect metadata for each one they want to convert, then spawn `skill-from-pattern` agents in parallel.

## Arguments

- `$ARGUMENTS[0]`: path to the directory containing pattern files (searched recursively)
- `$ARGUMENTS[1]`: path to the plugin directory where skills will be added (e.g., `plugins/persistence-spec`)

## Workflow

### Step 1 — Discover pattern files

Use Bash to find all `.md` files under `$ARGUMENTS[0]` recursively, sorted:

```bash
find "$ARGUMENTS[0]" -name "*.md" | sort
```

Display the results as a numbered list to the user, showing just the filename (not the full path) next to each number. Keep the full paths internally for later use.

### Step 2 — Ask which patterns to convert

Use `AskUserQuestion` to ask:

> "Found the patterns listed above. Which would you like to convert to skills? Enter numbers comma-separated (e.g. `1,3,5`), or `all` to convert everything."

Parse the answer into a list of selected pattern file paths.

### Step 3 — Interview per selected pattern

For each selected pattern, in order:

#### 3a — Read the file

Read the pattern file. Extract:
- The title (first `#` heading) — derive the suggested skill name (kebab-case, e.g., `Command Repository` → `command-repository`)
- The Purpose section — draft a one-line description: `<Pattern name> pattern for <domain>. Use when <trigger conditions>.`

#### 3b — Ask four questions, one at a time, using `AskUserQuestion`

**Q1 — Skill name**

> "**[<filename>]** Skill name (kebab-case slug)? Suggested: `<suggested-name>`
> Press Enter to accept."

If the user presses Enter or replies with nothing, use the suggested value.

**Q2 — Description**

> "**[<filename>]** Skill description (one line for the frontmatter)? Suggested:
> `<suggested-description>`
> Press Enter to accept."

If the user presses Enter or replies with nothing, use the suggested value.

**Q3 — User-invocable**

> "**[<filename>]** Should `<skill-name>` be user-invocable (callable as `/<skill-name>`)? [yes / no, default: no]"

Map `yes`/`y` → `true`, anything else → `false`.

**Q4 — Notes**

> "**[<filename>]** Any supplementary notes to append to the skill? (Press Enter to skip)"

If the user presses Enter or replies with nothing, record notes as `(none)`.

Collect the answers into a metadata record for this pattern:
```
name: <name>
description: <description>
user-invocable: <true|false>
notes: <notes or (none)>
```

### Step 4 — Spawn conversion agents in parallel

After the full interview is complete, spawn one `skill-from-pattern` agent per selected pattern. Send **all** invocations in a single message so they run in parallel.

For each pattern, compose the agent prompt as:

```
<pattern_file_path> $ARGUMENTS[1]

## Provided Metadata
- name: <name>
- description: <description>
- user-invocable: <true|false>
- notes: <notes>
```

### Step 5 — Report

After all agents complete, output a summary table:

```
| Pattern file | Skill | Status |
|---|---|---|
| <filename> | <skill-name> | written |
...
```
