# Modulos Reutilizaveis Martelo

## Objetivo
Este documento define como os modulos reutilizaveis devem ser entendidos, documentados e evoluidos no Martelo.

O objetivo nao e apenas listar modulos. E criar uma base funcional que permita:

- reutilizar estrutura tecnica com seguranca
- reduzir criacao manual de pecas e ferragens
- manter coerencia entre Dados Gerais, Dados Items e Custeio
- preparar historico reutilizavel para futuras sugestoes assistidas

## O que e um modulo
No contexto do Martelo, um modulo e uma estrutura reutilizavel de mobiliario que pode ser inserida num item do orcamento e depois adaptada ao caso concreto.

Um modulo deve permitir:

- ajustar medidas por variaveis
- decompor-se automaticamente em pecas
- decompor-se automaticamente em ferragens
- aplicar regras de materiais
- aplicar regras de producao
- calcular custo e preco
- aceitar ajustes locais quando necessario

## Papel do modulo no fluxo do sistema
O modulo entra no centro do fluxo funcional:

`Pedido do cliente -> Orcamento -> Item -> Modulo -> Decomposicao -> Custeio -> Producao`

A regra geral deve ser:

- primeiro reutilizar modulo equivalente
- depois adaptar o item ao caso concreto
- so em ultimo recurso construir manualmente a estrutura desde zero

## Contrato funcional minimo de um modulo
Para ser considerado um modulo reutilizavel valido, uma estrutura deve deixar claro:

- qual o problema funcional que resolve
- que variaveis aceita
- que pecas gera
- que ferragens gera
- que regras espera receber de Dados Gerais
- que regras podem ser definidas em Dados Items
- que ajustes podem ser feitos no Custeio sem destruir a estrutura

Se um modulo nao tiver este contrato minimamente explicito, a reutilizacao torna-se dependente de memoria informal.

## Relacao com os tres niveis de regras
Os modulos nao vivem isolados. Eles dependem da arquitetura de regras do Martelo.

### Dados Gerais
Fornecem defaults globais que o modulo pode consumir:

- materiais base
- ferragens padrao
- sistemas de correr
- acabamentos
- outras configuracoes comuns ao orcamento

### Dados Items
Permitem especializar o comportamento do modulo no contexto de um item especifico:

- substituir parcialmente materiais
- trocar ferragens
- ajustar sistemas
- especializar acabamentos

### Edicao Local no Custeio
Permite ajustar o resultado final linha a linha:

- material real aplicado
- ferragem real aplicada
- quantidades
- medidas
- excecoes tecnicas ou comerciais

O principio importante e este:

- o modulo define estrutura
- os Dados Gerais e Dados Items definem regras
- o Custeio permite afinacao final

## Tipos de modulos a documentar
Para facilitar organizacao futura, os modulos devem ser classificados por familia funcional.

Exemplos:

- roupeiros
- cozinhas
- WC
- armarios tecnicos
- modulos com portas de abrir
- modulos com portas de correr
- modulos com gavetas
- modulos com nichos ou prateleiras

Tambem faz sentido classificar por padrao construtivo:

- modulo simples
- modulo composto
- modulo com componente pai e filhos
- modulo com formulas dependentes
- modulo com ferragem dominante

## Template recomendado para ficha de modulo
Cada modulo reutilizavel deve passar a ter uma ficha minima com esta estrutura.

### 1. Identificacao

- Nome do modulo
- Codigo interno ou referencia
- Familia
- Estado: ativo, em revisao ou legado

### 2. Objetivo funcional

- Que tipo de caso resolve
- Em que contexto deve ser usado
- Em que contexto nao deve ser usado

### 3. Inputs do modulo

- variaveis principais: `H`, `L`, `P`, `HM`, `LM`, `PM`
- outras variaveis necessarias
- campos obrigatorios do item
- dependencias de Dados Gerais

### 4. Estrutura gerada

- lista de pecas principais
- lista de ferragens principais
- relacoes pai/filho, quando existirem
- regras de quantidade
- regras de medidas derivadas

