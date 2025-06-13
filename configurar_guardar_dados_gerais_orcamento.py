#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Módulo: configurar_guardar_dados_gerais_orcamento.py

Descrição:
Este novo módulo substitui o antigo guardar_dados_gerais_orcamento.py e
centraliza as funções de configuração e gravação dos Dados Gerais do orçamento.
A função configurar_dados_gerais realiza o seguinte:
  1. Obtém os valores "num_orc" e "ver_orc" a partir dos widgets na aba Orçamento.
  2. Verifica na base de dados se já existe uma configuração para esse orçamento (baseada em num_orc e ver_orc).
     - Se existir (por exemplo, na tabela de Materiais), a função carrega os dados salvos e preenche
       os QTableWidgets dos 4 separadores (Materiais, Ferragens, Sistemas Correr e Acabamentos),
       preenchendo as colunas:
         num_orc; ver_orc; ref_le; descricao_no_orcamento;
         pliq (form. moeda, ex.: 12.36€);
         desc1_plus (form. percentual, ex.: 13%); desc2_minus (form. percentual, ex.: 8%);
         und; desp (form. percentual, ex.: 13%); corres_orla_0_4; corres_orla_1_0;
         tipo; familia; comp_mp; larg_mp; esp_mp.
     - Se não existir, procede com o mapeamento manual: verifica se as células estão vazias ou divergentes
       e, conforme a resposta do usuário, preenche ou atualiza os dados.
  3. Ao final, a visualização é alterada para a aba "Dados Gerais MP".

Além disso, a função guardar_dados_gerais_orcamento grava (salva) os dados preenchidos nas 4 tabelas,
associando-os ao orçamento atual (identificado por num_orc e ver_orc).

Observação:
- Esse módulo depende de:
    • get_connection (importado de orcamentos)
    • QMessageBox, QTableWidgetItem, QInputDialog (do PyQt5)
    • Função converter_texto_para_valor (do módulo utils)
- A chamada do botão “Configurar Dados Gerais” permanece no script orcamento_items.py, que passa o objeto
  MainApp (que possui o atributo ui) como parâmetro.
  
