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
from PyQt5.QtWidgets import QTableWidgetItem, QInputDialog, QMessageBox, QComboBox, QDialog
from dialogs_modelos import SelecaoModeloDialog, GerirNomesDialog
from PyQt5.QtCore import Qt
import re
from db_connection import obter_cursor
from utils import formatar_valor_moeda, formatar_valor_percentual, original_pliq_values, converter_texto_para_valor

def listar_nomes_dados_gerais(tabela_bd, utilizador=None):
    """Retorna os nomes gravados na tabela ``dados_gerais_<tabela_bd>``.

    Se ``utilizador`` for fornecido, a listagem é filtrada para incluir
    apenas os modelos desse utilizador.
    """
    nomes = []
    tabela_bd_segura = f"dados_gerais_{tabela_bd.replace(' ', '_').lower()}"

    print(f"Listando nomes para: {tabela_bd_segura}")  # Debug
    try:
        with obter_cursor() as cursor:
            if utilizador:
                cursor.execute(
                    f"SELECT DISTINCT nome FROM `{tabela_bd_segura}` WHERE utilizador=%s ORDER BY nome",
                    (utilizador,),
                )
            else:
                cursor.execute(
                    f"SELECT DISTINCT nome FROM `{tabela_bd_segura}` ORDER BY nome"
                )
            nomes = [row[0] for row in cursor.fetchall() if row[0] is not None]
            nomes = [n for n in nomes if not re.fullmatch(r"\d+_\d+", str(n))]
    except mysql.connector.Error as err:
        if err.errno == 1146:  # Table doesn't exist
            print(f"Aviso: Tabela '{tabela_bd_segura}' não encontrada ao listar nomes.")
        else:
            print(f"Erro MySQL ao listar nomes de '{tabela_bd_segura}': {err}")
    except Exception as e:
        print(f"Erro inesperado ao listar nomes de '{tabela_bd_segura}': {e}")
    return nomes

def listar_nomes_descricoes_dados_gerais(tabela_bd, somente_completos=False, utilizador=None):
    """Retorna dicionário ``nome -> descricao_modelo`` da tabela.

    Quando ``utilizador`` é informado, apenas modelos pertencentes a esse
    utilizador são retornados. O parâmetro ``somente_completos`` mantém o
    comportamento anterior, filtrando somente modelos com nome e descrição
    preenchidos.
    """
    tabela_bd_segura = f"dados_gerais_{tabela_bd.replace(' ', '_').lower()}"
    resultados = {}
    try:
        with obter_cursor() as cursor:
            cursor.execute(
                f"SHOW COLUMNS FROM `{tabela_bd_segura}` LIKE 'descricao_modelo'",
            )
            has_col = cursor.fetchone() is not None
            if not has_col:
                try:
                    cursor.execute(
                        f"ALTER TABLE `{tabela_bd_segura}` ADD COLUMN descricao_modelo TEXT NULL AFTER nome",
                    )
                    has_col = True
                except mysql.connector.Error as alter_err:
                    print(
                        f"Erro ao adicionar coluna descricao_modelo em '{tabela_bd_segura}': {alter_err}"
                    )

            if has_col:
                sql = f"SELECT nome, MAX(descricao_modelo) FROM `{tabela_bd_segura}`"
            else:
                sql = f"SELECT DISTINCT nome, '' FROM `{tabela_bd_segura}`"
            params = []
            if utilizador:
                sql += " WHERE utilizador=%s"
                params.append(utilizador)
            if has_col:
                sql += " GROUP BY nome ORDER BY nome"
            else:
                sql += " ORDER BY nome"

            cursor.execute(sql, tuple(params))
            for row in cursor.fetchall():
                nome, desc = row
                if nome is not None:
                    desc_val = desc or ""
                    if (
                        not somente_completos
                        or (str(nome).strip() and desc_val.strip())
                    ):
                        resultados[nome] = desc_val
    except mysql.connector.Error as err:
        if err.errno == 1146:
            print(f"Aviso: Tabela '{tabela_bd_segura}' não encontrada ao listar descricoes.")
        else:
            print(f"Erro MySQL ao listar descricoes de '{tabela_bd_segura}': {err}")
    except Exception as e:
        print(f"Erro inesperado ao listar descricoes de '{tabela_bd_segura}': {e}")
    return resultados


