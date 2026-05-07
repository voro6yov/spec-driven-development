---
name: fake-implementations
description: Fake Implementations pattern for application-layer Protocol interfaces. Use when creating lightweight test doubles to isolate application services from external systems and capture method calls for assertion.
user-invocable: false
disable-model-invocation: false
---

# Fake Implementations

Purpose: Provide lightweight test doubles for Protocol interfaces to enable isolation testing

## Purpose

- Provide lightweight test doubles for Protocol interfaces.
- Enable isolation testing by replacing external system interactions.
- Capture method calls for assertion verification without complex mocking.
- Support test reset between test cases for isolation.

## Structure

- Inherit from the Protocol interface being faked.
- Initialize tracking collections (lists/dicts) in `__init__`.
- Implement interface methods to capture call arguments.
- Provide `reset()` method to clear state between tests.
- Export fake class in `__all__`.

## Behavior Checklist

- Use list of tuples to track method calls with all arguments.
- For methods whose return type is `None`, do not return anything — record the call only.
- For methods with a non-`None` return type, **never return a bare `None`**. Bare `None` poisons the application service's success path (e.g. a missing `evo_version` becomes `IllegalArgument` deep inside the aggregate factory). Instead, expose a configurable per-method seed with two safe outcomes:
    1. A `set_<method>_return(value)` setter that overrides the default.
    2. A method body that returns the seeded value if set; otherwise raises `NotImplementedError(f"Fake<X>.<method> has no configured return value — call set_<method>_return(...) before invoking, or override the default in __init__.")`. This fails loud at the call site instead of cascading a `None` through the success path.
- Initialize `self._<method>_return: <ReturnType> | _Sentinel = _UNSET` in `__init__`. The `reset()` method clears both call lists and configured returns.
- Keep implementation minimal — capture calls, raise loud on misconfiguration, don't add complex logic.
- Name tracking attributes as `{method_name}_calls`.
- Implement all Protocol methods.

## Template Variables

When using the template, provide these variables:

- `interface_name` - Protocol interface to fake (e.g., `ICanStopConveyor`)
- `interface_module` - Module path for interface import (e.g., `tss_load_processing.application`)
- `fake_class_name` - Name of fake class (e.g., `FakeConveyorClient`)
- `methods` - List of method objects:
    - `name` - method name
    - `parameters` - List of `{name, type}` objects
    - `return_type` - return type string (e.g., `None`, `dict`)
    - `tracking_attr` - attribute name for call tracking (e.g., `stop_conveyor_calls`)
    - `default_return` - optional default return value for non-None returns

## Examples

### Simple Fake (void methods)

```python
from tss_load_processing.application import ICanStopConveyor

__all__ = ["FakeConveyorClient"]

class FakeConveyorClient(ICanStopConveyor):
    def __init__(self):
        self.stop_conveyor_calls: list[tuple[str, str, str | None]] = []

    def stop_conveyor(self, warehouse_id: str, conveyor_id: str, reason: str | None = None) -> None:
        self.stop_conveyor_calls.append((warehouse_id, conveyor_id, reason))

    def reset(self) -> None:
        self.stop_conveyor_calls.clear()
```

### Fake with Return Values (configurable seed pattern)

```python
from tss_load_processing.application import ICanIdentifyEvoVersion

__all__ = ["FakeEvoVersionIdentifier"]

_UNSET = object()


class FakeEvoVersionIdentifier(ICanIdentifyEvoVersion):
    def __init__(self):
        self.identify_evo_version_calls: list[tuple[str]] = []
        self._identify_evo_version_return: object = _UNSET

    def identify_evo_version(self, conversion_reqs_id: str) -> str:
        self.identify_evo_version_calls.append((conversion_reqs_id,))
        if self._identify_evo_version_return is _UNSET:
            raise NotImplementedError(
                "FakeEvoVersionIdentifier.identify_evo_version has no configured return value — "
                "call set_identify_evo_version_return(...) before invoking, "
                "or override the default in __init__."
            )
        return self._identify_evo_version_return  # type: ignore[return-value]

    def set_identify_evo_version_return(self, value: str) -> None:
        self._identify_evo_version_return = value

    def reset(self) -> None:
        self.identify_evo_version_calls.clear()
        self._identify_evo_version_return = _UNSET
```

The `_UNSET` sentinel + `NotImplementedError` is intentional: a bare `None` would silently propagate into the application service and surface as a confusing aggregate-factory error far from the test, while the explicit raise points the author straight at the missing seed.

### Fake with Default Return (lookup-style)

When a method's contract is "return what was set, default empty," prefer storing real values:

```python
from tss_load_processing.application import ICanGetLoadDetails

__all__ = ["FakeLoadDetailsRepository"]

class FakeLoadDetailsRepository(ICanGetLoadDetails):
    def __init__(self):
        self.load_of_id_calls: list[tuple[str, str]] = []
        self._loads: dict[tuple[str, str], dict] = {}

    def load_of_id(self, load_id: str, warehouse_id: str) -> dict | None:
        self.load_of_id_calls.append((load_id, warehouse_id))
        return self._loads.get((load_id, warehouse_id))

    def add_load(self, load_id: str, warehouse_id: str, load_data: dict) -> None:
        self._loads[(load_id, warehouse_id)] = load_data

    def reset(self) -> None:
        self.load_of_id_calls.clear()
        self._loads.clear()
```

