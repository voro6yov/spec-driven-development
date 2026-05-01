---
name: file-upload-endpoint
description: File Upload Endpoint pattern for REST APIs. Use when accepting multipart/form-data file uploads, processing binary content server-side, or supporting mixed payloads with files and JSON/form fields.
user-invocable: false
disable-model-invocation: false
---

# File Upload Endpoint

## Purpose

- Handle file uploads via multipart/form-data requests.
- Support mixed payloads with both file uploads and JSON body fields.
- Process binary file content within endpoint handlers.

## Structure

- Use FastAPI's `UploadFile` for file parameters.
- Use `File()` for file field definitions.
- Use `Body()` for non-file form fields in mixed requests.
- Access file content via `.file.read()` or async `.read()`.

## Template Parameters

- `{{ router_name }}` - Name of the router variable
- `{{ endpoint_path }}` - URL path for the endpoint
- `{{ file_params }}` - List of file parameter definitions
- `{{ body_params }}` - List of body parameter definitions (for mixed requests)
- `{{ response_serializer }}` - Response model class name

## When to Use

Use file upload endpoints when:

- Accepting binary file uploads (images, documents, etc.)
- Processing uploaded file content server-side
- Supporting mixed form data with files and metadata
- Handling multiple file uploads in a single request

## Example

### Single File Upload

```python
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, File, UploadFile, status

from my_service.application import DocumentCommands
from my_service.containers import Containers

from ...endpoint_marker import MarkerRoute
from ...endpoint_visibility import Visibility
from ...serializers import UploadDocumentResponse

__all__ = ["documents_router"]

documents_router = APIRouter(prefix="/documents", tags=["Documents"], route_class=MarkerRoute)

@documents_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=UploadDocumentResponse,
)
@inject
def upload_document(
    document_file: UploadFile = File(..., alias="documentFile"),
    document_commands: DocumentCommands = Depends(Provide[Containers.document_commands]),
):
    return UploadDocumentResponse.from_domain(
        document_commands.upload(
            filename=document_file.filename,
            content=document_file.file.read(),
        ),
    )
```

### Mixed File Upload with Body Parameters

When you need both file uploads and form fields in the same request:

```python
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Body, Depends, File, UploadFile, status

from my_service.application import TireCommands
from my_service.containers import Containers

from ...endpoint_marker import MarkerRoute
from ...endpoint_visibility import Visibility
from ...serializers import StartIdentificationResponse

__all__ = ["tires_router"]

tires_router = APIRouter(prefix="/tires", tags=["Tires"], route_class=MarkerRoute)

@tires_router.post(
    "/files",
    status_code=status.HTTP_201_CREATED,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=StartIdentificationResponse,
)
@inject
def start_identification_with_files(
    conveyor_id: str | None = Body(None, alias="conveyorId"),
    upc_code: str | None = Body(None, alias="upcCode"),
    label_file: UploadFile = File(..., alias="labelFile"),
    sidewall_file: UploadFile = File(..., alias="sidewallFile"),
    secondary_sidewall_file: UploadFile | None = File(None, alias="secondarySidewallFile"),
    tire_commands: TireCommands = Depends(Provide[Containers.tire_commands]),
):
    return StartIdentificationResponse.from_domain(
        tire_commands.start_identification_with_files(
            conveyor_id=conveyor_id,
            label_filename=label_file.filename,
            label_file=label_file.file.read(),
            primary_sidewall_filename=sidewall_file.filename,
            primary_sidewall_file=sidewall_file.file.read(),
            secondary_sidewall_filename=secondary_sidewall_file.filename if secondary_sidewall_file else None,
            secondary_sidewall_file=secondary_sidewall_file.file.read() if secondary_sidewall_file else None,
            barcodes=[upc_code] if upc_code else None,
        ),
    )
```

### Multiple File Upload

```python
@documents_router.post(
    "/batch",
    status_code=status.HTTP_201_CREATED,
    openapi_extra={"visibility": Visibility.PUBLIC},
    response_model=BatchUploadResponse,
)
@inject
def upload_documents_batch(
    files: list[UploadFile] = File(...),
    document_commands: DocumentCommands = Depends(Provide[Containers.document_commands]),
):
    return BatchUploadResponse.from_domain(
        document_commands.upload_batch(
            files=[
                {"filename": f.filename, "content": f.file.read()}
                for f in files
            ],
        ),
    )
```

## Parameter Types

### File Parameters

```python
# Required file
document_file: UploadFile = File(...)

# Required file with alias
document_file: UploadFile = File(..., alias="documentFile")

# Optional file
document_file: UploadFile | None = File(None, alias="documentFile")

# Multiple files
files: list[UploadFile] = File(...)
```

### Body Parameters (Mixed Requests)

When mixing files with form fields, use `Body()` instead of Pydantic models:

```python
# Required body field with alias
conveyor_id: str = Body(..., alias="conveyorId")

# Optional body field
conveyor_id: str | None = Body(None, alias="conveyorId")
```