Autor: Paulo Catarino
Data: 27-01-2025
"""

from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem, QInputDialog, QComboBox, QDialog
from PyQt5.QtCore import Qt
import mysql.connector # Adicionado para erros específicos
from db_connection import obter_cursor
from utils import converter_texto_para_valor, formatar_valor_moeda, formatar_valor_percentual
from dados_gerais_manager import apagar_registros_por_nome, apagar_registros_por_orcamento
from dialogs_modelos import SelecaoModeloDialog
from dados_gerais_mp import (limpar_linha_dados_gerais,COLUNAS_LIMPAR_MATERIAIS,COLUNAS_LIMPAR_FERRAGENS,COLUNAS_LIMPAR_SISTEMAS_CORRER,COLUNAS_LIMPAR_ACABAMENTOS)
import math


# ------------------------------------------------------------------------------
# FUNÇÃO AUXILIAR: formatar_versao
# ------------------------------------------------------------------------------
def formatar_versao(raw_ver):
    """
    Converte o valor raw_ver para uma string de dois dígitos.
    Exemplos:
      "0" ou "00" -> "00"
      "1" ou "01" -> "01"
      "2"        -> "02"
      "10"       -> "10"
    Se ocorrer erro na conversão, retorna "00".
    """
    raw_ver = raw_ver.strip()
    # print(f"DEBUG: Raw version from UI: {raw_ver=}")  # Para debugar o valor recebido
    try:
        ver_int = int(raw_ver)
        formatted = f"{ver_int:02d}"
        # print(f"DEBUG: Formatted version: {formatted=}")
        return formatted
    except Exception:
        return "00"

# ------------------------------------------------------------------------------
# FUNÇÃO AUXILIAR: mapear_registro_gerais
# ------------------------------------------------------------------------------


def mapear_registro_gerais(registro, column_names=None):
    """
    Reordena os dados de um registro vindo do banco de dados para a ordem
    que será apresentada no QTableWidget.

    Atenção: O campo ver_orc (registro[7]) é convertido para uma string de dois dígitos.

    Mapeamento (índices do QTableWidget):
      1  ← registro[4]  (descrição)
      3  ← registro[6]  (num_orc)
      4  ← ver_orc formatado (registro[7])
      5  ← registro[8]  (ref_le)
      6  ← registro[9]  (descricao_no_orcamento)
      7  ← registro[10] (ptab)
      8  ← registro[11] (pliq)
      9  ← registro[12] (desc1_plus)
      10 ← registro[13] (desc2_minus)
      11 ← registro[14] (und)
      12 ← registro[15] (desp)
      13 ← registro[16] (corres_orla_0_4)
      14 ← registro[17] (corres_orla_1_0)
      15 ← registro[18] (tipo)
      16 ← registro[19] (familia)
      17 ← registro[20] (comp_mp)
      18 ← registro[21] (larg_mp)
      19 ← registro[22] (esp_mp)

        # Índice BD | Campo        | Índice UI | Descrição
    # ---------|--------------|-----------|----------
    # 0        | id           | N/A       |
    # 1        | nome         | N/A       |
    # 2        | linha        | N/A       |
    # 3        | material(*)  | 0         | (* ou ferragem, etc.) -> Este mapeamento parece incorreto na docstring original. A coluna 0 da UI é o nome da linha.
    # 4        | descricao    | 1         |
    # 5        | id_<tipo>    | 2         | (id_mat, id_fer, etc.) -> Não está no SELECT original
    # 6        | num_orc      | 3         |
    # 7        | ver_orc      | 4         |
    # 8        | ref_le       | 5         |
    # 9        | desc_orc     | 6         |
    # 10       | ptab         | 7         |
    # 11       | pliq         | 8         |
    # 12       | desc1_plus   | 9         |
    # 13       | desc2_minus  | 10        |
    # 14       | und          | 11        |
    # 15       | desp         | 12        |
    # 16       | orla_0_4     | 13        |
    # 17       | orla_1_0     | 14        |
    # 18       | tipo         | 15        |
    # 19       | familia      | 16        |
    # 20       | comp_mp      | 17        |
    # 21       | larg_mp      | 18        |
    # 22       | esp_mp       | 19        |
    # --- REVISAR ESTE MAPEAMENTO CUIDADOSAMENTE ---
    """
    try:
        if column_names:
            dados = dict(zip(column_names, registro))
            mapeamento = {
                1: "descricao",
                3: "num_orc",
                4: "ver_orc",
                5: "ref_le",
                6: "descricao_no_orcamento",
                7: "ptab",
                8: "pliq",
                9: "desc1_plus",
                10: "desc2_minus",
                11: "und",
                12: "desp",
                13: "corres_orla_0_4",
                14: "corres_orla_1_0",
                15: "tipo",
                16: "familia",
                17: "comp_mp",
                18: "larg_mp",
                19: "esp_mp",
            }
            resultado = {}
            for ui_idx, col_nome in mapeamento.items():
                valor = dados.get(col_nome)
                if col_nome == "ver_orc":
                    valor = formatar_versao(str(valor) if valor is not None else "00")
                resultado[ui_idx] = valor
            return resultado
        # Assume que o SELECT * retorna as colunas na ordem de criação (id, nome, linha, ...)
        ver_orc_formatada = formatar_versao(
            str(registro[7]) if registro[7] is not None else "00")
        return {
            1: registro[4],   # descricao -> UI[1]
            3: registro[6],   # num_orc -> UI[3]
            4: ver_orc_formatada,  # ver_orc -> UI[4]
            5: registro[8],   # ref_le -> UI[5]
            6: registro[9],   # descricao_no_orcamento -> UI[6]
            7: registro[10],  # ptab -> UI[7]
            8: registro[11],  # pliq -> UI[8]
            9: registro[12],  # desc1_plus -> UI[9]
            10: registro[13],  # desc2_minus -> UI[10]
            11: registro[14],  # und -> UI[11]
            12: registro[15],  # desp -> UI[12]
            13: registro[16],  # corres_orla_0_4 -> UI[13]
            14: registro[17],  # corres_orla_1_0 -> UI[14]
            15: registro[18],  # tipo -> UI[15]
            16: registro[19],  # familia -> UI[16]
            17: registro[20],  # comp_mp -> UI[17]
            18: registro[21],  # larg_mp -> UI[18]
            19: registro[22]  # esp_mp -> UI[19]
        }
    except IndexError:
        print(
            f"[ERRO] mapear_registro_gerais: Registro inválido ou incompleto: {registro}")
        return {}  # Retorna dicionário vazio em caso de erro


# ---------------------------------------------------------------------------
# FUNÇÃO AUXILIAR: Carregar a configuração já salva na base para uma determinada tabela
# ---------------------------------------------------------------------------
def carregar_configuracao_dados_gerais(parent, nome_tabela):
    """
    Carrega os dados salvos na tabela 'dados_gerais_<nome_tabela>' para o orçamento atual,
    utilizando os valores de num_orc e ver_orc obtidos dos widgets.

    Parâmetros:
      parent     : objeto principal da aplicação (MainApp) – é usado como parent para os diálogos.
      nome_tabela: string com o nome da tabela de dados gerais (ex.: "materiais", "ferragens", etc.)

    Observação:
      Este exemplo preenche os QTableWidgets com os dados salvos, atualizando as colunas:
      num_orc, ver_orc, ref_le, descricao_no_orcamento, ptab, desc1_plus, desc2_minus,
      und, desp, corres_orla_0_4, corres_orla_1_0, tipo, familia, comp_mp, larg_mp, esp_mp.
      Para cada registro obtido do banco, os dados são reordenados e atribuídos às colunas
    do QTableWidget conforme a seguinte lógica:
      UI[1]  ← descricao (DB[4])
      UI[3]  ← num_orc   (DB[6])
      UI[4]  ← ver_orc   (DB[7])
      UI[5]  ← ref_le    (DB[8])
      UI[6]  ← descricao_no_orcamento (DB[9])
      UI[7]  ← ptab      (DB[10])
      UI[8]  ← pliq      (DB[11])
      UI[9]  ← desc1_plus (DB[12])
      UI[10] ← desc2_minus (DB[13])
      UI[11] ← und       (DB[14])
      UI[12] ← desp      (DB[15])
      UI[13] ← corres_orla_0_4 (DB[16])
      UI[14] ← corres_orla_1_0 (DB[17])
      UI[15] ← tipo      (DB[18])
      UI[16] ← familia   (DB[19])
      UI[17] ← comp_mp   (DB[20])
      UI[18] ← larg_mp   (DB[21])
      UI[19] ← esp_mp    (DB[22])
    """
    ui = parent.ui
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    # Aplica formatação na versão ao importar
    ver_orc = formatar_versao(ui.lineEdit_versao_orcamento.text())

    registros = []
    tabela_bd_segura = f"dados_gerais_{nome_tabela.replace(' ', '_').lower()}"
    print(
        f"Carregando configuração para '{nome_tabela}' (Orc: {num_orc}, Ver: {ver_orc})...")

    try:
        with obter_cursor() as cursor:
            # Carrega pela combinação de num_orc e ver_orc
            query = (
                f"SELECT * FROM `{tabela_bd_segura}` "
                f"WHERE num_orc=%s AND ver_orc=%s ORDER BY linha"
            )
            print(f"  Query: {query}")
            print(f"  Params: {(num_orc, ver_orc)}")
            cursor.execute(query, (num_orc, ver_orc))
            registros = cursor.fetchall()
            col_names = cursor.column_names
        print(f"  Encontrados {len(registros)} registos.")

    except mysql.connector.Error as err:
        if err.errno == 1146:
            print(f"Aviso: Tabela '{tabela_bd_segura}' não encontrada.")
        else:
            print(f"Erro MySQL ao carregar config '{nome_tabela}': {err}")
            QMessageBox.warning(parent, "Erro BD", f"Erro: {err}")
        return  # Retorna se não conseguiu carregar
    except Exception as e:
        print(f"Erro inesperado ao carregar config '{nome_tabela}': {e}")
        QMessageBox.critical(parent, "Erro", f"Erro: {e}")
        return

    # Seleciona o QTableWidget correspondente
    widget_map = {"materiais": ui.Tab_Material, "ferragens": ui.Tab_Ferragens,
                  "sistemas_correr": ui.Tab_Sistemas_Correr, "acabamentos": ui.Tab_Acabamentos}
    table = widget_map.get(nome_tabela)
    if not table:
        return

    table.blockSignals(True)
    table.setProperty("importando", True)
    try:
        row_count_ui = table.rowCount()
        print(f"  Preenchendo {min(len(registros), row_count_ui)} linhas na tabela UI '{table.objectName()}'.")
        for i in range(min(len(registros), row_count_ui)):
            registro_bd = registros[i]
            dados_mapeados = mapear_registro_gerais(registro_bd, col_names)  # Mapeia dados da BD para índices UI

            for col_idx_ui, valor_bd in dados_mapeados.items():
                if not (0 <= col_idx_ui < table.columnCount()):
                    continue  # Segurança

                # Formata o valor para exibição
                texto_formatado = ""
                if valor_bd is not None:
                    # Adapta a formatação baseada no ÍNDICE DA COLUNA UI
                    if col_idx_ui in [7, 8]:
                        texto_formatado = formatar_valor_moeda(valor_bd)
                    elif col_idx_ui in [9, 10, 12]:
                        texto_formatado = formatar_valor_percentual(valor_bd)
                    else:
                        texto_formatado = str(valor_bd)

                # Preenche a célula (widget ou item)
                widget = table.cellWidget(i, col_idx_ui)
                if isinstance(widget, QComboBox):
                    idx_combo = widget.findText(
                        texto_formatado, Qt.MatchFixedString)
                    widget.setCurrentIndex(idx_combo if idx_combo >= 0 else -1)
                else:
                    item = table.item(i, col_idx_ui)
                    if item is None:
                        item = QTableWidgetItem()
                        table.setItem(i, col_idx_ui, item)
                    item.setText(texto_formatado)

            # Preenche as colunas fixas num_orc e ver_orc (colunas 3 e 4)
            item_num = table.item(i, 3)
            if not item_num:
                item_num = QTableWidgetItem()
                table.setItem(i, 3, item_num)
            item_num.setText(num_orc)
            item_ver = table.item(i, 4)
            if not item_ver:
                item_ver = QTableWidgetItem()
                table.setItem(i, 4, item_ver)
            item_ver.setText(ver_orc)

        # A informação de carregamento automático foi removida para evitar
        # mensagens constantes ao alternar de separador ou ao abrir um
        # orçamento. Mantemos o preenchimento silencioso das tabelas.
    finally:
        table.setProperty("importando", False)
        table.blockSignals(False)
        table.resizeColumnsToContents()  # Ajusta as colunas para o conteúdo

# ---------------------------------------------------------------------------
# FUNÇÃO PRINCIPAL: Configurar Dados Gerais
# ---------------------------------------------------------------------------


def configurar_dados_gerais(parent):
    """
    Configura (ou carrega) os Dados Gerais dos 4 separadores (Materiais, Ferragens, Sistemas Correr e Acabamentos)
    para o orçamento atual.

    Primeiro, obtém os valores dos campos 'Num Orçamento' e 'Versão' na aba Orçamento.
    Em seguida, verifica se já existe alguma configuração salva no banco (usando, por exemplo, a tabela de Materiais):
      - Se existir, chama a função auxiliar para carregar os dados salvos para as 4 tabelas.
      - Se não existir, procede com o mapeamento manual: preenche (ou atualiza) as colunas
        "num_orc" (índice 3) e "ver_orc" (índice 4) (e possivelmente outras) com os valores atuais,
        perguntando ao usuário se houver divergência.
    Ao final, alterna a visualização para a aba "Dados Gerais MP".

    Parâmetros:
      parent: objeto principal da aplicação (MainApp) que possui o atributo ui.
    """
    ui = parent.ui
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    ver_orc = formatar_versao(ui.lineEdit_versao_orcamento.text())
    if not num_orc or not ver_orc:
        QMessageBox.warning(
            parent, "Aviso", "Preencha os campos 'Num Orçamento' e 'Versão'.")
        return

    # Verifica se já existe configuração salva na tabela de Materiais (pode ser usada como referência)
    count_materiais = 0
    tabela_referencia = "dados_gerais_materiais"  # Usa materiais como referência
    try:
        with obter_cursor() as cursor:
            # Verifica se já existe configuração para este num_orc e ver_orc
            query_check = (
                f"SELECT COUNT(*) FROM `{tabela_referencia}` "
                f"WHERE num_orc=%s AND ver_orc=%s"
            )
            cursor.execute(query_check, (num_orc, ver_orc))
            resultado = cursor.fetchone()
            if resultado: count_materiais = resultado[0]

    except mysql.connector.Error as err:
        if err.errno == 1146:
            # Tabela não existe, é a primeira vez
            print(f"Tabela '{tabela_referencia}' não existe ainda.")
        else:
            print(f"Erro MySQL ao verificar dados gerais: {err}")
            QMessageBox.critical(parent, "Erro BD", f"Erro: {err}")
        count_materiais = 0  # Assume que não existe se houver erro
    except Exception as e:
        print(f"Erro inesperado ao verificar dados gerais: {e}")
        QMessageBox.critical(parent, "Erro", f"Erro: {e}")
        count_materiais = 0  # Assume que não existe se houver erro

    if count_materiais > 0:
        # Se existir, carrega os dados salvos para as 4 tabelas
        carregar_configuracao_dados_gerais(parent, "materiais")
        carregar_configuracao_dados_gerais(parent, "ferragens")
        carregar_configuracao_dados_gerais(parent, "sistemas_correr")
        carregar_configuracao_dados_gerais(parent, "acabamentos")
    else:
        # Nenhum dado encontrado para este orçamento: limpa possíveis dados existentes
        limpar_todas_tabelas_dados_gerais(parent)
    

    # Ao final, alterna a visualização para a aba "Dados Gerais MP"
    for i in range(ui.tabWidget_orcamento.count()):
        widget = ui.tabWidget_orcamento.widget(i)
        if widget.objectName() in ("dados_gerais_mp", "tab_dados_gerais_mp"):
            ui.tabWidget_orcamento.setCurrentIndex(i)
            break

# ---------------------------------------------------------------------------
# FUNÇÃO: Carrega automaticamente dados gerais se existirem
# ---------------------------------------------------------------------------
def carregar_dados_gerais_se_existir(parent):
    """Preenche as quatro tabelas de dados gerais caso já existam
    registros para o orçamento atual."""
    ui = parent.ui
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    ver_orc = formatar_versao(ui.lineEdit_versao_orcamento.text())
    if not num_orc or not ver_orc:
        return

    # Identificador usado quando os dados foram gravados previamente
    nome_modelo = f"{num_orc}-{ver_orc}"  # Mantido apenas para unicidade interna
    tabela_ref = "dados_gerais_materiais"
    existe = 0
    try:
        with obter_cursor() as cursor:
            cursor.execute(
                f"SELECT COUNT(*) FROM `{tabela_ref}` WHERE num_orc=%s AND ver_orc=%s",
                (num_orc, ver_orc),
            )
            res = cursor.fetchone()
            if res:
                existe = res[0]
    except Exception as e:
        print(f"Erro ao verificar dados gerais existentes: {e}")
        return

    if existe > 0:
        carregar_configuracao_dados_gerais(parent, "materiais")
        carregar_configuracao_dados_gerais(parent, "ferragens")
        carregar_configuracao_dados_gerais(parent, "sistemas_correr")
        carregar_configuracao_dados_gerais(parent, "acabamentos")
    else:
        limpar_todas_tabelas_dados_gerais(parent)

def limpar_todas_tabelas_dados_gerais(parent):
    """Remove dados das quatro tabelas de dados gerais."""
    ui = parent.ui
    tabelas = [
        (ui.Tab_Material, COLUNAS_LIMPAR_MATERIAIS),
        (ui.Tab_Ferragens, COLUNAS_LIMPAR_FERRAGENS),
        (ui.Tab_Sistemas_Correr, COLUNAS_LIMPAR_SISTEMAS_CORRER),
        (ui.Tab_Acabamentos, COLUNAS_LIMPAR_ACABAMENTOS),
    ]
    for tabela, cols in tabelas:
        for row in range(tabela.rowCount()):
            limpar_linha_dados_gerais(tabela, row, cols)

# ---------------------------------------------------------------------------
# FUNÇÃO AUXILIAR: Guarda os dados da tabela no banco de dados
# ---------------------------------------------------------------------------
def guardar_por_tabela(parent, nome_tabela, table_widget, mapping, col_names_db):
    """
    Salva os dados do QTableWidget da aba 'dados_gerais_<nome_tabela>' no banco de dados,
    associando-os ao orçamento atual (usando os campos num_orc e ver_orc).

    Parâmetros:
      parent     : objeto principal (MainApp) que possui o atributo ui.
      nome_tabela: string com o nome (ex.: "materiais").
      table_widget: QTableWidget da aba correspondente.
      mapping    : dicionário mapeando os nomes dos campos para os índices das colunas no QTableWidget.
      col_names  : lista com os nomes das colunas a serem inseridas no banco, na ordem desejada.

    Retorna True se os dados foram gravados com sucesso; False caso contrário.
    """
    ui = parent.ui
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    ver_orc = formatar_versao(ui.lineEdit_versao_orcamento.text())
    # Identificador utilizado anteriormente (mantido apenas para mensagens)  # Usa o numero e a versao do orçamento para criar um identificador unico.
    nome_registro = f"{num_orc}-{ver_orc}"

    if not num_orc or not ver_orc:
        QMessageBox.warning(
            parent, "Aviso", "Os campos 'Num Orçamento' e 'Versão' devem estar preenchidos!")
        return False

    num_rows = table_widget.rowCount()
    dados_para_salvar = []
    campos_moeda = {"ptab", "pliq"}
    campos_percentual = {"desc1_plus", "desc2_minus", "desp"}

    # Coleta dados da UI
    for row in range(num_rows):
        # Garante que as colunas num_orc e ver_orc estejam preenchidas na UI.
        # Se o utilizador não tiver configurado manualmente estas colunas,
        # definimo-las aqui para evitar que sejam gravadas como NULL.
        item_num = table_widget.item(row, 3)
        if item_num is None:
            item_num = QTableWidgetItem()
            table_widget.setItem(row, 3, item_num)
        if not item_num.text().strip():
            item_num.setText(num_orc)

        item_ver = table_widget.item(row, 4)
        if item_ver is None:
            item_ver = QTableWidgetItem()
            table_widget.setItem(row, 4, item_ver)
        if not item_ver.text().strip():
            item_ver.setText(ver_orc)

        # Preenche o identificador (id_mat/id_fer/id_sc/id_acb) se existir.
        col_id = mapping.get('id_mat') or mapping.get('id_fer') \
                 or mapping.get('id_sc') or mapping.get('id_acb')
        if col_id is not None and col_id < table_widget.columnCount():
            item_id = table_widget.item(row, col_id)
            if item_id is None:
                item_id = QTableWidgetItem()
                table_widget.setItem(row, col_id, item_id)
            if not item_id.text().strip():
                item_id.setText(str(row))

        # Primeiro, adiciona o identificador da linha e as referências
        # do orçamento. As colunas 'nome' e 'descricao_modelo' devem
        # permanecer nulas quando os dados são gravados através deste
        # diálogo.
        dados_linha = {
            'nome': None,
            'linha': row,
            'num_orc': num_orc,
            'ver_orc': ver_orc,
        }

        # Adiciona as colunas mapeadas
        for campo_bd, col_ui in mapping.items():
            if col_ui >= table_widget.columnCount():
                continue  # Segurança

            widget = table_widget.cellWidget(row, col_ui)
            valor_str = ""
            if widget and isinstance(widget, QComboBox):
                valor_str = widget.currentText()
            else:
                item = table_widget.item(row, col_ui)
                valor_str = item.text() if item else ""

            valor_final = None
            if valor_str:
                if campo_bd in campos_moeda:
                    try:
                        valor_final = converter_texto_para_valor(
                            valor_str, "moeda")
                    except:
                        valor_final = None
                elif campo_bd in campos_percentual:
                    try:
                        valor_final = converter_texto_para_valor(
                            valor_str, "percentual")
                    except:
                        valor_final = None
                else:
                    valor_final = valor_str.strip() if valor_str else None
            dados_linha[campo_bd] = valor_final

        # Cria tupla na ordem correta das colunas do BD: nome nulo
        # seguido pelo número da linha e demais campos.
        tupla_linha = [dados_linha.get('nome'), row] + \
            [dados_linha.get(cn, None) for cn in col_names_db]
        dados_para_salvar.append(tuple(tupla_linha))

    # Monta a query INSERT
    tabela_bd_segura = f"dados_gerais_{nome_tabela.replace(' ', '_').lower()}"
    # Nomes das colunas BD para INSERT. As colunas 'nome' e
    # 'descricao_modelo' não são utilizadas neste contexto.
    col_names_insert = ['nome', 'linha'] + col_names_db
    placeholders = ", ".join(["%s"] * len(col_names_insert))
    col_names_sql = ", ".join(f"`{c}`" for c in col_names_insert)
    # Utiliza INSERT simples. Os registros antigos já foram eliminados com
    # apagar_registros_por_orcamento(), portanto não é necessário usar REPLACE.
    query_insert = (
        f"INSERT INTO `{tabela_bd_segura}` ({col_names_sql}) VALUES ({placeholders})"
    )

    try:
        # Usa obter_cursor para a transação de inserção
        with obter_cursor() as cursor:
            # A exclusão dos dados antigos (se o nome já existia)
            # deve ser feita ANTES de chamar esta função, idealmente em guardar_dados_gerais_orcamento
            # ou obter_nome_para_salvar.
            # Aqui apenas inserimos:
            cursor.executemany(query_insert, dados_para_salvar)
        # Commit automático
        print(
            f"Dados para '{nome_tabela}' (Modelo: {nome_registro}) guardados.")
        return True
    except mysql.connector.Error as err:
        print(
            f"Erro MySQL ao guardar dados gerais para '{nome_tabela}': {err}")
        QMessageBox.critical(parent, "Erro Base de Dados",
                             f"Erro ao guardar '{nome_tabela}':\n{err}")
        return False
    except Exception as e:
        print(
            f"Erro inesperado ao guardar dados gerais para '{nome_tabela}': {e}")
        QMessageBox.critical(parent, "Erro Inesperado",
                             f"Erro ao guardar '{nome_tabela}':\n{e}")
        import traceback
        traceback.print_exc()
        return False


# ---------------------------------------------------------------------------
# FUNÇÃO PARA GRAVAR OS DADOS GERAIS DO ORÇAMENTO
# ---------------------------------------------------------------------------
def guardar_dados_gerais_orcamento(parent):
    """
    Função principal que guarda os dados gerais de um orçamento, associando os dados
    de cada uma das 4 abas (materiais, ferragens, sistemas_correr e acabamentos) ao orçamento
    atual (identificado por num_orc e ver_orc).

    Para cada tabela, chama a função auxiliar guardar_por_tabela() (definida abaixo) com o mapeamento
    específico de índices e nomes de colunas.

    Retorna True se todos os dados foram salvos com sucesso, False caso contrário.
    """
    ui = parent.ui
    sucesso = True

    # Identificador a ser utilizado nas tabelas de BD
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    ver_orc = formatar_versao(ui.lineEdit_versao_orcamento.text())
    nome_registro = f"{num_orc}_{ver_orc}"

    # Remove registos anteriores deste orçamento utilizando num_orc e ver_orc  elimina registas nas 4 tabelas dados gerais
    for tabela in ("materiais", "ferragens", "sistemas_correr", "acabamentos"):
        apagar_registros_por_orcamento(tabela, num_orc, ver_orc)

    # Mapeamento e nomes de colunas para a aba Materiais
    mapping_materiais = {
        "material": 0,
        "descricao": 1,
        "id_mat": 2,
        "num_orc": 3,
        "ver_orc": 4,
        "ref_le": 5,
        "descricao_no_orcamento": 6,
        "ptab": 7,
        "pliq": 8,
        "desc1_plus": 9,
        "desc2_minus": 10,
        "und": 11,
        "desp": 12,
        "corres_orla_0_4": 13,
        "corres_orla_1_0": 14,
        "tipo": 15,
        "familia": 16,
        "comp_mp": 17,
        "larg_mp": 18,
        "esp_mp": 19
    }
    col_names_materiais = [
        "material", "descricao", "id_mat", "num_orc", "ver_orc",
        "ref_le", "descricao_no_orcamento", "ptab", "pliq",
        "desc1_plus", "desc2_minus", "und", "desp",
        "corres_orla_0_4", "corres_orla_1_0", "tipo", "familia",
        "comp_mp", "larg_mp", "esp_mp"
    ]
    if not guardar_por_tabela(parent, "materiais", ui.Tab_Material, mapping_materiais, col_names_materiais):
        sucesso = False

    # Mapeamento para a aba Ferragens
    mapping_ferragens = {
        "ferragens": 0,
        "descricao": 1,
        "id_fer": 2,
        "num_orc": 3,
        "ver_orc": 4,
        "ref_le": 5,
        "descricao_no_orcamento": 6,
        "ptab": 7,
        "pliq": 8,
        "desc1_plus": 9,
        "desc2_minus": 10,
        "und": 11,
        "desp": 12,
        "corres_orla_0_4": 13,
        "corres_orla_1_0": 14,
        "tipo": 15,
        "familia": 16,
        "comp_mp": 17,
        "larg_mp": 18,
        "esp_mp": 19
    }
    col_names_ferragens = [
        "ferragens", "descricao", "id_fer", "num_orc", "ver_orc",
        "ref_le", "descricao_no_orcamento", "ptab", "pliq",
        "desc1_plus", "desc2_minus", "und", "desp",
        "corres_orla_0_4", "corres_orla_1_0", "tipo", "familia",
        "comp_mp", "larg_mp", "esp_mp"
    ]
    if not guardar_por_tabela(parent, "ferragens", ui.Tab_Ferragens, mapping_ferragens, col_names_ferragens):
        sucesso = False

    # Mapeamento para a aba Sistemas Correr
    mapping_sistemas_correr = {
        "sistemas_correr": 0,
        "descricao": 1,
        "id_sc": 2,
        "num_orc": 3,
        "ver_orc": 4,
        "ref_le": 5,
        "descricao_no_orcamento": 6,
        "ptab": 7,
        "pliq": 8,
        "desc1_plus": 9,
        "desc2_minus": 10,
        "und": 11,
        "desp": 12,
        "corres_orla_0_4": 13,
        "corres_orla_1_0": 14,
        "tipo": 15,
        "familia": 16,
        "comp_mp": 17,
        "larg_mp": 18,
        "esp_mp": 19
    }
    col_names_sistemas_correr = [
        "sistemas_correr", "descricao", "id_sc", "num_orc", "ver_orc",
        "ref_le", "descricao_no_orcamento", "ptab", "pliq",
        "desc1_plus", "desc2_minus", "und", "desp",
        "corres_orla_0_4", "corres_orla_1_0", "tipo", "familia",
        "comp_mp", "larg_mp", "esp_mp"
    ]
    if not guardar_por_tabela(parent, "sistemas_correr", ui.Tab_Sistemas_Correr, mapping_sistemas_correr, col_names_sistemas_correr):
        sucesso = False

    # Mapeamento para a aba Acabamentos
    mapping_acabamentos = {
        "acabamentos": 0,
        "descricao": 1,
        "id_acb": 2,
        "num_orc": 3,
        "ver_orc": 4,
        "ref_le": 5,
        "descricao_no_orcamento": 6,
        "ptab": 7,
        "pliq": 8,
        "desc1_plus": 9,
        "desc2_minus": 10,
        "und": 11,
        "desp": 12,
        "corres_orla_0_4": 13,
        "corres_orla_1_0": 14,
        "tipo": 15,
        "familia": 16,
        "comp_mp": 17,
        "larg_mp": 18,
        "esp_mp": 19
    }
    col_names_acabamentos = [
        "acabamentos", "descricao", "id_acb", "num_orc", "ver_orc",
        "ref_le", "descricao_no_orcamento", "ptab", "pliq",
        "desc1_plus", "desc2_minus", "und", "desp",
        "corres_orla_0_4", "corres_orla_1_0", "tipo", "familia",
        "comp_mp", "larg_mp", "esp_mp"
    ]
    if not guardar_por_tabela(parent, "acabamentos", ui.Tab_Acabamentos, mapping_acabamentos, col_names_acabamentos):
        sucesso = False

    if sucesso:
        QMessageBox.information(
            parent, "Sucesso", "Dados gerais do orçamento guardados com sucesso em todas as tabelas.")
    else:
        QMessageBox.warning(
            parent, "Aviso", "Ocorreu algum problema ao guardar os dados gerais do orçamento.")

# (Manter importar_dados_gerais_com_opcao e importar_dados_gerais_por_modelo como na resposta anterior,
#  pois elas já usam obter_cursor indiretamente através das funções que chamam)


def importar_dados_gerais_com_opcao(parent_app, nome_tabela, mapeamento, modelo_escolhido=None):
    # ... (código da função mantido como antes, já usa listar_nomes e obter_cursor indiretamente) ...
    ui = parent_app.ui
    modelos = listar_nomes_dados_gerais(nome_tabela)
    if not modelos:
        QMessageBox.information(parent_app, "Importar",
                                f"Nenhum registo salvo para '{nome_tabela}'.")
        return
    if modelo_escolhido is None:
          dlg = SelecaoModeloDialog(modelos, titulo=f"Importa Dados Gerais para tenho duvida o que é ? ->  {nome_tabela}", parent=parent_app)
          if dlg.exec_() != QDialog.Accepted:
               return
          modelo_escolhido = dlg.modelo_escolhido()
          if not modelo_escolhido: return
    opcoes = ["Manter dados gravados no BD",
              "Atualizar com dados de matérias primas"]
    opcao_selecionada, ok = QInputDialog.getItem(
        parent_app, "Opção", f"Importar <b>{nome_tabela.upper()}<b>?", opcoes, 0, False)
    if not ok or not opcao_selecionada:
        return

    tabela_widgets = {"materiais": ui.Tab_Material, "ferragens": ui.Tab_Ferragens,
                      "sistemas_correr": ui.Tab_Sistemas_Correr, "acabamentos": ui.Tab_Acabamentos}
    table = tabela_widgets.get(nome_tabela)
    if not table:
        QMessageBox.warning(parent_app, "Erro",
                            f"Tabela UI '{nome_tabela}' não encontrada.")
        return

    registros_bd = []
    try:
        tabela_bd_segura = f"dados_gerais_{nome_tabela.replace(' ', '_').lower()}"
        colunas_select = ['linha'] + list(mapeamento.keys())
        colunas_sql = ", ".join(f"`{c}`" for c in colunas_select)
        query = f"SELECT {colunas_sql} FROM `{tabela_bd_segura}` WHERE nome = %s ORDER BY linha"
        with obter_cursor() as cursor:
            cursor.execute(query, (modelo_escolhido,))
            registros_bd = cursor.fetchall()
        if not registros_bd:
            QMessageBox.information(
                parent_app, "Importar", f"Nenhum dado para '{modelo_escolhido}'.")
            return

        table.blockSignals(True)
        table.setProperty("importando", True)
        row_count_ui = table.rowCount()
        dados_mp_cache = {}
        for reg_bd in registros_bd:
            reg_dict = dict(zip(colunas_select, reg_bd))
            linha_ui = reg_dict.get('linha')
            if linha_ui is None or not (0 <= linha_ui < row_count_ui):
                continue
            if opcao_selecionada == "Manter dados gravados no BD":
                for campo_bd, col_ui in mapeamento.items():
                    valor_bd = reg_dict.get(campo_bd)
                    texto_formatado = ""
                    if valor_bd is not None:
                        if campo_bd in ("pliq", "ptab", "comp_mp", "larg_mp", "esp_mp"):
                            texto_formatado = formatar_valor_moeda(valor_bd)
                        elif campo_bd in ("desc1_plus", "desc2_minus", "desp"):
                            texto_formatado = formatar_valor_percentual(
                                valor_bd)
                        else:
                            texto_formatado = str(valor_bd)
                    widget = table.cellWidget(linha_ui, col_ui)
                    if isinstance(widget, QComboBox):
                        idx = widget.findText(
                            texto_formatado, Qt.MatchFixedString)
                        widget.setCurrentIndex(idx if idx >= 0 else -1)
                    else:
                        item = table.item(linha_ui, col_ui)
                        if not item:
                            item = QTableWidgetItem()
                            table.setItem(linha_ui, col_ui, item)
                        item.setText(texto_formatado)
            else:  # Atualizar com Matérias-Primas
                ref_le = reg_dict.get("ref_le")
                dados_atuais_mp = None
                if ref_le:
                    if ref_le in dados_mp_cache:
                        dados_atuais_mp = dados_mp_cache[ref_le]
                    else:
                        with obter_cursor() as cursor_mp:
                            cursor_mp.execute(
                                "SELECT DESCRICAO_no_ORCAMENTO, PRECO_TABELA, PLIQ, DESC1_PLUS, DESC2_MINUS, UND, DESP, CORESP_ORLA_0_4, CORESP_ORLA_1_0, COMP_MP, LARG_MP, ESP_MP FROM materias_primas WHERE Ref_LE = %s", (ref_le,))
                            dados_atuais_mp = cursor_mp.fetchone()
                            dados_mp_cache[ref_le] = dados_atuais_mp
                if dados_atuais_mp:
                    map_mp_cols = ["descricao_no_orcamento", "ptab", "pliq", "desc1_plus", "desc2_minus",
                                   "und", "desp", "corres_orla_0_4", "corres_orla_1_0", "comp_mp", "larg_mp", "esp_mp"]
                    dados_mp_dict = dict(zip(map_mp_cols, dados_atuais_mp))
                    for campo_mp, col_ui in mapeamento.items():
                        if campo_mp in dados_mp_dict:
                            valor_bd = dados_mp_dict[campo_mp]
                            texto_formatado = ""
                            if valor_bd is not None:
                                if campo_mp in ("pliq", "ptab", "comp_mp", "larg_mp", "esp_mp"):
                                    texto_formatado = formatar_valor_moeda(
                                        valor_bd)
                                elif campo_mp in ("desc1_plus", "desc2_minus", "desp"):
                                    texto_formatado = formatar_valor_percentual(
                                        valor_bd)
                                else:
                                    texto_formatado = str(valor_bd)
                            widget = table.cellWidget(linha_ui, col_ui)
                            if isinstance(widget, QComboBox):
                                idx = widget.findText(
                                    texto_formatado, Qt.MatchFixedString)
                                widget.setCurrentIndex(idx if idx >= 0 else -1)
                            else:
                                item = table.item(linha_ui, col_ui)
                                if not item:
                                    item = QTableWidgetItem()
                                    table.setItem(linha_ui, col_ui, item)
                                item.setText(texto_formatado)
                        elif campo_bd == "ref_le":  # Mantem ref_le original se dados_mp não encontrado
                            valor_bd = reg_dict.get(campo_bd)
                            texto_formatado = str(
                                valor_bd) if valor_bd is not None else ""
                            item = table.item(linha_ui, col_ui)
                            if not item:
                                item = QTableWidgetItem()
                                table.setItem(linha_ui, col_ui, item)
                            item.setText(texto_formatado)
                else:  # Se não encontrou em matérias-primas, mantém dados gerais originais
                    print(
                        f"Aviso: Ref_LE '{ref_le}' não encontrado em matérias-primas (linha {linha_ui}). Mantendo dados gerais.")
                    for campo_bd, col_ui in mapeamento.items():
                        valor_bd = reg_dict.get(campo_bd)
                        texto_formatado = ""
                        if valor_bd is not None:
                            if campo_bd in ("pliq", "ptab", "comp_mp", "larg_mp", "esp_mp"):
                                texto_formatado = formatar_valor_moeda(
                                    valor_bd)
                            elif campo_bd in ("desc1_plus", "desc2_minus", "desp"):
                                texto_formatado = formatar_valor_percentual(
                                    valor_bd)
                            else:
                                texto_formatado = str(valor_bd)
                        widget = table.cellWidget(linha_ui, col_ui)
                        if isinstance(widget, QComboBox):
                            idx = widget.findText(
                                texto_formatado, Qt.MatchFixedString)
                            widget.setCurrentIndex(idx if idx >= 0 else -1)
                        else:
                            item = table.item(linha_ui, col_ui)
                            if not item:
                                item = QTableWidgetItem()
                                table.setItem(linha_ui, col_ui, item)
                            item.setText(texto_formatado)
        table.setProperty("importando", False)
        table.blockSignals(False)
        QMessageBox.information(parent_app, "Importar Dados Gerais",
                                f"Dados importados (Modelo: {modelo_escolhido}, Opção: {opcao_selecionada}).")
    except mysql.connector.Error as err:
        table.setProperty("importando", False)
        table.blockSignals(False)
        print(f"Erro BD: {err}")
        QMessageBox.critical(parent_app, "Erro", f"Erro BD: {err}")
    except Exception as e:
        table.setProperty("importando", False)
        table.blockSignals(False)
        print(f"Erro: {e}")
        QMessageBox.critical(parent_app, "Erro", f"Erro: {e}")
        import traceback
        traceback.print_exc()


def listar_nomes_dados_gerais(nome_tabela):
    """
    Retorna a lista de valores distintos de 'nome' da tabela
    dados_gerais_<nome_tabela>.
    """
    tabela_bd = f"dados_gerais_{nome_tabela.replace(' ', '_').lower()}"
    try:
        with obter_cursor() as cursor:
            cursor.execute(f"SELECT DISTINCT nome FROM `{tabela_bd}`")
            return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"Erro ao listar nomes de dados gerais para {nome_tabela}: {e}")
        return []


def importar_dados_gerais_por_modelo(parent_app, nome_tabela, mapeamento, modelo):
    """Importa dados de um modelo específico SEM interação."""
    # (Código mantido como na resposta anterior, já usa obter_cursor indiretamente)
    ui = parent_app.ui
    print(f"Importando modelo '{modelo}' para '{nome_tabela}'...")
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
            QMessageBox.information(
                parent_app, "Importar", f"Nenhum dado para '{modelo}'.")
            return
        tabela_widgets = {"materiais": ui.Tab_Material, "ferragens": ui.Tab_Ferragens,
                          "sistemas_correr": ui.Tab_Sistemas_Correr, "acabamentos": ui.Tab_Acabamentos}
        table = tabela_widgets.get(nome_tabela)
        if not table:
            return
        row_count_ui = table.rowCount()
        table.blockSignals(True)
        table.setProperty("importando", True)
        for reg_bd in registros_bd:
            reg_dict = dict(zip(colunas_select, reg_bd))
            linha_ui = reg_dict.get('linha')
            if linha_ui is None or not (0 <= linha_ui < row_count_ui):
                continue
            for campo_bd, col_ui in mapeamento.items():
                valor_bd = reg_dict.get(campo_bd)
                texto_formatado = ""
                if valor_bd is not None:
                    if campo_bd in ("pliq", "ptab", "comp_mp", "larg_mp", "esp_mp"):
                        texto_formatado = formatar_valor_moeda(valor_bd)
                    elif campo_bd in ("desc1_plus", "desc2_minus", "desp"):
                        texto_formatado = formatar_valor_percentual(valor_bd)
                    else:
                        texto_formatado = str(valor_bd)
                widget = table.cellWidget(linha_ui, col_ui)
                if isinstance(widget, QComboBox):
                    idx = widget.findText(texto_formatado, Qt.MatchFixedString)
                    widget.setCurrentIndex(idx if idx >= 0 else -1)
                else:
                    item = table.item(linha_ui, col_ui)
                    if not item:
                        item = QTableWidgetItem()
                        table.setItem(linha_ui, col_ui, item)
                    item.setText(texto_formatado)
        table.setProperty("importando", False)
        table.blockSignals(False)
        QMessageBox.information(
            parent_app, "Importar", f"Modelo '{modelo}' importado para '{nome_tabela}'.")
    except mysql.connector.Error as err:
        table.setProperty("importando", False)
        table.blockSignals(False)
        print(f"Erro BD: {err}")
        QMessageBox.critical(parent_app, "Erro", f"Erro BD: {err}")
    except Exception as e:
        table.setProperty("importando", False)
        table.blockSignals(False)
        print(f"Erro: {e}")
        QMessageBox.critical(parent_app, "Erro", f"Erro: {e}")
        import traceback
        traceback.print_exc()
