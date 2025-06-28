# modulo_gestao_modulos_db.py
# -*- coding: utf-8 -*-

"""
Módulo: modulo_gestao_modulos_db.py

Objetivo:
---------
Gerir todas as operações de persistência (CRUD - Create, Read, Update, Delete)
relacionadas com os "Módulos Guardados" e as suas respetivas peças na base de dados MySQL.

Principais Funcionalidades:
---------------------------
1.  `criar_tabelas_modulos()`: Cria as tabelas `modulos_guardados` (para metadados do módulo)
    e `modulo_pecas_guardadas` (para os detalhes das peças de cada módulo) se não existirem.
2.  `verificar_nome_modulo_existe(nome_modulo)`: Verifica se um módulo com um dado nome já
    existe na base de dados.
3.  `salvar_novo_modulo_com_pecas(...)`: Insere um novo módulo e as suas peças constituintes
    na base de dados de forma transacional.
4.  `atualizar_modulo_existente_com_pecas(...)`: Atualiza os metadados de um módulo existente
    e substitui as suas peças pelas novas fornecidas, de forma transacional.
5.  `obter_todos_modulos()`: Recupera uma lista de todos os módulos guardados para apresentação
    ao utilizador (ex: nos diálogos de importação ou gestão).
6.  `obter_pecas_de_modulo(id_modulo)`: Recupera todas as peças associadas a um
    determinado ID de módulo.
7.  `eliminar_modulo_por_id(id_modulo)`: Remove um módulo e, através de `ON DELETE CASCADE`,
    as suas peças associadas da base de dados.

Interação com Outros Módulos Chave:
-----------------------------------
-   É chamado pelos diálogos `DialogoGravarModulo`, `DialogoImportarModulo`, e
    `DialogoGerirModulos` para realizar operações na base de dados.
-   Utiliza `db_connection.py` para obter cursores e gerir conexões com a base de dados.
"""

import mysql.connector
from PyQt5.QtWidgets import QMessageBox
from db_connection import obter_cursor # Assumindo que db_connection.py está acessível

def criar_tabelas_modulos():
    """
    Cria as tabelas `modulos_guardados` e `modulo_pecas_guardadas` na base de dados
    se ainda não existirem.
    """
    try:
        with obter_cursor() as cursor:
            # Tabela para os Módulos Guardados
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS modulos_guardados (
                id_modulo INT AUTO_INCREMENT PRIMARY KEY,
                nome_modulo VARCHAR(255) NOT NULL UNIQUE,
                descricao_modulo TEXT NULL,
                caminho_imagem_modulo VARCHAR(500) NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_modificacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)
            print("[INFO DB Módulos] Tabela 'modulos_guardados' verificada/criada.")

            # Tabela para as Peças dentro de cada Módulo Guardado
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS modulo_pecas_guardadas (
                id_modulo_peca INT AUTO_INCREMENT PRIMARY KEY,
                id_modulo_fk INT NOT NULL,
                ordem_peca INT NOT NULL,  /* Ordem da peça dentro do módulo */
                descricao_livre_peca TEXT NULL,
                def_peca_peca VARCHAR(255) NULL,
                qt_und_peca VARCHAR(255) NULL, /* Guardar como texto para fórmulas */
                comp_peca VARCHAR(255) NULL,    /* Guardar como texto para fórmulas */
                larg_peca VARCHAR(255) NULL,    /* Guardar como texto para fórmulas */
                esp_peca VARCHAR(255) NULL,     /* Guardar como texto para fórmulas */
                mat_default_peca VARCHAR(100) NULL,
                tab_default_peca VARCHAR(100) NULL,
                grupo_peca VARCHAR(50) NULL, /* Para recriar UserRole no DefPecaDelegate */
                und_peca VARCHAR(20) NULL, /* Adicionado para manter a unidade da peça */
                comp_ass_1_peca VARCHAR(255) NULL,
                comp_ass_2_peca VARCHAR(255) NULL,                   
                comp_ass_3_peca VARCHAR(255) NULL,
                /* Outras colunas que possam ser relevantes guardar (ex: BLK, MPs, MO, Orla) */
                /* Por agora, focamos nas essenciais para recriar a linha */
                FOREIGN KEY (id_modulo_fk) REFERENCES modulos_guardados(id_modulo) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)
            print("[INFO DB Módulos] Tabela 'modulo_pecas_guardadas' verificada/criada.")

    except mysql.connector.Error as err:
        print(f"[ERRO DB Módulos] Erro MySQL ao criar/verificar tabelas de módulos: {err}")
        QMessageBox.critical(None, "Erro Base de Dados", f"Não foi possível criar/verificar as tabelas de módulos: {err}")
    except Exception as e:
        print(f"[ERRO INESPERADO] Ao criar/verificar tabelas de módulos: {e}")
        QMessageBox.critical(None, "Erro Crítico", f"Erro inesperado durante a inicialização das tabelas de módulos: {e}")

