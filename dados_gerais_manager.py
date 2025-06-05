'''
dados_gerais_manager.py
=======================
Módulo responsável por gerenciar o salvamento (guardar) e a importação dos dados
dos separadores de Dados Gerais para o banco de dados.
Contém funções para:
  - Listar os nomes dos modelos salvos.
  - Apagar registros de um modelo.
  - Solicitar ao usuário um nome para salvar os dados.
  - Salvar os dados do QTableWidget na tabela do banco.
  - Importar os dados do banco para o QTableWidget.
  
Observação:
  Todas as operações de banco de dados utilizam MySQL, através da função get_connection()
  importada do módulo db_connection.py. Certifique-se de que esse módulo esteja devidamente configurado.
"""
'''
import math  # Para verificação de valores NaN
import mysql.connector # Adicionado para erros específicos
from PyQt5.QtWidgets import QTableWidgetItem, QInputDialog, QMessageBox, QComboBox
from PyQt5.QtCore import Qt
from db_connection import obter_cursor
from utils import formatar_valor_moeda, formatar_valor_percentual, original_pliq_values, converter_texto_para_valor

def listar_nomes_dados_gerais(tabela_bd):
    """
    Retorna uma lista com os nomes já salvos na tabela 'dados_gerais_<tabela_bd>'.
    """
    nomes = []
    # Nome seguro para a tabela (evita SQL Injection simples)
    tabela_bd_segura = f"dados_gerais_{tabela_bd.replace(' ', '_').lower()}"
    # Validação básica do nome da tabela (opcional, mas recomendado)
    # if tabela_bd_segura not in ["dados_gerais_materiais", "dados_gerais_ferragens", ...]:
    #     print(f"Erro: Nome de tabela inválido '{tabela_bd}' em listar_nomes_dados_gerais.")
    #     return nomes

    print(f"Listando nomes para: {tabela_bd_segura}") # Debug
    try:
        with obter_cursor() as cursor:
            # Usar backticks para o nome da tabela
            cursor.execute(f"SELECT DISTINCT nome FROM `{tabela_bd_segura}` ORDER BY nome")
            nomes = [row[0] for row in cursor.fetchall() if row[0] is not None] # Filtra None
    except mysql.connector.Error as err:
         # Trata erro específico se a tabela não existir
        if err.errno == 1146: # Código de erro para "Table doesn't exist"
            print(f"Aviso: Tabela '{tabela_bd_segura}' não encontrada ao listar nomes.")
            # Retorna lista vazia, pois não há nomes a listar
        else:
            print(f"Erro MySQL ao listar nomes de '{tabela_bd_segura}': {err}")
            # Poderia mostrar QMessageBox aqui se fosse chamado diretamente pela UI
    except Exception as e:
        print(f"Erro inesperado ao listar nomes de '{tabela_bd_segura}': {e}")
    return nomes

def apagar_registros_por_nome(tabela_bd, nome):
    """
    Apaga do banco de dados todos os registros da tabela 'dados_gerais_<tabela_bd>'
    cujo campo 'nome' seja igual a <nome>.
    """
    tabela_bd_segura = f"dados_gerais_{tabela_bd.replace(' ', '_').lower()}"
    rows_deleted = 0
    print(f"Tentando apagar registos de '{nome}' em '{tabela_bd_segura}'...")
    try:
        with obter_cursor() as cursor:
            # Usar backticks e placeholders
            cursor.execute(f"DELETE FROM `{tabela_bd_segura}` WHERE nome=%s", (nome,))
            rows_deleted = cursor.rowcount # Captura número de linhas apagadas
        # Commit automático
        print(f"{rows_deleted} registos apagados com sucesso.")
        return True
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao apagar registos de '{nome}' em '{tabela_bd_segura}': {err}")
        QMessageBox.critical(None, "Erro Base de Dados", f"Erro ao apagar registos:\n{err}")
        return False
    except Exception as e:
        print(f"Erro inesperado ao apagar registos: {e}")
        QMessageBox.critical(None, "Erro Inesperado", f"Erro ao apagar registos:\n{e}")
        return False