def apagar_registros_por_nome(tabela_bd, nome, utilizador=None):
    """Apaga registos pelo ``nome`` e opcionalmente pelo ``utilizador``."""
    tabela_bd_segura = f"dados_gerais_{tabela_bd.replace(' ', '_').lower()}"
    rows_deleted = 0
    print(f"Tentando apagar registos de '{nome}' em '{tabela_bd_segura}'...")
    try:
        with obter_cursor() as cursor:
            sql = f"DELETE FROM `{tabela_bd_segura}` WHERE nome=%s"
            params = [nome]
            if utilizador:
                sql += " AND utilizador=%s"
                params.append(utilizador)
            cursor.execute(sql, tuple(params))
            rows_deleted = cursor.rowcount
        print(f"{rows_deleted} registos apagados com sucesso.")
        return True
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao apagar registos de '{nome}' em '{tabela_bd_segura}': {err}")
        QMessageBox.critical(None, "Erro Base de Dados", f"Erro ao apagar registos:\n{err}")
        return False
    
def apagar_registros_por_orcamento(tabela_bd, num_orc, ver_orc):
    """Apaga todos os registros associados ao par ``(num_orc, ver_orc)``.

    Esta função é utilizada quando se guardam dados gerais para um
    orçamento específico através do botão *guardar_dados_gerais_orcamento*.
    Nessa operação o campo ``nome`` não é preenchido e, portanto, não pode
    ser utilizado como chave para eliminação dos registos antigos.
    """
    tabela_bd_segura = f"dados_gerais_{tabela_bd.replace(' ', '_').lower()}"
    try:
        with obter_cursor() as cursor:
            cursor.execute(
                f"DELETE FROM `{tabela_bd_segura}` WHERE num_orc=%s AND ver_orc=%s",
                (num_orc, ver_orc),
            )
            rows = cursor.rowcount
        print(f"{rows} registos removidos de '{tabela_bd_segura}' para o orçamento {num_orc}-{ver_orc}.")
        return True
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao eliminar registos de '{tabela_bd_segura}': {err}")
        QMessageBox.critical(None, "Erro Base de Dados", f"Erro ao apagar registros:\n{err}")
        return False
    except Exception as e:
        print(f"Erro inesperado ao eliminar registos de '{tabela_bd_segura}': {e}")
        QMessageBox.critical(None, "Erro Inesperado", f"Erro ao apagar registros:\n{e}")
        return False

def renomear_registros(tabela_bd, nome_antigo, nome_novo, utilizador=None):
    """Atualiza o campo 'nome' filtrando opcionalmente por ``utilizador``."""
    tabela_bd_segura = f"dados_gerais_{tabela_bd.replace(' ', '_').lower()}"
    try:
        with obter_cursor() as cursor:
            sql = f"UPDATE `{tabela_bd_segura}` SET nome=%s WHERE nome=%s"
            params = [nome_novo, nome_antigo]
            if utilizador:
                sql += " AND utilizador=%s"
                params.append(utilizador)
            cursor.execute(sql, tuple(params))
        return True
    except mysql.connector.Error as err:
        print(
            f"Erro MySQL ao renomear '{nome_antigo}' para '{nome_novo}' em '{tabela_bd_segura}': {err}"
        )
        QMessageBox.critical(
            None,
            "Erro Base de Dados",
            f"Erro ao renomear registros:\n{err}",
        )
        return False
    
def atualizar_descricao_modelo(tabela_bd, nome, nova_descricao, utilizador=None):
    """Atualiza ``descricao_modelo`` de todas as linhas do modelo."""
    tabela_bd_segura = f"dados_gerais_{tabela_bd.replace(' ', '_').lower()}"
    try:
        with obter_cursor() as cursor:
            sql = f"UPDATE `{tabela_bd_segura}` SET descricao_modelo=%s WHERE nome=%s"
            params = [nova_descricao, nome]
            if utilizador:
                sql += " AND utilizador=%s"
                params.append(utilizador)
            cursor.execute(sql, tuple(params))
        return True
    except Exception as e:
        print(f"Erro ao atualizar descricao de '{nome}' em '{tabela_bd_segura}': {e}")
        return False

def obter_nome_para_salvar(parent, tabela_bd, utilizador=None):
    """Abre um diálogo para escolher ou introduzir o nome e descrição a guardar.

    Lista apenas os modelos pertencentes ao ``utilizador`` (se fornecido).
    """
    nomes_desc = listar_nomes_descricoes_dados_gerais(tabela_bd, somente_completos=True, utilizador=utilizador)
    dlg = GerirNomesDialog(tabela_bd, nomes_desc, parent)
    if dlg.exec_() != QDialog.Accepted:
        return None, None
    nome, descricao, eliminado, editados, desc_editadas = dlg.obter_nome()
    nome = (nome or "").strip()
    descricao = (descricao or "").strip()
    if not nome or not descricao:
        QMessageBox.warning(parent, "Aviso", "Preencha Nome e Descrição para gravar o modelo.")
        return None, None
    if eliminado:
        apagar_registros_por_nome(tabela_bd, eliminado, utilizador)
    for old, new in editados.items():
        renomear_registros(tabela_bd, old, new, utilizador)
        if old == nome:
            nome = new
    for n, nova_desc in desc_editadas.items():
        atualizar_descricao_modelo(tabela_bd, n, nova_desc, utilizador)
    if nome in nomes_desc and nome not in editados.values() and nome != eliminado:
        apagar_registros_por_nome(tabela_bd, nome, utilizador)
    return nome, descricao

