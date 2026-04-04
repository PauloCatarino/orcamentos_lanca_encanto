# Roadmap Martelo

## Objetivo do roadmap
Este roadmap organiza a evolucao do Martelo de forma incremental, com prioridade para estabilidade funcional, coerencia de calculo e reutilizacao de conhecimento.

O criterio principal nao e adicionar funcionalidades depressa. E consolidar as areas que sustentam o negocio:

- modulos reutilizaveis
- coerencia entre Dados Gerais, Dados Items e Custeio
- estabilidade da tabela `tab_custeio_items`
- preparacao de producao
- historico reutilizavel
- integracoes externas

## Principios de execucao
Cada fase deve respeitar estas regras:

- evolucao incremental e segura
- compatibilidade com orcamentos anteriores sempre que possivel
- testes nas zonas sensiveis
- documentacao funcional antes de grandes refactors
- protecao da edicao manual onde ela e necessaria
- separacao clara entre regra global, regra do item e override local

## Fase 1. Consolidacao do nucleo funcional
Foco: estabilizar as bases do comportamento do sistema.

Prioridades:

- consolidar a logica dos modulos reutilizaveis
- clarificar o contrato funcional de um modulo
- reduzir ambiguidade entre Dados Gerais, Dados Items e Custeio
- reforcar a seguranca funcional da `tab_custeio_items`

Entregaveis esperados:

- documentacao dos modulos base
- regras de heranca e override explicitadas
- checklist de alteracoes seguras no custeio
- testes de regressao nas areas de calculo e decomposicao

Indicadores de fecho:

- menor dependencia de conhecimento informal para editar modulos
- menos regressos em calculo por alteracoes locais
- maior previsibilidade no fluxo `item -> custeio`

## Fase 2. Robustez de calculo e decomposicao
Foco: garantir que a estrutura tecnica gerada a partir dos modulos se comporta de forma consistente.

Prioridades:

- rever formulas e variaveis globais e locais
- reforcar relacoes pai/filho entre componentes
- validar quantidades, medidas e regras herdadas
- melhorar rastreabilidade entre modulo de origem e linhas geradas

Entregaveis esperados:

- documentacao de variaveis suportadas
- testes para cenarios com formulas e herdanca
- melhor leitura do impacto de overrides locais

Indicadores de fecho:

- menor risco de erro em pecas e ferragens geradas
- maior confianca na reutilizacao de modulos equivalentes

## Fase 3. Coerencia comercial e historico reutilizavel
Foco: transformar o conhecimento acumulado em acelerador operativo.

Prioridades:

- preparar historico reutilizavel de modulos e items
- melhorar pesquisa e recuperacao de solucoes anteriores
- manter ligacao clara entre item atual e casos semelhantes
- reforcar consistencia do preco final

Entregaveis esperados:

- criterios de classificacao de modulos
- base minima de modulos documentados
- melhor reaproveitamento de items de orcamentos anteriores

Indicadores de fecho:

- reducao do tempo de criacao de orcamentos semelhantes
- menor duplicacao manual de estrutura tecnica

## Fase 4. Producao e integracoes operacionais
Foco: fechar melhor a ponte entre orcamentacao e producao.

Estado observado:

- `PHC` ja participa na consulta de encomendas e em validacoes de estado
- `CUT-RITE` ja entra no fluxo documental da obra
- `IMOS` ja alimenta parte da preparacao e programas

Prioridades:

- endurecer sincronizacao de estados `PHC -> Producao`
- formalizar regras de criacao de processo a partir do PHC
- estabilizar preparacao documental com `CUT-RITE` e `Caderno de Encargos`
- consolidar envio de programas CNC para obra e MPR

Entregaveis esperados:

- mapa de estados PHC reconhecidos pelo Martelo
- checklist operacional da preparacao da obra
- validacao de campos obrigatorios para integracoes

Indicadores de fecho:

- menos divergencias manuais entre PHC e Producao
- menor falha operacional em preparacao documental
- maior confianca no arranque da producao

## Fase 5. Base para assistencia por IA
Foco: preparar o sistema para apoio inteligente sem perder controlo humano.

Prioridades:

- estruturar historico de modulos e items
- melhorar qualidade dos dados reutilizaveis
- definir como a IA sugere modulos, nunca como decide sozinha
- ligar contexto tecnico, comercial e historico

Entregaveis esperados:

- catalogo de modulos com metadata util
- criterios de semelhanca entre pedidos, modulos e items antigos
- fluxo assistido para gerar rascunho inicial de orcamento

Indicadores de fecho:

- capacidade de sugerir ponto de partida com base em pedidos do cliente
- validacao humana mantida como etapa obrigatoria

## Riscos que exigem maior cuidado
As areas que devem evoluir com mais seguranca sao:

- `tab_custeio_items`
- logica de modulos reutilizaveis
- fronteira entre Dados Gerais, Dados Items e edicao local
- formulas, variaveis e relacoes pai/filho
- compatibilidade com historico de orcamentos

## Proximos passos recomendados
Ordem recomendada para continuar:

1. Documentar melhor os modulos reutilizaveis.
2. Formalizar regras de heranca e override.
3. Reforcar testes do custeio e da decomposicao.
4. Consolidar o fluxo `PHC -> Producao`.
5. Preparar base de historico para reutilizacao e IA.
