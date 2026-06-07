# Consolidating the 5 duplicated `naming-conventions` skills

> **Status — EXECUTED (2026-06-07).** Decision: **Option B (new `spec-core` base plugin)**, not Option A. The single canonical skill lives at `plugins/spec-core/skills/naming-conventions/SKILL.md` (superset of all five); all spec plugins + `model-diagrams` reference `spec-core:naming-conventions` (311 refs rewritten across 117 files); the 5 old copies deleted; the REST package-layout section relocated to `rest-api-scaffolder.md`. marketplace + 6 plugin versions bumped; CLAUDE.md documents the unenforced `spec-core` dependency. Adversarially verified PASS (no content lost, 0 stale refs). The analysis below is the pre-execution design; §5 Option A was the original recommendation, overridden in favor of B for cleaner dependency layering.

## 1. Executive summary

Consolidation is **fully feasible** and should be done. Cross-plugin skill sharing is not just supported in theory — it already ships in this repo (`model-diagrams/diagrams-scaffolder.md` auto-loads `domain-spec:naming-conventions` from its frontmatter today). The five copies have already drifted (5 distinct line counts / md5s, divergent section sets), so the duplication is an active correctness hazard, not a hypothetical one.

**Recommended approach: home a single canonical skill in `domain-spec`** (the pipeline root), make it the **superset** of all five bodies, and rewire the other four plugins (plus `model-diagrams`, already wired) to reference `domain-spec:naming-conventions`. This reuses the one proven cross-plugin precedent verbatim, adds no new plugin, and collapses 5 catalog entries to 1 (helping the active-skills-footprint goal).

The one decision you own: **accept the cross-plugin coupling** that homing introduces (persistence/application/rest-api/messaging will then require `domain-spec` to be enabled), versus paying for a neutral 8th "core" plugin to keep the dependency direction clean. I recommend domain-spec because naming-conventions is currently the *only* shared skill; revisit the core-plugin option only when you consolidate the other ~17 cross-shared references the footprint note identifies.

## 2. Current state

Five byte-divergent copies, one per spec plugin, each declaring `name: naming-conventions` and each referenced through its **own** namespace by its own agents. There is **no** `dependencies`/`requires` field anywhere in `plugin.json` or `marketplace.json` (grep-confirmed), so co-installation is an unenforced runtime assumption.

