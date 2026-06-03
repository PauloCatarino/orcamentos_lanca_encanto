---
name: martelo-protecao-dados-criticos
description: Use when analyzing, proposing, or executing any Martelo cleanup, migration, normalization, deduplication, replacement import, bulk correction, or deletion that can remove, overwrite, or irreversibly change existing business data in the database or persisted budget files.
---

# Martelo Protecao Dados Criticos

## Overview

Use this skill before any task that can destroy, replace, or silently rewrite existing Martelo data.

This skill exists to prevent accidental loss of the most valuable asset in the system: the user's business data.

## Mandatory Rules

- Treat `DELETE`, `DROP`, `TRUNCATE`, bulk `UPDATE`, import with replace, cleanup scripts, deduplication scripts, corrective migrations, and destructive filesystem cleanup as high-risk actions.
- Never execute high-risk actions automatically or because they seem like the fastest technical fix.
- Never assume user intent for data deletion, even when the task mentions "limpar", "corrigir", "normalizar", or "reimportar".
- If a change can remove or overwrite existing records, require explicit user confirmation before execution.

## Required Workflow

1. Diagnose the problem first.
2. State exactly what data is at risk:
   - tables, models, or files
   - estimated records or scope
   - whether cascading deletes or replace semantics are involved
3. Propose the safest path first:
   - dry-run or report
   - transaction
   - backup/export/snapshot
   - soft-delete/quarantine
4. Ask for explicit confirmation before any irreversible step.
5. Only after confirmation, execute the destructive step.
6. Report what was executed and what remains recoverable.

## Confirmation Standard

Before execution, summarize in plain language:

- what will be deleted, replaced, or rewritten
- why it is needed
- what cannot be undone
- what backup or rollback path exists

If any of those points are unknown, stop and resolve that gap before proceeding.

## Scope Notes

- Normal user editing inside the Martelo UI is not automatically the same as technical cleanup.
- Internal save flows that temporarily replace rows as part of a confirmed user edit do not justify hidden maintenance scripts elsewhere.
- When working near `Dados Gerais`, `Dados Items`, `Custeio Items`, or reusable models, be especially careful with cascade effects.

## Project References

- Read [../../../AGENTS.md](../../../AGENTS.md) for the global project rule on critical data protection.
- If the task touches `Dados Gerais`, `Dados Items`, import/model persistence, or the bridge into `Custeio`, also use [../martelo-dados-gerais-items/SKILL.md](../martelo-dados-gerais-items/SKILL.md).
