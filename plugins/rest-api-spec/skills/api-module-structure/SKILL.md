---
name: api-module-structure
description: API Module Structure pattern for REST APIs. Use when organizing routing, serialization, authentication, and error handling components in a versioned API package.
user-invocable: false
disable-model-invocation: false
---

# API Module Structure

## Purpose

- Organize REST API components in a consistent, maintainable structure.
- Separate concerns: routing, serialization, authentication, error handling.
- Support API versioning with clear boundaries.

## Structure

The API module follows this hierarchical organization:

```
my_service/api/
├── __init__.py                        # Module exports
├── auth.py                            # User authentication
├── endpoint_marker.py                 # Custom route class
├── endpoint_visibility.py             # Visibility enum
├── error_handlers.py                  # Exception → HTTP mapping
├── fastapi_auth.py                    # OpenAPI security schema
├── endpoints/                         # Route definitions
│   ├── __init__.py                    # Router aggregation
│   ├── debug.py                       # Debug utilities
│   ├── healthcheck.py                 # Health checks
│   ├── service_info.py                # Build/version info
│   ├── v1/                            # API version 1
│   │   ├── __init__.py                # v1 router
│   │   └── {resource}.py              # Resource endpoints
│   ├── v2/                            # API version 2
│   │   ├── __init__.py                # v2 router
│   │   └── {resource}.py              # Resource endpoints
│   └── internal/                      # Internal endpoints (optional)
│       ├── __init__.py
│       └── {resource}.py
└── serializers/                       # Request/Response models
    ├── __init__.py                    # Serializer exports
    ├── build_info.py                  # Build info model
    ├── configured_base_serializer.py  # Base classes
    ├── error.py                       # Error response
    ├── json_utils.py                  # camelCase conversion
    ├── paginated_result_metadata.py   # Pagination metadata
    ├── result_set.py                  # Result set metadata
    ├── v1/                            # v1 serializers
    │   └── {resource}/                # Resource serializers
    │       ├── __init__.py
    │       ├── create_{resource}.py
    │       ├── get_{resource}.py
    │       └── get_{resources}.py
    └── v2/                            # v2 serializers
        └── {resource}/
            └── ...
```

## Module Responsibilities

### Root Level Files

| File | Responsibility |
| --- | --- |
| `__init__.py` | Export all public API components |
| `auth.py` | Extract user from JWT token, set context vars |
| `endpoint_marker.py` | Custom `APIRoute` for OpenAPI summary |
| `endpoint_visibility.py` | `Visibility` enum (PUBLIC, INTERNAL) |
| `error_handlers.py` | Register exception handlers with FastAPI |
| `fastapi_auth.py` | Configure OpenAPI security scheme |

### endpoints/ Directory

Contains router definitions organized by version:

- `debug.py` - Debug endpoints (500 error trigger, etc.)
- `healthcheck.py` - Database and service health checks
- `service_info.py` - Build info and version endpoint
- `v1/__init__.py` - Version 1 router aggregating all v1 resources
- `v1/{resource}.py` - Endpoints for a specific resource

### serializers/ Directory

Contains Pydantic models for request/response serialization:

- `configured_base_serializer.py` - Base classes with shared configuration
- `error.py` - Error response format
- `v1/{resource}/` - Serializers for each resource in v1

## Export Pattern

Each `__init__.py` follows this pattern:

```python
# type: ignore
from .auth import *
from .endpoint_marker import *
from .endpoint_visibility import *
from .endpoints import *
from .fastapi_auth import *
from .serializers import *

__all__ = (
    auth.__all__
    + endpoints.__all__
    + serializers.__all__
    + endpoint_marker.__all__
    + endpoint_visibility.__all__
    + fastapi_auth.__all__
)
```

## Versioning Guidelines

### When to Create a New Version

- Breaking changes to request/response format
- Major changes to endpoint behavior
- Significant restructuring of resource relationships

### Version Coexistence

- Multiple versions can coexist (v1, v2, v3)
- Each version has independent routers and serializers
- Share utility code via base serializers and common modules

## Best Practices

1. **One file per endpoint group** - Group related endpoints by resource
2. **Mirror serializer structure** - Match serializer directory structure to endpoints
3. **Version-specific serializers** - Don't share response models between versions
4. **Shared utilities** - Base serializers and utils are version-agnostic
5. **Internal endpoints** - Use `/internal/` prefix for service-to-service calls
