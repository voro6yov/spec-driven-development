# Reference-skill demotion — refined analysis & options

> Supersedes the original note (preserved verbatim at `active-skills-footprint-original.md`). The
> original proposed demoting the "reference skills" into read-by-path files based on a small
> sample. This note replaces that
> with a full, repo-verified dependency graph, a panel of fully-developed options, and an
> adversarial critique folded into the recommendation. All counts below were re-counted from
> the repo (`grep -rl "Invoke with:"` for command skills, `references/` and `CLAUDE_PLUGIN_ROOT`
> probes for the consumption mechanics).

> **Revised 2026-06-12.** §0 was added after settling the note's load-bearing unknowns — the cap
> unit (answered from the official docs), the `CLAUDE_PLUGIN_ROOT` mechanics (probed empirically
> against the live install), and a repo recount. **Read §0 first.** It answers §4's open
> question, invalidates §6's addressing mechanism, and replaces it with the umbrella-skill
> shape. §1–§3 are kept as the baseline audit; their arithmetic needs re-baselining (§0.3)
> before any wave executes.

---

## 0. Verified findings (2026-06-12) — read first

Three of the analysis's load-bearing unknowns are now settled — one from the official docs, two
empirically against the live install on this machine — and the repo has moved underneath the
audit. The headline: **the demotion idea is correct and necessary, but §6's mechanism would
fail on first contact; the umbrella-skill shape (§0.4) replaces it.**

### 0.1 The cap unit is ANSWERED: size-based, documented, and we are ~10× over

- Claude Code documents **`skillListingBudgetFraction`** (default `0.01` = 1% of the context
  window ≈ **2,000 tokens** at 200K) capping the total skill metadata injected per session, and
  **`maxSkillDescriptionChars`** (default `1536`) truncating each description. On overflow,
  descriptions truncate first, then **whole skills are silently dropped** from the listing.
  (Source: code.claude.com/docs/en/settings.md.)
- **`/doctor` reports truncation status.** This replaces §4's trim-experiment as the Step-0
  diagnostic — one command, zero changes.
- The ~83.7 KB of description text ≈ ~20K tokens against a ~2K budget: skills are being dropped
  **today, deterministically** — demotion is necessary, not prophylactic.
- Escape hatch, dev-only: raising `skillListingBudgetFraction` in local settings clears the
  symptom for this checkout, but a marketplace **cannot set its consumers' settings**, so the
  structural fix must still ship.
- **Caveat:** no *agent*-catalog budget is documented anywhere (counts, bytes, or overflow
  behavior). The reproduced symptom was agent-side ("doesn't find agents"), so Option D stays
  measurement-gated rather than dismissed — see the revised STEP 4 in §5.

### 0.2 §6's addressing mechanism is BROKEN — verified empirically

