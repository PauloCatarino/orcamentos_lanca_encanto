# Implementacao Atual

## Ficheiros principais

Servicos:

- `Martelo_Orcamentos_V2/app/services/dados_gerais.py`
- `Martelo_Orcamentos_V2/app/services/dados_items.py`

Paginas e dialogos:

- `Martelo_Orcamentos_V2/ui/pages/dados_gerais.py`
- `Martelo_Orcamentos_V2/ui/pages/dados_items.py`
- `Martelo_Orcamentos_V2/ui/pages/custeio_items.py`

Modelos ORM:

- `Martelo_Orcamentos_V2/app/models/dados_gerais.py`

Documentacao funcional do projeto:

- `AGENTS.md`
- `docs/visao_funcional_martelo.md`

## Estrutura de dados persistida

Tabelas de `Dados Gerais`:

- `dados_gerais_materiais`
- `dados_gerais_ferragens`
- `dados_gerais_sistemas_correr`
- `dados_gerais_acabamentos`
- `dados_gerais_modelos`
- `dados_gerais_modelo_items`

Tabelas de `Dados Items`:

- `dados_items_materiais`
- `dados_items_ferragens`
- `dados_items_sistemas_correr`
- `dados_items_acabamentos`
- `dados_items_modelos`
- `dados_items_modelo_items`

Scopes atuais:

- `Dados Gerais`: contexto por `cliente_id + ano + num_orcamento + versao`
- `Dados Items`: contexto por `orcamento_id + item_id`

## 4 menus e linhas fixas

Os dois servicos partilham a mesma estrutura base:

- `MENU_MATERIAIS`
- `MENU_FERRAGENS`
- `MENU_SIS_CORRER`
- `MENU_ACABAMENTOS`

O contrato real usa:

- `MENU_FIXED_GROUPS`
- `MENU_PRIMARY_FIELD`
- `MENU_DEFAULT_FAMILIA`

Isto significa que as tabelas nao sao listas arbitrarias. Existe uma ordem base e grupos fixos esperados por menu.

Ao carregar dados, ambos os servicos usam `_ensure_menu_rows(...)` para garantir a estrutura minima, mesmo quando nao existem linhas persistidas ou quando faltam grupos.

## Contrato real dos modelos

Este ponto e importante.

Hoje, os modelos de `Dados Gerais` e `Dados Items` nao guardam a linha completa tal como aparece na grelha.

O snapshot guardado por modelo e compacto:

- campo primario do menu (`grupo_material`, `grupo_ferragem`, `grupo_sistema`, `grupo_acabamento`)
- `ref_le`
- `descricao_material`
- `preco_tab`
- `preco_liq`
- `margem`
- `desconto`
- `und`

Isto vem de:

- `MODEL_COMMON_FIELDS` em `app/services/dados_gerais.py`
- `_prepare_model_line(...)` em `app/services/dados_gerais.py`
- `_filter_model_row(...)` em `app/services/dados_items.py`

Consequencia:

- campos como `descricao`, `desp`, `orl_0_4`, `orl_1_0`, `tipo`, `familia`, `comp_mp`, `larg_mp`, `esp_mp`, `id_mp` nao fazem parte do snapshot base do modelo
- esses campos sao reidratados ou completados no momento da importacao, sobretudo via merge com `Materias-Primas`

Nao documentar isto como se o modelo fosse um clone integral da tabela.

## Dados Gerais: persistencia e modelos

### Guardar dados do orcamento

`guardar_dados_gerais(...)` em `app/services/dados_gerais.py`:

- substitui as linhas existentes por menu para o contexto do orcamento
- insere de novo as linhas recebidas no payload
- grava por `cliente_id`, `ano`, `num_orcamento`, `versao`

### Modelos reutilizaveis

`guardar_modelo(...)` em `app/services/dados_gerais.py`:

- grava um modelo por `tipo_menu`
- suporta `replace_id`
- suporta `is_global`
- suporta `add_timestamp`

`listar_modelos(...)`:

- devolve modelos do utilizador atual
- inclui tambem modelos marcados por `GLOBAL_PREFIX = "__GLOBAL__|"`

`carregar_modelo(...)`:

- devolve `{"modelo": ..., "linhas": [...]}` para um unico menu

UI relevante em `ui/pages/dados_gerais.py`:

- `GuardarModeloDialog`
- `ImportarModeloDialog`
- `ImportarMultiModelosDialog`

Detalhes atuais da UI:

- `Guardar Modelo` permite marcar `Disponibilizar como Global`
- tambem permite adicionar data/hora ao nome
- importacao simples trabalha sobre a tabela ativa
- importacao multipla permite escolher um modelo por menu e definir `Substituir`

## Dados Items: persistencia e modelos

