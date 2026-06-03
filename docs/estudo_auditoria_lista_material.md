# Estudo - Auditoria Lista Material

## Objetivo

A funcionalidade "Auditoria Lista Material" deve ajudar a rever o ficheiro
`Lista_Material_*.xlsm`, folha `listagem_cut_rite`, antes de seguir para
producao / CUT-RITE.

O valor principal nao e corrigir automaticamente o Excel. O valor principal e
mostrar ao utilizador, de forma concentrada, diferencas que normalmente passam
despercebidas em listagens grandes:

- notas escritas de forma ligeiramente diferente
- materiais com nomes equivalentes mas inconsistentes
- descricoes alteradas fora do conjunto esperado
- valores de orlas fora de contexto
- linhas tecnicamente iguais com instrucoes diferentes

Esta auditoria deve continuar read-only. Qualquer alteracao no Excel deve ser
feita pelo utilizador ou por um fluxo futuro explicitamente confirmado.

## Estado atual observado

A implementacao atual esta concentrada em:

- `Martelo_Orcamentos_V2/app/services/producao_lista_material_audit.py`
- `Martelo_Orcamentos_V2/ui/dialogs/lista_material_audit.py`
- `tests/test_lista_material_audit.py`

O servico atual ja faz pontos importantes:

- encontra o ficheiro `Lista_Material_*.xlsm`
- le a folha `listagem_cut_rite`
- prefere a tabela `Tabela_Cut_Rite`, com fallback por cabecalho
- valida colunas obrigatorias
- sinaliza descricao/artigo vazios
- sinaliza quantidade invalida ou com formula
- sinaliza dimensoes tecnicas vazias
- normaliza notas por espacos, maiusculas e alguns aliases
- agrupa notas equivalentes mesmo quando a ordem dos tokens muda
- protege casos como `19+19`, para nao separar medidas como se fossem tokens
- valida incoerencia simples entre piso no artigo e piso nas notas
- sinaliza material vazio, com excecoes configuraveis
- suporta aliases e lista canonica externa de materiais
- classifica valores de orlas como orla real, maquinacao, sutar ou desconhecido
- exporta relatorio Excel com resumo, grupos e ocorrencias
- mantem configuracao externa em `_Lista_Material_Audit`
- esta atras de feature flag por utilizador

Os testes atuais da auditoria passam no ambiente virtual do projeto:

```text
18 passed
```

Houve apenas aviso de cache do pytest, sem impacto funcional.

## Analise da obra exemplo 0817_JF_VIVA

Ficheiro analisado:

```text
Lista_Material_0817_01_26_JF_VIVA.xlsm
Folha: LISTAGEM_CUT_RITE
Tabela: Tabela_Cut_Rite
Linhas: 548
```

Resumo da lista:

- `Descricao`: 548 preenchidas, 22 valores distintos.
- `Material`: 548 preenchidos, 5 valores distintos.
- `Notas`: 295 preenchidas, 253 vazias, 15 valores distintos.
- Orlas: 4 valores distintos, todos classificados como orla real.

Resultado da auditoria antes da melhoria:

- 0 erros.
- 3 avisos, apenas `Qt` com formula.
- 0 sugestoes.
- 4 informacoes de orlas agregadas.

Isto confirma o problema reportado: para uma lista grande e com muitas linhas
comparaveis, a auditoria quase nao dava informacao pratica.

Motivo principal:

- A assinatura usada para comparar linhas era demasiado rigida.
- Incluia orlas e CNC, mas nao incluia o artigo.
- Assim, linhas da mesma peca/artigo com diferenca nas notas deixavam de ser
  comparadas se tambem variassem numa orla ou num campo tecnico secundario.
- A regra de piso tambem era demasiado restrita: reconhecia artigo `P2`, mas
  nao reconhecia nomes reais como `RP 03 P2`, `RP 09 P1 DIR` ou `RP 18 RC ESQ`.

Depois da primeira melhoria, a mesma obra passou a devolver:

- 0 erros.
- 3 avisos estruturais.
- 51 sugestoes de revisao.
- 44 grupos de uniformizacao.
- 4 informacoes de orlas agregadas.

As novas sugestoes aparecem sobretudo em casos como:

```text
Mesmo artigo + mesma descricao + mesmo material + mesmas medidas,
mas uma linha tem "RASGO FIO LED" e outra esta sem nota.
```

Isto nao quer dizer que a linha esteja errada. Quer dizer que agora a auditoria
mostra ao utilizador uma diferenca que antes ficava invisivel.

