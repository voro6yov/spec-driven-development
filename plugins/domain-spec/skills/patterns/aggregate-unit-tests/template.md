# Aggregate Unit Test Templates

## State Transition Test

```python
def test_{{ aggregate_name }}_{{ method_name }}__success({{ fixture_name }}):
    # GIVEN {{ precondition_description }}

    # WHEN {{ action_description }}
    {{ fixture_name }}.{{ method_name }}({% for arg in method_args %}{{ arg }}{% if not loop.last %}, {% endif %}{% endfor %})

    # THEN {{ outcome_description }}
    assert {{ fixture_name }}.{{ state_property }} == {{ expected_value }}
```

## Factory Method Test

```python
def test_{{ aggregate_name }}_{{ factory_method }}__creates_{{ aggregate_name }}({{ data_fixture_name }}):
    # GIVEN {{ data_fixture_description }}

    # WHEN creating via factory
    {{ aggregate_name }} = {{ aggregate_class }}.{{ factory_method }}(
        {{ tenant_constant }},
        {% for arg in factory_args -%}
        {{ arg }},
        {% endfor -%}
        {{ data_fixture_name }},
    )

    # THEN has correct values
    assert {{ aggregate_name }}.id == {{ data_fixture_name }}["id"]
    assert {{ aggregate_name }}.{{ state_property }} == {{ expected_value }}
```

## Domain Event Test (Type + Payload)

```python
def test_{{ aggregate_name }}_{{ method_name }}__emits_{{ event_name_snake }}({{ fixture_name }}):
    # GIVEN {{ precondition_description }}

    # WHEN {{ action_description }}
    {{ fixture_name }}.{{ method_name }}()

    # THEN emits {{ event_class }} with correct payload
    event = next(e for e in {{ fixture_name }}.events if isinstance(e, {{ event_class }}))
    assert event.{{ aggregate_name }}_id == {{ fixture_name }}.id
    {% for field in event_fields -%}
    assert event.{{ field }} == {{ fixture_name }}.{{ field }}
    {% endfor %}
```

## Validation / Error Test

```python
def test_{{ aggregate_name }}_{{ method_name }}__{{ scenario }}__raises({{ fixture_name }}):
    # GIVEN {{ precondition_description }}

    # WHEN / THEN
    with pytest.raises({{ exception_class }}):
        {{ fixture_name }}.{{ method_name }}({% for arg in method_args %}{{ arg }}{% if not loop.last %}, {% endif %}{% endfor %})
```

## Query Method Test

```python
def test_{{ aggregate_name }}_{{ query_property }}__returns_{{ return_description }}({{ fixture_name }}):
    # GIVEN {{ precondition_description }}

    # WHEN / THEN
    assert {{ fixture_name }}.{{ query_property }} == {{ expected_value }}
```

## Value Object Creation Test

```python
def test_{{ value_object_name }}_new__creates_value_object():
    # WHEN creating {{ value_object_class }}
    {{ value_object_name }} = {{ value_object_class }}.new(
        {% for arg in constructor_args -%}
        {{ arg.name }}={{ arg.value }},
        {% endfor -%}
    )

    # THEN has correct values
    {% for field in expected_fields -%}
    assert {{ value_object_name }}.{{ field.name }} == {{ field.value }}
    {% endfor %}
```

## Value Object Operation Test

```python
def test_{{ value_object_name }}_{{ operation }}__{{ scenario }}__{{ outcome }}():
    # GIVEN two {{ value_object_class }} objects
    {{ value_object_name }}_a = {{ value_object_class }}.new({% for arg in args_a %}{{ arg.name }}={{ arg.value }}{% if not loop.last %}, {% endif %}{% endfor %})
    {{ value_object_name }}_b = {{ value_object_class }}.new({% for arg in args_b %}{{ arg.name }}={{ arg.value }}{% if not loop.last %}, {% endif %}{% endfor %})

    # WHEN {{ operation_description }}
    result = {{ value_object_name }}_a.{{ operation }}({{ value_object_name }}_b)

    # THEN {{ outcome_description }}
    assert result.equals({{ value_object_class }}.new({% for arg in expected_result %}{{ arg.name }}={{ arg.value }}{% if not loop.last %}, {% endif %}{% endfor %}))
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ aggregate_name }}` | Aggregate name (lowercase) | `load`, `conveyor` |
| `{{ aggregate_class }}` | Aggregate class name | `Load`, `Conveyor` |
| `{{ fixture_name }}` | Fixture variable name — use `{aggregate}_{n}` pattern | `load_1`, `load_2`, `load_3` |
| `{{ data_fixture_name }}` | Data fixture variable name | `load_1_data` |
| `{{ data_fixture_description }}` | Description of data fixture | `"load data with items"` |
| `{{ method_name }}` | Public method under test | `start_receiving`, `pause_receiving` |
| `{{ factory_method }}` | Factory method name | `from_load_data`, `new` |
| `{{ factory_args }}` | Extra factory arguments | `["conveyor-001"]` |
| `{{ tenant_constant }}` | Tenant/warehouse constant | `DEFAULT_WAREHOUSE_ID` |
| `{{ event_class }}` | Domain event class | `LoadReceivingStarted` |
| `{{ event_name_snake }}` | Event name in snake_case | `receiving_started` |
| `{{ event_fields }}` | List of event payload fields to assert | `["warehouse_id", "conveyor_id"]` |
| `{{ exception_class }}` | Exception class to expect | `LoadAlreadyCompletedError` |
| `{{ scenario }}` | Test precondition variation | `already_completed`, `negative_amount` |
| `{{ state_property }}` | Public property to assert | `status`, `items_count` |
| `{{ expected_value }}` | Expected property value | `"receiving"`, `2` |
| `{{ precondition_description }}` | GIVEN comment text | `"a load in pending state"` |
| `{{ action_description }}` | WHEN comment text | `"starting receiving"` |
| `{{ outcome_description }}` | THEN comment text | `"status changes to receiving"` |
| `{{ query_property }}` | Query property name | `items_count`, `is_active` |
| `{{ return_description }}` | Return value description (for name) | `count`, `true` |
| `{{ method_args }}` | List of method call arguments | `[]`, `["conveyor-001"]` |
| `{{ value_object_name }}` | Value object variable name | `money`, `address` |
| `{{ value_object_class }}` | Value object class name | `Money`, `Address` |
| `{{ constructor_args }}` | List of `{name, value}` constructor args | `[{name: "amount", value: 100}]` |
| `{{ expected_fields }}` | List of `{name, value}` fields to assert | `[{name: "amount", value: 100}]` |
| `{{ operation }}` | Value object operation name | `add`, `subtract` |
| `{{ operation_description }}` | Description of the operation | `"adding two money amounts"` |
| `{{ args_a }}` | Constructor args for first object | `[{name: "amount", value: 100}]` |
| `{{ args_b }}` | Constructor args for second object | `[{name: "amount", value: 50}]` |
| `{{ expected_result }}` | Constructor args for expected result | `[{name: "amount", value: 150}]` |