### Preenchimento a partir de Dados Gerais

`preencher_com_dados_gerais(...)` em `app/services/dados_items.py`:

- copia as 4 tabelas de `Dados Gerais` para o item corrente
- substitui os dados atuais do item pelas linhas equivalentes

`dados_items_em_sincronia_com_gerais(...)`:

- compara os 4 menus do item com a base de `Dados Gerais`

### Guardar dados do item

`guardar_dados_gerais(...)` em `app/services/dados_items.py`:

- apaga linhas existentes por `item_id`
- reinsere as linhas recebidas
- grava contexto por `orcamento_id`, `item_id`, `cliente_id`, `ano`, `num_orcamento`, `versao`

### Modelos locais de item

`guardar_modelo(...)` em `app/services/dados_items.py`:

- grava um modelo ligado ao `orcamento_id`
- normalmente ligado tambem ao `item_id`
- guarda um payload por menu dentro de `dados_items_modelo_items`

`listar_modelos(...)`:

- filtra por `orcamento_id`
- quando recebe `item_id`, permite modelos do item e modelos com `item_id is null`
- quando recebe `user_id`, tambem aceita `user_id is null` e nomes com `GLOBAL_PREFIX`

Importante:

- o servico suporta `is_global`
- mas a UI principal de `Dados Items` grava de forma local ao item/orcamento, atraves de um `QInputDialog`
- por isso, na documentacao convem distinguir capacidade do servico de fluxo principal exposto ao utilizador

UI relevante em `ui/pages/dados_items.py`:

- `ImportarDadosItemsDialog`
- `ImportarMultiDadosItemsDialog`
- `MateriaPrimaConflictDialog`

Fluxo de importacao simples:

- separador `Dados Items` para modelos locais
- separador `Dados Gerais` para modelos vindos da base geral

Fluxo de importacao multipla:

- por menu, o utilizador escolhe origem `Local` ou `Global`
- por menu, o utilizador escolhe se quer `Substituir`

## Merge com Materias-Primas

Tanto `Dados Gerais` como `Dados Items` usam uma etapa de merge com `Materias-Primas` no momento da importacao.

Implementacao:

- `_merge_with_materias_primas(...)` em `ui/pages/dados_gerais.py`
- `_merge_with_materias_primas(...)` em `ui/pages/dados_items.py`

Comportamento atual:

- procura `Materias-Primas` por `ref_le`
- preenche campos em falta como `desp`, `orl_0_4`, `orl_1_0`, `comp_mp`, `larg_mp`, `esp_mp`, `id_mp`
- compara campos principais do modelo com os da materia-prima
- quando ha diferencas, abre dialogo para o utilizador decidir entre `Modelo` e `Materia-Prima`

Isto e parte do comportamento funcional importante. Nao tratar como mero detalhe cosmetico.

## Diferencas atuais entre importacao de Dados Gerais e Dados Items

### Dados Gerais

`_apply_imported_rows(...)` em `ui/pages/dados_gerais.py`:

- usa o campo primario do menu como chave de merge
- se `replace=True`, atualiza linhas existentes por chave
- se `replace=False`, acrescenta so as que nao encontrarem chave

### Dados Items

`_apply_imported_rows(...)` em `ui/pages/dados_items.py`:

- se `replace=True`, alinha primeiro pela ordem fixa das linhas da tabela
- preserva alguns valores existentes quando o modelo trouxer vazio
- se `replace=False`, delega para a logica base depois de fazer merge com `Materias-Primas`

Esta diferenca e real e pode ter impacto funcional. Qualquer refactor tem de a avaliar explicitamente.

## Ponte com Custeio Items

Em `ui/pages/custeio_items.py` existe o botao:

- `Preencher Dados Items`

Comportamento atual:

- copia `Dados Gerais` para as 4 tabelas de `Dados Items` do item corrente
- usa os servicos de `dados_items`
- consulta tambem se `Dados Items` esta em sincronia com `Dados Gerais`

Isto significa que alteracoes em `Dados Gerais` e `Dados Items` podem ter impacto direto no fluxo de trabalho do `Custeio`.

## Ambiguidades ou pontos a validar antes de grandes alteracoes

- O prompt funcional do projeto fala como se o modelo representasse a tabela ja preenchida por completo, mas o contrato real do codigo hoje e compacto.
- O servico de `Dados Items` suporta prefixo global, mas a UI principal parece operar sobretudo como modelo local do orcamento/item.
- `Dados Gerais` e `Dados Items` partilham muita infraestrutura, mas a semantica de importacao `replace` nao e exatamente igual.

Quando fores alterar esta area, explicita sempre qual destes tres niveis estas a mudar:

- contrato funcional esperado
- implementacao atual
- comportamento UI efetivamente exposto ao utilizador
