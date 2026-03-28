# Pattern Selection Examples

## Example 1: Simple Aggregate

```mermaid
classDiagram
class Profile {
    <<Aggregate Root>>
    -id: str
    -tenant_id: str
    -name: str
    -created_at: datetime
    -updated_at: datetime
    +new(tenant_id, name) Profile$
}
```

**Pattern List:**
- `domain-spec:aggregate-root`
- `domain-spec:guards-and-checks` + `domain-spec:constructor-guard-type-mapping`

**Reason:** Stereotype + factory method + timestamps. Guards are fundamental for all aggregates.

---

## Example 2: Aggregate with Value Object

```mermaid
classDiagram
class Order {
    <<Aggregate Root>>
    -id: str
    -details: OrderDetails
    +new(tenant_id, data) Order$
}

class OrderDetails {
    <<Value Object>>
    -customer_name: str
}

Order *-- OrderDetails
```

**Pattern List for Order:**
- `domain-spec:aggregate-root`
- `domain-spec:guards-and-checks` + `domain-spec:constructor-guard-type-mapping`
- `domain-spec:flat-constructor-arguments`

**Pattern List for OrderDetails:**
- `domain-spec:value-object`
- `domain-spec:guards-and-checks` + `domain-spec:constructor-guard-type-mapping`

**Note:**
- Order needs Flat Constructor if OrderDetails has multiple fields
- Order doesn't need Value Objects pattern -- OrderDetails does
- Both need Guards & Checks

---

## Example 3: Aggregate with Collection and Events

```mermaid
classDiagram
class Order {
    <<Aggregate Root>>
    -id: str
    -items: OrderItems
    +new(tenant_id) Order$
    +add_item(sku, qty) None
}

class OrderItems {
    <<Value Object>>
    +add_item(sku, qty, aggregate) None
}

class OrderCreated {
    <<Event>>
    +order_id: str
}

Order *-- OrderItems
Order --> OrderCreated : emits (new)
```

**Pattern List for Order:**
- `domain-spec:aggregate-root`
- `domain-spec:guards-and-checks` + `domain-spec:constructor-guard-type-mapping`

**Pattern List for OrderItems:**
- `domain-spec:value-object`
- `domain-spec:collection-value-objects`
- `domain-spec:delegation-and-event-propagation`
- `domain-spec:guards-and-checks` + `domain-spec:constructor-guard-type-mapping`

**Pattern List for OrderCreated:**
- `domain-spec:domain-events`

**Note:**
- Order emits events, but Aggregate Root pattern already covers event management
- OrderItems is a Value Object that also follows Collection Value Objects pattern
- OrderItems needs Delegation pattern because it delegates events to Order

---

## Example 4: Aggregate with Status

```mermaid
classDiagram
class Profile {
    <<Aggregate Root>>
    -id: str
    -status: ProfileStatus
    +update_status(new_status, error) None
}

class ProfileStatus {
    <<Value Object>>
    -status: Literal["new", "processing", "completed", "failed"]
    -error: str | None
}

Profile *-- ProfileStatus
```

**Pattern List for Profile:**
- `domain-spec:aggregate-root`
- `domain-spec:flat-constructor-arguments`
- `domain-spec:guards-and-checks` + `domain-spec:constructor-guard-type-mapping`

**Why Flat Constructor:** Profile's `__init__` will accept `status: str, error: str | None` (flat args) and internally construct `ProfileStatus(status, error)`.

**Pattern List for ProfileStatus:**
- `domain-spec:value-object`
- `domain-spec:statuses`
- `domain-spec:optional-values`
- `domain-spec:guards-and-checks` + `domain-spec:constructor-guard-type-mapping`

**Why Optional Values:** ProfileStatus has `error: str | None` -- needs guidance on conditional assignment.

**Note:**
- When a value object has multiple fields (status + error), the owning aggregate uses Flat Constructor pattern
- Class names ending in "Status" indicate the Statuses pattern (factory methods like `completed()`, `failed(error)` and boolean properties like `is_completed`, `is_failed`)

---

## Example 5: Complex Aggregate with Multiple Optional Attributes

