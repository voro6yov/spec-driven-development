---
name: ops-services
description: Authoring and review conventions for ops orchestration/inference diagrams (<stem>.ops.<service>.md) — free-form <<Application>> class, on_<event> handlers, ICan* ports, epoch_token gating.
user-invocable: false
---

# Ops / orchestration application services

**Applies to:** ops diagrams (`<stem>.ops.<service>.md`)

> Ops diagrams are a third application-diagram kind, alongside the single `<stem>.commands.md` and single `<stem>.queries.md`. Each models one event-reacting orchestration/inference service as a free-form `<<Application>>` class that consumes its own aggregate's domain events, calls `<<Service>>` inferrer ports and `<<Interface>>` capability/write-back ports, and gates every skip and every write-back on an `epoch_token`. This theme tells you how to author and review them.

## Conventions

### Ops diagram filename and multiplicity (N-per-aggregate)

- **Rule:** File each ops service in its own sibling named `<stem>.ops.<service-kebab>.md`, where `<service-kebab>` matches the `%% Messaging - <channel>` marker inside it. Unlike commands and queries (exactly one each), ops services are **N-per-aggregate** — one file per orchestration service.
- **Notation:**
  ```
  ruleset.ops.mapping-rules-inference.md
  ruleset.ops.mappings-inference.md
  ```
- **Example:** the `ruleset` aggregate ships two ops files — `ruleset.ops.mapping-rules-inference.md` (class `MappingRulesInference`) and `ruleset.ops.mappings-inference.md` (class `MappingsInference`) — from `ruleset.md`.
- **You may:** author any number of ops files for one aggregate, or none at all; an aggregate with an inference-shaped lifecycle is not obligated to carry an ops diagram.
- **Review:** treat the `<stem>.ops.<service>.md` name and the presence of multiple ops files for one aggregate as canonical — do not flag N-per-aggregate ops files as a CQRS/single-service violation, and do not flag a missing ops file as incomplete.

### Free-form `<<Application>>` orchestration class

- **Rule:** Give the ops class the `<<Application>>` stereotype on the first body line (one stereotype per class), and the same mermaid front-matter as `<X>Commands`/`<X>Queries`: `title:` set to the verbatim class name, `config.class.hideEmptyMembersBox: true`, then `classDiagram`. Name the class for its **domain action** — free-form, with **no** mandated `Commands`/`Queries`/`Ops`/`Service` suffix. The class is bound to exactly one aggregate but never holds the live aggregate. Close the file with a trailing `## Invariants` section keyed `### <Class>` / `#### <Class>.<method>`.
- **Notation:**
  ```mermaid
  ---
  title: MappingRulesInference
  config:
      class:
          hideEmptyMembersBox: true
  ---

  classDiagram
    class MappingRulesInference {
      <<Application>>
      ...
    }
  ```
- **Example:** `class MappingRulesInference { <<Application>> ... }` with `title: MappingRulesInference` — from `ruleset.ops.mapping-rules-inference.md`. Both authored classes (`MappingRulesInference`, `MappingsInference`) end in `Inference`, but that is a chosen domain-action name, not a required suffix.
- **You may:** name the class with any domain-action noun (the observed names happen to end in `Inference`); declare the ops-supporting `<<Service>>` inferrer ports and `<<Interface>>` `ICan*` ports either in the ops file or upstream in the domain file (`ruleset.md` declares them all in the domain file).
- **Review:** treat a suffixless, free-form `<<Application>>` class name as canonical — do not flag the absence of a `Commands`/`Queries`/`Ops`/`Service` suffix, and do not propose renaming it to one.

### Two method families: `on_<event>` handlers (wide envelope) + free-form demand actions (`feedback`)

- **Rule:** Give the ops class two method families, both returning `None` (free-return — ops carry **no** return-the-aggregate invariant). (1) **Event handlers** `on_<event_snake>`, one per consumed domain event, taking the flattened event payload via a **wide shared envelope**: `ruleset_id`, `epoch_token: int`, `evo_version`, `category_code`, `globals: Globals`, then the id-list params `file_ids`, `domain_type_codes`, `mapping_type_codes`, `cache_type_codes` (each `list[str]`); the retry handler adds `error_stages: list[str]`. (2) **Demand-driven action methods** — free-form **singular** verbs keyed by the interior entity id plus a distinctive `feedback: str` param. Handlers call the inferrer's **bulk** methods; demand actions call the **singular** method.
- **Notation:**
  ```
  +on_ruleset_files_added(ruleset_id: str, epoch_token: int, evo_version: str, category_code: str, globals: Globals, file_ids: list[str], domain_type_codes: list[str], mapping_type_codes: list[str], cache_type_codes: list[str]) None
  +on_rules_inference_retried(ruleset_id: str, epoch_token: int, evo_version: str, category_code: str, globals: Globals, file_ids: list[str], domain_type_codes: list[str], mapping_type_codes: list[str], cache_type_codes: list[str], error_stages: list[str]) None
  +infer_rule(ruleset_id: str, mapping_rule_id: str, feedback: str) None
  ```
