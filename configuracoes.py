# 28-01-2025
'''configuracoes.py
Funções:
No separador Configurações, este módulo gerencia:
  - A configuração dos caminhos da base de dados e da pasta de orçamentos.
  - A criação da tabela "configuracoes" no banco de dados MySQL.
  - O carregamento e a atualização dessas configurações na interface.
  
Observação:
  As operações de banco de dados utilizam MySQL através da função get_connection() importada
  do módulo "db_connection.py". Certifique-se de que este módulo esteja devidamente configurado.
'''

import os
import mysql.connector # Adicionado para erros específicos
from PyQt5.QtWidgets import QLineEdit, QPushButton, QMessageBox, QTableWidgetItem
# Importa a função de conexão MySQL do módulo de conexão (certifique-se de que db_connection.py esteja configurado)
from db_connection import obter_cursor

# Variável global para armazenar o caminho da base de dados (este campo pode continuar sendo usado para configuração dos caminhos)
#db_path = ""

def set_db_path(line_edit: QLineEdit):
    """
    Atualiza o caminho da base de dados a partir do campo 'lineEdit_base_dados'.
    Embora em MySQL a conexão seja feita via parâmetros, este valor pode ser usado para armazenar
    configurações de caminhos, se necessário.
    """
    # (Código mantido como na resposta anterior)
    db_path_text = line_edit.text().strip() # Usa o texto do lineEdit
    if not db_path_text:
        print("[AVISO] Caminho da base de dados em configurações está vazio.")
        return
    try:
        # Assume que o path é para um diretório ou ficheiro. Se for ficheiro, pega diretório.
        target_path = db_path_text
        if not os.path.isdir(target_path):
             target_path = os.path.dirname(target_path)

        # Garante que o diretório existe
        if target_path and not os.path.exists(target_path):
            os.makedirs(target_path)
            print(f"Diretório criado: {target_path}")
    except Exception as e:
        print(f"Erro ao verificar/criar o diretório base '{db_path_text}': {e}")
        # QMessageBox.warning(None, "Erro de Diretório", f"Não foi possível verificar ou criar o diretório:\n{db_path_text}\n\nErro: {e}")


# Removemos a função get_connection() local, pois agora usamos a importada de db_connection.py

def criar_tabela_configuracoes():
    """
    Cria a tabela 'configuracoes' no banco de dados MySQL, se ainda não existir.
    A tabela possui as colunas:
      - id: chave primária auto-incrementada.
      - caminho_base_dados: texto com o caminho da base de dados.
      - caminho_orcamentos: texto com o caminho da pasta de orçamentos.
    Se não houver configurações salvas, insere valores padrão.
    """
    #print("Verificando/Criando tabela 'configuracoes'...")
    try:
        with obter_cursor() as cursor:
            # Cria a tabela se não existir
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS configuracoes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    caminho_base_dados TEXT NOT NULL,
                    caminho_orcamentos TEXT NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # Verifica se a tabela está vazia
            cursor.execute("SELECT COUNT(*) FROM configuracoes")
            if cursor.fetchone()[0] == 0:
                print("Tabela 'configuracoes' vazia. Inserindo valores padrão...")
                # Insere valores padrão (ajustar caminhos se necessário)
                cursor.execute("""
                    INSERT INTO configuracoes (caminho_base_dados, caminho_orcamentos)
                    VALUES (%s, %s)
                """, (
                    "C:\\Users\\Utilizador\\Documents\\ORCAMENTOS_LE_V2\\Base_Dados_Orcamento\\orcamentos.db", # Exemplo, pode ser apenas o nome do ficheiro
                    "C:\\Users\\Utilizador\\Documents\\ORCAMENTOS_LE_V2\\ORCAMENTOS\\Dep._Orcamentos"  # Exemplo
                ))
                print("Valores padrão inseridos.")
        # Commit automático
        #print("Tabela 'configuracoes' verificada/criada com sucesso.")
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao criar/verificar tabela 'configuracoes': {err}")
        QMessageBox.critical(None, "Erro Crítico BD", f"Falha na tabela 'configuracoes':\n{err}")
    except Exception as e:
        print(f"Erro inesperado ao criar/verificar tabela 'configuracoes': {e}")
        QMessageBox.critical(None, "Erro Crítico", f"Falha na configuração inicial:\n{e}")


