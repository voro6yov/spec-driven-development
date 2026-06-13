---
name: update-specs
description: "Propagates a diagram change across every generated spec layer by running each layer's /…-spec:update-specs in dependency order (domain → {persistence, application} → {rest-api, messaging}), skipping layers that were never generated. Invoke with: /spec-core:update-specs <domain_diagram>"
argument-hint: <domain_diagram>
allowed-tools: Read, Bash, Skill
---

You are the **cross-layer spec-update orchestrator**. Given a domain diagram whose working tree differs from `git HEAD`, you propagate that change through every spec layer the aggregate has generated — domain, persistence, application, rest-api, messaging — by invoking each layer's own `/…-spec:update-specs` skill in dependency order. You own the **cross-plugin fan-out and nothing else**: every layer skill detects its own deltas, regenerates its own specs, and emits its own `updates.md`; this skill only decides *which* layers run, *in what order*, and *with what flag*, and surfaces each one's outcome.

This skill is the single home of the cross-plugin update cascade. It replaces the old in-skill chaining where `domain-spec:update-specs` fanned out to persistence/application from its own tail (Step 10) and `application-spec:update-specs` re-cascaded to rest-api/messaging from its own tail (Step 9). Those two skills are now **pure single-plugin updaters** that no longer invoke any other plugin; the topology they used to encode lives here, in one place, in the plugin that already owns every cross-plugin convention (`spec-core`). See `spec-core:naming-conventions` for the artifact paths each layer reads and writes.

## Why this is homed in spec-core

The cascade is a cross-plugin concern: it names `domain-spec`, `persistence-spec`, `application-spec`, `rest-api-spec`, and `messaging-spec` by their skill namespaces. Homing it in `domain-spec` (as the old design did) made the innermost layer depend on the four layers above it — a dependency pointing *up* the stack, and an unenforceable one (there is no manifest-level dependency mechanism, so a missing leaf plugin made the old Step 10 `Skill` call fail hard). Homing it here inverts that the right way: `spec-core` is the glue every spec plugin already depends on, and this orchestrator **probes each layer's spec artifact on disk and skips the layer when it is absent**, turning the old hard crash into graceful degradation and a natural opt-out — run only the layers you have generated.

The **data coupling** (downstream layers reading `<stem>.domain/updates.md` and the `<stem>.application/{commands,queries,ops}-updates.md` detector reports) is unchanged and lives on the same documented cross-plugin paths — that coupling is healthy (a layer depends on an *artifact*, mediated by `spec-core:naming-conventions`, not on a *caller*). This skill changes only the **control coupling** (who invokes whom).

## Input path convention

Per `spec-core:naming-conventions`, given `<domain_diagram>` at `<dir>/<stem>.md`:

- `<dir>` = directory containing the diagrams.
- `<stem>` = the canonical aggregate stem (domain filename with `.md` stripped); must satisfy `^[a-z][a-z0-9-]*$`.

Each layer's per-plugin folder is `<dir>/<stem>.<layer>` (`<stem>.domain`, `<stem>.persistence`, `<stem>.application`, `<stem>.rest-api`, `<stem>.messaging`). This orchestrator never reads or writes any spec file itself — it only `test -f` / `ls` probes the **presence marker** of each layer to decide whether to invoke it, and passes `$ARGUMENTS[0]` verbatim to each layer skill. Every layer skill derives its own `<dir>`/`<stem>` from that argument.

| Layer | Presence marker probed | Invoked skill | Reads (data coupling) |
|---|---|---|---|
| domain | `<dir>/<stem>.domain/specs.md` | `/domain-spec:update-specs` | (produces `<stem>.domain/updates.md`) |
| persistence | `<dir>/<stem>.persistence/command-repo-spec.md` | `/persistence-spec:update-specs` | `<stem>.domain/updates.md` |
| application | `<dir>/<stem>.application/commands.specs.md` | `/application-spec:update-specs` | `<stem>.domain/updates.md`; produces `<stem>.application/{commands,queries,ops}-updates.md` |
| rest-api | `<dir>/<stem>.rest-api/spec.md` | `/rest-api-spec:update-specs` | `<stem>.domain/updates.md` + the three `<stem>.application/*-updates.md` reports |
| messaging | at least one `<dir>/<stem>.messaging/*.md` ≠ `updates.md` | `/messaging-spec:update-specs` | `<stem>.domain/updates.md` + `<stem>.application/{commands,ops}-updates.md` |

## Workflow