- `${CLAUDE_PLUGIN_ROOT}` is **not interpolated in skill/agent markdown**
  (anthropics/claude-code#9354 — it resolves only in JSON configs: hooks, MCP servers).
- **Probed live** (a plugin agent run in diagnostic mode, 2026-06-12):
  `echo $CLAUDE_PLUGIN_ROOT` from inside `domain-spec:domain-bootstrapper`'s Bash returned
  **empty**. The variable is not in the agent's shell environment either. An agent has **no
  runtime mechanism** to resolve its own plugin's install path the way §6 assumes.
- **Install layout (verified):** plugins are cached per-plugin, **per-version** —
  `~/.claude/plugins/cache/spec-driven-development/<plugin>/<version>/`. So the cross-plugin
  form `${CLAUDE_PLUGIN_ROOT}/../<owner>/references/…` is wrong twice: the sibling actually
  lives at `../../<owner>/<owner-version>/`, and a consumer cannot know the owner's version
  string. Cross-plugin relative reads are not "fragile" — they are **unaddressable**.
- The structural reading the whole note missed: **the skill registry IS the path-resolution
  mechanism.** Today's relative `[template.md](template.md)` links resolve only because the
  registry loads the `SKILL.md` and the harness therefore knows its directory. Demoting a file
  out of the registry removes the only thing that told anyone where it lives. "Same content,
  cheaper delivery" is actually "same content, **no** delivery" unless something registered
  still anchors the path — which is what §0.4 restores.

### 0.3 The repo moved: recount (2026-06-12)

| Plugin | Skills | Agents |
|---|---:|---:|
| domain-spec | 30 | 22 |
| application-spec | 23 | 29 |
| persistence-spec | 20 | 32 |
| rest-api-spec | 33 | 23 |
| messaging-spec | 20 | 17 |
| model-diagrams | 5 | 4 |
| adr-log | 4 | 6 |
| spec-core | 1 | 0 |
| **Totals** | **136** | **133** = **269** |

- **The 5 divergent `naming-conventions` copies are gone** — consolidated into
  `spec-core:naming-conventions` (exactly one copy remains). §1-correction-5, bucket D's "hard
  tail", §5's old STEP 3, and Option B's "skip the 5 naming-conventions" are all **moot**.
- **Agents grew 121 → 133** (the `*:specs-generator` / `*:code-generator` orchestrators).
  Agents are now the **larger** half: a references-only plan floors at 29 commands + 133 agents
  = **162**, not the 150 quoted throughout §3.
- **A thin `spec-core` plugin now exists** (Option E in embryo), and CLAUDE.md prescribes homing
  shared cross-plugin conventions there. This **contradicts Option C / Wave-3 vendoring**:
  bucket-B refs should migrate *into spec-core*, not be copied per consumer — the divergent-md5
  drift §2.3 feared already happened once and was cleaned up exactly this way.
- §1–§3 below are kept as the baseline audit. Re-derive the bucket counts (§2.2) before
  executing any wave; the deltas above shift every gate number.

### 0.4 The revised migration shape: umbrella skill + supporting files

Replaces §6's `references/` + path-read scheme. Uses only documented mechanics that this repo
already exercises daily (the 18 `template.md` companions work this way):

- **Per plugin, ONE registered umbrella skill** — e.g. `domain-spec:patterns` — whose `SKILL.md`
  is a short index of its contents. All of that plugin's reference docs move under its directory
  as **supporting files** (documented as not auto-loaded and not catalog entries):
  - single-file ref → `skills/patterns/<name>.md`
  - multi-file ref → `skills/patterns/<name>/` with the old `SKILL.md` renamed to **`index.md`**
    (so no stray nested `SKILL.md` risks discovery) + its `template.md`/`examples.md` unchanged;
    the relative link survives because the directory moved intact.
- **Consumers:** implementer agents replace N pattern entries in frontmatter `skills:` with the
  one umbrella entry. When it auto-loads, the harness supplies its directory — the agent Reads
  `<umbrella-dir>/<name>.md` siblings. Path resolution comes from the registry anchor, for free.
- **Dynamic union loaders** (`code-implementer` + the 5 `code-change-writer`s): keep the
  union/dedupe logic; replace each Skill-load with a Read of
  `<umbrella-dir>/<pattern>{.md,/index.md}` and **hard-fail on a missing path**. The
  producer-resolved-paths idea (§5 short version) still applies and still collapses the two-site
  rewrite to one.
- **Footprint:** ~111 reference entries → **~6 umbrella entries** (not 0 — deliberately: the
  index skills preserve discoverability and a fail-loud surface that pure path reads lose).
- **Cross-plugin (bucket B):** shared refs move into a `spec-core` umbrella (e.g.
  `spec-core:shared-patterns`); consumers frontmatter-load it. No vendoring, no inter-plugin
  paths, consistent with the CLAUDE.md spec-core convention.
- **Bridge of last resort:** if a true cross-plugin *file path* is ever unavoidable, a
  `spec-core` SessionStart **hook** (JSON — where `${CLAUDE_PLUGIN_ROOT}` *does* interpolate)
  can write its resolved root to a well-known location. The umbrella-load route should make
  this unnecessary.

### 0.5 Wave 1 executed (2026-06-13) — domain-spec demoted

The §0.4 shape shipped for domain-spec (after the live `@pattern-loader` probe confirmed
skill-context path resolution, 2/2 patterns):

- **16 intra-plugin reference skills deleted** (deregistered): aggregate-data-fixtures,
  aggregate-root, aggregate-unit-tests, class-spec-template, commands,
  delegation-and-event-propagation, domain-events, domain-pattern-selection, domain-services,
  domain-typed-dicts, entity, guards-and-checks, query-dtos, repositories, statuses,
  value-object. The umbrella copies under `skills/patterns/` are now the only copy.
- **8 cross-plugin-consumed refs kept registered** (deliberate deviation from a full Wave-1
  demotion, to avoid touching foreign plugins): aggregate-fixtures, collection-value-objects,
  constructor-guard-type-mapping, domain-exceptions, flat-constructor-arguments,
  optional-values, package-layout, updates-report-template. They are **dual-homed** — the
  standalone skill stays authoritative for foreign consumers; the umbrella copy (used by
  domain-spec's own loaders) must be re-synced byte-identically on edit. Wave 3 demotes them.
- **All 13 domain-spec consumer agents rewired** uniformly: frontmatter loads `domain-spec:patterns`,
  bodies Read `<patterns_dir>/<name>/index.md` (+ companions) with a hard-fail-on-missing guard.
  Token vocabulary (`domain-spec:<name>` in specs/briefs/pattern-assigner tables) unchanged.
- **`pattern-loader` probe agent deleted** (served its diagnostic purpose).
- Footprint: domain-spec registered skills 31 → **15** (6 commands + umbrella + 8 dual-homed);
  agents 23 → 22. domain-spec `plugin.json` 0.51.0 → 0.52.0.

**Wave 1, persistence-spec (2026-06-13).** Same shape replicated:

- **13 intra-plugin reference skills deleted** (deregistered): cleanup-fixtures,
  collection-fixtures, command-repo-spec-template, command-repository, implementation-roadmap,
  mappers, migration, migration-vocabulary, query-context, query-repository,
  repository-test-rules, table-definitions, updates-report-template. The umbrella copies under
  `skills/patterns/` are now the only copy. All 15 refs are single-file (no
  `template.md`/`examples.md` companions in this plugin).
- **2 cross-plugin-consumed refs kept registered** (dual-homed twins): persistence-fixtures and
  unit-of-work — both cited by `messaging-spec:messaging-handler-fixtures` (table cells, the
  only foreign consumer found by an exact-token re-scan). Umbrella copies byte-identical;
  Wave 3 demotes them.
- **Bucket-E stale ref `persistence-spec:persistence-dtos`** was already gone from the tree
  (zero hits anywhere) — nothing to delete.
- **All 19 persistence-spec consumer agents rewired** uniformly: frontmatter loads
  `persistence-spec:patterns`, bodies Read `<patterns_dir>/<name>/index.md` with a
  hard-fail-on-missing guard. The brief-mediated union loaders (`code-change-writer`,
  `code-review-writer`) keep their dedup logic over Reads. Token vocabulary
  (`persistence-spec:<name>` in briefs/dispatch tables) unchanged. References to other plugins'
  skills (`spec-core:naming-conventions`, `domain-spec:updates-report-template`) untouched.
- Footprint: persistence-spec registered skills 20 → **8** (5 commands + umbrella +
  2 dual-homed); agents unchanged at 32. persistence-spec `plugin.json` 0.67.0 → 0.68.0.

**Wave 1, application-spec (2026-06-13).** Same shape replicated:

- **13 intra-plugin reference skills deleted** (deregistered):
  application-service-integration-test-rules, commands, commands-dependencies-template,
  commands-methods-template, dependency-injection-patterns, interfaces, ops,
  queries-dependencies-template, queries-methods-template, queries-pattern, retry-transaction,
  settings, updates-report-template. The umbrella copies under `skills/patterns/` are now the
  only copy. All 18 refs are single-file (no companions in this plugin).
- **5 cross-plugin-consumed refs kept registered** (dual-homed twins):
  application-updates-report-template (rest-api-spec + messaging-spec),
  fake-implementations (messaging-spec), fake-override-fixtures (messaging-spec),
  ops-updates-report-template (rest-api-spec + messaging-spec + domain-spec:update-code), and
  services-report-template (messaging-spec) — all foreign hits are format/vocabulary citations,
  found by an exact-token re-scan. **The set differs from §2.3's prediction:** `commands` has
  **zero** foreign hits with exact-token boundaries (§2.3's hit was the
  `application-spec:commands-deps-writer` agent-name false-match — the same trap the
  persistence wave documented), while `ops-updates-report-template` (8 foreign hits, post-ops
  extension) joins the set. Umbrella copies byte-identical; Wave 3 demotes them.
- **Bucket-E stale refs `application-spec:sorting` and
  `application-spec:queries-specification-template`** were already gone from the tree (zero
  hits anywhere), and the three stale forward-references (`application-spec:update-code`, the
  wrong-infix `application-spec:application-service-updates-report-template`, the
  `application-spec:notes/...` path fragment) were already cleaned — nothing to delete.
- **All 22 application-spec consumer agents rewired** uniformly: frontmatter loads
  `application-spec:patterns`, bodies Read `<patterns_dir>/<name>/index.md` with a
  hard-fail-on-missing guard. The brief-mediated union loaders (`code-change-writer`,
  `code-review-writer`) keep their dedupe logic over Reads; `code-brief-writer`'s role→patterns
  table still emits `application-spec:<name>` tokens as data. Token vocabulary in
  briefs/specs/citations unchanged; references to other plugins' skills
  (`spec-core:naming-conventions`, `domain-spec:domain-exceptions`) untouched. The
  `commands-updates-detector` frontmatter carried the unprefixed form
  `application-updates-report-template` — rewired the same way.
- Footprint: application-spec registered skills 23 → **11** (5 commands + umbrella +
  5 dual-homed); agents unchanged at 29. application-spec `plugin.json` 0.70.0 → 0.71.0.

**Wave 1, messaging-spec (2026-06-13).** Same shape replicated — a **pure intra-plugin
demotion** (the only wave so far with an empty dual-homed set):

- **15 intra-plugin reference skills deleted** (deregistered): command-handlers,
  consumer-spec-template, dispatcher-cli-command, dispatcher-container-registration,
  dispatcher-runner-function, domain-event-dispatchers, domain-event-handlers,
  event-fields-template, event-tables-template, message-events-external,
  messaging-handler-fixtures, messaging-handler-test-rules, messaging-module-structure,
  multi-aggregate-domain-event-dispatchers, updates-report-template. Each `SKILL.md` was
  **moved** (not copied) to `skills/patterns/<name>/index.md`; the umbrella copies are now the
  **only** copy. All 15 refs are single-file (no `template.md`/`examples.md` companions in this
  plugin).
- **Zero dual-homed twins.** An exact-token re-scan of every other plugin (domain-spec,
  application-spec, persistence-spec, rest-api-spec, model-diagrams, spec-core) found **no**
  foreign consumer of any messaging-spec reference skill — foreign plugins touch messaging-spec
  only through the `update-specs` command skill (16 hits; stays registered regardless) and four
  agent names (`target-locations-finder`, `code-brief-writer`, `code-change-writer`,
  `code-review-writer` — fan-out edges, not skills). This confirms §2.3's ownership table
  (messaging-spec owns no foreign-consumed ref); the umbrella carries **zero ✦ rows** and there
  is no byte-identical-sync obligation. messaging-spec is a pure *consumer* of other plugins'
  shared refs (`spec-core:naming-conventions`, `domain-spec:*`, `persistence-spec:*`,
  `application-spec:*`), all left untouched.
- **Bucket-E stale refs** (`messaging-spec:{command-dispatchers, command-replies,
  container-initialization, message-commands, internal-domain-events,
  mixed-dispatcher-events-and-commands}`) were already gone from the tree (zero hits, no skill
  dirs) — nothing to delete.
- **`messaging-spec:update-code` is intentional roadmap prose** (the planned
  `/messaging-spec:update-code` skill), not an erroneous forward-reference — preserved verbatim
  in `messaging-updates-writer`, the `updates-report-template` ref, and the `update-specs`
  command skill. Unlike the application/rest-api waves there were no bad forward-references and
  no wrong-infix / `notes/...` path-fragment tokens to clean.
- **All 14 messaging-spec consumer agents rewired** uniformly: frontmatter loads
  `messaging-spec:patterns`, bodies Read `<patterns_dir>/<name>/index.md` with a
  hard-fail-on-missing guard. The brief-mediated dynamic loaders — `code-change-writer` (Phase 2,
  the only agent with real `Skill messaging-spec:…` body invocations) and `code-review-writer`
  (Phase 3) — keep their per-artifact lazy-load semantics over Reads; `code-brief-writer`'s
  kind-derived role→patterns table still emits `messaging-spec:<name>` tokens as data.
  `code-review-writer` had no reference skill in frontmatter, so it *gained* the
  `messaging-spec:patterns` entry. Token vocabulary in specs/briefs/prose citations unchanged;
  the `update-specs/SKILL.md` prose citation of `messaging-spec:event-tables-template` (a
  non-load-bearing grammar reference) left as-is.
- Footprint: messaging-spec registered skills 20 → **6** (5 commands + umbrella; **no
  dual-homed**); agents unchanged at 17. messaging-spec `plugin.json` 0.42.0 → 0.43.0.

### 0.6 Residual gap demotion does not close

Even after full demotion (~35 registered skills incl. umbrellas + 133 agents), the remaining
description bytes still exceed a default 1%-of-context budget for marketplace consumers. The
end-state needs demotion **plus** description trimming (`/trim-descriptions` +
`description-trimmer`, already in-repo), and likely a documented recommended
`skillListingBudgetFraction` for marketplace users. "Fewer entries" and "fits in 1% of context"
are different finish lines; plan for both.

---

## 1. What changed vs the original note

The original note's headline framing ("demote the 120 reference skills to read-by-path files")
is directionally correct, but it was built on a partial sample and got several load-bearing
details wrong. The corrected, measured picture:

### Per-plugin catalog (verified)

| Plugin | Command skills | Reference skills | Agents | Plugin total |
|---|---:|---:|---:|---:|
| domain-spec | 6 | 25 | 20 | 51 |
| application-spec | 5 | 20 | 26 | 51 |
| persistence-spec | 5 | 17 | 30 | 52 |
| rest-api-spec | 5 | 30 | 20 | 55 |
| messaging-spec | 5 | 22 | 15 | 42 |
| model-diagrams | 3 | 2 | 4 | 9 |
| adr-log | 0 | 4 | 6 | 10 |
| **Totals** | **29** | **120** | **121** | **270** |

So **149 skills (29 command + 120 reference) + 121 agents = 270 catalog entries.**

### Corrections to the original note

1. **Agents are half the catalog, and the original note ignored them.** 121 agents vs 149
   skills. Any plan that only demotes references can, at best, reach **150 entries** (29
   commands + 121 agents) — it physically cannot go lower without touching agents. The original
   note framed the problem as a pure reference problem; it is not.
2. **The cascade root was mis-attributed.** Domain `/update-specs` Step 10 does **not** hard-call
   all four downstream updaters. It cascades only to **persistence + application**; it is
   **application** `/update-specs` Step 9 that re-cascades into **rest-api + messaging** (with
   `--detectors-fresh`), which then inverse-cascade *back* into
   `application-spec:{commands,queries}-updates-detector`.
3. **Demotion is a two-site rewrite, not a flat find/replace.** Each pattern reference is wired
   in **two** places: (a) the dynamic docstring/brief pattern-name **union** (`code-implementer`
   in domain; `code-brief-writer` → `code-change-writer` in the other four layers), and (b) the
   **frontmatter** `skills:` list of the matching implementer agent. Missing either site is a
   *silent* regression, not a crash.
4. **There are zero path-based reads today.** No agent reads a reference via `CLAUDE_PLUGIN_ROOT`;
   there is no `references/` directory anywhere (both verified empty). The read-by-path
   convention the original note assumed has **never run in this repo** — it must be introduced
   and proven.
5. **`naming-conventions` is already vendored** — physically copied into all 5 layer plugins
   with **divergent md5s** (`8078ba…`, `483644…`, `4cd528…`, …). Drift across copies is already
   real, not hypothetical.
6. **A measured stopgap already ships in this repo:** `.claude/skills/trim-descriptions` +
   `.claude/agents/description-trimmer` (both verified present). The original note listed it
   (option ④) but did not treat it as the *diagnostic* it actually is (see §4).
7. **The cap unit was never established.** The original note assumed an entry-count budget. The
   reproduced symptom (`application-spec:update-specs` "doesn't find agents") is equally
   consistent with a **cumulative-description-size / token** budget. This is the single biggest
   open question and it changes which option is correct (see §4).
8. **20 of the 120 references are multi-file, and "move the SKILL.md" silently breaks them.**
   Both the original note and the first cut of this one assumed each reference is a lone
   `SKILL.md`. It isn't: 19 domain-spec refs + 1 rest-api-spec ref carry a co-located
   `template.md` (×18) or `examples.md` (×2) pulled in by a **relative** markdown link
   (`See [template.md](template.md)`) that resolves only because the two files share a directory.
   Flattening `skills/<name>/SKILL.md` → `references/<name>.md` orphans the companion and would
   collide all 18 identically-named `template.md` files in one flat dir. The footprint math is
   unaffected (companions were never catalog entries — only the `SKILL.md` registers), but the
   migration must move the **directory**, not the file (see §2.6 and the revised §6).

---

## 2. Where the footprint actually lives

Three answers: references vs agents vs commands; the demotion-difficulty buckets; and the two
runtime couplings.

### 2.1 References vs agents vs commands

| Class | Count | Demotable mechanically? | Notes |
|---|---:|---|---|
| Command skills | 29 | No (they are the slash entry points) | Irreducible floor unless relocated (Option E) |
| Reference skills | 120 | Yes — name→path rewrite | The original target; but 2 wiring sites each |
| Agents | 121 | Only by *refactor* (parametrize clones) | The bigger structural half; untouched by demotion |

### 2.2 Reference buckets (the 120, by demotion difficulty)

| Bucket | Meaning | Count | Difficulty | Demotion shape |
|---|---|---:|---|---|
| A — intra-mechanical | Per-pattern docs, one deterministic loader, single plugin | ~72–74 | easy / trivial | name→path at **2 sites** (docstring/brief union + implementer frontmatter) |
| B — cross-shared | Read by a *foreign* plugin | 17 (graph) / 18 (incl. domain `naming-conventions`→model-diagrams) | moderate | needs a stable cross-plugin path (vendor / `CLAUDE_PLUGIN_ROOT`) |
| C — model-discovered | Surfaced to the model by description | **0** | n/a | none exist → demotion is safe (no discovery dependency) |
| D — orchestrator-template | `*-template`, `*-report-template`, `naming-conventions`, `implementation-roadmap` | 23 | easy → **hard** | per-plugin `naming-conventions` is the hard tail: 15–24 frontmatter consumers each |
| E — stale / unconsumed | Zero namespaced consumers | 10 | trivial | delete-or-demote, **no loader to rewrite** (free −10) |

The **10 stale refs** (free win): `persistence-spec:persistence-dtos`,
`rest-api-spec:container-wiring`, `messaging-spec:{command-dispatchers, command-replies,
container-initialization, message-commands}`, `application-spec:{sorting,
queries-specification-template}`, `messaging-spec:{internal-domain-events,
mixed-dispatcher-events-and-commands}`. Plus 4 **stale forward-references** to clean regardless:
`application-spec:update-code` and `rest-api-spec:update-code` (no skill dir),
`application-spec:application-service-updates-report-template` (wrong infix; real skill is
`application-updates-report-template`), and the `application-spec:notes/...` path fragment.

### 2.3 Cross-plugin shared reference set (bucket B — the vendoring set)

The hub is **`domain-spec:updates-report-template` (4 foreign plugins)** and
**`domain-spec:domain-exceptions` (reused wholesale by application-spec)**.

> **Coupling-metric caveat (verified against the repo).** A bare `grep -rl` reports **13** files
> for `updates-report-template` and **9** for `domain-exceptions` — but those raw counts include
> the owning plugin's own `SKILL.md`, same-plugin prose, and stale forward-references. The *true*
> coupling metric is `foreignPluginCount` (**4** and **1**). Size the vendoring blast radius off
> the foreign count, not the raw grep, or you will over-engineer the path resolution.

| Owner | Shared ref | Foreign-plugin count |
|---|---|---:|
| domain-spec | updates-report-template | 4 |
| domain-spec | flat-constructor-arguments | 3 |
| domain-spec | package-layout | 2 |
| application-spec | naming-conventions | 2 |
| domain-spec | optional-values, domain-exceptions, constructor-guard-type-mapping, collection-value-objects, aggregate-fixtures, naming-conventions | 1 each |
| application-spec | services-report-template, fake-implementations, fake-override-fixtures, application-updates-report-template, commands | 1 each |
| persistence-spec | persistence-fixtures, unit-of-work | 1 each |
| rest-api-spec | surface-markers | 1 |

### 2.4 Runtime coupling — what actually breaks if a plugin is disabled

Neither coupling is a reference skill alone:

1. **Cross-plugin agent fan-out.** `domain-spec:update-code` is the single marketplace-wide code
   orchestrator and `@`-invokes **~16–20 foreign agents** (the brief/change/review trio +
   `target-locations-finder` per layer, plus persistence's `query-code-change-writer`).
2. **The spec-update cascade.** Rooted at domain `/update-specs` Step 10 (→ persistence +
   application), then application Step 9 (→ rest-api + messaging), which inverse-cascade back to
   `application-spec:{commands,queries}-updates-detector` (shared write-once-read-many producers).

These are **agent edges**, independent of reference demotion. They are what break — today as a
hard "agent not found" — if a layer plugin is selectively disabled.

### 2.5 Agent duplication (the structural win)

| Group | Agents | Collapses to | Saved |
|---|---:|---:|---:|
| Per-layer brief/change/review trio (×5 layers) | 15 | 3 | 12 |
| Per-layer `target-locations-finder` (verified 5, not 4) | 5 | 1 | 4 |
| application commands/queries/ops writer triplets | 12 | 4 | 8 |
| persistence scaffold+implement pairs | ~11 | 4–5 | 6 |
| persistence command-repo-spec section chain | 6 | 3 | 3 |
| rest-api per-table writers | 5 | 2 | 3 |
| rest-api serializer implementers | 3 | 2 | 1 |
| adr-log linear pipeline | 6 | 2 | 4 |
| **Realistic total** | **63** | **~21–25** | **~38–41** |

### 2.6 Multi-file reference skills (20 of 120 — the migration trap)

Not every reference is a lone `SKILL.md`. **20** of the 120 ship a co-located companion that the
`SKILL.md` pulls in by a **relative** markdown link, working only because the two files share a
directory:

| Plugin | Multi-file refs | Companion | Count |
|---|---|---|---:|
| domain-spec | entity, value-object, aggregate-root, aggregate-fixtures, aggregate-data-fixtures, aggregate-unit-tests, collection-value-objects, commands, delegation-and-event-propagation, domain-events, domain-exceptions, domain-services, domain-typed-dicts, flat-constructor-arguments, guards-and-checks, query-dtos, repositories, statuses, value-object | `template.md` | 18 |
| domain-spec | domain-pattern-selection | `examples.md` | 1 |
| rest-api-spec | endpoint-io-template | `examples.md` | 1 |

Key facts:

- **The link is relative** — `See [template.md](template.md)` / `[`examples.md`](./examples.md)`.
  It resolves against the file's own directory. Flattening `skills/<name>/SKILL.md` →
  `references/<name>.md` breaks it twice: the companion is orphaned, and all **18**
  identically-named `template.md` files collide in a single flat `references/` dir.
- **Footprint is unchanged.** A skill registers **one** catalog entry (its `SKILL.md` frontmatter);
  the companion is a bundled resource, not a catalog entry. So these files cost nothing today and
  nothing after demotion — the 120/270 numbers and all §3 arithmetic stand. This is a
  *migration-mechanics* gap, not a footprint gap.
- **The fix is to move the directory, not the file:** `skills/<name>/` → `references/<name>/`
  (SKILL.md + companion stay co-located → the relative link survives untouched). Single-file refs
  still flatten to `references/<name>.md`. See the revised §6.
- **It compounds bucket B.** Four cross-shared refs are *also* multi-file —
  `domain-exceptions`, `flat-constructor-arguments`, `collection-value-objects`,
  `aggregate-fixtures` — so vendoring them across plugins means copying a **directory**
  (SKILL.md + template.md), widening the drift surface §2.3 already flags.
- The `template.md` payloads are the substantial Jinja2 code templates the implementers render;
  losing one is a *silent* output regression, the same failure mode §3-Option-A calls out for
  dynamic names. The §6 "path must exist or hard-fail" guard must cover the companion too.

---

## 3. The options

The panel's five options (A–E) plus three genuinely-missing options the critique surfaced (S, M,
H). The headline comparison — **all "after" totals are the all-layers-enabled state** unless the
row says otherwise (Option C's selective number is a category mismatch; see its note):

> **§0 overrides on this table (2026-06-12):** every option's *mechanism* that relies on
> `references/<name>.md` + `${CLAUDE_PLUGIN_ROOT}` reads is invalidated by §0.2 — substitute
> the §0.4 umbrella shape (end-state ≈ +6 umbrella entries vs the figures shown). All agent
> columns read 121 but are now 133 (§0.3), so A/B/H stage-1 totals shift from 150/155 to
> ~162/~167. Option C's vendoring and Option E's fat-core are additionally contradicted by the
> existing thin `spec-core` (§0.3). The comparative *ranking* of options survives; the absolute
> numbers do not.

| Opt | Title | Skills | Agents | Total | Addresses S/A/Cpl | Effort | Reversibility |
|---|---|---:|---:|---:|---|---|---|
| **S** | Trim descriptions (stopgap + diagnostic) | 149 | 121 | 270* | size only | trivial | full (minutes) |
| **M** | Delete 10 stale + 4 fwd-refs, then stop | 139 | 121 | 260 | S(small) | trivial | git revert |
| **A** | Full reference demotion | 29 | 121 | 150 | S | high | high (lockstep) |
| **B** | Tiered demotion w/ gates | 34 | 121 | 155 | S | high | high (per-wave) |
| **C** | Cross-plugin decouple + tolerant fan-out | 132 (all-on) / 48 (subset) | 121 / 54 | 253 / 102 | S/A/Cpl (cond.) | high | moderate |
| **D** | Agent consolidation | 149 | ~83 | ~232 | A/Cpl | high | low–moderate |
| **E** | spec-core + on-demand layers | 46 | 121 | 167 (all-on) | S/Cpl | very-high | low |
| **H** | A→measure→D (hybrid sequence) | 29 → 29 | 121 → ~83 | 150 → ~110 | S/A/Cpl | high (staged) | high then low |

\* Option S changes **bytes, not entry counts** — its win is invisible to a count-based cap and
decisive against a size-based cap.

---

### Option S — Description-trimming (stopgap + diagnostic) *(critic-surfaced; do this first)*

- **One-liner:** Run the already-shipped `/trim-descriptions` on the largest plugin to cut
  frontmatter description bytes ~30% **without changing any entry count**, then check whether the
  "agent not found" symptom clears.
- **Mechanism:** `.claude/skills/trim-descriptions` + `.claude/agents/description-trimmer`
  already exist. ~83.7 KB of description text is injected today across 270 entries. Trimming
  leaves the catalog at 270 entries but shrinks the injected metadata.
- **Footprint:** 149 / 121 / **270** (entries unchanged); injected bytes drop ~30% on the
  trimmed plugin.
- **Addresses:** size-based pressure only. Not count.
- **Effort:** trivial. **Reversibility:** full (revert in minutes via git).
- **Key risks:** none material — it is the cheapest experiment available.
- **Residual:** if the cap is count-based, this provides **zero** relief.
- **Clears the limit if:** the cap is **size/token-based** — then this alone may clear it, and it
  is the only zero-restructure lever. **Its true value is diagnostic:** if trimming clears the
  symptom, the cap is size-based and you should prioritize trimming + demotion (which also
  removes description bytes) and *de-prioritize* agent-count consolidation.

---

### Option M — Delete the 10 stale + 4 forward-refs, then re-measure *(critic-surfaced)*

- **One-liner:** Remove dead weight that has zero consumers, re-measure against the real cap,
  and stop if it clears.
- **Mechanism:** The 10 E-bucket refs have zero namespaced consumers; deletion needs no loader
  rewrite. Clean the 4 stale forward-references at the same time.
- **Footprint:** **139** / 121 / **260** (−10 skills; −14 tokens-worth of dangling edges).
- **Addresses:** skills (small). **Effort:** trivial (~0.5 day). **Reversibility:** git revert.
- **Key risks:** none — these are unconsumed or broken.
- **Residual:** nowhere near a tight cap on its own.
- **Clears the limit if:** the catalog is only **marginally** over budget. This is the
  do-the-minimum-and-stop terminal state the panel never named (Option B's Wave 0 is the same
  work but framed as a prerequisite to a 10–13-day plan).

---

### Option A — Full reference demotion to read-by-path files

- **One-liner:** Move all 120 reference `SKILL.md` → `plugins/X/references/<name>.md`, rewire
  every consumer from Skill-by-name to Read-by-path. Leaves 29 commands + 121 agents.
- **Mechanism:** Physically relocate each `skills/<ref>/SKILL.md` to `references/<ref>.md`
  (leaving the loadable catalog) and rewrite **two** wiring sites: (1) the **dynamic** docstring/brief
  union in `code-implementer` and the 5 `code-change-writer`s (the pattern name is computed at
  runtime, so this is a name→path **map** plus a Read, not a literal replace), and (2) the
  **frontmatter** `skills:` list of each implementer agent. The 17–18 cross-plugin refs need a
  stable path into the producing plugin.
- **Footprint:** **29** / 121 / **150**.
- **Addresses:** skills only.
- **Effort:** high (the rewrite surface spans 100+ files). **Reversibility:** high in principle,
  but reversal cost ≈ forward cost (the dynamic name→path loader logic must be undone in lockstep).
- **Key risks:** **dynamic-name failures are silent** (a missing `references/<name>.md` surfaces
  mid-run as a skipped Read, losing the registry's fail-loud behavior — add a "path must exist or
  hard-fail" guard); **cross-plugin path fragility** (18 sibling-plugin reads with no registry
  fallback if the install layout differs from the dev checkout); **two-site drift**; stray
  un-rewritten bare `plugin:ref` tokens.
- **Residual:** does **not** touch the 121 agents or the two runtime couplings; introduces 18
  hidden inter-plugin paths.
- **Clears the limit if:** **skills-only cap** — decisively (149→29). **Combined cap** — only if
  the threshold is **≥150** (agents untouched at 121, so 121+29=150 is the floor). Below 150,
  A alone is **insufficient** and must be paired with agent consolidation.

> Note on A's arithmetic: deleting the 10 stale refs is a freebie that lands at 29 either way
> (they were references). The panel's "−110 reduction" branch is misleading phrasing — the end
> state is 29 regardless of whether the 10 are deleted or demoted.

---

### Option B — Tiered demotion by bucket with per-wave measurement gates

- **One-liner:** Demote in ordered waves (free stale → A intra-mechanical → D non-naming
  templates → B cross-shared with vendoring), re-measuring after each wave and **stopping the
  moment the catalog is under budget**.
- **Mechanism:** Same name→path two-site rewrite as A, ordered by difficulty. Wave 0: 10 stale
  (free). Wave 1: 72 bucket-A. Wave 2: 18 of 23 bucket-D (explicitly **skips** the 5
  `naming-conventions`). Wave 3: 15 bucket-B (needs vendored paths).
- **Footprint after each gate (skills / total):** W0 139/260 → W1 67/188 → W2 49/170 → W3 34/155.
- **Addresses:** skills only.
- **Effort:** high (~10–13 days if run to completion). **Reversibility:** high, per-wave.
- **Key risks:** 72×2 = 144 edit points in Wave 1; Wave-3 vendoring can break the cascade;
  **cap-unit ambiguity makes the stop condition unreliable** — if the budget is combined, B
  floors at 155 and may never clear after burning ~13 days.
- **Residual:** leaves the 5 hard `naming-conventions` and all 121 agents; an early gated stop
  leaves buckets D/B as skills, so clean per-plugin disabling is never achieved.
- **Clears the limit if:** skills-only cap **≥67** clears after Wave 1; the full plan reaches 34.
  Combined cap clears only if **≥155**.

> Reconciliation: Wave 1 uses "72" bucket-A refs while the narrative says "~74" — off by 2,
> unreconciled in the source; treat 72–74 as the band. The 5 residual skills = the 5 layer
> `naming-conventions` copies, consistent.

---

### Option C — Cross-plugin decoupling (vendor 17 shared refs) + tolerant fan-out

- **One-liner:** Cut cross-plugin runtime coupling so users can safely **disable whole plugins** —
  the only lever that touches the agent half (enabling only domain+persistence+model-diagrams
  drops the *live* catalog to ~102).
- **Mechanism:** (1) **Vendor** each of the 17 shared refs into every consuming plugin
  (`plugins/<consumer>/vendored/<ref>.md`, read via `CLAUDE_PLUGIN_ROOT`) — exactly how
  `naming-conventions` already works. (2) **Tolerant fan-out:** each cascade fan-out probes layer
  availability and emits "WARNING: <layer> not enabled; skipping" instead of "agent not found".
- **Footprint:** all-on **132 / 121 / 253**; selective (domain+persistence+model-diagrams)
  **48 / 54 / 102**.
- **Addresses:** skills + agents + coupling — but the agent win is **conditional on disabling**.
- **Effort:** high. **Reversibility:** moderate (tolerant fan-out is a one-line flip; vendoring
  is a wide multi-file diff).
- **Key risks:** vendoring duplicates source (drift — `naming-conventions`' 5 copies already
  differ); path reads via `CLAUDE_PLUGIN_ROOT` are unprecedented here; tolerant fan-out can
  **mask a genuinely-misconfigured layer** (quiet half-update instead of loud failure); the
  headline 102 only materializes if users actually disable plugins.
- **Residual:** all-on it only removes 17 refs (270→253); the 121 agents are not consolidated;
  bucket-A refs and `naming-conventions` are untouched.
- **Clears the limit if:** decisive **only under the enable-on-demand operating model** (≤3
  layers live). With all 7 enabled it sits at 253 and clears nothing tight.

> **Two corrections folded in.** (a) The "tolerant fan-out precedent" the panel cites
> (application Step 0a treats a missing *report file* as no-change) is **data-absence** tolerance,
> not **agent/plugin-absence** tolerance — this is genuinely new control flow, not a proven
> pattern. (b) The "149→132 (remove 17)" claim only holds if each shared ref is also fully
> demoted in its **owner**; if the owning copy stays a registered skill, the all-on catalog does
> **not** drop by 17. C's 102 is a *selective-enable* number and is not comparable to A's all-on
> 150.

---

### Option D — Agent-footprint reduction (parametrize the clones)

- **One-liner:** Attack the 121-agent half directly — merge the 5×-cloned brief/change/review
  trio, the 5 `target-locations-finder`s, application's commands/queries/ops triplets,
  persistence's scaffold+implement pairs, the rest-api per-table/serializer writers, and the ADR
  linear flow.
- **Mechanism:** Encode per-layer/per-axis/per-kind differences as a path-addressed **data
  manifest** (the same manifest demotion produces), then collapse each clone family into one
  parametrized agent. `ops` already reuses the `commands` templates, proving axis-parametrizability.
  (Verified: 5 `code-change-writer` and 5 `target-locations-finder` files, one per layer.)
- **Footprint:** 149 / **~83** / **~232** (point estimate ~38 saved; group enumeration supports
  ~41 → ~80; the panel's 83 figure uses 38).
- **Addresses:** agents + (indirectly) coupling.
- **Effort:** high — **real refactoring**, not a mechanical rewrite. **Reversibility:**
  low–moderate (rewrites agent bodies + every `@`-fan-out site; do it group-by-group on main for
  independently-revertible commits).
- **Key risks:** **parallelism loss** (a single multi-mode agent serializes the pipeline unless
  the orchestrator still emits N parallel calls with different layer args); **quality dilution**
  (the brief/change/review roles write real code); missed `@`-edges reproduce "agent not found";
  persistence's `query-code-change-writer` is a layer-specific extra that must not be dropped.
- **Residual:** **zero** skills relief — if the cap is skills-only this does nothing. The cascade
  coupling survives (not a duplication group).
- **Clears the limit if:** skills-only — **never**. Combined cap **~221–232** — clears; tighter
  than ~221 requires pairing with demotion.

---

### Option E — Thin always-on spec-core + enable-on-demand layers

- **One-liner:** Extract the 29 orchestrators + cascade dispatcher + 17 shared refs into ONE
  always-on `spec-core` plugin; each layer becomes enable-on-demand carrying only its own agents
  and its intra-plugin refs demoted to files.
- **Mechanism:** Move all 29 commands and the split cascade root into `spec-core`; move the 17
  shared refs in as `core:<name>`; demote each layer's intra-plugin refs to read-by-path; gate
  every fan-out on layer-enablement.
- **Footprint:** all-layers-on **46 / 121 / 167**; core+domain **46/20/66**;
  core+domain+persistence **46/50/96**.
- **Addresses:** skills + coupling (agents untouched).
- **Effort:** **very high** — biggest blast radius. **Reversibility:** **low** (a structural
  marketplace re-org; revertible only as one big git revert).
- **Key risks:** a single missed name→`core:` rewrite reproduces the failure being eliminated;
  read-by-path is unproven here; the enabled-layer guard is new control flow with no precedent;
  moving commands into a new namespace **changes user-facing slash-command names**; putting
  adr-log/model-diagrams commands into a "spec-core" is architecturally odd.
- **Residual:** the 121 agents are untouched; the ~46-entry core is an irreducible always-on
  floor; all-layers-on returns to ~167.
- **Clears the limit if:** skills-only — decisively (149→46). Combined cap — only under
  enable-on-demand (few layers live); all-on 167 clears nothing tight without also doing D.

> E's arithmetic is internally shaky: 167 silently assumes the dispatcher adds zero catalog
> entries (its own text hedges "+ ~5 dispatcher agents if counted"), and the "~57 intra-plugin
> refs demote" figure doesn't reconcile with 120 − 17 − 10 − 4(naming) ≈ 89. Treat E's numbers
> as optimistic floors.

---

### Option H — Hybrid: A → measure → D *(critic-surfaced; this is the real answer)*

- **One-liner:** Do the mechanical reference demotion first (clears any skills-only cap),
  **measure**, and escalate to agent consolidation **only if** a combined cap is still binding.
- **Mechanism:** Sequence the panel options by reversibility and diagnostic value rather than
  picking one. A (or B) is mechanical and reversible; D is a refactor and is only paid for if the
  measurement proves it necessary.
- **Footprint:** stage 1 → **29 / 121 / 150**; stage 2 (if needed) → **29 / ~83 / ~110–115**.
- **Addresses:** skills, then agents, then (via the staging) coupling discipline.
- **Effort:** staged-high. **Reversibility:** high through stage 1, low once stage 2 lands.
- **Key risks:** inherits A's two-site/dynamic-name risk in stage 1 and D's parallelism/quality
  risk in stage 2 — but you only incur stage-2 risk if measurement forces it.
- **Residual:** none structural if both stages run; cross-plugin path fragility from A persists.
- **Clears the limit if:** **any** cap — skills-only clears at stage 1 (150, or 29 skills); a
  tight combined cap (<150) clears at stage 2 (~110–115). This is the only strategy that is
  robust against **both** cap units.

---

## 4. The decisive open question & how to settle it

> **ANSWERED (2026-06-12) — see §0.1.** The skill budget is **size-based and documented**
> (`skillListingBudgetFraction`, default 1% of context; `maxSkillDescriptionChars` 1536;
> silent drop on overflow; `/doctor` reports truncation). The empirical test below is
> superseded for the skill side. What remains genuinely open is whether **agents** have any
> analogous budget — that is undocumented, and it gates STEP 4 (Option D) in the revised §5.
> The section is preserved for the reasoning trail.

**Every `clears-the-limit-if` above is conditional on one unknown: is the budget a (a) skill
entry count, (b) combined skill+agent entry count, or (c) cumulative description size / tokens?**
The reproduced symptom (`application-spec:update-specs` "doesn't find agents") is consistent with
*all three*. Until this is settled, the options are un-rankable.

This is also where the original note and the panel share their biggest blind spot: the panel's
math assumes **count**; the symptom evidence (silent drops, ~83.7 KB of descriptions) points at
**size**. If the cap is size-based, demotion still helps (the description bytes leave context
too), but agent *count* consolidation may be a **wash** if merged agents inherit concatenated
longer descriptions.

### The empirical test (cheap, reversible, already-tooled)

1. **Run `/trim-descriptions plugins/persistence-spec`** (the largest, 30 agents). This cuts
   description **bytes** ~30% **without changing entry counts**.
2. **Reproduce the symptom** — re-run `/update-specs` and watch for the "agent not found" drop.
3. **Read the result:**
   - **Symptom clears →** cap is **size/token-based**. Prioritize **S + reference demotion**
     (both remove description bytes); **de-prioritize Option D** (count cuts may not help, and
     could be neutral if merged descriptions grow).
   - **Symptom persists →** cap is **count-based**. Proceed to step 4.
4. **Second diagnostic (count-based path):** delete the 10 stale refs (Option M → 149→139) and
   re-measure. If that alone clears, **ship and stop** — cheapest terminal state. If not, the cap
   is tight and you need demotion (A/B), and possibly agents (D).
5. **Establish whether agents count.** If after full reference demotion (149→29 skills) the
   symptom persists, the cap is **combined** and binding below 150 → escalate to D.

Also verify, before committing to any path read, that Claude Code does **not** index
`plugins/<p>/references/*.md` (no option proves this; if the loader globs all `.md` under a
plugin, demotion-in-tree won't remove a size-based entry and the files must live outside the
indexed tree). And confirm `CLAUDE_PLUGIN_ROOT` resolves identically in a marketplace install vs
the dev checkout (zero precedent in the repo today).

---

## 5. Recommended sequence

Opinionated, composed, gated. The ordering principle is **most-reversible-and-diagnostic first**,
escalating only when measurement forces it.

```
STEP 0  Diagnose against the documented budget (≈10 min, zero changes) [revised per §0.1]
        - run /doctor with all plugins enabled → confirm skill-listing truncation.
        - optional local confirm: raise skillListingBudgetFraction, re-run /update-specs,
          watch the symptom clear. Dev-only — consumers cannot be shipped this setting.
        The old trim-experiment GATE 0a/0b is superseded: the skill cap is size-based (§0.1).
        The agent-side budget remains undocumented → STEP 4 stays measurement-gated.

STEP 1  Free cleanup (Option M, ≈0.5 day, git-revertible)
        - re-verify the stale list first (the spec-core consolidation moved things),
          then delete stale refs + stale forward-references.
        GATE 1: /doctor + re-measure. Truncation gone → STOP (unlikely; we are ~10× over).

STEP 2  Umbrella-skill demotion (§0.4 shape — replaces the old Wave-1..3 mechanics)
        - WAVE 1 (pilot): domain-spec only. Create skills/patterns/ umbrella; move bucket-A
          refs in as supporting files (multi-file refs keep their directory, SKILL.md →
          index.md); rewrite code-implementer's union loader to path Reads with a
          hard-fail-on-missing guard; swap demoted names for the umbrella in agent
          frontmatter. Run the §6 verification + an output-equivalence run.
        GATE 2a: /doctor + re-measure. Then roll the same shape across the other 4 layers.
        - WAVE 2: bucket-D templates → same per-plugin umbrella.
        - WAVE 3: bucket-B shared refs → a spec-core umbrella (NOT vendoring; §0.3).
        GATE 2c: /doctor + re-measure. Target: ~35 registered skills (29 commands + ~6 umbrellas).

STEP 3  Description trimming on everything still registered (commands + umbrellas + agents)
        - /trim-descriptions per plugin. This closes the §0.6 residual-bytes gap that
          demotion alone cannot.

STEP 4  If agent-side symptoms persist after Steps 1–3: FIRST establish empirically whether
        agent descriptions are truncated/dropped at this scale (no documented budget exists);
        only then Option D, group-by-group on main, one plugin-version bump per group.
        PRESERVE PARALLELISM: keep N parallel Agent calls with a <layer> arg.
        Baseline is now 133 agents (§0.3), incl. the new orchestrators — re-derive §2.5.

DROPPED: the old STEP 3 (demote the 5 naming-conventions copies) — already consolidated
        into spec-core:naming-conventions (§0.3).
DO NOT DO: Option C vendoring (contradicts the spec-core convention AND the verified
        per-version cache layout, §0.2–0.3); Option E wholesale (spec-core already exists
        thin — grow it with shared refs only, not with the 29 commands).
```

**The opinionated short version:** this is **Option H** (A/B → measure → D) with **Option M** as
the free first step, `/doctor` as the diagnostic (§0.1), and the **umbrella-skill shape (§0.4)**
as the demotion mechanism. Avoid C and E. Where you can, **move pattern-path resolution into the
producer** (`pattern-assigner` / `code-brief-writer` write resolved *paths*, not bare names, into
the docstring/brief) — this collapses the two-site rewrite to **one** site and eliminates the
dynamic-name silent-skip risk Option A flags as its highest.

---

## 6. Per-plugin migration checklist

> **Revised 2026-06-12.** The original `references/` + `${CLAUDE_PLUGIN_ROOT}` scheme is
> unimplementable (§0.2: no markdown interpolation, empty in agent env, per-version cache
> layout). This checklist now implements the **umbrella-skill shape** (§0.4): one registered
> skill per plugin anchors path resolution; everything else becomes supporting files under it.

Idempotent, repeatable per plugin. Target shape — **two layouts, decided by file count** (§2.6),
both under the umbrella directory `plugins/<plugin>/skills/patterns/`:

- **Single-file ref:** `skills/patterns/<name>.md` (frontmatter stripped or kept as heading).
- **Multi-file ref:** keep the **directory** — `skills/patterns/<name>/` with the old `SKILL.md`
  renamed to **`index.md`** (no nested `SKILL.md` below the umbrella, so the registry cannot
  re-discover it) + the co-located `template.md`/`examples.md` unchanged. The relative
  `[template.md](template.md)` link survives because the directory moved intact. **Do not
  flatten** — it orphans the companion and collides the 18 identically-named `template.md` files.

The umbrella `skills/patterns/SKILL.md` is a short index: one line per contained pattern
(name → relative path → one-clause purpose). Consumers resolve paths **relative to the loaded
umbrella skill's directory** — the same registry-anchored mechanism that makes today's
companion links work. Cross-plugin shared refs (bucket B) move into a **`spec-core` umbrella**
(e.g. `spec-core:shared-patterns`) that consumers frontmatter-load; no vendoring, no
inter-plugin paths.

### Per-plugin steps (run for each of domain / application / persistence / rest-api / messaging)

1. **Stale sweep first.** Delete this plugin's E-bucket refs and any stale forward-references it
   emits. Verify: `grep -rl "<plugin>:<deleted-ref>" plugins/` returns nothing. (Re-verify the
   stale list against the current tree — §0.3.)
2. **Create the umbrella + relocate refs.** Create `skills/patterns/SKILL.md` (index). Then per
   ref, classify by `find plugins/<plugin>/skills/<ref> -type f | wc -l`:
   - **Single-file:** `git mv plugins/<plugin>/skills/<ref>/SKILL.md
     plugins/<plugin>/skills/patterns/<ref>.md` and remove the empty dir.
   - **Multi-file:** `git mv plugins/<plugin>/skills/<ref> plugins/<plugin>/skills/patterns/<ref>`
     then `git mv .../patterns/<ref>/SKILL.md .../patterns/<ref>/index.md`.
   Add each to the umbrella index. Idempotent: skip if already under `skills/patterns/`.
3. **Rewrite the dynamic union loaders (the one that matters most).**
   - **domain:** `code-implementer` Step 3 reads `- **Pattern**: a; b` docstring lines, takes the
     UNION, and `Skill`-loads each. Replace each Skill-load with a **Read** of
     `<patterns-skill-dir>/<pattern>{.md,/index.md}` (the directory is known because the umbrella
     is in the agent's frontmatter `skills:` list and loads with its location). Keep the
     union/dedupe logic. **Add a hard-fail if the path is missing.**
   - **other 4 layers:** the same union is brief-mediated — `code-change-writer` Step 2 iterates
     the `- Patterns:` bullet of `code-brief.md` and Skill-loads each name. Convert to umbrella
     Reads identically. (Best: have `code-brief-writer` / `pattern-assigner` write resolved
     **paths relative to the umbrella** so this loop reads paths directly — one-site fix.)
4. **Rewrite frontmatter (the second site).** Strip every demoted name from the `skills:` list of
   every implementer/writer agent and add the **umbrella skill** in its place; where prose relied
   on auto-loaded skill bodies, add an explicit Read of `<patterns-dir>/<name>.md`. Verify both
   sites moved together (no two-site drift).
5. **Orchestrator-template refs (bucket D).** Same treatment: move into the plugin's umbrella
   (or the spec-core umbrella if shared) and rewrite each Skill-load in skill bodies/agent prose
   to an umbrella-relative Read. (The 5 `naming-conventions` copies no longer exist — §0.3.)
6. **Cross-plugin shared refs (bucket B).** Move each into the `spec-core` umbrella; every
   consuming agent adds `spec-core:shared-patterns` (or reuses an existing spec-core skill) to
   its frontmatter and Reads the file relative to it. Prioritize the hub
   `domain-spec:updates-report-template` (4 foreign) and `domain-spec:domain-exceptions`
   (application reuse across 5 files). Size off `foreignPluginCount`, **not** raw grep counts.
   Do **not** vendor (§0.3).
7. **Bump `plugin.json` version** (user-visible: skills leave the catalog and the slash-skill list).

### Cross-cutting verification (after each gate)

- **No dangling tokens:** `grep -rEn "[a-z-]+-spec:[a-z-]+" plugins/*/agents/*.md plugins/*/skills/*/SKILL.md`
  — every hit must be either a still-registered command/agent/umbrella or already rewritten to an
  umbrella-relative path; no bare token for a demoted/deleted ref.
- **Both wiring sites moved:** for each demoted pattern, confirm it appears in **zero**
  frontmatter `skills:` lists AND that its union loader now Reads the umbrella path.
- **No re-discovery:** `find plugins/*/skills/patterns -mindepth 2 -name SKILL.md` returns
  nothing (all nested copies renamed to `index.md`), and `/doctor` shows the umbrella as ONE
  catalog entry per plugin.
- **Path existence:** every `patterns/<name>.md` (or `patterns/<name>/index.md`) referenced by a
  loader actually exists (the guard from step 3 should make a missing one fail loud, not skip
  silently).
- **Companion integrity (multi-file refs, §2.6):** for each relocated multi-file ref, confirm the
  `template.md`/`examples.md` moved alongside its `index.md` and the relative link still resolves
  from the new location — `grep -l "\](template.md)" skills/patterns/*/index.md` then verify the
  sibling exists. No `template.md` should land directly in the flat `patterns/` dir.
- **Cross-plugin resolution:** an agent whose frontmatter loads the spec-core umbrella can Read a
  shared ref with the **consuming plugin's own** plugin set enabled — verified via a live agent
  probe (the §0.2 method), not by inspection.
- **Re-count and gate:** recompute the active catalog (entries *and*, if size-based, injected
  description bytes) and compare to budget. Stop at the first gate that clears.
- **Output-equivalence:** run the affected top-level orchestrator
  (`generate-domain` / `generate-application` / … / `update-code`) end-to-end and diff generated
  output against a pre-change golden run (modulo LLM drift) — without a golden harness, "no
  regression" is unfalsifiable given the dynamic-name risk.
