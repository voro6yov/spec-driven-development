---
name: update-code
description: Builds a per-artifact code-update plan from the four `<stem>.<layer>/updates.md` reports by mapping each affected artifact to its driving spec section, extracting the `Pattern:` skill list that must be loaded to implement the change correctly, surfacing genuine ambiguities via a targeted interview, and presenting the plan via plan mode for review. Execution is out of scope — after plan-mode approval, the calling agent applies the plan with the named skills loaded. Invoke with: /update-code <domain_diagram>
argument-hint: <domain_diagram>
allowed-tools: Read, Bash, Write, AskUserQuestion
---

You are a cross-layer **code-update planner**. After `/update-specs` has refreshed every per-layer spec sibling, this skill builds a unified plan that names, for every affected artifact across the five layers, the exact set of pattern skills that must be loaded to implement the change correctly. The plan is presented via plan mode and is the skill's only deliverable.

This is the planning analog of `/update-specs`. Where `/update-specs` cascades through five spec updaters surgically, this skill produces one unified plan spanning the same five layers. **It does not edit any code.** After plan-mode approval, the calling agent (general Claude) walks the plan, loads each artifact's named patterns via the `Skill` tool, and applies the edits — that is out of scope here.

The skill's load-bearing job is the **driving-spec lookup**: for every row in every `Affected Artifacts` table across the five `<stem>.<layer>/updates.md` reports, locate the spec section that drives the change and extract its `Pattern:` skill list. Surfacing the skill list per-artifact is the safety check — without it, downstream execution drifts from the canonical patterns (wrong Guard form, wrong delegation, missing event emission, wrong migration template).

## Inputs

Given `<domain_diagram>` at `<dir>/<stem>.md`, the skill reads:

| File | Owner | Required |
|---|---|---|
| `<dir>/<stem>.domain/updates.md` | `domain-spec:updates-detector` | **Yes** |
| `<dir>/<stem>.persistence/updates.md` | `persistence-spec:command-repo-spec-updates-writer` | Yes if persistence layer exists |
| `<dir>/<stem>.application/updates.md` | `application-spec:application-updates-writer` | Yes if application layer exists |
| `<dir>/<stem>.rest-api/updates.md` | `rest-api-spec:rest-api-updates-writer` | Yes if REST API layer exists |
| `<dir>/<stem>.messaging/updates.md` | `messaging-spec:messaging-updates-writer` | Yes if messaging layer exists |

Plus the spec siblings that drive each row's mapping (`<dir>/<stem>.domain/specs.md`, `<dir>/<stem>.persistence/command-repo-spec.md`, `<dir>/<stem>.application/{commands,queries}.specs.md`, `<dir>/<stem>.rest-api/spec.md`, `<dir>/<stem>.messaging/<consumer>.md`).

## Output

A unified plan written to `<dir>/<stem>.code-plan.md` and surfaced via plan mode. The plan groups changes by layer and per-artifact lists the driving spec section, skill list, and change summary.

## Workflow

### Step 0 — Preflight

Read `<dir>/<stem>.domain/updates.md`. If missing, hard-fail:

```
ERROR: <stem>.domain/updates.md not found. Run `/update-specs <domain_diagram>` before `/update-code`.
```

For each of the other four `<layer>/updates.md` files, probe via `Bash` (`test -f`). Mark each layer **active** iff its `updates.md` exists; mark it **inactive** otherwise (it means that layer was never generated). The domain layer is always active.

If the domain `updates.md` Summary contains a `_warning: HEAD ...` line (degraded baseline), hard-fail:

```
ERROR: Degraded baseline in <stem>.domain/updates.md. Re-run `/update-specs` after fixing HEAD, or regenerate via `/generate-code <domain_diagram>`.
```

### Step 1 — No-op early exit

For each active layer, check whether its `updates.md` shows `_no changes_` under every body section AND has an empty (or absent) `Affected Artifacts` table. If **all** active layers are no-ops, print `No code updates required across active layers.` and exit cleanly without entering plan mode.

### Step 2 — Build the artifact-pattern mapping

For each active layer, parse its `updates.md` `Affected Artifacts` table. Each row becomes one mapping entry:

```
{
  layer, path, action ("add"|"modify"),
  driving_section,                          # verbatim from the table
  spec_section,                             # resolved per-layer (rules below)
  patterns: [<skill>, ...],                 # extracted from spec_section
  summary,                                  # one-line description
  kind,                                     # classified below
}
```

**Driving-section → spec-section → pattern list resolution, per layer:**

