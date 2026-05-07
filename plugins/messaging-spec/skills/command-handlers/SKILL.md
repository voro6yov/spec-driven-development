---
name: command-handlers
description: Command Handlers pattern for processing commands from pubsub queues. Use when implementing handlers that consume CommandMessage instances, invoke application services, and send success or failure reply messages back to the calling service.
user-invocable: false
disable-model-invocation: false
---

# Command Handlers

Category: Handler Pattern

## Purpose

- Process commands received from pubsub queues.
- Execute the requested action via application layer services.
- Return success or failure reply to the calling service.

## Distinction from Event Handlers

| Aspect | Command Handlers | Event Handlers |
| --- | --- | --- |
| **Input type** | `CommandMessage[CommandType]` | `DomainEventEnvelope[EventType]` |
| **Return value** | List of `CommandHandlerReplyBuilder` results | `None` |
| **Response** | Must send reply back | No reply expected |
| **Reply channel** | From `CommandMessageHeaders.REPLY_TO` | N/A |

## Structure

- Implemented as functions decorated with `@inject` for dependency injection.
- Accept `CommandMessage[CommandType]` as the first parameter.
- Use dependency injection to access application layer services.
- Build and return reply messages using `CommandHandlerReplyBuilder`.

## Template Parameters

When using the template, replace these placeholders with your project-specific values:

- `{{ application_module }}` - Module path for application layer (e.g., `my_project.application`)
- `{{ service_class_name }}` - Name of the application service class
- `{{ containers_module }}` - Module path for dependency injection containers
- `{{ containers_class_name }}` - Name of the containers class (e.g., `Containers`)
- `{{ container_property_name }}` - Property name on containers for the service instance
- `{{ command_class_name }}` - Name of the command class to handle
- `{{ handler_function_name }}` - Name of the handler function
- `{{ service_param_name }}` - Parameter name for the injected service
- `{{ service_method_name }}` - Method name on service to call
- `{{ service_method_params }}` - Parameters to pass to service method
- `{{ success_reply_class }}` - Success reply command class
- `{{ failure_reply_class }}` - Failure reply command class
- `{{ success_reply_construction }}` - How to construct success reply
- `{{ failure_reply_construction }}` - How to construct failure reply

## Example

```python
import logging
from typing import cast

from dependency_injector.wiring import Provide, inject
from deps_pubsub.commands.common import CommandMessageHeaders, make_message_for_command
from deps_pubsub.commands.consumer import CommandHandlerReplyBuilder
from deps_pubsub.commands.consumer.command_message import CommandMessage
from deps_pubsub.events.mappers import JsonMapper

from my_project.application import LabelProcessingService
from my_project.containers import Containers

from .commands import (
    LabelProcessingFailure,
    LabelProcessingSuccess,
    StartLabelProcessing,
)

logger = logging.getLogger(__name__)

@inject
def start_label_processing_command_handler(
    command_message: CommandMessage[StartLabelProcessing],
    application: LabelProcessingService = Provide[Containers.label_processing_service],
):
    command: StartLabelProcessing = command_message.command
    replies_channel = command_message.message.headers[CommandMessageHeaders.REPLY_TO]

    result = application.process_label(
        conveyor_id=command.conveyor_id,
        warehouse_id=command.warehouse_id,
        tire_id=command.tire_id,
        label_text=command.label_text,
    )

    if result.is_success:
        command_reply = LabelProcessingSuccess(
            conveyor_id=result.conveyor_id,
            warehouse_id=result.warehouse_id,
            tire_id=result.tire_id,
            extracted_product_name=result.extracted_product_name,
            checklist=result.checklist,
            score=cast(dict[str, float] | None, result.score),
            processing_time=result.processing_time,
        )
    else:
        command_reply = LabelProcessingFailure(
            conveyor_id=result.conveyor_id,
            warehouse_id=result.warehouse_id,
            tire_id=result.tire_id,
            error_message=result.error_message,
        )

    message_reply = make_message_for_command(
        channel=replies_channel,
        payload=JsonMapper().serialize(command_reply),
        command_type=command_reply.__class__.__name__,
        reply_to="NONE",
    )

    return [CommandHandlerReplyBuilder.with_success(message_reply)]
```

