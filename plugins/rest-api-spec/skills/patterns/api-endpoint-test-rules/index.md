---
name: api-endpoint-test-rules
description: API Endpoint Integration Test Rules pattern for REST APIs. Use when writing or reviewing integration tests for HTTP endpoints to ensure correct request handling, service delegation, response serialization, and status code verification.
user-invocable: false
disable-model-invocation: false
---

# API Endpoint Integration Test Rules

## Purpose

Explicit rules for writing REST API endpoint integration tests. These tests verify that HTTP endpoints correctly handle requests, delegate to application services, serialize responses, and return appropriate HTTP status codes.

## RULE 1: Use Fixtures for Test Data

**All test data MUST come from fixtures. Never create or persist objects inside test functions.**

This rule applies equally to API tests as it does to repository and application tests.

### VIOLATION: Creating and Persisting in Test

```python
# WRONG - creating and persisting objects in test
def test_get_load__success(client, request_headers, unit_of_work):
    load = Load.from_load_data(  # ❌ VIOLATION - creating in test
        DEFAULT_WAREHOUSE_ID,
        "conveyor-001",
        {"id": "load-001", "items": [...]},
    )
    with unit_of_work:
        unit_of_work.loads.save(load)  # ❌ VIOLATION - persisting in test
        unit_of_work.commit()
    
    response = client.get(f"/api/v2/loads/{load.id}?warehouseId={DEFAULT_WAREHOUSE_ID}")
    assert response.status_code == HTTPStatus.OK
```

### CORRECT: Use Persistence Fixtures

```python
# CORRECT - fixtures handle creation and persistence
def test_get_load__success(client, request_headers, load_1, add_loads):
    # GIVEN load exists in DB (via add_loads fixture)
    # WHEN getting load via API
    response = client.get(
        f"/api/v2/loads/{load_1.id}?warehouseId={DEFAULT_WAREHOUSE_ID}",
        headers=request_headers,
    )
    
    # THEN returns success with load data
    assert response.status_code == HTTPStatus.OK
    assert response.json()["id"] == load_1.id
```

## RULE 2: Always Use Authentication Headers

**All API tests MUST include authentication headers when endpoints require authentication.**

### Fixture Pattern

These fixtures are defined in the root `tests/conftest.py`.

### VIOLATION: Missing Headers

```python
# WRONG - missing authentication headers
def test_get_load__success(client, add_loads):
    response = client.get(f"/api/v2/loads/load-123?warehouseId={DEFAULT_WAREHOUSE_ID}")
    # May return 401 Unauthorized
```

### CORRECT: Include Headers

```python
# CORRECT - headers included
def test_get_load__success(client, request_headers, add_loads):
    response = client.get(
        f"/api/v2/loads/load-123?warehouseId={DEFAULT_WAREHOUSE_ID}",
        headers=request_headers,
    )
    assert response.status_code == HTTPStatus.OK
```

## RULE 3: Test HTTP Status Codes Explicitly

**Always assert the expected HTTP status code before asserting response body.**

### Status Code Mapping

| Domain Exception | HTTP Status Code | When to Use |
| --- | --- | --- |
| Success | `200 OK` | Successful GET, PUT, PATCH, POST returning data |
| Created | `201 Created` | Successful POST creating new resource |
| No Content | `204 No Content` | Successful DELETE with no response body |
| Bad Request | `400 Bad Request` | Validation errors, invalid input |
| Unauthorized | `401 Unauthorized` | Missing or invalid authentication |
| Forbidden | `403 Forbidden` | Authenticated but not authorized |
| Not Found | `404 Not Found` | Resource doesn't exist |
| Conflict | `409 Conflict` | Business rule violation, state conflict |
| Unprocessable Entity | `422 Unprocessable Entity` | Semantic validation errors |
| Internal Server Error | `500 Internal Server Error` | Unhandled exceptions |

### Test Pattern for Each Status

```python
# Success (200)
def test_get_load__success(client, request_headers, add_loads):
    response = client.get(f"/api/v2/loads/load-123?warehouseId={DEFAULT_WAREHOUSE_ID}", headers=request_headers)
    assert response.status_code == HTTPStatus.OK

# Not Found (404)
def test_get_load__not_found(client, request_headers):
    response = client.get(f"/api/v2/loads/non-existent?warehouseId={DEFAULT_WAREHOUSE_ID}", headers=request_headers)
    assert response.status_code == HTTPStatus.NOT_FOUND

# Conflict (409)
def test_start_receiving__already_started__conflict(client, request_headers, load_receiving, add_loads):
    response = client.post(
        f"/api/v2/loads/{load_receiving.id}/start-receiving?warehouseId={DEFAULT_WAREHOUSE_ID}",
        headers=request_headers,
    )
    assert response.status_code == HTTPStatus.CONFLICT
```

