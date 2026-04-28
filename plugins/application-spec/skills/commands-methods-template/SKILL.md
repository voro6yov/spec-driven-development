---
name: commands-methods-template
description: Commands Methods Template pattern for application service command specs. Use when filling the Method Specifications section of a `<AggregateRoot>Commands` spec.
user-invocable: false
disable-model-invocation: false
---

# Commands Methods Template

Documents one entry per public method on a `<AggregateRoot>Commands` application service. Each method has the same three subsections: **Purpose**, **Method Flow**, **Postconditions**. Dependencies, preconditions, error handling, and implementation notes are either captured at the service level or expressed directly inside the flow.

**Pattern Reference**: `application-spec:commands`

---

## Canonical Method Shape

The dominant shape is `load → mutate → save → publish → return`. Use it as the default and only deviate where the method genuinely differs (e.g. factory creation, collaborator call). Express deviations as different flow steps, not as a different template.

```
### Method: `method_name(param1: type, param2: type) -> ReturnType`

**Purpose**: [One-liner describing what this method does]

**Method Flow**:

1. Call `command_repository.<lookup_method>(<params>)` to retrieve the aggregate
2. Call one or more aggregate methods to mutate state
   (e.g. `<aggregate>.<reset_method>()` then `<aggregate>.<domain_method>(<params>)`)
3. Call `command_repository.save(<aggregate>)` to persist changes
4. Extract events from the aggregate and publish via `event_publisher`
5. Return the updated `<Aggregate>`

**Postconditions**:

- [State change on the aggregate, e.g. attribute overwritten / entity appended / entity removed]
- `updated_at` set to current timestamp
- [Domain event published, if relevant to the postcondition]
```

### Inline notes inside flow steps

Use indented `**Note**:` sub-bullets under a flow step to capture short-circuits, branches, or behaviors that would otherwise need their own section. Keep them inside the step they qualify — do not move them to a separate "Implementation Notes" section.

```
2. Call `<service>.detect(<aggregate>)` to trigger reconciliation
   - **Note**: `detect()` may short-circuit by calling `<aggregate>.add_errors(errors)` if errors are detected. In that case the downstream mutation is skipped and the aggregate transitions to `not_reconciled`.
   - **Note**: When `<flag>` is present, `detect()` follows the terminal path — status is resolved immediately and no downstream commands are emitted.
```

---

## Deviation: Factory / Create

Used when no aggregate is loaded (creation path). Steps 1-3 differ; the tail of the flow is unchanged. The existence check is optional — include it only when natural-key uniqueness is enforced at the application layer.

```
**Method Flow**:

1. (Optional) Call `command_repository.<existence_check>(<natural_key>, tenant_id)` to check for conflicts
2. (Optional) If a matching aggregate exists, raise `<Aggregate>AlreadyExistsError`
3. Call `<Aggregate>.new(<params>)` to construct a new aggregate
4. Call `command_repository.save(<aggregate>)` to persist the new aggregate
5. Extract events from the aggregate and publish via `event_publisher`
6. Return the created `<Aggregate>`
```

---

## Deviation: Collaborator Call

Used when the method calls an injected collaborator between load and save. Covers both:

- **External interfaces** — Protocol-typed adapters for external systems (conveyor, ERP, downstream service). The interface returns a result that is then passed to an aggregate method.
- **Domain services** — concrete services in the domain layer (e.g. detection, reconciliation orchestration). The service typically takes the aggregate and mutates it in place; no separate aggregate-mutate step is needed.

```
**Method Flow**:

1. Call `command_repository.<lookup_method>(<params>)` to retrieve the aggregate
2. Call `<collaborator>.<operation>(<params>)`
   - For an **external interface**: capture the result and pass it to the next aggregate call
   - For a **domain service**: the service mutates the aggregate in place; skip the explicit mutate step
3. (External-interface case only) Call `<aggregate>.<domain_method>(<result>)` on the aggregate
4. Call `command_repository.save(<aggregate>)` to persist changes
5. Extract events from the aggregate and publish via `event_publisher`
6. Return the updated `<Aggregate>`
```