def obter_nome_para_salvar(parent, tabela_bd):
    """
    Solicita ao usuário um nome para salvar os dados do tipo <tabela_bd>.
    Se o nome já existir, oferece opções (Substituir, Eliminar, Editar ou Cancelar).

    Retorna o nome escolhido ou None se o usuário cancelar.
    """
    nomes_existentes = listar_nomes_dados_gerais(tabela_bd)
    if nomes_existentes:
        nomes_texto_html = "<br>".join(nomes_existentes)
        QMessageBox.information(
            parent,
            "Modelos Existentes",
            f"Modelos já salvos para <b>{tabela_bd.upper()}</b>:<br>{nomes_texto_html}"
        )
    
    while True:
        nome, ok = QInputDialog.getText(
            parent,
            "Guardar Dados",
            f"Digite o nome para salvar os dados de <b>{tabela_bd.upper()}</b>:"
        )
        if not ok or not nome.strip():
            return None  # Usuário cancelou ou não digitou nada
        
        nome = nome.strip()
        if nome not in nomes_existentes:
            return nome
        
        # Se o nome já existir, oferece opções ao usuário
        msg_box = QMessageBox(parent)
        msg_box.setWindowTitle("Nome já existe")
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setText(
            f"O nome <b>{nome}</b> já existe em <b>{tabela_bd.upper()}</b>.<br><br>"
            "Selecione uma opção:<br>"
            "<b>Substituir</b> = Substituir os dados existentes<br>"
            "<b>Eliminar</b> = Eliminar os dados e cancelar o salvamento<br>"
            "<b>Editar</b> = Digitar um novo nome<br>"
            "<b>Cancelar</b> = Cancelar a operação")
        
        btn_substituir = msg_box.addButton("Substituir", QMessageBox.YesRole)
        btn_eliminar = msg_box.addButton("Eliminar", QMessageBox.NoRole)
        btn_editar = msg_box.addButton("Editar", QMessageBox.ActionRole)
        btn_cancelar = msg_box.addButton("Cancelar", QMessageBox.RejectRole)
        
        msg_box.exec_()
        clicked_button = msg_box.clickedButton()
        
        if clicked_button == btn_substituir:
            if apagar_registros_por_nome(tabela_bd, nome): return nome # Apaga e retorna nome
            else: return None # Erro ao apagar
        elif clicked_button == btn_eliminar:
            apagar_registros_por_nome(tabela_bd, nome)
            return None
        elif clicked_button == btn_editar:
            continue
        else:
            return None

