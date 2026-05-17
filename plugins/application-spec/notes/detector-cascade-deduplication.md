# Detector Cascade Deduplication — Design

This note designs how to avoid the **triple invocation** of the two app-service-axis detectors (`commands-updates-detector`, `queries-updates-detector`) when domain `/update-specs` cascades through the three downstream `…-spec:update-specs` skills (application, rest-api, messaging).

It is the consolidated follow-up for the three "Open questions → cascade-deduplication" items in:

- [`commands-queries-integration-approach.md`](commands-queries-integration-approach.md) (application-spec)
- [`../../rest-api-spec/notes/commands-queries-integration-approach.md`](../../rest-api-spec/notes/commands-queries-integration-approach.md)
- [`../../messaging-spec/notes/commands-queries-integration-approach.md`](../../messaging-spec/notes/commands-queries-integration-approach.md)

For the detector agents themselves, see [`../agents/commands-updates-detector.md`](../agents/commands-updates-detector.md) and [`../agents/queries-updates-detector.md`](../agents/queries-updates-detector.md). For the cascade orchestrator that fans out the three downstream skills, see [`../../domain-spec/skills/update-specs/SKILL.md`](../../domain-spec/skills/update-specs/SKILL.md) (Steps 10–13).

---

## Recommendation

**Approach B — each detector self-guards via a HEAD-hash sentinel embedded in its report.** Implementation lives entirely in the two detector agents. No cascade-orchestrator or downstream-skill changes are required. Single-plugin landing; preserves standalone invocability trivially; first-run safe by construction; partial-write safe by construction.