## UploadFile Properties

| Property | Type | Description |
| --- | --- | --- |
| `filename` | `str \ | None` |
| `file` | `SpooledTemporaryFile` | File-like object for reading |
| `content_type` | `str \ | None` |
| `size` | `int \ | None` |

## Reading File Content

### Synchronous (for small files)

```python
content = file.file.read()
```

### Asynchronous (recommended for large files)

```python
content = await file.read()
```

### Streaming (for very large files)

```python
async def process_large_file(file: UploadFile):
    while chunk := await file.read(1024 * 1024):  # 1MB chunks
        process_chunk(chunk)
```

## Content-Type Header

File upload endpoints automatically expect `multipart/form-data`:

```bash
curl -X POST "http://localhost:8000/api/service/v1/documents" \
  -H "Content-Type: multipart/form-data" \
  -F "documentFile=@/path/to/file.pdf"
```

For mixed requests:

```bash
curl -X POST "http://localhost:8000/api/service/v1/tires/files" \
  -F "conveyorId=conv-123" \
  -F "labelFile=@/path/to/label.jpg" \
  -F "sidewallFile=@/path/to/sidewall.jpg"
```

## Testing Guidance

- Test with valid file uploads and verify processing.
- Test file size limits and rejection of oversized files.
- Test optional file parameters with and without files.
- Test mixed requests with all combinations of body params.
- Test filename extraction and content reading.
- Mock file uploads in unit tests using `UploadFile` constructor.

### Test Example

```python
from fastapi.testclient import TestClient
from io import BytesIO

def test_upload_document(client: TestClient):
    file_content = b"test file content"
    response = client.post(
        "/api/service/v1/documents",
        files={"documentFile": ("test.pdf", BytesIO(file_content), "application/pdf")},
    )
    assert response.status_code == 201
```

---

## Template

```python
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter{% if body_params %}, Body{% endif %}, Depends, File, UploadFile, status

from {{ application_module }} import {{ command_class }}
from {{ containers_module }} import {{ containers_class_name }}

from ...endpoint_marker import MarkerRoute
from ...endpoint_visibility import Visibility
from ...serializers import {{ response_serializer }}

__all__ = ["{{ router_name }}"]

{{ router_name }} = APIRouter(prefix="{{ router_prefix }}", tags={{ router_tags }}, route_class=MarkerRoute)

@{{ router_name }}.post(
    "{{ endpoint_path }}",
    status_code=status.{{ status_code }},
    openapi_extra={"visibility": Visibility.{{ visibility }}},
    response_model={{ response_serializer }},
)
@inject
def {{ endpoint_function_name }}(
{% for param in body_params %}
    {{ param.name }}: {{ param.type }} = Body({{ param.default }}, alias="{{ param.alias }}"),
{% endfor %}
{% for param in file_params %}
    {{ param.name }}: {{ param.type }} = File({{ param.default }}{% if param.alias %}, alias="{{ param.alias }}"{% endif %}),
{% endfor %}
    {{ command_param }}: {{ command_class }} = Depends(Provide[{{ containers_class_name }}.{{ container_property }}]),
):
    return {{ response_serializer }}.from_domain(
        {{ command_param }}.{{ command_method }}({{ method_params }})
    )
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ application_module }}` | Application layer module | `my_service.application` |
| `{{ containers_module }}` | Containers module | `my_service.containers` |
| `{{ containers_class_name }}` | Containers class name | `Containers` |
| `{{ router_name }}` | Router variable name | `documents_router` |
| `{{ router_prefix }}` | URL prefix | `/documents` |
| `{{ router_tags }}` | OpenAPI tags | `["Documents"]` |
| `{{ endpoint_path }}` | Endpoint path | `""`, `"/files"` |
| `{{ status_code }}` | HTTP status code | `HTTP_201_CREATED` |
| `{{ visibility }}` | Endpoint visibility | `PUBLIC` |
| `{{ response_serializer }}` | Response model class | `UploadDocumentResponse` |
| `{{ endpoint_function_name }}` | Function name | `upload_document` |
| `{{ body_params }}` | List of body parameter definitions | See structure below |
| `{{ file_params }}` | List of file parameter definitions | See structure below |
| `{{ command_class }}` | Injected command class | `DocumentCommands` |
| `{{ command_param }}` | Command parameter name | `document_commands` |
| `{{ container_property }}` | Container property | `document_commands` |
| `{{ command_method }}` | Method to call | `upload` |
| `{{ method_params }}` | Method parameters | `filename=..., content=...` |

### Parameter Definition Structure

```python
# body_params
{"name": "conveyor_id", "type": "str | None", "default": "None", "alias": "conveyorId"}

# file_params
{"name": "label_file", "type": "UploadFile", "default": "...", "alias": "labelFile"}
{"name": "secondary_file", "type": "UploadFile | None", "default": "None", "alias": "secondaryFile"}
```
