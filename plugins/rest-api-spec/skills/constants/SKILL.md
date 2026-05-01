---
name: constants
description: Constants pattern for REST API services. Use when defining service-wide configuration values such as API routing prefixes, OpenAPI metadata, and messaging infrastructure names.
user-invocable: false
disable-model-invocation: false
---

# Constants

## Purpose

- Define service-wide configuration values used across API components.
- Centralize API routing prefixes and URLs.
- Provide consistent naming for queues, channels, and other infrastructure.

## Structure

- Single `constants.py` file at the project root level.
- Groups of related constants: API routing, messaging, destinations.
- All values are module-level constants (uppercase naming).

## Template Parameters

- `{{ project_name }}` - Kebab-case project name for URLs
- `{{ project_description }}` - Human-readable service description
- `{{ api_versions }}` - List of supported API versions
- `{{ has_internal_api }}` - Whether internal endpoints exist
- `{{ messaging_constants }}` - Queue/channel names (optional)

## Required Constants

### API Routing

| Constant | Purpose | Example |
| --- | --- | --- |
| `PROJECT_NAME` | Service identifier | `"tire-identification"` |
| `DESCRIPTION` | OpenAPI description | `"Tire Identification Service"` |
| `BASE_API_PREFIX` | Root URL prefix | `"/api/tire-identification"` |
| `V1_PREFIX` | Version 1 path segment | `"/v1"` |
| `V1_API_PREFIX` | Full v1 URL prefix | `"/api/tire-identification/v1"` |
| `SWAGGER_DOC_URL` | Swagger UI path | `"/docs"` |

### Optional Constants

| Constant | Purpose | Example |
| --- | --- | --- |
| `INTERNAL_PREFIX` | Internal endpoints path | `"/internal"` |
| `V2_PREFIX` | Version 2 path segment | `"/v2"` |
| `INTERNAL_API_PREFIX` | Full internal URL prefix | `"/api/tire-identification/internal"` |

## Example

```python
PROJECT_NAME = "tire-identification"
DESCRIPTION = "Tire Identification Service"
V1_PREFIX = "/v1"
V2_PREFIX = "/v2"
INTERNAL_PREFIX = "/internal"
BASE_API_PREFIX = "/api/tire-identification"
V1_API_PREFIX = BASE_API_PREFIX + V1_PREFIX
V2_API_PREFIX = BASE_API_PREFIX + V2_PREFIX
INTERNAL_API_PREFIX = BASE_API_PREFIX + INTERNAL_PREFIX
SWAGGER_DOC_URL = "/docs"

DOCUMENTS_EXCHANGER = "Documents"

EVENTS_QUEUE = "tire-identification-events"
METRICS_COLLECTION_QUEUE = "tire-identification-metrics-collection"
COMMANDS_QUEUE = "tire-identification-commands"

COMMANDS_CHANNEL = "TireIdentification"
COMMANDS_REPLIES_CHANNEL = "TireIdentificationReplies"

DEFAULT_WAREHOUSE_ID = "1"

TIRE_DESTINATION = "Tire"
CONVEYOR_DESTINATION = "Conveyor"
LOAD_DESTINATION = "Load"
```

## Usage

### In Entrypoint

```python
from my_service import constants

fastapi_app = FastAPI(
    title=constants.PROJECT_NAME,
    docs_url=f"{constants.V1_API_PREFIX}{constants.SWAGGER_DOC_URL}",
    description=constants.DESCRIPTION,
)
fastapi_app.include_router(api.v1_router, prefix=constants.BASE_API_PREFIX)
```

### In Auth Middleware

```python
from my_service import constants

PUBLIC_ENDPOINTS = (
    f"{constants.V1_API_PREFIX}/docs",
    f"{constants.V1_API_PREFIX}/openapi.json",
    f"{constants.BASE_API_PREFIX}/debug/500",
    f"{constants.BASE_API_PREFIX}/healthcheck",
)
INTERNAL_ENDPOINTS_PREFIX = f"{constants.BASE_API_PREFIX}/internal/"
```

## Naming Conventions

### Project Name

- Use kebab-case: `tire-identification`, `load-processing`
- Should match the URL path segment

### Prefixes

- Always start with `/`
- Use `_PREFIX` suffix for path segments
- Use `_API_PREFIX` suffix for full URL prefixes

### Queues and Channels

- Use project name as prefix: `tire-identification-events`
- Use PascalCase for channel names: `TireIdentification`

## Testing Guidance

- Verify constants are correctly composed (V1_API_PREFIX = BASE_API_PREFIX + V1_PREFIX).
- Test that all API routes use constants (no hardcoded URLs).
- Verify OpenAPI docs are accessible at configured URL.

---

## Template

```python
PROJECT_NAME = "{{ project_name }}"
DESCRIPTION = "{{ project_description }}"
V1_PREFIX = "/v1"
{% if 'v2' in api_versions %}
V2_PREFIX = "/v2"
{% endif %}
{% if has_internal_api %}
INTERNAL_PREFIX = "/internal"
{% endif %}
BASE_API_PREFIX = "/api/{{ project_name }}"
V1_API_PREFIX = BASE_API_PREFIX + V1_PREFIX
{% if 'v2' in api_versions %}
V2_API_PREFIX = BASE_API_PREFIX + V2_PREFIX
{% endif %}
{% if has_internal_api %}
INTERNAL_API_PREFIX = BASE_API_PREFIX + INTERNAL_PREFIX
{% endif %}
SWAGGER_DOC_URL = "/docs"
{% if messaging_constants %}

DOCUMENTS_EXCHANGER = "Documents"

EVENTS_QUEUE = "{{ project_name }}-events"
METRICS_COLLECTION_QUEUE = "{{ project_name }}-metrics-collection"
COMMANDS_QUEUE = "{{ project_name }}-commands"

COMMANDS_CHANNEL = "{{ commands_channel }}"
COMMANDS_REPLIES_CHANNEL = "{{ commands_channel }}Replies"
{% endif %}
{% if default_values %}

{% for key, value in default_values.items() %}
{{ key }} = "{{ value }}"
{% endfor %}
{% endif %}
{% if destinations %}

{% for dest in destinations %}
{{ dest | upper }}_DESTINATION = "{{ dest }}"
{% endfor %}
{% endif %}
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ project_name }}` | Kebab-case project name | `tire-identification` |
| `{{ project_description }}` | Service description | `Tire Identification Service` |
| `{{ api_versions }}` | List of versions | `["v1", "v2"]` |
| `{{ has_internal_api }}` | Has internal endpoints | `true` |
| `{{ messaging_constants }}` | Include messaging | `true` |
| `{{ commands_channel }}` | PascalCase channel name | `TireIdentification` |
| `{{ default_values }}` | Default config values | `{"DEFAULT_WAREHOUSE_ID": "1"}` |
| `{{ destinations }}` | Message destinations | `["Tire", "Conveyor", "Load"]` |
