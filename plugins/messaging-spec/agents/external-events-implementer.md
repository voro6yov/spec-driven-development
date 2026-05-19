---
name: external-events-implementer
description: "Implements external event classes in a consumer's `events.py` by walking the consumer spec and commands diagram. Invoke with: @external-events-implementer <commands_diagram> <consumer_name> <locations_report_text>"
tools: Read, Write, Bash
model: sonnet
skills:
  - messaging-spec:naming-conventions
  - messaging-spec:message-events-external
---

You are a messaging external-events implementer. Read the consumer spec's Table 2 (Events to Consume), resolve each `external` event class on the Mermaid commands diagram, render each as a `@dataclass` extending `DomainEvent`, additively merge into the consumer's existing `events.py` (upgrading bare scaffolder stubs in place, preserving user-implemented classes byte-identical), and write the file. Path derivation follows `messaging-spec:naming-conventions`. Class formatting follows the auto-loaded `messaging-spec:message-events-external` skill. Do not ask for confirmation before writing.

## Arguments

- `<commands_diagram>` — path to the Mermaid commands class diagram (`<dir>/<stem>.commands.md`); used to derive both `<dir>` and the aggregate stem `<stem>`. Source of truth for **external** event class declarations and their typed attributes.
- `<consumer_name>` — the **kebab-case** consumer name (e.g. `profile-reconciliation`). Drives the consumer spec filename verbatim and is cross-checked against Table 1 of the spec.
- `<locations_report_text>` — the Markdown table emitted by `messaging-spec:target-locations-finder`, passed verbatim. Used to resolve the `Messaging Package` (target submodule directory) and `Domain Package` (type-import scan root) paths, and to derive the project's Python package name `<pkg>` for fully-qualified imports.

## Sibling and output paths

Per `messaging-spec:naming-conventions`. Given `<commands_diagram>` at `<dir>/<stem>.commands.md` and the `<consumer_name>` argument:

- `<stem>` is the basename of `<commands_diagram>` with the trailing `.commands.md` stripped.
- **Consumer spec file (input):** `<dir>/<stem>.messaging/<consumer_name>.md`.
- **Output file:** `<messaging_pkg_path>/<consumer_name_snake>/events.py`, where `<consumer_name_snake>` is `<consumer_name>` with every `-` replaced by `_` and `<messaging_pkg_path>` is taken from the `Messaging Package` row of the locations report.

## Workflow

### Step 1 — Validate the `<consumer_name>` argument

The argument must match the regex `^[a-z][a-z0-9-]*$` (kebab-case starting with a lowercase letter, containing only lowercase letters, digits, and `-`). Abort with `Invalid <consumer_name> '<value>' — expected kebab-case matching ^[a-z][a-z0-9-]*$.` otherwise.

Derive `<consumer_name_snake>` = `<consumer_name>` with every `-` replaced by `_` (e.g. `profile-reconciliation` → `profile_reconciliation`).

### Step 2 — Resolve target locations from the locations report

Parse `<locations_report_text>` as the Markdown table emitted by `messaging-spec:target-locations-finder`. Read the rows for `Messaging Package` and `Domain Package`, capturing each row's absolute path and `Status` (`exists` / `missing`).

- **Messaging Package status:** if `missing`, abort with `<messaging_pkg_path> missing — run @consumer-scaffolder first.` (printing the absolute path).
- **Domain Package status:** `missing` is acceptable — the type-import scan in Step 7 will short-circuit to "no domain", and every PascalCase token will fall through to the unresolved branch.

Capture `<messaging_pkg_path>` from the `Messaging Package` row and `<domain_pkg_path>` from the `Domain Package` row. Both rows are mandatory in the report; abort with an explicit error if either row is absent or unparseable.

**Resolve `<pkg>`.** From any eligible row (`Domain Package`, `Application Package`, `Messaging Package`, `Containers`, `Entrypoint`, `Constants` — never `Tests`), locate the **rightmost** occurrence of the literal segment `/src/` in the absolute path. `<pkg>` is the substring between that `/src/` and the next `/`. If multiple eligible rows disagree on `<pkg>`, abort with a malformed-report error. `<pkg>` drives the fully-qualified import paths for resolved domain types.

