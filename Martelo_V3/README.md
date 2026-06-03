# Martelo V3 - Protótipo

Este pacote é separado do `Martelo_Orcamentos_V2` e não grava dados reais. O objetivo é validar o fluxo gráfico e funcional do MVP de orçamentação guiada.

## Executar

```powershell
.\.venv_Martelo\Scripts\python.exe -m Martelo_V3.run_demo
```

Alternativa:

```powershell
.\.venv_Martelo\Scripts\python.exe run_martelo_v3_demo.py
```

## O que a demo inclui

- Navegação V3: Orçamentos, Items, Configurador, Custeio, Proposta, Produção, Bibliotecas e Configurações.
- Configurador por etapas: resumo, módulo/medidas, materiais/ferragens, peças geradas, custos, cálculo linha e validação.
- Catálogo simulado com roupeiros, portas de correr, cozinha e WC.
- Custeio V3 com estrutura, regra aplicada, fórmula, resultado, custo e override local separados.
- Proposta com custo interno, custos administrativos, margem e preço proposto.

## Como o cálculo demo funciona

Cada linha do custeio guarda as fórmulas das suas parcelas:

- Peças: `área m2 = comp x larg / 1000000`; material = `área x quantidade x preço m2`.
- Orlas: `ml = ((comp x lados compridos) + (larg x lados curtos)) / 1000 x quantidade`.
- Acabamentos: `área x faces x quantidade x preço m2/face`.
- Ferragens: `quantidade x preço unitário`.
- Produção: `minutos / 60 x custo hora x quantidade`.
- Linha: `material + orla + acabamento + produção`.
- Item/proposta: soma das linhas, custos administrativos e margem.

O objetivo não é fechar já a fórmula final da fábrica, mas tornar visível onde cada parte do preço nasce.

## Instalação V3 prevista

- Aplicação instalada localmente em cada posto da fábrica.
- Base de dados V3 partilhada no servidor da empresa.
- Cada posto liga por configuração própria (`DB_URI`/`.env`) e credenciais do utilizador.
- Transações curtas, bloqueio lógico por orçamento/item em edição, histórico de alterações e backups no servidor.
- Importação do V2 deve ser read-only na fase inicial.

## Referências funcionais analisadas

- Microvellum: estimativas com materiais, mão de obra, custos de produção, relatórios e propostas.
- Mozaik/Cabinet Vision: ligação entre desenho, cut lists, ferragens, relatórios e CNC.
- PolyBoard: relatórios por materiais, orlas, ferragens, operações e custos adicionais.
- Kerf: quoting rápido com material real, orlas, mão de obra e markup.

## Guardrail

A fase atual é apenas protótipo clicável. Importação do V2 deve continuar read-only até existir plano de migração validado.
