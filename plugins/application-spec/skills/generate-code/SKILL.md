---
name: generate-code
description: Implements the application layer for an aggregate from its merged commands spec, merged queries spec, and services report siblings. Invoke with: /application-spec:generate-code <domain_diagram>
argument-hint: <domain_diagram>
allowed-tools: Bash, Agent, Skill
---

You are an application implementation orchestrator. Implement the application layer for the aggregate described by `$ARGUMENTS[0]` (the domain diagram). The skill consumes the merged sibling artifacts that `/application-spec:generate-specs` produces — it does not regenerate them. Sibling diagrams (`<commands_diagram>`, `<queries_diagram>`) and spec files are derived internally per `application-spec:naming-conventions`; downstream agents accept only `<domain_diagram>` plus non-derivable extras and derive the rest themselves.

## Precondition

Project-wide application-layer scaffolding (`application/`, `infrastructure/`, `infrastructure/services/`, `tests/fakes/`, and a minimal `tests/conftest.py` preamble) must already be in place, and the project's hand-authored `containers.py` and `constants.py` must exist. Run `/application-spec:init-application` once per project before this skill. This skill does **not** scaffold any aggregate-agnostic artifact; per-aggregate agents below will fail loudly if their parent packages or `constants.py` are missing.

## Sibling file convention

Per `application-spec:naming-conventions`. From `$ARGUMENTS[0]` (the domain diagram) at `<dir>/<stem>.md`:

- `<dir>` = directory containing the diagrams
- `<stem>` = the canonical aggregate stem (domain filename with `.md` stripped)
- `<plugin_dir>` = `<dir>/<stem>.application` — the per-plugin folder for application-spec

| Sibling artifact | Path |
|---|---|
| Merged commands spec | `<plugin_dir>/commands.specs.md` |
| Merged queries spec | `<plugin_dir>/queries.specs.md` |
| Services report | `<plugin_dir>/services.md` |

If any of these artifacts is missing the downstream agents abort with their own one-sentence errors — this orchestrator does not pre-validate. The orchestrator does not pass the spec-file paths to agents; each agent derives them internally from `$ARGUMENTS[0]`.

## Workflow

### Step 1 — Compute the services report path

Derive the services report path from `$ARGUMENTS[0]` (the domain diagram path) — it is needed locally for service enumeration in Step 4a:

- Let `<dir>` = `dirname($ARGUMENTS[0])`
- Let `<stem>` = `basename($ARGUMENTS[0])` with the trailing `.md` stripped
- Let `<plugin_dir>` = `<dir>/<stem>.application`
- Let `<services_report>` = `<plugin_dir>/services.md`

This local binding is only used by the Bash command in Step 4a; it is not passed to any agent.

### Step 2 — Find target locations

Invoke `application-spec:target-locations-finder` with an empty prompt. Wait for completion.

Capture the agent's full Markdown table output verbatim as `<locations_report_text>`. This text is the locations argument passed to every downstream agent in Steps 3–6. Pass it verbatim — do not trim, summarize, or reformat it.

Parse one value from the report for use in Step 7:

- **`<tests_dir>`** — read the `Absolute path` cell of the `Tests` row. Bind that value verbatim — it is an absolute path (e.g. `/repo/src/tests`). If the `Tests` row is missing or its path cell is empty, skip Step 7 entirely (emit a single bullet in the Step 8 report under the **Tests** phase noting `skipped (Tests location not reported)`).

### Step 3 — Scaffold application and infrastructure stubs

Invoke `application-spec:application-files-scaffolder` with prompt `$ARGUMENTS[0] <locations_report_text>`. Wait for completion.

This emits the per-aggregate application package (`<aggregate>_commands.py`, `<aggregate>_queries.py`, `<aggregate>_queries_settings.py`, one stub per external interface, aggregator `__init__.py`), one infrastructure service stub per `<attr>` collaborator, and the `<UPPER_AGGREGATE>_DESTINATION` constant in `constants.py`. Subsequent steps assume these stubs exist on disk.

### Step 4 — Fan out service implementers

#### Step 4a — Enumerate service identifiers

Run via Bash:

```bash
grep -E '^## ' "<services_report>" | sed 's/^## //'
```

Each output line is one `<service_identifier>` (PascalCase). Bind the list (preserving order) to `<services>`.

