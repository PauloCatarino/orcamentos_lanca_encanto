# Prompt Mestre

Usa este prompt como base para futuras tarefas sobre `Dados Gerais` e `Dados Items`.

```text
Usa $martelo-dados-gerais-items para analisar e trabalhar a area de Dados Gerais / Dados Items do projeto Martelo_Orcamentos_V2.

Objetivo:
[descrever a tarefa concreta]

Contexto funcional a respeitar:
- manter a sequencia correta: Dados Gerais -> Dados Items -> Custeio Items
- preservar a logica das 4 tabelas: Materiais, Ferragens, Sistemas Correr e Acabamentos
- nao misturar "guardar dados do contexto atual" com "guardar modelo reutilizavel"
- respeitar a diferenca entre base geral do orcamento e base especifica do item
- preservar a possibilidade de edicao local no Custeio

Regras de execucao:
- alinhar com AGENTS.md e com a skill
- confirmar o comportamento real no codigo antes de alterar logica funcional
- considerar a reconciliacao com Materias-Primas ao importar modelos
- nao assumir que os modelos guardam a linha completa da grelha
- explicar se a alteracao afeta Dados Gerais, Dados Items, modelos/importacao ou a ponte para Custeio

Se fizeres alteracoes, analisa pelo menos:
- app/services/dados_gerais.py
- app/services/dados_items.py
- ui/pages/dados_gerais.py
- ui/pages/dados_items.py
- ui/pages/custeio_items.py, se a tarefa tocar a ponte com Custeio

Resultado esperado:
- ficheiros alterados
- resumo do comportamento atual
- alteracao proposta ou implementada
- riscos / pontos sensiveis
- ambiguidades para validar depois
```

## Variante curta

```text
Usa $martelo-dados-gerais-items.

Preciso de [analisar / corrigir / documentar / evoluir] a area de Dados Gerais / Dados Items no Martelo.

Tarefa:
[pedido]

Mantem:
- Dados Gerais -> Dados Items -> Custeio Items
- 4 tabelas principais
- distincao entre guardar dados e guardar modelo
- reconciliacao com Materias-Primas quando relevante

No fim indica:
- comportamento atual
- alteracao feita ou proposta
- ficheiros tocados
- riscos e ambiguidades
```

## Quando usar a versao longa

Usa a versao longa quando:

- a tarefa mexe em persistencia
- a tarefa mexe em importacao ou modelos
- a tarefa mexe na ponte com `Custeio Items`
- queres uma resposta mais auditavel

## Quando usar a versao curta

Usa a versao curta quando:

- a tarefa e pequena
- precisas apenas de analise rapida
- queres reutilizar a skill sem repetir muito contexto
