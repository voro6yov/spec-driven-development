# wiki-scaffold — design notes

Status: **design / first draft** · Date: 2026-06-26 · Name: *provisional (see §9)*

A "from scratch" capability for **knowledge**, the sibling of `project-scaffold`'s
"from scratch" capability for **code**. `project-scaffold` turns an empty git repo
into a runnable microservice skeleton; `wiki-scaffold` turns a pile of raw inputs
into a runnable, well-shaped **LLM-maintained knowledge base** — with the right page
types, kinds, relationships, schema, and operating skills already in place.

The distinctive move: the setup is not a fill-in-the-blanks template. It is a
**prism-driven interview** that *derives* the wiki's representation from a few sample
raw inputs, using the ontology-prism / KEOPS method as its elicitation engine.

> Reference implementation: `~/dev/wiki/knowledge-base` is a hand-built instance of
> exactly the wiki this plugin scaffolds (three layers `raw/` + wiki + `CLAUDE.md`,
> `/ingest`·`/query`·`/lint` skills, `index.md`/`log.md`). This plugin extracts the
> domain-agnostic core of that repo and makes the domain-specific parts *derived*
> instead of hand-authored.

---

## 1. The two source ideas

**LLM Wiki** (Karpathy, 2026) — instead of [[RAG]] re-deriving knowledge per query,
have an LLM *compile* raw sources once into a persistent, interlinked markdown wiki
and keep it current. Three layers (`raw/` immutable sources · the LLM-authored wiki ·
a `CLAUDE.md` schema), three operations (ingest · query · lint), `index.md` + `log.md`.
Near-zero maintenance cost is what makes it viable where humans abandon wikis.

**Ontological Prisms** (Fannader, 2026) — a knowledge-engineering framework that
refracts knowledge into a triptych of **facts** (observed worlds), **concepts**
(meanings/intents), and **categories** (shared representations), kept *separately
identified yet interoperable*. Its engineering methodology, **KEOPS**, builds an
ontology iteratively/incrementally, **starting from facts**, characterizing things
with a finite set of **modalities**, and framing deliverables as **commitments**
(use cases) rather than requirements.

**The synthesis** (worked out in the reference KB; see its
`concepts/llm-maintained-knowledge-base.md` and `concepts/ontological-prism.md`):
the two have an almost exact division of blind spots.

- The LLM wiki supplies the **maintenance engine** the prism never staffs — the
  prism has no account of *who* keeps a living ontology current at near-zero cost.
- The prism supplies the **representational discipline** the wiki hand-waves —
  Karpathy says cross-references are "already there" but never says how they're
  *typed*, how a concept (meaning) is kept distinct from its page-*kind* (category),
  or how heterogeneous domains stay consistent as one wiki spans them.

This plugin sits exactly on that seam.

---

## 2. The gap this plugin closes

Standing up a *good* LLM wiki is easy to start and hard to get right. The hard part
is the **schema**: the `kind` registry, the page types, the relationship vocabulary,
the frontmatter. Those are load-bearing (the reference KB's whole quality rides on
them) but they require ontology-design judgment most people don't have — and a bad
initial ontology makes the wiki **rot confidently** (the wiki's #1 documented
failure mode). So most people either:

- never type anything (a flat pile of notes — no compounding graph), or
- over-engineer a baroque taxonomy up front that never survives contact with real
  inputs.

The plugin's bet: **don't ask the user to design an ontology — derive it from their
facts and have them ratify it.** That is precisely what the prism's facts-first
KEOPS method does.

---

## 3. Why the prism fits (it already specifies this pipeline)

The interview is, almost line for line, a lightweight conversational **KEOPS** run:

| KEOPS says | The interview does |
| --- | --- |
| "Mapping extensions — start **not from requests but from facts**." | Stage 1: the user pastes 2–3 real raw inputs. |
| Characterize individuals with **modalities** before deciding entity-vs-aspect. | Stages 2–4: the 7 modalities become a finite, plain-language questionnaire. |
| Frame deliverables as **commitments / use cases** (OPUC), not requirements. | Stage 6: "what will you *do* with it?" selects which operations to ship. |
| "KEOPS cannot run on sequential **layered stacks** — agentic collaboration relies on **conversational loops**." | The setup is an **interview**, not a static config form — the book sanctions the modality. |
| **Foundational** vs **domain** ontology: shared upper concepts, varying domain categories. | The **plugin** is the foundational layer (shared mechanism); each **scaffolded wiki** is a domain ontology. |

The prism's "unfold a third dimension to separate **concepts** (meaning) from
**categories** (representation)" is the single most valuable thing it buys: it forces
the interview to keep *what a thing means* distinct from *how you file it* —
conflating those is the most common way a hand-rolled KB rots.

---

## 4. The 7-stage interview → scaffold mapping

The core flow. Each stage has a prism mechanism (its principled job) and a concrete
output. The LLM **proposes**, the human **ratifies** (the prism's *judgment firewall*:
observation/reasoning are shareable with the agent, judgment is reserved for people).

