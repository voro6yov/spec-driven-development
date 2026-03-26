# Flat Constructor Arguments Template

```python
class {{ aggregate_name }}(metaclass=Entity):
    id = Guard[str](str, ImmutableCheck())
    tenant_id = Guard[str](str, ImmutableCheck())
    info = Guard[{{ info_value_object }}]({{ info_value_object }}, ImmutableCheck())
    items = Guard[{{ collection_value_object }}]({{ collection_value_object }}, ImmutableCheck())
    bypass_mode = Guard[bool](bool)
    created_at = Guard[datetime](datetime, ImmutableCheck())
    updated_at = Guard[datetime](datetime)

    def __init__(
        self,
        # 1. Identity
        id_: str,
        tenant_id: str,
        # 2. {{ info_value_object }} components (flat)
        number_of_units: int,
        eta: datetime,
        status: str,
        started_at: datetime | None,
        # 3. {{ collection_value_object }} components (flat)
        items: list[{{ entity_name }}] | None,
        changes: list[dict] | None,
        # 4. Primitives
        bypass_mode: bool,
        # 5. Timestamps
        created_at: datetime,
        updated_at: datetime,
        # 6. Infrastructure (keyword-only, with defaults)
        *,
        events: list[Event] | None = None,
        commands: list[Command] | None = None,
    ) -> None:
        self.id = id_
        self.tenant_id = tenant_id
        # Build value objects from flat args
        self.info = {{ info_value_object }}(number_of_units, eta, status, started_at)
        self.items = {{ collection_value_object }}(items, changes) or {{ collection_value_object }}.new()
        self.bypass_mode = bypass_mode
        self.created_at = created_at
        self.updated_at = updated_at
        self.events = events or []
        self.commands = commands or []
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ aggregate_name }}` | Aggregate class name | `Load`, `Order` |
| `{{ info_value_object }}` | Value object for descriptive fields | `ShipmentInfo`, `OrderInfo` |
| `{{ collection_value_object }}` | Collection value object | `Items`, `Tires` |
| `{{ entity_name }}` | Child entity type | `LineItem`, `Tire` |

## Repository mapping benefit

This pattern simplifies repository code — just pass database columns directly:

```python
class LoadRepository:
    def get(self, load_id: str) -> Load:
        row = self._fetch_row(load_id)
        return Load(
            id_=row["id"],
            tenant_id=row["tenant_id"],
            number_of_units=row["number_of_units"],
            eta=row["eta"],
            status=row["status"],
            started_at=row["started_at"],
            items=self._load_items(load_id),
            changes=None,
            bypass_mode=row["bypass_mode"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
```
