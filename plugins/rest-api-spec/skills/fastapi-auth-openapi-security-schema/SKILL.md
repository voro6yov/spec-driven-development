---
name: fastapi-auth-openapi-security-schema
description: FastAPI Auth (OpenAPI Security Schema) pattern for REST API. Use when configuring OpenAPI security schemes for Swagger UI, enabling the Authorize button, or defining JWT Bearer authentication for FastAPI apps.
user-invocable: false
disable-model-invocation: false
---

# FastAPI Auth (OpenAPI Security Schema)

## Purpose

- Configure OpenAPI security scheme for Swagger UI.
- Enable "Authorize" button in documentation.
- Define JWT Bearer authentication format.

## Structure

- Function that modifies FastAPI's OpenAPI schema.
- Adds security scheme definition.
- Applies security globally to all endpoints.

## Template Parameters

- `{{ auth_scheme_name }}` - Name for the security scheme (e.g., "Bearer Auth")
- `{{ bearer_format }}` - Token format (e.g., "JWT")

## Example

```python
__all__ = ["add_auth_to_openapi"]

def add_auth_to_openapi(fastapi_app):
    from fastapi.openapi.utils import get_openapi

    security_schema = {
        "securitySchemes": {
            "Bearer Auth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            },
        },
    }

    def custom_openapi():
        if fastapi_app.openapi_schema:
            return fastapi_app.openapi_schema

        openapi_schema = get_openapi(
            title=fastapi_app.title,
            version=fastapi_app.version,
            routes=fastapi_app.routes,
        )

        schema_components = openapi_schema.get("components")
        if schema_components:
            openapi_schema["components"].update(security_schema)
        else:
            openapi_schema["components"] = security_schema

        openapi_schema["security"] = [{"Bearer Auth": []}]

        fastapi_app.openapi_schema = openapi_schema
        return fastapi_app.openapi_schema

    fastapi_app.openapi = custom_openapi
```

## How It Works

1. **Define security scheme**: JWT Bearer authentication configuration.
2. **Override openapi method**: Replace FastAPI's default schema generator.
3. **Add components**: Inject security scheme into OpenAPI components.
4. **Apply globally**: Set security requirement for all endpoints.

## Usage in Entrypoint

```python
def register_auth(app: FastAPI):
    api.add_auth_to_openapi(app)
    # ... register middleware
```

## Swagger UI Result

After applying:

- "Authorize" button appears in Swagger UI
- Users can enter Bearer token
- Token is sent in Authorization header for all requests

## Testing Guidance

- Verify OpenAPI schema contains securitySchemes.
- Test Swagger UI shows Authorize button.
- Test authenticated requests include Authorization header.

---

## Template

```python
__all__ = ["add_auth_to_openapi"]

def add_auth_to_openapi(fastapi_app):
    from fastapi.openapi.utils import get_openapi

    security_schema = {
        "securitySchemes": {
            "{{ auth_scheme_name }}": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "{{ bearer_format }}",
            },
        },
    }

    def custom_openapi():
        if fastapi_app.openapi_schema:
            return fastapi_app.openapi_schema

        openapi_schema = get_openapi(
            title=fastapi_app.title,
            version=fastapi_app.version,
            routes=fastapi_app.routes,
        )

        schema_components = openapi_schema.get("components")
        if schema_components:
            openapi_schema["components"].update(security_schema)
        else:
            openapi_schema["components"] = security_schema

        openapi_schema["security"] = [{"{{ auth_scheme_name }}": []}]

        fastapi_app.openapi_schema = openapi_schema
        return fastapi_app.openapi_schema

    fastapi_app.openapi = custom_openapi
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ auth_scheme_name }}` | Name for security scheme | `Bearer Auth` |
| `{{ bearer_format }}` | Token format description | `JWT` |
