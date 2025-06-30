# db_connection.py
import mysql.connector
from mysql.connector import Error, pooling # Importar pooling explicitamente pode ser útil
from contextlib import contextmanager
import time # Para adicionar um pequeno delay em caso de erro de pool

# Configurações do Pool de Conexões
# NOTA: Em produção, considere carregar estas configurações de um ficheiro externo seguro.
POOL_CONFIG = {
    "pool_name": "orcamentos_pool",
    "pool_size": 10,  # Número de conexões mantidas abertas e prontas
    # 'pool_reset_session': True, # Opcional: Garante estado limpo da sessão
    #"host": "localhost",# # Use 'localhost' ou o IP do servidor MySQL
    "host": "192.168.5.101",
    "user": "orcamentos_le",
    "password": "admin",
    "database": "orcamentos",
    "charset": "utf8mb4",       # Boa prática especificar charset
    "collation": "utf8mb4_unicode_ci" # Boa prática especificar collation
}

# Tenta criar o pool de conexões uma vez quando o módulo é carregado
try:
    print("Inicializando pool de conexões MySQL...")
    connection_pool = pooling.MySQLConnectionPool(**POOL_CONFIG)
    #print(f"Pool '{POOL_CONFIG['pool_name']}' inicializado com sucesso (Tamanho: {POOL_CONFIG['pool_size']}).")
except Error as err:
    print(f"[ERRO CRÍTICO] Falha ao inicializar o pool de conexões MySQL: {err}")
    # Em caso de falha ao criar o pool, a aplicação provavelmente não funcionará.
    # Poderia levantar uma exceção aqui ou definir connection_pool como None
    # para que as tentativas de obter conexão falhem claramente.
    connection_pool = None
    # exit() # Descomente se a aplicação não deve continuar sem pool
def get_connection():
    """
    Obtém uma conexão do pool de conexões.
    Tenta obter uma conexão; se o pool estiver esgotado ou indisponível,
    pode levantar uma exceção (PoolError).
    """
    if connection_pool is None:
        print("[ERRO] Pool de conexões não inicializado.")
        raise Error("Pool de conexões não está disponível.") # Levanta erro para indicar falha

    try:
        # Pede uma conexão ao pool
        conn = connection_pool.get_connection()
        # print(f"[DEBUG Pool] Conexão {id(conn)} obtida do pool.") # Debug
        return conn
    except pooling.PoolError as err:
        # Erro comum: Pool esgotado (nenhuma conexão disponível)
        print(f"[ERRO Pool] Erro ao obter conexão do pool: {err}")
        # Opcional: Esperar um pouco e tentar novamente? Ou apenas levantar o erro?
        # time.sleep(0.1) # Pequeno delay antes de re-levantar
        raise # Re-levanta a exceção para que a função chamadora saiba que falhou

@contextmanager
def obter_cursor(commit_on_exit=True):
    """
    Gerenciador de contexto que fornece um cursor usando uma conexão do pool.
    Garante que a conexão seja devolvida ao pool no final, mesmo em caso de erro.

    Parâmetros:
    -----------
    commit_on_exit : bool
        Se True (padrão), faz commit da transação ao sair do bloco 'with' sem erros.
        Se False, o chamador é responsável por fazer commit ou rollback.
    """
    if connection_pool is None:
        print("[ERRO DB] Pool de conexões não está disponível. Não é possível obter cursor.")
        # Pode-se levantar uma exceção aqui para sinalizar falha crítica
        raise ConnectionError("Pool de conexões MySQL não inicializado.")
        # Ou retornar None e deixar o chamador tratar (menos ideal para @contextmanager)
        # yield None 
        # return 

    connection = None
    cursor = None
    try:
        connection = connection_pool.get_connection()
        cursor = connection.cursor(dictionary=False) # dictionary=False para retornar tuplas
        # print("[DEBUG DB] Conexão obtida do pool. Cursor criado.") # Debug
        yield cursor
        # Se commit_on_exit for True e não houve exceções, faz commit
        if commit_on_exit:
            connection.commit()
            # print("[DEBUG DB] Transação comitada (padrão).") # Debug
    except mysql.connector.Error as err:
        print(f"[ERRO DB Transação] Erro durante a transação: {err}")
        if connection and connection.is_connected():
            connection.rollback()
            # print("[DEBUG DB] Transação revertida (rollback).") # Debug
        raise # Re-levanta a exceção para o chamador tratar ou logar
    except Exception as e:
        print(f"[ERRO DB Inesperado] Erro inesperado com o cursor/conexão: {e}")
        if connection and connection.is_connected():
            connection.rollback()
            # print("[DEBUG DB] Transação revertida (rollback inesperado).") # Debug
        raise # Re-levanta a exceção
    finally:
        if cursor:
            cursor.close()
            # print("[DEBUG DB] Cursor fechado.") # Debug
        if connection and connection.is_connected():
            connection.close() # Retorna a conexão ao pool
            # print("[DEBUG DB] Conexão retornada ao pool.") # Debug

# Exemplo de uso (pode ser removido ou mantido para teste rápido)
if __name__ == "__main__":
    try:
        print("\nTestando obter_cursor()...")
        with obter_cursor() as cur:
            cur.execute("SELECT DATABASE();")
            db_name = cur.fetchone()
            print(f"Conectado à base de dados: {db_name[0] if db_name else 'N/A'}")

            # Teste de query simples (ex: contar clientes)
            cur.execute("SELECT COUNT(*) FROM clientes;")
            count = cur.fetchone()
            print(f"Número de clientes na tabela: {count[0] if count else 'N/A'}")

        print("Conexão fechada e devolvida ao pool (pelo 'with').")

        # Teste de erro (ex: tabela inexistente) para verificar rollback
        print("\nTestando tratamento de erro (query inválida)...")
        try:
             with obter_cursor() as cur:
                  cur.execute("SELECT * FROM tabela_nao_existe;")
        except Error as e:
             print(f"Erro esperado capturado: {e}")
             print("Rollback deve ter sido executado e conexão devolvida ao pool.")

    except Error as e:
        print(f"Erro durante o teste de conexão: {e}")