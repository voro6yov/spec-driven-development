---
name: unify
description: Unify high-maturity concept pages that have accreted source-by-source — lift cross-source synthesis into `## What it is` and collapse `## Across sources` to thin per-source provenance — by fanning out the `concept-unifier` agent one page at a time. Detects drifted pages, repairs them, and reports. Use after a batch of ingests, or when `## Across sources` has grown into a per-chapter ledger.
---
# Unify accreted concept pages

`$ARGUMENTS` = optional scope — a concept name (`{{EXAMPLE_CONCEPT}}`), a tag/domain (`teams`), or empty for **all** drifted high-maturity pages.

**Flag — `--review`.** Recommended for unification — these are prose rewrites, not mechanical fixes. If present, strip it out (the remainder is the scope) and present the worklist + per-page diffs for approval; otherwise apply page-by-page with a diff summary.

First load the **`conventions`** skill and read `conventions/concept/` → *"Synthesis in the body, provenance in `## Across sources`"* — the canonical target shape this skill enforces. It is the same rule the `concept-unifier` agent applies; the agent repairs **one** page, this skill **selects and orchestrates**.

## 1 — Detect the worklist
Scope to `maturity: growing|evergreen` (seedlings are too new to bother). A page is a **candidate** when its `## Across sources` shows accretion drift — any of:
- a bullet that runs to a paragraph (heuristic ≳ 50 words) — buried synthesis or a per-chapter wall;
- `#bullets > #sources` — a per-chapter ledger;
- a single bullet that recaps a source chapter-by-chapter.

A bash sweep over `concepts/*.md` computes these (per-source bullet count vs the frontmatter `sources` count; max bullet word-count). Rank by severity (worst single bullet, then total `## Across sources` words). **Exclude nothing on body length alone** — a long `## What it is` is fine; the agent decides cohesive-vs-cluster-vs-hub per page and leaves cohesive pages essentially untouched.

## 2 — Order & dispatch
Order the worklist so a **child concept is unified before any hub that delegates to it** (so the hub can safely push detail to an already-finished page). Then invoke **`@concept-unifier <page>` once per page, sequentially** — never in parallel: hub delegation writes into neighbour (child) pages, and concurrent agents would clobber shared neighbours (the same reason `/ingest` drives a book chapter-by-chapter). Each invocation runs in its own fresh context.

## 3 — Gate & report
- **`--review`:** present the ranked worklist first and **STOP** for go/no-go; then apply, showing each page's before/after diff.
- **Default:** apply page-by-page, emitting each agent's one-line report (shape, `## What it is` and `## Across sources` deltas, any child delegation).

End with a summary: pages unified vs skipped (already-unified), total detail delegated to children, and the `git add -A && git commit && git push` reminder.
