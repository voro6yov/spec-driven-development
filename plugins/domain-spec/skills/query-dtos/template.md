# Query DTOs Template

```python
from typing import TypedDict

class {{ dto_name }}(TypedDict, total=False):
    id: str
    tenant_id: str
    status: str
    items: list[dict[str, str]]

class {{ dto_collection_name }}(TypedDict):
    items: list[{{ dto_name }}]
    metadata: dict[str, int]
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ dto_name }}` | Single item DTO name | `LoadData`, `OrderData`, `ProfileData` |
| `{{ dto_collection_name }}` | Collection DTO name | `LoadsInfo`, `OrdersInfo`, `ProfilesInfo` |

## Examples

```python
from typing import TypedDict

class OrderData(TypedDict, total=False):
    id: str
    tenant_id: str
    customer_name: str
    status: str
    items: list[dict[str, str]]
    created_at: str

class OrderInfo(TypedDict):
    id: str
    tenant_id: str
    order_number: str
    total_amount: float
    status: str

class OrdersInfo(TypedDict):
    items: list[OrderInfo]
    metadata: dict[str, int]
```