def salvar_configuracoes(caminho_base_dados, caminho_orcamentos):
    """
    Atualiza as configurações na tabela 'configuracoes' com os novos valores.
    Utiliza a cláusula LIMIT 1 para atualizar apenas o primeiro registro.
    """
    print(f"Salvando configurações: BD='{caminho_base_dados}', Orc='{caminho_orcamentos}'")
    try:
        with obter_cursor() as cursor:
            # Assume que há sempre apenas uma linha (ou queremos atualizar a primeira)
            # Usar backticks para segurança
            cursor.execute("""
                UPDATE configuracoes
                SET `caminho_base_dados` = %s, `caminho_orcamentos` = %s
                WHERE id = 1 -- Ou outra lógica para identificar a linha a atualizar
            """, (caminho_base_dados, caminho_orcamentos))
            # Commit automático
            if cursor.rowcount > 0:
                 print("Configurações salvas com sucesso.")
                 return True
            else:
                 print("Nenhuma linha de configuração encontrada para atualizar (ID=1). Tentando inserir...")
                 # Se não atualizou (ex: tabela vazia ou id!=1), tenta inserir
                 cursor.execute("""
                     INSERT INTO configuracoes (id, caminho_base_dados, caminho_orcamentos)
                     VALUES (1, %s, %s)
                     ON DUPLICATE KEY UPDATE -- Garante que só há uma linha (se id=1 for PK)
                         caminho_base_dados = VALUES(caminho_base_dados),
                         caminho_orcamentos = VALUES(caminho_orcamentos)
                 """, (caminho_base_dados, caminho_orcamentos))
                 print("Nova linha de configuração inserida/atualizada.")
                 return True

    except mysql.connector.Error as err:
        print(f"Erro MySQL ao salvar configurações: {err}")
        QMessageBox.critical(None, "Erro Base de Dados", f"Erro ao salvar configurações:\n{err}")
        return False
    except Exception as e:
        print(f"Erro inesperado ao salvar configurações: {e}")
        QMessageBox.critical(None, "Erro Inesperado", f"Erro ao salvar configurações:\n{e}")
        return False

