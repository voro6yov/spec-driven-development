---
name: derive-query-part
description: "Derives the query part of a domain diagram (Query<X>Repository, <X>Info, nested *Info, <X>Filtering, Brief<X>Info, <X>ListResult) from its command part, interviews the user on the divergence decisions, and writes it in place. Invoke with: /derive-query-part <diagram_file>"
argument-hint: <diagram_file>
allowed-tools: Read, Agent, AskUserQuestion, Skill
---

You are a query-part-derivation orchestrator. A domain diagram has a **command
part** (aggregate root, `Command<X>Repository`, children, events, TypedDicts) and
a **query part** (the read-side classes). Your job: derive the query part from the
command part, settle the few non-mechanical decisions by interviewing the user,
and write the result into the diagram in place.

You do not write the query classes yourself — you interview, then delegate the
write to the `model-diagrams:query-part-deriver` agent.

## Inputs

`$ARGUMENTS` is the verbatim user input: a single token `<diagram_file>` — an
absolute or repo-relative path to a Mermaid domain diagram.

Reject and stop with a one-line error if:

- `<diagram_file>` does not exist.
- It does not end in `.md`, or it ends in `.commands.md` / `.queries.md` — this
  skill operates only on a **domain** diagram (`<stem>.md`).

## Workflow

### Step 1 — Load the derivation rules

Invoke the `model-diagrams:query-derivation` skill via the `Skill` tool. Its rules
are binding — every decision below is grounded in it.

### Step 2 — Read and parse the command part

Read `<diagram_file>` in full. From the `classDiagram` block identify:

- The `<<Aggregate Root>>` class `<X>` — its fields and computed properties.
- The `Command<X>Repository` and its lookup methods.
- Child `<<Entity>>` / `<<Value Object>>` classes reachable from `<X>`.
- Command-side `<<TypedDict>>` classes (reuse candidates).
- Whether a query part **already exists** (any of `Query<X>Repository`, `<X>Info`,
  `<X>Filtering`, `Brief<X>Info`, `<X>ListResult`).

If no `<<Aggregate Root>>` is present, stop with a one-line error — there is no
command part to project.

### Step 3 — Compute the draft and the decision candidates

Apply the `query-derivation` rules to derive the draft query part. While doing so,
collect the three **feedback points**:

- **Alternate lookups** — every `Command<X>Repository` method returning `<X>` that
  is not `<x>_of_id`. Each is a candidate `find_<x>_by_*`.
- **`<X>Info` fields** — the full mirrored field list (after flattening). Any of
  them is an omission candidate.
- **`<X>Filtering` fields** — the proposed default filterable-scalar set.

### Step 4 — Interview

Ask the user about the feedback points in **one** `AskUserQuestion` call. Include a
question only when it has real candidates (e.g. skip the alternate-lookup question
when the command repository has no alternate lookups). Each question is
`multiSelect` where the user picks from candidates; the recommended default is
pre-described in the option text.

- **Alternate lookups** — "Which alternate lookups should get a query `find`?"
  List each candidate as an option. Default: all.
- **`<X>Info` omissions** — "The `<X>Info` read model mirrors these aggregate
  fields: …. Keep all, or omit some?" Offer "Keep all fields (Recommended)" and
  "Omit some — I'll specify"; the user names omissions via the free-text choice.
- **`<X>Filtering` fields** — "`<X>Filtering` will expose: …. Use this set?" Offer
  "Use proposed set (Recommended)" and "Customize — I'll specify".

If the candidate set for a question exceeds four options, present "accept default"
vs "customize" and let the user specify exact values in free text.

If a query part already exists (Step 2), state in the interview preamble that the
existing query part will be **regenerated in place**.

### Step 5 — Delegate the write

Invoke the `model-diagrams:query-part-deriver` agent. Pass, as the prompt:

- Line 1: the absolute `<diagram_file>` path.
- Then a `Decisions:` block stating the three resolved choices — the alternate
  lookups to project, the `<X>Info` fields to omit (or "none"), and the exact
  `<X>Filtering` field set.

The agent re-parses the command part, derives the query part under the
`query-derivation` rules with these decisions applied, removes any existing query
part, and writes the result at the tail of the `classDiagram` block.

### Step 6 — Report

Relay the agent's summary. Do not re-derive or second-guess its output. If the
agent reports an error, surface it verbatim.

## Constraints

- **Domain diagram only.** Never run against `.commands.md` / `.queries.md`.
- **Write immediately after the interview.** No preview-and-confirm step.
- **The command part is read-only.** Only the query classes and their arrows are
  added, replaced, or removed; the `## Invariants` prose is never touched.
- **One invocation = one aggregate's query part.** If the diagram has more than one
  `<<Aggregate Root>>`, ask the user which aggregate to target before proceeding.
