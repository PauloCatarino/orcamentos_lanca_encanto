# Catalogo de Modulos de Referencia

## Objetivo
Este catalogo reune tres modulos de referencia para documentacao, alinhamento funcional e testes.

O objetivo destes casos nao e fechar todos os detalhes construtivos do sistema. E criar uma base comum para:

- discutir comportamento esperado
- validar coerencia entre modulo, item e custeio
- orientar testes funcionais
- servir de semente para um catalogo maior

## Como ler este catalogo
Cada modulo abaixo deve ser lido como caso de referencia funcional.

Isto significa:

- define o uso esperado
- define a estrutura minima esperada
- define os pontos onde Dados Gerais, Dados Items e Custeio interagem
- define validacoes minimas para testes

Os detalhes exatos de formulas, materiais e ferragens podem variar por contexto real, mas a logica funcional nao deve ser perdida.

No estado atual do projeto, estes 3 casos tambem estao ligados ao runtime como modulos globais de referencia, criados no arranque da aplicacao quando ainda nao existirem na base de dados.

## Caso 1. Modulo com 1 porta e 5 prateleiras

### Identificacao

- Nome: Modulo Base 1 Porta 5 Prateleiras
- Familia: Roupeiro / Armario vertical
- Tipo: Modulo simples com frente de porta e interior de prateleiras
- Estado documental: referencia inicial

### Objetivo funcional
Representar um corpo vertical simples com uma porta frontal e cinco prateleiras interiores.

Este modulo serve como caso base para validar:

- decomposicao estrutural simples
- ferragens de porta
- repeticao de elementos interiores
- impacto de medidas no custo

### Contexto de uso
Usar quando o item corresponde a um armario vertical simples com uma unica frente de acesso.

Nao usar quando:

- existirem duas frentes independentes
- existir sistema de correr
- a estrutura interior depender de divisao central

### Inputs principais

- `H`: altura total
- `L`: largura total
- `P`: profundidade total
- espessura de material do corpo
- tipo de material principal
- acabamento principal
- regra de ferragem de porta

### Estrutura minima esperada
Pecas principais:

- 2 laterais
- 1 topo
- 1 base
- 1 costas, quando aplicavel
- 5 prateleiras
- 1 porta

Ferragens principais:

- dobradicas da porta
- puxador ou sistema equivalente
- suportes de prateleira, quando aplicavel
- fixacoes base do modulo

### Regras funcionais esperadas

- as prateleiras devem ser tratadas como repeticao consistente da mesma tipologia
- a porta deve depender das medidas uteis do vao frontal
- a quantidade de ferragens da porta deve acompanhar dimensao e regra definida
- o preco deve reagir a alteracoes de material, ferragem e dimensoes principais

### Relacao com os tres niveis de regras

Dados Gerais:

- material padrao do corpo
- ferragem padrao da porta
- acabamento padrao

Dados Items:

- troca de material da porta
- troca da ferragem
- ajuste de acabamento

Edicao Local no Custeio:

- afinacao de quantidade de ferragens
- ajuste fino de medidas
- substituicao pontal de uma linha

### Pontos sensiveis

- medidas uteis da porta
- distribuicao das prateleiras
- consistencia entre quantidade de prateleiras e ferragens associadas
- overrides locais que quebram repeticao estrutural

### Validacoes minimas para testes

1. Inserir o modulo gera 1 porta e 5 prateleiras.
2. Alterar `H`, `L` ou `P` afeta pecas relevantes.
3. Trocar o material em Dados Items nao destrui a estrutura.
4. Ajustar uma linha de custeio localmente nao elimina as restantes pecas.
5. O preco total muda quando mudam material ou ferragens.

### Cenario de teste simples

- Medidas exemplo: `H=2400`, `L=600`, `P=550`
- Esperado: corpo simples, 1 porta, 5 prateleiras, ferragens coerentes com uma unica frente

## Caso 2. Modulo com 2 portas e 5 prateleiras

### Identificacao

- Nome: Modulo Base 2 Portas 5 Prateleiras
- Familia: Roupeiro / Armario vertical
- Tipo: Modulo simples com frente dupla
- Estado documental: referencia inicial

### Objetivo funcional
Representar um corpo vertical com duas portas frontais e cinco prateleiras interiores.

Este modulo serve para validar:

- variacao de frente sobre o mesmo corpo base
- divisao funcional do vao frontal
- aumento de ferragens face ao caso de 1 porta
- impacto comercial da frente dupla

### Contexto de uso
Usar quando o modulo exige duas portas de abrir na frente do mesmo corpo.

Nao usar quando:

- a largura e tao reduzida que tecnicamente uma unica porta seja mais correta
- existir sistema de correr
- houver compartimentos com comportamento interno diferente entre esquerda e direita

### Inputs principais

- `H`: altura total
- `L`: largura total
- `P`: profundidade total
- espessura de material
- regra de divisao da frente
- ferragens por porta

### Estrutura minima esperada
Pecas principais:

- 2 laterais
- 1 topo
- 1 base
- 1 costas, quando aplicavel
- 5 prateleiras
- 2 portas

Ferragens principais:

- dobradicas para porta esquerda
- dobradicas para porta direita
- puxadores ou sistema equivalente
- eventuais batentes, alinhadores ou ferragens complementares

### Regras funcionais esperadas

- a largura util da frente deve ser repartida por duas portas
- a decomposicao do corpo deve manter-se coerente com o caso de 1 porta
- o aumento de ferragens deve refletir a segunda frente
- o preco final deve diferir do modulo de 1 porta por materiais e ferragens adicionais

