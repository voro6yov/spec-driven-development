---
name: init-messaging
description: "Initializes the project-wide messaging scaffolding (project package discovery, src/<pkg>/messaging/ as an empty aggregator package, and a canonical Click __main__.py skeleton). Invoke with: /messaging-spec:init-messaging"
allowed-tools: Bash, Write, Agent
---

You are the project-wide messaging initializer. Ensure that the current repository has the minimum directory structure and module set required for any subsequent `/messaging-spec:generate-code` run:

- the `messaging/` Python package (empty zero-byte `__init__.py`; populated per-consumer by `@consumer-scaffolder`),
- a canonical Click `__main__.py` skeleton (with `@click.group() def cli()` and the `if __name__ == "__main__": cli()` main guard) so `@dispatch-integrator`'s Step 6a precondition check passes on the first consumer run.

This skill performs no per-consumer work — the `<consumer_name>/` submodule, dispatcher Singleton in `containers.py`, runner in `entrypoint.py`, Click command in `__main__.py`, destination/queue constants in `constants.py`, handler fixtures in `tests/conftest.py`, and the `messaging/__init__.py` aggregator entries are all owned by the per-consumer scaffolders and implementers run via `/messaging-spec:generate-code`.

This skill performs no `containers.py`, `entrypoint.py`, or `constants.py` bootstrapping — those files are preconditions for `@dispatch-integrator` and `@consumer-scaffolder` but are owned by the persistence-spec and rest-api-spec init pipelines (or hand-authored). The only work here on those files is the existence pre-checks in Steps 2-4.

## Inputs

None. The skill operates entirely on the current working directory.

## Output discipline

This skill is **silent on success**. Print nothing — not even a closing confirmation — when every step succeeds, whether the work happened, was partial, or was already done. Print only on failure: a single `ERROR: ...` line naming the failure, then stop. Do not summarize, do not emit progress text, do not echo sub-agent confirmation lines.

## Workflow

### Step 1 — Discover src/ and the project package

Run `pwd` to obtain `<repo>`. Set `<src>` = `<repo>/src`.

Check `<src>` exists. If not, emit:

```
ERROR: src/ not found at <src>. Initialize a Python project under <repo>/src/ before running /messaging-spec:init-messaging.
```

List entries directly under `<src>`, excluding `tests`, hidden entries (names starting with `.`), and `__pycache__`:

```bash
ls -1 <src> 2>/dev/null | grep -v -E '^(tests|__pycache__|\..*)$'
```

Filter the output to directories only and bind the result. Exactly one directory must remain — bind it as `<pkg>`. Abort with `ERROR: ...` on any of these conditions:

- Zero directories remain:

  ```
  ERROR: no project package found under <src>. Expected exactly one directory (other than tests/). /messaging-spec:init-messaging does not bootstrap a project package; create src/<pkg>/ first.
  ```

- More than one directory remains:

  ```
  ERROR: ambiguous project package under <src>; found multiple candidates: <comma-separated list>. /messaging-spec:init-messaging requires exactly one src/<pkg>/.
  ```

Bind:

- `<pkg_dir>` = `<src>/<pkg>`
- `<containers_file>` = `<pkg_dir>/containers.py`
- `<entrypoint_file>` = `<pkg_dir>/entrypoint.py`
- `<constants_file>` = `<pkg_dir>/constants.py`
- `<tests_dir>` = `<src>/tests`
- `<messaging_pkg>` = `<pkg_dir>/messaging`
- `<messaging_init>` = `<messaging_pkg>/__init__.py`
- `<main_file>` = `<pkg_dir>/__main__.py`

### Step 2 — Pre-check containers.py exists

Check whether `<containers_file>` exists:

```bash
[ -f "<containers_file>" ]
```

If it does not exist, emit:

```
ERROR: containers.py not found at <containers_file>. /messaging-spec:init-messaging requires the project's containers.py to be in place — @dispatch-integrator registers a <consumer>_dispatcher: providers.Singleton[IMessageConsumer] provider in it. Run /persistence-spec:init-persistence (or otherwise create containers.py) before this skill.
```

and stop. Do not create the file. Do not proceed to any further step.

### Step 3 — Pre-check entrypoint.py exists

