---
name: application-service-integration-test-rules
description: Application Service Integration Test Rules pattern for application service integration testing. Use when writing or reviewing integration tests that verify application services orchestrating domain operations, persistence, and event publishing.
user-invocable: false
disable-model-invocation: false
---

# Application Service Integration Test Rules

## Purpose

Explicit rules for writing application service integration tests. These tests verify that application services correctly orchestrate domain operations, persistence, and event publishing.

## RULE 1: Use Fixtures for Test Data

**All test data MUST come from fixtures. Never create or persist objects inside test functions.**

This rule applies equally to application service tests as it does to repository tests.

### VIOLATION: Creating and Persisting in Test

```python
# WRONG - creating and persisting objects in test
def test_on_document_types_assigned__replaces_existing(document_commands, unit_of_work):
    existing_doc = Document.new(  # ❌ VIOLATION - creating in test
        tenant_id=tenant_id,
        file_id=file_id,
        document_type={"kind": "passport", "reference": {"id": "ref-001"}},
    )
    existing_doc.events.clear()
    
    with unit_of_work:
        unit_of_work.documents.save(existing_doc)  # ❌ VIOLATION - persisting in test
        unit_of_work.commit()
    
    # ... rest of test
```

### CORRECT: Use Fixtures

```python
# CORRECT - fixtures handle creation and persistence
def test_on_document_types_assigned__replaces_existing(
    document_commands, unit_of_work, document_1, add_documents
):
    # GIVEN document exists in DB (via add_documents fixture)
    file_id = document_1.file_id
    tenant_id = document_1.tenant_id
    
    # WHEN assigning new document types
    new_types = [{"kind": "driver_licence", "reference": {"id": "ref-new"}}]
    new_documents = document_commands.on_document_types_assigned(file_id, tenant_id, new_types)
    
    # THEN old document is deleted, new created
    assert unit_of_work.documents.document_of_id(document_1.id, tenant_id) is None
    assert len(new_documents) == 1
```

## RULE 2: Configure Fakes Before Action

**Set up fake responses BEFORE calling the service method.**

### Fake Configuration Pattern

```python
def test_on_document_created__success(
    document_commands,
    fake_text_retriever,
    fake_information_extractor,
    document_1,
    add_documents,
    extraction_result_individual_data,
):
    # GIVEN document exists in DB
    # GIVEN text retriever configured to return text
    text = Text(kind="OCR", result=[{"sequence": 1, "text": "test"}])
    fake_text_retriever.set_text(document_1.file_id, document_1.tenant_id, text)
    
    # GIVEN information extractor configured to return result
    result = ProcessingResult.for_entity(
        kind="Individual", 
        entity=extraction_result_individual_data["entity"]
    )
    fake_information_extractor.set_result(document_1.document_type["kind"], "OCR", result)
    
    # WHEN processing document
    updated = document_commands.on_document_created(document_1.id, document_1.tenant_id)
    
    # THEN document is processed successfully
    assert updated.status.status == "extracted"
```

### Fake Error Configuration

```python
def test_on_document_created__text_not_found(
    document_commands,
    fake_text_retriever,
    document_1,
    add_documents,
):
    # GIVEN document exists in DB
    # GIVEN text retriever configured to raise error
    fake_text_retriever.set_should_raise_not_found(document_1.file_id, document_1.tenant_id)
    
    # WHEN processing document
    # THEN error is raised
    with pytest.raises(TextNotFoundError):
        document_commands.on_document_created(document_1.id, document_1.tenant_id)
```

## RULE 3: Verify Domain Events

**Verify event type, count, and payload. Don't just check that publish was called.**

### VIOLATION: Incomplete Event Verification

```python
# WRONG - only checks call count
def test_create_document__publishes_event(document_commands, domain_event_publisher_mock):
    document_commands.create_document(...)
    assert domain_event_publisher_mock.publish.call_count == 1  # ❌ Incomplete
```

### CORRECT: Full Event Verification

```python
# CORRECT - verifies event type, aggregate_id, and payload
def test_create_document__publishes_event(
    document_commands, domain_event_publisher_mock, document_1, add_documents
):
    # WHEN creating document
    result = document_commands.on_document_created(document_1.id, document_1.tenant_id)
    
    # THEN event is published
    domain_event_publisher_mock.publish.assert_called_once()
    
    # THEN event has correct metadata
    call_args = domain_event_publisher_mock.publish.call_args
    assert call_args.kwargs["aggregate_id"] == document_1.id
    
    # THEN event has correct type and payload
    events = call_args.kwargs["domain_events"]
    assert len(events) == 1
    assert isinstance(events[0], DocumentProcessingSucceeded)
    assert events[0].id == document_1.id
    assert events[0].subject_extracted is True
```

### Verifying No Events Published

```python
def test_idempotent_operation__no_event(
    document_commands, domain_event_publisher_mock, document_1, add_documents
):
    # WHEN calling idempotent operation
    document_commands.some_idempotent_operation(document_1.id, document_1.tenant_id)
    
    # THEN no events published
    domain_event_publisher_mock.publish.assert_not_called()
```

### Verifying Multiple Events

```python
def test_retry__publishes_multiple_events(
    document_commands, domain_event_publisher_mock, document_4, add_documents
):
    # WHEN retrying failed document
    document_commands.retry(document_4.id, document_4.tenant_id)
    
    # THEN multiple events published
    domain_event_publisher_mock.publish.assert_called_once()
    call_args = domain_event_publisher_mock.publish.call_args
    events = call_args.kwargs["domain_events"]
    
    assert len(events) == 2
    assert isinstance(events[0], DocumentProcessingRetried)
    assert isinstance(events[1], DocumentCreated)
```

## RULE 4: Verify External Service Calls