### Relacao com os tres niveis de regras

Dados Gerais:

- padrao de ferragem por porta
- material e acabamento base

Dados Items:

- alteracao do tipo de puxador
- alteracao do acabamento das portas
- especializacao da ferragem por contexto

Edicao Local no Custeio:

- ajuste de ferragens por porta
- ajuste de dimensao real das portas
- correcao localizada de uma linha

### Pontos sensiveis

- divisao correta do vao frontal
- alinhamento entre 2 portas e ferragens
- diferenca de comportamento versus modulo de 1 porta
- risco de reutilizar este modulo quando a logica correta e porta unica

### Validacoes minimas para testes

1. Inserir o modulo gera 2 portas e 5 prateleiras.
2. O numero de ferragens da frente aumenta face ao modulo de 1 porta.
3. Alterar a largura total repercute-se nas duas portas.
4. A troca de ferragem em Dados Items nao descaracteriza o modulo.
5. O custo total reflete a diferenca de frente dupla.

### Cenario de teste simples

- Medidas exemplo: `H=2400`, `L=900`, `P=550`
- Esperado: corpo simples, 2 portas equilibradas, 5 prateleiras, mais ferragens do que no caso de 1 porta

## Caso 3. Modulo com sistema de correr

### Identificacao

- Nome: Modulo Base com Sistema de Correr
- Familia: Roupeiro / Frente de correr
- Tipo: Modulo dependente de sistema
- Estado documental: referencia inicial

### Objetivo funcional
Representar um modulo onde o sistema de correr e determinante para frente, ferragens e comportamento construtivo.

Este caso serve para validar:

- dependencia forte de regras externas
- relacao entre sistema escolhido e ferragens carregadas
- impacto de configuracao no preco
- maior sensibilidade entre Dados Gerais, Dados Items e Custeio

### Contexto de uso
Usar quando o item depende de portas ou frentes de correr.

Nao usar quando:

- a frente real e de abrir
- o sistema nao esta definido
- o item ainda nao tem informacao suficiente para escolher ferragem de correr

### Inputs principais

- `H`: altura total
- `L`: largura total
- `P`: profundidade total
- sistema de correr
- numero de folhas
- material das folhas
- regras associadas a perfis, calhas e ferragens

### Estrutura minima esperada
Pecas principais:

- corpo do modulo, quando aplicavel
- folhas de correr
- elementos estruturais associados ao sistema
- componentes interiores, quando existirem

Ferragens principais:

- calha superior
- calha inferior, quando aplicavel
- perfis ou kits do sistema
- componentes de guiamento e travagem

### Regras funcionais esperadas

- o sistema de correr deve comandar o conjunto de ferragens carregado
- mudar o sistema deve alterar ferragens e possivelmente medidas derivadas
- o custo final deve refletir fortemente o sistema escolhido
- se o sistema nao estiver definido, o modulo deve ser tratado como incompleto ou bloqueado

### Relacao com os tres niveis de regras

Dados Gerais:

- sistema de correr padrao
- materiais e acabamentos padrao

Dados Items:

- selecao de sistema especifico para o item
- especializacao de ferragens do sistema
- especializacao do acabamento da frente

Edicao Local no Custeio:

- ajuste de componentes do kit
- ajuste fino de quantidades
- correcao localizada de ferragem ou perfil

### Pontos sensiveis

- dependencia de sistema externo ou tabela base correta
- risco de deixar o modulo sem sistema definido
- forte impacto de override manual em linhas de ferragem
- maior probabilidade de incoerencia entre configuracao e custo

### Validacoes minimas para testes

1. Inserir o modulo sem sistema definido gera aviso, pendencia ou estado incompleto.
2. Definir o sistema carrega ferragens coerentes com correr.
3. Trocar o sistema altera as linhas relevantes no custeio.
4. O preco muda de forma visivel quando muda o sistema.
5. Overrides locais nao devem apagar a identidade do sistema sem aviso.

### Cenario de teste simples

- Medidas exemplo: `H=2400`, `L=1800`, `P=650`
- Sistema: caso base de correr definido em Dados Gerais ou Dados Items
- Esperado: frentes e ferragens coerentes com correr, custo claramente dependente do sistema

## Comparacao rapida entre os 3 casos

| Caso | Frente | Sensibilidade principal | Dependencia de regras |
| --- | --- | --- | --- |
| 1 porta + 5 prateleiras | simples | porta unica e repeticao interior | media |
| 2 portas + 5 prateleiras | dupla | divisao da frente e ferragens duplicadas | media |
| sistema de correr | correr | sistema, ferragens e configuracao | alta |

## Ordem recomendada para usar estes casos

1. Comecar pelo modulo `1 porta + 5 prateleiras` para validar o caso base.
2. Validar depois `2 portas + 5 prateleiras` para testar variacao da frente.
3. Validar por fim o `modulo com sistema de correr`, por ser o mais sensivel a configuracao.

## Proximo passo recomendado
Depois destes tres casos de referencia, o passo seguinte deve ser:

1. transformar cada caso num exemplo real do sistema
2. ligar cada caso a testes de custeio
3. ligar cada caso a exemplos reais de orcamento
4. expandir o catalogo para gavetas, cozinha e WC

Testes ligados a este catalogo em `tests/test_catalogo_modulos_referencia.py`.

Camadas atuais:

- limpeza e importacao de snapshots de modulo
- geracao funcional de linhas e auto-dimensionamento
- resolucao real de `Dados Items` para porta, ferragens e sistemas de correr
- roundtrip de `custeio`: gerar, guardar e voltar a listar