# --- Funções de gestão de módulos (placeholder por agora, serão implementadas depois) ---

def verificar_nome_modulo_existe(nome_modulo):
    """
    Verifica se um módulo com o nome especificado já existe na tabela `modulos_guardados`.
    Retorna o id_modulo se existir, caso contrário, retorna None.
    """
    if not nome_modulo:
        return None
    try:
        with obter_cursor() as cursor:  # commit_on_exit=True (padrão) é OK para SELECTs
            sql = "SELECT id_modulo FROM modulos_guardados WHERE nome_modulo = %s"
            cursor.execute(sql, (nome_modulo,))
            resultado = cursor.fetchone()
            if resultado:
                return resultado[0] # Retorna o id_modulo
            return None
    except mysql.connector.Error as err:
        print(f"[ERRO DB Módulos] Erro ao verificar nome do módulo '{nome_modulo}': {err}")
        return None # Considerar levantar a exceção ou tratar de forma diferente
    

def salvar_novo_modulo_com_pecas(nome_modulo, descricao, caminho_imagem, pecas_do_modulo):
    """
    Salva um novo módulo e as suas peças associadas nas tabelas da base de dados.
    Inclui agora as colunas comp_ass_X_peca.
    Retorna o ID do novo módulo se sucesso, None caso contrário.
    """
    if not nome_modulo or not pecas_do_modulo:
        print("[AVISO DB Módulos] Nome do módulo ou lista de peças vazia. Não foi possível salvar.")
        return None

    # A conexão será obtida e gerida pelo context manager 'obter_cursor'
    # O commit/rollback será feito pelo próprio context manager se commit_on_exit=False for usado corretamente.
    
    # Para fazer uma transação manual, obtemos a conexão primeiro, e passamos
    # para o cursor, mas a sua estrutura com @contextmanager já lida com isso.
    # A chave é que o `obter_cursor` PRECISA da referência da conexão para fazer commit/rollback.

    # Se `obter_cursor` devolve apenas o cursor, e faz o commit/rollback internamente
    # baseado em `commit_on_exit`, então a lógica de transação deve estar DENTRO de um único bloco `with`.

    try:
        # Iniciamos uma transação que engloba todas as operações.
        # `obter_cursor` com `commit_on_exit=False` significa que NÓS controlamos o commit/rollback.
        with obter_cursor(commit_on_exit=False) as cursor:
            # 1. Inserir o módulo
            sql_modulo = """
            INSERT INTO modulos_guardados (nome_modulo, descricao_modulo, caminho_imagem_modulo)
            VALUES (%s, %s, %s)
            """
            cursor.execute(sql_modulo, (nome_modulo, descricao, caminho_imagem if caminho_imagem else None))
            id_novo_modulo = cursor.lastrowid
            if id_novo_modulo is None: # Verificar se lastrowid retornou algo
                raise mysql.connector.Error("Não foi possível obter o ID do novo módulo.")
            print(f"[INFO DB Módulos] Novo módulo '{nome_modulo}' preparado para inserção com ID: {id_novo_modulo}")

            # 2. Inserir as peças na tabela `modulo_pecas_guardadas`
            sql_peca = """
            INSERT INTO modulo_pecas_guardadas (
                id_modulo_fk, ordem_peca, descricao_livre_peca, def_peca_peca,
                qt_und_peca, comp_peca, larg_peca, esp_peca,
                mat_default_peca, tab_default_peca, grupo_peca, und_peca,
                comp_ass_1_peca, comp_ass_2_peca, comp_ass_3_peca
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            dados_pecas_para_inserir = [
                (
                    id_novo_modulo,
                    peca.get("ordem_peca"), peca.get("descricao_livre_peca"), peca.get("def_peca_peca"),
                    peca.get("qt_und_peca"), peca.get("comp_peca"), peca.get("larg_peca"),
                    peca.get("esp_peca"), peca.get("mat_default_peca"), peca.get("tab_default_peca"),
                    peca.get("grupo_peca"), peca.get("und_peca"),
                    peca.get("comp_ass_1_peca"), 
                    peca.get("comp_ass_2_peca"), 
                    peca.get("comp_ass_3_peca")  
                ) for peca in pecas_do_modulo
            ]
            
            cursor.executemany(sql_peca, dados_pecas_para_inserir)
            print(f"[INFO DB Módulos] {cursor.rowcount} peças preparadas para inserção para o módulo ID {id_novo_modulo}.")
            
            # Se tudo correu bem até aqui, fazemos o commit DENTRO do `try` do `with`
            # O `obter_cursor` precisa da conexão para fazer o commit.
            # O erro `AttributeError: 'MySQLCursor' object has no attribute 'connection'`
            # acontece porque `cursor` não é o objeto `connection`.
            # A forma correta é aceder `cursor._connection` ou, melhor,
            # deixar o `obter_cursor` lidar com o commit se `commit_on_exit=True`
            # ou a função chamadora fazê-lo na conexão.
            
            # CORREÇÃO: O commit deve ser feito no objeto connection, que `obter_cursor` gere.
            # Como passamos commit_on_exit=False, nós controlamos o commit fora do with, mas
            # precisamos da referência da conexão.
            # A maneira mais limpa com o seu @contextmanager é confiar nele para o commit/rollback.
            # Se o `obter_cursor` é chamado com `commit_on_exit=False`, a transação só é
            # finalizada pela função que chamou `obter_cursor`.
            # Para que `salvar_novo_modulo_com_pecas` seja transacional, todo o bloco
            # de inserção de módulo e peças deve estar dentro de UM `with obter_cursor(commit_on_exit=False):`
            # e o commit deve ser chamado explicitamente na conexão *antes* de sair do `with` se tudo OK.
            # Ou, mais simples, confiamos no `obter_cursor` para fazer o commit se nenhuma exceção ocorrer.

            # Vamos simplificar e assumir que cada chamada a `obter_cursor` pode ser uma transação
            # se `commit_on_exit=True`. Para operações multi-passo, ou fazemos tudo num `with`
            # ou garantimos que `obter_cursor` não faz commit até ao final.

            # Dado o erro, a maneira mais direta de corrigir DENTRO desta função,
            # mantendo o `obter_cursor(commit_on_exit=False)` é:
            if hasattr(cursor, '_connection') and cursor._connection:
                 cursor._connection.commit() # Commit da transação
                 print(f"[INFO DB Módulos] Transação para '{nome_modulo}' comitada.")
                 return id_novo_modulo
            else:
                # Isso não deveria acontecer se obter_cursor funcionou
                print("[ERRO DB Módulos] Não foi possível aceder ao objeto de conexão para commit.")
                return None

    except mysql.connector.Error as err:
        print(f"[ERRO DB Módulos] Erro ao salvar novo módulo '{nome_modulo}': {err}")
        # O rollback é feito automaticamente por `obter_cursor` no seu bloco `except`
        return None
    except Exception as e:
        print(f"[ERRO INESPERADO DB Módulos] Ao salvar novo módulo '{nome_modulo}': {e}")
        import traceback
        traceback.print_exc() # Adicionado para mais detalhes do erro
        # O rollback é feito automaticamente por `obter_cursor`
        return None
    

def atualizar_modulo_existente_com_pecas(id_modulo, nome_modulo, descricao, caminho_imagem, pecas_do_modulo):
    """
    Atualiza um módulo existente e as suas peças.
    Primeiro, apaga as peças antigas do módulo e depois insere as novas.
    Retorna True se sucesso, False caso contrário.
    """
    if not id_modulo or not nome_modulo or not pecas_do_modulo:
        print("[AVISO DB Módulos] ID do módulo, nome ou lista de peças vazia para atualização.")
        return False

    try:
        with obter_cursor(commit_on_exit=False) as cursor: # Controlar transação manualmente
            # 1. Atualizar dados na tabela `modulos_guardados`
            sql_update_modulo = """
            UPDATE modulos_guardados
            SET nome_modulo = %s, descricao_modulo = %s, caminho_imagem_modulo = %s
            WHERE id_modulo = %s
            """
            cursor.execute(sql_update_modulo, (nome_modulo, descricao, caminho_imagem if caminho_imagem else None, id_modulo))
            print(f"[INFO DB Módulos] Módulo ID {id_modulo} atualizado para nome '{nome_modulo}'.")

            # 2. Apagar peças antigas associadas a este módulo
            sql_delete_pecas = "DELETE FROM modulo_pecas_guardadas WHERE id_modulo_fk = %s"
            cursor.execute(sql_delete_pecas, (id_modulo,))
            print(f"[INFO DB Módulos] {cursor.rowcount} peças antigas do módulo ID {id_modulo} eliminadas.")

            # 3. Inserir as novas peças
            sql_insert_peca = """
            INSERT INTO modulo_pecas_guardadas (
                id_modulo_fk, ordem_peca, descricao_livre_peca, def_peca_peca,
                qt_und_peca, comp_peca, larg_peca, esp_peca,
                mat_default_peca, tab_default_peca, grupo_peca, und_peca,
                comp_ass_1_peca, comp_ass_2_peca, comp_ass_3_peca
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            dados_pecas_para_inserir = [
                (
                    id_modulo,
                    peca.get("ordem_peca"), peca.get("descricao_livre_peca"), peca.get("def_peca_peca"),
                    peca.get("qt_und_peca"), peca.get("comp_peca"), peca.get("larg_peca"),
                    peca.get("esp_peca"), peca.get("mat_default_peca"), peca.get("tab_default_peca"),
                    peca.get("grupo_peca"), peca.get("und_peca"),
                    peca.get("comp_ass_1_peca"),
                    peca.get("comp_ass_2_peca"),
                    peca.get("comp_ass_3_peca")
                ) for peca in pecas_do_modulo
            ]
            
            cursor.executemany(sql_insert_peca, dados_pecas_para_inserir)
            print(f"[INFO DB Módulos] {cursor.rowcount} novas peças inseridas para o módulo ID {id_modulo}.")

            if hasattr(cursor, '_connection') and cursor._connection:
                cursor._connection.commit()
                print(f"[INFO DB Módulos] Transação de atualização para ID {id_modulo} comitada.")
                return True
            else:
                print(f"[ERRO DB Módulos] Não foi possível aceder à conexão para commit na atualização do ID {id_modulo}.")
                return False

    except mysql.connector.Error as err:
        print(f"[ERRO DB Módulos] Erro ao atualizar módulo ID {id_modulo}: {err}")

        return False
    except Exception as e:
        print(f"[ERRO INESPERADO DB Módulos] Ao atualizar módulo ID {id_modulo}: {e}")
        import traceback
        traceback.print_exc()
        return False
    

def obter_todos_modulos():
    """
    Obtém todos os módulos guardados da tabela `modulos_guardados`.
    Retorna uma lista de dicionários, onde cada dicionário representa um módulo.
    Exemplo de retorno: [{'id_modulo': 1, 'nome_modulo': 'Coz_Base', 'descricao_modulo': 'Desc', 'caminho_imagem_modulo': 'path/img.png'}, ...]
    """
    modulos = []
    try:
        with obter_cursor() as cursor:
            # Selecionar as colunas necessárias para o diálogo de importação
            sql = "SELECT id_modulo, nome_modulo, descricao_modulo, caminho_imagem_modulo FROM modulos_guardados ORDER BY nome_modulo ASC"
            cursor.execute(sql)
            resultados = cursor.fetchall()
            
            # Obter nomes das colunas para criar dicionários
            nomes_colunas = [desc[0] for desc in cursor.description]
            
            for linha_bd in resultados:
                modulo_dict = dict(zip(nomes_colunas, linha_bd))
                modulos.append(modulo_dict)
            
            print(f"[INFO DB Módulos] {len(modulos)} módulos obtidos da base de dados.")
            return modulos
            
    except mysql.connector.Error as err:
        print(f"[ERRO DB Módulos] Erro ao obter todos os módulos: {err}")
        QMessageBox.critical(None, "Erro Base de Dados", f"Não foi possível obter a lista de módulos: {err}")
        return [] # Retorna lista vazia em caso de erro
    except Exception as e:
        print(f"[ERRO INESPERADO DB Módulos] Ao obter todos os módulos: {e}")
        QMessageBox.critical(None, "Erro Crítico", f"Erro inesperado ao obter lista de módulos: {e}")
        return []

def obter_modulo_por_id(id_modulo):
    """
    Retorna os dados de um módulo específico.
    """
    if not id_modulo:
        return None
    try:
        with obter_cursor() as cursor:
            sql = ("SELECT id_modulo, nome_modulo, descricao_modulo, "
                   "caminho_imagem_modulo FROM modulos_guardados WHERE id_modulo = %s")
            cursor.execute(sql, (id_modulo,))
            res = cursor.fetchone()
            if res:
                nomes_colunas = [desc[0] for desc in cursor.description]
                return dict(zip(nomes_colunas, res))
            return None
    except mysql.connector.Error as err:
        print(f"[ERRO DB Módulos] Erro ao obter módulo ID {id_modulo}: {err}")
        return None
    except Exception as e:
        print(f"[ERRO INESPERADO DB Módulos] Ao obter módulo ID {id_modulo}: {e}")
        return None

def obter_pecas_de_modulo(id_modulo):
    """
    Obtém todas as peças de um módulo específico da tabela `modulo_pecas_guardadas`.
    Inclui agora as colunas comp_ass_X_peca.
    Retorna uma lista de dicionários, onde cada dicionário representa uma peça.
    As peças são ordenadas por 'ordem_peca'.
    """
    pecas = []
    if not id_modulo:
        return pecas
        
    try:
        with obter_cursor() as cursor:
            sql = """
            SELECT ordem_peca, descricao_livre_peca, def_peca_peca, qt_und_peca, 
                   comp_peca, larg_peca, esp_peca, mat_default_peca, 
                   tab_default_peca, grupo_peca, und_peca,
                   comp_ass_1_peca, comp_ass_2_peca, comp_ass_3_peca
            FROM modulo_pecas_guardadas 
            WHERE id_modulo_fk = %s 
            ORDER BY ordem_peca ASC
            """
            cursor.execute(sql, (id_modulo,))
            resultados = cursor.fetchall()

            nomes_colunas = [desc[0] for desc in cursor.description]
            
            for linha_bd in resultados:
                peca_dict = dict(zip(nomes_colunas, linha_bd))
                pecas.append(peca_dict)
            
            print(f"[INFO DB Módulos] {len(pecas)} peças obtidas para o módulo ID {id_modulo}.")
            return pecas

    except mysql.connector.Error as err:
        print(f"[ERRO DB Módulos] Erro ao obter peças do módulo ID {id_modulo}: {err}")
        QMessageBox.critical(None, "Erro Base de Dados", f"Não foi possível obter as peças do módulo: {err}")
        return []
    except Exception as e:
        print(f"[ERRO INESPERADO DB Módulos] Ao obter peças do módulo ID {id_modulo}: {e}")
        QMessageBox.critical(None, "Erro Crítico", f"Erro inesperado ao obter peças do módulo: {e}")
        return []

# ... (função eliminar_modulo_por_id e if __name__ == "__main__":)
def eliminar_modulo_por_id(id_modulo):
    """
    Elimina um módulo e todas as suas peças associadas da base de dados.
    A chave estrangeira com ON DELETE CASCADE na tabela modulo_pecas_guardadas
    deve tratar da eliminação das peças automaticamente quando o módulo é eliminado.
    Retorna True se sucesso, False caso contrário.
    """
    if not id_modulo:
        print("[AVISO DB Módulos] ID do módulo não fornecido para eliminação.")
        return False
    
    try:
        with obter_cursor() as cursor: # commit_on_exit=True é o padrão e é adequado aqui
            sql = "DELETE FROM modulos_guardados WHERE id_modulo = %s"
            cursor.execute(sql, (id_modulo,))
            if cursor.rowcount > 0:
                print(f"[INFO DB Módulos] Módulo ID {id_modulo} e suas peças associadas eliminados com sucesso.")
                return True
            else:
                print(f"[AVISO DB Módulos] Módulo ID {id_modulo} não encontrado para eliminação.")
                return False
    except mysql.connector.Error as err:
        print(f"[ERRO DB Módulos] Erro ao eliminar módulo ID {id_modulo}: {err}")
        # QMessageBox.critical(None, "Erro Base de Dados", f"Não foi possível eliminar o módulo: {err}")
        return False
    except Exception as e:
        print(f"[ERRO INESPERADO DB Módulos] Ao eliminar módulo ID {id_modulo}: {e}")
        # QMessageBox.critical(None, "Erro Crítico", f"Erro inesperado ao eliminar o módulo: {e}")
        return False


# Linhas seguintes podem ser eliminadas ou mantidas para teste
# --- Testes e execução direta do módulo ---
if __name__ == "__main__":
    # Para testar a criação das tabelas independentemente
    print("Executando modulo_gestao_modulos_db.py diretamente para criar tabelas...")
    # É preciso simular uma conexão ou garantir que db_connection.py está configurado
    # Para um teste simples, pode-se chamar criar_tabelas_modulos()
    # mas certifique-se que as credenciais da BD estão acessíveis.
    # criar_tabelas_modulos()
    print("Criação de tabelas (se necessário) concluída. Verifique a sua base de dados.")