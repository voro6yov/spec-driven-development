---
name: api-client-fixtures
description: API Client Fixtures pattern for REST API testing. Use when writing pytest fixtures for FastAPI TestClient, authentication headers, and DI container overrides in integration/API tests.
user-invocable: false
disable-model-invocation: false
---

# API Client Fixtures

## Purpose

- Provide FastAPI TestClient for making HTTP requests in tests.
- Manage authentication headers and token payloads.
- Configure dependency injection container overrides.
- Ensure test isolation with proper setup/teardown.

## CRITICAL: Placement Rule

**API client and authentication fixtures MUST be defined in root `tests/conftest.py`.**

This is mandatory because:

- All API tests need access to the client
- Authentication fixtures are shared across all test types
- Container fixtures need session scope for performance

```
tests/
├── conftest.py           # client, request_headers, app, containers
├── integration/
│   ├── conftest.py       # add_*, unit_of_work (uses containers)
│   └── api/
│       └── test_*.py     # API tests use client + add_* fixtures
└── unit/
    └── test_*.py
```

## Core Fixtures

### FastAPI Application Fixture

Creates the FastAPI application instance once per test session.

```python
import pytest
from fastapi import FastAPI

from {{ module_path }}.entrypoint import create_fastapi

@pytest.fixture(scope="session")
def app() -> FastAPI:
    fastapi_app = create_fastapi()
    yield fastapi_app
```

### TestClient Fixture

Provides HTTP client for making requests to the application.

```python
from starlette.testclient import TestClient

@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client
```

### DI Container Fixture

Provides access to the dependency injection container for overrides.

```python
@pytest.fixture(scope="session")
def containers(app):
    return app.containers
```

## Authentication Fixtures

### Token Payload Fixture

Provides JWT token payload data.

```python
from typing import Any

@pytest.fixture
def token_payload() -> dict[str, Any]:
    return {
        "sub": "user_id",
        "email": "test@email.com",
        "given_name": "John",
        "family_name": "Doe",
    }
```

### Request Headers Fixture

Provides authorization headers for authenticated requests.

```python
import jwt

@pytest.fixture
def request_headers(token_payload):
    return {
        "Authorization": f"Bearer {jwt.encode(token_payload, None, algorithm='none')}",
    }
```

## Fixture Dependencies

```
┌─────────────────────────────────────────────────┐
│ test function                                   │
│   - depends on: client, request_headers, add_* │
└─────────────────────────────────────────────────┘
                    │
      ┌─────────────┼─────────────┐
      ▼             ▼             ▼
┌──────────┐  ┌───────────────┐  ┌──────────────┐
│ client   │  │request_headers│  │ add_loads    │
│ (func)   │  │    (func)     │  │   (func)     │
└──────────┘  └───────────────┘  └──────────────┘
      │             │                   │
      ▼             ▼                   ▼
┌──────────┐  ┌───────────────┐  ┌──────────────┐
│   app    │  │ token_payload │  │ unit_of_work │
│(session) │  │    (func)     │  │   (func)     │
└──────────┘  └───────────────┘  └──────────────┘
      │                               │
      ▼                               ▼
┌─────────────────────────────────────────────────┐
│ containers (session)                            │
└─────────────────────────────────────────────────┘
```

## Scoping Rules

| Fixture | Scope | Reason |
| --- | --- | --- |
| `app` | session | Expensive to create, stateless |
| `containers` | session | Tied to app lifecycle |
| `client` | function | Fresh connection per test |
| `token_payload` | function | May vary per test |
| `request_headers` | function | Depends on token_payload |

## Session vs Function Scope

### Session Scope (Reused Across Tests)

```python
@pytest.fixture(scope="session")
def app() -> FastAPI:
    # Created once, shared across all tests
    fastapi_app = create_fastapi()
    yield fastapi_app
```

### Function Scope (Fresh Per Test)

```python
@pytest.fixture
def client(app):
    # Fresh client for each test
    with TestClient(app) as client:
        yield client
```

## Testing Different User Contexts

### Override Token Payload for Specific Test

```python
def test_get_loads__different_user__sees_own_data(
    client,
    token_payload,
    add_loads,
):
    # Override token for this specific test
    custom_payload = {**token_payload, "sub": "different_user_id"}
    headers = {
        "Authorization": f"Bearer {jwt.encode(custom_payload, None, algorithm='none')}",
    }
    
    response = client.get(
        f"/api/v2/loads?warehouseId={DEFAULT_WAREHOUSE_ID}",
        headers=headers,
    )
    assert response.status_code == HTTPStatus.OK
```