### Step 0 — Resolve and require the domain layer

Derive `<dir>` and `<stem>` from `$ARGUMENTS[0]` per `spec-core:naming-conventions`. If `<stem>` does not satisfy `^[a-z][a-z0-9-]*$`, hard-fail:

```
ERROR: <domain_diagram> path does not yield a valid aggregate stem (must match ^[a-z][a-z0-9-]*$).
```

Using `Bash` (`test -f`), require the domain layer — it is the root of the cascade and the producer of `<stem>.domain/updates.md` that every other layer reads:

- If `<dir>/<stem>.domain/specs.md` is missing → hard-fail:

  ```
  ERROR: <dir>/<stem>.domain/specs.md not found. The cross-layer updater propagates a change across
  already-generated layers; it is not the first-run pipeline. Run `/domain-spec:generate-domain
  <domain_diagram>` (and the other layers' generators) first.
  ```

No other layer is probed yet — the downstream probes happen in Steps 2 and 3 so the report this skill prints reflects the actual run.

### Step 1 — Wave 1: domain (always)

Invoke `/domain-spec:update-specs` with args `$ARGUMENTS[0]`. Wait for it to complete.

This regenerates the domain-side specs **and always (re)writes `<dir>/<stem>.domain/updates.md`** via its Step 0 detector — even on its no-op early-exit or a preflight hard-fail, the detector ran first, so the report exists for the downstream waves to read. The domain skill prints its own outcome line; surface it as-is.

**Do not abort the cascade on a domain-side `ERROR:`.** A domain preflight hard-fail (degraded baseline, stereotype change, aggregate-root removal) still leaves a usable `<stem>.domain/updates.md` on disk, and the downstream layers handle those conditions themselves — persistence hard-fails cleanly on the same condition, while application/rest-api/messaging *disable only their domain axis* and still process their app-service axes. Proceed to Step 2 regardless; the only thing that stops the cascade after Step 0 is the absence of downstream layers.

