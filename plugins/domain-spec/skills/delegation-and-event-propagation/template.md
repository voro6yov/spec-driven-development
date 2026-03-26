# Delegation and Event Propagation Template

```python
from datetime import datetime
from typing import Callable

from ..shared import Event
from .events import {{ event_name }}

def delegate_event(aggregate: "{{ aggregate_name }}", build_event: Callable[[], Event]) -> None:
    event = build_event()
    aggregate.events.append(event)
    aggregate.updated_at = datetime.now()

class {{ collaborator_name }}:
    def __init__(self) -> None:
        self.state: dict[str, str] = {}

    def handle(self, reference: str, aggregate: "{{ aggregate_name }}") -> None:
        self.state[reference] = "processed"
        delegate_event(
            aggregate,
            lambda: {{ event_name }}(
                aggregate_id=aggregate.id,
                tenant_id=aggregate.tenant_id,
                reference=reference,
            ),
        )
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ aggregate_name }}` | Owning aggregate type | `Load`, `Order` |
| `{{ collaborator_name }}` | Collaborator class name | `ItemsProcessor`, `AddressValidator` |
| `{{ event_name }}` | Event emitted by collaborator | `ItemProcessed`, `AddressValidated` |

## Example

```python
from datetime import datetime
from typing import Callable
from ..shared import Event
from .events import OrderItemAdded

def delegate_event(aggregate: "Order", build_event: Callable[[], Event]) -> None:
    event = build_event()
    aggregate.events.append(event)
    aggregate.updated_at = datetime.now()

class OrderItemsProcessor:
    def __init__(self) -> None:
        self.pending_items: list[str] = []

    def add_item(self, item_number: str, aggregate: "Order") -> None:
        self.pending_items.append(item_number)
        delegate_event(
            aggregate,
            lambda: OrderItemAdded(
                aggregate_id=aggregate.id,
                tenant_id=aggregate.tenant_id,
                item_number=item_number,
            ),
        )
```