### 5. Regras de heranca e override

- que regras herda de Dados Gerais
- que regras podem ser redefinidas em Dados Items
- que campos podem ser alterados localmente no Custeio
- que alteracoes locais sao perigosas

### 6. Impacto no preco

- fatores principais de custo
- fatores principais de preco
- pontos que costumam exigir revisao humana

### 7. Validacoes

- verificacoes tecnicas minimas
- casos de erro conhecidos
- sinais de que o modulo foi usado fora do contexto certo

### 8. Exemplo real

- exemplo de medidas
- resultado esperado em pecas
- resultado esperado em ferragens
- observacoes de custeio

## Template curto para uso rapido
Quando for preciso documentar muitos modulos rapidamente, pode usar-se esta versao resumida:

```md
## Nome do Modulo
- Familia:
- Objetivo:
- Inputs:
- Pecas geradas:
- Ferragens geradas:
- Herda de Dados Gerais:
- Overrides em Dados Items:
- Ajustes locais frequentes:
- Riscos:
- Exemplo de uso:
```

## Exemplos base a documentar primeiro
Os primeiros modulos a documentar devem ser os mais reutilizados e mais explicativos para o negocio.

### Exemplo 1. Modulo com 1 porta e 5 prateleiras
Uso esperado:

- roupeiro simples
- armario vertical
- caso base para testar relacao entre corpo, porta e prateleiras

Pontos a documentar:

- regras de medidas da porta
- quantidade e espacamento de prateleiras
- ferragens da porta
- materiais padrao por tipo de peca
- impacto de troca de material no custo

### Exemplo 2. Modulo com 2 portas e 5 prateleiras
Uso esperado:

- variacao do caso anterior com frente dupla

Pontos a documentar:

- divisao de vao
- largura util de cada porta
- ferragens adicionais
- impacto no preco versus modulo de 1 porta

### Exemplo 3. Modulo com sistema de correr
Uso esperado:

- casos em que o sistema de correr e determinante para ferragens e comportamento construtivo

Pontos a documentar:

- dependencia forte de Dados Gerais ou Dados Items
- regras do sistema de correr
- componentes associados
- riscos se o sistema estiver mal definido

## Regras de documentacao segura
Ao documentar um modulo, convem distinguir sempre:

- estrutura base do modulo
- regras herdadas
- excecoes conhecidas
- pontos de override manual

Nao convem misturar no mesmo bloco:

- comportamento geral do modulo
- afinacoes de um caso isolado

Essa mistura torna a documentacao pouco reutilizavel.

## Checklist para alterar um modulo existente
Sempre que um modulo for alterado, deve ser revista pelo menos esta checklist:

1. A estrutura base continua valida para os casos onde o modulo ja era usado.
2. A decomposicao em pecas nao perdeu coerencia.
3. A decomposicao em ferragens continua correta.
4. As formulas e variaveis continuam compativeis.
5. Os Dados Gerais continuam a alimentar o modulo como esperado.
6. Os Dados Items continuam a conseguir especializar o modulo.
7. A edicao local no Custeio continua possivel.
8. O impacto no preco continua compreensivel.
9. A alteracao nao quebra reutilizacao de casos antigos.

## Riscos principais nos modulos reutilizaveis
Os riscos mais frequentes nesta area sao:

- modulos sem contrato funcional explicito
- formulas pouco transparentes
- dependencia excessiva de ajustes manuais
- mistura entre regra estrutural e excecao local
- reutilizacao de modulos fora da familia correta
- alteracoes que parecem pequenas mas mudam o resultado do custeio

## Proximo passo recomendado
A partir deste documento, o passo mais util e criar um catalogo progressivo de modulos reais.

Ordem sugerida:

1. Identificar os 10 modulos mais usados.
2. Preencher uma ficha resumida para cada um.
3. Escolher 3 modulos de referencia e documenta-los em detalhe.
4. Ligar essa documentacao aos testes e aos exemplos de orcamento.

Catalogo inicial disponivel em `docs/catalogo_modulos_referencia.md`.
