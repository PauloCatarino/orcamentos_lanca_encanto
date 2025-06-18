# 27-01-2025
# Funçoes e funcionalidades  do separador Consulta Orcamentos
#_______________________________________///___________________________________________
"""
orcamentos.py
=============
Módulo responsável pelas funcionalidades do separador "Consulta Orçamentos".
Neste módulo são criadas funções para:
 - Criação da tabela de orçamentos no MySQL (caso não exista)
 - Inserção, edição, pesquisa e exclusão de orçamentos
 - Atualização e formatação dos dados exibidos na interface (QT)
 - Criação de pastas no servidor para armazenar arquivos de orçamento

OBSERVAÇÃO:
Este código utiliza a função get_connection() importada de um módulo (por exemplo, db_connection.py)
que deve retornar uma conexão MySQL configurada (host, usuário, senha, base de dados).
"""

import os
import pandas as pd
from openpyxl import load_workbook
import datetime
import re
import mysql.connector # Importar para capturar erros específicos
from PyQt5.QtWidgets import (QLineEdit, QTableWidget, QTableWidgetItem, QMessageBox, QDialog, QComboBox, QPlainTextEdit)
from PyQt5.QtCore import QProcess, Qt  
from apagar_orcamento_le_layout import Ui_Dialog  # Interface da janela de exclusão
from utils import (
    limpar_campos_orcamento,
    atualizar_campos_para_novo_orcamento, # Esta função já usa as versões refatoradas de gerar_id/sugerir_num
    gerar_id_orcamento,                   # Importar diretamente se necessário (embora atualizar_campos... já use)
    sugerir_numero_orcamento,              # Importar diretamente se necessário
    formatar_valor_moeda,               # Formatação de moeda (se necessário)
    limpar_formatacao_preco             # Limpa formatação de preço (se necessário)
)
# Importar o gestor de contexto do módulo de conexão
from db_connection import obter_cursor


# --- Funções de Geração de Nomes de Pasta (Movidas para aqui para clareza) ---
def _gerar_nome_pasta_orcamento(num_orcamento, nome_cliente):
    """Gera o nome da pasta principal do orçamento.

    A nova regra ignora a data e utiliza apenas o número do orçamento e o nome
    do cliente. Caracteres inválidos são removidos.
    """

    nome_cliente_seguro = re.sub(r'[\\/*?:"<>|]+', '', nome_cliente.strip().upper().replace(' ', '_'))
    if not nome_cliente_seguro:
        print("Erro: Nome de cliente inválido para gerar nome de pasta.")
        return None

    return f"{num_orcamento}_{nome_cliente_seguro}"


# OBS: Como a conexão MySQL não depende de um ficheiro (como no SQLite),
# a função set_db_path() poderá ser dispensada. Contudo, se for necessário
# armazenar o nome da base ou outro parâmetro vindo da interface, pode ser mantida.
def set_db_path(line_edit: QLineEdit):
    """
    Atualiza o "caminho" ou nome da base de dados a partir do campo lineEdit_base_dados.
    Neste exemplo, apenas garantimos que o diretório (se for usado para armazenar arquivos)
    existe. A conexão propriamente dita será feita pelos parâmetros definidos no módulo de conexão.
    """
    db_path = line_edit.text()
    if not db_path: # Não faz nada se o caminho estiver vazio
        return
    try:
        # Assume que o path é para um diretório, não um ficheiro
        if not os.path.exists(db_path):
            os.makedirs(db_path)
            print(f"Diretório criado: {db_path}")
    except Exception as e:
        print(f"Erro ao verificar/criar o diretório base '{db_path}': {e}")
        QMessageBox.warning(None, "Erro de Diretório", f"Não foi possível verificar ou criar o diretório:\n{db_path}\n\nErro: {e}")


# Função refatorada para usar obter_cursor()
def criar_tabela_orcamentos():
    """
    Cria a tabela 'orcamentos' no MySQL caso ela ainda não exista.
    Usa obter_cursor() para gerenciar a conexão.
    """
    #print("Verificando/Criando tabela 'orcamentos'...")
    try:
        with obter_cursor() as cursor:
            # Query para criar a tabela, usando tipos MySQL e especificando engine/charset
            # Adicionada verificação NOT NULL onde apropriado e valores DEFAULT
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orcamentos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    id_cliente INT NOT NULL,      -- Chave estrangeira para a tabela de clientes
                    utilizador TEXT NULL,
                    ano VARCHAR(4) NULL,
                    num_orcamento VARCHAR(20) NULL,
                    versao VARCHAR(10) DEFAULT '00',
                    status VARCHAR(50) NULL,
                    nome_cliente VARCHAR(255) NULL,
                    enc_phc VARCHAR(50) NULL,
                    data VARCHAR(10) NULL,        -- Considerar usar DATE ou DATETIME no futuro
                    preco DOUBLE NULL DEFAULT 0.0, -- Usar DOUBLE ou DECIMAL para preços
                    ref_cliente VARCHAR(50) NULL,
                    obra TEXT NULL,
                    caracteristicas TEXT NULL,
                    localizacao TEXT NULL,
                    info_1 TEXT NULL,
                    info_2 TEXT NULL,
                    FOREIGN KEY (id_cliente) REFERENCES clientes(id) ON DELETE RESTRICT ON UPDATE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            # O commit é feito automaticamente pelo gestor de contexto
            #print("Tabela 'orcamentos' verificada/criada com sucesso.")
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao criar/verificar tabela 'orcamentos': {err}")
        QMessageBox.critical(None, "Erro Crítico de Base de Dados", f"Não foi possível criar/verificar a tabela 'orcamentos':\n{err}")
    except Exception as e:
        print(f"Erro inesperado ao criar/verificar tabela 'orcamentos': {e}")
        QMessageBox.critical(None, "Erro Crítico", f"Erro inesperado durante a inicialização da tabela 'orcamentos':\n{e}")
