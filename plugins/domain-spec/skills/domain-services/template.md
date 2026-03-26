# Domain Services & Interfaces Template

```python
from abc import ABC, abstractmethod

from .dtos import {{ dto_name }}

class {{ service_interface_name }}(ABC):
    @abstractmethod
    def execute(self, payload: bytes) -> {{ dto_name }}:
        pass
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ service_interface_name }}` | Name of service interface | `LoadDataParser`, `ProfileValidator` |
| `{{ dto_name }}` | Return DTO type | `LoadData`, `ProfileData` |

## Examples

```python
from abc import ABC, abstractmethod
from .dtos import OrderData

class OrderParser(ABC):
    @abstractmethod
    def parse(self, raw_data: bytes) -> OrderData:
        pass

class PricingService(ABC):
    @abstractmethod
    def calculate_total(self, order_id: str, items: list[dict]) -> float:
        pass
```