## RULE 4: Assert Response Structure

**Verify response structure uses correct field naming (camelCase for JSON API).**

### VIOLATION: Assuming Field Names

```python
# WRONG - not verifying response structure
def test_get_load__success(client, request_headers, add_loads):
    response = client.get(...)
    assert response.status_code == HTTPStatus.OK
    # No structure verification
```

### CORRECT: Verify Response Fields

```python
# CORRECT - verify response structure
def test_get_load__response_structure__contains_camel_case_fields(client, request_headers, add_loads):
    response = client.get(
        f"/api/v2/loads/load-123?warehouseId={DEFAULT_WAREHOUSE_ID}",
        headers=request_headers,
    )
    
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    
    # Verify top-level fields
    assert "id" in data
    assert "warehouseId" in data  # camelCase
    assert "numberOfTires" in data  # camelCase
    assert "lineItems" in data  # camelCase
    
    # Verify nested structure
    if len(data["lineItems"]) > 0:
        line_item = data["lineItems"][0]
        assert "itemNumber" in line_item
        assert "productName" in line_item
        assert "totalQuantity" in line_item
```

## RULE 5: Test Query Parameters and Filters

**Test all query parameter combinations and edge cases.**

### Query Parameter Test Patterns

```python
# Filter by single value
def test_get_loads__filter_by_status__returns_matching(client, request_headers, add_loads):
    response = client.get(
        f"/api/v2/loads?warehouseId={DEFAULT_WAREHOUSE_ID}&statuses=pending",
        headers=request_headers,
    )
    assert response.status_code == HTTPStatus.OK
    for load in response.json()["loads"]:
        assert load["status"] == "pending"

# Filter by multiple values
def test_get_loads__filter_by_multiple_statuses__returns_matching(client, request_headers, add_loads):
    response = client.get(
        f"/api/v2/loads?warehouseId={DEFAULT_WAREHOUSE_ID}&statuses=pending&statuses=receiving",
        headers=request_headers,
    )
    assert response.status_code == HTTPStatus.OK
    for load in response.json()["loads"]:
        assert load["status"] in ["pending", "receiving"]

# Search with case insensitivity
def test_get_loads__search_case_insensitive__returns_matching(client, request_headers, add_loads):
    response = client.get(
        f"/api/v2/loads?warehouseId={DEFAULT_WAREHOUSE_ID}&search=MICHELIN",
        headers=request_headers,
    )
    assert response.status_code == HTTPStatus.OK

# Sorting
def test_get_loads__sort_ascending__returns_sorted(client, request_headers, add_loads):
    response = client.get(
        f"/api/v2/loads?warehouseId={DEFAULT_WAREHOUSE_ID}&sorting=status:asc",
        headers=request_headers,
    )
    assert response.status_code == HTTPStatus.OK
    statuses = [load["status"] for load in response.json()["loads"]]
    assert statuses == sorted(statuses)

# Combined filters
def test_get_loads__combined_search_filter_sort__applies_all(client, request_headers, add_loads):
    response = client.get(
        f"/api/v2/loads?warehouseId={DEFAULT_WAREHOUSE_ID}&search=Sport&statuses=pending&sorting=eta:desc",
        headers=request_headers,
    )
    assert response.status_code == HTTPStatus.OK
```

## RULE 6: Test Path Parameters

**Test both valid and invalid path parameters.**

```python
# Valid path parameter
def test_get_load__valid_id__returns_load(client, request_headers, load_1, add_loads):
    response = client.get(
        f"/api/v2/loads/{load_1.id}?warehouseId={DEFAULT_WAREHOUSE_ID}",
        headers=request_headers,
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()["id"] == load_1.id

# Invalid path parameter (not found)
def test_get_load__invalid_id__returns_not_found(client, request_headers):
    response = client.get(
        f"/api/v2/loads/non-existent-id?warehouseId={DEFAULT_WAREHOUSE_ID}",
        headers=request_headers,
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
```

## RULE 7: Test Request Body Validation

**Test both valid and invalid request bodies for POST/PUT/PATCH endpoints.**

