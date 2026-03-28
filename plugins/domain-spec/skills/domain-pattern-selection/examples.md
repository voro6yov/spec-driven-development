# Pattern Selection Examples

## Example 1: Simple Aggregate

**`Profile`** `<<Aggregate Root>>`

- `id`: str
- `tenant_id`: str
- `name`: str
- `created_at`: datetime
- `updated_at`: datetime
- **Methods**:

    ◦ `new(tenant_id: str, name: str) -> Profile`

    ▪ Effect: creates a new Profile aggregate.

### Dependencies
1. *(none)*

**Pattern List:**
- `domain-spec:aggregate-root`
- `domain-spec:guards-and-checks` + `domain-spec:constructor-guard-type-mapping`

**Reason:** Stereotype + factory method + timestamps. Guards are fundamental for all aggregates.

---

## Example 2: Aggregate with Value Object

**`Order`** `<<Aggregate Root>>`

- `id`: str
- `details`: OrderDetails
- **Methods**:

    ◦ `new(tenant_id: str, data: OrderData) -> Order`

    ▪ Effect: creates a new Order aggregate.

**`OrderDetails`** `<<Value Object>>`

- `customer_name`: str

### Dependencies
1. **Order** composes **OrderDetails** (composition)

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

**`Order`** `<<Aggregate Root>>`

- `id`: str
- `items`: OrderItems
- **Methods**:

    ◦ `new(tenant_id: str) -> Order`

    ▪ Effect: creates a new Order aggregate.

    ◦ `add_item(sku: str, qty: int) -> None`

    ▪ Delegates: `self.items.add_item(sku, qty, self)`

**`OrderItems`** `<<Value Object>>`

- **Methods**:

    ◦ `add_item(sku: str, qty: int, aggregate: Order) -> None`

    ▪ Effect: adds an item to the collection.

    ▪ Emits: (events propagated through aggregate)

**`OrderCreated`** `<<Event>>`

- `order_id`: str

### Dependencies
1. **Order** composes **OrderItems** (composition)
2. **Order** emits **OrderCreated** (event emission)

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

**`Profile`** `<<Aggregate Root>>`

- `id`: str
- `status`: ProfileStatus
- **Methods**:

    ◦ `update_status(new_status: str, error: str | None) -> None`

    ▪ Effect: updates the profile status.

**`ProfileStatus`** `<<Value Object>>`

- `status`: Literal["new", "processing", "completed", "failed"]
- `error`: str | None

### Dependencies
1. **Profile** composes **ProfileStatus** (composition)

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

**`File`** `<<Aggregate Root>>`

- `id`: str
- `tenant_id`: str
- `path`: str
- `status`: FileStatus
- `preparation_result`: PreparationResult | None
- `text`: Text | None
- `classification_result`: ClassificationResult | None
- `created_at`: datetime
- `updated_at`: datetime
- **Methods**:

    ◦ `new(id: str, tenant_id: str, path: str) -> File`

    ▪ Effect: creates a new File aggregate.

    ◦ `add_preparation_result(result: PreparationResult) -> None`

    ▪ Effect: sets the preparation result.

    ▪ Emits: `FilePrepared`

    ◦ `add_retrieval_result(text: Text) -> None`

    ▪ Effect: sets the text.

    ▪ Emits: `TextRetrieved`

    ◦ `add_classification_result(result: ClassificationResult) -> None`

    ▪ Effect: sets the classification result.

    ▪ Emits: `FileClassificationSucceeded`

    ◦ `add_error(error: ProcessingError) -> None`

    ▪ Effect: records a processing error.

    ▪ Emits: `FileProcessingFailed`

    ◦ `retry() -> None`

    ▪ Effect: resets status for retry.

    ◦ `skip() -> None`

    ▪ Effect: marks file as skipped.

**`FileStatus`** `<<Value Object>>`

- `status`: Literal["new", "prepared", "retrieved", "classified", "failed", "skipped"]
- `error`: ProcessingError | None

**`FileCreated`** `<<Event>>`

- `id`: str
- `tenant_id`: str
- `path`: str

**`FilePrepared`** `<<Event>>`

- `id`: str
- `preparation_result`: PreparationResult

**`TextRetrieved`** `<<Event>>`

- `id`: str
- `text`: Text

**`FileClassificationSucceeded`** `<<Event>>`