```mermaid
classDiagram
class File {
    <<Aggregate Root>>
    -id: str
    -tenant_id: str
    -path: str
    -status: FileStatus
    -preparation_result: PreparationResult | None
    -text: Text | None
    -classification_result: ClassificationResult | None
    -created_at: datetime
    -updated_at: datetime
    +new(id, tenant_id, path) File$
    +add_preparation_result(result) None
    +add_retrieval_result(text) None
    +add_classification_result(result) None
    +add_error(error) None
    +retry() None
    +skip() None
}

class FileStatus {
    <<Value Object>>
    -status: Literal["new", "prepared", "retrieved", "classified", "failed", "skipped"]
    -error: ProcessingError | None
}

class FileCreated {
    <<Event>>
    +id: str
    +tenant_id: str
    +path: str
}

class FilePrepared {
    <<Event>>
    +id: str
    +preparation_result: PreparationResult
}

class TextRetrieved {
    <<Event>>
    +id: str
    +text: Text
}

class FileClassificationSucceeded {
    <<Event>>
    +id: str
    +document_types: list[DocumentType]
}

class FileProcessingFailed {
    <<Event>>
    +id: str
    +error: ProcessingError
}

File *-- FileStatus
File --() PreparationResult
File --() Text
File --() ClassificationResult
File --> FileCreated : emits (new)
File --> FilePrepared : emits (add_preparation_result)
File --> TextRetrieved : emits (add_retrieval_result)
File --> FileClassificationSucceeded : emits (add_classification_result)
File --> FileProcessingFailed : emits (add_error)
```

**Pattern List for File:**
- `domain-spec:aggregate-root`
- `domain-spec:flat-constructor-arguments`
- `domain-spec:optional-values`
- `domain-spec:guards-and-checks` + `domain-spec:constructor-guard-type-mapping`

**Why these patterns:**
- **Flat Constructor:** FileStatus has multiple fields (status + error)
- **Optional Values:** Has 3 optional complex attributes (preparation_result, text, classification_result)
- **Aggregate Root already covers:** Event emission pattern for all 5+ events

**Pattern List for FileStatus:**
- `domain-spec:value-object`
- `domain-spec:statuses`
- `domain-spec:optional-values`
- `domain-spec:guards-and-checks` + `domain-spec:constructor-guard-type-mapping`

**Pattern List for All Events:**
- `domain-spec:domain-events`

**Pattern List for PreparationResult, Text, ClassificationResult:**
- `domain-spec:domain-typed-dicts`

---

## Example 6: Repository

```mermaid
classDiagram
class CommandFileRepository {
    <<Repository>>
    -db_session: Session
    +file_of_id(id, tenant_id) File | None
    +save(file) None
    +delete(file) None
}

class QueryFileRepository {
    <<Repository>>
    -db_session: Session
    +find_one(id, tenant_id) FileDTO
    +find_many(filters) list[FileDTO]
}

CommandFileRepository --() File
```

**Pattern List for CommandFileRepository:**
- `domain-spec:repositories` -- Command variant

**Pattern List for QueryFileRepository:**
- `domain-spec:repositories` -- Query variant

**Note:**
- Command repositories work with domain aggregates (File)
- Query repositories return DTOs for read operations
- Naming convention: `Command{Aggregate}Repository` or `Query{Aggregate}Repository`

---

## Example 7: TypedDict for External Data

```mermaid
classDiagram
class ProcessingError {
    <<TypedDict>>
    +code: str
    +message: str
    +step: Literal["preparation", "retrieval", "classification"]
    +retryable: bool
}

class PreparationResult {
    <<TypedDict>>
    +file_type: Literal["PDF", "IMAGE"]
    +images: list[str]
}

class OCRPage {
    <<TypedDict>>
    +id: str
    +file_id: str
    +sequence: int
    +text: str
}

class Text {
    <<TypedDict>>
    +kind: Literal["OCR"]
    +result: list[OCRPage]
}

Text *-- OCRPage
```

**Pattern List for All TypedDict classes:**
- `domain-spec:domain-typed-dicts`

