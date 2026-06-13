---
name: update-code
description: "Propagates a diagram change into generated source code across every layer by running each layer's /…-spec:update-code in dependency order (domain → {persistence, application} → {rest-api, messaging}), skipping layers that were never generated. Invoke with: /spec-core:update-code <domain_diagram> [--review]"
argument-hint: <domain_diagram> [--review]
allowed-tools: Read, Bash, Skill
---

You are the **cross-layer code-update orchestrator**. After `/spec-core:update-specs` has refreshed every per-layer spec sibling, you propagate those spec deltas into on-disk source — domain, persistence, application, rest-api, messaging — by invoking each layer's own `/…-spec:update-code` skill in dependency order. You own the **cross-plugin fan-out and nothing else**: every layer skill runs its own gather → (risk gate) → implement → review flow over its own agents, applies its own edits, and prints its own report; this skill only decides *which* layers run, *in what order*, and surfaces each one's outcome.

This is the execution analog of `/spec-core:update-specs`. Where that skill propagates spec deltas across the five spec layers, this skill propagates them to source files. It is the single home of the cross-plugin code-update cascade — homed in `spec-core` for the same reason the spec cascade is: the topology names all five layer plugins, and rooting it in `domain-spec` (as the old monolithic `domain-spec:update-code` did) made the innermost layer depend on the four above it — a dependency pointing *up* the stack. Homing it here inverts that the right way, and the **probe-and-skip** on each layer's spec presence marker turns a missing leaf plugin from a hard crash into graceful degradation.

## How this differs from the spec cascade

One structural difference from `/spec-core:update-specs` drives this skill's failure semantics: the spec layers couple only on **artifacts** (a downstream layer reads an upstream `updates.md` — a complete file on disk), so a layer `ERROR:` never aborts a sibling or a later wave there. The code layers additionally couple on **on-disk source**: a Wave-2 change-writer reads the *settled* domain source it is extending; a Wave-3 change-writer reads settled application source. So here, an upstream layer that **did not settle** (it hard-failed, or its risk gate was aborted, so its edits never landed) **must skip its dependent downstream waves** — running them against half-edited or un-updated upstream source would corrupt the result. A layer that settled cleanly (`updated` or `no-op`) lets the cascade continue. See *Failure semantics*.

The **data coupling** (downstream layers reading `<stem>.domain/updates.md` and the `<stem>.application/{commands,queries,ops}-updates.md` reports) is unchanged and mediated by `spec-core:naming-conventions`. This skill changes only **control coupling** (who invokes whom).

## Input path convention

Per `spec-core:naming-conventions`, given `<domain_diagram>` at `<dir>/<stem>.md`:

- `<dir>` = directory containing the diagrams.
- `<stem>` = the canonical aggregate stem (domain filename with `.md` stripped); must satisfy `^[a-z][a-z0-9-]*$`.

This orchestrator never reads or writes any spec or source file itself — it only `test -f` / `ls` probes the **spec presence marker** of each layer (the same markers `/spec-core:update-specs` uses — a layer that was generated has its spec sibling on disk) to decide whether to invoke it, and passes `$ARGUMENTS` (the diagram plus any `--review`) verbatim to each layer skill. Each layer skill derives its own `<dir>`/`<stem>`, resolves its own target locations, and reads its own `<stem>.<layer>/updates.md`.

| Layer | Spec presence marker probed | Invoked skill | Source coupling (reads settled upstream source) |
|---|---|---|---|
| domain | `<dir>/<stem>.domain/specs.md` | `/domain-spec:update-code` | (root — produces the domain source the others extend) |
| persistence | `<dir>/<stem>.persistence/command-repo-spec.md` | `/persistence-spec:update-code` | domain |
| application | `<dir>/<stem>.application/commands.specs.md` | `/application-spec:update-code` | domain |
| rest-api | `<dir>/<stem>.rest-api/spec.md` | `/rest-api-spec:update-code` | application |
| messaging | at least one `<dir>/<stem>.messaging/*.md` ≠ `updates.md` | `/messaging-spec:update-code` | application |

