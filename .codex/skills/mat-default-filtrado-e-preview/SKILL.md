---
name: mat-default-filtrado-e-preview
description: Use when analyzing, documenting, or changing Mat_Default behavior in Custeio Items, especially contextual dropdown filtering, Definicoes de Pecas as rule source, safe fallback to existing logic, and lightweight tooltip preview from Dados Items.
---

# Mat Default Filtrado e Preview

## Overview

Use this skill for work on the `Mat_Default` column in `Custeio Items`.

This skill exists to keep future changes aligned with the current Martelo contract:

`Dados Gerais -> Dados Items -> Custeio Items`

It is for analysis and incremental evolution. It is not a license to replace the current behavior without first mapping what already works.

## When To Use

Use this skill when the task involves any of the following:

- changing what appears in the `Mat_Default` dropdown
- tracing how a `Custeio` row maps to allowed material, ferragem, or sliding-system groups
- improving the role of `Definicoes de Pecas` in the filter contract
- adding preview support while navigating dropdown options
- reviewing regressions caused by parent/child rows, composed components, or special ferragem rules

Use together with [../martelo-dados-gerais-items/SKILL.md](../martelo-dados-gerais-items/SKILL.md) when the task touches the origin data in `Dados Items`.

When the task affects rows generated from modules or composed structures, also read:

- [../../../docs/modulos_reutilizaveis_martelo.md](../../../docs/modulos_reutilizaveis_martelo.md)
- [../../../docs/catalogo_modulos_referencia.md](../../../docs/catalogo_modulos_referencia.md)

## Core Contract

- `Mat_Default` is not only a display value. It is the source group used to resolve row data in `Custeio`.
- The preferred source of options is the active item data in `Dados Items`, mainly `Materiais`, `Ferragens`, and `Sistemas Correr`.
- Filtering must be contextual to the current row. A piece row must not receive absurd ferragem options, and a ferragem row must not look like a generic material row.
- `Definicoes de Pecas` should become the preferred rule source for allowed groups, but only with safe fallback to the current behavior.
- Preview inside the dropdown must support navigation only. Hover/highlight must not commit a value or mutate the row.

## Workflow

1. Read [references/visao-funcional.md](references/visao-funcional.md).
2. Read [references/implementacao-atual.md](references/implementacao-atual.md) before editing anything.
3. Separate current behavior from desired behavior.
4. If the task changes filtering, prefer a central resolver function for allowed options per row.
5. Prefer rules backed by `Definicoes de Pecas`, but keep explicit fallback to the current delegate/service logic.
6. Re-check composed rows, `DIVISAO INDEPENDENTE`, sliding-door systems, and special ferragem cases.
7. In the final answer, state:
   - current resolver path
   - new rule source
   - fallback behavior
   - regression risks

## What To Protect

- do not break rows that already resolve correctly
- do not mix `Materiais`, `Ferragens`, and `Sistemas Correr` without rule-based intent
- do not remove manual freedom in `Custeio`
- do not break parent/child behavior in composed components
- do not let UI preview change values implicitly

## Key References

- Functional framing: [references/visao-funcional.md](references/visao-funcional.md)
- Current code map: [references/implementacao-atual.md](references/implementacao-atual.md)