- **domain** — derive the class name from the artifact path stem, locate `**\`<ClassName>\`**` in `<stem>.domain/specs.md`. The `**Pattern**:` line follows within ≤2 lines and lists `;`-separated skills.
- **persistence** — the `Driving section` cell names a §2 sub-table (Tables / Mappers / Repository / Migrations / Context Integration). Look up the matching row in that sub-table in `<stem>.persistence/command-repo-spec.md`; the `Pattern` and `Template` columns give the skill directly.
- **application** — for `exceptions.py` rows, look up the exception block in `<stem>.application/{commands,queries}.specs.md` and read its `**Pattern**:` line. For `<aggregate>_commands.py` / `<aggregate>_queries.py` rows, the patterns are `application-spec:commands` or `application-spec:queries-pattern` plus the method's class-block patterns from `<stem>.domain/specs.md` (re-used because methods orchestrate against the aggregate).
- **rest-api** — patterns are kind-derived (the rest-api spec doesn't carry explicit `Pattern:` lines): surface kind maps to one of `rest-api-spec:endpoints`, `rest-api-spec:nested-resource-endpoints`, `rest-api-spec:command-action-endpoint`, `rest-api-spec:file-upload-endpoint`; serializer rows map to `rest-api-spec:request-serializers` / `rest-api-spec:response-serializers` / `rest-api-spec:pagination-serializers`.
- **messaging** — patterns are kind-derived: handler rows → `messaging-spec:domain-event-handlers` or `messaging-spec:command-handlers`; external event rows → `messaging-spec:message-events-external`; dispatcher rows → `messaging-spec:domain-event-dispatchers` or `messaging-spec:multi-aggregate-domain-event-dispatchers`.

**Kind classification** (informs the executor, not the planner) per `notes/code-updater-approach-c.md`:

- `add` on a class file → `class-impl` (scaffold + whole-module generation).
- `modify` on a mechanical class (VO, entity, event, command, TypedDict, repo ABC, service ABC) → `whole-module-impl` (Approach B regen).
- `modify` on the aggregate root, `<aggregate>_commands.py`, `<aggregate>_queries.py`, an endpoint module, a serializer module, or a handler module → `per-member-edit` (Approach C surgery).
- `add` on a migration YAML, a new endpoint module, a new serializer module → `new-file` (scaffold + implement chain).
- Any `__init__.py` row → `init-py` (re-derived globally).
- Any `test_*.py` row → `test-impl` (per-test surgery).

### Step 3 — Surface ambiguities

Two ambiguity classes warrant interview; everything else is mechanical.

- **A — Pattern list changed on a touched spec block.** If the spec section's `Pattern:` list was modified by `/update-specs` (added/removed a skill compared to HEAD), flag the affected artifacts so the operator can confirm the new pattern set applies on disk. Detect by checking whether the spec section is listed under `## Per-Class Changes` (or layer-equivalent) in the layer's `updates.md`.
- **B — Multi-pattern conflict on a per-member edit.** When an aggregate-root method is touched (`per-member-edit` kind on the aggregate file), the class-level Pattern list may include 4+ skills, not all of which apply to every method. Surface the touched methods and let the operator pick the applicable subset per method.

Collect all ambiguities into one or more `AskUserQuestion` calls (cap **4 questions per call**, mutually-exclusive 2–4 options each; first option is always `Apply the patterns as listed in the spec (recommended)`). If there are **zero** ambiguities, skip Step 3 entirely. Do not invent questions to fill the cap.

Record each answer; merge into the mapping table as a `patterns_override` field on affected rows.

### Step 4 — Emit the plan

Write `<dir>/<stem>.code-plan.md` with this shape:

```markdown
# Code Update Plan — <stem>

_Source: <stem>.domain/updates.md (+ active per-layer updates.md). Generated by /update-code._

## Summary

- Layers active: <comma-separated list>
- Artifacts to add: <n>
- Artifacts to modify: <n>
- Ambiguities resolved: <n> (or "none")

## Layer: domain

### <path> — <action>

- **Driving spec section:** `<path>#<heading>`
- **Kind:** <class-impl | whole-module-impl | per-member-edit | init-py | test-impl | new-file>
- **Patterns to apply:** <skill1>, <skill2>, ...
- **Change summary:** <one line>
- **Executor hint:** <existing agent name | "direct edit">

(...repeat per artifact, then per layer in order: persistence, application, rest-api, messaging...)

## Suggested execution order

(This is guidance for the calling agent — not enforced by this skill.)

1. domain (added classes → whole-module regen → per-member edits → exceptions → tests)
2. persistence (tables → mappers → repository → migrations scaffold+implement → context integration)
3. application (exceptions → settings → commands → queries → tests)
4. rest-api (serializers → endpoints → app integration)
5. messaging (external events → handlers → dispatcher → wiring → tests)
6. final pass: regenerate `__init__.py` for each touched package, then run the project formatter (ruff / black)
```

The plan is **always written**, even when no ambiguities surfaced — the operator may still want to inspect or hand-edit it.

### Step 5 — Enter plan mode

Hand control back to the calling agent with one final instruction:

> Enter plan mode and present the contents of `<dir>/<stem>.code-plan.md` inline for review. On approval, execute the plan by walking it in the suggested order: for each artifact, invoke `Skill` for every entry in its `Patterns to apply` list, then apply the change per the executor hint (existing agent or direct Edit).

The skill itself stops here. It does not invoke `EnterPlanMode`, does not edit any code, and does not chain to any executor. Execution semantics are entirely owned by the calling agent.

## Failure semantics

- Every step that aborts emits one `ERROR:` line and exits. There are no partial writes to roll back — the only file this skill writes is the plan itself, and only after Step 4.
- The plan file at `<dir>/<stem>.code-plan.md` survives every abort path. The operator can inspect or hand-edit it before retry.
- Every step is idempotent on stable inputs: re-running `/update-code` on the same updates.md set regenerates the same plan (modulo LLM drift in summaries).

## What this skill deliberately does not do

- It does not edit any source file or test file. Execution is delegated to the calling agent post-plan-mode-approval.
- It does not re-detect spec deltas. The five `updates.md` files are authoritative — run `/update-specs` first.
- It does not re-read diagrams. All inputs come from the spec siblings.
- It does not run tests, format code, or regenerate `__init__.py` files. Those are executor concerns and appear only as guidance in the plan's "Suggested execution order".
- It does not invoke `EnterPlanMode`. That is the calling agent's responsibility after the plan is on disk.
- It does not handle aggregate-root removals or stereotype changes — `/update-specs` hard-fails on those before this skill is ever reached.
- It does not detect hand-edited code on disk. Operators with hand-tuned method bodies must reconcile manually after execution.
