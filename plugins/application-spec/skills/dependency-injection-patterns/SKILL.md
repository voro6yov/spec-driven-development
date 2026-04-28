---
name: dependency-injection-patterns
description: Dependency Injection Patterns pattern for application services. Use when wiring application services with Protocol-based interfaces, configuring DI containers, or setting up test fixtures with fakes and overrides.
user-invocable: false
disable-model-invocation: false
---

# Dependency Injection Patterns

Purpose: Enable loose coupling and testability through Protocol-based interfaces and container configuration

## Purpose

- Enable loose coupling between application services and their dependencies.
- Support testability by allowing fake implementations to be injected.
- Centralize dependency configuration in containers for consistent wiring.
- Facilitate integration testing with real infrastructure and isolation testing with fakes.

## Core Concepts

### 1. Application Service Constructor Injection

Application services receive all dependencies through constructor parameters:

```python
class LoadCommands:
    def __init__(
        self,
        unit_of_work: AbstractUnitOfWork,
        domain_event_publisher: DomainEventPublisher,
        command_producer: CommandProducer,
        tire_identification: ICanUpdateConveyorItems,
        load_details_repository: ICanGetLoadDetails,
        conveyor_client: ICanStopConveyor,
        d365_client: ICanUpdateLineItems,
    ) -> None:
        self._uow = unit_of_work
        self._domain_event_publisher = domain_event_publisher
        self._command_producer = command_producer
        self._tire_identification = tire_identification
        self._load_details_repository = load_details_repository
        self._conveyor_client = conveyor_client
        self._d365_client = d365_client
```

**Key patterns:**

- Use abstract types (`AbstractUnitOfWork`) or Protocol interfaces (`ICanStopConveyor`) for dependencies
- Store dependencies as private attributes (`self._*`)
- Core infrastructure deps: `unit_of_work`, `domain_event_publisher`, `command_producer`
- External system deps: Protocol interfaces like `ICanStopConveyor`, `ICanUpdateLineItems`

### 2. Protocol-Based Interfaces

Define capabilities using `Protocol` from `typing`:

```python
from typing import Protocol

class ICanStopConveyor(Protocol):
    def stop_conveyor(self, warehouse_id: str, conveyor_id: str, reason: str | None = None) -> None:
        pass
```

**Naming convention:** `ICan{Action}` (e.g., `ICanQueryLoads`, `ICanUpdateLineItems`)

### 3. Container Configuration

Use `dependency_injector` library with `DeclarativeContainer`:

```python
from dependency_injector import containers, providers

class Containers(containers.DeclarativeContainer):
    config = providers.Configuration()
    
    # Infrastructure layer
    unit_of_work: providers.Singleton[AbstractUnitOfWork] = providers.Singleton(
        SqlAlchemyUnitOfWork,
        database_session=datasources.postgres_session,
    )
    
    # External service clients (concrete implementations)
    conveyor_client: providers.Singleton[ConveyorClient] = providers.Singleton(
        ConveyorClient,
    )
    
    # Application services - wire all dependencies
    load_commands: providers.Singleton[LoadCommands] = providers.Singleton(
        LoadCommands,
        unit_of_work=unit_of_work,
        domain_event_publisher=domain_event_publisher,
        command_producer=command_producer,
        tire_identification=tire_identification,
        load_details_repository=load_details_repository,
        conveyor_client=conveyor_client,
        d365_client=d365_client,
    )
```

**Patterns:**

- Use `providers.Singleton` for stateless services
- Use `providers.Container` for sub-containers (Messaging, Datasources, Repositories)
- Wire dependencies by referencing other provider names
- Type hint providers: `providers.Singleton[ServiceType]`

### 4. Nested Containers

Organize dependencies into logical sub-containers:

```python
class Datasources(containers.DeclarativeContainer):
    config = providers.Configuration()
    postgres_session: providers.Provider[DatabaseSession] = providers.Singleton(...)

class Repositories(containers.DeclarativeContainer):
    config = providers.Configuration()
    datasources = providers.DependenciesContainer()
    
    query_load: providers.Singleton[IQueryLoadRepository] = providers.Singleton(
        QueryLoadRepository,
        database=datasources.postgres_session,
    )

class Containers(containers.DeclarativeContainer):
    datasources: providers.Container[Datasources] = providers.Container(
        Datasources,
        config=config.database,
    )
    
    repositories: providers.Container[Repositories] = providers.Container(
        Repositories,
        config=config,
        datasources=datasources,
    )
```