**When to use TypedDict:**
- External API responses or requests
- Data transfer objects within domain
- Structured data that domain references but doesn't own
- Nested data structures (Text contains list of OCRPage)

**Note:**
- TypedDicts are not domain objects -- they're structured data definitions
- No Guards & Checks needed (TypedDict provides type validation)
- Can be nested (Text contains OCRPage list)

---

## Example 8: Aggregate with Child Entities

```mermaid
classDiagram
class Profile {
    <<Aggregate Root>>
    -id: str
    -tenant_id: str
    -files: list[File]
    -status: ProfileStatus
    +new(id, tenant_id) Profile$
    +add(file_path) None
    +mark_file_as_classified(file_id, types) None
    +mark_file_as_failed(file_id, error) None
}

class File {
    <<Entity>>
    -id: str
    -path: str
    -status: FileStatus
    -document_types: list[str] | None
    +new(path, profile) File$
    +mark_as_classified(types) None
    +mark_as_failed(error) None
}

class ProfileStatus {
    <<Value Object>>
    -status: Literal["new", "in_progress", "classified", "failed"]
    +from_files(files) ProfileStatus$
    +update(profile) ProfileStatus
}

class FileStatus {
    <<Value Object>>
    -status: Literal["new", "in_progress", "classified", "failed"]
    -error: FileError | None
}

class FileError {
    <<TypedDict>>
    +code: str
    +message: str
}

class FileUploaded {
    <<Event>>
    +id: str
    +profile_id: str
    +path: str
}

class FilesStatusUpdated {
    <<Event>>
    +profile_id: str
    +status: str
}

Profile *-- File
Profile *-- ProfileStatus
File *-- FileStatus
FileStatus *-- FileError
File --> FileUploaded : emits (new)
ProfileStatus --> FilesStatusUpdated : emits (update)
```

**Pattern List for Profile:**
- `domain-spec:aggregate-root`
- `domain-spec:flat-constructor-arguments`
- `domain-spec:guards-and-checks` + `domain-spec:constructor-guard-type-mapping`

**Pattern List for File (Entity, not Aggregate Root):**
- `domain-spec:entity`
- `domain-spec:flat-constructor-arguments`
- `domain-spec:optional-values`
- `domain-spec:guards-and-checks` + `domain-spec:constructor-guard-type-mapping`

**Pattern List for ProfileStatus:**
- `domain-spec:value-object`
- `domain-spec:statuses`
- `domain-spec:delegation-and-event-propagation`
- `domain-spec:guards-and-checks` + `domain-spec:constructor-guard-type-mapping`

**Pattern List for FileStatus:**
- `domain-spec:value-object`
- `domain-spec:statuses`
- `domain-spec:optional-values`
- `domain-spec:guards-and-checks` + `domain-spec:constructor-guard-type-mapping`

**Pattern List for FileError:**
- `domain-spec:domain-typed-dicts`

**Pattern List for Events:**
- `domain-spec:domain-events`

**Key Insights:**
- **Entities vs Value Objects:** File is an Entity (has identity, owned by Profile), not a Value Object
- **Entity Pattern:** File needs Entity pattern -- it's a child entity within Profile aggregate boundary
- **Delegation Pattern:** ProfileStatus accepts `profile: Profile` parameter and emits events -- needs Delegation pattern
- **Factory with Aggregate:** ProfileStatus has `from_files()` factory and `update(profile)` method
- **Entity Constructor:** File's `new()` accepts `profile: Profile` parameter to establish relationship
- **list[Entity] is NOT Collection Value Object:** Profile has `list[File]` but File is Entity, not Value Object

---

## Example 9: Nested Value Objects with Union Types and Event Delegation

