# 26-01-2025
'''clientes.py
Funções:
  - Criação da tabela "clientes" com os campos necessários no banco de dados MySQL.
  - Inserir, editar e eliminar registros na tabela de clientes.
  - Listar e pesquisar registros de clientes.
  - Conectar os componentes da interface do separador "Clientes" às funcionalidades do banco.
  
Observação:
  Este módulo utiliza MySQL para todas as operações de banco de dados, por meio da função
  get_connection() importada do módulo "db_connection.py". Certifique-se de que o módulo de conexão esteja devidamente configurado.
'''

import os
import datetime
import mysql.connector # Adicionado para erros específicos
from PyQt5.QtWidgets import QLineEdit, QPushButton, QMessageBox, QTableWidget, QTableWidgetItem, QGroupBox, QAbstractItemView
from PyQt5.QtCore import Qt
from utils import atualizar_campos_para_novo_orcamento, limpar_dados_cliente, limpar_campos_orcamento
# Importa a função de conexão MySQL; não é necessário definir get_connection localmente
from db_connection import obter_cursor

# Variável global para armazenar o caminho da base de dados (para fins de configuração, se necessário)
#db_path = ""

def set_db_path(line_edit: QLineEdit):
    """
    Atualiza o caminho da base de dados a partir do campo 'lineEdit_base_dados'.
    Embora a conexão com MySQL não dependa de um arquivo, este valor pode ser usado para referência.
    """
    db_path_text = line_edit.text().strip()
    if not db_path_text: return
    try:
        target_path = db_path_text
        if not os.path.isdir(target_path): target_path = os.path.dirname(target_path)
        if target_path and not os.path.exists(target_path):
            os.makedirs(target_path); print(f"Diretório criado: {target_path}")
    except Exception as e: print(f"Erro ao verificar/criar diretório '{db_path_text}': {e}")

def criar_tabela_clientes():
    """
    Cria a tabela 'clientes' no banco de dados MySQL, se ainda não existir.
    A tabela possui os campos:
      - id: chave primária auto-incrementada.
      - nome, nome_simplex, morada, email, pagina_web, numero_cliente_phc, info_1, info_2, telefone e telemovel.
    """
    #print("Verificando/Criando tabela 'clientes'...")
    try:
        with obter_cursor() as cursor:
            # Adicionar NOT NULL e DEFAULT onde apropriado
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clientes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nome TEXT NOT NULL, -- Nome principal é obrigatório
                    nome_simplex TEXT NULL,
                    morada TEXT NULL,
                    email TEXT NULL,
                    pagina_web TEXT NULL,
                    numero_cliente_phc VARCHAR(50) NULL, -- Aumentado tamanho
                    info_1 TEXT NULL,
                    info_2 TEXT NULL,
                    telefone VARCHAR(50) NULL, -- Aumentado tamanho
                    telemovel VARCHAR(50) NULL, -- Aumentado tamanho
                    INDEX idx_nome_cliente (nome(255)), -- Índice em parte do campo TEXT
                    INDEX idx_nome_simplex (nome_simplex(255))
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
        # Commit automático
        #print("Tabela 'clientes' verificada/criada.")
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao criar/verificar tabela 'clientes': {err}")
        QMessageBox.critical(None, "Erro Crítico BD", f"Falha na tabela 'clientes':\n{err}")
    except Exception as e:
        print(f"Erro inesperado ao criar/verificar tabela 'clientes': {e}")
        QMessageBox.critical(None, "Erro Crítico", f"Falha na configuração inicial:\n{e}")

