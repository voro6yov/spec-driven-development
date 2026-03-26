# Statuses Template

```python
from ..shared import Guard, ImmutableCheck, ValueObject

__all__ = ["{{ class_name }}"]

class {{ class_name }}(metaclass=ValueObject):
    # Status constants
    PENDING: str = "pending"
    IN_PROGRESS: str = "inProgress"
    COMPLETED: str = "completed"

    status = Guard[str](str, ImmutableCheck())

    def __init__(self, status: str) -> None:
        self.status = status

    def __call__(self) -> str:
        return self.status

    @classmethod
    def pending(cls) -> "{{ class_name }}":
        return cls(status=cls.PENDING)

    @classmethod
    def in_progress(cls) -> "{{ class_name }}":
        return cls(status=cls.IN_PROGRESS)

    @classmethod
    def completed(cls) -> "{{ class_name }}":
        return cls(status=cls.COMPLETED)

    @property
    def is_pending(self) -> bool:
        return self.status == self.PENDING

    @property
    def is_in_progress(self) -> bool:
        return self.status == self.IN_PROGRESS

    @property
    def is_completed(self) -> bool:
        return self.status == self.COMPLETED
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ class_name }}` | Name of your status class | `LoadStatus`, `OrderStatus` |

Add/remove status constants, factory methods, and boolean properties to match your domain's actual states.
