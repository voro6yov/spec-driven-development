---
name: adr-creation-steps
description: Step-by-step guide for writing ADRs through the advice process. Use when starting an ADR, guiding the decision workflow, or facilitating advice-seeking.
user-invocable: false
disable-model-invocation: false
---

# ADR Creation Steps

**Type:** Reference

---

## Step 1: Create Your Empty ADR and Set Its Metadata

Create a new ADR file from the template. Add a self-evident placeholder title (e.g., `(DRAFTING) Changing subscription payment details`) and a unique ID (e.g., `ADR-003`). This announces to everyone that a decision process has begun.

Set:
- **Status:** Draft
- **Date:** today
- **Author:** your name (or team name)

> **Tip:** ADR titles should ultimately state the decision taken. At the start, you don't yet know that — so a placeholder title is fine. It may change multiple times before a decision is reached.

---

## Step 2: Write the Context

The Context section explains why a decision is required. Write it before the Decision section — leave Decision blank for now.

A good Context section:
- States the forces, constraints, and relevant historical steps that led here.
- Includes applicable requirements (cross-functional and functional).
- Includes technical, sociotechnical, and organizational facts.
- Is thorough enough that potential advisers have what they need to offer useful advice.

**Approach:**
1. Brain-dump everything relevant — don't worry about structure yet.
2. Focus and trim: remove extraneous details, keep what future readers need.
3. Add diagrams if they help (even hand-drawn photos work at this stage).
4. Update the ADR title so it now asks the question the decision will answer.

> Seeking advice on the Context section before writing anything else is fine — just tell advisers where you are in the process.

---

## Step 3: Make Options and Gather Their Consequences

Once the Context is solid, work on options and consequences (skip the Options section header for now; work in the Consequences section first).

- Start with options you already know about.
- Always consider "do nothing" and "not yet" as explicit options.
- Aim for 3–5 options (fewer than 2 is a bad smell; more than 10 risks analysis paralysis).
- For each option, list pros and cons. Let the brain dump be messy first, then tidy up.

---

## Step 4: Propose a Selected Option

Once you have a comprehensive options set with consequences, provisionally select one (if you feel confident).

- Mark the provisionally selected option clearly (e.g., "SELECTED" or "provisionally selected").
- Update Status from **Draft** to **Proposed**.
- Leave the Decision section empty — it will be filled after advice-seeking is complete.

> **Note on authority:** If you are in a position of authority, consider whether to include a provisional selection. The anchoring effect of authority can be strong and may unduly influence advisers.

---

## After Step 4: Advice-Seeking Phase

With options and provisional selection in place, seek advice from stakeholders. Record all advice in the **Advice** section verbatim, including name, role, and date of each adviser. Then incorporate the advice into the body of the ADR and write the final **Decision** section.