## Testing Patterns

### 1. Test Fixture Structure

Main conftest.py (session-scoped):

```python
@pytest.fixture(scope="session")
def app() -> FastAPI:
    fastapi_app = create_fastapi()
    yield fastapi_app

@pytest.fixture(scope="session")
def containers(app):
    return app.containers
```

Integration conftest.py:

```python
@pytest.fixture
def unit_of_work(containers):
    return containers.unit_of_work()

@pytest.fixture
def load_commands(containers):
    return containers.load_commands()
```

### 2. Overriding Dependencies with Fakes

Session-scoped fake override:

```python
@pytest.fixture(autouse=True, scope="session")
def fake_conveyor_client_session(containers):
    fake_client = FakeConveyorClient()
    containers.conveyor_client.override(fake_client)
    
    yield fake_client
    
    containers.conveyor_client.reset_override()
```

Per-test reset:

```python
@pytest.fixture(autouse=True)
def fake_conveyor_client(fake_conveyor_client_session):
    fake_conveyor_client_session.reset()
    yield fake_conveyor_client_session
```

### 3. Mocking Domain Event Publishers

```python
@pytest.fixture(autouse=True, scope="session")
def domain_event_publisher_session_mock(containers):
    mock = Mock(containers.domain_event_publisher())
    containers.domain_event_publisher.override(mock)
    
    yield mock
    
    containers.domain_event_publisher.reset_override()

@pytest.fixture(autouse=True)
def domain_event_publisher_mock(domain_event_publisher_session_mock):
    domain_event_publisher_session_mock.reset_mock()
    yield domain_event_publisher_session_mock
```

### 4. Fake Implementation Pattern

```python
from tss_load_processing.application import ICanStopConveyor

class FakeConveyorClient(ICanStopConveyor):
    def __init__(self):
        self.stop_conveyor_calls: list[tuple[str, str, str | None]] = []

    def stop_conveyor(self, warehouse_id: str, conveyor_id: str, reason: str | None = None) -> None:
        self.stop_conveyor_calls.append((warehouse_id, conveyor_id, reason))

    def reset(self) -> None:
        self.stop_conveyor_calls.clear()
```

**Key patterns:**

- Implement the Protocol interface
- Track method calls in lists for assertions
- Provide `reset()` method for test isolation
- Keep implementation minimal - just capture calls

### 5. Data Preloading Fixtures

```python
@pytest.fixture()
def add_loads(unit_of_work, test_loads, add_conveyors):
    with unit_of_work:
        for load in test_loads:
            unit_of_work.loads.save(load)
        unit_of_work.commit()
        yield

@pytest.fixture(autouse=True)
def empty_unit_of_work(unit_of_work):
    try:
        with unit_of_work:
            unit_of_work.loads.erase_all()
            unit_of_work.conveyors.erase_all()
            unit_of_work.commit()
        yield
        with unit_of_work:
            unit_of_work.loads.erase_all()
            unit_of_work.conveyors.erase_all()
            unit_of_work.commit()
    except Exception:
        pass
```

## Dependency Categories

| Category | Examples | Injection Pattern |
| --- | --- | --- |
| Unit of Work | `AbstractUnitOfWork` | Required, first parameter |
| Event Publishing | `DomainEventPublisher` | Required for commands |
| Command Producing | `CommandProducer` | Required for saga patterns |
| External Systems | `ICanStopConveyor`, `ICanUpdateLineItems` | Protocol interfaces |
| Query Repositories | `IQueryLoadRepository` | Domain interfaces |
| Settings/Config | `LoadQueriesSettings` | Optional with defaults |

## Best Practices

1. **Commands vs Queries separation**
    - Commands: `unit_of_work`, `domain_event_publisher`, `command_producer`, external system interfaces
    - Queries: `query_repository`, `external_query_interfaces`, `settings`
2. **External system abstraction**
    - Always define Protocol interfaces for external systems
    - Place interfaces in application layer: `application/{context}/i_can_{action}.py`
    - Place implementations in infrastructure: `infrastructure/services/`
3. **Container organization**
    - Group by technical concern: `Datasources`, `Repositories`, `Messaging`, `MessageBrokers`
    - Application services at root container level
    - Use `providers.Container` for sub-containers
