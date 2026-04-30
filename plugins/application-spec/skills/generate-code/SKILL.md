---
name: generate-code
description: Implements the application layer for an aggregate from its merged commands spec, merged queries spec, and services report siblings. Resolves target locations once, scaffolds the application/infrastructure stubs, fans out per-service implementers, wires settings + exceptions, implements the commands + queries application services, and finally generates the integration tests for both. Invoke with: /application-spec:generate-code <commands_diagram> <queries_diagram> <domain_diagram>
argument-hint: <commands_diagram> <queries_diagram> <domain_diagram>
allowed-tools: Bash, Agent
---

You are an application implementation orchestrator. Implement the application layer for the aggregate described by `$ARGUMENTS[0]` (commands diagram), `$ARGUMENTS[1]` (queries diagram), and `$ARGUMENTS[2]` (domain diagram). The skill consumes the merged sibling artifacts that `/application-spec:generate-specs` produces — it does not regenerate them.

## Sibling file convention

For each diagram at `<dir>/<stem>.md`, agents derive `<stem>` by stripping the trailing `.md`. The three sibling artifacts consumed here are:

| Diagram | Sibling artifact | Bound to |
|---|---|---|
| `$ARGUMENTS[0]` | `<commands_stem>.specs.md` | `<commands_spec_file>` |
| `$ARGUMENTS[1]` | `<queries_stem>.specs.md` | `<queries_spec_file>` |
| `$ARGUMENTS[2]` | `<domain_stem>.services.md` | `<services_report>` |

If any of these artifacts is missing the downstream agents abort with their own one-sentence errors — this orchestrator does not pre-validate.

## Workflow

### Step 1 — Compute sibling paths

Derive the three sibling artifact paths by string substitution on the diagram arguments. For each diagram path, strip the trailing `.md` suffix and append the artifact suffix:

- `<commands_spec_file>` = `$ARGUMENTS[0]` with `.md` replaced by `.specs.md`
- `<queries_spec_file>` = `$ARGUMENTS[1]` with `.md` replaced by `.specs.md`
- `<services_report>` = `$ARGUMENTS[2]` with `.md` replaced by `.services.md`

If any diagram path does not end in `.md`, fall back to appending the suffix unchanged. Do not shell-expand — substitute these strings directly when constructing prompts in subsequent steps. These are passed verbatim to downstream agents.

### Step 2 — Find target locations

Invoke `application-spec:target-locations-finder` with an empty prompt. Wait for completion.

Capture the agent's full Markdown table output verbatim as `<locations_report_text>`. This text is the locations argument passed to every downstream agent in Steps 3–6. Pass it verbatim — do not trim, summarize, or reformat it.

Parse one value from the report for use in Step 7:

- **`<tests_dir>`** — read the `Absolute path` cell of the `Tests` row. Bind that value verbatim — it is an absolute path (e.g. `/repo/src/tests`). If the `Tests` row is missing or its path cell is empty, skip Step 7 entirely (emit a single bullet in the Step 8 report under the **Tests** phase noting `skipped (Tests location not reported)`).

### Step 3 — Scaffold application and infrastructure stubs

Invoke `application-spec:application-files-scaffolder` with prompt `<commands_spec_file> <queries_spec_file> <locations_report_text>`. Wait for completion.

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
$ARGUMENTS[0] $ARGUMENTS[1] <services_report> <locations_report_text> <service_identifier>
```

(That is: commands diagram, queries diagram, services report, locations report, and the per-agent `<service_identifier>`.)

All invocations launch in parallel — do not sequence them. Wait for every invocation to complete before proceeding. Each agent operates on its own service end-to-end (application interface stubs, infrastructure stub, test fake, DI provider, and conftest fixtures) and does not touch the others' files.

### Step 5 — Wire settings and exceptions in parallel

Emit both `Agent` calls in a single message — do not sequence them:

- `application-spec:queries-settings-implementer` with prompt `<locations_report_text>`.
- `application-spec:exceptions-implementer` with prompt `<commands_spec_file> <queries_spec_file> <locations_report_text>`.

Both invocations MUST appear as two tool calls in the same assistant turn. Issuing them across two turns is a violation of this step's contract.

Wait for both to complete. The settings implementer fills every `<aggregate>_queries_settings.py` stub under the application package; the exceptions implementer appends fully implemented application exception classes (and updates the `..shared` import + `__all__` and the aggregate `__init__.py` wiring) on the domain aggregate's `exceptions.py`.

These two agents touch disjoint files and are safe to run concurrently. They must run after Step 4 only loosely (they do not depend on service-implementer output) but before Step 6, because the commands/queries implementers consume the settings class and the application exceptions.

### Step 6 — Implement commands and queries in parallel

Emit both `Agent` calls in a single message — do not sequence them:

- `application-spec:commands-implementer` with prompt `<commands_spec_file> <locations_report_text>`.
- `application-spec:queries-implementer` with prompt `<queries_spec_file> <locations_report_text>`.

Both invocations MUST appear as two tool calls in the same assistant turn. Issuing them across two turns is a violation of this step's contract.

Wait for both to complete. Both implementers validate that their dep providers (services from Step 4, settings/exceptions from Step 5, plus the persistence-spec providers) already exist in `containers.py` and abort with a clear error if a provider is missing.

If either implementer aborts, propagate the failure and stop — do not retry.

### Step 7 — Implement integration tests in parallel

Skip this step entirely if `<tests_dir>` was not bound in Step 2 (the `Tests` row was missing). The two test implementers require `<tests_dir>/conftest.py` and `<tests_dir>/integration/conftest.py` to exist (produced by the persistence-spec pipeline's `@integration-test-package-preparer` and the unit-of-work / integration fixtures preparers); they each abort with a one-sentence error if a prerequisite is missing — this orchestrator does not pre-validate.

Emit both `Agent` calls in a single message — do not sequence them:

- `application-spec:commands-tests-implementer` with prompt `<tests_dir> <commands_spec_file>`.
- `application-spec:queries-tests-implementer` with prompt `<tests_dir> <queries_spec_file>`.

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

End with: `Application code generation complete for $ARGUMENTS[0] and $ARGUMENTS[1].`
