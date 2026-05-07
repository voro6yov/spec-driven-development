---
name: command-replies
description: Command Replies pattern for messaging command handlers. Use when defining structured success and failure response types for the request-response command pattern.
user-invocable: false
disable-model-invocation: false
---

# Command Replies

Category: Command Pattern

## Purpose

- Define success and failure response types for command handlers.
- Provide structured response payloads for the request-response pattern.
- Enable the calling service to process results appropriately.

## Structure

Command replies are defined as **pairs**:

- **Success reply** - Contains the positive outcome data
- **Failure reply** - Contains error information

Both extend `Command` from `deps_pubsub.commands.common` and are typically defined alongside the incoming command.

## Naming Conventions

| Type | Pattern | Example |
| --- | --- | --- |
| Success | `{Action}Success` | `LabelProcessingSuccess` |
| Failure | `{Action}Failure` | `LabelProcessingFailure` |

## Template Parameters

When using the template, replace these placeholders with your project-specific values:

- `{{ action_name }}` - Base name of the action (e.g., `LabelProcessing`)
- `{{ success_fields }}` - Fields for success response
- `{{ failure_fields }}` - Fields for failure response (typically includes `error_message: str`)
- `{{ common_fields }}` - Fields common to both success and failure (e.g., correlation IDs)

## Example

```python
from dataclasses import dataclass
from typing import Any

from deps_pubsub.commands.common import Command

__all__ = [
    "StartLabelProcessing",
    "LabelProcessingSuccess",
    "LabelProcessingFailure",
]

@dataclass
class StartLabelProcessing(Command):
    conveyor_id: str
    warehouse_id: str
    tire_id: str
    label_text: str

@dataclass
class LabelProcessingSuccess(Command):
    conveyor_id: str
    warehouse_id: str
    tire_id: str
    extracted_product_name: dict[str, Any]
    checklist: dict[str, str]
    score: dict[str, float] | None
    processing_time: float | None

@dataclass
class LabelProcessingFailure(Command):
    conveyor_id: str
    warehouse_id: str
    tire_id: str
    error_message: str
```

## Usage Patterns

- Group incoming command with its reply types in the same module.
- Include correlation fields (IDs) in both success and failure to enable response routing.
- Failure replies should always include `error_message` for debugging.
- Success replies should include all data needed by the caller.

## Constants for Reply Routing

Define a reply channel constant:

```python
# constants.py
COMMANDS_CHANNEL = "LabelProcessing"
COMMANDS_REPLIES_CHANNEL = "LabelProcessingReplies"
COMMANDS_QUEUE = "label-processing-commands"
```

## Testing Guidance

- Test both success and failure reply construction.
- Verify correlation fields match between request and response.
- Test serialization/deserialization of complex field types.

---

## Template

```python
from dataclasses import dataclass
from typing import Any

from deps_pubsub.commands.common import Command

__all__ = [
    "{{ command_name }}",
    "{{ action_name }}Success",
    "{{ action_name }}Failure",
]

@dataclass
class {{ command_name }}(Command):
    {{ command_fields }}

@dataclass
class {{ action_name }}Success(Command):
    {{ common_fields }}
    {{ success_fields }}

@dataclass
class {{ action_name }}Failure(Command):
    {{ common_fields }}
    error_message: str
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ command_name }}` | Name of the incoming command | `StartLabelProcessing` |
| `{{ action_name }}` | Base action name for replies | `LabelProcessing` |
| `{{ command_fields }}` | Fields for the incoming command | `tire_id: str\n    label_text: str` |
| `{{ common_fields }}` | Fields common to both replies (correlation IDs) | `conveyor_id: str\n    warehouse_id: str\n    tire_id: str` |
| `{{ success_fields }}` | Additional fields for success response | `extracted_data: dict[str, Any]\n    processing_time: float` |