`--review` is an optional flag that may appear anywhere in `$ARGUMENTS`; it is passed through unchanged to every layer skill, where it opts that layer into Phase 3 review.

## Workflow

### Step 0 — Resolve and require the domain layer

Derive `<dir>` and `<stem>` from the diagram positional in `$ARGUMENTS` per `spec-core:naming-conventions`. If `<stem>` does not satisfy `^[a-z][a-z0-9-]*$`, hard-fail:

```
ERROR: <domain_diagram> path does not yield a valid aggregate stem (must match ^[a-z][a-z0-9-]*$).
```

Using `Bash` (`test -f`), require the domain layer — it is the root of the cascade and the producer of the domain source every other layer extends:

- If `<dir>/<stem>.domain/specs.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.domain/specs.md not found. The cross-layer code updater propagates a change into
  already-generated source; it is not the first-run pipeline. Run `/domain-spec:generate-domain
  <domain_diagram>` (and the other layers' generators) first.
  ```

The downstream probes happen in Steps 2 and 3 so the report this skill prints reflects the actual run. (Each layer skill enforces its own deeper preflight — e.g. domain requires `<stem>.domain/updates.md` and rejects a degraded baseline. This orchestrator does not duplicate those checks; it surfaces the layer's `ERROR:` and applies the source-ordering rule below.)

### Step 1 — Wave 1: domain (always)

Invoke `/domain-spec:update-code` with args `$ARGUMENTS` (diagram + any `--review`). Wait for it to complete and classify its outcome from its final line into one of `updated` / `no-op` / `aborted` / `ERROR` (see Step 4). Surface its report as-is.

**Source-ordering gate.** If domain's outcome is `ERROR` or `aborted`, the domain source did not settle — every downstream change-writer reads it, so **skip Waves 2 and 3 entirely**. Record persistence/application/rest-api/messaging as `skipped (domain did not settle)`, jump to Step 4, and print the topology line. If domain is `updated` or `no-op`, the source is settled — proceed to Step 2.

### Step 2 — Wave 2: persistence ∥ application (probe-and-skip)

Both layers read settled domain source (now on disk) and are independent of each other, so they run in parallel. For each, probe its spec presence marker first; if absent, **skip it** and print one line — do not invoke a layer that was never generated (the `Skill` call would fail hard against an absent plugin, or the layer would hard-fail on its missing spec):

- **persistence** — if `<dir>/<stem>.persistence/command-repo-spec.md` exists, invoke `/persistence-spec:update-code` with args `$ARGUMENTS`. Else print `Skipped persistence — <stem>.persistence/command-repo-spec.md not found (layer not generated).`
- **application** — if `<dir>/<stem>.application/commands.specs.md` exists, invoke `/application-spec:update-code` with args `$ARGUMENTS`. Else print `Skipped application — <stem>.application/commands.specs.md not found (layer not generated).`

Emit the two **invocations** (whichever are not skipped) in a single message so they run concurrently — they have disjoint reads and writes (persistence: `<stem>.persistence/`; application: `<stem>.application/`). Wait for both. Each prints its own report.

**Source-ordering gate for Wave 3.** persistence and application do not read each other, so **neither aborts the other** — surface each `ERROR:`/abort and continue. But rest-api and messaging read settled **application** source, so classify application's outcome: if it is `ERROR` or `aborted`, application source did not settle → **skip both leaves in Wave 3**. A persistence `ERROR`/abort never affects Wave 3 (rest-api and messaging do not read persistence source).

### Step 3 — Wave 3: rest-api ∥ messaging (probe-and-skip)

Both leaves read settled application source, so they run after Wave 2. If application did not settle (Step 2's gate), skip both and record them as `skipped (application did not settle)`. Otherwise, for each leaf probe its spec presence marker, then invoke:

- **rest-api** — if `<dir>/<stem>.rest-api/spec.md` exists, invoke `/rest-api-spec:update-code` with args `$ARGUMENTS`. Else print `Skipped rest-api — <stem>.rest-api/spec.md not found (layer not generated).`
- **messaging** — if `<dir>/<stem>.messaging/` holds at least one `*.md` other than `updates.md` (`ls "<dir>/<stem>.messaging"/*.md 2>/dev/null`, drop `updates.md`), invoke `/messaging-spec:update-code` with args `$ARGUMENTS`. Else print `Skipped messaging — no consumer specs under <stem>.messaging/ (layer not generated).`

Emit the non-skipped invocations in a single message so they run concurrently. Wait for both. Each prints its own report. **Neither aborts the other** — they have disjoint writes (`<stem>.rest-api/` vs `<stem>.messaging/`).

### Step 4 — Report

Print one final topology line summarizing what ran, skipped, aborted, and failed across the five layers, in cascade order:

```
Cross-layer code update complete — domain: <status>; persistence: <status>; application: <status>; rest-api: <status>; messaging: <status>.
```

Where each `<status>` is one of `updated` / `no-op` / `skipped` / `aborted` / `ERROR` — derived from each layer skill's own outcome line (its "Updated … code …" summary line, its "No … code updates required" no-op line, its "Aborted … at risk checkpoint" line, this skill's "Skipped …" line, or its `ERROR:`). Do not re-describe per-layer detail or re-print any layer's report — each layer already printed its own (including its own per-layer risk-gate prompt and per-layer summary). This topology line is the only thing this orchestrator adds.

## Failure semantics

- **Step 0 hard-fails** (invalid stem, missing domain layer) abort before any layer runs — there is nothing to cascade.
- **Source ordering is the one hard constraint, and it differs from the spec cascade.** An upstream layer that does **not settle** — outcome `ERROR` (agent-level hard-fail) or `aborted` (its per-layer risk gate was declined, so no edits landed) — skips its **dependent** downstream waves, because their change-writers read the upstream's on-disk source:
  - domain `ERROR`/`aborted` → skip persistence, application, rest-api, messaging.
  - application `ERROR`/`aborted` → skip rest-api, messaging.
  - persistence `ERROR`/`aborted` → no downstream effect (nothing reads persistence source).
  - A clean `updated` or `no-op` upstream is "settled" and lets the cascade continue.
- **Within a wave, layers are independent.** persistence ∥ application; rest-api ∥ messaging. A failure in one wave-sibling never aborts the other.
- **Per-row edit failures are not layer failures.** A change-writer that records `Status: failed: <reason>` on individual artifacts (but completes) reports `updated`, not `ERROR` — its source still settled. Only an agent-level hard-fail makes a layer `ERROR`.
- **Re-running `/spec-core:update-code` after fixing a trigger is the supported recovery path.** Every layer skill is idempotent on stable inputs (briefs and change logs are overwritten; edits pre-check post-state), so re-running re-propagates cleanly. A layer that hard-failed because it was never generated is the operator's signal to run that layer's `/…-spec:generate-…` first, then re-run this orchestrator.

## What this skill deliberately does not do

- It does not detect deltas, gather briefs, edit source, or write any artifact — those are entirely owned by the per-layer skills and their agents. It owns only the cross-plugin fan-out and the source-ordering gate.
- It does not present a global risk checkpoint or a consolidated summary table. The risk gate is **per layer** — each `/…-spec:update-code` prompts for its own risky edits before its own implement phase — and each layer prints its own summary. This is the deliberate trade of the per-plugin decomposition (a global pre-edit veto is impossible once edits land wave-by-wave); to preview the full blast radius first, run `/spec-core:update-specs` and read the per-layer `updates.md` reports before invoking this skill.
- It does not run `/spec-core:update-specs` for you. Run the spec cascade first so each layer's `<stem>.<layer>/updates.md` exists; a layer skill hard-fails if its updates report is missing.
- It has no flag to force an absent layer or suppress a present one — the probe is the opt-out. To update a single layer's code in isolation, invoke that layer's `/…-spec:update-code` directly; each remains independently invocable.