This shape is appropriate when the method's return type is `Optional[T]` and the contract explicitly allows `None` to mean "not found." For non-optional return types, use the configurable seed pattern above.

### Fake with Error Simulation

```python
from tss_load_processing.application import ICanUpdateLineItems
from tss_load_processing.domain import LoadNotFound

__all__ = ["FakeD365Client"]

class FakeD365Client(ICanUpdateLineItems):
    def __init__(self):
        self.update_line_items_calls: list[tuple[str, str, list]] = []
        self._should_fail: bool = False
        self._fail_load_id: str | None = None

    def update_line_items(self, load_id: str, warehouse_id: str, changes: list) -> None:
        self.update_line_items_calls.append((load_id, warehouse_id, changes))
        if self._should_fail and (self._fail_load_id is None or self._fail_load_id == load_id):
            raise LoadNotFound(load_id, warehouse_id)

    def simulate_failure(self, load_id: str | None = None) -> None:
        self._should_fail = True
        self._fail_load_id = load_id

    def reset(self) -> None:
        self.update_line_items_calls.clear()
        self._should_fail = False
        self._fail_load_id = None
```

## File Organization

Place fakes in `tests/fakes/` directory:

```
tests/
  fakes/
    __init__.py
    fake_conveyor_client.py
    fake_d365_client.py
    fake_load_details_repository.py
    fake_tire_identification.py
```

Export all fakes from `__init__.py`:

```python
from .fake_conveyor_client import *
from .fake_d365_client import *
from .fake_load_details_repository import *
from .fake_tire_identification import *

__all__ = (
    fake_conveyor_client.__all__
    + fake_d365_client.__all__
    + fake_load_details_repository.__all__
    + fake_tire_identification.__all__
)
```

## Testing Guidance

- Wire fakes into DI container via fixture overrides.
- Use session-scoped fixtures for fake creation, per-test fixtures for reset.
- Assert on call tracking attributes after test execution.
- Verify call counts, argument values, and call order as needed.
- Use `simulate_failure()` helpers to test error paths.

---

## Template

```python
{# Template for fake implementation of a Protocol interface #}
{# Variables:
   - interface_name: Name of the Protocol interface (e.g., ICanStopConveyor)
   - interface_module: Module path to import interface from (e.g., tss_load_processing.application)
   - fake_class_name: Name of the fake class (e.g., FakeConveyorClient)
   - methods: List of method objects with:
     - name: method name
     - parameters: List of parameter objects with name and type
     - return_type: return type (e.g., None, str, dict). When non-None, an
       _UNSET sentinel is rendered and the method raises NotImplementedError
       until set_<name>_return(...) is called by the test.
     - tracking_attr: attribute name to track calls (e.g., stop_conveyor_calls)
#}
from {{ interface_module }} import {{ interface_name }}

__all__ = ["{{ fake_class_name }}"]

{% set has_returns = methods | selectattr('return_type', 'ne', 'None') | list | length > 0 %}
{% if has_returns %}
_UNSET = object()
{% endif %}


class {{ fake_class_name }}({{ interface_name }}):
    def __init__(self) -> None:
{% for method in methods %}
        self.{{ method.tracking_attr }}: list[tuple[{% if method.parameters %}{{ method.parameters | map(attribute='type') | join(', ') }}{% else %}(){% endif %}]] = []
{% if method.return_type != 'None' %}
        self._{{ method.name }}_return: object = _UNSET
{% endif %}
{% endfor %}

{% for method in methods %}
    def {{ method.name }}(self{% for param in method.parameters %}, {{ param.name }}: {{ param.type }}{% endfor %}) -> {{ method.return_type }}:
        self.{{ method.tracking_attr }}.append(({% for param in method.parameters %}{{ param.name }}{% if not loop.last %}, {% endif %}{% endfor %}))
{% if method.return_type != 'None' %}
        if self._{{ method.name }}_return is _UNSET:
            raise NotImplementedError(
                "{{ fake_class_name }}.{{ method.name }} has no configured return value — "
                "call set_{{ method.name }}_return(...) before invoking, "
                "or override the default in __init__."
            )
        return self._{{ method.name }}_return  # type: ignore[return-value]
{% endif %}

{% if method.return_type != 'None' %}
    def set_{{ method.name }}_return(self, value: {{ method.return_type }}) -> None:
        self._{{ method.name }}_return = value

{% endif %}
{% endfor %}
    def reset(self) -> None:
{% for method in methods %}
        self.{{ method.tracking_attr }}.clear()
{% if method.return_type != 'None' %}
        self._{{ method.name }}_return = _UNSET
{% endif %}
{% endfor %}
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ interface_name }}` | Protocol interface to fake | `ICanStopConveyor`, `ICanGetLoadDetails` |
| `{{ interface_module }}` | Module path for interface import | `tss_load_processing.application` |
| `{{ fake_class_name }}` | Name of fake class | `FakeConveyorClient`, `FakeLoadDetailsRepository` |
| `{{ methods }}` | List of method objects with `name`, `parameters` (list of `{name, type}`), `return_type`, `tracking_attr`, and optional `default_return` | `[{"name": "stop_conveyor", "parameters": [{"name": "warehouse_id", "type": "str"}, {"name": "conveyor_id", "type": "str"}], "return_type": "None", "tracking_attr": "stop_conveyor_calls"}]` |