def listar_clientes():
    """
    Retorna uma lista de todos os registros da tabela 'clientes'.
    """
    #print("Listando todos os clientes...")
    clientes = []
    try:
        with obter_cursor() as cursor:
            cursor.execute("SELECT * FROM clientes ORDER BY nome") # Ordena por nome
            clientes = cursor.fetchall()
        #print(f"Encontrados {len(clientes)} clientes.")
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao listar clientes: {err}")
        QMessageBox.warning(None, "Erro BD", f"Não foi possível listar clientes:\n{err}")
    except Exception as e:
        print(f"Erro inesperado ao listar clientes: {e}")
        QMessageBox.warning(None, "Erro", f"Falha ao listar clientes:\n{e}")
    return clientes

def pesquisar_clientes(termos):
    """
    Pesquisa clientes na tabela com base em múltiplos termos (separados por '%').
    Os termos são aplicados a várias colunas (nome, nome_simplex, morada, email, etc.).
    
    Parâmetros:
      termos: lista de termos para pesquisa.
      
    Retorna:
      Uma lista de registros que correspondem aos termos de pesquisa.
    """
    registros = []
    if not termos or all(not t.strip() for t in termos):
        print("Nenhum termo de pesquisa de cliente fornecido."); return registros

    print(f"Pesquisando clientes por termos: {termos}")
    
    try:
        with obter_cursor() as cursor:
            colunas_pesquisa = [ # Colunas onde pesquisar
                "nome", "nome_simplex", "morada", "email", "pagina_web",
                "numero_cliente_phc", "info_1", "info_2", "telefone", "telemovel"
            ]
            where_clauses = []
            parametros = []
            for termo in termos:
                termo_like = f"%{termo.strip()}%"
                clausulas_termo = [f"LOWER(`{col}`) LIKE LOWER(%s)" for col in colunas_pesquisa]
                where_clauses.append(f"({' OR '.join(clausulas_termo)})")
                parametros.extend([termo_like] * len(colunas_pesquisa))

            where_final = " AND ".join(where_clauses)
            query = f"SELECT * FROM clientes WHERE {where_final} ORDER BY nome"

            cursor.execute(query, parametros)
            registros = cursor.fetchall()
            print(f"Pesquisa de clientes encontrou {len(registros)} registos.")
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao pesquisar clientes: {err}")
        QMessageBox.warning(None, "Erro Pesquisa", f"Erro na pesquisa de clientes:\n{err}")
    except Exception as e:
        print(f"Erro inesperado ao pesquisar clientes: {e}")
        QMessageBox.warning(None, "Erro Pesquisa", f"Erro inesperado na pesquisa:\n{e}")
    return registros



def inserir_cliente(nome, nome_simplex, morada, email, pagina_web, numero_cliente_phc, info_1, info_2, telefone, telemovel):
    """
    Insere um novo registro na tabela 'clientes' com os dados fornecidos.
    """
    if not nome: # Nome é obrigatório (NOT NULL na tabela)
        QMessageBox.warning(None, "Erro", "O campo 'Nome' do cliente é obrigatório.")
        return False
    print(f"Inserindo cliente: {nome}")
    try:
        with obter_cursor() as cursor:
            insert_query = """
                INSERT INTO clientes (nome, nome_simplex, morada, email, pagina_web,
                                      numero_cliente_phc, info_1, info_2, telefone, telemovel)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (
                nome, nome_simplex, morada, email, pagina_web, numero_cliente_phc,
                info_1, info_2, telefone, telemovel))
        # Commit automático
        print("Cliente inserido com sucesso.")
        return True
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao inserir cliente: {err}")
        QMessageBox.critical(None, "Erro Base de Dados", f"Erro ao inserir cliente:\n{err}")
        return False
    except Exception as e:
        print(f"Erro inesperado ao inserir cliente: {e}")
        QMessageBox.critical(None, "Erro Inesperado", f"Erro ao inserir cliente:\n{e}")
        return False

"""
    def transportar_dados_cliente_orcamento(ui):
        
        Transfere os dados do cliente selecionado na aba de Clientes para os campos do orçamento.
        Realiza:
        1) Limpeza dos campos do orçamento.
        2) Atualização dos campos para um novo orçamento (geração de ID, número, etc.).
        3) Preenchimento dos campos de ID e nome do cliente no separador de Consulta de Orçamentos.
        4) Mudança automática para a aba de Consulta de Orçamentos.
        
        try:
            limpar_campos_orcamento(ui)
            atualizar_campos_para_novo_orcamento(ui, get_connection)
            id_cliente_str = ui.lineEdit_idCliente.text().strip()
            nome_simplex = ui.lineEdit_nome_cliente_simplex.text().strip()
            # Atribui o ID do cliente (supondo que ui.lineEdit_idCliente_noOrc já esteja acessível)
            ui.lineEdit_idCliente_noOrc.setText(id_cliente_str)
            ui.lineEdit_nome_cliente_2.setText(nome_simplex)
            
            ui.tabWidget_orcamento.setCurrentIndex(3)  # Muda para o separador de orçamentos
        except Exception as e:
            print(f"Erro ao transferir dados: {e}")