- `id`: str
- `document_types`: list[DocumentType]

**`FileProcessingFailed`** `<<Event>>`

- `id`: str
- `error`: ProcessingError

### Dependencies
1. **File** composes **FileStatus** (composition)
2. **File** depends on **PreparationResult** (optional association)
3. **File** depends on **Text** (optional association)
4. **File** depends on **ClassificationResult** (optional association)
5. **File** emits **FileCreated** (event emission)
6. **File** emits **FilePrepared** (event emission)
7. **File** emits **TextRetrieved** (event emission)
8. **File** emits **FileClassificationSucceeded** (event emission)
9. **File** emits **FileProcessingFailed** (event emission)

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

**`CommandFileRepository`** `<<Repository>>`

- `db_session`: Session
- **Methods**:

    ◦ `file_of_id(id: str, tenant_id: str) -> File | None`

    ▪ Effect: loads and rehydrates a File aggregate, or returns None.

    ◦ `save(file: File) -> None`

    ▪ Effect: persists File state.

    ◦ `delete(file: File) -> None`

    ▪ Effect: deletes file record(s).

**`QueryFileRepository`** `<<Repository>>`

- `db_session`: Session
- **Methods**:

    ◦ `find_one(id: str, tenant_id: str) -> FileDTO`

    ▪ Effect: queries and returns a FileDTO.

    ◦ `find_many(filters: FileFilters) -> list[FileDTO]`

    ▪ Effect: queries and returns a list of FileDTOs.

### Dependencies
1. **CommandFileRepository** depends on **File** (retrieve/store)

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

**`ProcessingError`** `<<TypedDict>>`

- `code`: str
- `message`: str
- `step`: Literal["preparation", "retrieval", "classification"]
- `retryable`: bool

**`PreparationResult`** `<<TypedDict>>`

- `file_type`: Literal["PDF", "IMAGE"]
- `images`: list[str]

**`OCRPage`** `<<TypedDict>>`

- `id`: str
- `file_id`: str
- `sequence`: int
- `text`: str

**`Text`** `<<TypedDict>>`

- `kind`: Literal["OCR"]
- `result`: list[OCRPage]

### Dependencies
1. **Text** composes **OCRPage** (composition)

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

**`Profile`** `<<Aggregate Root>>`

- `id`: str
- `tenant_id`: str
- `files`: list[File]
- `status`: ProfileStatus
- **Methods**:

    ◦ `new(id: str, tenant_id: str) -> Profile`

    ▪ Effect: creates a new Profile aggregate.

    ◦ `add(file_path: str) -> None`

    ▪ Effect: creates a new File entity and adds it to files.

    ▪ Emits: `FileUploaded`

    ◦ `mark_file_as_classified(file_id: str, types: list[str]) -> None`

    ▪ Delegates: `file.mark_as_classified(types)`

    ◦ `mark_file_as_failed(file_id: str, error: FileError) -> None`

    ▪ Delegates: `file.mark_as_failed(error)`

**`File`** `<<Entity>>`

- `id`: str
- `path`: str
- `status`: FileStatus
- `document_types`: list[str] | None
- **Methods**:

    ◦ `new(path: str, profile: Profile) -> File`

    ▪ Effect: creates a new File entity within the Profile aggregate.

    ◦ `mark_as_classified(types: list[str]) -> None`

    ▪ Effect: updates status and sets document_types.

    ◦ `mark_as_failed(error: FileError) -> None`

    ▪ Effect: updates status with error.

**`ProfileStatus`** `<<Value Object>>`

- `status`: Literal["new", "in_progress", "classified", "failed"]
- **Methods**:

    ◦ `from_files(files: list[File]) -> ProfileStatus`

    ▪ Effect: derives aggregate status from file statuses.

    ◦ `update(profile: Profile) -> ProfileStatus`

    ▪ Effect: recalculates status and emits event.

    ▪ Emits: `FilesStatusUpdated`

**`FileStatus`** `<<Value Object>>`

- `status`: Literal["new", "in_progress", "classified", "failed"]
- `error`: FileError | None

**`FileError`** `<<TypedDict>>`

- `code`: str
- `message`: str

**`FileUploaded`** `<<Event>>`

- `id`: str
- `profile_id`: str
- `path`: str