def pesquisar_orcamentos(termos):
    """
    Pesquisa orçamentos com base em múltiplos termos.
    Cada termo é aplicado a diversas colunas utilizando a cláusula LIKE.
    Retorna uma lista de registros.
    """
    registros = [] # Retorna lista vazia por padrão
    if not termos or all(not t.strip() for t in termos): # Verifica se a lista de termos não está vazia ou só tem strings vazias
         print("Nenhum termo de pesquisa fornecido.")
         return registros # Retorna lista vazia se não houver termos válidos

    try:
        with obter_cursor() as cursor:
            # Colunas a pesquisar (ajuste conforme necessário)
            colunas_pesquisa = [
                "utilizador", "ano", "num_orcamento", "versao", "nome_cliente",
                "enc_phc", "status", "data", "preco", "ref_cliente", "obra",
                "caracteristicas", "localizacao", "info_1", "info_2"
            ]
            # Monta a cláusula WHERE dinamicamente
            where_clauses = []
            parametros = []
            for termo in termos:
                termo_like = f"%{termo.strip()}%"
                clausulas_termo = [f"`{col}` LIKE %s" for col in colunas_pesquisa]
                where_clauses.append(f"({' OR '.join(clausulas_termo)})")
                parametros.extend([termo_like] * len(colunas_pesquisa))

            # Junta as cláusulas de cada termo com AND
            where_final = " AND ".join(where_clauses)

            # Query final com ordenação
            query = f"""
                SELECT * FROM orcamentos
                WHERE {where_final}
                ORDER BY CAST(num_orcamento AS UNSIGNED),
                         CASE WHEN versao = '00' THEN 0 ELSE 1 END,
                         CAST(versao AS UNSIGNED)
            """
            # print(f"[DEBUG Query Pesquisa]: {query}") # Descomente para depurar a query
            # print(f"[DEBUG Params Pesquisa]: {parametros}") # Descomente para depurar os parâmetros

            cursor.execute(query, parametros)
            registros = cursor.fetchall()
            print(f"Pesquisa encontrou {len(registros)} registos.")

    except mysql.connector.Error as err:
        print(f"Erro MySQL ao pesquisar orçamentos: {err}")
        QMessageBox.warning(None, "Erro de Pesquisa", f"Erro ao realizar a pesquisa na base de dados:\n{err}")
    except Exception as e:
        print(f"Erro inesperado ao pesquisar orçamentos: {e}")
        QMessageBox.warning(None, "Erro de Pesquisa", f"Ocorreu um erro inesperado durante a pesquisa:\n{e}")

    return registros


