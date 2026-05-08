---
name: messaging-handler-fixtures
description: Messaging Handler Fixtures pattern for message-handler integration testing. Use when authoring pytest fixtures that expose injected event/command handlers and optional helper factories for constructing event envelopes and command messages.
user-invocable: false
disable-model-invocation: false
---

# Messaging Handler Fixtures

## Purpose

- Expose `@inject`-decorated event and command handlers as pytest fixtures with the DI container wired in.
- Optionally provide helper factories for constructing `DomainEventEnvelope` and `CommandMessage` objects.
- Document where each fixture lives so downstream test code resolves them correctly.

For the test scenarios that consume these fixtures, see `messaging-spec:messaging-handler-test-rules`.

---

## Injected Handler Fixture Pattern

Handlers use `@inject` decorator, so fixtures must wire the container:

```python
# root conftest.py

@pytest.fixture
def file_classification_succeeded_handler(containers):
    """Injected event handler with wired dependencies."""
    from my_project.messaging.document_ops.handlers import (
        file_classification_succeeded_handler as handler,
    )
    return handler

@pytest.fixture
def start_label_processing_handler(containers):
    """Injected command handler with wired dependencies."""
    from my_project.messaging.label_processing.handlers import (
        start_label_processing_command_handler as handler,
    )
    return handler
```

---

## Helper Fixtures (Optional)

If you frequently construct similar envelopes/messages, create helpers:

```python
# root conftest.py

@pytest.fixture
def make_event_envelope():
    """Factory for creating event envelopes."""
    def _make(event):
        return DomainEventEnvelope(
            event=event,
            metadata=EventMetadata(
                event_id=str(uuid4()),
                timestamp=datetime.now(UTC),
            ),
        )
    return _make

@pytest.fixture
def make_command_message():
    """Factory for creating command messages."""
    def _make(command, reply_to="test-reply-channel"):
        return CommandMessage(
            command=command,
            message=Message(
                headers={CommandMessageHeaders.REPLY_TO: reply_to},
                payload=JsonMapper().serialize(command),
            ),
        )
    return _make
```

---

## Fixture Location Reference

Messaging-specific fixtures live in the root `conftest.py`. Other fixtures referenced by handler tests are owned by upstream tiers and are not redefined here.

| Fixture Type | Location | Scope | Owner |
| --- | --- | --- | --- |
| `{handler}` | root `conftest.py` | function | this skill |
| `make_event_envelope` | root `conftest.py` | function | this skill |
| `make_command_message` | root `conftest.py` | function | this skill |
| `{aggregate}_n` | root `conftest.py` | function | `domain-spec:aggregate-fixtures` |
| `add_{aggregates}` | integration `conftest.py` | function | `persistence-spec:persistence-fixtures` |
| `unit_of_work` | integration `conftest.py` | function | `persistence-spec:unit-of-work` |
| `domain_event_publisher_mock` | integration `conftest.py` | function | `application-spec:fake-override-fixtures` |
