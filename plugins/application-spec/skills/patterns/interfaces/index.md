---
name: interfaces
description: Interfaces pattern for application services. Use when defining Protocol-based abstractions for external system interactions or complex queries using the ICan* naming convention.
user-invocable: false
disable-model-invocation: false
---

# Interfaces

Purpose: Define Protocol-based interfaces for external system interactions using ICan* naming convention

## Purpose

- Define Protocol-based interfaces for external system interactions or complex queries.
- Use `ICan*` naming convention to indicate capability.
- Enable dependency injection and testability through Protocol abstraction.

## Structure

- Use `Protocol` from `typing` module.
- Name interfaces with `ICan*` prefix (e.g., `ICanUpdateLineItems`, `ICanQueryLoads`).
- Define methods with clear signatures and return types.
- Use `pass` in method bodies (Protocols don't require implementation).

## Behavior checklist

- Use descriptive method names that indicate the capability.
- Include all necessary parameters for the operation.
- Return appropriate types (DTOs, domain objects, or None).
- Export interface in `__all__`.

## Testing guidance

- Create fake implementations for testing.
- Verify interface contracts are satisfied by implementations.
- Test that Protocol-based dependency injection works correctly.

---

## Template

```python
from typing import Protocol

{% if imports %}
{% for import in imports %}
{{ import }}
{% endfor %}
{% endif %}

__all__ = ["{{ interface_name }}"]

class {{ interface_name }}(Protocol):
{% for method in methods %}
    def {{ method.name }}(
        self,
{% for param in method.parameters %}
        {{ param.name }}: {{ param.type }}{% if param.optional %} | None{% endif %},
{% endfor %}
    ) -> {{ method.return_type }}:
        pass

{% endfor %}
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ interface_name }}` | Name of the Protocol interface | `ICanQueryLoads`, `ICanStopConveyor` |
| `{{ methods }}` | List of method objects with `name`, `parameters` (list of `{name, type, optional?}`), and `return_type` | `[{"name": "stop_conveyor", "parameters": [{"name": "warehouse_id", "type": "str"}, {"name": "reason", "type": "str", "optional": true}], "return_type": "None"}]` |
| `{{ imports }}` | Optional list of import statements (full lines) | `["from tss_load_processing.domain import LoadData"]` |
