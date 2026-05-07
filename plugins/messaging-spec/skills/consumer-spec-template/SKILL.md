---
name: consumer-spec-template
description: Reference template for the Consumer Basics table (Table 1) of a messaging consumer input spec. Load when authoring or reviewing the input spec for a messaging consumer — covers the three required fields of Table 1, casing/format rules, queue-name derivation conventions, and worked examples.
user-invocable: false
disable-model-invocation: false
---

# Consumer Spec Template — Consumer Basics

## Purpose

Defines the canonical shape of **Table 1: Consumer Basics** of a messaging consumer input spec. Every consumer spec consists of exactly this one table — no further sections. Table 1 anchors the consumer's identity (which submodule under `messaging/` it corresponds to) and the names of the two queues it binds to.

A consumer in this codebase is a single submodule under `messaging/<consumer_name>/` that owns a dispatcher factory (`make_<consumer_name>_dispatcher`), one or more handlers, and the queue constants it consumes from. See the `messaging-module-structure` skill for the surrounding layout.

## Table 1 layout

| Field | Value |
| --- | --- |
| **Consumer name** |  |
| **Events queue name** |  |
| **Commands queue name** |  |

## Fields

### Consumer name

- **Format:** `snake_case`
- **Cardinality:** Names a **processing concern**, not an event source. Always the directory name of the consumer's submodule under `messaging/` (e.g. `messaging/profile_reconciliation/` ⇒ Consumer name `profile_reconciliation`).
- **Examples:** `profile_reconciliation`, `document_ops`, `subject_extraction`
- **Counter-examples:** `ProfileReconciliation` (wrong case), `profile-reconciliation` (kebab-case — reserved for queue names), `files_events` (named after source, not concern), `documents_consumer` (redundant `_consumer` suffix), `profile_created_handler` (named after a single handler, not the concern)

### Events queue name

- **Format:** `kebab-case`
- **Derivation (strict):** `<svc>-<consumer-as-kebab>-events`
    - `<svc>` is the service prefix derived from the project's Python package name converted to kebab-case (e.g. project `clients_service` ⇒ `clients-service`; project `clients` ⇒ `clients`; project `inventory_api` ⇒ `inventory-api`). When the project name has a generic suffix like `_service`, callers commonly drop it for brevity (e.g. `clients_service` ⇒ `clients`); document the chosen short form in the project's constants and reuse it across all consumer specs.
    - `<consumer-as-kebab>` is the Consumer name with every `_` replaced by `-` (e.g. `profile_reconciliation` ⇒ `profile-reconciliation`).
    - Suffix is the literal `events`.
- **Required.** Always present. If the consumer does not subscribe to an events queue, fill the cell with an em dash `—` (see *Unused queues* below).
- **Examples:** `clients-profile-reconciliation-events`, `clients-document-ops-events`, `inventory-subject-extraction-events`
- **Counter-examples:** `clients-profile-reconciliation` (missing `-events` suffix), `Clients-Profile-Reconciliation-Events` (must be lowercase), `clients_profile_reconciliation_events` (must be kebab-case, not snake), `profile-reconciliation-events` (missing service prefix)

### Commands queue name

- **Format:** `kebab-case`
- **Derivation (strict):** `<svc>-<consumer-as-kebab>-commands`
    - `<svc>` and `<consumer-as-kebab>` are derived as for the Events queue name; the only difference is the literal suffix `commands`.
- **Required.** Always present. If the consumer does not subscribe to a commands queue, fill the cell with an em dash `—` (see *Unused queues* below).
- **Examples:** `clients-profile-reconciliation-commands`, `clients-document-ops-commands`, `inventory-subject-extraction-commands`
- **Counter-examples:** `clients-profile-reconciliation-cmds` (must be the literal `commands`), `clients-profile-reconciliation-command` (singular — must be `commands` plural), `commands-clients-profile-reconciliation` (suffix in wrong position)

### Unused queues

Both rows are always present in Table 1. When a consumer does not bind to one of the two queues (e.g. an events-only consumer with no commands queue), fill the unused cell with a single em dash `—`. Never delete the row; never leave the cell empty; never write `N/A` or `none`. The em dash signals "intentionally absent" and keeps every Consumer Basics table the same shape across the codebase.

## Derivation summary

Given a Consumer name and the project's service prefix `<svc>`, the rest of Table 1 is fully determined:

```
Consumer name       = <snake_case processing concern>
Events queue name   = "<svc>-" + replace(Consumer name, "_", "-") + "-events"     (or "—" if unused)
Commands queue name = "<svc>-" + replace(Consumer name, "_", "-") + "-commands"   (or "—" if unused)
```

`<svc>` is project-wide, not per-consumer: every consumer spec in a given project uses the same prefix.

## Worked examples

**Example A — `profile_reconciliation` in the `clients` service (both queues used)**

```markdown
### Table 1: Consumer Basics

| Field | Value |
| --- | --- |
| **Consumer name** | profile_reconciliation |
| **Events queue name** | clients-profile-reconciliation-events |
| **Commands queue name** | clients-profile-reconciliation-commands |
```

**Example B — `subject_extraction` in the `inventory_api` service (events-only)**

```markdown
### Table 1: Consumer Basics

| Field | Value |
| --- | --- |
| **Consumer name** | subject_extraction |
| **Events queue name** | inventory-api-subject-extraction-events |
| **Commands queue name** | — |
```

**Example C — `document_ops` in the `clients` service (commands-only)**

```markdown
### Table 1: Consumer Basics

| Field | Value |
| --- | --- |
| **Consumer name** | document_ops |
| **Events queue name** | — |
| **Commands queue name** | clients-document-ops-commands |
```

## Validation checklist

### Table 1

- [ ] Consumer name is `snake_case` and names a processing concern (not an event source, not a single handler, no `_consumer` suffix)
- [ ] Consumer name matches the submodule directory under `messaging/` exactly
- [ ] Events queue name equals `<svc>-<consumer-as-kebab>-events` exactly, or `—` when unused
- [ ] Commands queue name equals `<svc>-<consumer-as-kebab>-commands` exactly, or `—` when unused
- [ ] Both rows are present; unused cells use a single em dash `—`, never empty, never `N/A`
- [ ] At least one of the two queue cells is a real queue name (not both `—`)
- [ ] `<svc>` prefix is identical across every consumer spec in the project