def preencher_tabela_orcamentos(ui, registros=None):
    """
    Preenche a tabela de orçamentos (tableWidget_orcamentos) com os registros do BD.
    Se 'registros' for None, realiza uma consulta para obter todos os orçamentos.
    """
    if registros is None:
        #print("Preenchendo tabela: buscando todos os orçamentos...")
        try:
            with obter_cursor() as cursor:
                query = """
                    SELECT * FROM orcamentos
                    ORDER BY CAST(num_orcamento AS UNSIGNED),
                             CASE WHEN versao = '00' THEN 0 ELSE 1 END,
                             CAST(versao AS UNSIGNED)
                """
                cursor.execute(query)
                registros = cursor.fetchall()
            #print(f"Encontrados {len(registros)} orçamentos na BD.")
        except mysql.connector.Error as err:
            print(f"Erro MySQL ao buscar todos os orçamentos: {err}")
            QMessageBox.critical(None, "Erro Base de Dados", f"Não foi possível carregar os orçamentos: {err}")
            registros = [] # Define como lista vazia para evitar erros posteriores
        except Exception as e:
            print(f"Erro inesperado ao buscar todos os orçamentos: {e}")
            QMessageBox.critical(None, "Erro Inesperado", f"Erro ao carregar orçamentos: {e}")
            registros = []

    # Limpa a tabela antes de preencher
    ui.tableWidget_orcamentos.setRowCount(0)

    # Preenche a tabela com os registros obtidos
    for linha_bd in registros:
        row_idx = ui.tableWidget_orcamentos.rowCount()
        ui.tableWidget_orcamentos.insertRow(row_idx)
        for col_idx, valor_bd in enumerate(linha_bd):
            # Formata a coluna de preço (índice 10) como moeda
            if col_idx == 10:
                texto_item = formatar_valor_moeda(valor_bd) # Usa a função de formatação
            else:
                texto_item = str(valor_bd) if valor_bd is not None else "" # Converte para string, tratando None

            item = QTableWidgetItem(texto_item)
            # Opcional: tornar colunas não editáveis
            if col_idx in [0, 1, 4]: # Ex: id, id_cliente, num_orcamento
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            ui.tableWidget_orcamentos.setItem(row_idx, col_idx, item)

    # Configuração das larguras de colunas (ajuste conforme necessário)
    ui.tableWidget_orcamentos.setColumnWidth(0, 30)    # ID
    ui.tableWidget_orcamentos.setColumnWidth(1, 30)    # id_cliente
    ui.tableWidget_orcamentos.setColumnWidth(2, 80)    # Utilizador
    ui.tableWidget_orcamentos.setColumnWidth(3, 80)    # Ano
    ui.tableWidget_orcamentos.setColumnWidth(4, 80)    # Num_Orcamento
    ui.tableWidget_orcamentos.setColumnWidth(5, 30)    # Versão
    ui.tableWidget_orcamentos.setColumnWidth(6, 150)   # Status
    ui.tableWidget_orcamentos.setColumnWidth(7, 250)   # Nome_Cliente
    ui.tableWidget_orcamentos.setColumnWidth(8, 80)    # Enc PHC
    ui.tableWidget_orcamentos.setColumnWidth(9, 80)    # Data
    ui.tableWidget_orcamentos.setColumnWidth(10, 80)   # Preço
    ui.tableWidget_orcamentos.setColumnWidth(11, 80)   # Ref_Cliente
    ui.tableWidget_orcamentos.setColumnWidth(12, 150)  # Obra
    ui.tableWidget_orcamentos.setColumnWidth(13, 500)  # Características
    ui.tableWidget_orcamentos.setColumnWidth(14, 200)  # Localização
    ui.tableWidget_orcamentos.setColumnWidth(15, 200)  # Info_1
    ui.tableWidget_orcamentos.setColumnWidth(16, 200)  # Info_2

    
def transportar_dados_cliente_orcamento():
    """
    Limpa os campos do orçamento e atualiza para novo orçamento,
    usando os dados do cliente selecionado (se houver).
    """
    # Verificar se há um cliente selecionado na tabela de clientes (se aplicável)
    # id_cliente = ui.lineEdit_id_cliente.text() # Exemplo
    # nome_cliente = ui.lineEdit_nome_cliente.text() # Exemplo
    # ref_cliente = ui.lineEdit_ref_cliente.text() # Exemplo

    # Obtém dados do cliente selecionado
    id_cliente = ui.lineEdit_idCliente.text().strip()
    nome_simplex = ui.lineEdit_nome_cliente_simplex.text().strip()

    if not id_cliente:
        QMessageBox.warning(None, "Aviso", "Selecione um cliente antes de transportar os dados.")
        return

    # Limpa os campos do orçamento e prepara um novo orçamento
    limpar_campos_orcamento(ui)
    atualizar_campos_para_novo_orcamento(ui)

    # Preenche os campos do orçamento com os dados do cliente
    ui.lineEdit_idCliente_noOrc.setText(id_cliente)
    ui.lineEdit_nome_cliente_2.setText(nome_simplex)

    # Muda para o separador Consulta Orçamentos
    ui.tabWidget_orcamento.setCurrentWidget(ui.tab_consulta_orcamentos)

def atualizar_campos_por_selecao():
    """
    Atualiza os campos do formulário com os dados da linha selecionada na tabela.
    """
    linha_selecionada = ui.tableWidget_orcamentos.currentRow()
    if linha_selecionada >= 0:
        campos = [
            ui.lineEdit_id,                # QLineEdit
            ui.lineEdit_idCliente_noOrc,     # QLineEdit
            ui.comboBox_utilizador,          # QComboBox
            ui.lineEdit_ano,                # QLineEdit
            ui.lineEdit_num_orcamento_2,      # QLineEdit
            ui.lineEdit_versao,             # QLineEdit
            ui.comboBox_status,             # QComboBox
            ui.lineEdit_nome_cliente_2,     # QLineEdit
            ui.lineEdit_enc_phc,            # QLineEdit
            ui.lineEdit_data,               # QLineEdit
            ui.lineEdit_preco,              # QLineEdit
            ui.lineEdit_ref_cliente_2,      # QLineEdit
            ui.lineEdit_obra_2,             # QLineEdit
            ui.plainTextEdit_caracteristicas, # QPlainTextEdit
            ui.lineEdit_localizacao,        # QLineEdit
            ui.plainTextEdit_info_1,        # QPlainTextEdit
            ui.plainTextEdit_info_2         # QPlainTextEdit
        ]
        for coluna, campo in enumerate(campos):
            item = ui.tableWidget_orcamentos.item(linha_selecionada, coluna)
            if item:
                valor = item.text()
                # Formatação especial para o campo de preço
                if campo == ui.lineEdit_preco:
                    # O valor já vem formatado da função preencher_tabela_orcamentos
                    campo.setText(valor)
                elif isinstance(campo, QLineEdit):
                    campo.setText(valor)
                elif isinstance(campo, QComboBox):
                    # Tenta encontrar o texto exato no ComboBox
                    index = campo.findText(valor, Qt.MatchFixedString)
                    if index >= 0:
                        campo.setCurrentIndex(index)
                    else:
                        # Se não encontrar, pode adicionar ou deixar em branco/padrão
                        print(f"Aviso: Valor '{valor}' não encontrado no ComboBox '{campo.objectName()}'")
                        campo.setCurrentIndex(-1) # Limpa a seleção
                elif isinstance(campo, QPlainTextEdit):
                    campo.setPlainText(valor)


