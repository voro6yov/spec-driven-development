---
name: module-exports
description: Module Exports pattern for REST API packages. Use when structuring `__init__.py` files to provide clean import paths and aggregate exports across endpoint and serializer sub-modules.
user-invocable: false
disable-model-invocation: false
---

# Module Exports

## Purpose

- Provide clean import paths for API components.
- Aggregate exports from sub-modules for easier consumption.
- Enable `from my_service.api import router, serializer` style imports.

## Structure

- Each module directory has an `__init__.py` with re-exports.
- Use wildcard imports (`from .module import *`) for aggregation.
- Aggregate `__all__` lists for explicit exports.

## Patterns

### Endpoints Module Export

The `api/endpoints/__init__.py` file aggregates all router exports:

```python
# type: ignore
from .debug import *
from .healthcheck import *
from .internal import *
from .service_info import *
from .v1 import *
from .v2 import *

__all__ = (
    debug.__all__
    + healthcheck.__all__
    + service_info.__all__
    + v1.__all__
    + internal.__all__
    + v2.__all__
)
```

Note: `# type: ignore` suppresses type checker warnings about wildcard imports.

### Version Router Export

Each version directory (`v1/`, `v2/`) has its own aggregation:

```python
from fastapi import APIRouter

from .conveyors import *
from .loads import *

__all__ = ["v1_router"]

v1_router = APIRouter(prefix="/v1")

v1_router.include_router(loads_router)
v1_router.include_router(conveyors_router)
```

### Serializers Module Export

The `api/serializers/__init__.py` aggregates all serializer exports:

```python
# type: ignore
from .build_info import *
from .configured_base_serializer import *
from .error import *
from .json_utils import *
from .paginated_result_metadata import *
from .result_set import *
from .v1 import *
from .v2 import *

__all__ = (
    build_info.__all__
    + configured_base_serializer.__all__
    + error.__all__
    + json_utils.__all__
    + paginated_result_metadata.__all__
    + result_set.__all__
    + v1.__all__
    + v2.__all__
)
```

### Version Serializers Export

Each version directory aggregates resource serializers:

```python
# api/serializers/v1/__init__.py
from .conveyors import *
from .loads import *

__all__ = conveyors.__all__ + loads.__all__
```

### Resource Serializers Export

Each resource directory aggregates its serializers:

```python
# api/serializers/v1/conveyors/__init__.py
from .create_conveyor import *
from .get_conveyor import *
from .get_conveyors import *

__all__ = (
    create_conveyor.__all__
    + get_conveyor.__all__
    + get_conveyors.__all__
)
```

## API Module Export

The top-level `api/__init__.py` exports all API components:

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

## Module `__all__` Convention

Each module should define `__all__` listing its public exports:

```python
# In conveyors.py
__all__ = ["conveyors_router"]

conveyors_router = APIRouter(prefix="/conveyors", ...)
```

```python
# In get_conveyor.py
__all__ = ["GetConveyorResponse"]

class GetConveyorResponse(ConfiguredResponseSerializer):
    ...
```

## Directory Structure

```
api/
├── __init__.py                    # Top-level API exports
├── auth.py
├── endpoint_marker.py
├── endpoint_visibility.py
├── error_handlers.py
├── fastapi_auth.py
├── endpoints/
│   ├── __init__.py               # Aggregates all routers
│   ├── debug.py
│   ├── healthcheck.py
│   ├── service_info.py
│   ├── internal/
│   │   ├── __init__.py           # Internal router + sub-routers
│   │   ├── conveyors.py
│   │   └── tires.py
│   ├── v1/
│   │   ├── __init__.py           # v1 router + sub-routers
│   │   ├── conveyors.py
│   │   └── loads.py
│   └── v2/
│       ├── __init__.py           # v2 router + sub-routers
│       └── loads.py
└── serializers/
    ├── __init__.py               # Aggregates all serializers
    ├── build_info.py
    ├── configured_base_serializer.py
    ├── error.py
    ├── json_utils.py
    ├── paginated_result_metadata.py
    ├── result_set.py
    ├── v1/
    │   ├── __init__.py           # v1 serializers aggregation
    │   ├── conveyors/
    │   │   ├── __init__.py       # Conveyor serializers
    │   │   ├── create_conveyor.py
    │   │   ├── get_conveyor.py
    │   │   └── get_conveyors.py
    │   └── loads/
    │       ├── __init__.py       # Load serializers
    │       └── ...
    └── v2/
        ├── __init__.py           # v2 serializers aggregation
        └── loads/
            ├── __init__.py
            └── ...
```

## Import Benefits

With proper exports, consumers can use clean imports:

```python
# Instead of:
from my_service.api.endpoints.v1.conveyors import conveyors_router
from my_service.api.serializers.v1.conveyors.get_conveyor import GetConveyorResponse

# Use:
from my_service.api import conveyors_router, GetConveyorResponse
```

## Testing Guidance

- Verify all exports are accessible from top-level modules.
- Test that `__all__` matches actual module contents.
- Ensure no circular import issues between modules.

## Common Issues

### Circular Imports

If you encounter circular imports, check the import order in `__init__.py` files. Import order matters - independent modules first, dependent modules later.

### Missing Exports

If an export isn't accessible, verify:

1. The class/function has `__all__` in its module
2. The parent `__init__.py` includes the wildcard import
3. The parent `__all__` includes the child `__all__`

### Type Checker Warnings

Use `# type: ignore` comment on the first line of files with wildcard imports to suppress type checker warnings about `import *`.