def guardar_dados_gerais(parent_app, nome_tabela, col_info, nome_registro=None):
    """
    Salva os dados do QTableWidget na tabela 'dados_gerais_<nome_tabela>'.

    Parâmetros:
      ui: objeto principal da aplicação (MainApp), que contém a interface (ui).
      nome_tabela: identificador (ex.: "materiais").
      col_info: dicionário mapeando o índice da coluna do QTableWidget para
                { 'nome': <nome no BD>, 'type': <"float" ou "text">, 'percent': <bool> }.
      nome_registro: nome do modelo a ser salvo (obtido via interação com o usuário).
    """
    ui = parent_app.ui # Acessa a UI a partir da instância da aplicação principal
    if not nome_registro:
        QMessageBox.warning(ui, "Aviso", "Nenhum nome foi fornecido para salvar os dados.") # Modified: Removed parent=ui
        return
    
    # Seleciona o QTableWidget de acordo com o tipo
    if nome_tabela == "materiais":
        table = ui.Tab_Material
    elif nome_tabela == "ferragens":
        table = ui.Tab_Ferragens
    elif nome_tabela == "sistemas_correr":
        table = ui.Tab_Sistemas_Correr
    elif nome_tabela == "acabamentos":
        table = ui.Tab_Acabamentos
    else:
        QMessageBox.warning(ui, "Erro", f"Tabela para {nome_tabela} não encontrada.") # Modified: Removed parent=ui
        return
    
    row_count = table.rowCount()
    col_count = table.columnCount()
    dados = []
    
    # Percorre cada linha e coluna para coletar os dados
    for row in range(row_count):
        registro = [nome_registro, row]  # Inicia com o nome e o índice da linha
        for col in range(col_count):
            if col not in col_info:
                continue  # Pula colunas que não estão no mapeamento
            cell_widget = table.cellWidget(row, col)
            if cell_widget and hasattr(cell_widget, "currentText"):
                valor = cell_widget.currentText()
            else:
                item = table.item(row, col)
                valor = item.text() if item else ""
            tipo = col_info[col].get("type", "text")
            # Converte o valor para float, se necessário
            if tipo == "float":
                try:
                    valor = valor.replace('€', '').replace('%', '').replace(',', '.').strip()
                    valor = float(valor) if valor != "" else 0.0
                    if col_info[col].get("percent", False):
                        valor = valor / 100.0
                except:
                    valor = 0.0
            registro.append(valor)
        dados.append(tuple(registro))
    
    # Monta a query SQL para inserir os dados
    col_names_bd = [col_info[c]["nome"] for c in sorted(col_info.keys())]
    col_names_str = ", ".join(col_names_bd)
    # Para MySQL, usa-se %s como placeholder
    placeholders = ", ".join(["%s"] * (2 + len(col_info)))
    
    sql_insert = f"""
        INSERT INTO dados_gerais_{nome_tabela} (nome, linha, {col_names_str})
        VALUES ({placeholders})
    """
    
    try:
        # Usa obter_cursor para garantir transação e fecho
        with obter_cursor() as cursor:
            # Remove registros antigos (a função apagar_registros_por_nome já faz commit/rollback)
            # Não precisamos chamar apagar aqui se já foi feito em obter_nome_para_salvar
            # Se obter_nome_para_salvar não foi chamado, descomentar a linha abaixo:
            # cursor.execute(f"DELETE FROM `{tabela_bd_segura}` WHERE nome=%s", (nome_registro,))

            # Insere os novos registros
            # executemany é mais eficiente para múltiplos inserts
            cursor.executemany(sql_insert, dados)
        # Commit automático

        QMessageBox.information(parent_app, "Sucesso",
                                f"Dados de '{nome_tabela}' gravados como '{nome_registro}'!")
    except mysql.connector.Error as err:
        # Rollback é automático em caso de erro no 'with'
        print(f"Erro MySQL ao guardar dados gerais para '{nome_tabela}': {err}")
        QMessageBox.critical(parent_app, "Erro Base de Dados", f"Erro ao salvar dados:\n{err}")
    except Exception as e:
        print(f"Erro inesperado ao guardar dados gerais para '{nome_tabela}': {e}")
        QMessageBox.critical(parent_app, "Erro Inesperado", f"Erro ao salvar dados:\n{e}")
        import traceback; traceback.print_exc()