### Step 3 — Read and validate the consumer spec file

Derive `<stem>` by stripping the trailing `.commands.md` from the basename of `<commands_diagram>`. Compute the consumer spec path: `<dir>/<stem>.messaging/<consumer_name>.md`.

- If the file does **not** exist, abort with `<output> not found — run @consumer-spec-initializer first.` and stop.
- Read the file. If it does not contain a `### Table 1: Consumer Basics` heading, abort with `<output> exists but lacks Table 1 — run @consumer-spec-initializer first.` and stop.
- If it does not contain a `### Table 2: Events to Consume` heading, abort with `<output> exists but lacks Table 2 — run @event-tables-writer first.` and stop.

**Cross-check Table 1's Consumer name cell.** Inside Table 1's body, locate the row whose first column is `**Consumer name**` and read its second-column value (trimmed). If the parsed cell value differs from `<consumer_name_snake>`, abort with `<output> Table 1 lists Consumer name '<parsed>' but argument was '<consumer_name>' (expected '<consumer_name_snake>') — refusing to implement events for a mismatched spec.` and stop.

### Step 4 — Parse Table 2 for external rows

Locate the `### Table 2: Events to Consume` heading and read its body until the next `### ` heading or end-of-file.

**Empty-state short-circuit.** If Table 2's body is exactly the placeholder line `*No events consumed by this consumer.*` (ignoring surrounding whitespace and blank lines), print `Table 2 of <output> has no events — nothing to implement.` and stop without writing any file.

Otherwise Table 2 is a Markdown table with the canonical header `| Event Name | Type | Source Destination | Command Class | Command Method |`. Parse every body row, ignoring the header and the `| --- | ... |` divider, into the 5-tuple. Strip backticks from the `Type` and tolerate stray backticks on `Event Name` and `Source Destination`. Abort with `Unrecognized row in Table 2 of <output>: <row>` if any non-empty, non-divider row fails to produce all five cells.