---

## Worked examples

The three examples below cover the canonical shape, the factory deviation, and a collaborator-call deviation that also exercises multi-step mutation and inline flow notes.

### Example 1 — Canonical shape (`update_details` on `ProfileTypeCommands`)

```
### Method: `update_details(id: str, tenant_id: str, name: str, description: str, subject_kind: str) -> ProfileType`

**Purpose**: Updates the core identity attributes (name, description, subject kind) of an existing ProfileType.

**Method Flow**:

1. If `subject_kind` is not provided, default to `"CustomEntity"`
2. Call `command_repository.profile_type_of_id(id, tenant_id)` to retrieve the aggregate
3. Call `profile_type.update_details(name, description, subject_kind)` on the aggregate
4. Call `command_repository.save(profile_type)` to persist changes
5. Extract events from the aggregate and publish via `event_publisher`
6. Return the updated `ProfileType`

**Postconditions**:

- `profile_type_details` overwritten with new `ProfileTypeDetails`
- `updated_at` set to current timestamp
```

### Example 2 — Factory deviation (`create` on `ProfileTypeCommands`)

```
### Method: `create(tenant_id: str, name: str, description: str, subject_kind: str) -> ProfileType`

**Purpose**: Creates a new ProfileType aggregate with the given details.

**Method Flow**:

1. If `subject_kind` is not provided, default to `"CustomEntity"`
2. Call `command_repository.profile_type_of_name(name, tenant_id)` to check whether a ProfileType with the same name already exists
3. If a matching ProfileType exists, raise `ProfileTypeAlreadyExistsError`
4. Call `ProfileType.new(tenant_id, name, description, subject_kind)` to construct a new aggregate
5. Call `command_repository.save(profile_type)` to persist the new aggregate
6. Extract events from the aggregate and publish via `event_publisher`
7. Return the created `ProfileType`

**Postconditions**:

- A new `ProfileType` aggregate exists with generated `id` and empty `fields`, `document_types`, `reconciliation_rules`, `validation_rules`
- `created_at` and `updated_at` set to current timestamp
- No other `ProfileType` with the same `name` exists within the same `tenant_id`
```

### Example 3 — Collaborator (domain service) + multi-step mutation + inline notes (`on_profile_submitted` on `ProfileCommands`)

```
### Method: `on_profile_submitted(id: str, tenant_id: str) -> Profile`

**Purpose**: Event handler that triggers subject detection and reconciliation when a user explicitly submits a profile.

**Method Flow**:

1. Call `command_repository.profile_of_id(id, tenant_id)` to retrieve the aggregate
2. Call `subject_detection.detect(profile)` to trigger reconciliation
   - **Note**: `detect()` may short-circuit by calling `Profile.add_errors(errors)` if identification errors are detected. In that case entity addition and `Profile.reconcile()` are skipped — the Profile transitions to `not_reconciled` with error details.
   - **Note**: When `profile_type` is present, `detect()` follows the Custom Entity path — reconciliation is **terminal** (status resolves to `reconciled` or `not_reconciled` immediately, no `SaveIndividual`/`SaveLegalEntity` commands are emitted, no async reply handlers are needed).
3. Call `command_repository.save(profile)` to persist changes
4. Extract events from the aggregate and publish via `event_publisher`
5. Return the updated `Profile`

**Postconditions**:

- Reconciliation is triggered (or skipped if identification errors are detected)
- Profile state is updated based on reconciliation outcome
- **Custom Entity path** is terminal — status resolves immediately to `reconciled` or `not_reconciled`, no downstream commands emitted
- **Individual/LegalEntity path** keeps status `new` while async `SaveIndividual`/`SaveLegalEntity` commands are pending; status transitions happen in reply handlers
```

The third example is also a **multi-aggregate-call shape** in spirit: `subject_detection.detect(profile)` mutates the aggregate in place, so step 2 substitutes for an explicit `profile.<method>()` mutate step. When a method needs both — e.g. `profile.clear()` followed by `profile.add_subject(...)` — list each call as its own line under the same step or as adjacent numbered steps.