## Melhorias ja aplicadas

Foram aplicadas melhorias conservadoras, mantendo a auditoria read-only:

- categoria propria `Descricao`
- ficheiro externo `descriptions.json`
- deteccao de variantes de escrita em `Descricao`
- leitura de piso dentro de artigos reais como `RP 03 P2` e `RP 09 P1 DIR`
- comparacao de notas com assinatura menos rigida
- deteccao de possivel nota em falta em linhas tecnicamente equivalentes
- validacao de espessura do material contra a coluna `Esp`
- aviso por valor desconhecido nas colunas de orla
- sugestao quando texto de maquinacao aparece numa coluna de orla
- merge entre configuracao default e configuracao externa existente, para
  melhorias futuras nao ficarem bloqueadas por ficheiros JSON antigos

Testes da auditoria depois da melhoria:

```text
23 passed
```

## Limitacoes principais

### 1. Notas

A normalizacao atual ja encontra casos simples, mas ainda depende muito de
aliases fixos. Faltam camadas para detetar:

- textos quase iguais por pontuacao, parenteses, barras, hifens ou erros curtos
- abreviaturas nao configuradas
- tokens equivalentes ainda desconhecidos
- linhas parecidas que diferem so numa palavra critica
- outliers: uma nota rara dentro de muitas notas quase iguais

Exemplo do problema esperado:

```text
MONTADO + PUX APLICAR (JF_VIVA)
PUXADOR APLICAR(JF VIVA)+ MONTADO
Montado / pux aplicar JF_VIVA
```

Estas linhas deviam aparecer juntas como "possivel mesma instrucao", com a
forma dominante sugerida.

### 2. Material

A analise atual so ganha forca quando a lista canonica externa estiver bem
preenchida. Sem essa configuracao, apenas apanha variantes muito proximas pelo
normalizador.

Faltam validacoes como:

- material parecido com outro ja usado na mesma lista
- mesma descricao + espessura + dimensoes com materiais diferentes
- material com espessura no nome incoerente com a coluna `Esp`
- materiais raros dentro do mesmo artigo/processo
- materiais com sufixos/prefixos equivalentes escritos de outra forma
- sugestao de material canonico por similaridade, nao apenas por alias exato

### 3. Descricao

Hoje a coluna `Descricao` praticamente so e validada quando esta vazia.

Como esta coluna tem nomes bem definidos, deveria ter auditoria propria:

- descricao fora da lista permitida
- descricao parecida com uma descricao permitida
- variantes de escrita da mesma descricao
- descricao incomum para determinado tipo de material/espessura/orla
- linhas tecnicamente iguais com descricoes diferentes

Esta deve ser uma categoria propria, e nao apenas "estrutura".

### 4. Orlas

A auditoria atual classifica valores das quatro colunas de orla, mas ainda nao
analisa contexto.

Faltam regras como:

- valor desconhecido por coluna e por linha, nao so agregado
- nomes de maquinacao escritos em colunas de orla quando deveriam estar em CNC
- `SUTAR` ou `FRESAR` misturado com orla real sem regra clara
- orla incompatvel com material/espessura
- padroes anormais por descricao: por exemplo porta sem orla onde quase todas
  as portas semelhantes tem orla
- diferencas ESQ/DIR/CIMA/BAIXO em linhas quase iguais
- valores raros de orla dentro da mesma lista

## Proposta de melhoria

### A. Criar categoria `descricao`

Adicionar a categoria entre `notas` e `materiais`.

Regras sugeridas:

- `descricao_desconhecida`
- `descricao_parecida`
- `descricao_uniformizar`
- `descricao_incoerente_em_linhas_equivalentes`

Fonte canonica:

- ficheiro externo `descricoes.json` em `_Lista_Material_Audit`
- opcionalmente alimentado no futuro a partir de configuracoes internas ou
  historico validado

Formato sugerido:

```json
{
  "canonical_descriptions": [
    "Porta",
    "Lateral",
    "Prateleira",
    "Fundo",
    "Tampo",
    "Base"
  ],
  "aliases": {
    "PORTAS": "Porta",
    "PRATEL.": "Prateleira"
  }
}
```

### B. Melhorar normalizacao de notas

Manter o que existe e adicionar:

- normalizacao de pontuacao leve
- equivalencia entre separadores (`+`, `/`, `;`, `,`) quando configurado
- comparacao por tokens ordenados e por sequencia original
- similaridade fuzzy entre notas normalizadas
- deteccao de outliers por frequencia

