---
name: package-layout
description: Package layout and import conventions for DDD Python domain packages. Use when scaffolding a new domain package, organizing modules, setting up __init__.py exports, or deciding how to structure subpackages vs flat modules.
user-invocable: false
disable-model-invocation: false
---

# Package Layout Pattern

**Type:** Reference

## Purpose

- Define a consistent module structure for domain packages so that consumers import from one surface (`from my_domain import Foo`) regardless of where `Foo` lives internally.
- Keep internal cross-module imports explicit and relative so the package can be relocated without breaking paths.

## Package structure

A domain package follows this layout:

```
<domain>/
├── __init__.py                  # re-exports everything; builds __all__
├── <module_a>.py                # flat module — one cohesive concept per file
├── <module_b>.py
└── <subpackage>/                # subpackage — use when a concept owns multiple files
    ├── __init__.py              # re-exports from submodules; builds __all__
    ├── <submodule_x>.py
    └── <submodule_y>.py
```

**Use a flat module** (`<module>.py`) when the concept fits in one file.
**Use a subpackage** (`<name>/`) when the concept has helper types, internal utilities, or enough surface area to justify splitting (e.g., `guards/` with `guard.py`, `checks.py`, `attribute_name.py`).

## `__all__` conventions

### Every module declares its own `__all__`

Each `.py` file lists exactly the public names it owns:

```python
__all__ = ["Guard"]
```

`__all__` must be declared **before** the class/function definitions so it is easy to audit at a glance.

### Subpackage `__init__.py` aggregates submodule `__all__`s

```python
# guards/__init__.py
from .attribute_name import *
from .checks import *
from .guard import *

__all__ = attribute_name.__all__ + checks.__all__ + guard.__all__  # type: ignore
```

The `# type: ignore` suppresses the "module not defined" false positive from static analysers — the names are in scope after the star-imports.

### Top-level `__init__.py` aggregates all module/subpackage `__all__`s

```python
# shared/__init__.py
from .command import *
from .entity import *
from .guards import *          # subpackage — one import line covers all of guards/
...

__all__ = (
    command.__all__
    + entity.__all__
    + guards.__all__
    ...
)
```

The result: `from shared import Guard`, `from shared import Entity`, etc., all work via the single top-level surface.

## Import rules

| Situation | Rule |
|-----------|------|
| Within the same package (sibling modules) | Use relative imports: `from .guards import Guard` |
| From a subpackage to its parent package | Use relative parent imports: `from ..exceptions import IllegalArgument` |
| From outside the package | Import from the top-level `__init__` only; never reach into internal modules |

### Examples from the `shared` package

```python
# entity.py (sibling) imports from sibling subpackage
from .guards import Guard

# guards/checks.py (subpackage) imports from parent package
from ..exceptions import IllegalArgument

# guards/guard.py (within subpackage) imports from sibling submodule
from .attribute_name import AttributeName
from .checks import Check, NoneCheck, TypeCheck
```

## Naming conventions

- Module files are **snake_case**, matching the primary class they contain (`entity_id.py` → `EntityId`).
- Subpackage directories are also **snake_case** (`guards/`).
- `__all__` entries are the exported class or function names (PascalCase for classes).

## What NOT to do

- Do **not** import from internal submodules outside the package (e.g., `from shared.guards.checks import ImmutableCheck`). Always import from the package surface.
- Do **not** omit `__all__` from any module — wildcard imports without `__all__` leak everything, including private helpers.
- Do **not** put multiple unrelated concepts in one module to avoid creating a subpackage. One cohesive concept per file is the rule.
- Do **not** use absolute imports inside the package. Relative imports make the package portable.
