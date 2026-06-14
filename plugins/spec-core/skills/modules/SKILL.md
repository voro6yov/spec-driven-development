---
name: modules
description: "Umbrella catalog of the reference Python modules the spec pipeline copies verbatim into a target repo during init/scaffold (shared domain primitives, persistence context packages, REST serializers). Each group is a sibling folder of this file. Load to resolve the modules directory and copy a group by path."
user-invocable: false
---

# Reference modules (spec-core)

The spec pipeline ships a set of **runtime contract modules** — real Python source the *generated* code imports (Entity, ValueObject, guards, UnitOfWork, QueryContext, DatabaseSession, the serializer base). They are not generated per-aggregate; they are copied **verbatim** into the target repo once, by each layer's init/scaffold flow.

They are homed here in spec-core — the shared foundation every spec plugin already depends on — so there is **one** canonical source with **one** resolvable path, instead of each plugin resolving its own bundle via brittle `find ~/.claude/plugins` globs or impossible "walk up to a `plugins/` ancestor" heuristics. Those heuristics do not work from an agent's or skill's runtime Bash (the `${CLAUDE_PLUGIN_ROOT}` variable is not exposed there); the umbrella mechanism does, because loading this skill reveals its own directory.

Each group is a **supporting folder** of real `.py` files (not an `index.md` doc) sibling to this `SKILL.md`. The files are never auto-loaded into context — consumers copy them to disk on demand.

## Resolution rule

A consumer resolves `<modules_dir>` as the directory containing this `SKILL.md` — its loaded context (frontmatter auto-load for agents, or the `Skill` tool for skills) reveals its location. A group named `<group>` is then the folder `<modules_dir>/<group>/`.

Copy a group with a directory-tree copy from the resolved absolute path:

```bash
cp -r <modules_dir>/<group> <destination>
```

Be **idempotent**: never overwrite a file that already exists at the destination; copy only what is missing. Preserve contents byte-for-byte. A group name with no matching folder is an **error** — report it loudly; never skip it silently.

## Catalog

| Group | Folder | Copied by | Contents |
|---|---|---|---|
| shared | [shared/](shared/) | `domain-spec:init-domain` | domain primitives — `entity.py`, `value_object.py`, `entity_id.py`, `event.py`, `command.py`, `clock.py`, `extended_enum.py`, `exceptions.py`, pagination/result-set DTOs, and the nested `guards/` package |
| database_session | [database_session/](database_session/) | `persistence-spec:database-session-scaffolder` | `__init__.py`, `constants.py`, `database_session.py` |
| unit_of_work | [unit_of_work/](unit_of_work/) | `persistence-spec:context-package-scaffolder` (`unit_of_work` axis) | `__init__.py`, `abstract_unit_of_work.py`, `sql_alchemy_unit_of_work.py` |
| query_context | [query_context/](query_context/) | `persistence-spec:context-package-scaffolder` (`query_context` axis) | `__init__.py`, `abstract_query_context.py`, `sql_alchemy_query_context.py` |
| serializers | [serializers/](serializers/) | `rest-api-spec:serializers-copier` | `error.py`, `configured_base_serializer.py`, `json_utils.py` |

Some consumers patch a freshly-copied file after the copy (e.g. `context-package-scaffolder` rewrites the `DatabaseSession` import placeholder; `serializers-copier` regenerates the aggregator `__init__.py`). That post-copy work is owned by the consumer, not this catalog. The `sql_alchemy_*` files under `unit_of_work`/`query_context` intentionally ship with a `# Add DatabaseSession import there` placeholder line for that reason.
