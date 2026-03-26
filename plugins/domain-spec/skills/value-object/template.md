# Value Object Template

```python
from datetime import datetime

from ..shared import Event, Guard, ImmutableCheck, ValueObject
from .events import {{ state_event }}

class {{ value_object_name }}(metaclass=ValueObject):
    number_of_units = Guard[int](int, ImmutableCheck())
    eta = Guard[datetime](datetime, ImmutableCheck())
    status = Guard[str](str)
    started_at = Guard[datetime](datetime)
    finished_at = Guard[datetime](datetime)

    def __init__(
        self,
        number_of_units: int,
        eta: datetime,
        status: str,
        started_at: datetime | None,
        finished_at: datetime | None,
    ) -> None:
        self.number_of_units = number_of_units
        self.eta = eta
        self.status = status

        if started_at is not None:
            self.started_at = started_at

        if finished_at is not None:
            self.finished_at = finished_at

        self.events: list[Event] = []

    def start(self, aggregate: "{{ aggregate_name }}") -> None:
        self.started_at = datetime.now()
        self.status = "inProgress"
        aggregate.events.append(
            {{ state_event }}(
                aggregate_id=aggregate.id,
                tenant_id=aggregate.tenant_id,
                started_at=self.started_at.isoformat(),
            )
        )

    def finish(self, aggregate: "{{ aggregate_name }}") -> None:
        self.finished_at = datetime.now()
        self.status = "finished"
        aggregate.events.append(
            {{ state_event }}(
                aggregate_id=aggregate.id,
                tenant_id=aggregate.tenant_id,
                finished_at=self.finished_at.isoformat(),
            )
        )
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ value_object_name }}` | Name of your value object class | `ShipmentInfo`, `OrderInfo` |
| `{{ state_event }}` | Event emitted on state changes | `ShipmentStarted`, `OrderFinished` |
| `{{ aggregate_name }}` | Owning aggregate type | `Load`, `Order` |
