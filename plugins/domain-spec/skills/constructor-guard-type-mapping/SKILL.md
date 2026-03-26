---
name: constructor-guard-type-mapping
description: Constructor Arguments and Guard Type Mapping reference for DDD Python. Use when declaring Guard descriptors, mapping Python types to correct runtime types, handling optional vs required fields, or understanding ImmutableCheck semantics.
user-invocable: false
disable-model-invocation: false
---

# Constructor Arguments and Guard Type Mapping

**Type:** Supporting

## Purpose

Define how domain model types map to guard declarations and constructor parameter type hints.

## Type mapping reference

### Required fields

| Domain Type | Guard Declaration | Constructor Parameter |
| --- | --- | --- |
| `str` | `Guard[str](str, ImmutableCheck())` | `name: str` |
| `int` | `Guard[int](int, ImmutableCheck())` | `quantity: int` |
| `bool` | `Guard[bool](bool)` | `enabled: bool` |
| `datetime` | `Guard[datetime](datetime, ImmutableCheck())` | `created_at: datetime` |
| `ValueObject` | `Guard[VO](VO, ImmutableCheck())` | `info: VO` |
| `TypedDict` | `Guard[SomeTypedDict](dict, ImmutableCheck())` | `data: SomeTypedDict` |
| `list[Item]` | `Guard[list[Item]](list, ImmutableCheck())` | `items: list[Item]` |

### Optional fields

| Domain Type | Guard Declaration | Constructor Parameter |
| --- | --- | --- |
| `str?` | `Guard[str](str)` | `name: str \| None` |
| `int?` | `Guard[int](int)` | `quantity: int \| None` |
| `datetime?` | `Guard[datetime](datetime)` | `started_at: datetime \| None` |
| `ValueObject?` | `Guard[VO](VO)` | `info: VO \| None` |
| `TypedDict?` | `Guard[SomeTypedDict](dict)` | `data: SomeTypedDict \| None` |
| `list[Item]?` | `Guard[list[Item]](list, ImmutableCheck())` | `items: list[Item] \| None` |

## Rules

1. **`ImmutableCheck` ≠ required**: `ImmutableCheck` prevents *reassignment*, not `None`. `NoneCheck` (built-in) rejects `None`.
2. **Optional assignment patterns**:
   ```python
   # Pattern A: Conditional assignment (datetime, value objects)
   if started_at is not None:
       self.started_at = started_at

   # Pattern B: Default to empty (lists)
   self.items = items or []
   ```
3. **Reserved names**: Use trailing underscore in constructor for Python reserved words:
   ```python
   def __init__(self, id_: str) -> None:
       self.id = id_
   ```
4. **Generic list runtime type**: Always use `list` (not `list[Item]`) as the runtime type in Guard:
   ```python
   Guard[list[RecognizedTire]](list, ImmutableCheck())  # correct
   ```
5. **TypedDict runtime type**: TypedDict is a type hint only; use `dict` as runtime type:
   ```python
   Guard[ExtractionInfo](dict, ImmutableCheck())  # correct
   ```
