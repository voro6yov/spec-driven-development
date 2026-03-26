---
name: commands
description: Commands pattern for DDD Python. Use when implementing command dataclasses for message-driven architectures, request-reply semantics with success/failure replies, or when the spec contains <<Command>> stereotype.
user-invocable: false
disable-model-invocation: false
---

# Commands Pattern

**Type:** Primary

## Purpose

- Define intent to perform an action or state change in a message-driven architecture.
- Enable asynchronous processing with request-reply semantics (command → success/failure replies).
- Decouple command initiators from processors via channels.

## Structure

- Commands are `@dataclass` descendants of `Command` base class.
- Named with imperative verb (e.g., `StartLabelProcessing`, `ProcessSidewallImage`).
- Declare `COMMAND_CHANNEL` and `REPLY_CHANNEL` as `ClassVar[str]` for message routing.
- Contain only the data required to execute the action.
- Always have corresponding Success and Failure reply dataclasses.

## Command vs Event

| Aspect | Command | Event |
| --- | --- | --- |
| **Intent** | Request to do something | Notification that something happened |
| **Naming** | Imperative verb (`Start...`, `Process...`) | Past tense (`...Created`, `...Completed`) |
| **Reply** | Expects success/failure | No reply expected |
| **Channels** | Command + Reply channels | Event channel only |

## File organization

- Group command, success reply, and failure reply in the same file.
- Name file after the operation (e.g., `label_processing.py`).

## Usage patterns

- Commands are queued by aggregates alongside events (`self.commands.append(...)`).
- Application layer publishes commands to `COMMAND_CHANNEL`.
- Processors consume from channel, execute, and reply to `REPLY_CHANNEL`.

## Testing guidance

- Assert command payloads contain all required fields for processing.
- Verify success replies include all result data.
- Verify failure replies include meaningful error messages.
- Test that correlation identifiers propagate through command → reply flow.

## Template

See [template.md](template.md) for the full Python template with Jinja2 placeholders and examples.