### Fixture for Admin User

```python
@pytest.fixture
def admin_token_payload() -> dict[str, Any]:
    return {
        "sub": "admin_user_id",
        "email": "admin@email.com",
        "given_name": "Admin",
        "family_name": "User",
        "roles": ["admin"],
    }

@pytest.fixture
def admin_request_headers(admin_token_payload):
    return {
        "Authorization": f"Bearer {jwt.encode(admin_token_payload, None, algorithm='none')}",
    }
```

## Fake Override Fixtures for API Tests

API tests use the same fake override pattern as application tests.

```python
@pytest.fixture(autouse=True, scope="session")
def fake_external_service_session(containers):
    fake = FakeExternalService()
    containers.external_service.override(fake)
    
    yield fake
    
    containers.external_service.reset_override()

@pytest.fixture(autouse=True)
def fake_external_service(fake_external_service_session):
    fake_external_service_session.reset()
    yield fake_external_service_session
```

## Complete Root conftest.py Template

```python
from typing import Any
from unittest.mock import Mock

import jwt
import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from tests.fakes import FakeTextRetriever, FakeInformationExtractor
from {{ module_path }}.entrypoint import create_fastapi

# ============================================================
# Application & Client Fixtures
# ============================================================

@pytest.fixture(scope="session")
def app() -> FastAPI:
    fastapi_app = create_fastapi()
    yield fastapi_app

@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client

@pytest.fixture(scope="session")
def containers(app):
    return app.containers

@pytest.fixture
def repositories(containers):
    return containers.repositories

# ============================================================
# Authentication Fixtures
# ============================================================

@pytest.fixture
def token_payload() -> dict[str, Any]:
    return {
        "sub": "user_id",
        "email": "test@email.com",
        "given_name": "John",
        "family_name": "Doe",
    }

@pytest.fixture
def request_headers(token_payload):
    return {
        "Authorization": f"Bearer {jwt.encode(token_payload, None, algorithm='none')}",
    }

# ============================================================
# Fake Override Fixtures
# ============================================================

@pytest.fixture(autouse=True, scope="session")
def fake_text_retriever_session(containers):
    fake = FakeTextRetriever()
    containers.text_retriever.override(fake)
    
    yield fake
    
    containers.text_retriever.reset_override()

@pytest.fixture(autouse=True)
def fake_text_retriever(fake_text_retriever_session):
    fake_text_retriever_session.reset()
    yield fake_text_retriever_session

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

# ============================================================
# Service Fixtures
# ============================================================

@pytest.fixture
def document_commands(containers):
    return containers.document_commands()

@pytest.fixture
def profile_commands(containers):
    return containers.profile_commands()

# ============================================================
# Aggregate Fixtures (see aggregate-fixtures.md for details)
# ============================================================

# ... aggregate data fixtures ...
# ... aggregate fixtures ...
# ... collection fixtures ...
```

---

## Templates

### Application Fixture

```python
import pytest
from fastapi import FastAPI

from {{ module_path }}.entrypoint import create_fastapi

@pytest.fixture(scope="session")
def app() -> FastAPI:
    fastapi_app = create_fastapi()
    yield fastapi_app
```

### Client Fixture

```python
from starlette.testclient import TestClient

@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client
```

### Authentication Fixtures

```python
from typing import Any

import jwt
import pytest

@pytest.fixture
def token_payload() -> dict[str, Any]:
    return {
        "sub": "{{ user_id }}",
        "email": "{{ user_email }}",
        "given_name": "{{ first_name }}",
        "family_name": "{{ last_name }}",
    }

@pytest.fixture
def request_headers(token_payload):
    return {
        "Authorization": f"Bearer {jwt.encode(token_payload, None, algorithm='none')}",
    }
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ module_path }}` | Module path for imports | `iv_documents`, `tss_load_processing` |
| `{{ user_id }}` | Test user ID | `"user_id"`, `"test-user-001"` |
| `{{ user_email }}` | Test user email | `"test@email.com"` |
| `{{ first_name }}` | Test user first name | `"John"` |
| `{{ last_name }}` | Test user last name | `"Doe"` |
