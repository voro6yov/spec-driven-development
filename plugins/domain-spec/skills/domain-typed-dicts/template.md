# Domain TypedDicts Template

```python
from typing import Literal, TypedDict

# Optional: import nested TypedDicts
# from .processing_info import ProcessingInfo

__all__ = ["{{ typed_dict_name }}"]  # add "{{ factory_name }}" if using factory

class {{ typed_dict_name }}(TypedDict):
    # field_name: field_type
    status: Literal["pending", "processing", "completed"]
    timestamp: str

# Optional factory — use when construction logic is non-trivial
class {{ factory_name }}:
    def __init__(self, param1: str, param2: int) -> None:
        self.param1 = param1
        self.param2 = param2

    @classmethod
    def new(cls, param1: str, param2: int) -> "{{ typed_dict_name }}":
        factory = cls(param1, param2)
        # compute derived values here
        return {{ typed_dict_name }}(
            status="pending",
            timestamp=param1,
        )
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ typed_dict_name }}` | TypedDict class name | `ProcessingInfo`, `ItemWithScore` |
| `{{ factory_name }}` | Optional factory class name | `ProcessingInfoFactory`, `ItemWithScoreFactory` |

## Examples

### Simple TypedDict

```python
from typing import Literal, TypedDict

__all__ = ["ProcessingInfo"]

class ProcessingInfo(TypedDict):
    status: Literal["pending", "processing", "completed"]
    timestamp: str
    error_message: str | None
```

### TypedDict with Factory

```python
from typing import TypedDict

__all__ = ["ItemWithScore", "ItemWithScoreFactory"]

class ItemWithScore(TypedDict):
    item_id: str
    score: float
    matched: bool

class ItemWithScoreFactory:
    def __init__(self, item_id: str, raw_score: int, threshold: int) -> None:
        self.item_id = item_id
        self.raw_score = raw_score
        self.threshold = threshold

    @classmethod
    def new(cls, item_id: str, raw_score: int, threshold: int) -> ItemWithScore:
        factory = cls(item_id, raw_score, threshold)
        normalized_score = factory.raw_score / 100.0
        matched = factory.raw_score >= factory.threshold

        return ItemWithScore(
            item_id=factory.item_id,
            score=normalized_score,
            matched=matched,
        )
```

### Nested TypedDict

```python
from typing import TypedDict
from .processing_info import ProcessingInfo

__all__ = ["PendingItem"]

class PendingItem(TypedDict):
    item_number: str
    quantity: int
    processing: ProcessingInfo
```
