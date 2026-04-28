---
name: settings
description: Settings pattern for application service configuration. Use when defining configuration defaults with Pydantic BaseSettings, grouping related settings into nested classes, or supporting environment variable overrides.
user-invocable: false
disable-model-invocation: false
---

# Settings

Purpose: Provide configuration defaults for application services using Pydantic BaseSettings

## Purpose

- Provide configuration defaults for application services.
- Use Pydantic BaseSettings for type-safe configuration with environment variable support.
- Group related settings into nested classes.

## Structure

- Extend `BaseSettings` from `pydantic_settings`.
- Define nested settings classes (e.g., `PaginationSettings`) for logical grouping.
- Provide sensible defaults for all settings.
- Use descriptive names that indicate the setting's purpose.

## Behavior checklist

- Group related settings into nested classes (e.g., `pagination: PaginationSettings`).
- Provide default values that work for development environments.
- Use descriptive property names that indicate units or constraints.
- Export settings class in `__all__`.

## Testing guidance

- Write unit tests that verify default values.
- Test settings can be overridden via environment variables (if using Pydantic BaseSettings).
- Verify nested settings are properly initialized.

---

## Template

```python
from pydantic_settings import BaseSettings

__all__ = ["{{ settings_class_name }}"]

class PaginationSettings(BaseSettings):
    default_per_page: int = 10
    default_page: int = 0

class {{ settings_class_name }}(BaseSettings):
    pagination: PaginationSettings = PaginationSettings()
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ settings_class_name }}` | Name of the settings class | `LoadQueriesSettings`, `ProfileQueriesSettings` |

The template includes a standard `PaginationSettings` nested class. If you need additional nested settings, extend the template.