- **Example:** `+infer_rule(ruleset_id: str, mapping_rule_id: str, feedback: str) None` — from `ruleset.ops.mapping-rules-inference.md`; its sibling `ruleset.ops.mappings-inference.md` carries `+infer_mapping(ruleset_id: str, mapping_id: str, feedback: str) None`. The four `on_*` handlers (`on_ruleset_files_added`, `on_ruleset_file_removed`, `on_ruleset_file_stage_changed`, `on_rules_inference_retried`) all carry the identical wide envelope.
- **You may:** declare any number of `on_<event>` handlers (one per consumed event) and any number of singular `feedback`-bearing demand actions; the demand action's interior-id param is named for the entity it targets (`mapping_rule_id`, `mapping_id`).
- **Review:** treat the wide repeated envelope across handlers, the `None` (free) return on every method, and the singular `feedback`-bearing demand actions as canonical — do not flag the envelope repetition as duplication, do not flag the `None` return as a missing-aggregate-return, and do not flag the `feedback` param (absent from commands/queries) as non-standard. A handler returning the aggregate would be the anomaly, not the `None`.

### Idempotent no-op `<X> | None` return on ops methods

- **Rule:** An ops `<<Application>>` method may declare a return type of `<X> | None`, where the `None` arm signals an **idempotent no-op** (the target no longer exists / was concurrently deleted, so there is nothing to persist and the call returns without error rather than raising not-found).
- **Notation:**
  ```
  +on_<event>(...) <AggregateRoot> | None
  ```
- **Example:** see the idempotent-no-op convention owned by `application-services/` (`model-diagrams:conventions`, "Application-service methods may return `<Aggregate> | None`"), which lists the ops `<stem>.ops.<op-name>.md` diagram as a covered case.
- **You may:** use `<X> | None` on any ops handler/demand method whose missing-target branch is a benign return; the `<X>` arm may be the aggregate root or any return DTO / value object.
- **Review:** this is the **same** idempotent-no-op convention owned by application-services — do not re-document it here and do not flag it. When an ops method returns `<X> | None`, check the three cues that convention defines (the diagram is an ops or commands `<<Application>>` diagram; the return is `<X> | None`; the Flow describes the missing-target branch as a return-without-error / no-op). If they hold, do not flag as "inconsistent optionality", "should raise NotFound", or "missing error handling"; do not propose raising not-found as remediation. A `Queries` method returning `<DTO> | None` is an ordinary nullable lookup, not this convention.

### Dependency vocabulary: `--() : uses` and `--() : raises` only — `ICan*` ports + `<X>Inferrer`, no repository/publisher/manipulates

- **Rule:** Inject every ops collaborator as a private snake_case field drawn `--() <Collaborator> : uses`, and draw each raised exception `--() <Exception> : raises`. Ops diagrams carry **only** `uses` and `raises` edges — **no** `<<Repository>>`, **no** `DomainEventPublisher`, **no** `manipulates`/`returns`/`takes as argument` edges. Use three collaborator kinds: (1) a fallible external-IO **`<<Service>>` `<X>Inferrer` port** returning an `Inferenced*` result-or-error envelope (bulk + singular methods); (2) read-only **`<<Interface>>` `ICanRetrieve<Thing>Info` ports** returning `Info` TypedDicts; (3) a single **`<<Interface>>` `ICanManage<Aggregate>` write-back client** that replaces the `Command<X>Repository`. Field names are role-descriptive (`file_storage`, `ruleset_client`, `mapping_rule_inferrer`), not type-echoing.
- **Notation:**
  ```
  MappingRulesInference --() MappingRuleInferrer : uses
  MappingRulesInference --() ICanRetrieveFilesInfo : uses
  MappingRulesInference --() ICanManageRuleset : uses
  MappingRulesInference --() RulesetNotFound : raises
  MappingRulesInference --() RulesetEpochSuperseded : raises
  ```
