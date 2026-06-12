---
name: query-context
description: Query Context pattern for persistence. Use when implementing a read-only SQLAlchemy context manager for CQRS query repositories separate from the unit of work.
user-invocable: false
disable-model-invocation: false
---

# Query Context

**Type:** Supporting

> **Optional Pattern**: This pattern complements Query Repository for CQRS implementations. Use when you have Query Repositories and need a dedicated context for read operations. Skip if using Unit of Work for all database access.
> 

## Purpose

- Provide a read-only context manager for query repository operations.
- Separate query concerns from command/transaction boundaries.
- Enable dependency injection of query repositories without unit of work overhead.

## Structure

- Abstract base class (`AbstractQueryContext`) declares query repository attributes and abstract `close()` method.
- Concrete implementation (`SqlAlchemyQueryContext`) takes a `DatabaseSession` dependency and initializes query repositories in `__enter__`.
- Context manager pattern ensures proper session cleanup via `__exit__` or explicit `close()`.
- Query repository attributes are set during context entry and used by application services.

## Behavior checklist

- Implement `__enter__` to create database session and initialize query repository attributes.
- Implement `__exit__` to clean up session factory.
- Expose `close()` method for explicit cleanup (used by async contexts).
- Query repository attributes should match domain query repository interfaces.

## Testing guidance

- Write unit tests using fakes for `DatabaseSession` and verify repository initialization.
- Test context manager behavior: proper cleanup on exit, explicit close works.
- Use integration tests to verify query operations with real database connections.

---

## Template

### Abstract Query Context

```python
import abc

from {{ domain_module }} import {{ query_repository_interface }}

__all__ = ["AbstractQueryContext"]

class AbstractQueryContext(abc.ABC):
    {{ repository_attribute }}: {{ query_repository_interface }}

    @abc.abstractmethod
    def close(self):
        raise NotImplementedError
```

### SQLAlchemy Query Context

```python
from sqlalchemy.orm import Session

from {{ extras_module }} import DatabaseSession

from ..repositories import {{ query_repository_class }}
from .abstract_query_context import AbstractQueryContext

__all__ = ["SqlAlchemyQueryContext"]

class SqlAlchemyQueryContext(AbstractQueryContext):
    _session: Session

    def __init__(self, database_session: DatabaseSession):
        self._database_session = database_session

    def __enter__(self):
        with self._database_session.connect() as session:
            self._session = session

            self.{{ repository_attribute }} = {{ query_repository_class }}(self._session)

    def __exit__(self, exc_type, exc_value, traceback):
        self._database_session.session_factory.remove()

    def close(self):
        self._database_session.session_factory.remove()
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ domain_module }}` | Domain module path | `domain.repositories`, `domain.interfaces` |
| `{{ query_repository_interface }}` | Query repository interface | `QueryRepository`, `OrderQueryRepository` |
| `{{ repository_attribute }}` | Repository attribute name | `order_query_repository`, `profile_query_repository` |
| `{{ extras_module }}` | Infrastructure extras module | `infrastructure.extras`, `persistence.extras` |
| `{{ query_repository_class }}` | Concrete query repository class | `SqlAlchemyOrderQueryRepository` |