| # | Interview stage (plain question) | Prism mechanism | Scaffolds |
| --- | --- | --- | --- |
| 1 | "What raw inputs will you feed it? Paste 2–3 real samples." | Extensional realm / *mapping extensions* (facts-first) | `raw/<medium>/` layout (manual drop) |
| 2 | "What entities/meanings recur in these?" (LLM does entity-resolution; you ratify) | Intensional realm / *perception* | The **concept** page type + a seed list of pages |
| 3 | "How do you *file* them — by what categories?" (kept separate from #2) | Logical realm — the "unfold the third dimension" move | The **`kind` registry** in `CLAUDE.md` |
| 4 | Walk the 7 modalities as everyday questions | Modalities | **Frontmatter schema** — temporality/veracity→`maturity`/staleness; agency→author/stakeholder pages; structure→part-of; identity→naming |
| 5 | "How do these relate — parts? kinds? trade-offs?" | Connector dichotomy / gears | The **reciprocal relationship vocabulary** |
| 6 | "What will you *do* with it — answer Qs? track decisions? audit?" | OPUC 2×2 (bounded/open × homo/heterogeneous) | **Which operating skills** to ship (query always; lint=alignment; unify/maps=interoperability) |
| 7 | Scaffold → ingest the samples → review → refine | Iterative/incremental + last-responsible-moment | The dogfood loop that **ratifies the ontology on contact** |

---

## 5. What gets scaffolded

The output is a ready-to-run wiki directory (its own git repo or a subdir):

```
<wiki>/
├── CLAUDE.md            ← GENERATED from the interview (page types, kind registry,
│                          relationship vocabulary, frontmatter schema, operations)
├── README.md            ← GENERATED (how this wiki works + the loop)
├── .gitignore           ← raw/ binaries ignored, markdown tracked
├── index.md  log.md     ← empty catalog + empty log
├── raw/<medium>/        ← fact cache, per the input types from stage 1
├── concepts/            ← the spine (seeded with stage-2 pages, ratified)
├── sources/             ← provenance
├── authors/  maps/      ← only if stage 4/6 call for them
└── .claude/
    ├── skills/          ← ingest · query · lint (+ unify) — COPIED from templates,
    │   │                   vocabulary INJECTED from the interview
    │   └── conventions/ ← per-type page specs — COPIED, examples drawn from the
    │                       user's own sampled facts (not software-architecture)
    └── agents/          ← books-ingester / concept-unifier (verbatim)
```

**Provenance of the templates:** the generic operating skills + the two
domain-agnostic agents were extracted (Phase 2, done) from the reference KB's
`.claude/` into the `templates` reference skill. Most text is **verbatim mechanism**;
the per-wiki kind registry and relationship vocabulary live in the *generated*
`CLAUDE.md` that the copied skills already reference, so only **four** slots remain
(`{{WIKI_NAME}}`, `{{ONE_LINER}}`, `{{DOMAIN}}`, `{{EXAMPLE_CONCEPT}}`). The scaffolder
resolves the templates dir via the `spec-core:modules` "loaded-skill-dir reveals its
own directory" trick, copies, renames `index.md → SKILL.md` for entry files, and fills
the slots.

---

## 6. Feasibility gradient (be precise about "scaffold skills/agents")

- **Interview + `CLAUDE.md` + conventions generation → high.** Structured text from a
  filled template; the modalities supply the question set.
- **Operating-skill scaffolding → medium.** ingest/query/lint are ~95% generic in the
  reference KB — *stamp the generic ones and inject the derived vocabulary*, don't
  synthesize.
- **Agent scaffolding → verbatim only.** `books-ingester` / `concept-unifier` ship
  unchanged; no agents are synthesized. Source acquisition is **manual drop into `raw/`**
  (fetchers were dropped — see §10).

The whole thing is plain markdown + git — **zero infrastructure**. The risk profile
is *refactor + packaging of a working reference implementation*, not greenfield.

---

## 7. Risks & mitigations

1. **Over-engineering — the #1 failure mode.** The prism is enterprise-ontology-grade;
   most personal wikis need ~5 kinds and ~5 relationships, and KEOPS itself concedes
   it has "no stopping rule — knowledge grows at the edges." *Mitigation, in the
   theory itself:* modalities are **discretionary, Occam-parsimonious** ("introduced
   or withdrawn as needed," applied early to "hit the ground running"); OPUC's
   **bounded** scope. The interview must hard-bias to a *minimal viable ontology* and
   let it grow. If it emits a 12-kind taxonomy on day one, it failed.
2. **Deriving concepts from samples is fuzzy** — entity-resolution readmits the
   statistical/GenLM inference the book elsewhere distrusts. *Mitigation:* the
   judgment firewall — the LLM proposes, the human ratifies. Output is a **draft**,
   never an authoritative ontology.
3. **Validation only happens on contact with real ingests.** *Mitigation:* stage 7 is
   not optional polish — scaffold, ingest 2–3 real samples, see whether the
   kinds/relations held, refine. That is KEOPS being bidirectional/iterative.
4. **Translating modality-speak into plain questions is the real authoring work.** The
   prism is abstract/philosophical; if the skill dumps prism vocabulary at the user
   it's useless. The `prism-interview` reference skill owns this translation — it is
   the make-or-break artifact.

---

## 8. Relationship to `project-scaffold`

Deliberate sibling, same shape, different substance:

| | `project-scaffold` | `wiki-scaffold` |
| --- | --- | --- |
| Bootstraps | a **code** repo (microservice skeleton) | a **knowledge** repo (LLM-maintained wiki) |
| Driven by | a service name + locked stack | an **interview** over sample facts |
| Core agent | `project-scaffolder` (writes the skeleton) | `wiki-scaffolder` (writes the wiki) |
| Output | runnable repo the spec layers fill in | runnable wiki the `/ingest` loop fills in |
| Then | `/spec-core:init-service` inits layers | dogfood: `/ingest` the sample facts |

No dependency between them; they share only a design philosophy
("interview/derive → scaffold → verify on contact").

---

## 9. Open questions

1. **Plugin name.** `wiki-scaffold` (parallels `project-scaffold`) vs `kb-scaffold`
   vs `prism-wiki`. The marketplace doesn't force `-spec` (cf. `model-diagrams`,
   `adr-log`). Leaning `wiki-scaffold`.
2. **Generic skills: copy-in or reference?** Each scaffolded wiki gets its **own**
   `.claude/skills/` copy (it's a standalone repo, may have no plugin installed) — so
   **copy-in**, like `spec-core:modules`. The plugin holds the parameterized
   templates; the wiki holds the filled copies.
3. **v1 scope.** **Bounded-homogeneous** wikis only (one domain, one realm). Defer
   multi-domain and cross-wiki interoperability (the prism's a-priori interoperability
   is elegant but `[[wikilinks]]` don't span separate git repos natively).
4. **How opinionated is the seed ontology?** Ship 1–2 starter **profiles** (a generic
   concept-graph; an architect-project profile reusing the reference KB's
   `architecture-decision-record`/`risk-storming`/`architecture-characteristics`
   vocabulary) as interview *defaults*, not as the only path.
5. **Where do example pages in the generated conventions come from?** From the
   *sampled facts* (stage 1), so the conventions read in the user's own domain — not
   from `microservices.md`. Requires the scaffolder to write 1–2 worked example pages.

---

## 10. Phased plan

- **Phase 0 (this draft)** — plugin skeleton: manifest, this note, the
  `prism-interview` reference skill (the operationalized prism), the `new-wiki`
  interview skill, and the `wiki-scaffolder` agent contract. No template extraction
  yet; the scaffolder targets a `skills/templates/` group Phase 2 fills.
- **Phase 1 (done)** — the **ontology spec** the interview emits: locked as the
  `ontology-spec` reference skill (every field, default, and validation invariant;
  minimal + architect-project examples). It is the single source of truth `new-wiki`
  emits and `wiki-scaffolder` consumes. De-risks everything downstream.
- **Phase 2 (done)** — **template extraction**: `ingest`/`query`/`lint`/`unify` +
  the `conventions` umbrella (8 themes) + `books-ingester`/`concept-unifier` lifted out
  of the reference KB into the `templates` reference skill, neutralized of
  software-architecture specifics (kinds defer to the generated `CLAUDE.md`; example
  page/book/author names genericized) and reduced to four substitution slots. The
  scaffolder's Step 4 now runs the `templates` copy procedure.
- **Fetchers — dropped.** A personal/curated wiki drops sources into `raw/` by hand; no
  fetcher automation. (Was a planned phase; cut by decision 2026-06-26.)
- **Phase 3 (done)** — **post-bootstrap & ergonomics additions**:
  `/wiki-scaffold:evolve-schema` (the day-N ontology-refinement loop — the keystone, since
  day-0-only contradicts the prism / LLM-wiki / DDD thesis that the schema is a hypothesis that
  must evolve), `/wiki-scaffold:adopt` (retrofit an existing markdown pile), starter
  **profiles** (§9.4) wired as Stage-1 interview defaults, and a prism-aware **lint lens**
  (concept/category separation — the prism's founding distinction).

---

## Provenance

- Reference implementation: `~/dev/wiki/knowledge-base` (`CLAUDE.md`, `.claude/skills/`).
- Source — *LLM Wiki*, Karpathy (2026); the originating idea file.
- Source — *Ontological Prisms*, Fannader (2026); the prism + KEOPS methodology.
- Synthesis filed in the reference KB's `concepts/llm-maintained-knowledge-base.md`
  and `concepts/ontological-prism.md` (the "complementary blind spots" tension).