- **Example:** `MappingRulesInference` injects six collaborators via `--() : uses` — `mapping_rule_inferrer: MappingRuleInferrer` (`<<Service>>`), the four `ICanRetrieve*Info` `<<Interface>>` ports (`ICanRetrieveFilesInfo`, `ICanRetrieveDomainModelsInfo`, `ICanRetrieveMappingTypesInfo`, `ICanRetrieveCacheTypesInfo`), and `ruleset_client: ICanManageRuleset` — from `ruleset.ops.mapping-rules-inference.md`; `MappingsInference` swaps in `mapping_inferrer: MappingInferrer`.
- **You may:** inject more or fewer ports as the service needs; the `<<Interface>>` ports and the `<<Service>>` inferrer port may be declared upstream in the domain file (`ICanManageRuleset { <<Interface>> +find_ruleset(...) +add_mapping_rules(...) ... }` lives in `ruleset.md`).
- **Review:** treat the `uses`+`raises`-only edge set, the `ICanRetrieve*`/`ICanManage*` `<<Interface>>` ports, and the `<X>Inferrer` `<<Service>>` port replacing the repository as canonical — do not flag the absence of a `Command<X>Repository`, a `DomainEventPublisher`, or a `manipulates` edge; do not propose adding a repository injection. The `<<Interface>>` stereotype on a capability port is canonical, not a non-standard interface marker.

### `epoch_token` optimistic-concurrency gating

- **Rule:** Thread the aggregate's monotonic `epoch_token: int` through every ops handler envelope and use it as the optimistic-concurrency gate: a `Pre-check` skips an event whose `epoch_token` is superseded (plus a same-stage idempotency flag), and **every** write-back through the client is epoch-token-gated. Forward `evo_version` and `globals: Globals` as standing envelope params (globals is passed into the inferrer), and feed each id-list param to its dedicated read port.
- **Notation:**
  ```
  +on_ruleset_files_added(ruleset_id: str, epoch_token: int, ...) None
  MappingRulesInference --() RulesetEpochSuperseded : raises
  ```
- **Example:** `epoch_token: int` appears in every `on_*` handler envelope, and the demand path surfaces supersession as `--() RulesetEpochSuperseded : raises` — from `ruleset.ops.mapping-rules-inference.md`; the aggregate `Ruleset` carries `-epoch_token: int` and `Ruleset --() RulesetEpochSuperseded : raises` in `ruleset.md`.
- **You may:** omit the epoch token only when the aggregate has no out-of-band write-back concurrency to gate; when present it is incremented by every (re)trigger and checked by every write-back.
- **Review:** treat the epoch-token envelope param and the `<Aggregate>EpochSuperseded` raise as canonical — do not flag the repeated `epoch_token` across handlers as redundant, and do not propose a stored-version-counter or last-writer-wins alternative.

### Per-method fork: handlers return-early on guards; demand actions raise

- **Rule:** Specify the ops `## Invariants` Flow with a **per-method fork**. **Event handlers** are at-least-once idempotent and **return early on guards** — a `Pre-check (skip superseded/duplicate work)` gate on `epoch_token` + the per-stage inferred flag, an `Empty-PRE guard` (no PRE-stage files), and an `Unexpected-failure guard` that records a *retryable* `add_errors` rather than throwing — never raising on the normal path. **Demand action methods** are synchronous and **raise typed exceptions** to their caller (e.g. `RulesetNotFound`, `RulesetNotCompleted`, `RulesetEpochSuperseded`, and the inference-failed exception); they deliberately do **not** persist the failure (persisting would flip a completed aggregate to failed). The retry handler is **selective on its own stage** — it acts only when its stage literal is present in `error_stages`.
- **Notation:**
  ```markdown
  #### <Class>.on_<event>
  **Flow:**
  1. **Pre-check (skip superseded / duplicate work).** ... Return early when ...
  ...
  7. **Unexpected-failure guard.** ... record a retryable failure via add_errors ...

  #### <Class>.<demand_action>
  **Flow:**
  1. ... If it returns None, raise <Aggregate>NotFound.
  ...
  5. If has_errors is true, ... raise <Inference>Failed ...
  ```
- **Example:** in `ruleset.ops.mapping-rules-inference.md`, `MappingRulesInference.on_ruleset_files_added` returns early on the `Pre-check`/`Empty-PRE` guards and records a retryable `ruleset_client.add_errors([...retryable: true...])` on unexpected failure, while `MappingRulesInference.infer_rule` raises `RulesetNotFound`, `RulesetNotCompleted`, and `MappingRuleInferenceFailed` to its synchronous caller; `on_rules_inference_retried` acts only when `"mapping-rules"` is present in `error_stages`.
- **You may:** name the inference-failed exception per stage (`MappingRuleInferenceFailed` vs `MappingInferenceFailed`); the handler guards (`Pre-check`/`Empty-PRE`/`Unexpected-failure`) are shared prose across an aggregate's ops files.
- **Review:** treat the handler-returns-early-vs-demand-action-raises fork as canonical and load-bearing — do not flag a handler for "swallowing errors" (the unexpected-failure guard recording a retryable `add_errors` is the pattern), do not flag a demand action for raising instead of returning a no-op, and do not flag the retry handler's early exit when its stage is absent from `error_stages`.

