# Aggregate Fixtures Templates

## Simple Aggregate Fixture (No Data Fixture)

```python
import pytest

from {{ module_path }}.constants import {{ tenant_constant }}
from {{ module_path }}.domain import {{ aggregate_class }}


@pytest.fixture
def {{ aggregate_name }}_{{ fixture_number }}():
    return {{ aggregate_class }}.{{ factory_method }}(
        {{ tenant_constant }},
        {% for arg in factory_args -%}
        {{ arg }},
        {% endfor -%}
    )
```

## Aggregate Fixture from Data Fixture (Complex)

```python
import pytest

from {{ module_path }}.constants import {{ tenant_constant }}
from {{ module_path }}.domain import {{ aggregate_class }}


@pytest.fixture
def {{ aggregate_name }}_{{ fixture_number }}({{ aggregate_name }}_{{ fixture_number }}_data):
    return {{ aggregate_class }}.{{ factory_method }}(
        {{ tenant_constant }},
        {% for arg in factory_args -%}
        {{ arg }},
        {% endfor -%}
        {{ aggregate_name }}_{{ fixture_number }}_data,
    )
```

## Aggregate Fixture with Mutations

```python
import pytest

from {{ module_path }}.constants import {{ tenant_constant }}
from {{ module_path }}.domain import {{ aggregate_class }}


@pytest.fixture
def {{ aggregate_name }}_{{ fixture_number }}({{ aggregate_name }}_1_data):
    """{{ docstring }}"""
    {{ aggregate_name }} = {{ aggregate_class }}.{{ factory_method }}(
        {{ tenant_constant }},
        {% for arg in factory_args -%}
        {{ arg }},
        {% endfor -%}
        {{ aggregate_name }}_1_data,
    )

    {% for mutation in mutations -%}
    {{ aggregate_name }}.{{ mutation.method }}({% for arg in mutation.args %}{{ arg }}{% if not loop.last %}, {% endif %}{% endfor %})
    {% endfor -%}
    {{ aggregate_name }}.clear_events()
    return {{ aggregate_name }}
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ module_path }}` | Module path for imports | `iv_documents.domain.document` |
| `{{ tenant_constant }}` | Constant for tenant ID | `DEFAULT_TENANT_ID`, `DEFAULT_WAREHOUSE_ID` |
| `{{ aggregate_class }}` | Aggregate class name | `Document`, `Load` |
| `{{ aggregate_name }}` | Name of your aggregate (lowercase) | `document`, `load` |
| `{{ fixture_number }}` | Sequential identifier | `1`, `2`, `3` |
| `{{ factory_method }}` | Factory method name | `from_data`, `new`, `from_load_data` |
| `{{ factory_args }}` | List of additional factory arguments | `["conveyor-001"]` |
| `{{ docstring }}` | Docstring describing fixture state | `"Load in receiving state"` |
| `{{ mutations }}` | List of mutation operations | `[{"method": "start_receiving", "args": []}]` |

## Example: Full conftest.py with Multiple States

```python
import pytest

from iv_loads.domain.load import Load
from iv_loads.domain.load import LoadData

DEFAULT_WAREHOUSE_ID = "warehouse-001"


@pytest.fixture
def load_1(load_1_data):
    """Load in initial pending state"""
    load = Load.from_load_data(DEFAULT_WAREHOUSE_ID, "conveyor-001", load_1_data)
    load.clear_events()
    return load


@pytest.fixture
def load_2(load_1_data):
    """Load in receiving state"""
    load = Load.from_load_data(DEFAULT_WAREHOUSE_ID, "conveyor-001", load_1_data)
    load.start_receiving()
    load.clear_events()
    return load


@pytest.fixture
def load_3(load_1_data):
    """Load in completed state"""
    load = Load.from_load_data(DEFAULT_WAREHOUSE_ID, "conveyor-001", load_1_data)
    load.start_receiving()
    load.complete_receiving()
    load.clear_events()
    return load


@pytest.fixture
def conveyor_1():
    from iv_loads.domain.conveyor import Conveyor
    return Conveyor.new(
        warehouse_id=DEFAULT_WAREHOUSE_ID,
        conveyor_id="conveyor-001",
        name="Inbound Conveyor",
    )
```
