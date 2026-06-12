# Domain Events Template

```python
from dataclasses import dataclass

from ..shared import Event

@dataclass
class {{ event_name }}(Event):
    aggregate_id: str
    tenant_id: str
    context_id: str
    payload: dict[str, str]
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ event_name }}` | Past-tense event name | `OrderCreated`, `ProfileUpdated`, `ItemAdded` |

## Examples

```python
@dataclass
class OrderCreated(Event):
    aggregate_id: str
    tenant_id: str
    order_number: str
    created_at: str

@dataclass
class OrderItemAdded(Event):
    aggregate_id: str
    tenant_id: str
    item_number: str
    quantity: int

@dataclass
class OrderCompleted(Event):
    aggregate_id: str
    tenant_id: str
    completed_at: str
```