| Plugin | File | Lines | Self-refs (this plugin's namespace) | Frontmatter `skills:` | Prose |
|---|---|---:|---:|---:|---:|
| domain-spec | `plugins/domain-spec/skills/naming-conventions/SKILL.md` | 232 | 46 | 14 | 32 |
| persistence-spec | `plugins/persistence-spec/skills/naming-conventions/SKILL.md` | 208 | 67 | 25 | 42 |
| application-spec | `plugins/application-spec/skills/naming-conventions/SKILL.md` | 228 | 78 | 24 | 54 |
| rest-api-spec | `plugins/rest-api-spec/skills/naming-conventions/SKILL.md` | 252 | 62* | 14 | 48 |
| messaging-spec | `plugins/messaging-spec/skills/naming-conventions/SKILL.md` | 220 | 58* | 13 | 45 |
| model-diagrams | (no own copy) | — | 2 (→ `domain-spec:`) | 1 | 1 |
| **Total** | | | **313 occurrences** | **91** | **222** |

\* rest-api-spec and messaging-spec each contain **1 cross-plugin** prose reference to `application-spec:naming-conventions` (in their `update-specs/SKILL.md`), because they invoke the borrowed `application-spec:commands-updates-detector` agent. The rest of each plugin's refs target its own namespace.

## 3. Content analysis

Roughly **85–90%** of the content is a byte-identical shared core. `persistence-spec` is effectively the pure core (it has zero unique additions — every other file is `persistence` plus a delta). Per-plugin deltas total ~100–130 unique/changed lines out of ~1140 lines across all five.

### Section-level matrix

| Section | Shared? | Divergences |
|---|---|---|
| YAML frontmatter | **Identical (all 5)** | byte-for-byte; generic cross-plugin description |
| `# Naming Conventions` title | **Identical** | none |
| `## When to consult` | **Identical** | none |
| `## Purpose` | **Identical** | none |
| `## The aggregate stem` (base prose) | **Identical** | domain-spec inserts a `### Python package name derivation` subsection mid-section |
| `### Python package name derivation` | **domain-spec only** | kebab→snake_case rule, stem→pkg table, `^[a-z][a-z0-9_]*$` validation |
| `## Diagram filenames` | 4/5 identical | application-spec adds an **Ops** diagram row + `<op-name>` paragraph + tree line |
| `## Per-plugin sibling folders` (base) | **Identical** | rest-api-spec & messaging-spec each append a distinct cross-plugin-report subsection |
| `### Cross-plugin reads — app-service-axis update reports` | **rest-api-spec only** | 3-col table; same topic as messaging's, different wording |
| `### Cross-plugin shared report: commands-updates.md` | **messaging-spec only** | prose form; semantically overlaps rest-api's, not byte-identical |
| `### <stem>.domain/` folder table | **Identical** | none |
| `### <stem>.application/` folder table | divergent | application-spec adds `updates.md` + 4 ops rows + rewritten paragraph; messaging-spec adds `commands-updates.md`/`queries-updates.md` rows |
| `### <stem>.persistence/` folder table | **Identical** | none |
| `### <stem>.rest-api/` folder table | **Identical** | none |
| `### <stem>.messaging/` folder table | 4/5 identical | messaging-spec adds `updates.md` row + sentence |
| `## Worked example` | 4/5 identical | application-spec adds ops + `updates.md` tree entries |
| `## Path resolution` (heading + intro) | **Identical** | none |
| `### Recovering <dir> and <stem> from inputs` | divergent | application-spec adds an `<ops_diagram>` recovery row |
| `### Deriving sibling paths from <stem>` | divergent | application-spec adds 4 ops/updates rows + rewritten closer; messaging-spec adds 3 updates rows |
| `### Caller responsibilities` | divergent | application-spec adds `<op-name>`/ops to bullet 1 |
| `## Path hygiene (shared rules for file-writing agents)` | **domain-spec only** | 5 numbered rules; closing line self-cites `domain-spec:naming-conventions` |
| `## Generated REST API Python package layout` | **rest-api-spec only** | whole `<api_pkg>/` tree, no-flat-star rule, import snippet |
| `## What NOT to do` | **Identical** | none |

### Genuinely plugin-specific fragments that block a naive merge

1. **domain-spec** — `### Python package name derivation` (kebab→snake; conceptually cross-plugin but worded for domain agents).
2. **domain-spec** — `## Path hygiene` 5 numbered rules; its closing sentence hard-codes the string `domain-spec:naming-conventions`.
3. **application-spec** — the entire **Ops application service** feature (`.ops.<op-name>.md` diagram, `ops.<op-name>.{specs,exceptions,deps,methods}.md`, recovery row, derivation rows, caller-responsibility extras, worked-example entries).
4. **application-spec** — its own `updates.md` (`application-updates-writer`).
5. **rest-api-spec** — `### Cross-plugin reads` subsection (table form).
6. **rest-api-spec** — `## Generated REST API Python package layout` (whole code-gen tree + import snippet).
7. **messaging-spec** — `### Cross-plugin shared report` subsection (prose form; overlaps #5).
8. **messaging-spec** — `commands-updates.md`/`queries-updates.md` rows placed in *its* application-folder table (asymmetric vs rest-api).
9. **messaging-spec** — messaging `updates.md` (`messaging-updates-writer`); note its worked-example tree omits it (an existing inconsistency to fix on merge).

The two cross-plugin-report fragments (#5, #7) cover the **same facts** with **different wording** and cannot collapse to one shared block without a rewrite.

## 4. How references work

- **Frontmatter `skills:` lists (91 occurrences):** one auto-load entry per agent file, e.g. `  - persistence-spec:naming-conventions`. These are the dangerous sites under homing — a missing namespaced skill fails to auto-load **silently**, leaving the agent's "derive paths per X:naming-conventions" prose as a dangling pointer to a body it never read.
- **Prose (222 occurrences):** dominated by a boilerplate "Path resolution." paragraph (~34 sites) saying siblings derive "per `<plugin>:naming-conventions`" and `<dir>`/`<stem>` are "recovered per the recovery table." A Skill-tool or agent **invocation** of a missing namespaced name is a **hard** not-found error (confirmed by `notes/active-skills-footprint.md` Option C).

### Cited section anchors that MUST survive the merge

Any merge must preserve these exact headings/structures or live citations go stale:

- `## Path resolution` and its `### Recovering <dir> and <stem> from inputs` (the recovery table) — referenced by ~49 lines.
- `### Deriving sibling paths from <stem>` (the artifact table).
- `## The aggregate stem` (regex `^[a-z][a-z0-9-]*$` quoted verbatim in ~10 hard-fail ERROR strings).
- `## Diagram filenames` and `## Per-plugin sibling folders`.
- `### Python package name derivation` — cited by `target-locations-finder` (domain) and `consumer-spec-initializer` (messaging).
- `## Path hygiene (shared rules for file-writing agents)` and its **numbered rules 1–5** — cited by exact number: `package-preparer.md` ("Path hygiene rule 2"), `generate-code/SKILL.md` ("Path hygiene rule 5"), plus `code-implementer`/`test-package-preparer`. These citations name `domain-spec:naming-conventions` literally, so homing in domain-spec keeps them valid for free.

### The `model-diagrams` finding

`plugins/model-diagrams/agents/diagrams-scaffolder.md` is the structural odd-one-out and the **proof of concept**: it owns no naming-conventions skill and already references `domain-spec:naming-conventions` in **both** its frontmatter `skills:` list (line 7) and prose (line 12), relying on the aggregate-stem regex and diagram-filename convention. This is the only cross-plugin frontmatter auto-load in the repo — and it points at exactly the home we recommend.

## 5. Cross-plugin feasibility

**Can plugin B use plugin A's skill? Yes — confirmed, high confidence.** An agent in plugin B can both auto-load (`skills: - A:skill`) and invoke (`Skill` tool with `skill: "A:skill"`) a skill homed in plugin A. Evidence: (1) `model-diagrams` already auto-loads `domain-spec:naming-conventions`; (2) four consumer plugins already cross-load other domain-spec skills (`updates-report-template`, `domain-exceptions`); (3) messaging-spec/rest-api-spec already invoke the cross-homed agent `application-spec:commands-updates-detector`; (4) docs: plugin skills are always namespaced `<plugin>:<skill>` and resolve across any installed plugins. **Invocation form is identical everywhere:** `<plugin-name>:<skill-name>` (no leading slash) in frontmatter and the Skill tool; `/<plugin>:<skill>` as a user slash command.

**Self-containment tradeoff.** There is **no manifest dependency mechanism** (grep-confirmed none). If a consumer plugin is enabled without the home plugin: frontmatter auto-load fails **silently** (agent runs without its path contract → silent `src/` path misderivation, the exact bug class CLAUDE.md warns about); Skill/agent invocation fails **hard**. The marketplace bundles all plugins, but enabling is per-plugin, so subset installs are a real, supported action this decision must survive.

### Homing options

| Option | Pros | Cons |
|---|---|---|
| **A. Home in domain-spec** (recommended) | Reuses the one proven precedent verbatim (model-diagrams already auto-loads it). domain-spec is the pipeline root every diagram flows from — natural truth-owner. Keeps the numbered-rule citations valid for free. 5→1 catalog entries. No new plugin. | Creates a hard runtime dependency: 4 consumer plugins break (silent on auto-load, hard on invoke) if domain-spec is disabled. Subset installs (e.g. messaging-only) regress. |
| **B. New `spec-core` plugin** | Cleanest layering: neutral base, no "persistence needs the whole domain plugin" coupling. Natural future home for the other ~17 cross-shared refs (many-to-many → many-to-one). | Adds an 8th plugin + maintenance surface. Doesn't eliminate the hard-dependency problem — relocates it so **all 5** layers depend on the core. Biggest lift. Overkill while naming-conventions is the only shared skill. |
| **C. Home in another layer (e.g. application-spec)** | Also 5→1; application-spec is already read cross-plugin. | Strictly worse than A: weaker dependency direction (domain shouldn't depend on application), and no existing precedent points at application-spec. |
| **D. Status quo (5 copies)** | Zero coupling; any subset install works. | Copies have **already diverged** (5 md5s, different sections) — active correctness bug. Costs 5 entries against the 270-limit. This is the problem to solve. |

**Recommendation: Option A** while naming-conventions is the only shared skill; graduate to Option B if/when you consolidate the broader set of cross-shared references.

## 6. Recommended design

**Where it lives:** `plugins/domain-spec/skills/naming-conventions/SKILL.md` becomes the single canonical skill. The four other copies are deleted; `model-diagrams` already points here.

**Frontmatter (unchanged — it is already correct and identical across all 5):**
```
name: naming-conventions
description: Cross-plugin naming and layout conventions for diagrams and spec artifacts. Defines the canonical aggregate stem, diagram filenames, and per-plugin sibling folder layout.
when_to_use: Use when scaffolding, reading, or writing any sibling spec file produced by domain-spec, application-spec, persistence-spec, rest-api-spec, or messaging-spec.
user-invocable: false
```

**Body = superset of all five.** Build the canonical body by taking the shared core and folding in every divergent fragment so no consumer loses a rule it cites. Strategy per fragment type:

- **Keep (already cross-plugin truth):** `### Python package name derivation` and `## Path hygiene` 5 rules — these are conceptually shared. Edit the Path-hygiene closing sentence's self-citation to read `naming-conventions` generically (it stays in domain-spec, so the literal `domain-spec:naming-conventions` is still accurate and the numbered-rule citations elsewhere stay valid).
- **Fold in (per-plugin artifact rows):** add application-spec's Ops rows + `updates.md`, messaging-spec's `updates.md` + `commands-updates.md`/`queries-updates.md` rows, and the corresponding recovery/derivation rows. These are additive table rows; they describe real artifacts every layer may need to *read*, so the superset is correct for all.
- **Merge the two overlapping cross-plugin-report subsections (#5, #7)** into **one** canonical subsection under `## Per-plugin sibling folders` (prefer the rest-api-spec table form; absorb messaging's command-side-only caveat as a note). This removes the only true wording conflict.
- **Move out (genuinely one-plugin code-gen detail):** `## Generated REST API Python package layout` is rest-api-specific code-generation layout with no cross-plugin value in a naming skill. **Relocate it into rest-api-spec's own agent/skill prose** (e.g. the scaffolder or `generate-code/SKILL.md`) rather than bloating the shared skill. This is the one fragment that should *not* live in the shared body.
- **Fix the known inconsistency:** add messaging's `updates.md` to the worked-example tree (it is currently omitted).

**Do not keep thin per-plugin stubs.** Stubs reintroduce N files (defeating the footprint goal) and a stub that merely `defer`s still needs the home plugin loaded — same coupling, more surface. One real skill + namespaced references is cleaner.

**Prose anchors preserved:** because the superset retains every heading from §4 verbatim (`## Path resolution`, `### Recovering…`, `### Deriving sibling paths…`, `## The aggregate stem`, `### Python package name derivation`, `## Path hygiene` rules 1–5), all ~313 citations resolve correctly after only their **namespace prefix** is rewritten.

## 7. Migration plan

Do this as two phases: a **pure content merge first** (no homing change), then the **rewire**. This keeps each step independently reviewable.

1. **Reconcile into the superset.** Edit `plugins/domain-spec/skills/naming-conventions/SKILL.md` to the superset body described in §6 (fold in ops/updates rows, merge the two cross-plugin-report subsections, fix the worked-example, relocate the REST package-layout section into rest-api-spec). Verify the existing domain numbered-rule citations still match.
2. **Relocate the REST-only section** out of the skill and into rest-api-spec prose (its scaffolder or `generate-code/SKILL.md`).
3. **Rewrite references** from each plugin's own namespace to `domain-spec:naming-conventions`. Exact counts to rewrite (occurrences, frontmatter + prose):
   - `persistence-spec`: **67** (25 frontmatter `skills:` entries + 42 prose)
   - `application-spec`: **78** (24 frontmatter + 54 prose)
   - `rest-api-spec`: **61** own-namespace (14 frontmatter + 47 prose); its **1** existing `application-spec:naming-conventions` prose ref is intentional and stays (the borrowed detector still derives via application-spec) — leave it as-is.
   - `messaging-spec`: **57** own-namespace (13 frontmatter + 44 prose); its **1** `application-spec:naming-conventions` ref also stays.
   - `domain-spec`: **0** to rewrite (already its own namespace; these become the canonical references).
   - `model-diagrams`: **0** (already `domain-spec:naming-conventions`).
   - **Total to rewrite: ~263** occurrences across 4 consumer plugins. A scripted `sed` of `s/<plugin>-spec:naming-conventions/domain-spec:naming-conventions/g` per plugin handles the bulk; manually leave the 2 deliberate `application-spec:` refs.
4. **Delete the 4 duplicate skills:** `plugins/{persistence,application,rest-api,messaging}-spec/skills/naming-conventions/SKILL.md` (and their now-empty `naming-conventions/` dirs).
5. **Bump `plugin.json` versions** for every plugin whose files changed: `domain-spec` (skill body), `persistence-spec`, `application-spec`, `rest-api-spec`, `messaging-spec` (refs + the rest-api relocation). `model-diagrams` is unchanged → no bump.
6. **No `marketplace.json` change** under Option A (no new plugin). If you later choose Option B, that step is added: new `plugin.json` for the core plugin + a `marketplace.json` entry + rewriting references to the core prefix instead.
7. **Update `CLAUDE.md`** to document that naming-conventions is homed in domain-spec and that the four consumer plugins now require domain-spec to be enabled (since no manifest dependency enforces it).
8. **Add an availability guard** at cross-plugin reference sites (see §8) to convert the silent-misderivation failure mode into a loud one.

## 8. Risks & open decisions

**Risks if executed naively:**
- **Silent path misderivation** if a consumer is enabled without domain-spec: the frontmatter auto-load quietly no-ops and the agent derives `src/` paths by ad-hoc substitution — exactly the bug class CLAUDE.md warns about. Mitigate with step 8's guard: each consumer's path-resolution prose should hard-fail with `ERROR: domain-spec:naming-conventions not available — enable the domain-spec plugin` rather than proceeding.
- **Stale numbered-rule citations** if the merge drops or renumbers Path-hygiene rules 1–5, or renames `## Path hygiene`. Keep the heading and rule numbering byte-stable.
- **Lost rules from divergent sections** if the merge isn't a true superset (e.g. dropping application's ops rows or messaging's updates rows). The §6 fold-in list is the checklist.
- **Worse subset-install blast radius:** homing adds 4 consumer plugins that hard-depend on domain-spec being enabled (the existing 18 cross-plugin refs already carry this fragility; this widens it).

**Decisions the user owns:**
1. **Coupling vs. self-containment — the central call.** Accept that persistence/application/rest-api/messaging now require domain-spec enabled (Option A, recommended), versus paying for a neutral `spec-core` plugin (Option B) to keep the dependency direction clean. My recommendation: A now, B only when you consolidate the broader ~17 cross-shared references.
2. **Whether to create a new shared plugin** at all (the Option B fork). This is worth it only if naming-conventions stops being the sole shared skill.
3. **Should the REST package-layout section move out of the skill** (recommended) or stay folded into the shared body? It is the one fragment with no cross-plugin value.
4. **Whether to add the availability guard now** (recommended, since there's no manifest dependency) or defer it as a known, documented risk.