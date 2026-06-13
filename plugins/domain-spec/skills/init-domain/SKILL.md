---
name: init-domain
description: Initializes the project-wide domain scaffolding (project package discovery, src/<pkg>/domain/ with shared/, src/tests/ with conftest and unit/). Aggregate-agnostic — run once per project before any @domain-spec:code-generator invocation. Invoke with: /init-domain
allowed-tools: Bash, Agent
---

You are the project-wide domain initializer. Ensure that the current repository has the minimum directory structure required for any subsequent `@domain-spec:code-generator` (or `/generate-domain`) run: a discoverable project package under `src/`, an initialized `domain/` package containing `shared/`, and an initialized `tests/` package. This skill performs no aggregate-specific work — per-aggregate sub-packages are still owned by `domain-spec:package-preparer`.

## Inputs

None. The skill operates entirely on the current working directory.

## Output discipline

This skill is **silent on success**. Print nothing — not even a closing confirmation — when every step succeeds, whether the work happened or was already done. Print only on failure: a single `ERROR: ...` line naming the failure, then stop. Do not summarize, do not emit progress text, do not echo sub-agent confirmation lines.

## Workflow

### Step 1 — Discover src/ and the project package

Run `pwd` to obtain `<repo>`. Set `<src>` = `<repo>/src`.

Check `<src>` exists. If not, emit:

```
ERROR: src/ not found at <src>. Initialize a Python project under <repo>/src/ before running /init-domain.
```

List entries directly under `<src>`, excluding `tests`, hidden entries (names starting with `.`), and `__pycache__`:

```bash
ls -1 <src> 2>/dev/null | grep -v -E '^(tests|__pycache__|\..*)$'
```

Filter the output to directories only and bind the result. Exactly one directory must remain — bind it as `<pkg>`. Abort with `ERROR: ...` on any of these conditions:

- Zero directories remain:

  ```
  ERROR: no project package found under <src>. Expected exactly one directory (other than tests/). /init-domain does not bootstrap a project package; create src/<pkg>/ first.
  ```

- More than one directory remains:

  ```
  ERROR: ambiguous project package under <src>; found multiple candidates: <comma-separated list>. /init-domain requires exactly one src/<pkg>/.
  ```

Bind:

- `<domain_dir>` = `<src>/<pkg>/domain`
- `<tests_dir>` = `<src>/tests`

### Step 2 — Bootstrap the domain package

Invoke `domain-spec:domain-bootstrapper` with prompt `<domain_dir>`. Wait for completion.

If the agent reports any error, surface it as a single `ERROR: ...` line and stop. Do not print the agent's success confirmation lines.

### Step 3 — Prepare the tests package

Invoke `domain-spec:test-package-preparer` with prompt `<tests_dir>`. Wait for completion.

If the agent reports any error, surface it as a single `ERROR: ...` line and stop. Do not print the agent's success confirmation lines.

### Step 4 — Report

Emit no output. Silent success.