def importar_dados_gerais_com_opcao(parent_app, nome_tabela, mapeamento, modelo_escolhido=None):
    """
    Importa os dados do banco de dados para o QTableWidget do separador,
    oferecendo duas opções:
      - Manter os dados já gravados no BD.
      - Atualizar os dados com os dados atuais da tabela de matérias primas
        (baseado na referência única 'ref_le').

    Parâmetros:
      ui: objeto principal da aplicação.
      nome_tabela: identificador (ex.: "materiais").
      mapeamento: dicionário mapeando os nomes dos campos para o índice da coluna no QTableWidget.
    """
    # Busca os modelos salvos para a tabela
    ui = parent_app.ui # Acessa a UI a partir da instância principal

    modelos = listar_nomes_dados_gerais(nome_tabela) # Já usa obter_cursor
    if not modelos:
        QMessageBox.information(parent_app, "Importar Dados Gerais", f"Nenhum registo salvo para '{nome_tabela}'.")
        return

    if modelo_escolhido is None:
        modelo_escolhido, ok = QInputDialog.getItem(parent_app, "Importar Dados Gerais",
                                                     f"Selecione o registo a importar (<b>{nome_tabela.upper()}</b>):",
                                                     modelos, 0, False)
        if not ok or not modelo_escolhido: return

    opcoes = ["Manter dados gravados no BD", "Atualizar com dados de matérias primas"]
    opcao_selecionada, ok = QInputDialog.getItem(parent_app, "Opção de Importação",
                                                 f"Como deseja importar os dados de <b>{nome_tabela.upper()}</b>?",
                                                 opcoes, 0, False)
    if not ok or not opcao_selecionada: return

    # Determina a tabela UI correta
    tabela_widgets = {
        "materiais": ui.Tab_Material, "ferragens": ui.Tab_Ferragens,
        "sistemas_correr": ui.Tab_Sistemas_Correr, "acabamentos": ui.Tab_Acabamentos
    }
    table = tabela_widgets.get(nome_tabela)
    if table is None:
        QMessageBox.warning(parent_app, "Erro", f"Tabela UI para '{nome_tabela}' não encontrada.")
        return

    registros_bd = []
    try:
        # Busca os dados do modelo escolhido
        tabela_bd_segura = f"dados_gerais_{nome_tabela.replace(' ', '_').lower()}"
        # Seleciona apenas as colunas que estão no mapeamento + 'linha'
        colunas_select = ['linha'] + list(mapeamento.keys())
        colunas_sql = ", ".join(f"`{c}`" for c in colunas_select)
        query = f"SELECT {colunas_sql} FROM `{tabela_bd_segura}` WHERE nome = %s ORDER BY linha"
        with obter_cursor() as cursor:
            cursor.execute(query, (modelo_escolhido,))
            registros_bd = cursor.fetchall()

        if not registros_bd:
            QMessageBox.information(parent_app, "Importar", f"Nenhum dado encontrado para o modelo '{modelo_escolhido}'.")
            return

        # Prepara dados para a tabela UI
        table.blockSignals(True); table.setProperty("importando", True)
        row_count_ui = table.rowCount()
        dados_mp_cache = {} # Cache para evitar buscas repetidas em matérias-primas

        for reg_bd in registros_bd:
            reg_dict = dict(zip(colunas_select, reg_bd)) # Mapeia coluna BD -> valor
            linha_ui = reg_dict.get('linha')

            if linha_ui is None or not (0 <= linha_ui < row_count_ui):
                print(f"Aviso: Índice de linha inválido ({linha_ui}) no registo importado.")
                continue

            # Opção 1: Manter dados da BD
            if opcao_selecionada == "Manter dados gravados no BD":
                for campo_bd, col_ui in mapeamento.items():
                    valor_bd = reg_dict.get(campo_bd)
                    # Formatação e preenchimento (lógica similar à anterior)
                    texto_formatado = ""
                    if valor_bd is not None:
                        if campo_bd in ("pliq", "ptab", "comp_mp", "larg_mp", "esp_mp"): texto_formatado = formatar_valor_moeda(valor_bd)
                        elif campo_bd in ("desc1_plus", "desc2_minus", "desp"): texto_formatado = formatar_valor_percentual(valor_bd)
                        else: texto_formatado = str(valor_bd)
                    # Preenche widget ou item
                    widget = table.cellWidget(linha_ui, col_ui)
                    if isinstance(widget, QComboBox):
                        idx = widget.findText(texto_formatado, Qt.MatchFixedString); widget.setCurrentIndex(idx if idx >= 0 else -1)
                    else:
                        item = table.item(linha_ui, col_ui);
                        if not item: item = QTableWidgetItem(); table.setItem(linha_ui, col_ui, item)
                        item.setText(texto_formatado)

            # Opção 2: Atualizar com Matérias-Primas
            else:
                ref_le = reg_dict.get("ref_le") # Pega ref_le dos dados gerais importados
                dados_atuais_mp = None
                if ref_le:
                    # Verifica cache primeiro
                    if ref_le in dados_mp_cache:
                        dados_atuais_mp = dados_mp_cache[ref_le]
                    else:
                        # Busca na tabela materias_primas
                        with obter_cursor() as cursor_mp:
                             # Seleciona apenas as colunas necessárias para atualização
                             cursor_mp.execute("""
                                 SELECT DESCRICAO_no_ORCAMENTO, PRECO_TABELA, PLIQ, DESC1_PLUS, DESC2_MINUS,
                                        UND, DESP, CORESP_ORLA_0_4, CORESP_ORLA_1_0, COMP_MP, LARG_MP, ESP_MP
                                 FROM materias_primas WHERE Ref_LE = %s
                             """, (ref_le,))
                             dados_atuais_mp = cursor_mp.fetchone()
                             dados_mp_cache[ref_le] = dados_atuais_mp # Guarda no cache

                if dados_atuais_mp:
                    # Mapeia os dados de materias_primas para os nomes de campo usados no mapeamento UI
                    map_mp_cols = ["descricao_no_orcamento", "ptab", "pliq", "desc1_plus", "desc2_minus",
                                   "und", "desp", "corres_orla_0_4", "corres_orla_1_0", "comp_mp", "larg_mp", "esp_mp"]
                    dados_mp_dict = dict(zip(map_mp_cols, dados_atuais_mp))

                    # Atualiza a linha na UI com os dados de materias_primas
                    for campo_mp, col_ui in mapeamento.items():
                        # Se o campo existe nos dados obtidos de materias_primas, usa esse valor
                        if campo_mp in dados_mp_dict:
                             valor_bd = dados_mp_dict[campo_mp]
                             texto_formatado = ""
                             if valor_bd is not None:
                                if campo_mp in ("pliq", "ptab", "comp_mp", "larg_mp", "esp_mp"): texto_formatado = formatar_valor_moeda(valor_bd)
                                elif campo_mp in ("desc1_plus", "desc2_minus", "desp"): texto_formatado = formatar_valor_percentual(valor_bd)
                                else: texto_formatado = str(valor_bd)
                             # Preenche widget ou item
                             widget = table.cellWidget(linha_ui, col_ui)
                             if isinstance(widget, QComboBox):
                                 idx = widget.findText(texto_formatado, Qt.MatchFixedString); widget.setCurrentIndex(idx if idx >= 0 else -1)
                             else:
                                 item = table.item(linha_ui, col_ui);
                                 if not item: item = QTableWidgetItem(); table.setItem(linha_ui, col_ui, item)
                                 item.setText(texto_formatado)
                        # Se o campo é ref_le, mantém o valor original dos dados gerais importados
                        elif campo_bd == "ref_le":
                             valor_bd = reg_dict.get(campo_bd)
                             texto_formatado = str(valor_bd) if valor_bd is not None else ""
                             item = table.item(linha_ui, col_ui);
                             if not item: item = QTableWidgetItem(); table.setItem(linha_ui, col_ui, item)
                             item.setText(texto_formatado)

                else:
                    # Se não encontrou em materias_primas, mantém os dados gerais originais (mesma lógica da opção 1)
                    print(f"Aviso: Ref_LE '{ref_le}' não encontrado em matérias-primas para linha {linha_ui}. Mantendo dados gerais.")
                    for campo_bd, col_ui in mapeamento.items():
                        valor_bd = reg_dict.get(campo_bd)
                        texto_formatado = ""
                        if valor_bd is not None:
                            if campo_bd in ("pliq", "ptab", "comp_mp", "larg_mp", "esp_mp"): texto_formatado = formatar_valor_moeda(valor_bd)
                            elif campo_bd in ("desc1_plus", "desc2_minus", "desp"): texto_formatado = formatar_valor_percentual(valor_bd)
                            else: texto_formatado = str(valor_bd)
                        widget = table.cellWidget(linha_ui, col_ui)
                        if isinstance(widget, QComboBox):
                            idx = widget.findText(texto_formatado, Qt.MatchFixedString); widget.setCurrentIndex(idx if idx >= 0 else -1)
                        else:
                            item = table.item(linha_ui, col_ui);
                            if not item: item = QTableWidgetItem(); table.setItem(linha_ui, col_ui, item)
                            item.setText(texto_formatado)


        # Fim do loop pelas linhas
        table.setProperty("importando", False); table.blockSignals(False)
        QMessageBox.information(parent_app, "Importar Dados Gerais",
                                f"Dados de '{nome_tabela}' (Modelo: {modelo_escolhido}) importados com opção:\n'{opcao_selecionada}'.")
    except mysql.connector.Error as err:
        table.setProperty("importando", False); table.blockSignals(False)
        print(f"Erro MySQL ao importar dados gerais para '{nome_tabela}': {err}")
        QMessageBox.critical(parent_app, "Erro Base de Dados", f"Erro ao importar dados:\n{err}")
    except Exception as e:
        table.setProperty("importando", False); table.blockSignals(False)
        print(f"Erro inesperado ao importar dados gerais para '{nome_tabela}': {e}")
        QMessageBox.critical(parent_app, "Erro Inesperado", f"Erro ao importar dados:\n{e}")
        import traceback; traceback.print_exc()
        
    
