"""
dados_gerais_base.py
====================
Módulo base para manipulação das tabelas de Dados Gerais.
Contém funções comuns para:
  - Criar a tabela no banco de dados para um determinado tipo de dados gerais.
  - Configurar o QTableWidget para exibir os dados.
  - Obter valores distintos de uma coluna (usado para preencher combobox).
  
Observação:
  Este módulo utiliza MySQL para todas as operações de banco de dados, através da função
  get_connection() importada do módulo "orcamentos" (ou "db_connection.py"). Certifique-se de que
  o módulo de conexão esteja devidamente configurado para conectar ao seu servidor MySQL.
"""

import mysql.connector # Adicionado para erros específicos
from PyQt5.QtWidgets import QTableWidgetItem, QComboBox, QPushButton, QMessageBox, QHeaderView, QTableWidget,QAbstractItemView
from PyQt5.QtCore import Qt
from orcamentos import obter_cursor

def criar_tabela_dados_gerais(nome_tabela, colunas, linhas):
    """
    Cria (se não existir) a tabela no banco de dados para os dados gerais.
    A tabela terá o nome 'dados_gerais_<nome_tabela>' e conterá:
      - id: chave primária auto-increment (usando MySQL).
      - nome: nome do modelo salvo.
      - linha: índice da linha (de 0 a len(linhas)-1).
      - As colunas definidas em 'colunas'.
      - Uma restrição UNIQUE para (nome, linha).
      
    Parâmetros:
      nome_tabela: identificador (ex.: "materiais").
      colunas: lista de dicionários com a definição de cada coluna (nome, tipo, etc.).
      linhas: lista de nomes para cada linha.
    """
    tabela_bd_segura = f"dados_gerais_{nome_tabela.replace(' ', '_').lower()}"
    #print(f"Verificando/Criando tabela '{tabela_bd_segura}'...")

    try:
        with obter_cursor() as cursor:
            # Verifica se a tabela já existe
            cursor.execute(f"SHOW TABLES LIKE '{tabela_bd_segura}'")
            if not cursor.fetchone():
                # Monta a definição das colunas a partir da lista 'colunas'
                # Ignora a primeira coluna ('material' ou similar, que é o nome da linha na UI)
                # e colunas que são apenas botões ou não armazenáveis diretamente.
                sql_colunas_list = []
                for col in colunas:
                    # Pula a coluna de nome de linha e colunas de botão
                    if col['nome'] == nome_tabela or col.get('botao'):
                        continue # Pula para a próxima coluna na lista 'colunas'

                    # --- Bloco Corrigido (Unindent) ---
                    # Adapta tipos Python/SQLite para tipos MySQL comuns
                    tipo_sql = "TEXT NULL" # Default
                    tipo_orig = col.get('tipo', 'TEXT').upper()
                    if tipo_orig == 'REAL': tipo_sql = "DOUBLE NULL DEFAULT 0.0"
                    elif tipo_orig == 'INTEGER': tipo_sql = "INT NULL"
                    elif tipo_orig == 'TEXT': tipo_sql = "TEXT NULL"
                    elif tipo_orig == 'VARCHAR': tipo_sql = "VARCHAR(255) NULL"
                    # Adiciona backticks ao nome da coluna
                    sql_colunas_list.append(f"`{col['nome']}` {tipo_sql}")
                    # --- Fim do Bloco Corrigido ---

                sql_colunas = ",\n".join(sql_colunas_list)

                # Query CREATE TABLE com colunas dinâmicas, nome, linha e UNIQUE KEY
                sql_create = f"""
                CREATE TABLE IF NOT EXISTS `{tabela_bd_segura}` (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nome VARCHAR(255) NOT NULL, -- Nome do modelo salvo
                    descricao_modelo TEXT NULL,
                    linha INT NOT NULL,         -- Índice da linha original (0 a N-1)
                    {sql_colunas},
                    UNIQUE KEY idx_nome_linha (nome, linha), -- Garante unicidade por modelo/linha
                    INDEX idx_nome (nome) -- Índice para buscar por nome
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
                # print(f"[DEBUG CREATE QUERY]:\n{sql_create}") # Descomentar para depurar a query
                cursor.execute(sql_create)
                print(f"Tabela '{tabela_bd_segura}' criada com sucesso.")
            else:
                print(f"Tabela '{tabela_bd_segura}' já existe.")  # Ao remover este print dá erro de commit Como remover esta linha?
                # Garante que a nova coluna 'descricao_modelo' esteja presente
                cursor.execute(
                    f"SHOW COLUMNS FROM `{tabela_bd_segura}` LIKE 'descricao_modelo'"
                )
                if not cursor.fetchone():
                    try:
                        cursor.execute(
                            f"ALTER TABLE `{tabela_bd_segura}` ADD COLUMN descricao_modelo TEXT NULL AFTER nome"
                        )
                        print(
                            f"Coluna 'descricao_modelo' adicionada à '{tabela_bd_segura}'."
                        )
                    except mysql.connector.Error as alter_err:
                        print(
                            f"Erro ao adicionar coluna descricao_modelo: {alter_err}"
                        )
        # Commit automático

    except mysql.connector.Error as err:
        print(f"Erro MySQL ao criar/verificar tabela '{tabela_bd_segura}': {err}")
        QMessageBox.critical(None, "Erro Base de Dados", f"Falha ao criar/verificar tabela '{tabela_bd_segura}':\n{err}")
    except Exception as e:
        print(f"Erro inesperado ao criar/verificar tabela '{tabela_bd_segura}': {e}")
        QMessageBox.critical(None, "Erro Inesperado", f"Falha na configuração da tabela '{tabela_bd_segura}':\n{e}")


def configurar_tabela_dados_gerais_ui(ui, nome_tabela, colunas, linhas):
    """
    Configura o QTableWidget para exibir os dados gerais de um determinado tipo.
    
    Parâmetros:
      ui: objeto da interface (criado no Qt Designer).
      nome_tabela: identificador (ex.: "materiais").
      colunas: lista com as definições de cada coluna.
      linhas: lista com os nomes de cada linha (ex.: "Mat_Costas", etc.).
    
    Este método pressupõe que no ui existam widgets nomeados:
      - Tab_Material (para "materiais")
      - Tab_Ferragens, Tab_Sistemas_Correr, Tab_Acabamentos, etc.
    """
    # Mapeamento nome_tabela -> nome do widget na UI
    widget_map = {
        "materiais": "Tab_Material",
        "ferragens": "Tab_Ferragens",
        "sistemas_correr": "Tab_Sistemas_Correr",
        "acabamentos": "Tab_Acabamentos"
    }
    widget_name = widget_map.get(nome_tabela)
    if not widget_name or not hasattr(ui, widget_name):
        print(f"Erro: Widget '{widget_name}' não encontrado na UI para tabela '{nome_tabela}'.")
        # Pode retornar None ou levantar uma exceção mais específica
        return None

    table_widget = getattr(ui, widget_name)
    table_widget.clear()

    num_cols = len(colunas)
    num_rows = len(linhas)
    table_widget.setColumnCount(num_cols)
    table_widget.setRowCount(num_rows)

    headers = [col['nome'] for col in colunas]
    table_widget.setHorizontalHeaderLabels(headers)
    table_widget.verticalHeader().setVisible(False)
    # Selecionar linhas completas para melhor visualização
    table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)

    # Configura cada coluna
    for col_idx, col_def in enumerate(colunas):
        for row_idx in range(num_rows):
            # Insere ComboBox se definido
            if col_def.get('combobox'):
                combo = QComboBox()
                combo.setEditable(True) # Permite digitação/autocompletar
                opcoes_func = col_def.get('opcoes')
                opcoes = []
                if callable(opcoes_func):
                    try:
                        # Chama a função lambda/função (que deve usar obter_cursor)
                        opcoes = opcoes_func()
                    except Exception as e:
                        print(f"Erro ao obter opções para ComboBox ({nome_tabela}, col {col_idx}): {e}")
                elif isinstance(opcoes_func, list): # Aceita lista estática também
                    opcoes = opcoes_func

                if opcoes: # Só adiciona se houver opções
                    combo.addItems(opcoes)
                # Define um item vazio ou placeholder inicial?
                combo.insertItem(0, "") # Adiciona item vazio no topo
                combo.setCurrentIndex(0) # Define o item vazio como padrão
                table_widget.setCellWidget(row_idx, col_idx, combo)

            # Insere Botão se definido
            elif col_def.get('botao'):
                btn = QPushButton(col_def.get('texto_botao', '...'))
                funcao_botao = col_def.get('funcao_botao')
                if callable(funcao_botao):
                    # Conecta o botão, passando ui, linha e nome da tabela
                    # Usa lambda para capturar corretamente o valor de row_idx no momento da criação
                    btn.clicked.connect(lambda checked, r=row_idx, nt=nome_tabela, fn=funcao_botao: fn(ui, r, nt))
                table_widget.setCellWidget(row_idx, col_idx, btn)

            # Caso contrário, cria um QTableWidgetItem
            else:
                item = QTableWidgetItem("") # Cria item vazio por padrão
                # Define se a célula é editável
                if not col_def.get('editavel', True):
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                table_widget.setItem(row_idx, col_idx, item)

    # Preenche a primeira coluna com os nomes das linhas
    for row_idx, nome_linha in enumerate(linhas):
        item_linha = QTableWidgetItem(nome_linha)
        # Torna a primeira coluna (nomes das linhas) não editável
        item_linha.setFlags(item_linha.flags() & ~Qt.ItemIsEditable)
        table_widget.setItem(row_idx, 0, item_linha)

    # Ajuste final das colunas (pode ser feito no módulo específico)
    # table_widget.resizeColumnsToContents() # Ajuste inicial
    # table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch) # Ou Interactive

    return table_widget

def get_distinct_values(col_name):
    """
    Retorna os valores distintos da coluna 'col_name' da tabela materias_primas.
    Esses valores são úteis para preencher os QComboBox.
    """
    values = []
    # Validação básica do nome da coluna
    allowed_cols = {"tipo", "familia", "ref_le", "descricao", "material", "und", "cor"} # Expandir conforme necessário
    col_name_safe = col_name.strip('`').lower()
    if col_name_safe not in allowed_cols:
        print(f"[ERRO] Tentativa de usar coluna não permitida em get_distinct_values: {col_name}")
        return values

    # Query SQL usando backticks e placeholders (embora não haja placeholders aqui)
    query = f"""
        SELECT DISTINCT `{col_name_safe}`
        FROM materias_primas
        WHERE `{col_name_safe}` IS NOT NULL AND `{col_name_safe}` <> ''
        ORDER BY `{col_name_safe}`
    """
    try:
        # Usa o gestor de contexto
        with obter_cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
            values = [row[0] for row in results]
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao obter valores distintos para '{col_name}': {err}")
    except Exception as e:
        print(f"Erro inesperado ao obter valores distintos para '{col_name}': {e}")
    return values
