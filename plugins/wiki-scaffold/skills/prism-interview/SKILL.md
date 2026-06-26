---
name: prism-interview
description: The ontology-prism / KEOPS playbook that the wiki-scaffold interview runs on — translates the prism's facts/concepts/categories triptych, its seven modalities, and its alignment-vs-interoperability split into a finite, plain-language questionnaire that derives a new wiki's representation from sample raw inputs. Load when running /wiki-scaffold:new-wiki. Reference only.
user-invocable: false
disable-model-invocation: false
---

# Prism interview playbook

**Type:** Reference (the knowledge `/wiki-scaffold:new-wiki` runs on).

This is the operationalized [ontology prism]. The book is abstract and philosophical;
this doc is the opposite — a bounded set of **plain questions with strong defaults**,
each tied to the one prism mechanism it implements. You are running a lightweight,
conversational **KEOPS**: start from facts, characterize with modalities, frame the
deliverable as a commitment. Never recite prism vocabulary at the user — ask the
everyday question; keep the theory in your head.

## Three standing rules

1. **Minimal viable ontology — the prime directive.** The single biggest failure is an
   over-elaborate taxonomy that never survives contact with real inputs. Modalities are
   *discretionary* (Occam-parsimonious — introduce only what a sample forces). **Floor:
   2 page types (`concept`, `source`), ~3–5 kinds, ~4 relationships.** Push back on
   anything richer unless a sampled fact *demands* it. A 12-kind taxonomy on day one is
   a failed interview.
2. **You propose, the human ratifies — the judgment firewall.** Deriving structure from
   samples (entity resolution) is inference, not truth. Present everything as a **draft
   to confirm or edit**, never as settled. Observation and reasoning are yours;
   judgment is the user's.
3. **Separate meaning from filing — unfold the third dimension.** Keep *what a thing
   means* (a **concept** — Stage 2) distinct from *how you file it* (a **kind / category**
   — Stage 3). Conflating them is the most common way a KB rots. This separation is the
   prism's founding move and the chief thing it buys you.

## Facts → concepts → categories (the map under every stage)

- **Facts** = the raw inputs (`raw/`). Observed, immutable, the source of truth.
- **Concepts** = the recurring *meanings* abstracted from facts (the `concepts/` spine).
- **Categories** = the shared *representations* that file concepts (the `kind` registry,
  page types). Derived from facts, *up* through concepts — never imposed top-down first.

---

## The seven stages

Run them in order, but conversationally — fold follow-ups in, skip a stage's deeper
questions when the default obviously holds. Each stage names: the **question**, the
**mechanism** (why), the **default**, and what it **emits** into the ontology spec.

### Stage 1 — Facts: "What will you feed it?"

- **Ask:** "What raw inputs will this wiki digest? Paste 2–3 real samples." Accept books,
  articles, chat logs, meeting notes, ADRs, tickets, code, papers, journal entries…
- **Mechanism:** *mapping extensions* — KEOPS starts from facts, not requirements. The
  samples are the ground truth every later stage is derived from and validated against.
- **Default:** one medium (e.g. books). Multiple media is fine but each adds a `raw/`
  subfolder.
- **Offer a profile (optional):** if a starter `profiles` template fits the samples' shape,
  offer it as a *starting point to refine* — never the answer; the user may start blank. The
  minimal-ontology rule still governs (drop any profile kind/relationship the samples don't
  justify).
- **Emits:** `raw/<medium>/` layout; the corpus the LLM reads for Stages 2–5.

### Stage 2 — Concepts: "What recurs here?"

- **Do:** read the samples and **propose** the recurring entities/meanings — the things
  the user will want a page *about*. Present as a short ratifiable list.
- **Mechanism:** *perception* / entity resolution — abstract intrinsic threads out of
  unstructured facts into concept candidates.
- **Page-worthy test (intrinsic-identity heuristic):** a candidate earns a page if it has
  a clear **intrinsic identity** (you can write a one-sentence definition + at least one
  relationship). If it's only a "kind-of" tag with no standalone meaning, it's a **tag,
  not a concept** — note it as a tag, don't mint a page. (Book's tell: `_AlcoholicBeverage`
  resolves; `_Diet` doesn't.)
- **Default:** the `concept` page type, plus `source` for provenance. Seed 5–15 concept
  pages from the samples.
- **Emits:** the `concept` page type; a seed concept list (each: name + one-line def).

### Stage 3 — Categories: "How do you file them?"

- **Ask:** "Across those concepts, what *kinds* of thing are they? Group them." Steer to a
  small set of **categories** that classify concepts — NOT more concepts.
- **Mechanism:** *logical realm* — categories are shared representations, the `kind`
  registry. This is where you **unfold the third dimension** (Rule 3): a `kind` is how you
  file a meaning, not a meaning itself.
- **Default:** start from the sample's natural grouping; cap at ~3–5 kinds. The reference
  KB's software-architecture set (`pattern`/`principle`/`technology`/…) is an *example of
  the shape*, not a default to copy — derive the user's own.
