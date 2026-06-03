---
name: martelo-dados-gerais-items
description: Use when analyzing, documenting, or changing the Martelo logic for Dados Gerais, Dados Items, model save/import flows, Materias-Primas reconciliation, and the bridge into Custeio Items.
---

# Martelo Dados Gerais / Dados Items

## Overview

Use this skill for work on the functional and technical contract of `Dados Gerais` and `Dados Items` in `Martelo_Orcamentos_V2`.

This skill is for the part of the product where the 4 menu tables (`Materiais`, `Ferragens`, `Sistemas Correr`, `Acabamentos`) define the rule chain:

`Dados Gerais -> Dados Items -> Custeio Items`

## When To Use

Use this skill when the task involves any of the following:

- analyzing or documenting the role of `Dados Gerais` or `Dados Items`
- changing persistence, import, save, rename, delete, or model logic for these menus
- changing the bridge between `Dados Gerais`, `Dados Items`, and `Custeio Items`
- reviewing behavior tied to `Materias-Primas` merge or price conflict resolution
- clarifying the difference between global/shared models and local item-scoped models

Do not use this skill for module catalog work unless the task explicitly touches `Dados Gerais`, `Dados Items`, or their effect on `Custeio`.

## Core Rules

- Preserve the 3-level rule system defined in `AGENTS.md`: `Dados Gerais`, `Dados Items`, and local edit in `Custeio`.
- Preserve the 4-table structure in both pages unless the task explicitly changes product scope.
- Keep the distinction between:
  - saving data into the active `orcamento` or `item`
  - saving a reusable model for later import
- Treat `Materias-Primas` reconciliation as part of the import contract, not as an incidental UI detail.
- Do not assume models persist the full visible row. Check the actual model contract before changing anything.
- If the task can delete, replace, or bulk-rewrite existing data, also use [../martelo-protecao-dados-criticos/SKILL.md](../martelo-protecao-dados-criticos/SKILL.md) before executing changes.
- When proposing a change, say whether it affects:
  - `Dados Gerais`
  - `Dados Items`
  - the bridge to `Custeio Items`
  - model persistence/import

## Workflow

1. Read `AGENTS.md` and keep the 3 levels of rules explicit in the analysis.
2. Read [references/visao-funcional.md](references/visao-funcional.md) for the business meaning and user flow.
3. Read [references/implementacao-atual.md](references/implementacao-atual.md) for the current code contract before editing anything.
4. If the task changes behavior, inspect both the service layer and the page/dialog layer.
5. If the task affects `Dados Items`, also inspect the bridge from `Custeio Items`, especially `Preencher Dados Items` and sync checks.
6. In the final answer, separate:
   - current behavior
   - intended behavior
   - proposed change
   - scope/risk

## What To Verify Before Editing

- Which scope owns the data: `orcamento`, `item`, `user`, or shared/global.
- Whether the change affects fixed rows/order for the 4 menus.
- Whether import is `replace` or `append/merge`.
- Whether the change touches the `Materias-Primas` comparison dialog.
- Whether the change alters what is stored inside a model versus what is rehydrated on import.

## Key References

- Functional rules and terminology: [references/visao-funcional.md](references/visao-funcional.md)
- Current implementation map and nuances: [references/implementacao-atual.md](references/implementacao-atual.md)
- Reusable task prompt template: [references/prompt-mestre.md](references/prompt-mestre.md)
- For contextual `Mat_Default` filtering and dropdown preview in `Custeio Items`, also use [../mat-default-filtrado-e-preview/SKILL.md](../mat-default-filtrado-e-preview/SKILL.md)
