---
name: patterns
description: "Umbrella catalog of all rest-api-spec pattern references. Each pattern lives in a sibling folder of this file — `<pattern-name>/` containing `index.md` (the pattern doc) plus an optional `examples.md` companion. Load to resolve pattern names to their reference docs by path instead of per-pattern skill invocations."
---

# Rest-api-spec pattern catalog (umbrella)

This skill is a path-resolution anchor: it registers **one** catalog entry for all rest-api-spec
pattern references. The pattern docs themselves are **supporting files** in folders next to this
`SKILL.md` and are never auto-loaded — consumers Read them on demand.

## Resolution rule

Every pattern named `<pattern-name>` resolves to the **folder** `<pattern-name>/` sibling to this
file:

- the pattern document is always `<pattern-name>/index.md`;
- companions, when present, sit in the same folder (`examples.md` — worked examples). Relative
  links inside `index.md` (e.g. `[examples.md](examples.md)`) resolve within that folder.

A pattern name that has no matching folder is an **error** — report it loudly; never skip it
silently.

## Catalog

| Pattern | Folder | Companions | Registered twin |
|---|---|---|---|
| api-client-fixtures | [api-client-fixtures/](api-client-fixtures/) | — | — |
| api-endpoint-test-rules | [api-endpoint-test-rules/](api-endpoint-test-rules/) | — | — |
| auth-middleware | [auth-middleware/](auth-middleware/) | — | — |
| command-action-endpoint | [command-action-endpoint/](command-action-endpoint/) | — | — |
| constants | [constants/](constants/) | — | — |
| endpoint-io-template | [endpoint-io-template/](endpoint-io-template/) | examples.md | — |
| endpoint-tables-template | [endpoint-tables-template/](endpoint-tables-template/) | — | — |
| endpoints | [endpoints/](endpoints/) | — | — |
| entrypoint | [entrypoint/](entrypoint/) | — | — |
| error-handlers | [error-handlers/](error-handlers/) | — | — |
| file-upload-endpoint | [file-upload-endpoint/](file-upload-endpoint/) | — | — |
| infrastructure-exception-handlers | [infrastructure-exception-handlers/](infrastructure-exception-handlers/) | — | — |
| internal-router | [internal-router/](internal-router/) | — | — |
| literal-type-fields | [literal-type-fields/](literal-type-fields/) | — | — |
| nested-resource-endpoints | [nested-resource-endpoints/](nested-resource-endpoints/) | — | — |
| nested-response-serializers | [nested-response-serializers/](nested-response-serializers/) | — | — |
| pagination-serializers | [pagination-serializers/](pagination-serializers/) | — | — |
| polymorphic-response-serializers | [polymorphic-response-serializers/](polymorphic-response-serializers/) | — | — |
| query-params | [query-params/](query-params/) | — | — |
| request-serializers | [request-serializers/](request-serializers/) | — | — |
| resource-spec-template | [resource-spec-template/](resource-spec-template/) | — | — |
| response-serializers | [response-serializers/](response-serializers/) | — | — |
| result-set-serializer | [result-set-serializer/](result-set-serializer/) | — | — |
| simple-command-response | [simple-command-response/](simple-command-response/) | — | — |
| static-response-serializer | [static-response-serializer/](static-response-serializer/) | — | — |
| surface-markers | [surface-markers/](surface-markers/) | — | ✦ |
| updates-report-template | [updates-report-template/](updates-report-template/) | — | — |
| version-router | [version-router/](version-router/) | — | — |

> **Authoritative copies & dual-homed twins.** For most patterns these folders are the **only**
> copy — the standalone `rest-api-spec:<pattern>` skills were deregistered (Wave 1 of the
> umbrella-skill demotion, `notes/active-skills-footprint.md` §0.4/§0.5). The one row marked ✦
> is **dual-homed**: a standalone skill `rest-api-spec:<pattern>` is still registered because a
> foreign plugin consumes it (`surface-markers` — cited by application-spec as the single source
> of truth for marker syntax); it remains the authoritative source until Wave 3 demotes it. The
> umbrella copy must stay **byte-identical** to its registered twin — when editing a ✦ pattern,
> edit the standalone skill first, then re-sync `<pattern>/index.md` from it.