If the command returns no lines (the report's body is exactly `_None_`, or the report lists no `## <Identifier>` sections), skip Step 4b silently and proceed to Step 5. A purely-CRUD aggregate with no external/domain service collaborators is a valid empty case per the `application-spec:services-report-template` contract.

#### Step 4b — Spawn service implementers in parallel

In a single message, invoke one `application-spec:service-implementer` agent per identifier in `<services>`. Each invocation uses the prompt:

```
$ARGUMENTS[0] <locations_report_text> <service_identifier>
```

(That is: domain diagram, locations report, and the per-agent `<service_identifier>`. The services report path is derived inside the agent.)

All invocations launch in parallel — do not sequence them. Wait for every invocation to complete before proceeding. Each agent operates on its own service end-to-end (application interface stubs, infrastructure stub, test fake, DI provider, and conftest fixtures) and does not touch the others' files.

### Step 5 — Wire settings and exceptions in parallel

Emit both `Agent` calls in a single message — do not sequence them:

- `application-spec:queries-settings-implementer` with prompt `<locations_report_text>`.
- `application-spec:exceptions-implementer` with prompt `$ARGUMENTS[0] <locations_report_text>`.

Both invocations MUST appear as two tool calls in the same assistant turn. Issuing them across two turns is a violation of this step's contract.

Wait for both to complete. The settings implementer fills every `<aggregate>_queries_settings.py` stub under the application package; the exceptions implementer appends fully implemented application exception classes (and updates the `..shared` import + `__all__` and the aggregate `__init__.py` wiring) on the domain aggregate's `exceptions.py`.

These two agents touch disjoint files and are safe to run concurrently. They must run after Step 4 only loosely (they do not depend on service-implementer output) but before Step 6, because the commands/queries implementers consume the settings class and the application exceptions.

### Step 6 — Implement commands and queries in parallel

Emit both `Agent` calls in a single message — do not sequence them:

- `application-spec:commands-implementer` with prompt `$ARGUMENTS[0] <locations_report_text>`.
- `application-spec:queries-implementer` with prompt `$ARGUMENTS[0] <locations_report_text>`.

Both invocations MUST appear as two tool calls in the same assistant turn. Issuing them across two turns is a violation of this step's contract.

Wait for both to complete. Both implementers validate that their dep providers (services from Step 4, settings/exceptions from Step 5, plus the persistence-spec providers) already exist in `containers.py` and abort with a clear error if a provider is missing.

If either implementer aborts, propagate the failure and stop — do not retry.

### Step 7 — Implement integration tests in parallel

Skip this step entirely if `<tests_dir>` was not bound in Step 2 (the `Tests` row was missing). The two test implementers require `<tests_dir>/conftest.py` and `<tests_dir>/integration/conftest.py` to exist (produced by the persistence-spec pipeline's `@integration-test-package-preparer` and the unit-of-work / integration fixtures preparers); they each abort with a one-sentence error if a prerequisite is missing — this orchestrator does not pre-validate.

Emit both `Agent` calls in a single message — do not sequence them:

- `application-spec:commands-tests-implementer` with prompt `$ARGUMENTS[0] <tests_dir>`.
- `application-spec:queries-tests-implementer` with prompt `$ARGUMENTS[0] <tests_dir>`.

Both invocations MUST appear as two tool calls in the same assistant turn. Issuing them across two turns is a violation of this step's contract.

Wait for both to complete. Both agents are append-only and idempotent, so re-running this step against an existing test file only adds missing scenarios. They write to disjoint files (`test_<aggregate>_commands.py` vs `test_<aggregate>_queries.py`) under `<tests_dir>/integration/<aggregate>/` and never modify shared `conftest.py` files.

If either implementer aborts, propagate the failure and stop — do not retry.

### Step 8 — Report

Emit a phased Markdown summary grouping bullets by phase:

- **Scaffolding** — one bullet for `application-files-scaffolder` reporting the count of stub modules in its output (the agent emits a bare bullet list of absolute paths, no status line).
- **Services** — one bullet per `service-implementer` invocation in Step 4 with its single-line status. If Step 4b was skipped (no services), emit the single bullet `- _None_ (services report empty; skipped)`.
- **Settings & Exceptions** — one bullet each for `queries-settings-implementer` and `exceptions-implementer` with their top-line outcomes.
- **Application Services** — one bullet each for `commands-implementer` and `queries-implementer` with their top-line outcomes.
- **Tests** — one bullet each for `commands-tests-implementer` and `queries-tests-implementer` with their top-line outcomes (the `Commands tests ready at ...` / `Queries tests ready at ...` line plus any preceding per-method status). If Step 7 was skipped, emit the single bullet `- _None_ (Tests location not reported; skipped)`.

End with: `Application code generation complete for $ARGUMENTS[0].`