def importar_dados_gerais_por_modelo(parent_app, nome_tabela, mapeamento, modelo):
    """
    Importa os dados do banco de dados para o QTableWidget do separador 'nome_tabela'
    utilizando o modelo (nome) fornecido, sem solicitar interatividade.
    """
    ui = parent_app.ui # Acessa a UI
    print(f"Importando modelo '{modelo}' para tabela '{nome_tabela}'...")

    registros_bd = []
    try:
        tabela_bd_segura = f"dados_gerais_{nome_tabela.replace(' ', '_').lower()}"
        colunas_select = ['linha'] + list(mapeamento.keys())
        colunas_sql = ", ".join(f"`{c}`" for c in colunas_select)
        query = f"SELECT {colunas_sql} FROM `{tabela_bd_segura}` WHERE nome = %s ORDER BY linha"

        with obter_cursor() as cursor:
            cursor.execute(query, (modelo,))
            registros_bd = cursor.fetchall()

        if not registros_bd:
            QMessageBox.information(parent_app, "Importar Modelo", f"Nenhum dado encontrado para o modelo '{modelo}'.")
            return

        # Seleciona a tabela UI correta
        tabela_widgets = { "materiais": ui.Tab_Material, "ferragens": ui.Tab_Ferragens,
                           "sistemas_correr": ui.Tab_Sistemas_Correr, "acabamentos": ui.Tab_Acabamentos }
        table = tabela_widgets.get(nome_tabela)
        if table is None: return # Erro já tratado

        row_count_ui = table.rowCount()
        table.blockSignals(True); table.setProperty("importando", True)

        # Preenche a tabela UI
        for reg_bd in registros_bd:
            reg_dict = dict(zip(colunas_select, reg_bd))
            linha_ui = reg_dict.get('linha')
            if linha_ui is None or not (0 <= linha_ui < row_count_ui): continue

            for campo_bd, col_ui in mapeamento.items():
                valor_bd = reg_dict.get(campo_bd)
                texto_formatado = ""
                if valor_bd is not None:
                    if campo_bd in ("pliq", "ptab", "comp_mp", "larg_mp", "esp_mp"): texto_formatado = formatar_valor_moeda(valor_bd)
                    elif campo_bd in ("desc1_plus", "desc2_minus", "desp"): texto_formatado = formatar_valor_percentual(valor_bd)
                    else: texto_formatado = str(valor_bd)

                widget = table.cellWidget(linha_ui, col_ui)
                if isinstance(widget, QComboBox):
                    idx = widget.findText(texto_formatado, Qt.MatchFixedString); widget.setCurrentIndex(idx if idx >= 0 else -1)
                else:
                    item = table.item(linha_ui, col_ui);
                    if not item: item = QTableWidgetItem(); table.setItem(linha_ui, col_ui, item)
                    item.setText(texto_formatado)

        table.setProperty("importando", False); table.blockSignals(False)
        QMessageBox.information(parent_app, "Importar Modelo", f"Dados do modelo '{modelo}' importados para '{nome_tabela}'.")

    except mysql.connector.Error as err:
        table.setProperty("importando", False); table.blockSignals(False) # Garante desbloqueio
        print(f"Erro MySQL ao importar modelo '{modelo}': {err}")
        QMessageBox.critical(parent_app, "Erro Base de Dados", f"Erro ao importar modelo:\n{err}")
    except Exception as e:
        table.setProperty("importando", False); table.blockSignals(False) # Garante desbloqueio
        print(f"Erro inesperado ao importar modelo '{modelo}': {e}")
        QMessageBox.critical(parent_app, "Erro Inesperado", f"Erro ao importar modelo:\n{e}")
        import traceback; traceback.print_exc()