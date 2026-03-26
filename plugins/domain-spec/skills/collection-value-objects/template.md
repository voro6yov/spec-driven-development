# Collection Value Objects Template

```python
from typing import TYPE_CHECKING

from ..shared import Guard, ImmutableCheck, ValueObject
from .entities import {{ entity_name }}
from .events import {{ overage_event }}
from .exceptions import {{ missing_exception }}, {{ overage_exception }}

if TYPE_CHECKING:
    from .aggregates import {{ aggregate_name }}

class {{ collection_value_object }}(metaclass=ValueObject):
    items = Guard[dict[str, {{ entity_name }}]](dict, ImmutableCheck())
    overages = Guard[dict[str, dict]](dict, ImmutableCheck())
    changes = Guard[list[dict]](list)

    BATCH_SIZE: int = 10

    def __init__(
        self,
        items: list[{{ entity_name }}] | None,
        overages: list[dict] | None,
        changes: list[dict] | None,
    ) -> None:
        self.items = {}
        if items:
            for item in items:
                self.items[item.id] = item

        self.overages = {}
        if overages:
            for overage in overages:
                self.overages[overage["reference"]] = overage

        self.changes = changes or []

    @classmethod
    def new(cls) -> "{{ collection_value_object }}":
        return cls(items=None, overages=None, changes=None)

    @classmethod
    def from_data(cls, raw_items: list[dict] | None) -> "{{ collection_value_object }}":
        if not raw_items:
            return cls.new()

        return cls(
            items=[
                {{ entity_name }}(
                    reference=item["reference"],
                    description=item["description"],
                    planned_quantity=item["planned_quantity"],
                    actual_quantity=item.get("actual_quantity", 0),
                    status=item.get("status", {{ entity_name }}.WAITING),
                    related_ids=item.get("related_ids", []),
                )
                for item in raw_items
            ],
            overages=None,
            changes=None,
        )

    def add_item(self, reference: str, description: str, planned_quantity: int, aggregate: "{{ aggregate_name }}") -> None:
        self.items[reference] = {{ entity_name }}.new(reference, description, planned_quantity)
        self.record_change(self.items[reference])
        self._flush_if_needed(aggregate)

    def increment(self, reference: str, related_id: str, aggregate: "{{ aggregate_name }}") -> None:
        item = self._find_available_item(reference)
        if item is not None:
            item.increment(related_id, self)
            self._flush_if_needed(aggregate)
            return

        self.overages[related_id] = {
            "reference": reference,
            "status": "waiting",
        }

        aggregate.events.append(
            {{ overage_event }}(
                aggregate_id=aggregate.id,
                tenant_id=aggregate.tenant_id,
                reference=reference,
                related_id=related_id,
            )
        )

    def confirm_overage(self, related_id: str, aggregate: "{{ aggregate_name }}") -> None:
        overage = self._get_overage(related_id)
        overage["status"] = "confirmed"

        item = self._get_item(overage["reference"])
        item.increment(related_id, self)
        self._flush_if_needed(aggregate)

    def defer_overage(self, related_id: str) -> None:
        overage = self._get_overage(related_id)
        overage["status"] = "deferred"

    def associate(self, reference: str, related_id: str, aggregate: "{{ aggregate_name }}") -> None:
        item = self._get_item(reference)
        item.increment(related_id, self)
        self._flush_if_needed(aggregate)

    def record_change(self, item: {{ entity_name }}) -> None:
        self.changes.append(
            {
                "reference": item.reference,
                "description": item.description,
                "planned_quantity": item.planned_quantity,
                "actual_quantity": item.actual_quantity,
                "status": item.status,
            }
        )

    def pop_changes(self) -> list[dict]:
        changes = self.changes
        self.changes = []
        return changes

    def _get_item(self, reference: str) -> {{ entity_name }}:
        item = self.items.get(reference)
        if item is None:
            raise {{ missing_exception }}(reference)
        return item

    def _get_overage(self, related_id: str) -> dict:
        overage = self.overages.get(related_id)
        if overage is None:
            raise {{ overage_exception }}(related_id)
        return overage

    def _find_available_item(self, reference: str) -> {{ entity_name }} | None:
        for item in self.items.values():
            if item.reference == reference and not item.is_completed:
                return item
        return None

    def _flush_if_needed(self, aggregate: "{{ aggregate_name }}") -> None:
        if len(self.changes) >= self.BATCH_SIZE:
            changes = self.changes
            self.changes = []
            aggregate.add_collection_changes(changes)
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ collection_value_object }}` | Name of collection class | `OrderItems`, `ProfileAddresses` |
| `{{ entity_name }}` | Child entity type | `LineItem`, `Address` |
| `{{ aggregate_name }}` | Owning aggregate type | `Order`, `Profile` |
| `{{ overage_event }}` | Event for overages | `ItemOverage`, `AddressOverage` |
| `{{ missing_exception }}` | Exception when item not found | `LineItemNotFound`, `AddressNotFound` |
| `{{ overage_exception }}` | Exception when overage not found | `OverageNotFound` |
