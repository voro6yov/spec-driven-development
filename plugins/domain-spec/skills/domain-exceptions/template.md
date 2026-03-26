# Domain Exceptions Template

```python
from ..shared import AlreadyExists, Conflict, DomainException, NotFound

__all__ = [
    "{{ aggregate_name }}AlreadyExists",
    "{{ aggregate_name }}NotFound",
]

class {{ aggregate_name }}AlreadyExists(AlreadyExists):
    code: str = "{{ aggregate_code }}_already_exists"

    def __init__(self, {{ id_param }}: str, {{ tenant_param }}: str):
        message = f"{{ aggregate_name }} {{{ id_param }}} already exists for {{ tenant_label }} {{{ tenant_param }}}"
        super().__init__(message)

class {{ aggregate_name }}NotFound(NotFound):
    code: str = "{{ aggregate_code }}_not_found"

    def __init__(self, {{ id_param }}: str, {{ tenant_param }}: str):
        message = f"{{ aggregate_name }} {{{ id_param }}} not found for {{ tenant_label }} {{{ tenant_param }}}"
        super().__init__(message)
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ aggregate_name }}` | PascalCase aggregate name | `Load`, `Order`, `Profile` |
| `{{ aggregate_code }}` | snake_case aggregate code | `load`, `order`, `profile` |
| `{{ id_param }}` | Parameter name for entity ID | `load_id`, `order_id`, `id_` |
| `{{ tenant_param }}` | Parameter name for tenant ID | `warehouse_id`, `tenant_id` |
| `{{ tenant_label }}` | Human label for tenant | `warehouse`, `tenant`, `organization` |

## Additional exception patterns

```python
# Child Entity NotFound (single identifier)
class ChildEntityNotFound(NotFound):
    code: str = "child_entity_not_found"

    def __init__(self, entity_id: str):
        message = f"Child entity {entity_id} not found"
        super().__init__(message)

# Child Entity NotFound (composite identifier)
class LineItemNotFound(NotFound):
    code: str = "line_item_not_found"

    def __init__(self, item_number: str, product_name: str):
        message = f"Line item {item_number} {product_name} not found"
        super().__init__(message)

# Conflict: Business Rule Violation
class ItemsShouldNotBeEmpty(Conflict):
    code: str = "items_should_not_be_empty"

    def __init__(self, load_id: str, warehouse_id: str):
        message = f"Load {load_id} items cannot be empty for warehouse {warehouse_id}"
        super().__init__(message)

# DomainException: Domain-Specific State Error
class ConveyorHasNoCurrentLoad(DomainException):
    code: str = "conveyor_has_no_current_load"

    def __init__(self, id_: str, warehouse_id: str):
        message = f"Conveyor {id_} from warehouse {warehouse_id} has no current load."
        super().__init__(message)
```
