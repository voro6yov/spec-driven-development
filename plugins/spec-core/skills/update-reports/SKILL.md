---
name: update-reports
description: "Umbrella catalog of the cross-layer spec-update detector report schemas (domain, application-service axis, ops). Each schema lives in a sibling `<layer>/index.md` folder of this file. Load to resolve the report schema the cross-layer update cascade's detectors emit and downstream layers parse."
user-invocable: false
---

# Update Reports (spec-core)

The spec-update **detector** reports are the data contracts of the cross-layer update cascade that `spec-core:update-specs` orchestrates. Each layer's detector produces one; downstream layers parse them by these schemas. They are homed here in spec-core — next to the orchestrator — because they are consumed across plugin boundaries (a domain-diagram diff drives persistence, application, REST API, and messaging; the application-service and ops diffs drive REST API and messaging).

Each schema is a **supporting file** in a sibling folder; Read it by path. Only this index is auto-loaded by frontmatter — the per-layer docs are not.

| Schema | Path | Produced by | Describes |
|---|---|---|---|
| domain | [domain/index.md](domain/index.md) | `domain-spec:updates-detector` | `<stem>.domain/updates.md` — the class-grouped domain-diagram diff + stereotype→category footer |
| application-axis | [application/index.md](application/index.md) | `application-spec:{commands,queries}-updates-detector` | `<stem>.application/{commands,queries}-updates.md` — the application-service diagram diff |
| ops | [ops/index.md](ops/index.md) | `application-spec:ops-updates-detector` | `<stem>.application/ops-updates.md` — the per-`<op-name>` ops-service diagram diff |

**Resolution.** A consumer that auto-loads `spec-core:update-reports` via frontmatter resolves `<update_reports_dir>` as the directory containing this `SKILL.md` (its loaded context reveals its location), then Reads `<update_reports_dir>/<layer>/index.md`. Hard-fail on a missing path; never skip silently.

**Not homed here.** Each layer's own **code-update** report (`<stem>.persistence/updates.md`, `<stem>.application/updates.md`, `<stem>.rest-api/updates.md`, `<stem>.messaging/updates.md`) — the `## Affected Artifacts` dispatch schema each plugin's `update-code` flow consumes — remains a plugin-private supporting file under that plugin's own `patterns` umbrella. Only the cross-consumed detector schemas live here.
