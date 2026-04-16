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

## Example: Status-Machine Aggregate (Full conftest.py)

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

## Example: CRUD-Collection Aggregate (Full conftest.py)

```python
import pytest

from profiles.domain.profile_type import ProfileType
from profiles.domain.profile_type import FieldDetails

DEFAULT_TENANT_ID = "tenant-001"


# --- Initial state ---

@pytest.fixture
def profile_type_1():
    """ProfileType in initial state — all collections empty."""
    profile_type = ProfileType.new(
        tenant_id=DEFAULT_TENANT_ID,
        name="Individual Profile",
        description="Profile type for individual clients",
        subject_kind="Individual",
    )
    profile_type.clear_events()
    return profile_type


# --- Per-collection fixtures (one per independent collection group) ---

@pytest.fixture
def profile_type_2():
    """ProfileType with two fields (enough for update/delete testing)."""
    profile_type = ProfileType.new(
        tenant_id=DEFAULT_TENANT_ID,
        name="Individual Profile",
        description="Profile type for individual clients",
        subject_kind="Individual",
    )
    profile_type.add_field(
        name="Full Name",
        description="The full legal name",
        required=True,
        is_collection=False,
    )
    profile_type.add_field(
        name="Date of Birth",
        description="Date of birth",
        required=True,
        is_collection=False,
    )
    profile_type.clear_events()
    return profile_type


@pytest.fixture
def profile_type_3():
    """ProfileType with a document type and a nested validation rule."""
    profile_type = ProfileType.new(
        tenant_id=DEFAULT_TENANT_ID,
        name="Individual Profile",
        description="Profile type for individual clients",
        subject_kind="Individual",
    )
    profile_type.add_document_type(
        name="Identity Document",
        description="Primary identity document",
        fields=[],
    )
    doc_type_id = profile_type.document_types.document_types[0].id
    profile_type.add_document_type_validation_rule(
        document_type_id=doc_type_id,
        name="Expiry check",
        code="check_expiry",
        field_ids=[],
        description="Validates document is not expired",
    )
    profile_type.clear_events()
    return profile_type


@pytest.fixture
def profile_type_4():
    """ProfileType with one reconciliation rule."""
    profile_type = ProfileType.new(
        tenant_id=DEFAULT_TENANT_ID,
        name="Individual Profile",
        description="Profile type for individual clients",
        subject_kind="Individual",
    )
    profile_type.add_reconciliation_rule(
        name="Name match",
        description="Match by full name",
    )
    profile_type.clear_events()
    return profile_type


@pytest.fixture
def profile_type_5():
    """ProfileType with one validation rule."""
    profile_type = ProfileType.new(
        tenant_id=DEFAULT_TENANT_ID,
        name="Individual Profile",
        description="Profile type for individual clients",
        subject_kind="Individual",
    )
    profile_type.add_validation_rule(
        name="Required fields check",
        code="req_fields",
        field_ids=[],
        description="Ensures all required fields are present",
    )
    profile_type.clear_events()
    return profile_type


# --- Fully populated fixture ---

@pytest.fixture
def profile_type_6():
    """ProfileType fully populated — fields, document types, reconciliation rules, and validation rules."""
    profile_type = ProfileType.new(
        tenant_id=DEFAULT_TENANT_ID,
        name="Individual Profile",
        description="Profile type for individual clients",
        subject_kind="Individual",
    )
    profile_type.add_field(
        name="Full Name",
        description="The full legal name",
        required=True,
        is_collection=False,
    )
    profile_type.add_field(
        name="Date of Birth",
        description="Date of birth",
        required=True,
        is_collection=False,
    )
    profile_type.add_document_type(
        name="Identity Document",
        description="Primary identity document",
        fields=[],
    )
    profile_type.add_reconciliation_rule(
        name="Name match",
        description="Match by full name",
    )
    profile_type.add_validation_rule(
        name="Required fields check",
        code="req_fields",
        field_ids=[],
        description="Ensures all required fields are present",
    )
    profile_type.clear_events()
    return profile_type


# --- Detail update fixture ---

@pytest.fixture
def profile_type_7():
    """ProfileType fully populated with updated details."""
    profile_type = ProfileType.new(
        tenant_id=DEFAULT_TENANT_ID,
        name="Individual Profile",
        description="Profile type for individual clients",
        subject_kind="Individual",
    )
    profile_type.add_field(
        name="Full Name",
        description="The full legal name",
        required=True,
        is_collection=False,
    )
    profile_type.add_document_type(
        name="Identity Document",
        description="Primary identity document",
        fields=[],
    )
    profile_type.add_reconciliation_rule(
        name="Name match",
        description="Match by full name",
    )
    profile_type.add_validation_rule(
        name="Required fields check",
        code="req_fields",
        field_ids=[],
        description="Ensures all required fields are present",
    )
    profile_type.update_details(
        name="Corporate Profile",
        description="Profile type for corporate clients",
        subject_kind="Corporate",
    )
    profile_type.clear_events()
    return profile_type
```