"""
def editar_cliente(cliente_id, nome, nome_simplex, morada, email, pagina_web, numero_cliente_phc, info_1, info_2, telefone, telemovel):
    """
    Atualiza os dados de um cliente existente na tabela 'clientes'.
    """
    if not nome:
        QMessageBox.warning(None, "Erro", "O campo 'Nome' do cliente é obrigatório.")
        return False
    if not cliente_id: # Precisa do ID para saber quem editar
         QMessageBox.warning(None, "Erro", "ID do cliente inválido para edição.")
         return False
    print(f"Editando cliente ID: {cliente_id}")
    try:
        with obter_cursor() as cursor:
            update_query = """
                UPDATE clientes
                SET nome = %s, nome_simplex = %s, morada = %s, email = %s, pagina_web = %s,
                    numero_cliente_phc = %s, info_1 = %s, info_2 = %s, telefone = %s, telemovel = %s
                WHERE id = %s
            """
            cursor.execute(update_query, (
                nome, nome_simplex, morada, email, pagina_web, numero_cliente_phc,
                info_1, info_2, telefone, telemovel, cliente_id))
        # Commit automático
        print("Cliente editado com sucesso.")
        return True
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao editar cliente: {err}")
        QMessageBox.critical(None, "Erro Base de Dados", f"Erro ao editar cliente:\n{err}")
        return False
    except Exception as e:
        print(f"Erro inesperado ao editar cliente: {e}")
        QMessageBox.critical(None, "Erro Inesperado", f"Erro ao editar cliente:\n{e}")
        return False

def eliminar_cliente(cliente_id):
    """
    Elimina o cliente com o ID fornecido da tabela 'clientes'.
    """
    if not cliente_id:
        QMessageBox.warning(None, "Erro", "ID do cliente inválido para eliminação.")
        return False
    print(f"Eliminando cliente ID: {cliente_id}")
    try:
        with obter_cursor() as cursor:
            # IMPORTANTE: Verificar se há orçamentos associados antes de apagar,
            # devido à restrição FOREIGN KEY (ON DELETE RESTRICT).
            cursor.execute("SELECT COUNT(*) FROM orcamentos WHERE id_cliente = %s", (cliente_id,))
            count_orc = cursor.fetchone()[0]
            if count_orc > 0:
                 QMessageBox.warning(None, "Erro ao Eliminar",
                                     f"Não é possível eliminar este cliente (ID: {cliente_id}) "
                                     f"porque existem {count_orc} orçamento(s) associado(s) a ele.\n"
                                     "Elimine ou reatribua os orçamentos primeiro.")
                 return False

            # Se não houver orçamentos, pode apagar o cliente
            cursor.execute("DELETE FROM clientes WHERE id = %s", (cliente_id,))
            rows_affected = cursor.rowcount
        # Commit automático
        if rows_affected > 0:
             print("Cliente eliminado com sucesso.")
             return True
        else:
             print("Nenhum cliente encontrado com esse ID para eliminar.")
             return False # Ou True se não encontrar não for um erro?
    except mysql.connector.Error as err:
        # Captura outros erros potenciais (ex: restrições FK se ON DELETE RESTRICT falhar por outra razão)
        print(f"Erro MySQL ao eliminar cliente: {err}")
        QMessageBox.critical(None, "Erro Base de Dados", f"Erro ao eliminar cliente:\n{err}")
        return False
    except Exception as e:
        print(f"Erro inesperado ao eliminar cliente: {e}")
        QMessageBox.critical(None, "Erro Inesperado", f"Erro ao eliminar cliente:\n{e}")
        return False

def preencher_tabela_clientes(tabela: QTableWidget, clientes):
    """
    Preenche o QTableWidget com os dados dos clientes.
    
    Parâmetros:
      tabela: objeto QTableWidget a ser preenchido.
      clientes: lista de registros obtida do banco de dados.
    """
    tabela.setRowCount(0)
    for cliente in clientes:
        row_position = tabela.rowCount()
        tabela.insertRow(row_position)
        for column, data in enumerate(cliente):
            item = QTableWidgetItem(str(data) if data is not None else "") # Trata None
            # Tornar coluna ID (0) não editável
            if column == 0:
                 item.setFlags(item.flags() & Qt.ItemIsEditable)
            tabela.setItem(row_position, column, item)

# Função transportar_dados_cliente_orcamento foi movida para orcamentos.py
# pois lida principalmente com a UI de orçamentos. Vamos removê-la daqui.
# def transportar_dados_cliente_orcamento(ui): ... REMOVIDO
def conectar_clientes_ui(ui):
    """
    Conecta os componentes da interface do separador Clientes às funções do banco de dados.
    - Carrega os dados iniciais na tabela de clientes.
    - Conecta os botões de inserir, editar, eliminar e pesquisa.
    """
    def carregar_dados_iniciais():
        try:
            clientes = listar_clientes()
            preencher_tabela_clientes(ui.tableWidget_tabela_clientes, clientes)
            # Ajusta larguras das colunas
            ui.tableWidget_tabela_clientes.setColumnWidth(0, 50)   # ID
            ui.tableWidget_tabela_clientes.setColumnWidth(1, 250)  # Nome Cliente
            ui.tableWidget_tabela_clientes.setColumnWidth(2, 230)  # Nome Cliente Simplex
            ui.tableWidget_tabela_clientes.setColumnWidth(3, 300)  # Morada
            ui.tableWidget_tabela_clientes.setColumnWidth(4, 250)  # Email
            ui.tableWidget_tabela_clientes.setColumnWidth(5, 200)  # Página Web
            ui.tableWidget_tabela_clientes.setColumnWidth(6, 80)   # Número Cliente PHC
            ui.tableWidget_tabela_clientes.setColumnWidth(7, 250)  # Info_1
            ui.tableWidget_tabela_clientes.setColumnWidth(8, 250)  # Info_2
            ui.tableWidget_tabela_clientes.setColumnWidth(9, 90)   # Telefone
            ui.tableWidget_tabela_clientes.setColumnWidth(10, 90)  # Telemovel
        except Exception as e:
            print(f"Erro ao carregar os dados iniciais: {e}")

    def atualizar_campos_por_selecao():
        """
        Quando uma linha na tabela de clientes é selecionada, preenche os campos de edição com os dados dessa linha.
        """
        linha_selecionada = ui.tableWidget_tabela_clientes.currentRow()
        if linha_selecionada >= 0:
            id_cliente = ui.tableWidget_tabela_clientes.item(linha_selecionada, 0).text()
            nome = ui.tableWidget_tabela_clientes.item(linha_selecionada, 1).text()
            nome_simplex = ui.tableWidget_tabela_clientes.item(linha_selecionada, 2).text()
            morada = ui.tableWidget_tabela_clientes.item(linha_selecionada, 3).text()
            email = ui.tableWidget_tabela_clientes.item(linha_selecionada, 4).text()
            pagina_web = ui.tableWidget_tabela_clientes.item(linha_selecionada, 5).text()
            numero_phc = ui.tableWidget_tabela_clientes.item(linha_selecionada, 6).text()
            info_1 = ui.tableWidget_tabela_clientes.item(linha_selecionada, 7).text()
            info_2 = ui.tableWidget_tabela_clientes.item(linha_selecionada, 8).text()
            telefone = ui.tableWidget_tabela_clientes.item(linha_selecionada, 9).text()
            telemovel = ui.tableWidget_tabela_clientes.item(linha_selecionada, 10).text()

            ui.lineEdit_idCliente.setText(id_cliente)
            ui.lineEdit_nome_cliente.setText(nome)
            ui.lineEdit_nome_cliente_simplex.setText(nome_simplex)
            ui.lineEdit_morada_cliente.setText(morada)
            ui.lineEdit_email_cliente.setText(email)
            ui.lineEdit_pagina_web.setText(pagina_web)
            ui.lineEdit_num_cliente_phc.setText(numero_phc)
            ui.lineEdit_info_1.setText(info_1)
            ui.lineEdit_info_2.setText(info_2)
            ui.lineEdit_telefone.setText(telefone)
            ui.lineEdit_telemovel.setText(telemovel)

    def inserir():
        """Slot para o botão Inserir."""
        print("Botão Inserir Cliente clicado.")
        nome = ui.lineEdit_nome_cliente.text().strip()
        # Validação do nome (obrigatório)
        if not nome: QMessageBox.warning(None,"Aviso", "O campo 'Nome' é obrigatório!"); return

        # Chama a função refatorada inserir_cliente
        if inserir_cliente(
            nome, ui.lineEdit_nome_cliente_simplex.text().strip(), ui.lineEdit_morada_cliente.text().strip(),
            ui.lineEdit_email_cliente.text().strip(), ui.lineEdit_pagina_web.text().strip(),
            ui.lineEdit_num_cliente_phc.text().strip(), ui.lineEdit_info_1.text().strip(),
            ui.lineEdit_info_2.text().strip(), ui.lineEdit_telefone.text().strip(), ui.lineEdit_telemovel.text().strip()
        ):
            carregar_dados_iniciais() # Recarrega a tabela
            QMessageBox.information(None, "Sucesso", "Cliente inserido com sucesso.")
            limpar_dados_cliente(ui) # Limpa os campos

    def editar():
        """Slot para o botão Editar."""
        print("Botão Editar Cliente clicado.")
        linha_selecionada = ui.tableWidget_tabela_clientes.currentRow()
        if linha_selecionada >= 0:
            cliente_id_item = ui.tableWidget_tabela_clientes.item(linha_selecionada, 0)
            if not cliente_id_item or not cliente_id_item.text().isdigit():
                QMessageBox.warning(None, "Erro", "Selecione um cliente válido para editar (ID não encontrado).")
                return
            cliente_id = int(cliente_id_item.text())
            nome = ui.lineEdit_nome_cliente.text().strip()
            if not nome: QMessageBox.warning(None,"Aviso", "O campo 'Nome' é obrigatório!"); return

            # Chama a função refatorada editar_cliente
            if editar_cliente(
                cliente_id, nome, ui.lineEdit_nome_cliente_simplex.text().strip(), ui.lineEdit_morada_cliente.text().strip(),
                ui.lineEdit_email_cliente.text().strip(), ui.lineEdit_pagina_web.text().strip(),
                ui.lineEdit_num_cliente_phc.text().strip(), ui.lineEdit_info_1.text().strip(),
                ui.lineEdit_info_2.text().strip(), ui.lineEdit_telefone.text().strip(), ui.lineEdit_telemovel.text().strip()
            ):
                carregar_dados_iniciais()
                QMessageBox.information(None, "Sucesso", "Cliente atualizado com sucesso.")
                # Não limpar campos após editar, para visualização
        else:
            QMessageBox.warning(None, "Erro", "Nenhuma linha selecionada para editar.")

    def eliminar():
        """Slot para o botão Eliminar."""
        print("Botão Eliminar Cliente clicado.")
        linha_selecionada = ui.tableWidget_tabela_clientes.currentRow()
        if linha_selecionada >= 0:
            cliente_id_item = ui.tableWidget_tabela_clientes.item(linha_selecionada, 0)
            if not cliente_id_item or not cliente_id_item.text().isdigit():
                QMessageBox.warning(None, "Erro", "Selecione um cliente válido para eliminar (ID não encontrado).")
                return
            cliente_id = int(cliente_id_item.text())

            resposta = QMessageBox.question(None, "Confirmar Eliminação",
                                            f"Tem a certeza que deseja eliminar o cliente ID {cliente_id}?",
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if resposta == QMessageBox.Yes:
                # Chama a função refatorada eliminar_cliente
                if eliminar_cliente(cliente_id):
                    carregar_dados_iniciais()
                    QMessageBox.information(None, "Sucesso", "Cliente eliminado com sucesso.")
                    limpar_dados_cliente(ui) # Limpa campos após eliminar
                # A função eliminar_cliente já mostra mensagens de erro se falhar
        else:
            QMessageBox.warning(None, "Erro", "Nenhuma linha selecionada para eliminar.")

    def pesquisar():
        """Slot para pesquisar clientes."""
        termos_str = ui.lineEdit_pesquisar_cliente.text().strip()
        termos = [t for t in termos_str.split('%') if t.strip()]
        if termos:
            print(f"Pesquisando clientes por termos: {termos}")
            clientes = pesquisar_clientes(termos) # Chama a função refatorada
            preencher_tabela_clientes(ui.tableWidget_tabela_clientes, clientes)
        else:
            carregar_dados_iniciais() # Recarrega tudo se pesquisa vazia

    def limpar_pesquisa():
        """Slot para limpar pesquisa quando texto muda para vazio."""
        if not ui.lineEdit_pesquisar_cliente.text().strip():
            carregar_dados_iniciais()

    # --- Conexão dos Sinais aos Slots ---
    try:
        # Garante que a tabela existe
        criar_tabela_clientes() # Já usa obter_cursor
        # Carrega dados iniciais
        carregar_dados_iniciais()

        # Botões
        ui.pushButton_inserir_cliente.clicked.connect(inserir)
        # A ligação para transportar dados deve estar no módulo que lida com a aba de orçamentos
        # ui.pushButton_tranpordados_cliente_orcamento.clicked.connect(lambda: transportar_dados_cliente_orcamento(ui)) # Removido daqui
        ui.pushButton_editar_cliente.clicked.connect(editar)
        ui.pushButton_eliminar_cliente.clicked.connect(eliminar)
        ui.pushButton_limpar_dados_cliente.clicked.connect(lambda: limpar_dados_cliente(ui))

        # Tabela e Pesquisa
        ui.tableWidget_tabela_clientes.itemSelectionChanged.connect(atualizar_campos_por_selecao)
        ui.lineEdit_pesquisar_cliente.returnPressed.connect(pesquisar)
        ui.lineEdit_pesquisar_cliente.textChanged.connect(limpar_pesquisa)

        # Configuração inicial da UI
        ui.lineEdit_idCliente.setReadOnly(True) # ID é gerado automaticamente

        #print("[INFO] Conexões da UI Clientes configuradas.")

    except Exception as e:
        print(f"[ERRO FATAL] Erro ao conectar UI de Clientes: {e}")
        QMessageBox.critical(None, "Erro de Inicialização", f"Falha grave ao configurar a secção de Clientes:\n{e}")
        import traceback
        traceback.print_exc()