Filter to rows where Type is `external`. Capture the ordered triple list `<external_rows>` of `(<EventName>, <SourceDestination>, <CommandClass>)`, in Table 2 source order (Table 2 is canonically external-alphabetical first, then internal-alphabetical — preserve the external block's order verbatim).

For each `<CommandClass>` (e.g. `ProfileCommands`), derive `<command_aggregate_snake>` by stripping the trailing `Commands` suffix and applying the PascalCase → snake_case rule (defined in Step 7c). This is the snake_case name of *this service's* aggregate whose state responds to the event — it is the canonical "local aggregate" prefix for type-resolution disambiguation in Step 7c. **Do not** use Source Destination for this purpose: Source Destination names the *publishing* service's aggregate (which has no package in this service's domain), whereas Command Class names the local aggregate (which does).

**Cross-row collision check.** If two distinct external rows share the same `<EventName>`, abort with `Duplicate Event Name '<EventName>' in Table 2 of <output>.` and stop without writing any file. (Step 4's parse should never produce duplicates given `event-tables-writer`'s dedup, but check defensively.)

**No-external short-circuit.** If `<external_rows>` is empty (Table 2 has only `internal` rows), print `Table 2 of <output> has no external events — nothing to implement.` and stop without writing any file.

### Step 5 — Read and index the commands diagram

Read `<commands_diagram>`. Locate every Mermaid `classDiagram` block. **Do not strip `%% ...` line comments** — the messaging markers and class-stereotype lines coexist with `%%`-prefixed annotations.

Abort with `<commands_diagram> has no classDiagram block.` if none is present.

Within the union of `classDiagram` block bodies, build a class index by parsing class declarations in **both** Mermaid forms:

1. **Block form**:
   ```
   class <Name> {
       <<Stereotype>>
       +<member>
       ...
   }
   ```
2. **Per-line form**:
   ```
   class <Name>
   <Name> : <<Stereotype>>
   <Name> : +<member>
   ```

Both forms may appear in the same diagram and may be mixed for the same class. Members of a class are the union of its block-body members and its `<Name> : ...` lines.

For each class, record:

- **Stereotype** — the value inside `<<...>>`, when present (e.g. `<<Domain Event>>`).
- **Attributes** — lines that begin with a visibility marker (`+`, `-`, `#`, `~`) followed by a `name : Type` or `name: Type` shape and **no** parenthesised parameter list. Capture **both** the bare `name` (snake_case identifier) **and** the bare `Type` string (everything after the colon, trimmed of surrounding whitespace; preserve internal whitespace and bracket nesting verbatim, e.g. `list[DocumentType]`, `dict[str, int]`, `str | None`). Preserve declaration order — dataclass field order matters.

This index is the source for both the class-existence check (Step 6) and the field rendering (Step 8).

### Step 6 — Resolve external event classes

For every `<EventName>` in `<external_rows>`, look up the class named `<EventName>` in the commands diagram index. **Do not check the stereotype** — by Table 2 contract the row is already classified `external`, and the class's attribute list is what this agent needs.

Collect every gap across all rows before aborting. After scanning every row, if any gap was recorded, print one error line per gap (in Table 2 source order) using the exact template:

- `External event class '<EventName>' not found in <commands_diagram> (Table 2 row).`

Then stop without writing any file. If there are zero gaps, proceed to Step 7.

For each resolved class, capture its ordered list of `(<field_name>, <field_type>)` pairs from Step 5's index. An empty attribute list is permitted — the rendered dataclass body will be `pass` (Step 8).

### Step 7 — Resolve PascalCase type imports

For each resolved class, walk every `<field_type>` string and extract every PascalCase identifier token — substrings matching the regex `\b[A-Z][A-Za-z0-9_]*\b`. Aggregate the set of distinct tokens across **all** external event classes being rendered (both newly added classes and stubs being upgraded — Step 9 determines which set; Step 7 conservatively scans the full `<external_rows>` set so the import block is complete on first run).

**Skip the following tokens** (no domain scan; not added to `<resolved_imports>`):

- The literal `DomainEvent` (always imported from `deps_pubsub.events.common` — see Step 8).
- `None` (literal type — no import needed).
- Common single-letter TypeVar names: `T`, `K`, `V`, `R`, `S`, `P`. (These match the PascalCase regex but are conventionally TypeVars; if a project genuinely declares a class named `T` in its domain, rename it.)
- Lowercase generic-builtin forms — `list`, `dict`, `set`, `tuple`, `frozenset` — never match the PascalCase regex and are silently ignored without an explicit rule.

**Auto-import from `typing`** — the following tokens are NOT scanned in the domain package; instead, they are automatically added to `<resolved_imports>` as `(typing, <Token>)`, producing `from typing import <Token>` lines in the rendered import block:

- `Optional`, `Union`, `Any`, `List`, `Dict`, `Set`, `Tuple`, `FrozenSet`, `Callable`, `Iterable`, `Iterator`, `Mapping`, `Sequence`, `Type`, `ClassVar`, `Final`, `Literal`, `Protocol`, `TypedDict`, `NewType`, `TypeVar`, `Generic`, `Annotated`, `NotRequired`, `Required`.

Authors are still encouraged to use modern lowercase forms (`list[X]`, `X | None`) where possible — those need no import. The auto-import is a safety net so a diagram using `Optional[str]` produces a runnable file rather than a `NameError` at import time.

For every remaining token `<Type>`, resolve as follows:

**Step 7a — Skip if Domain Package status is `missing`.** When the locations report flagged `Domain Package` as `missing` (Step 2), no domain scan is possible. Treat every remaining `<Type>` as **unresolved** and proceed to Step 7d.

**Step 7b — Glob the domain package.** Run (via Bash):

```
grep -rEn "^class <Type>\b|^<Type>\s*=" <domain_pkg_path> --include="*.py" || true
```

The trailing `|| true` ensures a no-match exit is non-fatal. Each result line has the shape `<absolute_path>:<lineno>:<matched line>`. Capture `<absolute_path>` for every hit. Skip files under `__pycache__/` defensively.

**Step 7c — Disambiguate.** Convert each captured `<absolute_path>` to a relative module path under `<pkg>.domain` by:

1. Stripping the prefix `<domain_pkg_path>/` to get a path like `shared/document_types.py` or `profile/events.py`.
2. Stripping the `.py` suffix and replacing `/` with `.` to get e.g. `shared.document_types`.
3. The fully-qualified module name is `<pkg>.domain.<relative_module>`.

Apply this cascade to select **one** module per `<Type>`. Each rule either resolves the type, aborts, or falls through to the next rule — fall-through paths are spelled out explicitly so the cascade is unambiguous.

1. **Single match overall** — exactly one path matched. Use it. Done.
2. **Filter to `<domain_pkg_path>/shared/`** — if the original match set contains at least one path under `shared/`, narrow to those.
   - **Exactly one shared match** — use it. Done.
   - **Two or more shared matches** — abort with the rule-4 message below (real name collision in the canonical-types module; manual disambiguation required). Do **not** fall through to rule 3.
   - **Zero shared matches** — fall through to rule 3 with the **original** unfiltered match set.
3. **Filter the original match set to `<domain_pkg_path>/<command_aggregate_snake>/`** — where `<command_aggregate_snake>` was derived in Step 4 from each row's `<CommandClass>` (e.g. `ProfileCommands` → `profile`). This rule applies only when **all** rows that referenced this `<Type>` share the same `<CommandClass>` (and therefore the same `<command_aggregate_snake>`); if `<Type>` is referenced from rows with mixed Command Classes, rule 3 yields nothing and falls through to rule 4.
   - **Exactly one local-aggregate match** — use it. Done.
   - **Zero or two-plus matches under `<command_aggregate_snake>/`** — fall through to rule 4.
4. **Still ambiguous** — abort with `Type '<Type>' resolves to multiple modules in <domain_pkg_path> — disambiguate manually: <module1>, <module2>[, ...].` and stop without writing any file. List every candidate module from the **original** match set in lexicographic order.

**PascalCase → snake_case rule** (used for `<CommandClass>` aggregate stripping in Step 4 and elsewhere):

1. `re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)` — break boundary between a run of uppercase letters and a CamelCase tail.
2. `re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', step1)` — break boundary between a lowercase/digit and an uppercase letter.
3. `.lower()` — lowercase the whole string.

Examples: `Profile` → `profile`, `OCRReport` → `ocr_report`, `OrderLine` → `order_line`.

**Step 7d — Mark unresolved.** Tokens that produced zero matches in Step 7b (or were skipped in Step 7a) are recorded in the per-event `<unresolved>[event_name]` set, keyed by which event class declared the field that referenced them. The class will receive a `# TODO: import <Type>` comment immediately above its `@dataclass` decorator (Step 8).

The output of Step 7 is two structures:

- `<resolved_imports>` — an ordered set of `(<full_module>, <Type>)` pairs, sorted by `<full_module>` then `<Type>` (case-sensitive ASCII).
- `<unresolved>` — `dict[event_name, list[Type]]`, with each per-event token list deduplicated and sorted.

### Step 8 — Render the canonical events.py content

The full canonical content for an `events.py` containing every external event class is the concatenation of an import block, an `__all__` line, and one class block per row of `<external_rows>` (in Table 2 source order, which is alphabetical by Event Name within the `external` group).

#### 8a. Import block

```python
from dataclasses import dataclass

from deps_pubsub.events.common import DomainEvent
<resolved_import_lines>
```

Where `<resolved_import_lines>` is one line per entry of `<resolved_imports>` (Step 7), in the canonical sort order, of the form `from <full_module> import <Type>`. **Do not** group multiple types from the same module onto one line — emit one `from ... import <Type>` per token, deterministic and trivially additive. If `<resolved_imports>` is empty, omit `<resolved_import_lines>` (and the preceding blank line collapses).

The two fixed import groups (`dataclasses`, `deps_pubsub.events.common`) are separated by exactly one blank line; the `<resolved_import_lines>` block (if any) follows immediately after `deps_pubsub.events.common` with no extra blank line between them.

#### 8b. `__all__` line

```python
__all__ = ["<EventName1>", "<EventName2>", ...]
```

In Table 2 source order (external-alphabetical). Wrapped onto a single line; if the resulting line exceeds 100 characters, break onto multiple lines using PEP 8 vertical-list formatting:

```python
__all__ = [
    "<EventName1>",
    "<EventName2>",
    ...
]
```

Separated from the import block by exactly one blank line above and exactly two blank lines below (PEP 8 — top-level definitions follow).

#### 8c. Class blocks

For each `<EventName>` in `<external_rows>` source order, render one block. Two adjacent class blocks are separated by exactly two blank lines (PEP 8 top-level).

**Without unresolved tokens:**

```python
@dataclass
class <EventName>(DomainEvent):
    <field_name_1>: <field_type_1>
    <field_name_2>: <field_type_2>
    ...
```

**With unresolved tokens** (i.e. `<unresolved>[<EventName>]` is non-empty):

```python
# TODO: import <Type1>, <Type2>, ...
@dataclass
class <EventName>(DomainEvent):
    <field_name_1>: <field_type_1>
    ...
```

The TODO comment lists every unresolved token for that class, comma-separated in the same order as `<unresolved>[<EventName>]`. Exactly one TODO line per class — even if the class references multiple unresolved tokens. If a token is unresolved across multiple classes, each class gets its own TODO line (the comment is per-class, not per-file).

**Empty-attributes case:** if a resolved class has zero attributes, render its body as a single `pass` line:

```python
@dataclass
class <EventName>(DomainEvent):
    pass
```

The file MUST end with exactly one trailing `\n`.

### Step 9 — Splice into the existing events.py (per-class additive with stub upgrade)

Compute the output path: `<messaging_pkg_path>/<consumer_name_snake>/events.py`.

**Pre-condition.** Two existence checks, in order (via Bash):

1. `test -d <messaging_pkg_path>/<consumer_name_snake>` — if the consumer subdirectory does **not** exist, abort with `<messaging_pkg_path>/<consumer_name_snake>/ missing — run @consumer-scaffolder first.` and stop.
2. `test -f <output_path>` — if `events.py` does **not** exist, abort with `<output_path> not found — run @consumer-scaffolder first.` and stop. (This agent never bootstraps `events.py` from scratch — that is `consumer-scaffolder`'s job.)

Read the file. Parse it loosely into a sequence of segments by scanning line-by-line.

**Class-line regex.** A "class line" matches `^class\s+(?P<name>[A-Z][A-Za-z0-9_]*)\s*(\(.*\))?\s*:\s*$` — captures the class name, tolerates an optional parenthesised parent-class clause.

**Decorator regex.** `^@dataclass(\(.*\))?\s*$` — matches both the bare `@dataclass` form and parameterized variants like `@dataclass(frozen=True)` or `@dataclass(slots=True)`.

**Block-preamble rule.** For each class line, scan **upward** from that line and absorb the contiguous run of immediately-preceding lines (no blank line breaks the run) that match either the decorator regex above OR `^#.*$` (any comment line). The absorbed preamble plus the class line plus the class body forms one **class block**. The block's first line is the topmost absorbed preamble line (or the class line itself if no preamble was absorbed); the block's last line is the line just before the next block's first line, or end-of-file. This rule preserves `# TODO: import <X>` comments emitted by prior runs as part of the class they annotate.

The file segments are:

1. **Header region** — every line from the top of the file up to (but excluding) the first class block's first line (per the block-preamble rule above). The header may contain imports, `__all__`, blank lines, comments, and module-level docstrings.

2. **Class blocks** — one per class declaration on disk. Capture each block's `<Name>` (from the class line) and its **classification**:
   - **STUB** — the block consists of exactly two non-blank lines: `class <Name>:` followed by `    pass`, with **no** preamble (no `@dataclass` decorator, no `# TODO` comment) and **no** parent class clause. This is exactly what `consumer-scaffolder` emits.
   - **IMPLEMENTED** — anything else (has any preamble, has a parent class, has any field, has any non-`pass` body line, has methods, has a docstring, etc.).

3. **Trailing region** — anything after the last class block (typically empty or one trailing newline).

**Compute per-event actions.** For every `<EventName>` in `<external_rows>`:

- If a parsed class block exists with that name AND its classification is **STUB** → action `UPGRADE`.
- If a parsed class block exists with that name AND its classification is **IMPLEMENTED** → action `SKIP` (preserve the block byte-identical).
- If no parsed class block exists with that name → action `ADD`.

**No-op short-circuit.** Skip the write and proceed straight to Step 10's report (recording 0 added, 0 upgraded, n_skipped) iff **all** of the following hold:

1. Every `<EventName>` action is `SKIP` (no new classes to add, no stubs to upgrade).
2. The existing header contains exact-line matches for `from dataclasses import dataclass` and `from deps_pubsub.events.common import DomainEvent`.
3. The existing header contains exact-line matches for every `(<full_module>, <Type>)` entry of `<resolved_imports>` (so no new resolved imports would be appended on regeneration).
4. The existing `__all__` parsed as a list literal AND `<existing_all>` already includes every `<EventName>` from `<external_rows>` (order is irrelevant for the short-circuit — a parsed `__all__` that already covers every name produces the same merged list, whether or not it's in canonical order).

If any of (1)-(4) fails, fall through to the regenerate-the-file branch below.

**Otherwise, regenerate the file.** Compose the new content as follows:

1. **Header — additively rebuilt, never wiped.** From the pre-existing header, parse three things:
   - **Module-level docstring** — the first triple-quoted string at module top, if any. Preserved verbatim.
   - **Existing imports** — every line matching `^import\s+\S+\s*$` or `^from\s+\S+\s+import\s+.+\s*$` (single-line forms only; this is the form the agent itself emits, so on rerun every prior import round-trips losslessly). A multi-line `from ... import (...)` form is unusual in this generated file; if encountered, its full physical span is preserved as-is and treated as an opaque single "existing import" for dedup purposes.
   - **Existing `__all__`** — the first line matching `^__all__\s*=\s*.+$`. If the RHS parses as a list literal of string entries (regex: `^\[\s*("[A-Za-z_][A-Za-z0-9_]*"\s*,?\s*)*\]$` after stripping the assignment prefix; or a multi-line list literal with the same entry shape), capture the parsed entries as `<existing_all>`. Otherwise mark `__all__` as **unrecognized** and pass the original line through verbatim — record a Step 10 warning (`existing __all__ has unrecognized form — left untouched; new event names not added`).
   
   Discard everything else in the header (free-form blank lines and free-form comments are not preserved — `events.py` is a generated module with no prose convention).
   
   Compose the new header in this fixed order, with exactly one blank line between adjacent groups (collapsed when a group is empty):
   
   1. Module-level docstring (if any).
   2. The two **fixed imports**: `from dataclasses import dataclass`, then `from deps_pubsub.events.common import DomainEvent` (one blank line between the two — they belong to different import groups by PEP 8 convention: stdlib vs third-party). Both lines are emitted unconditionally; if the existing header already contained one or both verbatim, the existing copies are NOT also emitted (dedup by exact-line match).
   3. **Existing imports**, in their original order, **excluding** any line that exactly matches one of the two fixed imports above and **excluding** any line that exactly matches an entry of `<resolved_imports>` (those are emitted in the next group, in canonical sort order).
   4. **New `<resolved_imports>`** entries (Step 7) not already present in the existing imports as exact-line matches, in canonical sort order (`(<full_module>, <Type>)`). One `from <full_module> import <Type>` per line.
   5. **`__all__` line** — if `__all__` was parseable, the merged list is `<existing_all>` followed by every `<EventName>` from `<external_rows>` (in Table 2 order) not already in `<existing_all>`. Format per Step 8b. If `__all__` was unrecognized, emit the captured original line verbatim instead.
   
   Then exactly two blank lines before the first class block (PEP 8 — top-level definitions follow).

2. **Class blocks — Table 2 source order.** For each `<EventName>` in `<external_rows>` source order:
   - Action `ADD` or `UPGRADE` → emit the freshly-rendered block from Step 8c.
   - Action `SKIP` → emit the original block's text **byte-identical** (every line from the block's first line — the topmost absorbed preamble line per Step 9.2's block-preamble rule — through its last line, with trailing whitespace preserved).
   - Adjacent blocks separated by exactly two blank lines.

3. **Trailing region — discarded.** Original trailing whitespace is replaced by a single trailing `\n` at EOF.

Write the resulting content to `<output_path>` (via the Write tool, single full-file write — Edit cannot express the structural rewrite cleanly).

### Step 10 — Report

Print exactly one line:

`Implemented events.py for <consumer_name_snake> (<n_added> added, <n_upgraded> upgraded, <n_skipped> preserved, <n_unresolved_total> unresolved type token(s) flagged).`

Where:

- `<n_added>` = count of `ADD` actions.
- `<n_upgraded>` = count of `UPGRADE` actions.
- `<n_skipped>` = count of `SKIP` actions.
- `<n_unresolved_total>` = sum over `<unresolved>` of the per-event list lengths (counts each TODO token once per class that needs it, matching the rendered TODO comments).

If `<n_unresolved_total>` > 0, append one warning line per class with unresolved tokens, in Table 2 source order:

`  WARN: <EventName> references unresolved type token(s) <Type1>, <Type2>, ...; review TODO comments and add imports manually.`

If Step 9's existing-`__all__` parse marked it unrecognized, append a second class of warning line:

`  WARN: existing __all__ has unrecognized form — left untouched; new event names not added.`

(All warning lines are two-space indented so they are visually distinct from the headline.)

If the no-op short-circuit fired in Step 9, print instead:

`events.py for <consumer_name_snake> already up to date — no changes (<n_skipped> classes preserved).`

## Constraints

- Never bootstrap `events.py` from scratch — `@consumer-scaffolder` owns initial creation. This agent fails fast when `events.py` is missing, preserving a clean ownership boundary.
- Never modify a class block whose classification is `IMPLEMENTED` — its content is preserved byte-identical, regardless of whether its fields match the diagram. Drift between spec and code is the author's signal that the diagram and the file have diverged; this agent does not arbitrate.
- Never preserve a class block whose classification is `STUB` — those exist solely as scaffolder placeholders and are always upgraded to `@dataclass` form on first run.
- Never write to `events.py` for a consumer whose Table 2 has zero `external` rows — the file may legitimately not exist at all in that case (`consumer-scaffolder` skips it). Print a one-line no-op report and stop.
- Never check the `<<Domain Event>>` stereotype on the resolved class — Table 2's `external` Type is the contract; any class declared in the commands diagram with the matching name is consumed for its attribute list. (This is a deliberate divergence from `event-fields-writer`, which validates stereotypes; this agent trusts the spec author.)
- Never invent fields, field types, or field order — every field is taken verbatim (name, type) from the resolved class's diagram declaration in declaration order. Empty-attribute classes render `pass`.
- Auto-import scope: domain types from `<pkg>/domain/**` (resolved by glob) and `typing` module names (auto-imported from a fixed allow-list). Single-letter TypeVars (`T`, `K`, `V`, `R`, `S`, `P`) are skipped without import; rename them in the diagram if a real domain class shares the name. Imports beyond these two scopes (stdlib `uuid.UUID`, project `infrastructure` types, etc.) are author-managed — emit `# TODO: import <Type>` comments and let the user resolve them after generation.
- Never emit grouped imports (`from X import A, B`) — one `from <module> import <Type>` per token, ordered by `(<module>, <Type>)`. This makes the import block trivially additive on subsequent runs.
- Never silently pick between ambiguous type matches across two non-`shared`, non-local-aggregate domain modules — abort with a manual-disambiguation error listing every candidate. The local aggregate is the snake_case form of the row's `<CommandClass>` minus the `Commands` suffix (e.g. `ProfileCommands` → `profile`), NOT the row's Source Destination.
- Domain package missing in the locations report is non-fatal — every PascalCase token falls through to `# TODO: import <Type>` comments and gets reported as unresolved. The agent still writes a structurally correct file; the user resolves imports manually.
- `<pkg>` is mechanically derived from the locations report's absolute paths — do not infer it from `<commands_diagram>`'s containing directory or from any heuristic on the project name. The locations report is the source of truth.
- File ordering: import block, `__all__`, then class blocks in Table 2 source order. The order is intentionally mechanical so reruns produce byte-identical output (modulo `IMPLEMENTED`-block content, which is the user's responsibility).
- Idempotent: re-running on an unchanged commands diagram, unchanged consumer spec, unchanged locations report, and unchanged disk state is a no-op (zero files written, headline report prints `already up to date`).
