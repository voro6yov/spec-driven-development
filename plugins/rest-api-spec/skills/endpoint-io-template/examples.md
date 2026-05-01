# Endpoint I/O Template — Worked Examples

Companion to `SKILL.md`. Two condensed end-to-end examples covering the conventions defined in `SKILL.md` for Tables 4, 5, and 6 of the REST API resource input spec.

---

## Example A — File

### Table 4: Response Fields

**Endpoint:** `GET /{id}`

| Field Name | Type | Source |
| --- | --- | --- |
| id | `str` | `FileInfo["id"]` |
| tenant_id | `str` | `FileInfo["tenant_id"]` |
| profile_id | `str` | `FileInfo["profile_id"]` |
| path | `str` | `FileInfo["path"]` |
| status | `str` | `FileInfo["status"]` |
| error | `str \| None` | `FileInfo["error"]` |
| created_at | `datetime` | `FileInfo["created_at"]` |
| updated_at | `datetime` | `FileInfo["updated_at"]` |
| preparation_result | `PreparationResult \| None` | `FileInfo["preparation_result"]` (includable) |
| text | `Text \| None` | `FileInfo["text"]` (includable) |
| classification_result | `ClassificationResult \| None` | `FileInfo["classification_result"]` (includable) |

**Query Parameters:** `GET /{id}`

| Param Name | Type | Default | Description |
| --- | --- | --- | --- |
| include | `list[str] \| None` | `None` | Optional list of heavy fields to include: `preparation_result`, `text`, `classification_result` (Wish List pattern) |

**Endpoint:** `GET /`

| Field Name | Type | Source |
| --- | --- | --- |
| files | `list[BriefFileInfo]` | `FileListResult["files"]` |
| total | `int` | `FileListResult["total"]` |

**Nested:** `BriefFileInfo`

| Field Name | Type | Source |
| --- | --- | --- |
| id | `str` | `BriefFileInfo["id"]` |
| tenant_id | `str` | `BriefFileInfo["tenant_id"]` |
| profile_id | `str` | `BriefFileInfo["profile_id"]` |
| name | `str` | `BriefFileInfo["name"]` |
| status | `str` | `BriefFileInfo["status"]` |
| error | `str \| None` | `BriefFileInfo["error"]` |
| created_at | `datetime` | `BriefFileInfo["created_at"]` |
| updated_at | `datetime` | `BriefFileInfo["updated_at"]` |

**Query Parameters:** `GET /`

| Param Name | Type | Default | Description |
| --- | --- | --- | --- |
| profile_id | `str` | — | Required. UUID of the profile to retrieve files for |
| status | `str \| None` | `None` | Optional exact-match filter on file status |
| name | `str \| None` | `None` | Optional partial-match filter on file name |
| offset | `int \| None` | `None` | Pagination offset (defaults to `0` from settings) |
| limit | `int \| None` | `None` | Pagination limit (defaults to `20` from settings) |

**Endpoint:** `GET /{id}/content`

*Binary response* — returns raw `bytes` (`application/octet-stream`). No JSON response body.

**Query Parameters:** `GET /{id}/content`

*No query parameters — `tenant_id` inherited from auth context.*

### Table 5: Request Fields

**Endpoint:** `POST /{id}/retry`

*No request body — uses path parameter only.*

**Endpoint:** `POST /{id}/document-types`

| Field Name | Type | Validation |
| --- | --- | --- |
| document_types | `list[DocumentTypeRequest]` | Required, non-empty list, each item must have a valid `kind` (not `unknown`) and optional `page_ranges` |

**Nested:** `DocumentTypeRequest`

| Field Name | Type | Validation |
| --- | --- | --- |
| kind | `str` | Required; must be a valid document kind (not `unknown`) |
| page_ranges | `list[PageRangeRequest] \| None` | Optional; for multi-document files |

### Table 6: Parameter Mapping

**Endpoint:** `POST /{id}/retry` (retry)

| Command Parameter | Request Field / Path Param |
| --- | --- |
| `id` | Path param `{id}` |
| `tenant_id` | Auth context |

**Endpoint:** `POST /{id}/document-types` (assign_document_types)

| Command Parameter | Request Field / Path Param |
| --- | --- |
| `id` | Path param `{id}` |
| `tenant_id` | Auth context |
| `document_types` | Request body `document_types` |

**Endpoint:** `GET /` (find_files)

| Query Parameter | Source |
| --- | --- |
| `profile_id` | Query param `profile_id` |
| `tenant_id` | Auth context |
| `filtering` | Constructed from query params `status`, `name` → `FileFiltering` |
| `pagination` | Constructed from query params `offset`, `limit` → `Pagination` (defaults from settings if None) |

**Endpoint:** `GET /{id}/content` (find_file_content)

| Query Parameter | Source |
| --- | --- |
| `id` | Path param `{id}` |
| `tenant_id` | Auth context |

---

## Example B — Document

### Table 4: Response Fields

**Endpoint:** `GET /{id}` (find_document)

| Field Name | Type | Source |
| --- | --- | --- |
| id | `str` | `DocumentInfo["id"]` |
| tenant_id | `str` | `DocumentInfo["tenant_id"]` |
| profile_id | `str` | `DocumentInfo["profile_id"]` |
| file_id | `str` | `DocumentInfo["file_id"]` |
| document_type_id | `str \| None` | `DocumentInfo["document_type_id"]` |
| document_type_kind | `str` | `DocumentInfo["document_type_kind"]` |
| document_type_reference | `Reference \| None` | `DocumentInfo["document_type_reference"]` |
| status | `str` | `DocumentInfo["status"]` |
| error | `str \| None` | `DocumentInfo["error"]` |
| subject_kind | `str \| None` | `DocumentInfo["subject_kind"]` |
| subject_entity | `IndividualData \| LegalEntityData \| None` | `DocumentInfo["subject_entity"]` |
| created_at | `datetime` | `DocumentInfo["created_at"]` |
| updated_at | `datetime` | `DocumentInfo["updated_at"]` |

### Table 5: Request Fields

**Endpoint:** `POST /{id}/corrections` (add_corrections)

| Field Name | Type | Validation |
| --- | --- | --- |
| tenant_id | `str` | Required; valid UUID |
| kind | `Literal["Individual", "LegalEntity"]` | Required; must match document subject kind |
| entity | `IndividualData \| LegalEntityData` | Required; validated against `ExtractionSchema` |

**Endpoint:** `POST /{id}/retry` (retry)

*No request body — `tenant_id` inherited from auth context.*

### Table 6: Parameter Mapping

**Endpoint:** `POST /{id}/corrections` (add_corrections)

| Command Parameter | Request Field / Path Param |
| --- | --- |
| `id` | Path param `{id}` |
| `tenant_id` | Auth context |
| `corrections` | Request body (`kind`, `entity`) |

**Endpoint:** `POST /{id}/retry` (retry)

| Command Parameter | Request Field / Path Param |
| --- | --- |
| `id` | Path param `{id}` |
| `tenant_id` | Auth context |
