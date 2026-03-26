# Repositories Template

## Command Repository

```python
from abc import ABC, abstractmethod

from .aggregates import {{ aggregate_name }}

class {{ command_repository_name }}(ABC):
    @abstractmethod
    def {{ aggregate_lookup_method }}(self, id_: str, tenant_id: str) -> {{ aggregate_name }} | None:
        pass

    @abstractmethod
    def save(self, aggregate: {{ aggregate_name }}) -> None:
        pass
```

## Query Repository

```python
from typing import Protocol

from ..shared import Pagination
from .dtos import {{ dto_name }}, {{ list_dto_name }}

class {{ query_repository_name }}(Protocol):
    def find_one(self, id_: str, tenant_id: str) -> {{ dto_name }} | None:
        pass

    def find_many(self, pagination: Pagination | None = None) -> {{ list_dto_name }}:
        pass
```

## Placeholders — Command Repository

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ command_repository_name }}` | Command repository interface name | `LoadRepository`, `OrderRepository` |
| `{{ aggregate_name }}` | Aggregate type | `Load`, `Order` |
| `{{ aggregate_lookup_method }}` | Lookup method name | `load_of_id`, `order_of_id` |

## Placeholders — Query Repository

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ query_repository_name }}` | Query repository interface name | `LoadQueryRepository`, `OrderQueryRepository` |
| `{{ dto_name }}` | Single item DTO | `LoadInfo`, `OrderInfo` |
| `{{ list_dto_name }}` | Collection DTO | `LoadsInfo`, `OrdersInfo` |

## Example

```python
# Command repository
from abc import ABC, abstractmethod
from .aggregates import Order

class OrderRepository(ABC):
    @abstractmethod
    def order_of_id(self, id_: str, tenant_id: str) -> Order | None:
        pass

    @abstractmethod
    def save(self, aggregate: Order) -> None:
        pass

# Query repository
from typing import Protocol
from ..shared import Pagination
from .dtos import OrderInfo, OrdersInfo

class OrderQueryRepository(Protocol):
    def find_one(self, id_: str, tenant_id: str) -> OrderInfo | None:
        pass

    def find_many(self, pagination: Pagination | None = None) -> OrdersInfo:
        pass
```
