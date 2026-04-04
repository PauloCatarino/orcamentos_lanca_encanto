# Integracoes Futuras

## Objetivo
Este documento descreve a direcao de integracao do Martelo com sistemas externos e fluxos complementares.

As integracoes devem servir tres objetivos:

- reduzir trabalho manual repetitivo
- melhorar coerencia entre orcamentacao e producao
- reaproveitar informacao tecnica ja existente noutros sistemas

## Principios das integracoes
Qualquer integracao futura deve respeitar estes principios:

- o Martelo continua a ser orientado a modulos
- a validacao humana continua obrigatoria
- nenhuma integracao deve quebrar os tres niveis de regras
- overrides locais no custeio nao podem ser apagados silenciosamente
- cada campo relevante deve ter uma origem de verdade bem definida
- atualizacoes automaticas devem ser conservadoras quando existir ambiguidade

## Estado atual observado
Pelo estado atual do codigo, algumas integracoes ja estao em curso ou parcialmente operacionais.

### PHC
Ja existe trabalho funcional em:

- pesquisa de encomendas PHC
- importacao de dados de cliente e encomenda
- validacao do nome abreviado do cliente
- criacao de processo de producao a partir do PHC
- sincronizacao diaria de alguns estados PHC com Producao
- dialogo de divergencias entre Martelo e PHC

### CUT-RITE
Ja existe trabalho funcional em:

- uso do nome do plano CUT-RITE no processo
- deteccao do PDF exportado
- copia do PDF do plano para a pasta da obra
- verificacao de desatualizacao entre origem e copia da obra

### IMOS
Ja existe trabalho funcional em:

- referencia ao nome da encomenda IMOS
- uso de imagem IMOS no `Caderno de Encargos`
- ligacao a programas CNC e fluxo de preparacao

### CNC e MPR
Ja existe trabalho funcional em:

- copia de programas CNC para a pasta da obra
- envio de programas para a pasta anual de MPR
- validacao do estado desses ficheiros na preparacao

## Integracao futura com PHC
### Objetivos

- usar o PHC como fonte consistente para cliente e encomenda
- reduzir divergencias entre dados comerciais e operacionais
- melhorar o arranque de processos de producao

### Possiveis evolucoes

- mapa completo de estados PHC reconhecidos pelo Martelo
- sincronizacao controlada de campos chave
- validacao mais forte de referencias de cliente e encomenda
- historico de divergencias por obra
- diagnostico de correspondencias ambiguas

### Regras de seguranca

- nao atualizar automaticamente quando faltar `Ano`, `Num Enc PHC`, `Num Cliente PHC` ou `Nome Cliente`
- manter logica conservadora em match de registos
- nunca sobrescrever dados locais relevantes sem comparacao explicita

## Integracao futura com CUT-RITE
### Objetivos

- ligar melhor o plano de corte ao processo da obra
- reduzir falhas documentais na preparacao
- garantir que a copia usada em obra corresponde ao ultimo export

### Possiveis evolucoes

- importacao controlada de metadata do plano
- verificacao de versao do plano associado a obra
- checklist de consistencia entre plano, item e obra
- maior automatizacao da preparacao documental

### Regras de seguranca

- o plano associado a obra deve depender sempre do `Nome Plano CUT-RITE`
- ficheiros copiados para a obra nao devem ser assumidos como atuais sem comparacao de timestamps

## Integracao futura com IMOS
### Objetivos

- aproveitar melhor dados tecnicos e programas
- reduzir preparacao manual da obra
- ligar melhor documentacao, imagem e producao

### Possiveis evolucoes

- melhor descoberta de imagem e documentos por encomenda IMOS
- validacao mais forte dos programas CNC esperados
- ligacao mais clara entre estrutura do item e ficheiros tecnicos

### Regras de seguranca

- nomes de encomenda IMOS devem ser tratados como chaves operacionais
- o sistema deve falhar de forma explicita quando a pasta ou imagem esperada nao existirem

## Integracao futura com relatorios e documentos
### Objetivos

- consolidar documentacao de obra
- reduzir erros de impressao e versoes erradas
- facilitar controlo do que esta pronto para fabrica

### Possiveis evolucoes

- historico de geracao e impressao de documentos
- validacao de conjunto documental obrigatorio por tipo de obra
- melhor controlo de versoes entre PDF, Excel e origem tecnica

## Integracao futura com IA assistida
### Objetivo estrategico
Usar IA como apoio a criacao do orcamento a partir de pedidos do cliente, nunca como substituto integral da validacao humana.

### Cenario esperado

- o cliente envia texto, desenho ou imagem
- o sistema identifica modulos semelhantes
- o sistema encontra items semelhantes de historico
- o sistema sugere uma estrutura inicial
- o utilizador valida, ajusta e aprova

### Pre-condicoes para esta integracao

- modulos melhor documentados
- historico de items reutilizavel
- dados tecnicos e comerciais mais consistentes
- nomenclaturas mais estaveis

## Ordem recomendada de integracao
Prioridade pratica:

1. Consolidar `PHC`.
2. Estabilizar `CUT-RITE` e `IMOS` na preparacao de producao.
3. Formalizar contratos de dados entre obra, item, modulo e sistema externo.
4. Preparar historico reutilizavel.
5. Avancar para IA assistida.

## Riscos principais
As integracoes podem introduzir risco funcional se:

- misturarem regras externas com overrides locais sem controlo
- tratarem identificadores inconsistentes como se fossem equivalentes
- atualizarem estados ou custos sem contexto suficiente
- dependerem de ficheiros de rede sem mensagens claras de erro

## Criterio de sucesso
Uma integracao bem sucedida no Martelo deve:

- poupar trabalho manual real
- aumentar coerencia do processo
- nao reduzir controlo do utilizador
- ser auditavel e previsivel
- falhar de forma segura quando os dados externos forem ambiguos ou incompletos
