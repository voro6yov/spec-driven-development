---
name: init-domain
description: Initializes the project-wide domain scaffolding (project package discovery, src/<pkg>/domain/ with shared/, src/tests/ with conftest and unit/). Aggregate-agnostic — run once per project before any @domain-spec:code-generator invocation. Invoke with: /init-domain
allowed-tools: Bash, Agent, Skill
---

You are the project-wide domain initializer. Ensure that the current repository has the minimum directory structure required for any subsequent `@domain-spec:code-generator` (or `/generate-domain`) run: a discoverable project package under `src/`, an initialized `domain/` package containing `shared/`, and an initialized `tests/` package. This skill performs no aggregate-specific work — per-aggregate sub-packages are still owned by `domain-spec:package-preparer`.

## Inputs

None. The skill operates entirely on the current working directory.

## Output discipline

This skill is **silent on success**. Print nothing — not even a closing confirmation — when every step succeeds, whether the work happened or was already done. Print only on failure: a single `ERROR: ...` line naming the failure, then stop. Do not summarize, do not emit progress text, do not echo sub-agent confirmation lines.

## Workflow

### Step 1 — Discover src/ and the project package

Invoke `@spec-core:project-package-finder` with prompt `/init-domain`. Wait for completion. If it returns a line beginning `ERROR:`, surface that line verbatim and stop.

Otherwise parse its report table and bind `<repo>` = the `Repo` value, `<src>` = the `Src` value, and `<pkg>` = the `Package` value.

Bind:

- `<domain_dir>` = `<src>/<pkg>/domain`
- `<tests_dir>` = `<src>/tests`

### Step 2 — Bootstrap the domain package

Ensure the domain package directory exists with an `__init__.py` and contains the canonical `shared` sub-package copied from the `spec-core:modules` umbrella. This step never creates per-aggregate sub-packages — that responsibility belongs to `domain-spec:package-preparer`.

`<domain_dir>` is always bound from Step 1 (it is `<src>/<pkg>/domain`), so it is absolute and its parent (`<src>/<pkg>`) is the discovered project package. No re-derivation is needed.

**2a. Ensure the domain directory exists.** Check whether `<domain_dir>` already exists:

```bash
[ -d "<domain_dir>" ]
```

If it does not exist, create it as a Python package:

```bash
mkdir -p <domain_dir>
touch <domain_dir>/__init__.py
```

**2b. Ensure the shared package exists.** Check whether `<domain_dir>/shared` already exists:

```bash
[ -d "<domain_dir>/shared" ]
```

If it already exists, this step is done. Otherwise, locate the canonical `shared` source: it is the `shared` group of the `spec-core:modules` umbrella skill. Invoke that skill (via the `Skill` tool) and resolve `<modules_dir>` as the directory containing its `SKILL.md` (its loaded context reveals its location). The source directory is `<modules_dir>/shared`. Do not search `~/.claude/plugins`.

If `<modules_dir>` cannot be resolved, emit:

```
ERROR: could not resolve the spec-core:modules source directory.
```

Otherwise copy the source tree into the domain directory (this also installs the nested `guards/` sub-package):

```bash
cp -r <modules_dir>/shared <domain_dir>/shared
```

If any command in this step fails, surface it as a single `ERROR: ...` line and stop.

### Step 3 — Prepare the tests package

Ensure `<tests_dir>` exists as a Python package, contains a root `conftest.py`, and a `unit/` sub-package. `<tests_dir>` is always bound from Step 1 (it is `<src>/tests`), so it is absolute and its parent (`<src>`) is known to exist — no extra path-hygiene guards are needed here.

**3a. Ensure the tests package exists.** Check whether `<tests_dir>` already exists:

```bash
[ -d "<tests_dir>" ]
```

If it does not exist, create it as a Python package:

```bash
mkdir -p <tests_dir>
touch <tests_dir>/__init__.py
```

**3b. Ensure `tests/conftest.py` exists.** Check whether `<tests_dir>/conftest.py` already exists:

```bash
[ -f "<tests_dir>/conftest.py" ]
```

If it does not exist, create it:

```bash
touch <tests_dir>/conftest.py
```

**3c. Ensure the `tests/unit` package exists.** Check whether `<tests_dir>/unit` already exists:

```bash
[ -d "<tests_dir>/unit" ]
```

If it does not exist, create it as a Python package:

```bash
mkdir -p <tests_dir>/unit
touch <tests_dir>/unit/__init__.py
```

If any command in this step fails, surface it as a single `ERROR: ...` line and stop.

### Step 4 — Report

Emit no output. Silent success.