## Reply Construction Pattern

The reply is built in three steps:

1. **Determine success or failure** based on application result
2. **Construct reply command** with appropriate fields
3. **Serialize and send** using `make_message_for_command`

```python
# 1. Get reply channel from incoming message headers
replies_channel = command_message.message.headers[CommandMessageHeaders.REPLY_TO]

# 2. Build reply command (success or failure)
command_reply = SuccessReply(...) if success else FailureReply(...)

# 3. Create message and return
message_reply = make_message_for_command(
    channel=replies_channel,
    payload=JsonMapper().serialize(command_reply),
    command_type=command_reply.__class__.__name__,
    reply_to="NONE",
)
return [CommandHandlerReplyBuilder.with_success(message_reply)]
```

## Testing Guidance

- Test handlers with valid command messages and verify service calls.
- Test both success and failure paths.
- Verify correct reply commands are constructed with correct fields.
- Verify reply is sent to the correct channel from headers.

---

## Template

```python
import logging

from dependency_injector.wiring import Provide, inject
from deps_pubsub.commands.common import CommandMessageHeaders, make_message_for_command
from deps_pubsub.commands.consumer import CommandHandlerReplyBuilder
from deps_pubsub.commands.consumer.command_message import CommandMessage
from deps_pubsub.events.mappers import JsonMapper

from {{ application_module }} import {{ service_class_name }}
from {{ containers_module }} import {{ containers_class_name }}

from .commands import (
    {{ command_class_name }},
    {{ success_reply_class }},
    {{ failure_reply_class }},
)

logger = logging.getLogger(__name__)

@inject
def {{ handler_function_name }}(
    command_message: CommandMessage[{{ command_class_name }}],
    {{ service_param_name }}: {{ service_class_name }} = Provide[{{ containers_class_name }}.{{ container_property_name }}],
):
    command: {{ command_class_name }} = command_message.command
    replies_channel = command_message.message.headers[CommandMessageHeaders.REPLY_TO]

    result = {{ service_param_name }}.{{ service_method_name }}(
        {{ service_method_params }}
    )

    if result.is_success:
        command_reply = {{ success_reply_class }}(
            {{ success_reply_construction }}
        )
    else:
        command_reply = {{ failure_reply_class }}(
            {{ failure_reply_construction }}
        )

    message_reply = make_message_for_command(
        channel=replies_channel,
        payload=JsonMapper().serialize(command_reply),
        command_type=command_reply.__class__.__name__,
        reply_to="NONE",
    )

    return [CommandHandlerReplyBuilder.with_success(message_reply)]
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ application_module }}` | Module path for application layer | `my_project.application` |
| `{{ service_class_name }}` | Name of the application service class | `LabelProcessingService` |
| `{{ containers_module }}` | Module path for DI containers | `my_project.containers` |
| `{{ containers_class_name }}` | Name of the containers class | `Containers` |
| `{{ container_property_name }}` | Property on containers for service | `label_processing_service` |
| `{{ command_class_name }}` | Name of the command class | `StartLabelProcessing` |
| `{{ handler_function_name }}` | Name of the handler function | `start_label_processing_command_handler` |
| `{{ service_param_name }}` | Parameter name for injected service | `application` |
| `{{ service_method_name }}` | Method name on service to call | `process_label` |
| `{{ service_method_params }}` | Parameters to pass to service | `conveyor_id=command.conveyor_id` |
| `{{ success_reply_class }}` | Success reply command class | `LabelProcessingSuccess` |
| `{{ failure_reply_class }}` | Failure reply command class | `LabelProcessingFailure` |
| `{{ success_reply_construction }}` | Success reply field assignments | `tire_id=result.tire_id,\n            data=result.data` |
| `{{ failure_reply_construction }}` | Failure reply field assignments | `tire_id=result.tire_id,\n            error_message=result.error_message` |