- **Emits:** the `kind` registry (open — "add one when a concept fits none cleanly").

### Stage 4 — Modalities: the frontmatter questionnaire

Walk the seven modalities as everyday questions. Each decides a slice of the **frontmatter
schema** and which **page types** beyond `concept`/`source` exist. Ask only the ones a
sample makes live; take the default otherwise.

| Modality | Plain question | Decides | Default |
| --- | --- | --- | --- |
| **Temporality** | "Do entries have a lifecycle / go out of date?" | a `status`/`maturity` field; whether `log.md` matters | `maturity: seedling/growing/evergreen` |
| **Veracity** | "Do you need to track how *settled* a claim is (observed vs asserted vs deduced)?" | richer status; staleness checks in lint | folded into `maturity` |
| **Agency** | "Are there *actors* — people, teams, agents — in this domain?" | whether `author`/`stakeholder` page types exist | `author` page type (optional) |
| **Structure** | "Are things *made of* other things (parts/wholes)?" | a part-of relationship (Stage 5) | none unless a sample shows composition |
| **Identity** | "How is each entry named/identified?" | filename scheme (kebab slug vs id) | kebab-case slug |
| **Communication** | "Will pages cite each other / external sources heavily?" | `sources[]` frontmatter + `## Across sources` | yes (it's a wiki) |
| **Tally/Realm** | "One domain, or several heterogeneous ones?" | single vs multi-`raw/`; maps later | single (bounded — see Stage 6) |

- **Emits:** the frontmatter schema; any extra page types (`author`, `map`, domain-specific).

### Stage 5 — Connectors: "How do they relate?"

- **Ask:** "Pick the few ways these entries connect." Offer the small reciprocal starter
  set and let them keep/cut/add.
- **Mechanism:** the connector dichotomy — one neutral syntax, realm-specific semantics.
  Two families: **parthood** (composition/specialization — `specializes`, `part-of`) and
  **association** (functional ties — `enables`, `requires`, `trades off against`,
  `alternative to`). Every relationship is **reciprocal** (symmetric, or an inverse pair)
  — lint mirrors the other side, so the wiki only ever wires one direction.
- **Default (4):** `specializes↔generalizes`, `requires↔required-by`, `enables↔enabled-by`,
  `trades off against` (symmetric). Add `part-of` only if Stage 4 structure was live.
- **Emits:** the relationship vocabulary (verb + reciprocal + symmetric?).

### Stage 6 — Use case: "What will you *do* with it?"

- **Ask:** "Mostly answer questions? Track decisions over time? Audit/keep it consistent?
  Explore an open question?" And: "One subject area, or several that overlap?"
- **Mechanism:** OPUC — type the work by **scope** (bounded vs open) × **realm**
  (homogeneous vs heterogeneous) to pick the **operations** (skills) the wiki needs.
  - *ingest* + *query* — always.
  - *lint* (= **alignment**, static consistency) — whenever the graph should stay
    reciprocal/orphan-free. Default on.
  - *unify* / *maps* (= **interoperability**, cross-domain co-evolution) — only when the
    wiki spans **heterogeneous** sub-domains (Stage 4 "several"). Default off for v1.
- **v1 guard:** steer to **bounded-homogeneous** (one domain, one realm). Multi-domain is
  a later phase.
- **Emits:** the operations list (which skills to scaffold).

### Stage 7 — Commit & dogfood: "Let's test it on your samples."

- **Do:** present the assembled **ontology spec** (page types, kinds, relationships,
  frontmatter, operations) for final ratification. Then hand it to the scaffolder,
  and **ingest the Stage-1 samples into the fresh wiki**.
- **Mechanism:** iterative/incremental engineering + *last responsible moment* — the
  ontology is a **commitment, not a requirement**, proven on contact and cheap to revise.
- **Refine loop:** if the first ingest shows a kind that's never used, a missing
  relationship, or a concept/category confusion, **adjust the spec and re-stamp** the
  `CLAUDE.md`/conventions. Knowledge grows at the edges; the day-one ontology is a seed.
- **Emits:** a validated wiki + the first real pages; a short "what changed after first
  ingest" note.

---

## The ontology spec (the hand-off)

The interview's deliverable, consumed by `@wiki-scaffold:wiki-scaffolder`. Its exact shape —
every field, default, and validation invariant — is the **`ontology-spec`** reference skill
(the single source of truth; do not re-document it here). As you run the stages, accumulate
the spec's fields; each stage above names what it *emits* into it. Keep it small — it encodes
a *minimal viable ontology* (Rule 1), not an exhaustive one.

## Anti-patterns to refuse

- A taxonomy richer than the samples justify (Rule 1). Cut it back.
- A `kind` that is really a concept, or a concept that is really a tag (Rule 3 / Stage 2
  test). Re-file it.
- Wiring both directions of a relationship by hand (lint mirrors — wire one).
- Designing for a domain the user can't show you a sample of. No fact → no derived
  structure; ask for the sample or defer the structure.