**`FilesStatusUpdated`** `<<Event>>`

- `profile_id`: str
- `status`: str

### Dependencies
1. **Profile** composes **File** (composition)
2. **Profile** composes **ProfileStatus** (composition)
3. **File** composes **FileStatus** (composition)
4. **FileStatus** composes **FileError** (composition)
5. **File** emits **FileUploaded** (event emission)
6. **ProfileStatus** emits **FilesStatusUpdated** (event emission)

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

**`Document`** `<<Aggregate Root>>`

- `id`: str
- `tenant_id`: str
- `file_id`: str
- `subject`: Subject | None
- `status`: DocumentStatus
- **Methods**:

    ◦ `new(id: str, tenant_id: str, file_id: str, document_type: str) -> Document`

    ▪ Effect: creates a new Document aggregate.

    ◦ `add_extraction_result(result: ExtractionResult) -> None`

    ▪ Effect: sets the subject from extraction result.

    ◦ `add_corrections(corrections: Corrections) -> None`

    ▪ Delegates: `self.subject.add_corrections(corrections, self)`

    ▪ Emits: `CorrectionsAdded` (via delegation)

**`Subject`** `<<Value Object>>`

- `kind`: Literal["Individual", "LegalEntity"]
- `entity`: Individual | LegalEntity
- `has_missing_values`: bool
- **Methods**:

    ◦ `from_data(document_type: str, data: ExtractionResult) -> Subject`

    ▪ Effect: creates a Subject from extraction data.

    ◦ `add_corrections(corrections: Corrections, document: Document) -> Subject`

    ▪ Effect: applies corrections and returns a new Subject.

    ▪ Emits: `CorrectionsAdded` (delegated through document)

**`Individual`** `<<Value Object>>`

- `document_type`: str
- `full_name`: Field | None
- `date_of_birth`: Field | None
- `address`: Field | None
- `has_missing_values`: bool
- **Methods**:

    ◦ `from_data(document_type: str, data: IndividualData) -> Individual`

    ▪ Effect: creates an Individual from extracted data.

    ◦ `corrected(corrections: Corrections) -> Individual`

    ▪ Effect: returns a new Individual with corrections applied.

**`LegalEntity`** `<<Value Object>>`

- `document_type`: str
- `name`: Field | None
- `crn`: Field | None
- `boi`: list[BeneficialOwner]
- `has_missing_values`: bool
- **Methods**:

    ◦ `from_data(document_type: str, data: LegalEntityData) -> LegalEntity`

    ▪ Effect: creates a LegalEntity from extracted data.

    ◦ `corrected(corrections: Corrections) -> LegalEntity`

    ▪ Effect: returns a new LegalEntity with corrections applied.

**`BeneficialOwner`** `<<Value Object>>`

- `full_name`: Field | None
- `ownership_percentage`: Field | None
- **Methods**:

    ◦ `from_data(data: BeneficialOwnerData) -> BeneficialOwner`

    ▪ Effect: creates a BeneficialOwner from data.

    ◦ `corrected(corrections: Corrections) -> BeneficialOwner`

    ▪ Effect: returns a new BeneficialOwner with corrections applied.

**`Field`** `<<Value Object>>`

- `value`: str | datetime
- `source`: Literal["AI", "user"]
- `confidence`: float
- **Methods**:

    ◦ `from_data(data: FieldData) -> Field`

    ▪ Effect: creates a Field from data.

    ◦ `corrected(corrections: Corrections) -> Field`

    ▪ Effect: returns a new Field with corrections applied.

**`CorrectionsAdded`** `<<Event>>`

- `id`: str
- `corrections`: Corrections

**`ExtractionResult`** `<<TypedDict>>`

- `kind`: Literal["Individual", "LegalEntity"]
- `entity`: IndividualData | LegalEntityData

### Dependencies
1. **Document** composes **Subject** (composition)
2. **Subject** composes **Individual** (composition, XOR with LegalEntity)
3. **Subject** composes **LegalEntity** (composition, XOR with Individual)
4. **Individual** composes **Field** (composition)
5. **LegalEntity** composes **BeneficialOwner** (composition)
6. **BeneficialOwner** composes **Field** (composition)
7. **Subject** emits **CorrectionsAdded** (event emission)
8. **Subject** depends on **ExtractionResult** (optional association)

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