def configurar_campos_iniciais():
    """
    Configura os valores iniciais do formulário de orçamento.
    """
    new_id = gerar_id_orcamento()
    ui.lineEdit_id.setText(new_id)

    ano_atual = str(datetime.datetime.now().year)
    ui.lineEdit_ano.setText(ano_atual)

    # Chama a função refatorada de utils.py
    proximo_num = sugerir_numero_orcamento(ano_atual)
    ui.lineEdit_num_orcamento_2.setText(proximo_num)

    ui.lineEdit_versao.setText("00")
    ui.lineEdit_data.setText(datetime.datetime.now().strftime("%d/%m/%Y"))

def inserir_linha_orcamento(ui):
    """
    Insere um novo orçamento no banco de dados a partir dos dados preenchidos no formulário.
    """
    id_cliente_str = ui.lineEdit_idCliente_noOrc.text().strip()
    # Validação robusta do ID do cliente
    if not id_cliente_str or not id_cliente_str.isdigit():
        QMessageBox.warning(None, "Erro", "ID de cliente inválido ou em falta!")
        return
    id_cliente = int(id_cliente_str)

    utilizador = ui.comboBox_utilizador.currentText()
    ano = ui.lineEdit_ano.text().strip()
    num_orcamento = ui.lineEdit_num_orcamento_2.text().strip()
    nome_cliente = ui.lineEdit_nome_cliente_2.text().strip() # Nome vem da seleção do cliente
    versao = ui.lineEdit_versao.text().strip()
    status = ui.comboBox_status.currentText()
    enc_phc = ui.lineEdit_enc_phc.text().strip()
    data_ = ui.lineEdit_data.text().strip()
    # Limpa e converte o preço
    preco_str = limpar_formatacao_preco(ui.lineEdit_preco.text())
    try:
        preco = float(preco_str) if preco_str else 0.0 # Define 0.0 se vazio
    except ValueError:
        QMessageBox.warning(None, "Erro", f"Valor de preço inválido: '{ui.lineEdit_preco.text()}'")
        return
    ref_cliente = ui.lineEdit_ref_cliente_2.text().strip()
    obra = ui.lineEdit_obra_2.text().strip()
    caracteristicas = ui.plainTextEdit_caracteristicas.toPlainText().strip()
    localizacao = ui.lineEdit_localizacao.text().strip()
    info_1 = ui.plainTextEdit_info_1.toPlainText().strip()
    info_2 = ui.plainTextEdit_info_2.toPlainText().strip()

    # Validação de campos chave
    if not (ano and num_orcamento and versao and nome_cliente):
        QMessageBox.warning(None, "Erro", "Campos Ano, Nº Orçamento, Versão e Nome Cliente são obrigatórios!")
        return

    try:
        # Usa o gestor de contexto
        with obter_cursor() as cursor:
            insert_query = """
                INSERT INTO orcamentos (
                    id_cliente, utilizador, ano, num_orcamento, versao, nome_cliente, status,
                    enc_phc, data, preco, ref_cliente, obra, caracteristicas, localizacao, info_1, info_2
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (
                id_cliente, utilizador, ano, num_orcamento, versao, nome_cliente, status,
                enc_phc, data_, preco, ref_cliente, obra, caracteristicas, localizacao, info_1, info_2
            ))
        # Commit é automático

        # Atualiza a UI após sucesso
        preencher_tabela_orcamentos(ui)
        limpar_campos_orcamento(ui)
        # Atualiza para o próximo ID/Num Orc (usando as funções refatoradas de utils)
        atualizar_campos_para_novo_orcamento(ui)
        QMessageBox.information(None, "Sucesso", "Orçamento inserido com sucesso.")

    except mysql.connector.Error as err:
        print(f"Erro MySQL ao inserir orçamento: {err}")
        QMessageBox.critical(None, "Erro Base de Dados", f"Erro ao inserir orçamento:\n{err}")
    except Exception as e:
        print(f"Erro inesperado ao inserir orçamento: {e}")
        QMessageBox.critical(None, "Erro Inesperado", f"Erro ao inserir orçamento:\n{e}")

def criar_excel_resumo(orcam_path, num_orcamento, versao, template_path=None):
    """
    Cria o ficheiro Excel de resumo de custos dentro da pasta do orçamento.
    Se existir um template, copia-o. Caso contrário, cria um Excel vazio com separadores base.
    """
    # Falta criar uma template de excel com os separadores necessários e se possivel com graficos e resumos dos varios resumos para paresentar no menu do separador Resumo_Consumos_Orcamento_2

    nome_ficheiro = f"Resumo_Custos_{num_orcamento}_{versao}.xlsx"
    caminho_excel = os.path.join(orcam_path, nome_ficheiro)

    if os.path.exists(caminho_excel):
        print(f"O ficheiro Excel de resumo já existe: {caminho_excel}")
        return

    if template_path and os.path.exists(template_path):
        # Copiar template existente
        import shutil
        shutil.copy(template_path, caminho_excel)
        print(f"Excel de resumo criado a partir de template: {caminho_excel}")
    else:
        # Criar um Excel simples com separadores base
        with pd.ExcelWriter(caminho_excel, engine='xlsxwriter') as writer:
            # Cria sheets básicos - adapta conforme as tuas necessidades!
            pd.DataFrame(columns=['Categoria', 'Descrição', 'Custo']).to_excel(writer, sheet_name='Placas', index=False)
            pd.DataFrame(columns=['Tipo', 'Descrição', 'Valor']).to_excel(writer, sheet_name='Ferragens', index=False)
            pd.DataFrame(columns=['Tipo', 'Comprimento', 'Valor']).to_excel(writer, sheet_name='Orlas', index=False)
            pd.DataFrame(columns=['Margem', 'Valor']).to_excel(writer, sheet_name='Margens', index=False)
        print(f"Excel de resumo criado de raiz: {caminho_excel}")

    return caminho_excel

def abrir_criar_pasta_orcamento():
    """
    Cria ou abre a pasta do orçamento com base nos dados configurados no
    formulário.

    Estrutura das pastas: <Ano>/<Num_Cliente>/<Versao>
    A primeira versão é sempre ``00`` e todas as versões ficam separadas em
    subpastas dentro da pasta "mãe" do orçamento.
    """
    try:
        caminho_base = ui.lineEdit_orcamentos.text().strip()
        if not caminho_base:
            QMessageBox.warning(None, "Erro", "O caminho base dos orçamentos não está configurado.")
            return

        ano = ui.lineEdit_ano.text().strip()
        num_orcamento = ui.lineEdit_num_orcamento_2.text().strip()
        # Usa o nome do cliente do campo, pois pode ter sido alterado
        nome_cliente = ui.lineEdit_nome_cliente_2.text().strip()  # Nome do cliente simplex
        versao = ui.lineEdit_versao.text().strip() # Versão do orcaemnto

        if not (ano and num_orcamento and nome_cliente and versao):
            QMessageBox.warning(None, "Erro", "Preencha corretamente todos os dados do orçamento (Ano, Nº, Cliente, Versão).")
            return

        caminho_ano = os.path.join(caminho_base, ano)
        nome_pasta_orcamento = _gerar_nome_pasta_orcamento(num_orcamento, nome_cliente)
        if nome_pasta_orcamento is None:
            QMessageBox.critical(None, "Erro", "Não foi possível gerar o nome da pasta do orçamento.")
            return
        caminho_orcamento = os.path.join(caminho_ano, nome_pasta_orcamento)

        # A partir de agora cada orçamento possui subpastas para as versões
        # começando em '00'. Logo, o caminho final inclui sempre a versão.
        caminho_final = os.path.join(caminho_orcamento, versao)

        # Garante que a pasta da versão '00' exista mesmo quando se trabalha
        # noutra versão (útil para orçamentos antigos ou criação direta da '01').
        if versao != "00":
            caminho_zero = os.path.join(caminho_orcamento, "00")
            if not os.path.exists(caminho_zero):
                os.makedirs(caminho_zero, exist_ok=True)

        # Cria o diretório se não existir (incluindo diretórios pai)
        if not os.path.exists(caminho_final):
            os.makedirs(caminho_final,exist_ok=True)
            QMessageBox.information(None, "Sucesso", f"Pasta do Orçamento criada:\n{caminho_final}")
        else:
            QMessageBox.information(None, "Informação", f"Abrindo pasta existente:\n{caminho_final}")

        # Tenta abrir a pasta no explorador de arquivos (Windows)
        # Para outros OS, pode ser necessário ajustar o comando
        try:
                # os.startfile(caminho_final) # Funciona melhor no Windows
                # Alternativa mais portável usando QProcess:
                QProcess.startDetached('explorer', [os.path.normpath(caminho_final)])
        except AttributeError: # os.startfile não existe em alguns sistemas
                try:
                    # Tenta comando para Linux
                    QProcess.startDetached('xdg-open', [caminho_final])
                except Exception:
                    try:
                        # Tenta comando para macOS
                        QProcess.startDetached('open', [caminho_final])
                    except Exception as open_err:
                        QMessageBox.warning(None, "Erro ao Abrir", f"Não foi possível abrir a pasta automaticamente.\nCaminho: {caminho_final}\nErro: {open_err}")

    except Exception as e:
        QMessageBox.critical(None, "Erro", f"Erro ao criar/abrir pasta do orçamento: {e}")
        import traceback
        traceback.print_exc()

def editar_linha_orcamento():
    """
    Edita os dados do orçamento selecionado na tabela sem criar um novo registro.
    """
    linha_selecionada = ui.tableWidget_orcamentos.currentRow()
    if linha_selecionada < 0:
        QMessageBox.warning(None, "Erro", "Nenhuma linha selecionada para edição.")
        return

    # Obter o ID da linha selecionada na tabela (coluna 0)
    id_orcamento_item = ui.tableWidget_orcamentos.item(linha_selecionada, 0)
    if not id_orcamento_item or not id_orcamento_item.text().isdigit():
         QMessageBox.critical(None, "Erro", "Não foi possível obter o ID do orçamento selecionado.")
         return
    id_orcamento = int(id_orcamento_item.text())

    # Obter dados dos campos da UI
    preco_formatado = limpar_formatacao_preco(ui.lineEdit_preco.text())
    try:
        preco_real = float(preco_formatado) if preco_formatado else 0.0
    except ValueError:
        QMessageBox.warning(None, "Erro", f"Valor de preço inválido: '{ui.lineEdit_preco.text()}'")
        return

    # Validar ID do cliente
    id_cliente_str = ui.lineEdit_idCliente_noOrc.text().strip()
    if not id_cliente_str or not id_cliente_str.isdigit():
         QMessageBox.warning(None, "Erro", "ID de cliente inválido ou em falta no formulário.")
         return
    id_cliente = int(id_cliente_str)

    # Lista de valores na ordem correta para UPDATE
    novos_dados = (
        id_cliente, # id_cliente (verificar se pode ser alterado aqui)
        ui.comboBox_utilizador.currentText(),
        ui.lineEdit_ano.text().strip(),
        ui.lineEdit_num_orcamento_2.text().strip(), # num_orcamento (geralmente não editável)
        ui.lineEdit_versao.text().strip(),
        ui.comboBox_status.currentText(),
        ui.lineEdit_nome_cliente_2.text().strip(), # nome_cliente (geralmente não editável aqui)
        ui.lineEdit_enc_phc.text().strip(),
        ui.lineEdit_data.text().strip(),
        preco_real,
        ui.lineEdit_ref_cliente_2.text().strip(),
        ui.lineEdit_obra_2.text().strip(),
        ui.plainTextEdit_caracteristicas.toPlainText().strip(),
        ui.lineEdit_localizacao.text().strip(),
        ui.plainTextEdit_info_1.toPlainText().strip(),
        ui.plainTextEdit_info_2.toPlainText().strip(),
        id_orcamento # ID para a cláusula WHERE
    )

    # Campos a serem atualizados (verificar quais podem realmente ser editados)
    # Atenção: Não incluir id, id_cliente, num_orcamento, nome_cliente se não devem ser editáveis aqui
    update_fields = """
        utilizador=%s, ano=%s, versao=%s, status=%s, enc_phc=%s, data=%s,
        preco=%s, ref_cliente=%s, obra=%s, caracteristicas=%s, localizacao=%s,
        info_1=%s, info_2=%s
    """
    # Ajustar a query e os parâmetros se id_cliente, num_orcamento, nome_cliente não forem editáveis
    # Exemplo:
    # update_fields = "utilizador=%s, ano=%s, versao=%s, status=%s, ..."
    # update_query = f"UPDATE orcamentos SET {update_fields} WHERE id=%s"
    # novos_dados_update = (novos_dados[1], novos_dados[2], ...) # Excluir campos não editáveis

    # Query assumindo que todos os campos (exceto IDs) podem ser editados:
    update_query = """
        UPDATE orcamentos
        SET id_cliente=%s, utilizador=%s, ano=%s, num_orcamento=%s, versao=%s, status=%s,
            nome_cliente=%s, enc_phc=%s, data=%s, preco=%s, ref_cliente=%s, obra=%s,
            caracteristicas=%s, localizacao=%s, info_1=%s, info_2=%s
        WHERE id=%s
    """

    try:
        # Usa o gestor de contexto
        with obter_cursor() as cursor:
            cursor.execute(update_query, novos_dados)
        # Commit é automático

        # Atualiza a UI
        preencher_tabela_orcamentos(ui)
        # Limpar campos após edição bem-sucedida? Ou manter para visualização?
        # limpar_campos_orcamento(ui)
        QMessageBox.information(None, "Sucesso", f"Orçamento ID {id_orcamento} atualizado com sucesso.")

    except mysql.connector.Error as err:
        print(f"Erro MySQL ao editar orçamento: {err}")
        QMessageBox.critical(None, "Erro Base de Dados", f"Erro ao editar orçamento:\n{err}")
    except Exception as e:
        print(f"Erro inesperado ao editar orçamento: {e}")
        QMessageBox.critical(None, "Erro Inesperado", f"Erro ao editar orçamento:\n{e}")

# --- Funções da Interface do Usuário (Slots) ---

def on_status_changed(ui):
    """Slot chamado quando o status (ComboBox) muda."""
    if ui.comboBox_status.currentText() == "Adjudicado" and not ui.lineEdit_enc_phc.text():
        QMessageBox.information(None, "Lembrete", "Não se esqueça de criar a Encomenda no PHC!")

# Função movida para fora de configurar_orcamentos_ui
def abrir_janela_apagar_orcamento(ui):
    """
    Abre uma janela de confirmação para excluir um orçamento.
    Usa obter_cursor() para a exclusão no BD.
    """
    linha_selecionada = ui.tableWidget_orcamentos.currentRow()
    if linha_selecionada < 0:
        QMessageBox.warning(None, "Erro", "Nenhuma linha selecionada para exclusão.")
        return

    try:
        id_orc = int(ui.tableWidget_orcamentos.item(linha_selecionada, 0).text())
        num_orcamento = ui.tableWidget_orcamentos.item(linha_selecionada, 4).text()
        nome_cliente_bd = ui.tableWidget_orcamentos.item(linha_selecionada, 7).text()
        versao_orcamento = ui.tableWidget_orcamentos.item(linha_selecionada, 5).text()
        data_orcamento = ui.tableWidget_orcamentos.item(linha_selecionada, 9).text()
        ano_orcamento = ui.tableWidget_orcamentos.item(linha_selecionada, 3).text()
    except (AttributeError, ValueError, IndexError):
        QMessageBox.critical(None, "Erro", "Não foi possível obter os dados do orçamento selecionado na tabela.")
        return

    nome_pasta_base = _gerar_nome_pasta_orcamento(num_orcamento, nome_cliente_bd)
    if nome_pasta_base is None:
         QMessageBox.critical(None, "Erro", "Não foi possível gerar o nome da pasta devido a dados inválidos (Data ou Cliente).")
         return

    dialog = QDialog()
    dialog_ui = Ui_Dialog()
    dialog_ui.setupUi(dialog)
    dialog_ui.label_nome_orcamento.setText(f"Orçamento: {num_orcamento}")
    dialog_ui.label_versao_orcamento.setText(f"Versão: {versao_orcamento}")
    dialog_ui.label_cliente_orcamento.setText(f"Cliente: {nome_cliente_bd}")

    def processar_exclusao():
        orcamento_excluido = False
        pasta_excluida = False
        erros = []

        if dialog_ui.checkBox_apagar_bd.isChecked():
            print(f"Tentando excluir orçamento ID: {id_orc} da BD...")
            try:
                with obter_cursor() as cursor:
                    tabelas = [
                        "dados_def_pecas",
                        "dados_modulo_medidas",
                        "dados_gerais_materiais",
                        "dados_gerais_ferragens",
                        "dados_gerais_sistemas_correr",
                        "dados_gerais_acabamentos",
                        "dados_items_materiais",
                        "dados_items_ferragens",
                        "dados_items_sistemas_correr",
                        "dados_items_acabamentos",
                    ]
                    for tab in tabelas:
                        cursor.execute(
                            f"DELETE FROM {tab} WHERE num_orc=%s AND ver_orc=%s",
                            (num_orcamento, versao_orcamento),
                        )

                    cursor.execute(
                        "DELETE FROM orcamento_items WHERE id_orcamento=%s",
                        (id_orc,),
                    )
                    cursor.execute("DELETE FROM orcamentos WHERE id = %s", (id_orc,))
                    if cursor.rowcount > 0:
                        orcamento_excluido = True
                        print("Orçamento excluído da BD.")
                    else:
                        print(f"Orçamento não encontrado na BD (ID:{id_orc}).")

                if orcamento_excluido:
                    preencher_tabela_orcamentos(ui)
            except mysql.connector.Error as err:
                erros.append(f"Erro ao excluir da BD: {err}")
                print(f"[ERRO DB Exclusão]: {err}")
            except Exception as e:
                erros.append(f"Erro inesperado ao excluir da BD: {e}")
                print(f"[ERRO Inesperado Exclusão BD]: {e}")

        if dialog_ui.checkBox_apagar_pasta.isChecked():
            caminho_base = ui.lineEdit_orcamentos.text().strip()
            if not caminho_base or not os.path.isdir(caminho_base):
                erros.append("Caminho base dos orçamentos inválido.")
            else:
                caminho_ano = os.path.join(caminho_base, ano_orcamento)
                caminho_orcamento = os.path.join(caminho_ano, nome_pasta_base)  # Usa nome gerado
                caminho_final_apagar = None
                caminho_versao = os.path.join(caminho_orcamento, versao_orcamento)

                # Nova estrutura: pastas de versão sempre existentes. Contudo,
                # mantemos um fallback para orçamentos antigos sem subpastas.
                if os.path.isdir(caminho_versao):
                    caminho_final_apagar = caminho_versao
                elif os.path.isdir(caminho_orcamento):
                    caminho_final_apagar = caminho_orcamento  # compatibilidade antiga
                else:
                    erros.append(f"Pasta não encontrada: {caminho_versao} ou {caminho_orcamento}")

                if caminho_final_apagar:
                    print(f"Tentando excluir pasta: {caminho_final_apagar}")
                    try:
                        import shutil
                        shutil.rmtree(caminho_final_apagar)
                        pasta_excluida = True; print("Pasta excluída.")
                    except Exception as e:
                        erros.append(f"Falha ao excluir pasta '{os.path.basename(caminho_final_apagar)}': {e}"); print(f"[ERRO Exclusão Pasta]: {e}")

        msg_final = ""
        if orcamento_excluido:
            msg_final += f"Orçamento -> {nome_pasta_base} _ {versao_orcamento} <- excluído da Base de Dados.\n"
        if pasta_excluida:
            msg_final += f"Pasta do Orçamento -> {nome_pasta_base} _ {versao_orcamento}<- excluída.\n"
        if erros:
            msg_final += "\nErros:\n- " + "\n- ".join(erros)
        if not msg_final:
            msg_final = "Nenhuma ação selecionada ou realizada."

        if erros: QMessageBox.warning(None, "Exclusão Parcial ou Falhada", msg_final)
        else: QMessageBox.information(None, "Exclusão Concluída", msg_final)
        dialog.accept()

    dialog_ui.pushButton_ok.clicked.connect(processar_exclusao)
    dialog_ui.pushButton_cancel.clicked.connect(dialog.reject)
    dialog.exec_()

def pesquisar():
    """
    Captura o input do usuário e realiza a pesquisa dos orçamentos.
    """
    termos_str = ui.lineEdit_pesquisar.text().strip()
    # Separa por '%' e remove termos vazios resultantes de múltiplos '%' seguidos
    termos = [t for t in termos_str.split('%') if t.strip()]

    if termos:
        print(f"Pesquisando por termos: {termos}")
        registros = pesquisar_orcamentos(termos) # Chama a função refatorada
        preencher_tabela_orcamentos(ui, registros)
    else:
         print("Campo de pesquisa vazio ou inválido, recarregando todos.")
         preencher_tabela_orcamentos(ui) # Recarrega tudo se não houver termos

def limpar_pesquisa():
    """
    Se o campo de pesquisa estiver vazio, recarrega todos os orçamentos.
    """
    if not ui.lineEdit_pesquisar.text().strip():
        preencher_tabela_orcamentos(ui)

# Variável global 'ui' (assumindo que será definida antes de chamar configurar_orcamentos_ui)
ui = None
def configurar_orcamentos_ui(main_ui):
    """
    Configura os componentes do separador 'Consulta Orçamentos' e conecta as funções.
    Recebe a instância principal da UI.
    """
    global ui # Permite que as funções aninhadas acessem a UI
    ui = main_ui

    # Configuração inicial (cria tabela se necessário)
    criar_tabela_orcamentos()

    # Carrega os dados iniciais na tabela
    preencher_tabela_orcamentos(ui)

    # Conecta os sinais aos slots (funções)
    ui.lineEdit_pesquisar.returnPressed.connect(pesquisar)
    ui.lineEdit_pesquisar.textChanged.connect(limpar_pesquisa)
    ui.pushButton_inserir_linha_orcamento_2.clicked.connect(lambda: inserir_linha_orcamento(ui))
    ui.pushButton_apagar_orcamento.clicked.connect(lambda: abrir_janela_apagar_orcamento(ui))
    ui.pushButton_abrir_criar_pasta_orcamento.clicked.connect(abrir_criar_pasta_orcamento)
    ui.pushButton_editar_linha_orcamento.clicked.connect(editar_linha_orcamento)
    ui.tableWidget_orcamentos.itemSelectionChanged.connect(atualizar_campos_por_selecao)
    ui.pushButton_tranpordados_cliente_orcamento.clicked.connect(transportar_dados_cliente_orcamento)

    # Configuração adicional da UI
    ui.lineEdit_nome_cliente_2.setReadOnly(True) # Nome do cliente geralmente vem da seleção
    ui.lineEdit_idCliente_noOrc.setReadOnly(True) # ID do cliente geralmente vem da seleção
    ui.lineEdit_id.setReadOnly(True) # ID do orçamento é gerado automaticamente

    # Preenche campos com valores iniciais (ex: próximo ID, data atual)
    # configurar_campos_iniciais() # Comentar se preferir que comece vazio ou preenchido pela seleção
    limpar_campos_orcamento(ui) # Começa com campos limpos
    # Definir valores padrão para ComboBoxes, se aplicável
    # ui.comboBox_utilizador.setCurrentIndex(0) # Exemplo
    # ui.comboBox_status.setCurrentIndex(0) # Exemplo


# Fim do módulo orcamentos.py


