---
name: endpoint-marker
description: Endpoint Marker pattern for REST API endpoints. Use when customizing OpenAPI summaries to prepend visibility levels and convert function names to human-readable titles.
user-invocable: false
disable-model-invocation: false
---

# Endpoint Marker

## Purpose

- Customize OpenAPI summary generation for endpoints.
- Prepend visibility level to endpoint names.
- Convert function names to human-readable titles.

## Structure

- Custom `APIRoute` subclass.
- Override `__init__` to modify summary.
- Transform function names: `get_conveyor` → `Get Conveyor`.
- Prepend visibility: `[Public] Get Conveyor`.

## Template Parameters

- `{{ visibility_enum_module }}` - Import path for Visibility enum

## Example

```python
import inspect

from fastapi.routing import APIRoute

__all__ = ["MarkerRoute"]

class MarkerRoute(APIRoute):
    def __init__(self, *args, **kwargs) -> None:
        if inspect.isroutine(kwargs["endpoint"]) or inspect.isclass(kwargs["endpoint"]):
            name = kwargs["endpoint"].__name__
        else:
            name = kwargs["endpoint"].__class__.__name__

        endpoint_name = name.replace("_", " ").title()

        if kwargs.get("openapi_extra"):
            visibility = kwargs["openapi_extra"]["visibility"]
            kwargs["summary"] = f"[{visibility.value}] {endpoint_name}"

        super().__init__(*args, **kwargs)
```

## How It Works

1. **Extract endpoint name**: Get the function or class name from the endpoint.
2. **Format as title**: Replace underscores with spaces and title-case.
3. **Check for visibility**: If `openapi_extra` contains visibility, use it.
4. **Set summary**: Create summary with format `[Visibility] Endpoint Name`.

## Usage

Apply to routers that should have visibility markers:

```python
from fastapi import APIRouter

from ..endpoint_marker import MarkerRoute

router = APIRouter(
    prefix="/resources",
    tags=["Resources"],
    route_class=MarkerRoute,  # Apply marker route
)
```

## Result in OpenAPI

Without MarkerRoute:

- Summary: `get_conveyor`

With MarkerRoute and visibility:

- Summary: `[Public] Get Conveyor`

## Testing Guidance

- Test that function names are correctly converted to titles.
- Test that visibility is prepended to summary.
- Test endpoints without visibility have default summary.
- Test with both function and class-based endpoints.

---

## Template

```python
import inspect

from fastapi.routing import APIRoute

__all__ = ["MarkerRoute"]

class MarkerRoute(APIRoute):
    def __init__(self, *args, **kwargs) -> None:
        if inspect.isroutine(kwargs["endpoint"]) or inspect.isclass(kwargs["endpoint"]):
            name = kwargs["endpoint"].__name__
        else:
            name = kwargs["endpoint"].__class__.__name__

        endpoint_name = name.replace("_", " ").title()

        if kwargs.get("openapi_extra"):
            visibility = kwargs["openapi_extra"]["visibility"]
            kwargs["summary"] = f"[{visibility.value}] {endpoint_name}"

        super().__init__(*args, **kwargs)
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| (None) | This template has no required placeholders | - |

Note: This pattern is typically used as-is without modification. The visibility enum is accessed via the `openapi_extra` passed to each endpoint.
