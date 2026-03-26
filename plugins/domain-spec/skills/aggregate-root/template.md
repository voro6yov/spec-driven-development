# Aggregate Root Template

```python
from datetime import datetime

from ..shared import Command, Entity, Event, Guard, ImmutableCheck
from .value_objects import {{ info_value_object }}
from .collection_value_objects import {{ collection_value_object }}
from .dtos import {{ data_dto }}
from .events import {{ created_event }}, {{ changes_event }}

class {{ aggregate_name }}(metaclass=Entity):
    id = Guard[str](str, ImmutableCheck())
    tenant_id = Guard[str](str, ImmutableCheck())
    info = Guard[{{ info_value_object }}]({{ info_value_object }}, ImmutableCheck())
    items = Guard[{{ collection_value_object }}]({{ collection_value_object }}, ImmutableCheck())
    created_at = Guard[datetime](datetime, ImmutableCheck())
    updated_at = Guard[datetime](datetime)

    def __init__(
        self,
        id_: str,
        tenant_id: str,
        info: {{ info_value_object }},
        items: {{ collection_value_object }},
        created_at: datetime,
        updated_at: datetime,
        *,
        events: list[Event] | None = None,
        commands: list[Command] | None = None,
    ) -> None:
        self.id = id_
        self.tenant_id = tenant_id
        self.info = info
        self.items = items
        self.created_at = created_at
        self.updated_at = updated_at

        self.events = events or []
        self.commands = commands or []

    @classmethod
    def from_data(cls, tenant_id: str, data: {{ data_dto }}) -> "{{ aggregate_name }}":
        aggregate = cls(
            id_=data["id"],
            tenant_id=tenant_id,
            info={{ info_value_object }}.from_data(data),
            items={{ collection_value_object }}.from_data(data.get("items")),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            events=[
                {{ created_event }}(
                    aggregate_id=data["id"],
                    tenant_id=tenant_id,
                    source=data["source"],
                ),
            ],
        )

        aggregate._seed_items(data.get("items"))

        return aggregate

    def _seed_items(self, raw_items: list[dict[str, str]] | None) -> None:
        if not raw_items:
            return

        for item in raw_items:
            self.add_item(
                item_number=item["item_number"],
                description=item["description"],
                quantity=item["quantity"],
            )

    def add_item(self, item_number: str, description: str, quantity: int) -> None:
        self.items.add_item(item_number, description, quantity, self)
        self.updated_at = datetime.now()

    def add_collection_changes(self, changes: list[dict]) -> None:
        self.events.append(
            {{ changes_event }}(
                aggregate_id=self.id,
                tenant_id=self.tenant_id,
                changes=changes,
            )
        )
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ aggregate_name }}` | Name of your aggregate class | `OrderAggregate`, `ProfileAggregate` |
| `{{ info_value_object }}` | Value object for descriptive information | `OrderInfo`, `ProfileInfo` |
| `{{ collection_value_object }}` | Collection managing child entities | `OrderItems`, `ProfileAddresses` |
| `{{ data_dto }}` | Input DTO for factory constructor | `OrderData`, `ProfileData` |
| `{{ created_event }}` | Domain event emitted on creation | `OrderCreated`, `ProfileCreated` |
| `{{ changes_event }}` | Domain event for collection changes | `OrderItemsChanged`, `ProfileAddressesChanged` |
