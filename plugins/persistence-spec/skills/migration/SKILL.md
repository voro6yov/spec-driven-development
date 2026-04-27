---
name: migration
description: Migration pattern for persistence. Use when defining Liquibase YAML changeSets for database schema creation, column changes, indexes, and foreign keys with rollback.
user-invocable: false
disable-model-invocation: false
---

# Migration

**Type:** Primary

## Purpose

- Define database schema changes using Liquibase YAML format.
- Provide rollback capabilities for safe schema evolution.
- Version database schema changes alongside code changes.

## Structure

- Each migration is a YAML file with `databaseChangeLog` root element.
- Each changeSet has an `id`, `author`, `changes`, and `rollback` section.
- Changes are applied sequentially based on changeSet ID.
- Rollback section defines how to reverse the migration.

## Usage patterns

- **Create Table**: Use `createTable` with columns, constraints, and primary keys. Rollback uses `dropTable`.
- **Add Column**: Use `addColumn` to extend existing tables. Rollback uses `dropColumn`.
- **Rename Column**: Use `renameColumn` with old and new names. Rollback reverses the rename.
- **Add Index**: Use `createIndex` for standard indexes. Rollback uses `dropIndex`.
- **Add Foreign Key**: Use `addForeignKeyConstraint` with `onDelete` cascade option. Rollback uses `dropForeignKeyConstraint`.
- **Add Not Null**: Use `addNotNullConstraint` to enforce non-null values. Rollback uses `dropNotNullConstraint`.
- **Add JSONB Index**: Use raw SQL with `CREATE INDEX ... USING GIN` for JSONB column search optimization. Rollback uses `dropIndex`.

## Testing guidance

- Migrations are tested through integration tests that verify schema changes.
- Test both forward migration and rollback operations.
- Verify that migrations can be applied to existing databases without data loss.

---

## Template

### Create Table

```yaml
databaseChangeLog:
- changeSet:
    id: {{ change_set_id }}
    author: {{ author_name }}
    changes:
    - createTable:
        tableName: {{ table_name }}
        columns:
        - column:
            constraints:
              primaryKey: true
              primaryKeyName: {{ id_column }}
            name: {{ id_column }}
            type: VARCHAR
        - column:
            constraints:
              nullable: false
            name: {{ tenant_id_column }}
            type: VARCHAR
        - column:
            name: {{ jsonb_column }}
            type: JSONB
        - column:
            constraints:
              nullable: false
            name: {{ status_column }}
            type: VARCHAR
        - column:
            constraints:
              nullable: false
            name: created_at
            type: TIMESTAMP WITH TIME ZONE
        - column:
            constraints:
              nullable: false
            name: updated_at
            type: TIMESTAMP WITH TIME ZONE

    rollback:
    - dropTable:
        tableName: {{ table_name }}
```

### Create Table (Composite PK)

```yaml
databaseChangeLog:
- changeSet:
    id: {{ change_set_id }}
    author: {{ author_name }}
    changes:
    - createTable:
        tableName: {{ table_name }}
        columns:
        - column:
            constraints:
              primaryKey: true
            name: {{ id_column }}
            type: VARCHAR
        - column:
            constraints:
              primaryKey: true
            name: {{ tenant_id_column }}
            type: VARCHAR
        - column:
            constraints:
              nullable: false
            name: {{ additional_column }}
            type: {{ additional_column_type }}
        - column:
            constraints:
              nullable: false
            name: {{ status_column }}
            type: VARCHAR
        - column:
            constraints:
              nullable: false
            name: created_at
            type: TIMESTAMP WITH TIME ZONE
        - column:
            constraints:
              nullable: false
            name: updated_at
            type: TIMESTAMP WITH TIME ZONE

    rollback:
    - dropTable:
        tableName: {{ table_name }}
```

### Add Column

```yaml
databaseChangeLog:
- changeSet:
    id: {{ change_set_id }}
    author: {{ author_name }}
    changes:
    - addColumn:
        tableName: {{ table_name }}
        columns:
        - column:
            name: {{ column_name }}
            type: {{ column_type }}

    rollback:
    - dropColumn:
        tableName: {{ table_name }}
        columnName: {{ column_name }}
```

### Add Column with Default

```yaml
databaseChangeLog:
- changeSet:
    id: {{ change_set_id }}
    author: {{ author_name }}
    changes:
    - addColumn:
        tableName: {{ table_name }}
        columns:
        - column:
            name: {{ column_name }}
            type: {{ column_type }}
            defaultValueComputed: "{{ default_value }}"

    rollback:
    - dropColumn:
        tableName: {{ table_name }}
        columnName: {{ column_name }}
```

