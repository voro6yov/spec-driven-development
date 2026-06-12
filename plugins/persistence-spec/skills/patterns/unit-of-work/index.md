---
name: unit-of-work
description: Unit of Work pattern for persistence. Use when encapsulating transaction boundaries, coordinating multiple command repositories, and providing context manager commit/rollback control.
user-invocable: false
disable-model-invocation: false
---

# Unit of Work

**Type:** Primary

## Purpose

- Encapsulate transaction boundaries and coordinate multiple repositories within a single database transaction.
- Provide a context manager interface for explicit commit/rollback control.
- Isolate persistence concerns from application services by exposing repository attributes.

## Structure

- Abstract base class (`AbstractUnitOfWork`) declares repository attributes and abstract `commit()`/`rollback()` methods.
- Concrete implementation (`SqlAlchemyUnitOfWork`) takes a `DatabaseSession` dependency and initializes repositories in `__enter__`.
- Context manager pattern ensures automatic rollback on exception via `__exit__`.
- Repository attributes are set during context entry and used by application services.

## Behavior checklist

- Implement `__enter__` to create database session and initialize repository attributes.
- Implement `__exit__` to call `rollback()` automatically (can be overridden for commit-on-success patterns).
- Expose `commit()` method to persist changes explicitly.
- Expose `rollback()` method to discard changes.
- Repository attributes should match domain command repository interfaces.

## Testing guidance

- Write unit tests using fakes for `DatabaseSession` and verify repository initialization.
- Test context manager behavior: commit on explicit call, rollback on exception, rollback on exit.
- Use integration tests to verify transaction boundaries with real database connections.

---

## Template

### Abstract Unit of Work

```python
import abc

from {{ domain_module }} import {{ command_repository_interface }}

__all__ = ["AbstractUnitOfWork"]

class AbstractUnitOfWork(abc.ABC):
    {{ repository_attribute }}: {{ command_repository_interface }}

    def __exit__(self, *args):
        self.rollback()

    @abc.abstractmethod
    def commit(self):
        raise NotImplementedError

    @abc.abstractmethod
    def rollback(self):
        raise NotImplementedError
```

### SQLAlchemy Unit of Work

```python
from sqlalchemy.orm import Session

from {{ extras_module }} import DatabaseSession

from ..repositories import {{ uow_repository_class }}
from .abstract_unit_of_work import AbstractUnitOfWork

__all__ = ["SqlAlchemyUnitOfWork"]

class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    _session: Session

    def __init__(self, database_session: DatabaseSession) -> None:
        self._database_session = database_session

    def __enter__(self) -> None:
        with self._database_session.connect() as session:
            self._session = session

            self.{{ repository_attribute }} = {{ uow_repository_class }}(session)

    def commit(self):
        self._session.commit()

    def rollback(self):
        self._session.rollback()
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ domain_module }}` | Domain module path | `domain.repositories`, `domain.interfaces` |
| `{{ command_repository_interface }}` | Command repository interface name | `CommandRepository`, `OrderRepository` |
| `{{ repository_attribute }}` | Repository attribute name on UoW | `order_repository`, `profile_repository` |
| `{{ extras_module }}` | Infrastructure extras module | `infrastructure.extras`, `persistence.extras` |
| `{{ uow_repository_class }}` | Concrete repository class name | `SqlAlchemyOrderRepository`, `SqlAlchemyProfileRepository` |