```python
# Valid request body
def test_create_document__valid_body__returns_created(client, request_headers):
    response = client.post(
        "/api/v1/documents",
        headers=request_headers,
        json={
            "fileId": "file-123",
            "tenantId": "tenant-123",
            "documentType": {"kind": "passport"},
        },
    )
    assert response.status_code == HTTPStatus.OK

# Invalid request body - missing required field
def test_create_document__missing_required_field__returns_bad_request(client, request_headers):
    response = client.post(
        "/api/v1/documents",
        headers=request_headers,
        json={
            "fileId": "file-123",
            # Missing tenantId
        },
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

# Invalid request body - wrong type
def test_create_document__invalid_type__returns_bad_request(client, request_headers):
    response = client.post(
        "/api/v1/documents",
        headers=request_headers,
        json={
            "fileId": 123,  # Should be string
            "tenantId": "tenant-123",
        },
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
```

## RULE 8: Don't Test Internal Implementation

**API tests should verify HTTP contract, not internal implementation details.**

### VIOLATION: Testing Internal State

```python
# WRONG - accessing internal state
def test_start_receiving__success(client, request_headers, load_1, add_loads, unit_of_work):
    response = client.post(
        f"/api/v2/loads/{load_1.id}/start-receiving?warehouseId={DEFAULT_WAREHOUSE_ID}",
        headers=request_headers,
    )
    
    # ❌ VIOLATION - reaching into database to verify
    loaded = unit_of_work.loads.load_of_id(load_1.id)
    assert loaded.status == "receiving"
```

### CORRECT: Test HTTP Response Only

```python
# CORRECT - verify via API response
def test_start_receiving__success(client, request_headers, load_1, add_loads):
    response = client.post(
        f"/api/v2/loads/{load_1.id}/start-receiving?warehouseId={DEFAULT_WAREHOUSE_ID}",
        headers=request_headers,
    )
    
    assert response.status_code == HTTPStatus.OK
    assert response.json()["id"] == load_1.id
    
    # Verify state via GET endpoint if needed
    get_response = client.get(
        f"/api/v2/loads/{load_1.id}?warehouseId={DEFAULT_WAREHOUSE_ID}",
        headers=request_headers,
    )
    assert get_response.json()["status"] == "receiving"
```

## Test Naming Convention

```
test_{endpoint_action}__{scenario}__{expected_outcome}
```

### Components

| Part | Description | Example |
| --- | --- | --- |
| `{endpoint_action}` | HTTP method + resource | `get_load`, `create_document`, `start_receiving` |
| `{scenario}` | Input condition or precondition | `valid_id`, `not_found`, `filter_by_status` |
| `{expected_outcome}` | What should happen | `returns_load`, `returns_not_found`, `returns_sorted` |

### Examples

```python
# GET endpoints
test_get_load__valid_id__returns_load
test_get_load__not_found__returns_404
test_get_loads__filter_by_status__returns_matching
test_get_loads__search_case_insensitive__returns_matching

# POST command endpoints
test_start_receiving__load_exists__returns_success
test_start_receiving__load_not_found__returns_404
test_start_receiving__already_started__returns_conflict

# POST create endpoints
test_create_document__valid_body__returns_created
test_create_document__missing_field__returns_bad_request
```

## Test Structure Template

```python
def test_{endpoint_action}__{scenario}__{expected_outcome}(
    client,
    request_headers,
    {aggregate}_fixture,
    add_{aggregates},
):
    # GIVEN {precondition from fixtures}
    
    # WHEN {HTTP request}
    response = client.{method}(
        f"{API_PREFIX}/{endpoint}",
        headers=request_headers,
    )
    
    # THEN {expected HTTP response}
    assert response.status_code == HTTPStatus.{EXPECTED_STATUS}
    # Assert response body if applicable
```

## Summary of Violations

| Violation | Example | Fix |
| --- | --- | --- |
| Create object in test | `load = Load.new()` in test | Use fixture |
| Persist in test | `unit_of_work.save(load)` for setup | Use `add_*` fixture |
| Missing auth headers | No `headers=request_headers` | Add headers parameter |
| Not checking status code | Only check response body | Assert status code first |
| Testing internal state | Query DB after API call | Verify via API response |
| Hardcoded IDs | `load_id = "load-123"` | Use `load_1.id` from fixture |
| Missing required params | Omit `warehouseId` | Include all required params |

## What's NOT a Violation

| Action | Example | Why It's OK |
| --- | --- | --- |
| Creating input JSON in test | `json={"fileId": "..."}` | Input data, not domain object |
| Multiple API calls | GET after POST to verify | Valid integration test |
| Testing error responses | Assert 404, 409, etc. | Required for API contract |
| Using hardcoded expected values | `assert data["status"] == "pending"` | Testing serialization |
