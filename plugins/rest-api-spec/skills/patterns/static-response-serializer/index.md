---
name: static-response-serializer
description: Static Response Serializer pattern for REST API responses that expose enum values, configuration, or reference data. Use when an endpoint returns static or enum-based values without requiring domain object input.
user-invocable: false
disable-model-invocation: false
---

# Static Response Serializer

## Purpose

- Return static or enum-based values without requiring domain object input.
- Expose configuration values, supported options, or reference data via API.
- Provide `from_domain()` with no arguments for consistency with other serializers.

## Structure

- Extend `ConfiguredResponseSerializer` base class.
- Implement `from_domain()` as a classmethod with no parameters.
- Return static values, enum members, or configuration constants.

## Template Parameters

- `{{ serializer_name }}` - Name of the serializer class
- `{{ fields }}` - List of field definitions
- `{{ enum_import }}` - Import path for enum class (if applicable)
- `{{ enum_class }}` - Name of the enum class
- `{{ static_value }}` - Static value expression

## When to Use

Use static response serializers when:

- Exposing enum values as API reference data
- Returning supported options for dropdowns/selects
- Providing configuration values to clients
- API response doesn't depend on database state

## Example

### Enum-Based Static Response

```python
from my_service.domain import ReceivingLocation

from ...configured_base_serializer import ConfiguredResponseSerializer

__all__ = ["GetReceivingLocationsResponse"]

class GetReceivingLocationsResponse(ConfiguredResponseSerializer):
    receiving_locations: list[str]

    @classmethod
    def from_domain(cls) -> "GetReceivingLocationsResponse":
        return cls(receiving_locations=list(ReceivingLocation))
```

### Multiple Static Fields

```python
from my_service.domain import LoadStatus, TireStatus

from ...configured_base_serializer import ConfiguredResponseSerializer

__all__ = ["GetOptionsResponse"]

class GetOptionsResponse(ConfiguredResponseSerializer):
    load_statuses: list[str]
    tire_statuses: list[str]
    supported_formats: list[str]

    @classmethod
    def from_domain(cls) -> "GetOptionsResponse":
        return cls(
            load_statuses=[status.value for status in LoadStatus],
            tire_statuses=[status.value for status in TireStatus],
            supported_formats=["jpeg", "png", "pdf"],
        )
```

### Configuration-Based Response

```python
from my_service.constants import SUPPORTED_WAREHOUSES, MAX_FILE_SIZE

from ...configured_base_serializer import ConfiguredResponseSerializer

__all__ = ["GetConfigurationResponse"]

class GetConfigurationResponse(ConfiguredResponseSerializer):
    supported_warehouses: list[str]
    max_file_size_bytes: int
    api_version: str

    @classmethod
    def from_domain(cls) -> "GetConfigurationResponse":
        return cls(
            supported_warehouses=SUPPORTED_WAREHOUSES,
            max_file_size_bytes=MAX_FILE_SIZE,
            api_version="2.0.0",
        )
```

## Endpoint Usage

Static response endpoints typically don't require dependency injection:

```python
@router.get(
    "/receiving-locations",
    status_code=status.HTTP_200_OK,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=GetReceivingLocationsResponse,
)
@inject
def get_receiving_locations():
    return GetReceivingLocationsResponse.from_domain()
```

Note: The `@inject` decorator is kept for consistency but no dependencies are injected.

## Comparison with Regular Response Serializers

| Aspect | Regular Response | Static Response |
| --- | --- | --- |
| `from_domain()` params | Domain object | None |
| Data source | Database/domain | Enums/constants |
| Caching potential | Varies | Highly cacheable |
| Testing | Requires mocks | No mocks needed |

## Testing Guidance

- Test `from_domain()` returns expected static values.
- Verify enum values are correctly serialized.
- Test camelCase serialization in JSON output.
- No mocking required - test actual enum/constant values.

### Test Example

```python
def test_get_receiving_locations():
    response = GetReceivingLocationsResponse.from_domain()
    
    assert response.receiving_locations == ["DOCK_A", "DOCK_B", "DOCK_C"]

def test_get_options_response():
    response = GetOptionsResponse.from_domain()
    
    assert "pending" in response.load_statuses
    assert "jpeg" in response.supported_formats
```

---

## Template

```python
{% if enum_imports %}
{% for enum_import in enum_imports %}
from {{ enum_import.module }} import {{ enum_import.class }}
{% endfor %}
{% endif %}

from {{ base_serializer_module }} import ConfiguredResponseSerializer

__all__ = ["{{ serializer_name }}"]

class {{ serializer_name }}(ConfiguredResponseSerializer):
{% for field in fields %}
    {{ field.name }}: {{ field.type }}
{% endfor %}

    @classmethod
    def from_domain(cls) -> "{{ serializer_name }}":
        return cls(
{% for mapping in field_mappings %}
            {{ mapping.field }}={{ mapping.value }},
{% endfor %}
        )
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ serializer_name }}` | Name of the serializer class | `GetReceivingLocationsResponse` |
| `{{ base_serializer_module }}` | Import path for base serializer | `...configured_base_serializer` |
| `{{ enum_imports }}` | List of enum imports | `[{"module": "my_service.domain", "class": "LoadStatus"}]` |
| `{{ fields }}` | List of field definitions | `[{"name": "statuses", "type": "list[str]"}]` |
| `{{ field_mappings }}` | Field to value mappings | `[{"field": "statuses", "value": "list(LoadStatus)"}]` |
