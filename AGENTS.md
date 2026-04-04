# AGENTS.md - Martelo_Orcamentos_V2

## Visão geral do projeto
O Martelo_Orcamentos_V2 é um software interno para orçamentação e preparação de produção de mobiliário por medida.

O projeto começou com foco em orçamentos, mas evoluiu para incluir:
- gestão de items do orçamento
- dados gerais e dados específicos por item
- decomposição automática em peças e ferragens
- custeio detalhado
- preparação para produção
- relatórios
- futuras integrações com software externo
- futura assistência por IA com base em módulos e histórico de orçamentos

## Objetivo principal
Transformar pedidos do cliente em items orçamentáveis com cálculo técnico e comercial consistente.

O pedido do cliente pode chegar em vários formatos:
- descrição textual
- desenho manual
- imagem de referência
- modelo semelhante já produzido anteriormente

O objetivo do Martelo é permitir ao utilizador partir de módulos equivalentes, adaptá-los ao caso concreto e calcular o preço com supervisão humana.

## Filosofia principal do software
O Martelo é orientado a módulos.

Um módulo é uma estrutura reutilizável de mobiliário que, ao ser inserida no orçamento, pode:
- adaptar medidas por variáveis
- decompor-se automaticamente em peças
- decompor-se automaticamente em ferragens
- aplicar regras de materiais
- aplicar regras de produção
- calcular custo e preço

A reutilização de módulos é preferível à criação manual de todas as peças desde o zero.

## Fluxo principal do negócio
1. Criar orçamento
2. Definir dados gerais do orçamento
3. Inserir items no orçamento
4. Para cada item, usar módulo semelhante ou criar estrutura equivalente
5. Aplicar dados específicos do item, se necessário
6. Decompor o item em peças e ferragens
7. Editar localmente linhas de custeio quando necessário
8. Calcular custos e preço
9. Gerar relatórios
10. Preparar produção quando o orçamento for adjudicado

## Três níveis de regras
O sistema trabalha com três níveis de definição:

### 1. Dados Gerais
Regras comuns a todo o orçamento:
- materiais por tipo de peça
- ferragens padrão
- sistemas de correr
- acabamentos
- outras regras globais

### 2. Dados do Item
Regras específicas de cada item do orçamento:
- podem herdar dos Dados Gerais
- ou podem substituir parcialmente as regras globais

### 3. Edição Local no Custeio
Na tabela de custeio, cada linha pode ser editada localmente:
- material
- ferragem
- medidas
- quantidades
- regras específicas da linha

## Menus principais do programa
- Orçamentos
- Clientes
- Dados Gerais
- Dados Items
- Custeio dos Items
- Relatórios
- Configurações

## Núcleo crítico do sistema
A tabela mais importante do programa é a `tab_custeio_items`.

Esta tabela concentra:
- definição de peças
- quantidades
- medidas
- fórmulas
- materiais
- ferragens
- orlas
- tempos de máquina
- mão de obra
- acabamentos
- custos por linha
- custo total por item

Qualquer alteração nesta área deve ser feita com muito cuidado.

## Estrutura do domínio
O sistema trabalha com conceitos como:
- Cliente
- Orçamento
- Versão
- Item
- Módulo
- Peça
- Ferragem
- Produção
- Materiais
- Sistemas de correr
- Acabamentos
- Custeio

## Tabelas base principais
As tabelas base mais importantes incluem:
- Materiais
- Ferragens
- Sistemas de Correr
- Acabamentos

Estas tabelas alimentam Dados Gerais, Dados Items e Custeio.

## Lógica de módulos
Os módulos são base reutilizável do sistema.

Ao inserir um módulo:
- são carregadas as peças que o compõem
- são carregadas as ferragens associadas
- as medidas podem ser ajustadas por variáveis
- o preço é recalculado automaticamente
- o utilizador pode editar o resultado

Exemplos:
- módulo com 1 porta e 5 prateleiras
- módulo com 2 portas e 5 prateleiras
- outros módulos equivalentes de roupeiro, cozinha, WC, etc.

## Variáveis e fórmulas
O programa usa variáveis globais e locais para medidas:
- globais: H, L, P, H1, L1, P1...
- locais por módulo: HM, LM, PM

As medidas podem ser guardadas como fórmulas em texto e convertidas para resultados calculados.

## Relações entre componentes
O sistema pode trabalhar com:
- componente simples
- componente pai
- componente filho

Os componentes filhos podem herdar regras, quantidades ou medidas do componente pai.

## Futuro com IA
Uma direção estratégica do projeto é usar IA assistida para ajudar na criação do orçamento a partir de desenhos do cliente.

Cenário esperado:
- o cliente envia desenho manual, croqui ou imagem
- o sistema analisa o pedido
- identifica módulos semelhantes já existentes
- identifica items semelhantes em orçamentos anteriores
- sugere uma estrutura inicial de orçamento
- o utilizador valida e ajusta
- o sistema calcula o preço final

A IA deve funcionar como apoio à decisão, nunca como substituição total da validação humana.

## Regras para o Codex
Ao propor alterações:
- respeitar sempre a lógica orientada a módulos
- preservar os três níveis de regras: Dados Gerais, Dados do Item e Edição Local
- não quebrar decomposição automática em peças e ferragens
- não remover flexibilidade de edição manual
- explicar o impacto de qualquer alteração no fluxo do utilizador
- preservar compatibilidade com orçamentos anteriores sempre que possível
- priorizar evolução incremental e segura

## Prioridades atuais
1. Consolidar a lógica dos módulos reutilizáveis
2. Melhorar consistência entre Dados Gerais, Dados Items e Custeio
3. Garantir cálculos corretos por peça, ferragem e produção
4. Reforçar estabilidade da tabela `tab_custeio_items`
5. Preparar histórico reutilizável de módulos e items
6. Preparar base futura para sugestões assistidas por IA
7. Avaliar futuras integrações com CUT-RITE, IMOS e PHC

