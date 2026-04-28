---
name: queries-methods-template
description: Queries Methods Template pattern for application service query specs. Use when filling the Method Specifications section of a `<AggregateRoot>Queries` spec.
user-invocable: false
disable-model-invocation: false
---

# Queries Methods Template

Documents one entry per public method on a `<AggregateRoot>Queries` application service. Each method has the same three subsections: **Purpose**, **Method Flow**, **Returns**. Dependencies, preconditions, and error handling are either captured at the service level or expressed directly inside the flow.

**Pattern Reference**: `application-spec:queries`

---

## Canonical Method Shape

The dominant shape is `load → return`. Use it as the default and only deviate where the method genuinely differs (e.g. raises on missing, applies pagination defaults, calls an external interface). Express deviations as different flow steps, not as a different template.

```
### Method: `method_name(param1: type, param2: type) -> ReturnType`

**Purpose**: [One-liner describing what this method returns]

**Method Flow**:

1. Call `query_repository.<lookup_method>(<params>)` to retrieve the read model
2. Return the result

**Returns**:

- [Shape of the returned DTO / value object]
- If the method tolerates absence, type the return as `ReturnType | None` and document what `None` means (record missing, optional data not yet populated, etc.). Use this default when callers can handle a missing record gracefully — otherwise apply the *Not-Found Raises* deviation.
```

---

## Deviation: Not-Found Raises

Used when the absence of a record is an error condition. Adds an explicit raise step between load and return.

```
**Method Flow**:

1. Call `query_repository.<lookup_method>(<params>)` to retrieve the read model
2. If the result is `None`, raise `<Aggregate>NotFoundError`
3. Return the result

**Returns**:

- [DTO shape]
- Raises `<Aggregate>NotFoundError` when no record exists for the given key
```

---

## Deviation: Paginated List with Defaults

Used when a method returns a paginated list and the service applies pagination defaults from settings before delegating to the repository.

```
**Method Flow**:

1. If `pagination` is `None`, build defaults from `settings`
   (`pagination = Pagination(page=settings.pagination.default_page, per_page=settings.pagination.default_per_page)`)
2. Call `query_repository.<list_method>(<params>, filtering, pagination)` to retrieve the page
3. Return the result

**Returns**:

- `<Aggregate>ListResult` containing `items: list[<BriefDTO>]` and `total: int`
- Empty list with `total=0` when no records match
```

---

## Deviation: External Interface Call (two-step)

Used when the method combines a repository lookup with a call to an injected external interface (e.g. file storage, downstream service). Optionally includes a path / key transformation between the two calls.

```
**Method Flow**:

1. Call `query_repository.<resolve_method>(<params>)` to resolve the path / key
2. If the result is `None`, raise `<Aggregate>NotFoundError`
3. (Optional) Transform the resolved path / key
   (e.g. derive a redacted variant from the original path)
4. Call `<external_interface>.<operation>(<resolved_or_transformed>)` to retrieve the payload
5. Return the result

**Returns**:

- [Payload type, e.g. `bytes`]
- Raises `<Aggregate>NotFoundError` when no record exists for the given key
- Infrastructure errors from the external interface propagated to the caller
```

---

## Worked examples

The four examples below cover the canonical shape and each deviation. Each example shows the **Method Flow** block only; the surrounding Purpose and Returns subsections follow the canonical template.

### Example 1 — Canonical, None-tolerant (`find_file_text` on `FileQueries`)

```
1. Call `query_repository.find_file_text(id, tenant_id)` to retrieve the extracted text
2. Return the result
```

### Example 2 — Not-Found Raises (`find_file` on `FileQueries`)

```
1. Call `query_repository.find_file(id, tenant_id, include)` to retrieve the file data
2. If the result is `None`, raise `FileNotFoundError`
3. Return the `FileInfo` result
```

### Example 3 — Paginated List with Defaults (`find_files` on `FileQueries`)

```
1. If `pagination` is `None`, build defaults from `settings`
   (`pagination = Pagination(page=settings.pagination.default_page, per_page=settings.pagination.default_per_page)`)
2. Call `query_repository.find_files(profile_id, tenant_id, filtering, pagination)` to retrieve the page
3. Return the `FileListResult` result
```

### Example 4 — External Interface + path transform (`find_file_redacted_content` on `FileQueries`)

```
1. Call `query_repository.find_file_path(id, tenant_id)` to resolve the original storage path
2. If the result is `None`, raise `FileNotFoundError`
3. Derive `redacted_path` from the original path by inserting `-redacted` before the file extension
   (e.g. `s3://bucket/docs/file.pdf` → `s3://bucket/docs/file-redacted.pdf`)
4. Call `file_storage.download(redacted_path)` to retrieve the binary content
5. Return the `bytes` result
```
