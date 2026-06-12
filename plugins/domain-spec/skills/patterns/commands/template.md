# Commands Template

```python
from dataclasses import dataclass
from typing import ClassVar

from ..shared import Command, CommandReply

__all__ = ["{{ command_name }}", "{{ success_reply_name }}", "{{ failure_reply_name }}"]

@dataclass
class {{ command_name }}(Command):
    COMMAND_CHANNEL: ClassVar[str] = "{{ command_channel }}"
    REPLY_CHANNEL: ClassVar[str] = "{{ reply_channel }}"

    {{ correlation_field_1 }}: str
    {{ correlation_field_2 }}: str
    {{ aggregate_id }}: str
    {{ input_field_1 }}: {{ input_type_1 }}

@dataclass
class {{ success_reply_name }}(CommandReply):
    {{ correlation_field_1 }}: str
    {{ correlation_field_2 }}: str
    {{ aggregate_id }}: str
    {{ result_field_1 }}: {{ result_type_1 }}
    {{ result_field_2 }}: {{ result_type_2 }} | None

@dataclass
class {{ failure_reply_name }}(CommandReply):
    {{ correlation_field_1 }}: str
    {{ correlation_field_2 }}: str
    {{ aggregate_id }}: str
    error_message: str
```

## Placeholders — Command

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ command_name }}` | Imperative verb name | `StartLabelProcessing`, `ProcessSidewallImage` |
| `{{ command_channel }}` | Channel for command routing | `LabelProcessing`, `SidewallProcessing` |
| `{{ reply_channel }}` | Channel for reply routing | `TireIdentificationReplies`, `DocumentReplies` |
| `{{ correlation_field_1 }}` | First correlation identifier | `conveyor_id`, `session_id` |
| `{{ correlation_field_2 }}` | Second correlation identifier | `warehouse_id`, `tenant_id` |
| `{{ aggregate_id }}` | ID of target aggregate | `tire_id`, `document_id` |
| `{{ input_field_1 }}` | Input data for processing | `label_text`, `image_path` |
| `{{ input_type_1 }}` | Type of input data | `str`, `bytes`, `dict[str, str]` |

## Placeholders — Success Reply

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ success_reply_name }}` | Success reply class name | `LabelProcessingSuccess`, `SidewallProcessingSuccess` |
| `{{ result_field_1 }}` | Primary result field | `extracted_product_name`, `classification_result` |
| `{{ result_type_1 }}` | Type of primary result | `ExtractedProductName`, `ClassificationResult` |
| `{{ result_field_2 }}` | Secondary result field | `processing_time`, `confidence_score` |
| `{{ result_type_2 }}` | Type of secondary result | `float`, `dict[str, float]` |

## Placeholders — Failure Reply

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ failure_reply_name }}` | Failure reply class name | `LabelProcessingFailure`, `SidewallProcessingFailure` |

## Example

```python
from dataclasses import dataclass
from typing import ClassVar

from ..shared import Command, CommandReply

__all__ = ["StartLabelProcessing", "LabelProcessingSuccess", "LabelProcessingFailure"]

@dataclass
class StartLabelProcessing(Command):
    COMMAND_CHANNEL: ClassVar[str] = "LabelProcessing"
    REPLY_CHANNEL: ClassVar[str] = "TireIdentificationReplies"

    conveyor_id: str
    warehouse_id: str
    tire_id: str
    label_text: str

@dataclass
class LabelProcessingSuccess(CommandReply):
    conveyor_id: str
    warehouse_id: str
    tire_id: str
    extracted_product_name: str
    score: dict[str, float] | None

@dataclass
class LabelProcessingFailure(CommandReply):
    conveyor_id: str
    warehouse_id: str
    tire_id: str
    error_message: str
```

## Aggregate queuing commands

```python
def request_label_processing(self, label_text: str) -> None:
    self.commands.append(
        StartLabelProcessing(
            conveyor_id=self.conveyor_id,
            warehouse_id=self.warehouse_id,
            tire_id=self.id,
            label_text=label_text,
        )
    )
```