(The lone exception worth noting: if the domain skill's *detector* itself failed so hard that `<stem>.domain/updates.md` was not written, the downstream layers will surface their own missing-report errors in Steps 2–3. That is the correct, per-layer signal — this orchestrator does not second-guess it.)

### Step 2 — Wave 2: persistence ∥ application (probe-and-skip)

Both layers depend only on `<stem>.domain/updates.md` (now on disk) and are independent of each other, so they run in parallel. For each, probe its presence marker first; if absent, **skip it** and print one line — do not invoke a layer that was never generated (the `Skill` call would fail hard against an absent plugin or hard-fail inside the layer on a missing spec):

- **persistence** — if `<dir>/<stem>.persistence/command-repo-spec.md` exists, invoke `/persistence-spec:update-specs` with args `$ARGUMENTS[0]`. Else print `Skipped persistence — <stem>.persistence/command-repo-spec.md not found (layer not generated).`
- **application** — if `<dir>/<stem>.application/commands.specs.md` exists, invoke `/application-spec:update-specs` with args `$ARGUMENTS[0]`. Else print `Skipped application — <stem>.application/commands.specs.md not found (layer not generated).`

Emit the two **invocations** (whichever are not skipped) in a single message so they run concurrently. Persistence is domain-driven and receives no flag. Application produces the three app-service-axis detector reports (`commands-updates.md`, `queries-updates.md`, `ops-updates.md`) at its own Step 0 as part of its normal run — Wave 3 depends on those existing, which is why application runs here, before rest-api/messaging.

Wait for both to complete. Each prints its own report. **Neither aborts the other, and a layer `ERROR:` does not abort the cascade** — surface each `ERROR:` line as it returns and continue. They have disjoint reads and writes (persistence: `<stem>.persistence/`; application: `<stem>.application/`).

### Step 3 — Wave 3: rest-api ∥ messaging (probe-and-skip, detector-flag by disk state)

Both layers depend on the app-service-axis detector reports application produces, so they run after Wave 2. Decide the `--detectors-fresh` flag from **disk state**, not from application's outcome — this is robust whether application ran, was skipped, or hard-failed before producing the reports:

- `commands_fresh` ⇐ `test -f <dir>/<stem>.application/commands-updates.md`
- `queries_fresh` ⇐ `test -f <dir>/<stem>.application/queries-updates.md`

For each leaf, probe its presence marker, then invoke:

- **rest-api** — if `<dir>/<stem>.rest-api/spec.md` exists:
  - if `commands_fresh` AND `queries_fresh` → invoke `/rest-api-spec:update-specs` with args `$ARGUMENTS[0] --detectors-fresh` (it reuses application's reports and produces only the ops report itself).
  - else → invoke `/rest-api-spec:update-specs` with args `$ARGUMENTS[0]` (no flag — it produces all detector reports itself).
  - Else print `Skipped rest-api — <stem>.rest-api/spec.md not found (layer not generated).`
- **messaging** — if `<dir>/<stem>.messaging/` holds at least one `*.md` other than `updates.md` (`ls "<dir>/<stem>.messaging"/*.md 2>/dev/null`, drop `updates.md`):
  - if `commands_fresh` → invoke `/messaging-spec:update-specs` with args `$ARGUMENTS[0] --detectors-fresh` (messaging reads only the commands report; it produces the ops report itself).
  - else → invoke `/messaging-spec:update-specs` with args `$ARGUMENTS[0]` (no flag).
  - Else print `Skipped messaging — no consumer specs under <stem>.messaging/ (layer not generated).` (Messaging also exits cleanly on its own when its folder is empty, so this probe is belt-and-braces.)

Emit the non-skipped invocations in a single message so they run concurrently. Wait for both. Each prints its own report. **Neither aborts the other, and a leaf `ERROR:` does not abort the cascade** — they have disjoint writes (`<stem>.rest-api/` vs `<stem>.messaging/`).

The `--detectors-fresh` token is now an **orchestrator→leaf** optimization, passed uniformly by this skill, not a leaf→leaf handshake: when application populated the commands/queries reports this run, the leaves skip re-detecting those axes and read the reports directly. They always produce their own ops report regardless of the flag (application's `--detectors-fresh` promise covers only the commands/queries axes).

### Step 4 — Report

Print one final topology line summarizing what ran, skipped, and failed across the five layers, in cascade order:

```
Cross-layer update complete — domain: <status>; persistence: <status>; application: <status>; rest-api: <status>; messaging: <status>.
```

Where each `<status>` is one of `updated` / `no-op` / `skipped` / `ERROR` — derived from each layer skill's own outcome line (its summary line, its "no … updates required" no-op line, this skill's "Skipped …" line, or its `ERROR:`). Do not re-describe per-layer detail or re-print any layer's report — each layer already printed its own. This is the only line this orchestrator adds beyond the per-layer reports and the skip lines.

## Failure semantics

- **Step 0 hard-fails** (invalid stem, missing domain layer) abort before any layer runs — there is nothing to cascade. Re-run after generating the domain layer.
- **Every layer runs independently.** A layer's `ERROR:` is surfaced verbatim and does **not** abort its wave-sibling or any later wave. This preserves the old design's "no skill aborts the other" property, now centralized: persistence and application are independent; rest-api and messaging are independent; and a Wave-2 failure does not stop Wave 3 except through the data dependency (if application failed to produce the detector reports, Wave 3 simply runs the leaves without `--detectors-fresh`, and they self-detect).
- **Ordering is the only hard constraint.** Wave 1 (domain) before Wave 2 because everything reads `<stem>.domain/updates.md`; Wave 2's application before Wave 3 because rest-api/messaging read application's detector reports. Within a wave, layers are parallel.
- **Re-running `/spec-core:update-specs` after fixing a trigger is the supported recovery path.** Every layer skill is idempotent on stable inputs (each re-derives its reports from disk + git), so re-running re-propagates cleanly. A layer that hard-failed because it was never generated is the operator's signal to run that layer's `/…-spec:generate-…` (or `specs-generator`) first, then re-run this orchestrator.

## What this skill deliberately does not do

- It does not detect deltas, regenerate specs, or write any `updates.md` — those are entirely owned by the per-layer skills. It owns only the cross-plugin fan-out.
- It does not produce the `<stem>.domain/updates.md` or `<stem>.application/{commands,queries,ops}-updates.md` reports — domain and application produce them inside their own runs. This skill only sequences the runs so the reports exist before their consumers read them.
- It does not auto-update generated code in any layer — that is the cross-layer `/update-code` flow, a separate concern.
- It has no flag to force a layer that is absent on disk, and no flag to suppress a layer that is present — the probe is the opt-out (don't generate a layer, and it won't be cascaded to). To update a single layer in isolation, invoke that layer's `/…-spec:update-specs` directly; each remains independently invocable.
- It does not run the `domain-spec`/`application-spec` cascade tails that used to live in those skills — they no longer exist. This is the only place the cross-layer cascade is expressed.