The other three approaches considered (cascade-owned invocation, skill-level freshness checks, status quo) are rejected for the reasons in [§ Approaches considered](#approaches-considered).

---

## Problem statement

The application-spec integration ([`commands-queries-integration-approach.md`](commands-queries-integration-approach.md)) already invokes both detectors at its `update-specs` Step 0g. The rest-api-spec and messaging-spec integration notes propose the same Step-0g pattern. Once all three integrations land, the cascade triggered by domain `/update-specs` runs:

```
domain /update-specs
├── Step 10 — persistence (no app-service detectors)
├── Step 11 — application /update-specs
│   └── Step 0g: @commands-updates-detector, @queries-updates-detector  ← invocation #1
├── Step 12 — rest-api /update-specs
│   └── Step 0g: @commands-updates-detector, @queries-updates-detector  ← invocation #2
└── Step 13 — messaging /update-specs
    └── Step 0g: @commands-updates-detector  ← invocation #3 (commands only)
```

That is **5 detector invocations** per cascade — three of the commands detector and two of the queries detector — when one of each would suffice. The redundant runs are **correctness-safe** (detectors are byte-stable on stable inputs modulo LLM prose-summary drift), but **wasteful**:

- **LLM tokens** — each detector spawn loads the auto-attached `application-spec:naming-conventions` + `application-spec:application-updates-report-template` skills (~5–10k tokens of context), reads two files, parses the Mermaid, computes the diff, and on a non-trivial change emits one LLM-written paragraph per non-empty prose section delta (~200–1000 output tokens per section). On a clean working tree the prose-summary step does not fire, but the agent still pays the context-load + parse overhead. Conservatively, each redundant detector call is ~10–20k input tokens + ~1–3k output tokens.
- **Latency** — the two detectors within one skill's Step 0g already run in parallel, but the three skills' Step 0g blocks themselves are serial in the cascade. Two redundant Step-0g cycles add roughly 5–15 s each.
- **File I/O** — three pairs of `git show HEAD:<diagram>` + `Read <diagram>` calls instead of one. Negligible by itself but compounds with the agent-spawn overhead.

A typical cascade run pays ~30–60k redundant tokens and ~10–30 s of redundant latency. Not catastrophic; not free.

The design target is **one effective detector run per (diagram, working-tree-state)** across a cascade, with **zero additional coordination state** the operator has to think about.

---

## Constraints

Any chosen approach must preserve all four:

1. **Standalone invocability** — each downstream `update-specs` skill must remain runnable in isolation; the operator can invoke `/rest-api-spec:update-specs <domain>` without first running domain `/update-specs`. The detectors themselves must remain ad-hoc invocable via `@commands-updates-detector` / `@queries-updates-detector`.
2. **First-run safety** — on a clean repo where the reports don't yet exist, the chosen approach must produce them. No skip-on-cache-miss loop.
3. **Partial-write safety** — if a detector aborts mid-run (LLM error, IO failure, kill), the next invocation must regenerate the report. A partial report must not be treated as fresh.
4. **Per-plugin landability** — the rest-api-spec and messaging-spec integrations are still proposed (their `update-specs` skills don't yet invoke detectors). The dedup design should not block those integrations from landing per-plugin.

---

## Approaches considered

### A. Cascade orchestrator invokes detectors once before fan-out

Domain `/update-specs` inserts a new step (call it **Step 9.5**) between the domain-side Steps 0–9 and the cascade Steps 10–13. At Step 9.5 it invokes both detectors once. Each downstream `update-specs` skill's Step 0g checks for a fresh on-disk report and skips its own detector invocation when fresh.

**Mechanism for "fresh"** — must be chosen:

- **A.1 (mtime)** — downstream skill checks `mtime(<plugin_dir>/<side>-updates.md) > mtime(<diagram>)`. Cheapest. Fails on file-touch / git-checkout (which resets mtimes) and across worktree switches.
- **A.2 (sentinel hash in report)** — Step 9.5 detector embeds `<!-- baseline-head: <hash>; working-tree: <hash> -->` in the report. Each downstream skill reads the sentinel, recomputes the two hashes (`git rev-parse HEAD:<path>` + `git hash-object <path>`), skips if both match. Robust; survives clock skew and file touches.
- **A.3 (per-run marker file)** — Step 9.5 writes `<plugin_dir>/.fresh-from-cascade` alongside the report; downstream skills delete the marker after use. Survives standalone runs only by accident (file may persist from prior cascade); adds a side-channel state file the operator has to know about.

**Pros**:
- Cleanest conceptual story: producers run once.
- Downstream-skill behavior is "if fresh, skip; else run" — symmetric and explicit.

**Cons**:
- **Four-file change**: domain `update-specs/SKILL.md` adds Step 9.5; each downstream skill's Step 0g adds the freshness check; possibly the detectors themselves add the sentinel (under A.2). One atomic landing across four plugins or three sub-landings with intermediate broken states.
- **Standalone path still costs full detector runs** — the dedup only fires inside the cascade, not when the operator invokes a downstream skill directly. Standalone is the operator's most common ad-hoc workflow, so most of the win is missed.
- **First-run handling**: Step 9.5 needs its own logic for "what if the application detectors hard-fail" — does the cascade abort? Each downstream skill already had its own answer; now two layers do.
- **Mtime variant (A.1)** is fragile; **sentinel variant (A.2)** does most of B's work but in the wrong place (skill prose, not detector code); **marker-file variant (A.3)** is brittle.

### B. Each detector self-guards via a HEAD-hash sentinel ⭐ recommended

Each detector, at the start of its run:

1. Compute `head_hash = git rev-parse HEAD:<repo-relative-diagram-path>` (the HEAD blob hash of the diagram). If empty / first-run, treat as the sentinel value `none`.
2. Compute `wt_hash = git hash-object -- <diagram>` (the working-tree blob hash of the diagram).
3. `Read` the existing `<output_file>` if it exists. Extract the `<!-- detector-baseline: head=<hash>; working-tree=<hash> -->` sentinel from its first line. If absent, treat as `none/none`.
4. If `head_hash == sentinel.head` AND `wt_hash == sentinel.wt` → the report is fresh for this exact pair of blobs. Print `<side>-updates.md is fresh against current HEAD and working tree; skipping re-generation.` and exit 0. Do not rewrite.
5. Otherwise: proceed with the existing workflow (Steps 1–8). After successfully rendering the report body, **prepend** the new sentinel line `<!-- detector-baseline: head=<head_hash>; working-tree=<wt_hash> -->\n` as line 1 of the file before writing.

The sentinel is the **last** byte sequence prepared and the **first** line written, so it is part of the atomic `Write` call. A partial / aborted run leaves either no file (Write never executed) or no sentinel (an out-of-band failure between body assembly and Write) — both cases fail the equality check on the next run and force regeneration.

**Pros**:

- **Single-plugin change**: only the two detector agents (`commands-updates-detector.md`, `queries-updates-detector.md`) need patches. The `application-updates-report-template` skill can optionally document the sentinel for downstream consumers, but the rendering is mechanical and lives in the detector.
- **Standalone-invocability free**: the detector handles freshness internally regardless of caller. Ad-hoc `@commands-updates-detector` runs are dedup'd identically to cascade-triggered runs.
- **First-run safe by construction**: no existing report → no sentinel → mismatch → full run.
- **Partial-write safe by construction**: any abort before the final `Write` leaves no sentinel; the next run regenerates.
- **Symmetric across the three downstream skills**: each skill keeps its existing Step 0g `Agent` invocation; the agent itself fast-paths.
- **No new coordination state**: no marker files, no per-run identifiers, no orchestrator hand-offs. The sentinel lives in the artifact it describes.
- **Composes with future per-plugin integrations**: rest-api-spec and messaging-spec can land their Step 0g invocations in isolation; the detectors deduplicate without those skills knowing.

**Cons**:

- **Adds a sentinel line to the rendered report** — a `<!--`-style HTML comment on line 1. Invisible in rendered Markdown; trivially `git diff`-noisy on the first roll-out commit. The existing `application-updates-report-template` already has rendering rules; the sentinel is documented there alongside the other always-emitted scaffolding.
- **LLM prose-summary drift no longer regenerates** — when both blob hashes match, the prose-summary step is skipped on subsequent runs, so byte-stable LLM drift is hidden. This is the intended behavior, not a regression: drift in the prose summary across identical-input runs is `git diff` noise that the project already tolerates, and skipping the regen is preferable to producing churn.
- **Sentinel is per-detector, not per-skill** — three skills sharing the two report files all benefit identically; the sentinel doesn't know which skill "consumed" it. (This is a feature, not a bug, but worth calling out.)
- **Two `git` shell-outs per detector invocation** — `git rev-parse HEAD:<path>` and `git hash-object -- <path>`, each ~5–10 ms. Negligible.

### C. Each downstream skill checks freshness itself

Each `update-specs` skill's Step 0g grows a freshness check before invoking the detectors:

```
if mtime(<plugin_dir>/<side>-updates.md) > mtime(<diagram>):
    # fresh; skip invocation
    pass
else:
    invoke @<side>-updates-detector
```

**Pros**: no detector-agent changes.

**Cons**: same correctness issues as A.1 (mtime is unreliable across git operations); duplicates the check logic across three skills (drift risk between three implementations); doesn't help standalone `@detector` runs; requires three coordinated skill-prose changes; the cascade orchestrator gains nothing. Strictly worse than B in every dimension.

### D. Status quo (triple invocation)

**Pros**: zero work. **Cons**: ~30–60k redundant tokens and ~10–30 s redundant latency per cascade, growing every time a new downstream consumer of the reports is added. The cost is small enough today that "do nothing" is defensible, but only until a fourth consumer appears or the per-aggregate cascade frequency increases (e.g. CI integration that runs cascades on every diagram PR).

---

## First-run flow (Approach B)

A clean repo, never run before:

1. Operator runs `/update-specs <domain>` (the cascade entry).
2. Domain Steps 0–9 complete successfully.
3. Step 11 invokes `/application-spec:update-specs <domain>`.
4. Application Step 0g fans out the two detectors. Each detector:
   - Computes `head_hash` and `wt_hash` for its diagram.
   - Reads `<plugin_dir>/<side>-updates.md` — file not found.
   - Treats sentinel as `none/none`; mismatch → proceeds with Steps 1–8.
   - Renders the report body, prepends the new sentinel, writes.
5. Step 12 invokes `/rest-api-spec:update-specs <domain>`.
6. REST API Step 0g fans out the same two detectors. Each detector:
   - Recomputes `head_hash` and `wt_hash` (same values as in step 4 — no working-tree change between Step 11 and 12).
   - Reads the report from step 4.
   - Sentinel matches → prints "fresh; skipping" and exits zero.
   - The downstream skill proceeds with Steps 1+ as normal, reading the on-disk report.
7. Step 13 invokes `/messaging-spec:update-specs <domain>` — only the commands detector fires, finds its report fresh from step 4, fast-paths.

Net effect: **two detector runs** (one each in step 4) across the whole cascade, not five.

---

## Failure modes

| Mode | B's behavior |
|---|---|
| Detector aborts mid-run (LLM error, IO failure, kill) | No `Write` executed → no sentinel on disk → next call recomputes from scratch. |
| Detector hard-fails on a structural gate (stereotype change, anchor rename, multi-anchor) | Per existing detector contract: prints `ERROR:` and writes nothing. Sentinel from a prior successful run remains. The next call recomputes and re-hard-fails (deterministic) — the operator sees the same `ERROR:` repeatably until the diagram is fixed. **Not** a stale-skip risk: the gate fires before the freshness check would even matter, since the freshness check happens *before* Step 3's structural gates. Need to be careful here — see [§ Sequencing](#sequencing-where-the-freshness-check-fires). |
| Working tree changes between Step 11 and Step 12 (operator edits the diagram during the cascade) | `wt_hash` differs from sentinel → mismatch → Step 12's invocation runs as normal. The freshness check is robust to mid-cascade edits. |
| `git rev-parse HEAD:<path>` fails (untracked file) | Treat sentinel-head as `none`. If existing report sentinel is `none/<old_wt>` AND `wt_hash == old_wt` → still fresh. Otherwise recompute. Same untracked-file logic that's already in the detectors' Step 1. |
| Operator hand-edits the report (e.g. adds a note) | Hash recomputation doesn't change; the next detector run finds matching hashes and **doesn't overwrite** the hand-edit. Surprising? Yes. **Documented behavior**: the report is detector-owned, hand-edits are not preserved across detector runs that find a structural change; on a no-op-fresh run the hand-edit survives, which is desirable for one-off notes. If the operator wants to force a regenerate, they `rm` the report or strip the sentinel line. |
| `<output_file>` exists but the sentinel line is malformed (e.g. user manually edited it) | Treat as `none/none`; recompute. The detector should be tolerant of a missing-or-mangled sentinel — never abort on it. |

### Sequencing: where the freshness check fires

Important sequencing decision: the freshness check happens **before** Step 1 (Load both versions of the diagram) — because the whole point is to avoid the file reads and Mermaid parse. But the structural gates (anchor renamed, multi-anchor, stereotype change) live in Steps 2–3, and those gates **must still fire** on every invocation even when the report is otherwise fresh, because they direct the operator to `/application-spec:generate-specs`.

Resolution: the freshness check is a fast-path optimization that can only fire when **the previous successful run also passed the structural gates**. If the previous run hard-failed on a gate, no report was written, so no sentinel exists, so the freshness check doesn't trigger and the gates re-evaluate. If the previous run succeeded, the report-on-disk is by definition gate-clean, and the hashes guarantee the diagram is unchanged → re-running the gates would yield the same pass. The freshness check is therefore safe to short-circuit even the structural gates.

The only edge case: a previous successful run produced a clean report, the operator then hand-edited the diagram into a structurally broken state, the new hash differs from the sentinel, the freshness check fails, the detector proceeds into Steps 1–3 and hard-fails on the gate. Correct behavior.

---

## Implementation surface (Approach B)

**Files changed: 2.** Both in `plugins/application-spec/`.

| File | Change |
|---|---|
| `plugins/application-spec/agents/commands-updates-detector.md` | Insert a new "Step 0 — Freshness check" before Step 1. Insert sentinel-rendering instruction at Step 7 / 8. Document the sentinel format. Update *Idempotency* section to note the freshness fast-path. |
| `plugins/application-spec/agents/queries-updates-detector.md` | Same edits, symmetric. |

**Files changed optionally: 1.**

| File | Change |
|---|---|
| `plugins/application-spec/skills/application-updates-report-template/SKILL.md` | Document the `<!-- detector-baseline: head=<hash>; working-tree=<hash> -->` sentinel as line 1 of the rendered report. Single source of truth for both detectors. |

**Files not changed**:

- `plugins/domain-spec/skills/update-specs/SKILL.md` — cascade orchestrator unchanged.
- `plugins/application-spec/skills/update-specs/SKILL.md` — Step 0g unchanged (still invokes both detectors; they fast-path internally).
- `plugins/rest-api-spec/skills/update-specs/SKILL.md` — when the rest-api integration lands per [`commands-queries-integration-approach.md`](../../rest-api-spec/notes/commands-queries-integration-approach.md), its Step 0g grows the detector invocations as proposed; the dedup is invisible to the skill.
- `plugins/messaging-spec/skills/update-specs/SKILL.md` — same as rest-api.

**Plugin version bumps**: `plugins/application-spec/.claude-plugin/plugin.json` only.

**Land-ability**: single-plugin, atomic landing. No coordinated cross-plugin change needed. The rest-api-spec and messaging-spec integrations can land before or after the dedup — they compose either way.

---

## Cross-plugin coordination

Approach B requires **no cross-plugin coordination**. The two detector agents are owned by application-spec; rest-api-spec and messaging-spec only consume the reports the detectors produce. The freshness check is invisible to consumers.

This contrasts with approach A, which requires coordinated changes in domain-spec (Step 9.5), application-spec (Step 0g), rest-api-spec (Step 0g), and messaging-spec (Step 0g) — four plugins, with intermediate states where the cascade-owned invocation has landed but a downstream skill hasn't yet learned to skip its own (or vice versa).

---

## Sentinel format

```
<!-- detector-baseline: head=<git-rev-parse-output>; working-tree=<git-hash-object-output> -->
```

- Always **line 1** of the report (line 2 is the blank separator before the `# <Side> Updates — <stem>` heading per the template).
- Both hashes are full 40-character SHA-1 hex.
- `head=none` is the sentinel value when the diagram is untracked / not in HEAD (first-run path); the detector already handles untracked files in Step 1 with its `REPO_PATH` empty-stdout branch — extend that branch to record `head=none`.
- `working-tree=<hash>` is always computed via `git hash-object -- <path>` on the current working-tree blob. (Using `git hash-object` rather than just hashing the file contents ourselves matches what git uses internally to detect changes; it also handles autocrlf and other normalizations consistently with git.)
- Malformed / missing sentinel is treated as `head=none; working-tree=none` — guaranteed non-match against any real hash pair → forces regen.

---

## Alternatives that don't appear in the option table

- **Persisting a global "detector-run-id" in the cascade** — overkill; couples the detector to the cascade's lifecycle.
- **Per-detector lock files** — solves the wrong problem (concurrent invocation isn't the issue; redundant sequential invocation is).
- **Memoizing detector output in `<plugin_dir>/.cache/`** — same effect as B with extra files. The report itself is the cache.
- **Conditional invocation in the downstream skills via shell `test -nt` against the diagram** — fragile (`test -nt` uses mtimes, same problem as A.1) and embeds the freshness check in skill prose rather than detector logic.

---

## Open questions

- **Should the sentinel record the auto-loaded skills' versions too?** A change to `application-updates-report-template` could in principle change the rendered report shape; a `template-version=N` sentinel field would force regen when the template changes. Probably overkill — template changes are intentional and the operator can `rm` the report or bump the plugin version to force a sweep.
- **Should the sentinel be a top-line HTML comment or front-matter?** Comment is simpler (no YAML parser needed). Comment chosen.
- **What about the queries detector when the queries diagram doesn't exist?** Queries detector hard-fails on missing `<queries_diagram>` (Step 1). Pre-existing behavior; freshness check fires after Step 1 of the agent's existing workflow… actually it should fire *before* Step 1 to skip the file reads. But on a missing-file path, the detector still has to hard-fail with `ERROR:` — we can't skip that on a freshness hit because there's no report to be fresh. Resolution: do the freshness check inline with Step 1's existing file-presence test — if the file is missing, hard-fail as today; if it's present, then compute the hashes and check the sentinel; if the sentinel matches, fast-path; else fall through to the existing Step 1+ workflow.

---

## Out of scope for this note

- **The cascade orchestrator's chain semantics** — Steps 10–13 of domain `/update-specs` and the abort-on-`ERROR:` policy stay as-is. B does not change them.
- **The downstream skills' Step 0g content** — application-spec's Step 0g stays as written today; rest-api-spec's and messaging-spec's Step 0g grow per their integration notes. B is orthogonal.
- **The `<stem>.domain/updates.md` upstream report** — that's domain-spec-owned and has different lifecycle constraints (it's always regenerated at the top of domain `/update-specs`'s Step 0). Whether to apply the same dedup pattern to `domain-spec:updates-detector` is a separate decision; the value is much lower because the domain detector only runs once per cascade entry already.
- **Code-axis updaters** (`/…-spec:update-code` and downstream) — they consume the per-plugin `updates.md` files, not the detector reports directly, so they're unaffected.
