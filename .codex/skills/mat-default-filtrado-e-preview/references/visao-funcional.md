# Visao Funcional

## Visao Geral

`Mat_Default` e a ponte entre a linha atual do `Custeio` e o grupo de origem que fornece material, ferragem, sistema, descricao e preco base.

No fluxo normal do Martelo:

- `Dados Gerais` definem defaults do orcamento
- `Dados Items` especializam esses defaults para o item atual
- `Custeio Items` aplica e afina linha a linha

`Mat_Default` vive no terceiro nivel, mas a origem das opcoes vem sobretudo do segundo.

## Papel de Mat_Default

`Mat_Default` deve responder a esta pergunta:

`de que grupo coerente devem vir os dados desta linha?`

Por isso, o valor selecionado nao deve ser tratado como uma simples etiqueta. Ele influencia:

- lookup do registo em `Dados Items`
- reidratacao da linha no `Custeio`
- descricao no orcamento
- precos e descontos base
- aplicacao de familia e tipo
- comportamento de linhas especiais de ferragens e sistemas de correr

## Relacao Entre a Linha e as Opcoes Disponiveis

As opcoes disponiveis nao devem ser globais nem indiferenciadas.

Elas devem depender do contexto da linha atual, incluindo:

- `def_peca`
- `familia`
- `tipo`
- `row_type` pai/filho
- `child_source`
- regras especiais de ferragens
- regras especiais de sistemas de correr

Exemplos desejados:

- uma `COSTA CHAPAR` deve apontar para grupos coerentes de materiais de peca
- um `TETO` nao deve misturar dobradicas, leds ou puxadores
- uma `DOBRADICA RETA` deve filtrar para grupos coerentes com dobradicas
- um `PUXADOR` deve filtrar para grupos coerentes com puxadores
- um `SUPORTE PRATELEIRA` deve filtrar para grupos coerentes com esse tipo

## Origem das Opcoes

As opcoes da dropdown devem preferir os grupos ja presentes no item atual, em especial:

- `Dados Items > Materiais`
- `Dados Items > Ferragens`
- `Dados Items > Sistemas Correr`

Quando o item nao tiver informacao suficiente, e aceitavel usar fallback para grupos fixos do sistema, desde que o comportamento ja existente seja preservado.

## Papel da Tabela Definicoes de Pecas

`Definicoes de Pecas` ja e uma tabela de configuracao relevante para `Custeio`, mas hoje o seu papel principal esta ligado aos campos `CP**`.

Esta skill assume que essa tabela deve ser estudada como futuro ponto preferencial para controlar:

- que grupos sao permitidos por peca ou ferragem
- que familias devem ser priorizadas
- que casos especiais merecem override explicito

Mas essa evolucao deve ser incremental. Nao se deve desligar a logica atual sem uma fase de fallback seguro.

## Problemas Atuais

Os problemas mais provaveis nesta zona sao:

- logica espalhada entre UI, servicos e configuracao
- uso forte de regras hardcoded no delegate
- dropdown sem apoio visual suficiente durante a navegacao
- risco de misturar materiais com ferragens sem criterio
- risco de regressao em linhas compostas pai/filho

## Estrategia Recomendada

Trabalhar por fases:

1. mapear a logica atual da dropdown
2. isolar o resolvedor das opcoes permitidas por linha
3. introduzir regras de `Definicoes de Pecas` como fonte preferida
4. manter fallback para a logica atual
5. so depois simplificar hardcodes que fiquem cobertos por regras reais

## Preview por Tooltip

A primeira melhoria de usabilidade recomendada e uma tooltip simples durante a navegacao da dropdown.

Mostrar apenas:

- `Descricao Material`
- `Preco Liquido`

Origem desses dados:

- registo correspondente em `Dados Items`

Regras:

- a tooltip deve atualizar no highlight da opcao
- nao deve alterar a linha
- nao deve confirmar a selecao
- deve ser tratada como apoio visual de baixo risco tecnico

## Regras de Seguranca

- preservar compatibilidade com os utilizadores atuais
- nao quebrar componentes compostos
- nao alterar implicitamente valores ja gravados
- nao confiar apenas em `Definicoes de Pecas` antes de existir cobertura funcional suficiente
- manter sempre um fallback explicito para o comportamento atual