4. **Test isolation**
    - Session-scoped fakes for performance
    - Per-test reset for isolation
    - Use `autouse=True` for automatic cleanup
    - Prefer fakes over mocks for external dependencies
    - Use mocks only for event publishers (behavioral verification)

---

## Container Provider Template

```python
{# Template for adding application service to DI container #}
{# Variables:
   - service_class_name: Name of the application service class (e.g., LoadCommands)
   - service_var_name: Variable name for the provider (e.g., load_commands)
   - service_module: Module path to import from (e.g., tss_load_processing.application)
   - dependencies: List of dependency objects with:
     - name: dependency parameter name
     - provider: container provider reference (e.g., unit_of_work, repositories.query_load)
   - return_interface: Optional interface type for type hint (defaults to service_class_name)
#}
{% if service_module %}
from {{ service_module }} import {{ service_class_name }}
{% endif %}

{{ service_var_name }}: providers.Singleton[{{ return_interface | default(service_class_name) }}] = providers.Singleton(
    {{ service_class_name }},
{% for dep in dependencies %}
    {{ dep.name }}={{ dep.provider }},
{% endfor %}
)
```

### Container Provider Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ service_class_name }}` | Name of the application service class | `LoadCommands`, `ProfileQueries` |
| `{{ service_var_name }}` | Variable name for the provider | `load_commands`, `profile_queries` |
| `{{ service_module }}` | Module path to import from | `tss_load_processing.application` |
| `{{ dependencies }}` | List of dependency objects with `name` and `provider` | `[{"name": "unit_of_work", "provider": "unit_of_work"}, {"name": "conveyor_client", "provider": "conveyor_client"}]` |
| `{{ return_interface }}` | Optional interface type for type hint (defaults to service_class_name) | `ICanStopConveyor` |

## Test Fixtures Template

```python
{# Template for DI-based test fixtures #}
{# Variables:
   - service_name: Application service name (e.g., load_commands)
   - service_var: Variable name for the fixture (e.g., load_commands)
   - fake_class_name: Name of fake class (e.g., FakeConveyorClient)
   - fake_module: Module to import fake from (e.g., tests.fakes)
   - container_provider: Provider name in container (e.g., conveyor_client)
   - aggregate_name: Name of aggregate for data fixtures (e.g., Load)
   - aggregate_var_plural: Plural variable name (e.g., loads)
   - repository_attr: UoW repository attribute (e.g., loads)
#}
import pytest
{% if fake_module and fake_class_name %}
from {{ fake_module }} import {{ fake_class_name }}
{% endif %}

# Application service fixture - obtain from DI container
@pytest.fixture
def {{ service_var }}(containers):
    return containers.{{ service_name }}()

{% if fake_class_name %}
# Session-scoped fake override for external dependencies
@pytest.fixture(autouse=True, scope="session")
def fake_{{ container_provider }}_session(containers):
    fake = {{ fake_class_name }}()
    containers.{{ container_provider }}.override(fake)
    
    yield fake
    
    containers.{{ container_provider }}.reset_override()

# Per-test reset for isolation
@pytest.fixture(autouse=True)
def fake_{{ container_provider }}(fake_{{ container_provider }}_session):
    fake_{{ container_provider }}_session.reset()
    yield fake_{{ container_provider }}_session
{% endif %}

{% if aggregate_name %}
# Data preloading fixture
@pytest.fixture()
def add_{{ aggregate_var_plural }}(unit_of_work, test_{{ aggregate_var_plural }}):
    with unit_of_work:
        for {{ aggregate_var_plural[:-1] }} in test_{{ aggregate_var_plural }}:
            unit_of_work.{{ repository_attr }}.save({{ aggregate_var_plural[:-1] }})
        unit_of_work.commit()
        yield
{% endif %}
```

### Test Fixtures Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ service_name }}` | Application service name | `load_commands`, `profile_queries` |
| `{{ service_var }}` | Variable name for the fixture | `load_commands`, `profile_queries` |
| `{{ fake_class_name }}` | Name of fake class | `FakeConveyorClient`, `FakeD365Client` |
| `{{ fake_module }}` | Module to import fake from | `tests.fakes` |
| `{{ container_provider }}` | Provider name in container | `conveyor_client`, `d365_client` |
| `{{ aggregate_name }}` | Name of aggregate for data fixtures | `Load`, `Profile` |
| `{{ aggregate_var_plural }}` | Plural variable name | `loads`, `profiles` |
| `{{ repository_attr }}` | UoW repository attribute | `loads`, `profiles` |
