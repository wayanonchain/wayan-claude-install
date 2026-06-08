---
name: file-analyst
description: Analyze uploaded files — PDFs, screenshots, reports, contracts — and extract what matters.
read_only: true
---

# File Analyst

## Purpose
Read an uploaded file and turn it into a tight, actionable briefing.

## When to use
- A document/photo was uploaded (the gateway saves it to `uploads/` and gives
  you the absolute path).
- The operator asks you to summarize, review, or extract from a file.

## How to think
- **Read the file first** (the prompt gives you the exact path). If you cannot
  read it, say so and explain why — never guess at contents.
- Distinguish facts in the document from your inference.
- For contracts/legal/financial docs, surface obligations, deadlines, fees,
  and anything unusual or risky.
- If the operator asked for a deliverable file, write it into `outbox/` so it is
  returned automatically.

## Output format
- **Summary** — 2–4 sentences
- **Key points** — bulleted, the most important facts
- **Risks** — what could go wrong / what to be careful about
- **Action items** — concrete next steps
- **Questions to ask** — what's missing or needs clarification

## Rules
- Read-only playbook — do **not** edit this file.
- If you find an improvement, write a proposal in `skills/_proposals/`.
