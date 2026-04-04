# Visao Funcional Martelo

## Objetivo
O Martelo e um software interno para orcamentacao e preparacao de producao de mobiliario por medida.

O objetivo principal do sistema e transformar um pedido do cliente em items orcamentaveis com calculo tecnico e comercial consistente, mantendo sempre supervisao humana.

## Tipos de entrada do pedido
O pedido pode chegar ao utilizador em varios formatos:

- descricao textual
- desenho manual
- imagem de referencia
- caso semelhante ja produzido anteriormente

O sistema deve ajudar o utilizador a partir de uma base reutilizavel, adaptar ao caso concreto e fechar o preco final com controlo.

## Filosofia funcional
O Martelo e orientado a modulos.

Um modulo representa uma estrutura reutilizavel de mobiliario que pode:

- adaptar medidas por variaveis
- decompor-se automaticamente em pecas
- decompor-se automaticamente em ferragens
- aplicar regras de materiais
- aplicar regras de producao
- calcular custo e preco

A criacao manual de todas as linhas desde zero deve ser a excecao. O comportamento preferencial do sistema e reutilizar estruturas equivalentes e depois ajustar.

## Fluxo funcional principal
O fluxo principal do negocio e o seguinte:

1. Criar orcamento.
2. Definir Dados Gerais do orcamento.
3. Inserir items.
4. Para cada item, escolher um modulo semelhante ou criar estrutura equivalente.
5. Aplicar Dados do Item quando o item exigir regras proprias.
6. Decompor automaticamente o item em pecas e ferragens.
7. Ajustar localmente linhas de custeio quando necessario.
8. Calcular custos e preco.
9. Gerar relatorios.
10. Preparar producao quando o orcamento for adjudicado.

## Estrutura funcional por camadas
O comportamento do sistema assenta em tres niveis de regras.

### 1. Dados Gerais
Definem regras comuns ao orcamento inteiro, por exemplo:

- materiais por tipo de peca
- ferragens padrao
- sistemas de correr
- acabamentos
- outras regras globais

### 2. Dados do Item
Definem regras especificas de cada item.

Podem:

- herdar dos Dados Gerais
- substituir parcialmente regras globais
- especializar um item sem afetar o resto do orcamento

### 3. Edicao Local no Custeio
Na tabela de custeio, cada linha pode ser alterada localmente.

Os ajustes locais permitem controlar:

- material
- ferragem
- medidas
- quantidades
- regras especificas daquela linha

Este terceiro nivel e essencial para manter flexibilidade sem destruir a logica modular.

## Dominio principal
Os conceitos centrais do Martelo incluem:

- Cliente
- Orcamento
- Versao
- Item
- Modulo
- Peca
- Ferragem
- Materiais
- Sistemas de correr
- Acabamentos
- Custeio
- Producao

## Tabelas base
As tabelas base mais relevantes alimentam o comportamento do sistema:

- Materiais
- Ferragens
- Sistemas de Correr
- Acabamentos

Estas tabelas servem de base para Dados Gerais, Dados Items e Custeio.

## Nucleo critico
A area mais sensivel do Martelo e a tabela `tab_custeio_items`.

Esta tabela concentra:

- definicao de pecas
- quantidades
- medidas
- formulas
- materiais
- ferragens
- orlas
- tempos de maquina
- mao de obra
- acabamentos
- custos por linha
- custo total por item

Qualquer alteracao nesta zona pode afetar o calculo, a coerencia tecnica e a confianca no orcamento.

## Logica funcional dos modulos
Os modulos sao a base reutilizavel do sistema.

Ao inserir um modulo, o comportamento esperado e:

- carregar a estrutura de pecas
- carregar a estrutura de ferragens
- adaptar medidas com base em variaveis
- recalcular custo e preco
- permitir afinacao local pelo utilizador

Exemplos tipicos:

- modulo com 1 porta e 5 prateleiras
- modulo com 2 portas e 5 prateleiras
- modulos equivalentes de roupeiro, cozinha, WC e outros contextos

## Variaveis, formulas e componentes
O sistema trabalha com variaveis globais e locais.

Exemplos:

- globais: `H`, `L`, `P`, `H1`, `L1`, `P1`
- locais por modulo: `HM`, `LM`, `PM`

As medidas podem ser guardadas como formulas em texto e convertidas em resultados calculados.

O sistema tambem suporta relacoes entre componentes:

- componente simples
- componente pai
- componente filho

Os componentes filhos podem herdar medidas, quantidades ou regras do componente pai.

## Relacao entre orcamentacao e producao
O Martelo nao termina no preco. Depois da adjudicacao, o sistema acompanha a passagem para producao.

Essa fase inclui:

- preparacao documental
- relatorios
- programas CNC
- controlo de estado de producao
- integracoes com software externo

Pelo estado atual do projeto, esta frente ja inclui trabalho relevante de integracao com `PHC`, `CUT-RITE` e `IMOS`.

## Principios de evolucao funcional
Qualquer evolucao do sistema deve respeitar estes principios:

- preservar a logica orientada a modulos
- manter os tres niveis de regras
- nao quebrar a decomposicao automatica em pecas e ferragens
- nao remover flexibilidade de edicao manual
- explicar sempre o impacto no fluxo do utilizador
- preservar compatibilidade com orcamentos anteriores sempre que possivel
- evoluir de forma incremental e segura

## Leitura pratica da arquitetura atual
A arquitetura funcional atual pode ser resumida como:

`Orcamento -> Item -> Modulo -> Decomposicao -> Custeio -> Relatorio -> Producao`

O ponto forte do Martelo e combinar reutilizacao, calculo e controlo humano.

O principal desafio da arquitetura e garantir que modulos, Dados Gerais, Dados Items e Custeio continuam coerentes entre si mesmo quando existem excecoes reais de fabrico.
