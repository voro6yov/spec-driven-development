---
name: profiles
description: Optional starter ontology-spec templates the new-wiki interview offers as Stage-1 defaults — pre-built blueprints (the prism's reuse-of-categories) for common wiki shapes. The user picks one and refines it against their samples, or starts blank. Reference only.
user-invocable: false
disable-model-invocation: true
---

# Starter profiles

**Type:** Reference (interview defaults).

A profile is a ready-made `ontology-spec` (see the `ontology-spec` skill) for a common wiki
shape — the prism's [[ontological-blueprint|blueprint/template]] idea: **reuse of
tried-and-tested representations** instead of deriving every ontology from a blank page.

## How the interview uses them

At Stage 1 of `prism-interview`, after seeing the user's sample inputs, **offer a matching
profile as a starting point** — not as the answer. The user picks one or starts blank; either
way the rest of the interview **refines it against their actual samples**. The minimal-ontology
rule still governs: drop any profile kind/relationship the samples don't justify, add only what
they force. A profile is a head start, never a straitjacket ([[evolving-order]]).

## Catalog

| Profile | File | For |
|---|---|---|
| Concept graph | [concept-graph/](concept-graph/index.md) | a general wiki of ideas + how they relate (the default) |
| Architect project | [architect-project/](architect-project/index.md) | a living design record — decisions, components, risks |

Each file is a one-paragraph "when to use" + a complete `ontology-spec` YAML the interview
seeds from. Placeholders (`<project>`, `<domain>`, `<topic>`) are filled during the interview.

## Adding a profile

Add `<name>/index.md` (blurb + spec) and a catalog row. Keep profiles **small** — a profile
that ships 10 kinds teaches over-engineering.