**Verify that fake external services were called (or not called) with the correct arguments.**

For non-publisher external dependencies, custom fakes track calls in lists. Assert against those lists to verify behavior.

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

## RULE 5: Verify Persistence

**Always verify that state changes are persisted, not just returned.**

```python
def test_add_corrections__persists_changes(
    document_commands, unit_of_work, document_2, add_documents, corrections_data
):
    # WHEN adding corrections
    updated = document_commands.add_corrections(
        document_2.id, document_2.tenant_id, corrections_data
    )
    
    # THEN returned object has correct state
    assert updated.status.status == "corrected"
    
    # THEN changes are persisted (reload from DB)
    loaded = unit_of_work.documents.document_of_id(updated.id, updated.tenant_id)
    assert loaded.status.status == "corrected"
    assert loaded.equals(updated)
```

## RULE 6: Test All Service Method Types

Application services have different method types with different test patterns:

### Event Handlers (on_*)

Handle domain events from other aggregates/services.

```python
def test_on_file_uploaded__adds_file_to_profile(
    profile_commands, unit_of_work, profile_1, add_profiles
):
    # GIVEN existing profile
    file_id = uuid4().hex
    
    # WHEN handling file uploaded event
    updated = profile_commands.on_file_uploaded(
        profile_1.id, profile_1.tenant_id, file_id
    )
    
    # THEN file is added
    assert file_id in updated.files
    
    # THEN persisted
    loaded = unit_of_work.profiles.profile_of_id(profile_1.id, profile_1.tenant_id)
    assert file_id in loaded.files
```

### Commands (action methods)

Perform actions requested by users/API.

```python
def test_retry__reverts_to_created_status(
    document_commands, unit_of_work, document_4, add_documents
):
    # GIVEN document in failed status
    assert document_4.status.status == "failed"
    
    # WHEN retrying
    updated = document_commands.retry(document_4.id, document_4.tenant_id)
    
    # THEN status reverts to created
    assert updated.status.status == "created"
    assert updated.status.error is None
```

### Queries (get_*, list_*)

Return data without side effects.

```python
def test_get_document__returns_document(
    document_queries, document_1, add_documents
):
    # GIVEN document exists
    # WHEN querying
    result = document_queries.get_document(document_1.id, document_1.tenant_id)
    
    # THEN returns document data
    assert result["id"] == document_1.id
    assert result["status"] == document_1.status.status
```

## Test Patterns by Scenario

### Success Path

```python
def test_{service_method}__success(
    {service}_commands,
    unit_of_work,
    domain_event_publisher_mock,
    {aggregate}_fixture,
    add_{aggregates},
):
    # GIVEN aggregate exists in DB
    # WHEN calling service method
    result = {service}_commands.{method}({aggregate}_fixture.id, ...)
    
    # THEN state changes correctly
    assert result.status == "expected_status"
    
    # THEN changes persisted
    loaded = unit_of_work.{repository}.{query}(...)
    assert loaded.equals(result)
    
    # THEN correct events published
    domain_event_publisher_mock.publish.assert_called_once()
    events = domain_event_publisher_mock.publish.call_args.kwargs["domain_events"]
    assert isinstance(events[0], ExpectedEvent)
```

### Not Found Error

```python
def test_{service_method}__not_found(
    {service}_commands,
    {aggregate}_fixture,  # NOT persisted - no add_* fixture
):
    # GIVEN aggregate does NOT exist in DB
    # WHEN calling service method
    # THEN NotFoundError is raised
    with pytest.raises({Aggregate}NotFoundError) as exc_info:
        {service}_commands.{method}({aggregate}_fixture.id, ...)
    
    assert exc_info.value.{aggregate}_id == {aggregate}_fixture.id
```

### Domain Error (Invalid State)

```python
def test_{service_method}__invalid_state(
    {service}_commands,
    {aggregate}_in_wrong_state,  # Fixture with wrong state
    add_{aggregates},
):
    # GIVEN aggregate in invalid state for this operation
    # WHEN calling service method
    # THEN domain error is raised
    with pytest.raises({DomainError}):
        {service}_commands.{method}({aggregate}_in_wrong_state.id, ...)
```

### Idempotency

```python
def test_{service_method}__idempotent(
    {service}_commands,
    {aggregate}_fixture,
    add_{aggregates},
):
    # GIVEN aggregate exists
    # WHEN calling method twice
    result1 = {service}_commands.{method}(...)
    result2 = {service}_commands.{method}(...)
    
    # THEN second call returns same result or existing entity
    assert result2.id == result1.id
```

## Test Naming Convention

```
test_{service_method}__{scenario}__{expected_outcome}
```

### Examples

```python
# Event handlers
test_on_file_uploaded__adds_file_to_profile
test_on_document_created__success_with_data
test_on_document_created__text_not_found__raises

# Commands
test_retry__success
test_retry__not_retryable__raises
test_add_corrections__individual_success

# Queries
test_get_document__found__returns_document
test_get_document__not_found__returns_none
```

## Summary of Violations

| Violation | Example | Fix |
| --- | --- | --- |
| Create object in test | `Document.new()` in test | Use fixture |
| Persist in test | `unit_of_work.save()` for setup | Use `add_*` fixture |
| Incomplete event verification | `call_count == 1` only | Verify type + payload |
| Missing persistence verification | Only check returned object | Reload and verify |
| Unconfigured fake | Call service without fake setup | Configure fake first |

## What's NOT a Violation

| Action | Example | Why It's OK |
| --- | --- | --- |
| Configuring fakes in test | `fake.set_text(...)` | Required for test setup |
| Creating input data in test | `new_types = [{"kind": "..."}]` | Input, not domain object |
| Multiple service calls | Testing idempotency | Valid test scenario |