### Rename Column

```yaml
databaseChangeLog:
- changeSet:
    id: {{ change_set_id }}
    author: {{ author_name }}
    changes:
    - renameColumn:
        tableName: {{ table_name }}
        oldColumnName: {{ old_column_name }}
        newColumnName: {{ new_column_name }}
        columnDataType: {{ column_type }}

    rollback:
    - renameColumn:
        tableName: {{ table_name }}
        oldColumnName: {{ new_column_name }}
        newColumnName: {{ old_column_name }}
        columnDataType: {{ column_type }}
```

### Add Index

```yaml
databaseChangeLog:
- changeSet:
    id: {{ change_set_id }}
    author: {{ author_name }}
    changes:
    - createIndex:
        indexName: {{ index_name }}
        tableName: {{ table_name }}
        columns:
        - column:
            name: {{ column_name }}

    rollback:
    - dropIndex:
        indexName: {{ index_name }}
        tableName: {{ table_name }}
```

### Add Foreign Key

```yaml
databaseChangeLog:
- changeSet:
    id: {{ change_set_id }}
    author: {{ author_name }}
    changes:
    - addForeignKeyConstraint:
        baseTableName: {{ base_table_name }}
        baseColumnNames: {{ base_column_name }}
        referencedTableName: {{ referenced_table_name }}
        referencedColumnNames: {{ referenced_column_name }}
        constraintName: {{ constraint_name }}
        onDelete: {{ on_delete }}

    rollback:
    - dropForeignKeyConstraint:
        baseTableName: {{ base_table_name }}
        constraintName: {{ constraint_name }}
```

### Add Not Null Constraint

```yaml
databaseChangeLog:
- changeSet:
    id: {{ change_set_id }}
    author: {{ author_name }}
    changes:
    - addNotNullConstraint:
        tableName: {{ table_name }}
        columnName: {{ column_name }}
        columnDataType: {{ column_type }}

    rollback:
    - dropNotNullConstraint:
        tableName: {{ table_name }}
        columnName: {{ column_name }}
        columnDataType: {{ column_type }}
```

### Add JSONB Index

```yaml
databaseChangeLog:
- changeSet:
    id: {{ change_set_id }}
    author: {{ author_name }}
    changes:
    - sql:
        sql: CREATE INDEX {{ index_name }} ON {{ table_name }} USING GIN ({{ jsonb_column }})

    rollback:
    - dropIndex:
        indexName: {{ index_name }}
        tableName: {{ table_name }}
```

## Placeholders

| Placeholder | Description | Example |
| --- | --- | --- |
| `{{ change_set_id }}` | Unique changeSet identifier | `001-create-order-table`, `002-add-status-column` |
| `{{ author_name }}` | Migration author name | `system`, `developer-name` |
| `{{ table_name }}` | Database table name | `order`, `profile` |
| `{{ id_column }}` | Primary key column name | `id`, `order_id` |
| `{{ tenant_id_column }}` | Tenant ID column name | `tenant_id` |
| `{{ jsonb_column }}` | JSONB column name | `info`, `metadata` |
| `{{ status_column }}` | Status column name | `status` |
| `{{ additional_column }}` | Additional column name | `name`, `description` |
| `{{ additional_column_type }}` | Additional column SQL type | `VARCHAR`, `INTEGER`, `JSONB` |
| `{{ column_name }}` | Column name to add/rename | `status`, `created_at` |
| `{{ column_type }}` | Column SQL type | `VARCHAR`, `TIMESTAMP`, `JSONB` |
| `{{ default_value }}` | Default value expression | `'{}'::jsonb`, `NOW()` |
| `{{ old_column_name }}` | Old column name (for rename) | `old_name` |
| `{{ new_column_name }}` | New column name (for rename) | `new_name` |
| `{{ index_name }}` | Index name | `idx_order_status`, `idx_profile_tenant` |
| `{{ base_table_name }}` | Child table name | `order_item` |
| `{{ base_column_name }}` | Foreign key column(s) | `order_id` or `order_id, tenant_id` |
| `{{ referenced_table_name }}` | Parent table name | `order` |
| `{{ referenced_column_name }}` | Referenced column(s) | `id` or `id, tenant_id` |
| `{{ constraint_name }}` | Foreign key constraint name | `fk_order_item_order` |
| `{{ on_delete }}` | On delete action | `CASCADE`, `RESTRICT`, `SET NULL` |
