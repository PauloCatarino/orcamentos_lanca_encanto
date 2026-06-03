# Implementacao Atual

## Mapa Principal

Hoje a logica de `Mat_Default` esta repartida por tres zonas:

- UI da pagina de `Custeio Items`
- servicos de `custeio`
- configuracao `Definicoes de Pecas`

Qualquer alteracao segura deve partir deste mapa e nao de uma simplificacao teorica.

## UI: Delegate da Dropdown

Ficheiro principal:

- `Martelo_Orcamentos_V2/ui/pages/custeio_items.py`

Ponto central:

- `MatDefaultDelegate`

O metodo `_options_for_index()` ja faz filtro contextual, mas com muita logica embutida:

- bloqueia `DIVISAO INDEPENDENTE`
- trata linhas pai/filho de forma diferente
- usa `def_peca`, `familia`, `tipo`, `descricao` e `_child_source`
- aplica regras especiais para:
  - rodizios
  - acessorios de correr
  - grupos SPP
  - paines de correr
  - especiais de cozinhas
- para ferragens, usa `inferir_ferragem_info()`

O editor atual e um `QComboBox` simples:

- mostra texto plano
- abre popup automaticamente
- nao tem preview dinamica por tooltip

## UI: Aplicacao da Selecao

Ainda em `Martelo_Orcamentos_V2/ui/pages/custeio_items.py`, o metodo `_apply_mat_default_selection()`:

- ignora `DIVISAO INDEPENDENTE`
- tenta resolver o registo por familia/grupo
- grava `mat_default`
- reidrata a linha com `dados_material()`
- recalcula orlas e totais

Ou seja:

`Mat_Default` ja e um valor operacional do `Custeio`, nao apenas decorativo.

## Servicos: Origem das Opcoes

Ficheiro principal:

- `Martelo_Orcamentos_V2/app/services/custeio_items.py`

Funcoes mais importantes:

- `lista_mat_default()`
- `lista_mat_default_ferragens()`
- `lista_mat_default_ferragens_multi()`
- `lista_mat_default_sis_correr()`
- `_collect_group_options()`

Comportamento atual:

- quando existe `session + context`, as opcoes sao recolhidas das tabelas de `Dados Items`
- quando nao existem dados suficientes, ha fallback para `MENU_FIXED_GROUPS`
- ferragens usam filtros por `tipo`
- sistemas de correr usam filtros adicionais por `familia`, `grupo_sistema` e `tipo`

## Servicos: Lookup do Registo

No mesmo ficheiro ja existem helpers que podem apoiar futuras melhorias:

- `_buscar_material_por_menu()`
- `obter_material_por_grupo()`
- `obter_material_por_familia()`
- `dados_material()`
- `grupo_por_def_peca()`

Isto e relevante porque a preview por tooltip nao precisa de inventar outra fonte de dados. Deve reutilizar a mesma origem coerente com o `Custeio`.

## Definicoes de Pecas

Ficheiros relevantes:

- `Martelo_Orcamentos_V2/app/services/def_pecas.py`
- `Martelo_Orcamentos_V2/app/models/definicao_peca.py`
- `Martelo_Orcamentos_V2/ui/pages/settings.py`

Estado atual:

- a tabela guarda `tipo_peca_principal`, `subgrupo_peca`, `nome_da_peca` e campos `CP01..CP08`
- hoje o consumo principal desta tabela no `Custeio` e para preencher campos `CP**`
- ainda nao existe um contrato completo nesta tabela para filtrar `Mat_Default`

Isto significa:

- a tabela e candidata natural para governar o filtro
- mas ainda nao substitui a logica atual

## Extensao Recomendada

Se for preciso mexer nesta area, a ordem segura e:

1. criar um resolvedor central de opcoes por linha
2. deixar esse resolvedor consumir:
   - contexto da linha
   - regras futuras de `Definicoes de Pecas`
   - fallback para as funcoes atuais
3. so depois adaptar o delegate para usar esse resolvedor
4. por fim, acrescentar tooltip preview no editor

## Preview por Tooltip

O caminho de menor risco tecnico e:

- manter `QComboBox`
- atualizar tooltip no highlight da opcao
- ler do registo correspondente em `Dados Items`
- mostrar apenas:
  - `Descricao Material`
  - `Preco Liquido`

Evitar, numa primeira fase:

- delegates complexos com widgets ricos dentro da lista
- previews que alterem a selecao
- duplicacao de fontes de dados

## Riscos de Regressao

Os principais riscos desta zona sao:

- quebrar linhas pai/filho
- perder casos especiais de ferragens
- misturar materiais com ferragens por filtro demasiado generico
- desligar o fallback atual cedo demais
- tornar `Definicoes de Pecas` obrigatoria antes de ela cobrir os casos reais
