---
name: domain-exceptions
description: Domain Exceptions pattern for DDD Python. Use when implementing typed domain errors, business rule violations, not-found errors, conflict exceptions, or translating domain failures into HTTP responses.
user-invocable: false
disable-model-invocation: false
---

# Domain Exceptions Pattern

**Type:** Supporting

## Purpose

- Provide typed errors that express business rule violations without leaking infrastructure concerns.
- Enable the application layer to translate domain failures into API/error responses consistently.
- Carry machine-readable codes and human-readable messages for downstream handling.

## Exception hierarchy

```
DomainException          # Root; generic domain error
├── NotFound             # Entity/concept does not exist → HTTP 404
├── AlreadyExists        # Duplicate entity → HTTP 409
├── Conflict             # Business rule violation → HTTP 409
├── Unauthorized         # Authentication required → HTTP 401
└── Forbidden            # Permission denied → HTTP 403
```

## Required elements

1. `__all__` at module top — lists all exported exceptions
2. Import base exceptions from `..shared` (relative import within domain)
3. Class-level `code` attribute — snake_case, unique identifier for API responses
4. `__init__` with contextual parameters — accepts identifiers and context values
5. Descriptive f-string message — human-readable, includes all relevant identifiers
6. Call `super().__init__(message)`

## Naming conventions

| Element | Convention | Example |
| --- | --- | --- |
| Class name | PascalCase, verb/noun phrase | `LoadNotFound`, `LineItemAlreadyReceived` |
| Code attribute | snake_case matching class | `load_not_found`, `line_item_already_received` |
| Constructor params | Descriptive identifiers | `load_id`, `warehouse_id`, `item_number` |

## Checklist

- [ ] Exception extends appropriate shared base (`NotFound`, `AlreadyExists`, `Conflict`, `DomainException`)
- [ ] `code` attribute is snake_case and unique within domain
- [ ] Constructor accepts all identifiers needed for descriptive message
- [ ] Message is human-readable and includes all contextual identifiers
- [ ] Exception is listed in module's `__all__`

## Testing guidance

Assert both exception type and message for stable error contracts:

```python
def test_raises_load_not_found():
    with pytest.raises(LoadNotFound) as exc_info:
        service.get_load("nonexistent", "warehouse-1")

    assert exc_info.value.code == "load_not_found"
    assert "nonexistent" in str(exc_info.value)
    assert "warehouse-1" in str(exc_info.value)
```

## Template

See [template.md](template.md) for the full Python template with Jinja2 placeholders and additional exception patterns.
