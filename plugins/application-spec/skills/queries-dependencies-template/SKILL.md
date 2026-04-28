---
name: queries-dependencies-template
description: Queries Dependencies Template for the Dependencies section of a query application service spec. Auto-invoke after the class diagram exists, when authoring the Dependencies section of a `<AggregateRoot>Queries` spec.
user-invocable: false
disable-model-invocation: false
---

# Queries Dependencies Template

A query application service is named `<AggregateRoot>Queries`. It declares its
collaborators in two sections, **rendered in this order**:

1. **Query Repositories**
2. **External Interfaces**

Always render both sections — if a category has no entries, write `_None_`
under the heading.

The two categories differ in how they appear in the class diagram:

| Category | Diagram link from `<AggregateRoot>Queries` |
| --- | --- |
| Query Repository | `--() Query<AggregateRoot>Repository : uses` (lollipop) |
| External Interface | `--> <IInterfaceClass> : uses` (plain arrow, separate class node) |

---

## Query Repositories

List one row per query repository the query service depends on; a service may
declare more than one. Query repositories are declared on the application
service as private attributes
(`-query_<aggregate_root>_repository: Query<AggregateRoot>Repository`,
where `<aggregate_root>` is the aggregate root name in `snake_case` singular
and `<AggregateRoot>` is the same name in `PascalCase`). Use the class name
as it appears in the diagram (with the `Query` prefix) and the matching
query-context attribute the query body will read it from.

## External Interfaces

List one bullet per external interface the query service depends on; a
service may declare more than one. External interfaces are declared on the
application service as private attributes
(`-<interface_name>: <IInterfaceClass>`). Unlike query repositories, they
appear in the diagram as separate class nodes linked with a plain `-->`
arrow. Use the plain class name as it appears in the diagram.

---

## Skeleton

```markdown
## Query Repositories

| Repository | Query context attribute |
| --- | --- |
| Query{AggregateRoot}Repository | `query_context.{attr}` |

## External Interfaces

_None_
```