### Inbound messaging: own-aggregate `--() : handles` lollipop under `%% Messaging`

- **Rule:** Wire inbound messaging under a `%% Messaging - <service-channel>` marker with `--() <Event> : handles (<SourceAggregate>, on_<event>)` edges binding each consumed domain event to its `on_<event>` handler. On ops the source bracket names the **OWN aggregate** whose events are fed back via messaging (not an external context), and the handles edge is a **lollipop `--()`**. This closes an event → inference → write-back loop: the ops class consumes the events the root `emits` and calls back into the aggregate via the `ICanManage<X>` client.
- **Notation:**
  ```
  %% Messaging - mapping-rules-inference
  MappingRulesInference --() RulesetFilesAdded : handles (Ruleset, on_ruleset_files_added)
  MappingRulesInference --() RulesInferenceRetried : handles (Ruleset, on_rules_inference_retried)
  ```
- **Example:** `--() RulesetFilesAdded : handles (Ruleset, on_ruleset_files_added)` under `%% Messaging - mapping-rules-inference` — from `ruleset.ops.mapping-rules-inference.md`; the same four `handles` edges (`RulesetFilesAdded`, `RulesetFileRemoved`, `RulesetFileStageChanged`, `RulesInferenceRetried`) appear in `ruleset.ops.mappings-inference.md`. The events being handled are the same ones the root emits in `ruleset.md` (`Ruleset --> RulesetFilesAdded : emits (add_files, add_file)`).
- **You may:** use the lollipop `--() : handles` form on ops (note `<X>Commands` diagrams may draw the conceptually-similar edge as an association `-->`); the `%% Messaging - <channel>` marker segment matches the ops file's `<service-kebab>` segment.
- **Review:** treat the own-aggregate `handles` semantics and the lollipop `--() : handles` arrow style as canonical on ops diagrams — do not flag an ops class for handling its own aggregate's events (the feedback loop is the pattern), and do not flag the lollipop-vs-association arrow choice as inconsistent with the commands family. Ops diagrams carry **only** the `%% Messaging` block and **no** `%% internal` surface marker (that partition is a commands/queries idiom) — do not flag its absence.

## Pitfalls

- **Do not inject a repository or publisher.** Ops replace `Command<X>Repository` with the `ICanManage<Aggregate>` write-back client and emit nothing directly — drawing a `Command<X>Repository` `--() : uses` or a `DomainEventPublisher` injection on an ops diagram is wrong.
- **Do not draw `manipulates`/`returns`/`takes as argument` edges.** Ops diagrams carry only `--() : uses` and `--() : raises`. Those other role labels belong to commands/queries diagrams.
- **Do not return the aggregate from handlers.** Ops methods are free-return (`None` or `<X> | None`); the return-the-aggregate invariant is a commands idiom, not an ops one.
- **Do not hand the `Inferenced*` envelope to the aggregate.** The result-or-error envelope (`InferencedMappingRules`/`InferencedMappings`, gated on `has_errors`) is **unwrapped in the ops layer**; the aggregate exposes only granular `add_*`/`update_*` data-level entry points. Routing `has_errors` is application-layer dispatch, not an aggregate invariant.
- **Do not make handlers raise on the normal path, and do not make demand actions silently no-op a missing target.** A handler that raises a typed exception instead of returning early on its guards, or a demand action that returns silently instead of raising not-found / inference-failed, inverts the load-bearing per-method fork.
- **Do not omit the `epoch_token` from a handler envelope** when the aggregate uses optimistic concurrency — the skip-superseded gate and every write-back depend on it being threaded through.
- **Do not give the ops class a `Commands`/`Queries`/`Ops`/`Service` suffix.** It is a free-form domain-action name; a forced suffix is non-conforming.
- **Avoid commented-out (`%%`) port declarations with live references into them.** If an ops/domain diagram comments out an `ICan*` port or Info type, the active diagram must not still reference it (a `from_info(... : <CommentedType>)` or `--() <CommentedType>` lollipop into a `%%` block is a dangling reference to resolve before enabling).
