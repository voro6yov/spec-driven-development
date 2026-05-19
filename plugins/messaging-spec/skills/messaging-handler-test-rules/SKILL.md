---
name: messaging-handler-test-rules
description: Messaging Handler Test Rules pattern for message-handler integration testing. Use when writing or reviewing tests for event handlers and command handlers.
user-invocable: false
disable-model-invocation: false
---

# Messaging Handler Test Rules

## Purpose

Define testing patterns for **message handlers** (event handlers and command handlers). Handlers are thin adapter layers that route messages to application services — tests verify the full integration flow through handler → application service → persistence → events (and replies, for command handlers).

For the fixture definitions referenced throughout this skill, see `messaging-spec:messaging-handler-fixtures`.

---

## Core Principles

<aside>
📋

**Rules at a Glance**

- **Construct Events/Commands in Test** — Build `DomainEventEnvelope` / `CommandMessage` directly in test body (GIVEN phase)
- **No Mocking Application Layer** — Test full integration through handler → service → persistence → events
- **Use `add_*` Fixtures for Preconditions** — When handler needs existing aggregates in DB
- **Verify Like Application Service** — Assert state + persistence + events (command handlers also verify replies)
</aside>

---

## Handler Types

| Handler Type | Input | Output | Error Handling |
| --- | --- | --- | --- |
| **Event Handler** | `DomainEventEnvelope[EventType]` | `None` | Log + re-raise |
| **Command Handler** | `CommandMessage[CommandType]` | `List[CommandHandlerReplyBuilder]` | Construct failure reply |

---

## Event Handler Tests

### Pattern Overview

| What I'm Testing | Pattern | Fixtures Needed | Verify |
| --- | --- | --- | --- |
| Handler success | Construct envelope → call | `{aggregate}_n`, `add_{aggregates}`, `unit_of_work`, `domain_event_publisher_mock`, `{handler}` | State + Persistence + Events |
| Handler creates new aggregate | Construct envelope → call | `unit_of_work`, `domain_event_publisher_mock`, `{handler}` | Aggregate created + Persistence + Events |
| Handler idempotency | Construct envelope → call twice | `{aggregate}_n`, `add_{aggregates}`, `unit_of_work`, `domain_event_publisher_mock`, `{handler}` | No duplicate side effects |
| Invalid state error | Construct envelope → call with wrong-state aggregate | `{aggregate}_{wrong_state}`, `add_{aggregates}`, `{handler}` | Domain exception raised |

### Example: Event Handler Success

```python
def test_file_classification_succeeded_handler__creates_document(
    make_event_envelope,
    file_classification_succeeded_handler,  # injected handler
    unit_of_work,
    domain_event_publisher_mock,
):
    # GIVEN - construct event via the make_event_envelope helper
    envelope = make_event_envelope(
        FileClassificationSucceeded(
            file_id="file-123",
            tenant_id="tenant-abc",
            document_type="invoice",
        ),
    )

    # WHEN
    file_classification_succeeded_handler(envelope)

    # THEN - verify persistence
    repo = unit_of_work.documents
    document = repo.of_file_id(file_id="file-123", tenant_id="tenant-abc")
    assert document is not None
    assert document.document_type == "invoice"

    # THEN - verify events published
    assert domain_event_publisher_mock.publish.call_count == 1
    event = domain_event_publisher_mock.publish.call_args[0][0]
    assert isinstance(event, DocumentCreated)
```

### Example: Event Handler with Precondition

```python
def test_files_status_updated_handler__updates_profile(
    make_event_envelope,
    files_status_updated_handler,
    profile_2,
    add_profiles,
    unit_of_work,
    domain_event_publisher_mock,
):
    # GIVEN - construct event with matching profile ID off the populated _2 fixture
    envelope = make_event_envelope(
        FilesStatusUpdated(
            profile_id=profile_2.id,
            tenant_id=profile_2.tenant_id,
            files_status="classified",
        ),
    )

    # WHEN
    files_status_updated_handler(envelope)

    # THEN - verify state updated
    repo = unit_of_work.profiles
    updated = repo.of_id(profile_2.id, profile_2.tenant_id)
    assert updated.files_status == "classified"
```

