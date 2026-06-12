---
name: settings
description: Settings pattern for application service configuration. Use when defining configuration defaults with Pydantic BaseSettings, or supporting environment variable overrides.
user-invocable: false
disable-model-invocation: false
---

# Settings

Purpose: Provide configuration defaults for application services using Pydantic BaseSettings

## Purpose

- Provide configuration defaults for application services.
- Use Pydantic BaseSettings for type-safe configuration with environment variable support.

## Structure

- Extend `BaseSettings` from `pydantic_settings`.
- Provide sensible defaults for all settings.
- Use descriptive names that indicate the setting's purpose.

## Behavior checklist

- Provide default values that work for development environments.
- Use descriptive property names that indicate units or constraints.
- Export settings class in `__all__`.

## Testing guidance

- Write unit tests that verify default values.
- Test settings can be overridden via environment variables (if using Pydantic BaseSettings).

---

## Template

```python
from pydantic_settings import BaseSettings

__all__ = ["{{ settings_class_name }}"]

class {{ settings_class_name }}(BaseSettings):
    default_per_page: int = 10
    default_page: int = 0
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ settings_class_name }}` | Name of the settings class | `LoadQueriesSettings`, `ProfileQueriesSettings` |