Check whether `<entrypoint_file>` exists:

```bash
[ -f "<entrypoint_file>" ]
```

If it does not exist, emit:

```
ERROR: entrypoint.py not found at <entrypoint_file>. /messaging-spec:init-messaging requires the project's entrypoint.py to be in place — @dispatch-integrator inserts a run_<consumer>_dispatcher() runner into it. entrypoint.py is created by `@app-integrator` during /rest-api-spec:generate-code; run /rest-api-spec:init-rest-api before this skill, or hand-author entrypoint.py with at least the Settings / Containers / init_containers / _base_service_init helpers defined.
```

and stop. Do not create the file. Do not proceed to any further step.

### Step 4 — Pre-check constants.py exists

Check whether `<constants_file>` exists:

```bash
[ -f "<constants_file>" ]
```

If it does not exist, emit:

```
ERROR: constants.py not found at <constants_file>. /messaging-spec:init-messaging requires the project's constants.py to be in place — @consumer-scaffolder appends per-consumer destination and queue constants (<UPPER_AGGREGATE>_DESTINATION, <CONSUMER>_EVENTS_QUEUE, <CONSUMER>_COMMANDS_QUEUE) into it. constants.py is hand-authored or patch-merged by `@app-integrator` during /rest-api-spec:generate-code; create it before this skill.
```

and stop. Do not create the file. Do not proceed to any further step.

### Step 5 — Pre-check tests/ exists

Check whether `<tests_dir>` exists:

```bash
[ -d "<tests_dir>" ]
```

If it does not exist, emit:

```
ERROR: tests/ not found at <tests_dir>. /messaging-spec:init-messaging requires the tests package to be in place — @test-fixtures-preparer creates and patches <tests_dir>/conftest.py with the make_event_envelope helper and one handler fixture per Table 2 entry. Run /init-domain before this skill.
```

and stop. Do not create the directory. Do not proceed to any further step.

### Step 6 — Resolve target locations

Invoke `spec-core:target-locations-finder` with the prompt `messaging`. Wait for completion and capture its Markdown table output as `<locations_report>`.

If the agent reports any error, surface it as a single `ERROR: ...` line and stop. Do not print the agent's success confirmation lines.

The report is captured for parity with the other plugin init skills (which feed the report into downstream scaffolders); this skill does not consume any row beyond the existence checks performed above. The bindings derived in Step 1 are authoritative for Steps 7-8.

### Step 7 — Create the base messaging package

Run sequentially via `Bash`. Create the directory and an empty `__init__.py` if it does not already exist:

```bash
mkdir -p <messaging_pkg> && [ -f <messaging_init> ] || touch <messaging_init>
```

Never overwrite an existing `<messaging_init>` — its content is owned downstream and is additively patched on every per-consumer run by `@consumer-scaffolder` Step 7 (inserting `from . import <consumer_name_snake>`, `from .<consumer_name_snake> import *`, and extending `__all__`). The initial zero-byte file keeps the package importable until the first consumer is scaffolded.

### Step 8 — Scaffold __main__.py if absent

Check whether `<main_file>` already exists:

```bash
[ -f "<main_file>" ]
```

If it does not exist, write the file via `Write` with exactly this content (the canonical Click skeleton required by `@dispatch-integrator` Step 6a's precondition check):

```python
import click


@click.group()
def cli() -> None:
    pass


if __name__ == "__main__":
    cli()
```

The file ends with a single trailing newline. `@dispatch-integrator` (Step 6) additively patches this file on every per-consumer run to insert one `@click.command() def dispatch_<consumer>` block and one `cli.add_command(dispatch_<consumer>)` line inside the main guard, kept alphabetically sorted across reruns.

If the file already exists, **do not modify it** — its content is owned downstream and `@dispatch-integrator` only inserts (never replaces) the per-consumer click-command lines. If the existing file lacks the canonical Click shape (no `@click.group()`, no `def cli()`, no main guard, or no `cli()` invocation), this skill does not repair it — `@dispatch-integrator` Step 6a will abort with an explicit "shape unrecognized" error on the first consumer run, and the user must hand-fix `__main__.py` to the canonical form.

### Step 9 — Report

Emit no output. Silent success.
