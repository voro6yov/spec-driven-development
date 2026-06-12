# Guards and Checks Template

```python
from typing import Any

from ..shared import Guard, ImmutableCheck
from ..shared.guard import AttributeName, Check, IllegalArgument

class {{ check_name }}(Check[Any]):
    def __init__(self, pattern: str) -> None:
        self._pattern = pattern

    def is_correct(self, domain_obj: Any, value: str, attribute_name: AttributeName) -> None:
        if not value or not value.strip():
            raise IllegalArgument(
                f"Attribute {attribute_name.public} for {domain_obj.__class__.__name__} should not be empty."
            )

        if not value.startswith(self._pattern):
            raise IllegalArgument(
                f"Attribute {attribute_name.public} for {domain_obj.__class__.__name__} should start with {self._pattern}."
            )

class {{ guarded_type_name }}:
    code = Guard[str](str, ImmutableCheck(), {{ check_name }}("PREFIX-"))

    def __init__(self, code: str) -> None:
        self.code = code
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ check_name }}` | Custom check class name | `PrefixCheck`, `EmailFormatCheck` |
| `{{ guarded_type_name }}` | Type using the guard | `ProductCode`, `UserEmail` |

## Example

```python
class EmailFormatCheck(Check[Any]):
    def is_correct(self, domain_obj: Any, value: str, attribute_name: AttributeName) -> None:
        if "@" not in value:
            raise IllegalArgument(
                f"Attribute {attribute_name.public} for {domain_obj.__class__.__name__} must be a valid email."
            )

class User:
    email = Guard[str](str, ImmutableCheck(), EmailFormatCheck())

    def __init__(self, email: str) -> None:
        self.email = email
```