def guardar_dados_gerais(parent_app, nome_tabela, col_info, nome_registro=None, descricao_registro="", utilizador=None):
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
        registro = [nome_registro, utilizador, descricao_registro, row]  # Nome, utilizador, descrição e índice da linha
        for col in range(col_count):
            if col not in col_info:
                continue  # Pula colunas que não estão no mapeamento
            cell_widget = table.cellWidget(row, col)
            if cell_widget and hasattr(cell_widget, "currentText"):
                valor = cell_widget.currentText()
            else:
                item = table.item(row, col)
                if col_info[col].get("nome") == "nao_stock":
                    valor = 1 if (item and item.checkState() == Qt.Checked) else 0
                else:
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
    placeholders = ", ".join(["%s"] * (4 + len(col_info)))

    sql_insert = f"""
        INSERT INTO dados_gerais_{nome_tabela} (nome, utilizador, descricao_modelo, linha, {col_names_str})
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

def importar_dados_gerais_com_opcao(parent_app, nome_tabela, mapeamento, modelo_escolhido=None, utilizador=None):
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

    modelos_desc = listar_nomes_descricoes_dados_gerais(nome_tabela, somente_completos=True, utilizador=utilizador)
    if not modelos_desc:
        QMessageBox.information(parent_app, "Importar Dados Gerais", f"Nenhum registo salvo para '{nome_tabela}'.")
        return

    if modelo_escolhido is None:
        dlg = SelecaoModeloDialog(modelos_desc, titulo=f"Importar Dados Gerais ->> {nome_tabela}", parent=parent_app)
        if dlg.exec_() != QDialog.Accepted:
            return
        modelo_escolhido = dlg.modelo_escolhido()
        if not modelo_escolhido:
            return

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
        colunas_select = ['linha'] + list(mapeamento.keys())
        colunas_sql = ", ".join(f"`{c}`" for c in colunas_select)
        query = f"SELECT {colunas_sql} FROM `{tabela_bd_segura}` WHERE nome = %s"
        params = [modelo_escolhido]
        if utilizador:
            query += " AND utilizador=%s"
            params.append(utilizador)
        query += " ORDER BY linha"
        with obter_cursor() as cursor:
            cursor.execute(query, tuple(params))
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
                        if campo_bd in ("pliq", "ptab"):
                            texto_formatado = formatar_valor_moeda(valor_bd)
                        elif campo_bd in ("comp_mp", "larg_mp", "esp_mp"):
                            texto_formatado = f"{float(valor_bd):.1f}"
                        elif campo_bd in ("desc1_plus", "desc2_minus", "desp"):
                            texto_formatado = formatar_valor_percentual(valor_bd)
                        else:
                            texto_formatado = str(valor_bd)
                    # Preenche widget ou item
                    widget = table.cellWidget(linha_ui, col_ui)
                    if isinstance(widget, QComboBox):
                        idx = widget.findText(texto_formatado, Qt.MatchFixedString); widget.setCurrentIndex(idx if idx >= 0 else -1)
                    else:
                        item = table.item(linha_ui, col_ui);
                        if not item:
                            item = QTableWidgetItem()
                            table.setItem(linha_ui, col_ui, item)
                        if campo_bd == "nao_stock":
                            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                            item.setCheckState(Qt.Checked if valor_bd else Qt.Unchecked)
                        else:
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
                            cursor_mp.execute(
                                """
                                SELECT DESCRICAO_do_PHC, DESCRICAO_no_ORCAMENTO, PRECO_TABELA, PLIQ, MARGEM, DESCONTO,
                                       UND, DESP, CORESP_ORLA_0_4, CORESP_ORLA_1_0, COMP_MP, LARG_MP, ESP_MP
                                FROM materias_primas WHERE Ref_LE = %s
                                """,
                                (ref_le,))
                            dados_atuais_mp = cursor_mp.fetchone()
                            dados_mp_cache[ref_le] = dados_atuais_mp  # Guarda no cache

                if dados_atuais_mp:
                    # Mapeia os dados de materias_primas para os nomes de campo usados no mapeamento UI
                    map_mp_cols = [
                        "descricao",
                        "descricao_no_orcamento",
                        "ptab",
                        "pliq",
                        "desc1_plus",
                        "desc2_minus",
                        "und",
                        "desp",
                        "corres_orla_0_4",
                        "corres_orla_1_0",
                        "comp_mp",
                        "larg_mp",
                        "esp_mp",
                    ]
                    dados_mp_dict = dict(zip(map_mp_cols, dados_atuais_mp))

                    # Atualiza a linha na UI com os dados de materias_primas
                    for campo_mp, col_ui in mapeamento.items():
                        # Se o campo existe nos dados obtidos de materias_primas, usa esse valor
                        if campo_mp in dados_mp_dict:
                             valor_bd = dados_mp_dict[campo_mp]
                             texto_formatado = ""
                             if valor_bd is not None:
                                if campo_mp in ("pliq", "ptab"):
                                    texto_formatado = formatar_valor_moeda(valor_bd)
                                elif campo_mp in ("comp_mp", "larg_mp", "esp_mp"):
                                    texto_formatado = f"{float(valor_bd):.1f}"
                                elif campo_mp in ("desc1_plus", "desc2_minus", "desp"):
                                    texto_formatado = formatar_valor_percentual(valor_bd)
                                else:
                                    texto_formatado = str(valor_bd)
                             # Preenche widget ou item
                             widget = table.cellWidget(linha_ui, col_ui)
                             if isinstance(widget, QComboBox):
                                 idx = widget.findText(texto_formatado, Qt.MatchFixedString); widget.setCurrentIndex(idx if idx >= 0 else -1)
                             else:
                                 item = table.item(linha_ui, col_ui)
                                 if not item:
                                     item = QTableWidgetItem()
                                     table.setItem(linha_ui, col_ui, item)
                                 if campo_mp == "nao_stock":
                                     item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                                     item.setCheckState(Qt.Checked if valor_bd else Qt.Unchecked)
                                 else:
                                     item.setText(texto_formatado)
                        # Se o campo é ref_le, mantém o valor original dos dados gerais importados
                        elif campo_mp == "ref_le":
                             valor_bd = reg_dict.get(campo_mp)
                             texto_formatado = str(valor_bd) if valor_bd is not None else ""
                             item = table.item(linha_ui, col_ui)
                             if not item:
                                 item = QTableWidgetItem()
                                 table.setItem(linha_ui, col_ui, item)
                             if campo_mp == "nao_stock":
                                 item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                                 item.setCheckState(Qt.Checked if valor_bd else Qt.Unchecked)
                             else:
                                 item.setText(texto_formatado)

                else:
                    # Se não encontrou em materias_primas, mantém os dados gerais originais (mesma lógica da opção 1)
                    print(f"Aviso: Ref_LE '{ref_le}' não encontrado em matérias-primas para linha {linha_ui}. Mantendo dados gerais.")
                    for campo_bd, col_ui in mapeamento.items():
                        valor_bd = reg_dict.get(campo_bd)
                        texto_formatado = ""
                        if valor_bd is not None:
                            if campo_bd in ("pliq", "ptab"):
                                texto_formatado = formatar_valor_moeda(valor_bd)
                            elif campo_bd in ("comp_mp", "larg_mp", "esp_mp"):
                                texto_formatado = f"{float(valor_bd):.1f}"
                            elif campo_bd in ("desc1_plus", "desc2_minus", "desp"):
                                texto_formatado = formatar_valor_percentual(valor_bd)
                            else:
                                texto_formatado = str(valor_bd)
                        widget = table.cellWidget(linha_ui, col_ui)
                        if isinstance(widget, QComboBox):
                            idx = widget.findText(texto_formatado, Qt.MatchFixedString); widget.setCurrentIndex(idx if idx >= 0 else -1)
                        else:
                            item = table.item(linha_ui, col_ui)
                            if not item:
                                item = QTableWidgetItem()
                                table.setItem(linha_ui, col_ui, item)
                            if campo_bd == "nao_stock":
                                item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                                item.setCheckState(Qt.Checked if valor_bd else Qt.Unchecked)
                            else:
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
                    if campo_bd in ("pliq", "ptab"):
                        texto_formatado = formatar_valor_moeda(valor_bd)
                    elif campo_bd in ("comp_mp", "larg_mp", "esp_mp"):
                        texto_formatado = f"{float(valor_bd):.1f}"
                    elif campo_bd in ("desc1_plus", "desc2_minus", "desp"):
                        texto_formatado = formatar_valor_percentual(valor_bd)
                    else:
                        texto_formatado = str(valor_bd)

                widget = table.cellWidget(linha_ui, col_ui)
                if isinstance(widget, QComboBox):
                    idx = widget.findText(texto_formatado, Qt.MatchFixedString); widget.setCurrentIndex(idx if idx >= 0 else -1)
                else:
                    item = table.item(linha_ui, col_ui)
                    if not item:
                        item = QTableWidgetItem()
                        table.setItem(linha_ui, col_ui, item)
                    if campo_bd == "nao_stock":
                        item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                        item.setCheckState(Qt.Checked if valor_bd else Qt.Unchecked)
                    else:
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