# Entity Template

```python
from ..shared import Entity, Guard, ImmutableCheck

class {{ entity_name }}(metaclass=Entity):
    reference = Guard[str](str, ImmutableCheck())
    description = Guard[str](str, ImmutableCheck())
    planned_quantity = Guard[int](int)
    actual_quantity = Guard[int](int)
    status = Guard[str](str)
    related_ids = Guard[list[str]](list, ImmutableCheck())

    WAITING: str = "waiting"
    IN_PROGRESS: str = "inProgress"
    COMPLETED: str = "completed"
    OVERAGE: str = "overage"
    SHORTAGE: str = "shortage"

    def __init__(
        self,
        reference: str,
        description: str,
        planned_quantity: int,
        actual_quantity: int,
        status: str,
        related_ids: list[str] | None,
    ) -> None:
        self.id = reference
        self.reference = reference
        self.description = description
        self.planned_quantity = planned_quantity
        self.actual_quantity = actual_quantity
        self.status = status
        self.related_ids = related_ids or []

    @classmethod
    def new(cls, reference: str, description: str, planned_quantity: int) -> "{{ entity_name }}":
        return cls(reference, description, planned_quantity, 0, cls.WAITING, [])

    @property
    def is_completed(self) -> bool:
        return self.status == self.COMPLETED

    def increment(self, related_id: str, collection: "{{ collection_type }}") -> None:
        self.actual_quantity += 1

        if self.actual_quantity == self.planned_quantity:
            self.status = self.COMPLETED
        elif self.actual_quantity > self.planned_quantity:
            self.status = self.OVERAGE
        else:
            self.status = self.IN_PROGRESS

        self.related_ids.append(related_id)
        collection.record_change(self)

    def disassociate(self, related_id: str, collection: "{{ collection_type }}") -> None:
        self.related_ids.remove(related_id)
        self.actual_quantity -= 1

        if self.actual_quantity < self.planned_quantity:
            self.status = self.SHORTAGE
        elif self.actual_quantity == self.planned_quantity:
            self.status = self.COMPLETED
        else:
            self.status = self.OVERAGE

        collection.record_change(self)
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ entity_name }}` | Name of your entity class | `LineItem`, `OrderItem` |
| `{{ collection_type }}` | Parent collection type for callbacks | `LineItems`, `OrderItems` |