Regras sugeridas:

- `nota_parecida`
- `nota_token_desconhecido`
- `nota_outlier`
- `nota_pontuacao_diferente`

Importante: nao transformar isto em erro. Deve aparecer como `sugestao` ou
`aviso`, porque uma palavra diferente pode ser intencional.

### C. Melhorar analise de materiais

Adicionar um indice de materiais observados no proprio ficheiro, alem da lista
canonica externa.

Regras sugeridas:

- `material_parecido`
- `material_espessura_incoerente`
- `material_diferente_em_linhas_equivalentes`
- `material_raro_no_artigo`
- `material_desconhecido_com_sugestao`

Criticas mais fortes:

- mesmo artigo + descricao + comp + larg + esp + veio + orlas, mas material
  diferente
- material com `19MM` no nome e `Esp=16`

### D. Melhorar analise de orlas

Criar uma leitura por linha, nao apenas agregada.

Regras sugeridas:

- `orla_valor_desconhecido`
- `orla_maquinacao_em_coluna_orla`
- `orla_incoerente_em_linhas_equivalentes`
- `orla_vazia_em_linha_semelhante`
- `orla_espessura_incoerente`
- `orla_valor_raro`

Manter uma folha/tab "Orlas" agregada, mas permitir perceber as linhas
concretas.

### E. Melhorar a tabela da auditoria

A tabela atual mostra grupos resumidos. Para listas grandes, isso ajuda, mas
falta leitura comparativa.

Melhorias de UI:

- coluna "Valor dominante"
- coluna "Valor divergente"
- coluna "Linhas afetadas"
- coluna "Exemplos comparados"
- duplo clique no grupo para abrir ocorrencias detalhadas
- filtro por categoria, severidade, confianca e artigo
- botao "Copiar linhas" para facilitar procurar no Excel
- separacao visual entre erro tecnico e sugestao de uniformizacao

Modelo mental recomendado:

- `Erro`: impede confiar no ficheiro
- `Aviso`: pode causar erro em producao
- `Sugestao`: uniformizacao recomendada
- `Info`: estatistica / classificacao

### F. Relatorio de decisao

O resumo devia responder rapidamente:

- quantas linhas foram auditadas
- quantos erros reais existem
- quantos avisos precisam decisao humana
- quantas sugestoes sao apenas uniformizacao
- quais os 10 grupos com maior impacto
- que configuracoes externas foram usadas

Isto ajuda a decidir se a funcionalidade deve ficar definitiva.

## Implementacao incremental recomendada

### Fase 1 - Sem risco, alto valor

- adicionar categoria `descricao`
- adicionar `descricoes.json`
- validar descricoes desconhecidas e parecidas
- melhorar tabela/export para mostrar valor dominante vs divergente
- adicionar testes especificos para descricao

### Fase 2 - Comparacao fuzzy controlada

- adicionar similaridade por `difflib.SequenceMatcher` ou funcao equivalente
- aplicar fuzzy apenas dentro da mesma coluna e com limites conservadores
- nunca marcar como erro por fuzzy
- criar thresholds configuraveis por coluna
- adicionar testes com falsos positivos conhecidos

### Fase 3 - Contexto tecnico

- comparar linhas equivalentes por assinatura tecnica parcial
- separar assinaturas para notas, materiais, descricoes e orlas
- sinalizar diferencas fortes quando a linha e tecnicamente igual
- sinalizar outliers por artigo/material/descricao

### Fase 4 - Aprendizagem operacional

- permitir marcar sugestoes como "aceite", "ignorar" ou "adicionar alias"
- gravar apenas configuracao externa, nao alterar o Excel automaticamente
- preparar historico validado para futuras sugestoes assistidas por IA

## Decisao recomendada

A funcionalidade tem utilidade suficiente para continuar em teste controlado,
porque atua numa zona real de risco: inconsistencias manuais em ficheiros
grandes antes da producao.

Ainda nao deve passar a obrigatoria. Deve continuar por feature flag ate ter:

- categoria `descricao`
- melhor comparacao de notas
- analise contextual de materiais e orlas
- UI com grupos comparativos mais claros
- pelo menos alguns ficheiros reais auditados e classificados pelo utilizador

O caminho mais seguro e evoluir a auditoria como ferramenta read-only de
diagnostico, sem qualquer correcao automatica do Excel nesta fase.
