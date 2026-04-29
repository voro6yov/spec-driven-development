---
name: fake-override-fixtures
description: Fake Override Fixtures pattern for application service testing. Use when replacing external dependencies with fake implementations and overriding DI container providers in pytest.
user-invocable: false
disable-model-invocation: false
---

# Fake Override Fixtures

## Purpose

- Replace external dependencies with fake implementations for testing.
- Enable controlled test environments without real external services.
- Provide call tracking for behavior verification.

## Structure

Two-tier fixture pattern for efficiency:

1. **Session-scoped fixture**: Creates fake, overrides container, yields for session.
2. **Function-scoped fixture**: Resets fake state between tests.

## Behavior Checklist

- Session fixture creates fake instance once per test session.
- Session fixture overrides DI container provider.
- Session fixture resets override after session completes.
- Per-test fixture depends on session fixture.
- Per-test fixture calls `reset()` to clear call tracking.
- Per-test fixture yields the same fake instance.

## Scoping Rules

- Session scope for fake creation and DI override (expensive operation).
- Function scope for state reset (cheap operation).
- Two-tier pattern balances performance with test isolation.

## Dependencies

- Session fixture depends on `containers` fixture.
- Per-test fixture depends on session fixture.
- Use `autouse=True` for fixtures that should apply to all tests.

## Example: Two-Tier Pattern

```python
@pytest.fixture(autouse=True, scope="session")
def fake_d365_client_session(containers):
    fake_client = FakeD365Client()
    containers.d365_client.override(fake_client)

    yield fake_client

    containers.d365_client.reset_override()

@pytest.fixture(autouse=True)
def fake_d365_client(fake_d365_client_session):
    fake_d365_client_session.reset()
    yield fake_d365_client_session
```

## Example: Mock for Event Publisher

For domain event publishers, use Mock instead of custom fakes:

```python
@pytest.fixture(autouse=True, scope="session")
def domain_event_publisher_session_mock(containers):
    mock = Mock(containers.domain_event_publisher())
    containers.domain_event_publisher.override(mock)

    yield mock

    containers.domain_event_publisher.reset_override()

@pytest.fixture(autouse=True)
def domain_event_publisher_mock(domain_event_publisher_session_mock):
    domain_event_publisher_session_mock.reset_mock()
    yield domain_event_publisher_session_mock
```

## Non-Autouse Fakes

For fakes that tests explicitly request:

```python
@pytest.fixture(autouse=True)
def fake_load_details_repository(containers):
    fake_repo = FakeLoadDetailsRepository()
    containers.load_details_repository.override(fake_repo)

    yield fake_repo

    containers.load_details_repository.reset_override()
```

## Fake Implementation Requirements

Fakes must implement:

1. **`reset()` method** - clear state between tests
2. **Configuration methods** - set up responses/behavior
3. **Call tracking** - record calls for verification

```python
class FakeTextRetriever(ITextRetriever):
    def __init__(self):
        self._texts: dict[tuple[str, str], Text] = {}
        self._should_raise: dict[tuple[str, str], bool] = {}

    def get_text(self, file_id: str, tenant_id: str) -> Text:
        key = (file_id, tenant_id)
        if self._should_raise.get(key):
            raise TextNotFoundError(file_id=file_id, tenant_id=tenant_id)
        return self._texts.get(key)

    # Configuration methods
    def set_text(self, file_id: str, tenant_id: str, text: Text) -> None:
        self._texts[(file_id, tenant_id)] = text

    def set_should_raise_not_found(self, file_id: str, tenant_id: str) -> None:
        self._should_raise[(file_id, tenant_id)] = True

    # Reset method
    def reset(self) -> None:
        self._texts.clear()
        self._should_raise.clear()
```

## Configuring Fakes in Tests

**Configure fake responses BEFORE calling the service method.**

### Setting Up Success Response

```python
def test_process_document__success(
    document_commands,
    fake_text_retriever,
    fake_information_extractor,
    document_1,
    add_documents,
    extraction_result_data,
):
    # GIVEN document exists
    # GIVEN text retriever configured to return text
    text = Text(kind="OCR", result=[{"sequence": 1, "text": "test"}])
    fake_text_retriever.set_text(document_1.file_id, document_1.tenant_id, text)
    
    # GIVEN extractor configured to return result
    result = ProcessingResult.for_entity(kind="Individual", entity=extraction_result_data)
    fake_information_extractor.set_result(document_1.document_type["kind"], "OCR", result)
    
    # WHEN processing
    updated = document_commands.on_document_created(document_1.id, document_1.tenant_id)
    
    # THEN succeeds
    assert updated.status.status == "extracted"
```

### Setting Up Error Response

```python
def test_process_document__text_not_found(
    document_commands,
    fake_text_retriever,
    document_1,
    add_documents,
):
    # GIVEN document exists
    # GIVEN text retriever configured to raise error
    fake_text_retriever.set_should_raise_not_found(
        document_1.file_id, document_1.tenant_id
    )
    
    # WHEN processing
    # THEN error is raised
    with pytest.raises(TextNotFoundError):
        document_commands.on_document_created(document_1.id, document_1.tenant_id)
```

## Verifying Fake Calls

### Verifying Call Was Made

```python
def test_sync_load__calls_external_service(
    load_commands, fake_d365_client, load_1, add_loads
):
    # WHEN syncing
    load_commands.sync_load(load_1.id, load_1.warehouse_id)
    
    # THEN external service was called
    assert len(fake_d365_client.update_line_items_calls) == 1
```

### Verifying Call Arguments

```python
def test_sync_load__passes_correct_args(
    load_commands, fake_d365_client, load_1, add_loads
):
    # WHEN syncing
    load_commands.sync_load(load_1.id, load_1.warehouse_id)
    
    # THEN called with correct arguments
    call_args = fake_d365_client.update_line_items_calls[0]
    assert call_args[0] == load_1.id
    assert call_args[1] == load_1.warehouse_id
```

### Verifying No Call Was Made

```python
def test_skip_document__no_external_call(
    document_commands, fake_d365_client, document_4, add_documents
):
    # WHEN skipping
    document_commands.skip(document_4.id, document_4.tenant_id)
    
    # THEN no external call made
    assert len(fake_d365_client.update_line_items_calls) == 0
```

## Testing Guidance

**For complete test patterns, see [Application Service Test Rules](application-service-test-rules.md).**

---

## Template

```python
from unittest.mock import Mock

import pytest

from tests.fakes import {{ fake_class }}

@pytest.fixture(autouse=True, scope="session")
def {{ fake_name }}_session(containers):
    {% if use_mock -%}
    fake = Mock(containers.{{ container_provider }}())
    {% else -%}
    fake = {{ fake_class }}()
    {% endif -%}
    containers.{{ container_provider }}.override(fake)

    yield fake

    containers.{{ container_provider }}.reset_override()

@pytest.fixture(autouse=True)
def {{ fake_name }}({{ fake_name }}_session):
    {% if use_mock -%}
    {{ fake_name }}_session.reset_mock()
    {% else -%}
    {{ fake_name }}_session.reset()
    {% endif -%}

    yield {{ fake_name }}_session
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ fake_class }}` | Fake implementation class | `FakeTextRetriever`, `FakeD365Client` |
| `{{ fake_name }}` | Name of the fake fixture | `fake_text_retriever`, `fake_d365_client` |
| `{{ container_provider }}` | Container provider property name | `text_retriever`, `d365_client` |
| `{{ use_mock }}` | Boolean indicating Mock vs custom fake | `true` for Mock, `false` for custom fake |
