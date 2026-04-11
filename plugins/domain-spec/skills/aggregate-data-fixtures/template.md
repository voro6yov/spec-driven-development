# Aggregate Data Fixture Template

```python
from datetime import datetime

import pytest

from {{ module_path }}.domain import {{ data_type }}


@pytest.fixture
def {{ aggregate_name }}_{{ fixture_number }}_data() -> {{ data_type }}:
    return {
        "id": "{{ aggregate_name }}-{{ fixture_number | default('001') }}",
        {% for field in fields -%}
        "{{ field.name }}": {{ field.value }},
        {% endfor -%}
        {% if has_items -%}
        "items": [
            {% for item in items -%}
            {
                {% for field in item.fields -%}
                "{{ field.name }}": {{ field.value }},
                {% endfor -%}
            },
            {% endfor -%}
        ],
        {% endif -%}
    }
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ module_path }}` | Module path for imports | `iv_documents.domain.document` |
| `{{ data_type }}` | TypedDict type for the data | `DocumentData`, `LoadData` |
| `{{ aggregate_name }}` | Name of your aggregate | `document`, `load` |
| `{{ fixture_number }}` | Sequential identifier | `1`, `2`, `3` |
| `{{ fields }}` | List of field definitions | `[{"name": "status", "value": "\"pending\""}]` |
| `{{ has_items }}` | Boolean indicating nested collections | `true`, `false` |
| `{{ items }}` | List of item definitions (if has_items) | `[{"fields": [...]}]` |

## Example: Complex Aggregate with Nested Items

```python
from datetime import datetime

import pytest

from iv_loads.domain.load import LoadData


DEFAULT_WAREHOUSE_ID = "warehouse-001"


@pytest.fixture
def load_1_data() -> LoadData:
    return {
        "id": "load-001",
        "number_of_tires": 8,
        "eta": datetime(2025, 7, 7, 0, 0, 0),
        "status": "pending",
        "items": [
            {
                "item_number": "ITEM-001",
                "product_name": "Sample Product 1",
                "quantity": 5,
                "order_number": "ORDER-001",
            },
            {
                "item_number": "ITEM-002",
                "product_name": "Sample Product 2",
                "quantity": 3,
                "order_number": "ORDER-002",
            },
        ],
    }


@pytest.fixture
def load_1(load_1_data):
    return Load.from_load_data(DEFAULT_WAREHOUSE_ID, "conveyor-001", load_1_data)
```

## Counter-example: Simple Aggregate (NO data fixture)

```python
@pytest.fixture
def conveyor_1():
    return Conveyor.new(
        warehouse_id=DEFAULT_WAREHOUSE_ID,
        conveyor_id="conveyor-001",
        name="Main Conveyor",
    )


@pytest.fixture
def user_1():
    return User.new(user_id="user-001", name="John Doe", role="operator")
```
