---
name: adr-structure-description
description: Explains the purpose and conventions of each ADR section. Use when reviewing ADR sections, understanding ordering rationale, or explaining ADR structure to others.
user-invocable: false
disable-model-invocation: false
---

# ADR Structure Description

**Type:** Reference

ADRs are structured with the reader — not the writer — in mind. Completed ADRs have the following sections in this order:

---

## Sections Overview

| Section | Description |
| --- | --- |
| ID and Title | A unique identifier plus a very short summary of the decision (e.g., `ADR001—Use AKS for Kubernetes Pods`). The title should state the decision taken, not just the topic. |
| Status and Date | State of the ADR: typically Draft, Proposed, Adopted, Superseded, or Retired. The date reflects when the status last changed. |
| Author | The person (or team) accountable for the decision and the point of contact for questions. |
| Decision | The decision taken, described in a few sentences. Intentionally sparse — states intent and next actions only. |
| Context | The forces and circumstances that brought about the decision. |
| Options Considered | Each considered option described briefly, with pros and cons. The selected option comes first. |
| Consequences | The ramifications of selecting each option, both positive and negative. |
| Advice | Raw outputs from the advice process: all offered advice, with adviser name, role, and date. |

---

## Section Details

### ID and Title

- Format: `ADR{NNN}—{Short decision statement}` (e.g., `ADR002—Shorten Inventory IDs with Nano ID`)
- The title states the decision itself, not just the topic — this lets readers parse the decision history at a glance without opening each ADR.
- IDs must be unique and are typically included in the title.

### Status and Date

- **Status** tells the reader where the ADR sits in the decision process.
- **Date** records when the status last changed, placing the decision in a timeline.
- ADRs are point-in-time artifacts — once completed, they become effectively immutable (like entries in an event log).

### Decision

- Intentionally sparse: declares intent and next actions for implementers.
- Does **not** include: the problem context, unchosen options, or reasoning — those are in the following sections.
- Written last (after advice-seeking is complete).

### Context

- Explains why the decision matters and the circumstances at the time.
- Includes applicable requirements (cross-functional and functional), technical, sociotechnical, and organizational facts.
- Positioned after Decision (not before) — the decision itself is more important to a first-time reader than the background.

### Options Considered

- Lists every option considered, not just the one selected.
- Having only one option is a bad smell — there is always more than one way to go.
- The first option listed is traditionally the selected one.
- Each option is described lightly; consequences are handled in the next section.

### Consequences

- Details why the selected option was chosen and why each other option was not.
- For the **selected option**: includes both benefits and drawbacks (drawbacks = risks to mitigate).
- For **rejected options**: includes only the killer drawbacks (occasionally benefits too, to show the trade-off).

### Advice

- A bulleted list of contributions from advice offerers.
- Format: `[Advice] (Adviser name, role, date)`
- Recorded verbatim and unfiltered — the author mines this to shape the final decision.
- Acts as a learning resource showing how decisions were formed and who to consult in future.

---

## On Experimenting with the Template

The sections above — title, meta-elements, decision, context, options, consequences, advice — are essential and their order matters. However, you can add sections if your context requires them. Remove sections that teams consistently leave empty; a section filled half-heartedly defeats the purpose of the record.