The envelope is always constructed via the `make_event_envelope` helper fixture from `messaging-spec:messaging-handler-fixtures` — never inline `DomainEventEnvelope(...)`. The helper synthesizes a real `Message` payload, an `event_id` (UUID), and sensible defaults for `aggregate_type` / `aggregate_id`; tests that need to pin a specific aggregate identity pass it explicitly via the keyword-only kwargs.

---

## Command Handler Tests

### Pattern Overview

| What I'm Testing | Pattern | Fixtures Needed | Verify |
| --- | --- | --- | --- |
| Handler success | Construct command message → call | `{aggregate}_n`, `add_{aggregates}`, `unit_of_work`, `domain_event_publisher_mock`, `{handler}` | State + Persistence + Events + Success reply |
| Handler failure (business logic) | Construct → call (service returns failure) | Same as success | Failure reply with correct fields |
| Handler failure (exception) | Construct invalid → call | Depends on scenario | Failure reply constructed from exception |
| Reply channel routing | Construct with REPLY_TO header → call | Same as success | Reply sent to correct channel from headers |

### Example: Command Handler Success

```python
def test_start_label_processing_handler__success(
    unit_of_work,
    domain_event_publisher_mock,
    conveyor_1,
    add_conveyors,
    start_label_processing_handler,
):
    # GIVEN - construct command message directly
    command_message = CommandMessage(
        command=StartLabelProcessing(
            conveyor_id=conveyor_1.id,
            tenant_id=conveyor_1.tenant_id,
        ),
        message=Message(
            headers={CommandMessageHeaders.REPLY_TO: "reply-channel"},
            payload=b"...",
        ),
    )
    
    # WHEN
    result = start_label_processing_handler(command_message)
    
    # THEN - verify success reply
    assert len(result) == 1
    reply_builder = result[0]
    assert reply_builder.is_success
    
    # THEN - verify reply payload
    reply_message = reply_builder.message
    reply_payload = JsonMapper().deserialize(reply_message.payload)
    assert reply_payload["tire_id"] is not None
    
    # THEN - verify persistence
    repo = unit_of_work.conveyors
    updated = repo.of_id(conveyor_1.id, conveyor_1.tenant_id)
    assert updated.status == "processing"
```

### Example: Command Handler Failure Reply

```python
def test_start_label_processing_handler__conveyor_not_found__returns_failure(
    unit_of_work,
    start_label_processing_handler,
):
    # GIVEN - construct command for non-existent conveyor (NO add_conveyors)
    command_message = CommandMessage(
        command=StartLabelProcessing(
            conveyor_id="non-existent",
            tenant_id="tenant-abc",
        ),
        message=Message(
            headers={CommandMessageHeaders.REPLY_TO: "reply-channel"},
            payload=b"...",
        ),
    )
    
    # WHEN
    result = start_label_processing_handler(command_message)
    
    # THEN - verify failure reply
    assert len(result) == 1
    reply_builder = result[0]
    assert not reply_builder.is_success
    
    # THEN - verify failure payload
    reply_message = reply_builder.message
    reply_payload = JsonMapper().deserialize(reply_message.payload)
    assert "not found" in reply_payload["error_message"].lower()
```

---

## Naming Conventions

| Element | Pattern | Example |
| --- | --- | --- |
| Test name | `test_{handler_name}__{scenario}__{outcome}` | `test_file_classification_succeeded_handler__creates_document` |
| Handler fixture | `{event_or_command_name}_handler` | `file_classification_succeeded_handler` |
| Test file | `test_{consumer_name}_handlers.py` | `test_document_ops_handlers.py` |

---

## Common Violations to Avoid

| Violation | Impact | Fix |
| --- | --- | --- |
| Mocking application layer | Doesn't test real integration | Test full flow through service |
| Using fixtures for events/commands | Hides test intent | Construct in test body (GIVEN) |
| Not verifying persistence | May miss save failures | Reload from DB and assert |
| Not verifying events | May miss event publishing | Assert on `domain_event_publisher_mock` |
| Not verifying reply (commands) | May return wrong reply type | Assert success/failure + payload fields |
| Missing REPLY_TO header | Command handler may fail | Always include in command message |
