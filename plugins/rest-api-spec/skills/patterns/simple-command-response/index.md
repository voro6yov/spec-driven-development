---
name: simple-command-response
description: Simple Command Response pattern for REST API command/action endpoints. Use when defining minimal confirmation response serializers that return only a resource identifier (or minimal fields) after a successful command execution.
user-invocable: false
disable-model-invocation: false
---

# Simple Command Response

## Purpose

- Return minimal confirmation responses for command/action endpoints.
- Confirm successful execution with resource identifier only.
- Maintain consistency across all command action endpoints.

## Structure

- Extend `ConfiguredResponseSerializer` base class.
- Define single `id` field (or minimal identifying fields).
- Implement `from_domain()` extracting only the identifier.

## When to Use

Use simple command response serializers when:

- Command endpoint performs an action but doesn't need to return full resource data
- Client only needs confirmation that action succeeded
- Reducing response payload size for high-frequency operations
- Action result is implicit in successful execution (e.g., "pause" means status is now "paused")

## Example

### Basic ID-Only Response

```python
from my_service.domain import Load

from ...configured_base_serializer import ConfiguredResponseSerializer

__all__ = ["CloseLoadResponse"]

class CloseLoadResponse(ConfiguredResponseSerializer):
    id: str

    @classmethod
    def from_domain(cls, load: Load) -> "CloseLoadResponse":
        return cls(id=load.id)
```

### Multiple Command Responses in One File

When a resource has many command actions, group responses together:

```python
from my_service.domain import Load

from ...configured_base_serializer import ConfiguredResponseSerializer

__all__ = [
    "StartReceivingResponse",
    "PauseReceivingResponse",
    "ResumeReceivingResponse",
    "FinishUnloadingResponse",
    "CloseLoadResponse",
    "EnableBypassModeResponse",
    "DisableBypassModeResponse",
]

class StartReceivingResponse(ConfiguredResponseSerializer):
    id: str

    @classmethod
    def from_domain(cls, load: Load) -> "StartReceivingResponse":
        return cls(id=load.id)

class PauseReceivingResponse(ConfiguredResponseSerializer):
    id: str

    @classmethod
    def from_domain(cls, load: Load) -> "PauseReceivingResponse":
        return cls(id=load.id)

class ResumeReceivingResponse(ConfiguredResponseSerializer):
    id: str

    @classmethod
    def from_domain(cls, load: Load) -> "ResumeReceivingResponse":
        return cls(id=load.id)

class FinishUnloadingResponse(ConfiguredResponseSerializer):
    id: str

    @classmethod
    def from_domain(cls, load: Load) -> "FinishUnloadingResponse":
        return cls(id=load.id)

class CloseLoadResponse(ConfiguredResponseSerializer):
    id: str

    @classmethod
    def from_domain(cls, load: Load) -> "CloseLoadResponse":
        return cls(id=load.id)

class EnableBypassModeResponse(ConfiguredResponseSerializer):
    id: str

    @classmethod
    def from_domain(cls, load: Load) -> "EnableBypassModeResponse":
        return cls(id=load.id)

class DisableBypassModeResponse(ConfiguredResponseSerializer):
    id: str

    @classmethod
    def from_domain(cls, load: Load) -> "DisableBypassModeResponse":
        return cls(id=load.id)
```

### Response with Additional Context

When the client needs slightly more than just ID:

```python
from my_service.domain import Tire

from ...configured_base_serializer import ConfiguredResponseSerializer

__all__ = ["RetryFailedTireResponse"]

class RetryFailedTireResponse(ConfiguredResponseSerializer):
    id: str
    status: str

    @classmethod
    def from_domain(cls, tire: Tire) -> "RetryFailedTireResponse":
        return cls(id=tire.id, status=tire.status.value)
```

## Response Inheritance Pattern

For command responses that share the same structure, use inheritance:

```python
from my_service.domain import Tire

from ...configured_base_serializer import ConfiguredResponseSerializer

class BaseTireActionResponse(ConfiguredResponseSerializer):
    id: str

    @classmethod
    def from_domain(cls, tire: Tire) -> "BaseTireActionResponse":
        return cls(id=tire.id)

class ConfirmTireResponse(BaseTireActionResponse):
    pass

class DeferTireResponse(BaseTireActionResponse):
    pass

class RetryTireResponse(BaseTireActionResponse):
    pass
```

## File Organization

### Option 1: Grouped by Resource Action Type

```
serializers/v2/loads/
├── __init__.py
├── get_load_response.py           # Complex GET response
├── query_loads.py                 # List/query response
├── start_receiving_response.py    # Individual action
├── pause_receiving_response.py
└── load_action_responses.py       # OR: Group all simple responses
```

### Option 2: All Actions in Single File

```
serializers/v2/loads/
├── __init__.py
├── get_load_response.py
├── query_loads.py
└── action_responses.py            # All command responses
```

## Comparison with Full Response Serializers

| Aspect | Simple Command Response | Full Response |
| --- | --- | --- |
| Fields | 1-2 (ID, status) | Many (full resource) |
| Use case | Action confirmation | Resource retrieval |
| Payload size | Minimal | Full |
| Client needs | Just confirmation | Full data refresh |

## When to Return Full Response Instead

Consider returning a full response serializer when:

- Client will need to refresh UI with new state anyway
- Action result is complex and needs multiple fields
- Reducing round trips is more important than payload size
- Action creates new data the client needs immediately

## Testing Guidance

- Test `from_domain()` extracts correct ID.
- Test JSON serialization uses camelCase.
- Verify all command responses follow consistent pattern.

### Test Example

```python
def test_close_load_response():
    load = Load(id="LD001", ...)
    
    response = CloseLoadResponse.from_domain(load)
    
    assert response.id == "LD001"
    assert response.model_dump(by_alias=True) == {"id": "LD001"}
```

---

## Template

```python
from {{ domain_module }} import {{ domain_class }}

from ...configured_base_serializer import ConfiguredResponseSerializer

__all__ = [
{% for response in responses %}
    "{{ response.class_name }}",
{% endfor %}
]

{% for response in responses %}

class {{ response.class_name }}(ConfiguredResponseSerializer):
    id: str

    @classmethod
    def from_domain(cls, {{ response.domain_var }}: {{ domain_class }}) -> "{{ response.class_name }}":
        return cls(id={{ response.domain_var }}.id)
{% endfor %}
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ domain_module }}` | Domain layer module | `my_service.domain` |
| `{{ domain_class }}` | Domain entity class | `Load` |
| `{{ responses }}` | List of response definitions | See below |

### Response Definition Structure

```python
{
    "class_name": "StartReceivingResponse",
    "domain_var": "load"
}
```
