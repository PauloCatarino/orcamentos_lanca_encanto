# Visao Funcional

## Papel na arquitetura do Martelo

`Dados Gerais` e `Dados Items` sao a camada de regras que alimenta a tabela `Custeio Items`.

A sequencia funcional correta e:

`Dados Gerais -> Dados Items -> Dados Custeio`

Interpretacao:

- `Dados Gerais`: base geral do orcamento ativo
- `Dados Items`: especializacao por item do orcamento
- `Custeio Items`: aplicacao local, linha a linha, com possibilidade de edicao manual

Esta skill deve sempre manter esta hierarquia alinhada com `AGENTS.md`.

## Estrutura comum das paginas

Tanto `Dados Gerais` como `Dados Items` trabalham com 4 tabelas principais:

- `Materiais`
- `Ferragens`
- `Sistemas Correr`
- `Acabamentos`

Estas tabelas representam familias de regras e referencias que depois sao usadas no `Custeio Items`.

## Dados Gerais

`Dados Gerais` representa a base comum do orcamento ativo.

Responsabilidades:

- definir materiais base do orcamento
- definir ferragens base do orcamento
- definir sistema de correr base do orcamento
- definir acabamentos base do orcamento
- servir de origem para preenchimento dos `Dados Items`

Em `Materiais`, as linhas funcionam como grupos estruturais do dominio, por exemplo:

- `Costas`
- `Laterais`
- `Portas Abrir 1`
- `Prateleiras`
- `Remates Verticais`
- `Material_Livre_n`

Cada linha pode conter, entre outros, dados como:

- `descricao`
- `ref_le`
- `descricao_material`
- `preco_tab`
- `preco_liq`
- `margem`
- `desconto`
- `und`
- `desp`
- `orl_0_4`
- `orl_1_0`
- `tipo`
- `familia`
- `comp_mp`
- `larg_mp`
- `esp_mp`
- `id_mp`

## Dados Items

`Dados Items` usa a mesma familia de 4 tabelas, mas o seu papel e diferente.

Responsabilidades:

- especializar o item que esta a ser orcamentado
- herdar ou partir dos `Dados Gerais`
- permitir ajustes proprios do item
- fornecer uma base mais especifica para o `Custeio Items`

Regra funcional:

- `Dados Gerais` define a base comum
- `Dados Items` afina essa base para o item corrente
- `Custeio Items` continua a poder ser alterado localmente

## Referencias live / livres

As tabelas suportam linhas livres para referencias que nao existam de forma completa na base de `Materias-Primas`.

Na pratica:

- ha grupos livres como `Material_Livre_1`, `Material_Livre_2`, etc.
- o utilizador pode preencher manualmente descricao, referencia e outros campos
- essas referencias ficam disponiveis dentro do contexto do orcamento/item em que foram guardadas

Isto nao transforma a linha numa referencia global de cadastro; e uma referencia operacional dentro do contexto do trabalho atual.

## Modelos

Ambas as paginas suportam gravacao e importacao de modelos, mas com scopes diferentes.

### Modelos em Dados Gerais

Objetivo:

- reutilizar configuracoes de tabela para novos orcamentos
- evitar preenchimento repetitivo das 4 tabelas

Operacoes principais:

- `Guardar Modelo`
- `Importar Modelo`
- `Importar Multi Modelos`
- `Guardar Dados Gerais`

Distincao funcional:

- `Guardar Modelo`: cria uma base reutilizavel para importacao futura
- `Guardar Dados Gerais`: grava os dados nas tabelas associadas ao orcamento ativo

Shared/global vs utilizador:

- um modelo pode ser apenas do utilizador atual
- ou pode ficar disponivel como `Global` para todos os utilizadores

### Modelos em Dados Items

Objetivo:

- reutilizar dados de item dentro do orcamento ativo
- facilitar reaproveitamento entre items semelhantes

Operacoes principais:

- `Guardar Modelo`
- `Importar Dados Items`
- `Importar Multi Dados Items`
- `Guardar Dados Items`

Distincao funcional:

- `Guardar Dados Items`: grava as 4 tabelas no item corrente
- `Guardar Modelo`: cria um modelo reutilizavel para futura importacao

Origem de importacao:

- modelos locais de `Dados Items`
- modelos vindos de `Dados Gerais`

Isto e apresentado ao utilizador com dois separadores na importacao simples e com origem por menu na importacao multipla.

## Verificacao de precos e reconcilicao com Materias-Primas

Ao importar modelos, o comportamento funcional relevante nao e apenas "copiar linhas".

Tambem existe reconcilicao com `Materias-Primas`:

- a UI tenta completar campos em falta a partir da referencia `ref_le`
- quando ha diferencas entre valores do modelo e valores atuais de `Materias-Primas`, o utilizador pode decidir que origem aplicar

Este comportamento e importante porque evita assumir que o modelo antigo continua coerente com a base atual de materias-primas.

## Relacao com Custeio Items

Estas paginas nao sao um fim em si mesmas; elas alimentam o `Custeio Items`.

Pontos funcionais relevantes:

- o `Custeio` pode copiar `Dados Gerais` para `Dados Items` com `Preencher Dados Items`
- depois o `Custeio` usa as tabelas de `Dados Items` como referencia para materiais, ferragens, sistemas e acabamentos
- o utilizador continua a poder editar o custeio localmente

## Guardrails para futuras alteracoes

- nao colapsar `Dados Gerais` e `Dados Items` numa unica camada
- nao remover a possibilidade de importacao simples e multipla sem substituir por fluxo equivalente
- nao misturar "gravar modelo" com "gravar dados do contexto ativo"
- nao presumir que referencias livres pertencem ao cadastro global
- nao quebrar a relacao funcional com `Custeio Items`