```mermaid
classDiagram
class Document {
    <<Aggregate Root>>
    -id: str
    -tenant_id: str
    -file_id: str
    -subject: Subject | None
    -status: DocumentStatus
    +new(id, tenant_id, file_id, document_type) Document$
    +add_extraction_result(result) None
    +add_corrections(corrections) None
}

class Subject {
    <<Value Object>>
    +kind: Literal["Individual", "LegalEntity"]
    +entity: Individual | LegalEntity
    +has_missing_values: bool
    +from_data(document_type, data) Subject$
    +add_corrections(corrections, document) Subject
}

class Individual {
    <<Value Object>>
    +document_type: str
    +full_name: Field | None
    +date_of_birth: Field | None
    +address: Field | None
    +has_missing_values: bool
    +from_data(document_type, data) Individual$
    +corrected(corrections) Individual
}

class LegalEntity {
    <<Value Object>>
    +document_type: str
    +name: Field | None
    +crn: Field | None
    +boi: list[BeneficialOwner]
    +has_missing_values: bool
    +from_data(document_type, data) LegalEntity$
    +corrected(corrections) LegalEntity
}

class BeneficialOwner {
    <<Value Object>>
    +full_name: Field | None
    +ownership_percentage: Field | None
    +from_data(data) BeneficialOwner$
    +corrected(corrections) BeneficialOwner
}

class Field {
    <<Value Object>>
    +value: str | datetime
    +source: Literal["AI", "user"]
    +confidence: float
    +from_data(data) Field$
    +corrected(corrections) Field
}

class CorrectionsAdded {
    <<Event>>
    +id: str
    +corrections: Corrections
}

class ExtractionResult {
    <<TypedDict>>
    +kind: Literal["Individual", "LegalEntity"]
    +entity: IndividualData | LegalEntityData
}

Document *-- Subject
Subject *-- Individual : XOR
Subject *-- LegalEntity : XOR
Individual *-- Field
LegalEntity *-- BeneficialOwner
BeneficialOwner *-- Field
Subject --> CorrectionsAdded : emits (add_corrections)
Subject --() ExtractionResult : from_data argument
```

**Pattern List for Document:**
- `domain-spec:aggregate-root`
- `domain-spec:flat-constructor-arguments`
- `domain-spec:optional-values`
- `domain-spec:guards-and-checks` + `domain-spec:constructor-guard-type-mapping`

**Why:** Flat Constructor for DocumentStatus, Optional Values for optional Subject attribute.

**Pattern List for Subject:**
- `domain-spec:value-object`
- `domain-spec:optional-values`
- `domain-spec:delegation-and-event-propagation`
- `domain-spec:guards-and-checks` + `domain-spec:constructor-guard-type-mapping`

**Pattern List for Individual & LegalEntity:**
- `domain-spec:value-object`
- `domain-spec:optional-values`
- `domain-spec:guards-and-checks` + `domain-spec:constructor-guard-type-mapping`

**Pattern List for BeneficialOwner:**
- `domain-spec:value-object`
- `domain-spec:optional-values`
- `domain-spec:guards-and-checks` + `domain-spec:constructor-guard-type-mapping`

**Pattern List for Field:**
- `domain-spec:value-object`
- `domain-spec:optional-values`
- `domain-spec:guards-and-checks` + `domain-spec:constructor-guard-type-mapping`

**Pattern List for ExtractionResult:**
- `domain-spec:domain-typed-dicts`

**Pattern List for CorrectionsAdded:**
- `domain-spec:domain-events`

**Key Insights:**
- **Deeply Nested Value Objects:** Field -> BeneficialOwner -> LegalEntity -> Subject -> Document (4-5 levels deep)
- **Union Type Handling:** Subject.entity is `Individual | LegalEntity` (XOR relationship) -- needs Optional Values for union type handling
- **Value Object Event Delegation:** Subject emits CorrectionsAdded event and accepts `document: Document` parameter -- needs Delegation pattern
- **Computed Properties:** `has_missing_values` is computed from nested Field values
- **Immutable Mutations:** `corrected()` methods return NEW instances (Value Object immutability)
- **Transformation Chains:** Factory methods chain data: TypedDict -> Field -> Individual/LegalEntity -> Subject
- **list[ValueObject] without Collection Pattern:** LegalEntity has `list[BeneficialOwner]` but doesn't need Collection Value Objects (no add/remove lifecycle methods)
- **Value Objects can delegate to Aggregates:** Subject's `add_corrections(corrections, document)` takes aggregate parameter for event delegation
- All value objects need Optional Values due to pervasive optional Field attributes
