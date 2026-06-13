---
name: patterns
description: "Umbrella catalog of all messaging-spec pattern references. Each pattern lives in a sibling folder of this file — `<pattern-name>/` containing `index.md` (the pattern doc). Load to resolve pattern names to their reference docs by path instead of per-pattern skill invocations."
---

# Messaging-spec pattern catalog (umbrella)

This skill is a path-resolution anchor: it registers **one** catalog entry for all messaging-spec
pattern references. The pattern docs themselves are **supporting files** in folders next to this
`SKILL.md` and are never auto-loaded — consumers Read them on demand.

## Resolution rule

Every pattern named `<pattern-name>` resolves to the **folder** `<pattern-name>/` sibling to this
file:

- the pattern document is always `<pattern-name>/index.md`;
- companions, when present, sit in the same folder. Relative links inside `index.md` resolve
  within that folder. (No messaging-spec pattern currently ships a companion.)

A pattern name that has no matching folder is an **error** — report it loudly; never skip it
silently.

## Catalog

| Pattern | Folder | Companions |
|---|---|---|
| command-handlers | [command-handlers/](command-handlers/) | — |
| consumer-spec-template | [consumer-spec-template/](consumer-spec-template/) | — |
| dispatcher-cli-command | [dispatcher-cli-command/](dispatcher-cli-command/) | — |
| dispatcher-container-registration | [dispatcher-container-registration/](dispatcher-container-registration/) | — |
| dispatcher-runner-function | [dispatcher-runner-function/](dispatcher-runner-function/) | — |
| domain-event-dispatchers | [domain-event-dispatchers/](domain-event-dispatchers/) | — |
| domain-event-handlers | [domain-event-handlers/](domain-event-handlers/) | — |
| event-fields-template | [event-fields-template/](event-fields-template/) | — |
| event-tables-template | [event-tables-template/](event-tables-template/) | — |
| message-events-external | [message-events-external/](message-events-external/) | — |
| messaging-handler-fixtures | [messaging-handler-fixtures/](messaging-handler-fixtures/) | — |
| messaging-handler-test-rules | [messaging-handler-test-rules/](messaging-handler-test-rules/) | — |
| messaging-module-structure | [messaging-module-structure/](messaging-module-structure/) | — |
| multi-aggregate-domain-event-dispatchers | [multi-aggregate-domain-event-dispatchers/](multi-aggregate-domain-event-dispatchers/) | — |
| updates-report-template | [updates-report-template/](updates-report-template/) | — |
