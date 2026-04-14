---
name: adr-example
description: Completed ADR example (Nanoid inventory IDs). Use when reviewing a finished ADR, verifying section quality, or understanding what well-formed ADR content looks like.
user-invocable: false
disable-model-invocation: false
---

# ADR Example

**Type:** Reference

---

- Status: Accepted
- Date: 2020-03-25
- Author: Wisen Tanasa

## Decision

We will create shorter inventory IDs with randomly generated letters and numbers (Option 1). This will involve Nanoid with the following configuration:

- Building ID: length 6, characters `23456789ABCDEFGHJKMNPQRSTUVWXYZ`
- Space ID: length 8, characters `0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz`
- Provider ID: length 5, characters `0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz`

## Context

Our inventory IDs are currently UUID-style (e.g., `22cadcb6-00e5-4baa-a701-785854fc2a9e`). As inventory scales, these are too long. Shorter IDs improve UX:

- Users can type them into a browser when printing a building page.
- URLs can be shared without a URL shortener.

Decision criteria:

- Short
- Low collision probability
- Unambiguity — `0` (zero) and `O` (capital O) must not be confused
- Cost of implementation

## Options Considered

### Option 1 (SELECTED): Random generated letters and numbers with Nanoid

#### Consequences

- Selected because no infrastructure provisioning is required — the ID can be generated client-side with the Nanoid library.
- Selected because it works in serverless architecture.
- Selected because collision probability is low (even at 1 building ID/hour, collision probability is ~0.001%).
- Selected despite the small possibility of generating profanity words (likelihood is very low and IDs will clearly appear randomly generated to external consumers).

### Option 2: Automatically generated sequence ID

#### Consequences

- Rejected because it requires new infrastructure (not compatible with serverless architecture).

### Option 3: Manually generated ID

#### Consequences

- Rejected because it requires excessive human intervention.
- Rejected despite guaranteeing no collisions and no profanity words.

### Option 4: Pretty generated letters and numbers

#### Consequences

- Rejected because no free, appropriately licensed open-source library was found for this approach.

### Option 5: Combination of building name and generated ID

#### Consequences

- Rejected because a slug prefix can be added separately if needed for URL clarity.

## Advice

- Have we thought about the possibility of auto-generated profanity? It could be reputationally harmful. *(Monira R., Product Manager, 25 Aug 2024)*
- What is the collision probability for each option? Have we considered database-side ID generation? *(Hanna A., Infra team, 24 Aug 2024)*
- Does making the ID human-meaningful matter, or just human-readable? *(Rebecca F., UX, 25 Aug 2024)*
- Can we list all places where this ID will be used? *(Izzy H., Tech Lead — Site Search, 28 Aug 2024)*
- Will IDs be exposed publicly? Consider leakage of internal data models and attack surface. *(Pete H., Infosec, 25 Aug 2024)*
- What are the licensing concerns? Will any option cost more as we scale? *(Alina B., Architect, 24 Aug 2024)*
