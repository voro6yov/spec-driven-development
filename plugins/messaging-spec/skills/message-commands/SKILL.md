---
name: message-commands
description: Message Commands pattern for messaging modules. Use when defining commands received from other services that request specific actions and require a success/failure reply.
user-invocable: false
disable-model-invocation: false
---

# Message Commands

Category: Command Pattern

## Purpose

- Represent commands received from other services requesting specific actions.
- Define the contract for commands consumed from external bounded contexts.
- Enable request-response messaging patterns between services.

## Distinction from Events

Commands are **imperative** requests for action, while events are **notifications** of past occurrences.

| Aspect | Commands | Events |
| --- | --- | --- |
| **Intent** | Request action | Notify occurrence |
| **Direction** | Request-response | Fire-and-forget |
| **Naming** | Imperative verb (e.g., `StartLabelProcessing`) | Past-tense verb (e.g., `LabelProcessingSucceeded`) |
| **Base Class** | `Command` from `deps_pubsub.commands.common` | `DomainEvent` from `deps_pubsub.events.common` |
| **Response** | Required (success/failure reply) | None |

## Structure

- Implemented as `@dataclass` classes extending `Command` from `deps_pubsub.commands.common`.
- Named after the imperative action (e.g., `StartLabelProcessing`, `ProcessDocument`).
- Declared in `commands/` submodule within the messaging module.
- Include all fields needed to execute the requested action.

## Template Parameters

When using the template, replace these placeholders with your project-specific values:

- `{{ command_name }}` - Name of the command class (e.g., `StartLabelProcessing`)
- `{{ command_fields }}` - Dataclass field definitions (e.g., `conveyor_id: str\n    warehouse_id: str`)

## Example

```python
from dataclasses import dataclass

from deps_pubsub.commands.common import Command

__all__ = ["StartLabelProcessing"]

@dataclass
class StartLabelProcessing(Command):
    conveyor_id: str
    warehouse_id: str
    tire_id: str
    label_text: str
```

## Usage Patterns

- Each command represents a distinct action requested by an external service.
- Commands are immutable data carriers with no behavior.
- Commands are imported in dispatcher factories and used as type parameters in handlers.
- Commands always expect a reply (success or failure).

## Routing

Commands use **channels** (not destinations like events):

```python
# constants.py
COMMANDS_CHANNEL = "LabelProcessing"
COMMANDS_QUEUE = "label-processing-commands"
```

## Testing Guidance

- Assert full command payloads to ensure all fields are correctly populated.
- Test command construction with various combinations of required and optional fields.
- Verify commands can be deserialized from the message broker format.

---

## Template

```python
from dataclasses import dataclass

from deps_pubsub.commands.common import Command

__all__ = ["{{ command_name }}"]

@dataclass
class {{ command_name }}(Command):
    {{ command_fields }}
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ command_name }}` | Name of the command class | `StartLabelProcessing`, `ProcessDocument` |
| `{{ command_fields }}` | Dataclass field definitions | `conveyor_id: str\n    warehouse_id: str` |
