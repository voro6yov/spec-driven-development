---
name: queries-pattern
description: Queries pattern for application services. Use when implementing read operations that need pagination, filtering, sorting, or search and return DTOs rather than domain objects.
user-invocable: false
disable-model-invocation: false
---

# Queries

Purpose: Handle read operations with pagination, filtering, sorting, and search capabilities returning DTOs

## Purpose

- Handle read operations for domain aggregates and projections.
- Provide pagination, filtering, sorting, and search capabilities.
- Return DTOs (TypedDict) rather than domain objects for read operations.

## Structure

- Accept query repositories (e.g., `IQueryAggregateRepository`) for domain reads.
- Accept Protocol-based interfaces for complex queries spanning multiple sources.
- Accept settings object (e.g., `AggregateQueriesSettings`) for default values.
- Maintain a logger instance for operation tracking.

## Behavior checklist

- Apply default values from settings when parameters are `None`.
- Use query repositories for simple find operations.
- Delegate complex queries to Protocol interfaces that handle multi-source queries.
- Return TypedDict DTOs, not domain aggregates.
- Raise domain exceptions (e.g., `AggregateNotFound`) when entities are missing.
- Log query operations with relevant parameters.

## Testing guidance

- Write integration tests that verify query results match expected DTOs.
- Use fakes for query repositories and Protocol interfaces.
- Verify pagination, filtering, and sorting produce correct results.

---

## Template

```python
import logging
from typing import Any

{% if constants_module and default_tenant_id %}
from {{ constants_module }} import {{ default_tenant_id }}
{% elif default_tenant_id %}
{{ default_tenant_id }} = "{{ default_tenant_id_value }}"
{% endif %}
from {{ domain_module }} import (
    IQuery{{ aggregate_name }}Repository,
    {{ aggregate_not_found }},
    {{ aggregates_info }},
    Pagination,
)

{% if interface_name %}
from .{{ interface_module }} import {{ interface_name }}
{% endif %}
from .{{ settings_module }} import {{ settings_class_name }}
{# interface_module / settings_module are bare module names (no leading dot) #}

__all__ = ["{{ queries_class_name }}"]

class {{ queries_class_name }}:
    def __init__(
        self,
        query_{{ aggregate_var }}_repository: IQuery{{ aggregate_name }}Repository,
{% if interface_name %}
        {{ interface_param_name }}: {{ interface_name }},
{% endif %}
        settings: {{ settings_class_name }} | None = None,
    ) -> None:
        self._query_{{ aggregate_var }}_repository = query_{{ aggregate_var }}_repository
{% if interface_name %}
        self._{{ interface_param_name }} = {{ interface_param_name }}
{% endif %}

        self._settings = settings or {{ settings_class_name }}()

        self._logger = logging.getLogger(self.__class__.__name__)

    def find_{{ aggregate_var }}(self, {{ aggregate_id_param }}: str{% if tenant_param %}, {{ tenant_param }}: str | None = None{% endif %}) -> dict[str, Any]:
{% if tenant_param %}
        {{ tenant_param }} = {{ tenant_param }} or {{ default_tenant_id }}

        self._logger.info("Finding {{ aggregate_var }} with id - %s, {{ tenant_param }} - %s...", {{ aggregate_id_param }}, {{ tenant_param }})
{% else %}
        self._logger.info("Finding {{ aggregate_var }} with id - %s...", {{ aggregate_id_param }})
{% endif %}

        if not ({{ aggregate_var }} := self._query_{{ aggregate_var }}_repository.find_{{ aggregate_var }}({{ aggregate_id_param }}{% if tenant_param %}, {{ tenant_param }}{% endif %})):
            raise {{ aggregate_not_found }}({{ aggregate_id_param }}{% if tenant_param %}, {{ tenant_param }}{% endif %})

        return {{ aggregate_var }}

    def find_{{ aggregate_plural }}(
        self, page: int | None = None, per_page: int | None = None{% if tenant_param %}, {{ tenant_param }}: str | None = None{% endif %}
    ) -> {{ aggregates_info }}:
        page = self._settings.pagination.default_page if page is None else page
        per_page = self._settings.pagination.default_per_page if per_page is None else per_page
{% if tenant_param %}
        {{ tenant_param }} = {{ tenant_param }} or {{ default_tenant_id }}

        self._logger.info("Finding {{ aggregate_plural }}: page - %s, per page - %s, {{ tenant_param }} - %s...", page, per_page, {{ tenant_param }})
{% else %}
        self._logger.info("Finding {{ aggregate_plural }}: page - %s, per page - %s...", page, per_page)
{% endif %}

        return self._query_{{ aggregate_var }}_repository.find_{{ aggregate_plural }}(
            pagination=Pagination(page=page, per_page=per_page){% if tenant_param %}, {{ tenant_param }}={{ tenant_param }}{% endif %}
        )
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ queries_class_name }}` | Name of the queries class | `LoadQueries`, `ProfileQueries` |
| `{{ aggregate_name }}` | Domain aggregate class name | `Load`, `Profile` |
| `{{ aggregate_var }}` | Variable name for aggregate instance | `load`, `profile` |
| `{{ aggregate_plural }}` | Plural form for repository access | `loads`, `profiles` |
| `{{ aggregate_id_param }}` | Parameter name for aggregate ID | `load_id`, `profile_id` |
| `{{ aggregate_not_found }}` | Domain exception class | `LoadNotFound`, `ProfileNotFound` |
| `{{ aggregates_info }}` | Domain info DTO class | `LoadsInfo`, `ProfilesInfo` |
| `{{ domain_module }}` | Module path for domain imports | `tss_load_processing.domain` |
| `{{ interface_name }}` | Optional Protocol interface name | `ICanQueryLoads` |
| `{{ interface_module }}` | Optional sibling module name for the interface (no leading dot) | `i_can_query_loads` |
| `{{ interface_param_name }}` | Optional parameter name for interface | `load_details_repository` |
| `{{ settings_class_name }}` | Settings class name | `LoadQueriesSettings` |
| `{{ settings_module }}` | Sibling module name for settings (no leading dot) | `load_queries_settings` |
| `{{ constants_module }}` | Optional module path for constants | `tss_load_processing.constants` |
| `{{ tenant_param }}` | Optional tenant/warehouse parameter name | `warehouse_id` |
| `{{ default_tenant_id }}` | Optional default tenant constant name | `DEFAULT_WAREHOUSE_ID` |
| `{{ default_tenant_id_value }}` | Optional default tenant value (if not using constants module) | `"default_warehouse"` |