# ---------- Novas Funções para valores de máquinas ----------
def criar_tabela_maquinas_producao():
    """Cria tabela com valores de produção se não existir e insere defaults."""
    try:
        with obter_cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS maquinas_producao (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nome_variavel VARCHAR(50) UNIQUE,
                    valor_std DECIMAL(10,2),
                    valor_serie DECIMAL(10,2),
                    descricao TEXT
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            cursor.execute("SELECT COUNT(*) FROM maquinas_producao")
            if cursor.fetchone()[0] == 0:
                dados_padrao = [
                    ("VALOR_SECCIONADORA", 1.0, 0.5, "€/ML para a máquina Seccionadora"),
                    ("VALOR_ORLADORA", 0.70, 0.40, "€/ML para a máquina Orladora"),
                    ("CNC_PRECO_PECA_BAIXO", 2.0, 1.5, "€/peça se AREA_M2_und ≤ 0.7"),
                    ("CNC_PRECO_PECA_MEDIO", 2.5, 2.0, "€/peça se 0.7 < AREA_M2_und < 1"),
                    ("CNC_PRECO_PECA_ALTO", 3.0, 2.5, "€/peça se AREA_M2_und ≥ 1"),
                    ("VALOR_ABD", 0.80, 0.60, "€/peça para a máquina ABD"),
                    ("EUROS_HORA_CNC", 60.0, 48.0, "€/hora para a máquina CNC"),
                    ("EUROS_HORA_PRENSA", 22.0, 17.0, "€/hora para a máquina Prensa"),
                    ("EUROS_HORA_ESQUAD", 20.0, 15.0, "€/hora para a máquina Esquadrejadora"),
                    ("EUROS_EMBALAGEM_M3", 50.0, 35.0, "€/M³ para Embalagem"),
                    ("EUROS_HORA_MO", 22.0, 17.0, "€/hora para Mão de Obra"),
                ]
                cursor.executemany(
                    "INSERT INTO maquinas_producao (nome_variavel, valor_std, valor_serie, descricao) VALUES (%s,%s,%s,%s)",
                    dados_padrao,
                )
    except Exception as e:
        print(f"Erro ao criar tabela maquinas_producao: {e}")


def carregar_dados_maquinas(ui):
    """Carrega dados da tabela para o QTableWidget."""
    try:
        with obter_cursor() as cursor:
            cursor.execute(
                "SELECT nome_variavel, valor_std, valor_serie, descricao FROM maquinas_producao"
            )
            linhas = cursor.fetchall()
        tbl = ui.tableWidget_maquinas
        tbl.setRowCount(len(linhas))
        for r, (nome, std, serie, desc) in enumerate(linhas):
            tbl.setItem(r, 0, QTableWidgetItem(str(nome)))
            tbl.setItem(r, 1, QTableWidgetItem(str(std)))
            tbl.setItem(r, 2, QTableWidgetItem(str(serie)))
            tbl.setItem(r, 3, QTableWidgetItem(desc if desc else ""))
    except Exception as e:
        print(f"Erro ao carregar dados de maquinas: {e}")


def salvar_dados_maquinas(ui):
    """Guarda na base de dados os valores editados pelo utilizador."""
    tbl = ui.tableWidget_maquinas
    try:
        with obter_cursor() as cursor:
            for row in range(tbl.rowCount()):
                nome = tbl.item(row, 0).text() if tbl.item(row, 0) else ""
                std = tbl.item(row, 1).text() if tbl.item(row, 1) else "0"
                serie = tbl.item(row, 2).text() if tbl.item(row, 2) else "0"
                desc = tbl.item(row, 3).text() if tbl.item(row, 3) else ""
                cursor.execute(
                    """
                    INSERT INTO maquinas_producao (nome_variavel, valor_std, valor_serie, descricao)
                    VALUES (%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                        valor_std=VALUES(valor_std),
                        valor_serie=VALUES(valor_serie),
                        descricao=VALUES(descricao)
                    """,
                    (nome, float(std), float(serie), desc),
                )
        print("Valores de produção atualizados.")
        return True
    except Exception as e:
        print(f"Erro ao salvar dados de maquinas: {e}")
        return False
    

def configurar_configuracoes_ui(ui):
    """
    Conecta os campos e botões da interface 'tab_configuracoes' às funcionalidades deste módulo.
    - Atualiza o campo de configuração com os valores armazenados no banco.
    - Conecta o botão para salvar as novas configurações.
    """
    # Atualiza o caminho da base de dados a partir do campo da interface
    #print("[INFO] Configurando UI de Configurações...")
    set_db_path(ui.lineEdit_base_dados)

    def carregar_ui():
        """
        Preenche os campos da interface com os valores das configurações armazenadas no banco.
        """
        #print("Carregando configurações para a UI...")
        caminho_bd = ""
        caminho_orc = ""
        try:
            with obter_cursor() as cursor:
                # Assume que queremos a primeira (e única) linha de configuração
                cursor.execute("SELECT caminho_base_dados, caminho_orcamentos FROM configuracoes LIMIT 1")
                resultado = cursor.fetchone()
                if resultado:
                    caminho_bd = resultado[0] if resultado[0] is not None else ""
                    caminho_orc = resultado[1] if resultado[1] is not None else ""
                    print(f"  Configurações carregadas: BD='{caminho_bd}', Orc='{caminho_orc}'")
                else:
                     print("  Nenhuma configuração encontrada na BD.")
                     # Pode definir valores padrão aqui se desejar
                     # caminho_bd = "Caminho\\Padrao\\BD"
                     # caminho_orc = "Caminho\\Padrao\\Orcamentos"

            # Atualiza a UI fora do bloco 'with'
            ui.lineEdit_base_dados.setText(caminho_bd)
            ui.lineEdit_orcamentos.setText(caminho_orc)
            # Atualiza o caminho usado por set_db_path (valida/cria diretório)
            set_db_path(ui.lineEdit_base_dados)

        except mysql.connector.Error as err:
            print(f"Erro MySQL ao carregar configurações para UI: {err}")
            QMessageBox.warning(None, "Erro BD", f"Não foi possível carregar configurações:\n{err}")
        except Exception as e:
            print(f"Erro inesperado ao carregar configurações para UI: {e}")
            QMessageBox.warning(None, "Erro", f"Falha ao carregar configurações:\n{e}")

    def atualizar_configuracoes():
        """
        Atualiza as configurações no banco de dados conforme os valores editados pelo usuário.
        Valida que os campos não estejam vazios e, em seguida, salva os novos caminhos.
        """
        caminho_base_dados = ui.lineEdit_base_dados.text().strip()
        caminho_orcamentos = ui.lineEdit_orcamentos.text().strip()

        if not caminho_base_dados or not caminho_orcamentos:
            QMessageBox.warning(None, "Erro", "Os caminhos não podem estar vazios.")
            return

        # Chama a função refatorada para salvar
        if salvar_configuracoes(caminho_base_dados, caminho_orcamentos):
            set_db_path(ui.lineEdit_base_dados) # Atualiza caminho/cria pasta se necessário
            QMessageBox.information(None, "Sucesso", "Configurações atualizadas com sucesso.")
        # A função salvar_configuracoes já mostra mensagem de erro se falhar

    # --- Inicialização ---
    # 1. Garante que a tabela existe (e insere defaults se for nova)
    criar_tabela_configuracoes()  # Já usa obter_cursor
    criar_tabela_maquinas_producao()
    # 2. Carrega os dados da BD para a UI
    carregar_ui()  # Esta função interna foi refatorada para usar obter_cursor
    carregar_dados_maquinas(ui)

    # 3. Conecta os botões
    ui.pushButton_atualiza_configuracoes.clicked.connect(atualizar_configuracoes)
    ui.pushButton_gravar_producao.clicked.connect(lambda: salvar_dados_maquinas(ui))

    #print("[INFO] UI de Configurações configurada.")
