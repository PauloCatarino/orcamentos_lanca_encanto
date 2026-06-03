# Protocolo de confirmacao

Use este protocolo sempre que uma tarefa possa apagar, substituir ou reescrever dados de negocio existentes.

## Passos

1. Identificar a origem do pedido.
2. Distinguir entre:
   - edicao funcional normal pedida pelo utilizador
   - manutencao tecnica corretiva ou limpeza
3. Mapear o impacto:
   - tabelas e modelos
   - relacoes em cascata
   - ficheiros e pastas envolvidos
4. Propor medida de seguranca:
   - backup
   - export
   - transacao
   - dry-run
   - soft-delete
5. Pedir confirmacao explicita.
6. So depois executar.

## Frase minima de seguranca

Antes de executar, o agente deve conseguir responder claramente:

- O que vai ser alterado?
- O que pode ser perdido?
- Como se recupera?
- O utilizador confirmou explicitamente?

Se alguma resposta for "nao sei", nao executar.
