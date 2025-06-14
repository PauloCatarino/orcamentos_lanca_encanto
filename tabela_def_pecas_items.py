# tabela_def_pecas_items.py
# -*- coding: utf-8 -*-

# imagem-> tabela_def_pecas_items.png

"""
Módulo: tabela_def_pecas_items.py

Objetivo:
---------
Este módulo gerencia a interação com a tabela 'tab_def_pecas' (QTableWidget),
incluindo:
  - Inserção inicial de peças selecionadas dos QListWidget.
  - Manipulação de linhas (excluir, inserir, copiar) através de menu de contexto.
  - Configuração de Delegates para colunas específicas (Def_Peca, Mat_Default, células editáveis).
  - Funções auxiliares para atualizar IDs e manipular dados de linha.
  - Processamento inicial de dados ao selecionar/alterar peças ou materiais (chamando o orquestrador).

O processo de inserção é dividido:
  - Inserção Inicial: Preenche APENAS as colunas básicas e de identificação.
  - Processamento Completo: É despoletado pelo módulo 'modulo_orquestrador' (via botão "Atualizar Preços" ou carregamento)
    e preenche/calcula as colunas restantes, incluindo dados adicionais e componentes associados.

Observação:
------------
Para que o delegate do ComboBox em "Def_Peca" funcione, o grupo de origem do item
(caixote, ferragens, etc.) é armazenado no Qt.UserRole do QTableWidgetItem.
"""

from utils import set_item  # (Já incluído na importação de utils no topo)
from utils import safe_item_text
from PyQt5.QtWidgets import QTableWidgetItem, QMenu, QStyledItemDelegate, QComboBox, QAbstractItemView, QMessageBox, QLineEdit, QPushButton, QStyle
from PyQt5.QtCore import Qt, QTimer, QEvent, QObject
from PyQt5.QtGui import QColor, QPen
import openpyxl
import os
import decimal
import pandas as pd
import mysql.connector
# Importações de funções utilitárias (formatação/conversão de valores, filtros de dados etc.)
# Assumimos que utils.py contém converter_texto_para_valor, formatar_valor_moeda, formatar_valor_percentual
from utils import (formatar_valor_moeda, formatar_valor_percentual, converter_texto_para_valor,
                   validar_expressao_modulo, set_item, safe_item_text, VARIAVEIS_VALIDAS)
# Importa a função de orquestração central - crucial para o novo fluxo
# Importação feita localmente na função inserir_pecas_selecionadas para evitar dependência circular no topo
# Importa a função para aplicar formatação visual ao BLK coluna 12 'Bloqueado'
from aplicar_formatacao_visual_blk import aplicar_ou_limpar_formatacao_blk

# Importa as cores para os componentes associados e MODULO
from modulo_componentes_associados import COLOR_ASSOCIATED_BG, COLOR_MODULO_BG
# Importa a função para o botão "Escolher" (MP) na tabela
from modulo_orquestrador import atualizar_tudo

# Importa a função para aplicar o combobox na coluna Mat_Default
from tabela_def_pecas_combobox_mat_default import aplicar_combobox_mat_default
# Importa a função para consultar a base de dados
from db_connection import obter_cursor

# Importa a função para abrir o diálogo de seleção de material (necessário para o botão "Escolher")
# Importação feita localmente na função escolher_material_item para evitar dependência circular

# Importa a função auxiliar para atualizar as chaves na tab_modulo_medidas
# from modulo_dados_definicoes import actualizar_ids_num_orc_ver_orc_tab_modulo_medidas

# Índices das colunas de componentes associados (COMP_ASS_1..3)
IDX_PTAB = 20
IDX_PLIQ = 21
IDX_DES1PLUS = 22
IDX_DES1MINUS = 23
IDX_DESP = 25
IDX_QT_MOD = 4
IDX_QT_UND = 5
IDX_COMP = 6
IDX_LARG = 7
IDX_ESP = 8
IDX_COMP_ASS_1 = 34  # Componente Associado na coluna 34 tab_def_pecas
IDX_COMP_ASS_2 = 35
IDX_COMP_ASS_3 = 36


IDX_DEF_PECA = 2   # Coluna para Def_Peca
IDX_QT_MOD = 4   # Coluna que contém a quantidade modificada (QT_mod)
IDX_QT_UND = 5   # Coluna que contém a quantidade unitária (QT_und)
IDX_COMP = 6   # Coluna para COMP (comprimento, etc.) - Fórmula
IDX_LARG = 7   # Coluna para LARG (largura) - Fórmula
IDX_ESP = 8   # Coluna para ESP (espesura) - Fórmula
IDX_BLK = 12  # Checkbox BLK - Bloqueia atualização automática

##############################################
# Parte 1: Função para inserir peças na tabela
##############################################


def inserir_pecas_selecionadas(ui):
    """
    Percorre os 7 QListWidget e, para cada item com checkbox marcado (Qt.Checked),
    insere uma nova linha na tabela 'tab_def_pecas'.

    Esta função preenche APENAS as colunas básicas e de identificação inicial:
      0  -> id (será atualizado depois por update_ids)
      1  -> Descricao_Livre (vazio)
      2  -> Def_Peca (texto do item do QListWidget)
      3  -> Descricao (vazio - será preenchido por atualizar_dados_def_peca)
      4  -> QT_mod (vazio - será preenchido pelo orquestrador)
      5  -> QT_und (vazio - será preenchido pelo orquestrador e formatado)
      6  -> Comp (vazio - será preenchido pelo orquestrador)
      7  -> Larg (vazio - será preenchido pelo orquestrador)
      8  -> Esp (vazio - será preenchido por atualizar_dados_def_peca)
      9  -> MPs (checkbox - Unchecked)
      10 -> MO (checkbox - Unchecked)
      11 -> Orla (checkbox - Unchecked)
      12 -> BLK (checkbox - Unchecked)
      13 -> Mat_Default (valor do UserRole+1 do item do QListWidget)
      14 -> Tab_Default (valor do UserRole+2 do item do QListWidget)
      15 -> ids (do lineEdit_item_orcamento)
      16 -> num_orc (do lineEdit_num_orcamento)
      17 -> ver_orc (do lineEdit_versao_orcamento)
      33 -> MP (botão "Escolher")
      53 -> GRAVAR_MODULO (checkbox - Unchecked)
      59 -> ACB_SUP (checkbox - Unchecked)
      60 -> ACB_INF (checkbox - Unchecked)
      As colunas 18-32, 34-36, 37-81 SÃO DEIXADAS VAZIAS NESTA FASE.

    Após inserir todas as linhas básicas, chama 'atualizar_tudo' para processar
    e preencher as restantes colunas, realizar cálculos e inserir componentes associados.
    Desmarca os checkboxes dos itens selecionados nos QListWidget.
    """
    print("[INFO] Iniciando inserção de peças selecionadas...")

    # Importa a função de orquestração - aqui para evitar dependência circular no topo
    from modulo_orquestrador import atualizar_tudo

    # Mapeamento da lista dos 7 QListWidget por grupo
    grupos_widgets = {
        "caixote": ui.listWidget_caixote_4,
        "ferragens": ui.listWidget_ferragens_4,
        "mao_obra": ui.listWidget_mao_obra_4,
        "paineis": ui.listWidget_paineis_4,
        "remates_guarnicoes": ui.listWidget_remates_guarnicoes_4,
        "sistemas_correr": ui.listWidget_sistemas_correr_4,
        "acabamentos": ui.listWidget_acabamentos_4
    }

    table = ui.tab_def_pecas
    table.setSelectionBehavior(QAbstractItemView.SelectRows)

    # 4) Valores de identificação do orçamento
    valor_ids = ui.lineEdit_item_orcamento.text().strip()
    valor_num_orc = ui.lineEdit_num_orcamento.text().strip()
    valor_ver_orc = ui.lineEdit_versao_orcamento.text().strip()

    # 5) Sincroniza colunas ids/num_orc/ver_orc na tab_modulo_medidas (parte 16)
    # Esta chamada já foi ajustada para apenas atualizar as flags na tab_modulo_medidas
    # NOTA: A função actualizar_ids_num_orc_ver_orc_tab_modulo_medidas foi movida para este ficheiro (parte 16)
    actualizar_ids_num_orc_ver_orc_tab_modulo_medidas(
        ui, valor_ids, valor_num_orc, valor_ver_orc)

    # Lista para coletar os itens que foram marcados para desmarcar depois
    items_a_desmarcar = []

    # 6) Para cada peça marcada, insere UI + banco básico
    # Evita triggers de BLK durante inserção
    table.setProperty("importando_dados", True)
    table.blockSignals(True)
    try:
        for grupo, lw in grupos_widgets.items():
            for i in range(lw.count()):
                item = lw.item(i)
                if item.checkState() != Qt.Checked:
                    continue

                texto_def_peca = item.text().strip()

                # Obter Mat_Default e Tab_Default do item do QListWidget
                mat_def = item.data(Qt.UserRole+1) or ""
                tab_def = item.data(Qt.UserRole+2) or ""

                # --- Inserção na UI ---
                row = table.rowCount()
                table.insertRow(row)

                # id (Temporário, será atualizado por update_ids no final)
                # set_item garante item existe, get item depois para flags
                set_item(table, row, 0, str(row+1))
                it_id = table.item(row, 0)
                it_id.setFlags(it_id.flags() & ~Qt.ItemIsEditable)

                # descricao_livre (Vazio inicial)
                set_item(table, row, 1, "")

                # def_peca
                set_item(table, row, 2, texto_def_peca)
                it_dp = table.item(row, 2)
                # Mantém editável para o delegate ComboBox
                it_dp.setFlags(it_dp.flags() | Qt.ItemIsEditable)
                # Armazena o grupo para o delegate
                it_dp.setData(Qt.UserRole, grupo)

                # Colunas Descricao, QT_mod, QT_und, Comp, Larg, Esp (Vazias iniciais)
                # Estas serão preenchidas/calculadas pelo orquestrador
                for col in [3, 4, 5, 6, 7, 8]:
                    set_item(table, row, col, "")

                # Checkboxes (Unchecked iniciais)
                # MPs, MO, Orla, BLK, GRAVAR_MODULO, ACB_SUP, ACB_INF
                for col in [9, 10, 11, 12, 53, 59, 60]:
                    chk = QTableWidgetItem()  # Cria novo item checkbox
                    chk.setFlags(Qt.ItemIsUserCheckable |
                                 Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    chk.setCheckState(Qt.Unchecked)
                    # Adiciona o novo item à tabela
                    table.setItem(row, col, chk)

                # mat_default / tab_default (Preenchidos com dados do QListWidget)
                set_item(table, row, 13, mat_def)
                set_item(table, row, 14, tab_def)

                # ids / num_orc / ver_orc (Preenchidos com dados da UI)
                set_item(table, row, 15, valor_ids)
                set_item(table, row, 16, valor_num_orc)
                set_item(table, row, 17, valor_ver_orc)

                # Colunas 18-32 (ref_le a esp_mp) e 34-81 SÃO DEIXADAS VAZIAS
                for col in range(18, 82):  # 18 até 81 (inclusive)
                    if col == 33:  # Salta a coluna 33 onde vai o botão MP
                        continue
                    set_item(table, row, col, "")

                # botão Escolher (col 33)
                btn = QPushButton("Escolher")
                # Conecta o botão à função de seleção de material, passando a linha atual
                btn.clicked.connect(
                    lambda _, r=row: on_mp_button_clicked(ui, r, "tab_def_pecas"))
                table.setCellWidget(row, 33, btn)

                # --- Caso MODULO: ajustes especiais iniciais ---
                # Estes ajustes são apenas visuais e de editabilidade NESTA FASE INICIAL
                # O preenchimento dos valores '1' e negrito será feito pelo orquestrador
                if texto_def_peca.upper() == "MODULO":
                    # Limpa defs iniciais para MODULO
                    set_item(table, row, 13, "")
                    set_item(table, row, 14, "")
                    # Quantidade do módulo é 1 por defeito (mantida internamente)
                    # mas a célula fica visualmente vazia
                    set_item(table, row, 4, "") # QT_mod -> qantidade por defeito = 1
                    # Habilita edição e negrito para Descricao_Livre, Comp, Larg, Esp (serão validados depois)
                    for col in [1, 6, 7, 8]:  # Descricao_Livre, Comp, Larg, Esp
                        item_col = table.item(row, col) or QTableWidgetItem("")
                        item_col.setFlags(item_col.flags() | Qt.ItemIsEditable)
                        font = item_col.font()
                        font.setBold(True)
                        item_col.setFont(font)
                    # Define a cor de fundo cinza-claro para a linha MODULO
                    for c in range(table.columnCount()):
                        item_c = table.item(row, c)
                        if item_c:
                            # Cinza mais claro
                            item_c.setBackground(QColor(220, 220, 220))

                # Adiciona o item à lista para desmarcar depois
                items_a_desmarcar.append(item)
    finally:
        table.blockSignals(False)
        table.setProperty("importando_dados", False)

    # 7) Pós-processamento:
    update_ids(table)  # Renumera os IDs após todas as inserções
    # Configura/reaplica menu de contexto e delegates (incluindo DefPecaDelegate)
    setup_context_menu(ui, None)
    # Aplica o ComboBox Mat_Default (AGORA, depois de inserir Mat_Default/Tab_Default)
    aplicar_combobox_mat_default(ui)

    # Conecta o sinal itemChanged se ainda não estiver conectado
    # Esta conexão deve estar no setup_context_menu ou em setup inicial da UI
    # Verifique se a conexão já existe em main.py ou setup_context_menu
    # if not table.property("itemChangedConnected"):
    #     table.itemChanged.connect(on_item_changed_def_pecas)
    #     table.setProperty("itemChangedConnected", True)

    # Desmarcar os checkboxes dos itens selecionados nos QListWidget
    for item in items_a_desmarcar:
        item.setCheckState(Qt.Unchecked)

    print(f"[INFO] {len(items_a_desmarcar)} peças básicas inseridas na tabela.")

    # --- CHAMA O ORQUESTRADOR PARA PROCESSAR TUDO ---
    # Isto garante que os dados adicionais são carregados, cálculos feitos
    # e componentes associados são inseridos para as linhas acabadas de adicionar.
    print("[INFO] Chamando o orquestrador (atualizar_tudo) para processar as linhas inseridas...")
    atualizar_tudo(ui)  # Passa a referência da UI

##############################################
# 10. Inserção de Linha para Componente Associado ->Insere linha diretamente por nome de peça (ex: ao processar componente associado)
##############################################


def inserir_linha_componente(ui, texto_peca):
    """
    Insere uma nova linha BÁSICA na tabela 'tab_def_pecas' com base no nome da peça (texto_peca),
    que representa um componente associado. Esta função é usada pela lógica de inserção
    de componentes associados (que deve estar no orquestrador ou ser chamada por ele).

    Preenche APENAS:
      0  -> id (será atualizado depois)
      1  -> Descricao_Livre (vazio)
      2  -> Def_Peca (texto_peca, com cor azul claro e grupo no UserRole)
      3-12 -> Vazias / Checkboxes (Unchecked)
      13 -> Mat_Default (do QListWidget lookup)
      14 -> Tab_Default (do QListWidget lookup)
      15-17 -> IDs/Orcamento (da UI)
      33 -> MP (botão "Escolher")
      53, 59, 60 -> Checkboxes (Unchecked)
      Outras colunas SÃO DEIXADAS VAZIAS.

    Não consulta DB para dados adicionais, não calcula, não insere outros associados,
    não chama atualizar_tudo. Apenas prepara a linha para o orquestrador processar.
    """
    print(
        f"[INFO] Preparando para inserir linha básica para componente associado: '{texto_peca}'...")

    table = ui.tab_def_pecas

    # Encontrar o grupo a que pertence o tipo de peça e obter Mat_Default/Tab_Default do QListWidget
    lista_widgets = {
        "caixote": ui.listWidget_caixote_4,
        "ferragens": ui.listWidget_ferragens_4,
        "mao_obra": ui.listWidget_mao_obra_4,
        "paineis": ui.listWidget_paineis_4,
        "remates_guarnicoes": ui.listWidget_remates_guarnicoes_4,
        "sistemas_correr": ui.listWidget_sistemas_correr_4,
        "acabamentos": ui.listWidget_acabamentos_4
    }

    grupo_encontrado = None
    mat_default = ""
    tab_default = ""

    for grupo, widget in lista_widgets.items():
        for i in range(widget.count()):
            item = widget.item(i)
            if item.text().strip().upper() == texto_peca.strip().upper():
                grupo_encontrado = grupo
                mat_default = item.data(Qt.UserRole + 1) or ""
                tab_default = item.data(Qt.UserRole + 2) or ""
                break
        if grupo_encontrado:
            break

    if not grupo_encontrado:
        print(
            f"[Aviso] Componente associado '{texto_peca}' não encontrado em nenhum grupo QListWidget. Não será inserido.")
        return  # Retorna se não encontrar o item no QListWidget

    # Inserir nova linha na tabela
    new_row = table.rowCount()
    table.insertRow(new_row)
    print(f"[DEBUG] Linha {new_row} inserida para '{texto_peca}'.")

    # ID (coluna 0) - Temporário
    set_item(table, new_row, 0, str(new_row + 1))  # Usa set_item
    item_id = table.item(new_row, 0)  # Get item depois de set_item
    item_id.setFlags(item_id.flags() & ~Qt.ItemIsEditable)

    # Descricao_Livre (Vazio)
    set_item(table, new_row, 1, "")  # Usa set_item

    # Def_Peca (coluna 2)
    set_item(table, new_row, 2, texto_peca)  # Usa set_item
    item_def = table.item(new_row, 2)  # Get item depois de set_item
    # Mantém editável para delegate
    item_def.setFlags(item_def.flags() | Qt.ItemIsEditable)
    item_def.setData(Qt.UserRole, grupo_encontrado)  # Armazena o grupo
    # 🟦 cor azul clara para identificar componentes associados
    item_def.setBackground(QColor(230, 240, 255))
    # setItem NÃO é necessário aqui

    # Colunas 3-8 (Descricao, QT_mod, QT_und, Comp, Larg, Esp) - Vazias iniciais
    for col in range(3, 9):
        set_item(table, new_row, col, "")  # Usa set_item

    # Checkboxes (Unchecked iniciais)
    for col in [9, 10, 11, 12, 53, 59, 60]:  # MPs, MO, Orla, BLK, GRAVAR_MODULO, ACB_SUP, ACB_INF
        chk = QTableWidgetItem()  # Cria novo item checkbox
        chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled |
                     Qt.ItemIsSelectable)  # Adicionado IsSelectable
        chk.setCheckState(Qt.Unchecked)
        table.setItem(new_row, col, chk)  # Adiciona o novo item à tabela

    # Mat_Default e Tab_Default (colunas 13 e 14) - Preenchidos com dados do QListWidget
    set_item(table, new_row, 13, mat_default)  # Usa set_item
    set_item(table, new_row, 14, tab_default)  # Usa set_item

    # IDs e orçamentos (colunas 15, 16, 17) - Da UI atual
    # Usa set_item
    set_item(table, new_row, 15, ui.lineEdit_item_orcamento.text().strip())
    # Usa set_item
    set_item(table, new_row, 16, ui.lineEdit_num_orcamento.text().strip())
    # Usa set_item
    set_item(table, new_row, 17, ui.lineEdit_versao_orcamento.text().strip())

    # Colunas 18-32 (ref_le a esp_mp) e 34-81 SÃO DEIXADAS VAZIAS
    for col in range(18, 82):  # 18 até 81 (inclusive)
        if col == 33:
            continue  # Salta a coluna 33 onde vai o botão MP
        set_item(table, new_row, col, "")  # Usa set_item

    # Botão "Escolher" (col 33)
    btn = QPushButton("Escolher")
    # Conecta o botão à função de seleção de material, passando a linha atual
    btn.clicked.connect(
        lambda _, r=new_row: on_mp_button_clicked(ui, r, "tab_def_pecas"))
    table.setCellWidget(new_row, 33, btn)

    # NOTA: Esta função NÃO chama atualizar_dados_def_peca, calcular_orlas,
    # ou inserir_componentes_associados. O orquestrador fará isso DEPOIS
    # de todas as inserções básicas estarem completas.
    # print(f"[INFO] Linha básica para '{texto_peca}' inserida na UI.")

##############################################
# Parte 4: Atualiza dados da linha da tabela 'tab_def_pecas' consultando DB de Items
##############################################


def atualizar_dados_def_peca(ui, row):
    """
    Atualiza os dados da linha 'row' da tabela 'tab_def_pecas' consultando as tabelas
    de dados de items (dados_items_materiais, etc.) na base de dados.

    Busca dados como:
      - Descricao (coluna 3)
      - Esp (coluna 8)
      - ref_le a esp_mp (colunas 18 a 32, exceto coluna 33 MP)

    A consulta é baseada nos valores das colunas:
      - Mat_Default (col. 13)
      - Tab_Default (col. 14)
      - ids (col. 15)
      - num_orc (col. 16)
      - ver_orc (col. 17)

    Esta função verifica o checkbox BLK (col. 12). Se estiver marcado, a consulta
    à BD é saltada e os valores existentes na linha são mantidos (editados manualmente).

    Não faz cálculos, não insere linhas adicionais, apenas atualiza campos de dados base.
    É chamada pelo orquestrador para cada linha (exceto se BLK marcada).
    """
    table = ui.tab_def_pecas

    # --- Verifica o checkbox BLK (coluna 12) ---
    blk_item = table.item(row, 12)
    if blk_item and blk_item.checkState() == Qt.Checked:
        print(
            f"[INFO] Linha {row+1} está bloqueada (BLK=True). Saltando consulta à BD para dados adicionais.")
        # A formatação será aplicada pelo orquestrador após todos os passos de cálculo
        return  # Sai da função sem consultar a BD

    # Obter valores dos campos de identificação do orçamento e da linha
    valor_ids = safe_item_text(table, row, 15).strip()
    valor_num_orc = safe_item_text(table, row, 16).strip()
    valor_ver_orc = safe_item_text(table, row, 17).strip()
    mat_default = safe_item_text(table, row, 13).strip()
    tab_default = safe_item_text(table, row, 14).strip()

    # Se não houver chaves, tabela default ou material default, não há o que consultar
    if not valor_ids or not valor_num_orc or not valor_ver_orc or not tab_default or not mat_default:
        # print(f"[DEBUG] Linha {row+1}: Faltam chaves ou defaults para consultar BD. Saltando atualização de dados adicionais.")
        return  # Não há dados suficientes para fazer a consulta

    # Mapeamento Tab_Default -> Tabela BD e Coluna ID
    db_mapping = {
        "Tab_Material_11": "dados_items_materiais",
        "Tab_Ferragens_11": "dados_items_ferragens",
        "Tab_Acabamentos_12": "dados_items_acabamentos",
        "Tab_Sistemas_Correr_11": "dados_items_sistemas_correr"
    }
    id_mapping = {
        "Tab_Material_11": "id_mat",
        "Tab_Ferragens_11": "id_fer",
        "Tab_Acabamentos_12": "id_acb",
        "Tab_Sistemas_Correr_11": "id_sc"
    }

    # Verificar se tab_default existe nos mapeamentos antes de usar
    if tab_default not in db_mapping or tab_default not in id_mapping:
        print(
            f"[AVISO] Linha {row+1}: Mapeamento não encontrado para Tab_Default '{tab_default}'. Saltando atualização de dados adicionais.")
        return  # Tab_Default inválido/não esperado

    db_table = db_mapping[tab_default]
    id_column = id_mapping[tab_default]

    resultado = None
    try:
        # --- Consulta à Base de Dados ---
        with obter_cursor() as cursor:
            # Colunas selecionadas: Descricao (BD col 1), ref_le..esp_mp (BD col 4-16)
            # NOTA: O mapeamento abaixo no código assume a ordem destas colunas
            query = (
                "SELECT descricao, ref_le, descricao_no_orcamento, ptab, pliq, desc1_plus, desc2_minus, und, desp, "
                "corres_orla_0_4, corres_orla_1_0, tipo, familia, comp_mp, larg_mp, esp_mp "  # 16 colunas
                f"FROM `{db_table}` "  # Usar backticks para nomes de tabelas
                # Usar backticks para nomes de colunas
                f"WHERE `num_orc`=%s AND `ver_orc`=%s AND `{id_column}`=%s AND `material`=%s"
            )
            # Debug: Imprimir a query e os parâmetros ajuda a encontrar erros SQL
            # print(f"[DEBUG Query] {query}")
            # print(f"[DEBUG Params] {(valor_num_orc, valor_ver_orc, valor_ids, mat_default)}")

            cursor.execute(
                query, (valor_num_orc, valor_ver_orc, valor_ids, mat_default))
            resultado = cursor.fetchone()  # Deve retornar uma única linha ou None

        # --- Processa o resultado FORA do bloco 'with' ---
        if resultado:
            # Mapeamento: índice do resultado SQL -> coluna destino na tabela UI
            # IMPORTANTE: Este mapeamento DEVE CORRESPONDER EXATAMENTE à ordem das colunas no SELECT acima.
            mapping = {
                0: 3,    # descricao  -> Coluna 3 UI
                1: 18,   # ref_le
                2: 19,   # descricao_no_orcamento
                3: 20,   # ptab
                4: 21,   # pliq
                5: 22,   # desc1_plus
                6: 23,   # desc2_minus
                7: 24,   # und
                8: 25,   # desp
                9: 26,   # corres_orla_0_4
                10: 27,  # corres_orla_1_0
                11: 28,  # tipo
                12: 29,  # familia
                13: 30,  # comp_mp
                14: 31,  # larg_mp
                15: 32   # esp_mp
            }

            # Coluna Esp (índice 8 UI) é preenchida com o valor de esp_mp (índice 15 do resultado)
            IDX_ESP_UI = 8
            IDX_ESP_MP_RESULT = 15  # Índice de esp_mp no resultado da query

            # Bloquear sinais da tabela para evitar chamadas recursivas de on_item_changed durante o preenchimento
            table.blockSignals(True)
            try:
                for idx_res, col_target_ui in mapping.items():
                    valor_bd = resultado[idx_res]
                    # Formatação e tratamento de None
                    texto_formatado = ""
                    if valor_bd is not None:
                        if col_target_ui in {20, 21}:  # ptab, pliq (Moeda)
                            try:
                                texto_formatado = formatar_valor_moeda(
                                    float(valor_bd))
                            except (ValueError, TypeError):
                                texto_formatado = str(valor_bd)
                        # des1plus, des2_minus, desp (Percentual)
                        elif col_target_ui in {22, 23, 25}:
                            try:
                                texto_formatado = formatar_valor_percentual(
                                    float(valor_bd))
                            except (ValueError, TypeError):
                                texto_formatado = str(valor_bd)
                        else:  # Outros campos (Texto, números sem formatação especial)
                            texto_formatado = str(valor_bd)
                    # else: texto_formatado permanece "" (string vazia)

                    # Usa set_item para garantir que o item existe e definir o texto
                    set_item(table, row, col_target_ui, texto_formatado)
                    # item_destino = table.item(row, col_target_ui) # Não precisa de obter item aqui

                # --- Preenche a coluna "Esp" (coluna 8 UI) com o valor de esp_mp ---
                # Obter esp_mp do resultado
                esp_valor_bd = resultado[IDX_ESP_MP_RESULT]
                esp_str = str(esp_valor_bd) if esp_valor_bd is not None else ""
                # Usa set_item para garantir que o item existe e definir o texto
                set_item(table, row, IDX_ESP_UI, esp_str)

            finally:
                # Desbloquear sinais SEMPRE, mesmo que haja erro no preenchimento
                table.blockSignals(False)

        else:
            # Se não encontrou dados na BD para a combinação, limpa os campos relevantes na linha?
            # Por agora, apenas informa que não encontrou. O orquestrador fará os cálculos com o que estiver lá.
            print(f"[AVISO] Linha {row+1}: Nenhum dado encontrado em '{db_table}' para Mat: '{mat_default}', ItemOrc: '{valor_ids}', Orc: '{valor_num_orc}', Ver: '{valor_ver_orc}'. Campos relacionados não atualizados.")
            # Opcional: Limpar as colunas 3, 8, 18-32 aqui se o Mat_Default não for encontrado na BD
            # table.blockSignals(True)
            # try:
            #     for col_target_ui in [3, 8] + list(mapping.values()):
            #         set_item(table, row, col_target_ui, "") # Usa set_item para limpar
            # finally:
            #     table.blockSignals(False)

    except mysql.connector.Error as db_err:
        # Erro durante a consulta à BD
        print(
            f"[ERRO DB] Linha {row+1}: Erro ao buscar dados da peça em {db_table}: {db_err}")
        # Não mostrar QMessageBox aqui, para não travar o orquestrador se houver múltiplos erros
    except Exception as e:
        # Outros erros inesperados
        print(
            f"[ERRO INESPERADO] Linha {row+1}: Erro ao atualizar dados da peça: {e}")
        import traceback
        traceback.print_exc()
        # Não mostrar QMessageBox aqui


# --- Função auxiliar para obter texto de célula de forma segura ---
# Re-importar safe_item_text do utils.py para garantir que está disponível


# --- As Partes 2, 3, 4, 5, 6, 7, 8, 11, 12, 13, 14, 15 e 16 permanecem as mesmas ou terão pequenas adaptações no orquestrador ou delegates ---
# Apenas as funções de inserção (1 e 10) e a de atualização de dados (4) foram alteradas para este passo.

# Parte 2: Atualização Sequencial dos IDs (mantida)
def update_ids(table):
    """
    Atualiza a coluna "id" (coluna 0) de forma sequencial, de 1 até o número total de linhas.
    """
    print("[INFO] Atualizando IDs das linhas...")
    # Evita emissões de itemChanged durante a renumeração
    table.blockSignals(True)
    try:
        for row in range(table.rowCount()):
            # Obtém o item existente ou cria um se não existir (usando set_item)
            # Usa set_item para definir o texto e garantir o item
            set_item(table, row, 0, str(row + 1))
            item_id = table.item(row, 0)  # Obtém o item depois de set_item

            # Configura as flags (não editável) no item existente
            if item_id:  # Garante que o item foi criado
                item_id.setFlags(item_id.flags() & ~Qt.ItemIsEditable)

            # Opcional: Limpar a cor de fundo azul claro se não for mais um associado (se a linha for movida)
            # item_def = table.item(row, 2)
            # if item_def and item_def.background().color() == QColor(230, 240, 255):
            #    item_def.setBackground(Qt.white) # Pode redefinir a cor, mas complica se for linha MODULO
            # Melhor: A lógica de cor deve estar no orquestrador ao determinar o tipo de linha após todo o processamento.
    finally:
        table.blockSignals(False)
    print("[INFO] Atualização de IDs concluída.")

# Parte 3: Validação de Entradas para Peças MODULO (mantida, usa validar_expressao_modulo do utils)


def validar_input_modulo(item):
    """
    Função para validar entrada nas colunas Comp, Larg e Esp de linhas MODULO.
    Verifica se o valor inserido é numérico ou uma expressão válida contendo variáveis permitidas.
    """
    texto = item.text().strip().upper()
    if texto == "":
        return  # Vazio é válido
    # Usa a função de validação do utils.py
    # Passa row e column para a função validar_expressao_modulo mostrar mensagem mais útil
    table = item.tableWidget()
    row = item.row()
    col = item.column()
    # Obter o texto do cabeçalho de forma segura
    header_item = table.horizontalHeaderItem(col)
    header_text = header_item.text() if header_item else ""

    if not validar_expressao_modulo(texto, row, header_text):
        item.setText("")  # Limpa o conteúdo se a validação falhar

# Parte 4 (Função principal de atualização de dados da linha) -> Já reescrita acima.

# Parte 5: Configurar Menu de Contexto e Delegate (mantida)


def setup_context_menu(ui, opcoes_por_grupo=None):
    """
    Configura o menu de contexto para a tabela 'tab_def_pecas' e instala delegates.
    """
    # Importação local para evitar ciclo
    # from tabela_def_pecas_combobox_mat_default import aplicar_combobox_mat_default # Já importado no topo

    # Se opcoes_por_grupo não foi fornecido, gera-o
    if opcoes_por_grupo is None:
        grupos_widgets = {
            "caixote": ui.listWidget_caixote_4,
            "ferragens": ui.listWidget_ferragens_4,
            "mao_obra": ui.listWidget_mao_obra_4,
            "paineis": ui.listWidget_paineis_4,
            "remates_guarnicoes": ui.listWidget_remates_guarnicoes_4,
            "sistemas_correr": ui.listWidget_sistemas_correr_4,
            "acabamentos": ui.listWidget_acabamentos_4
        }
        opcoes_por_grupo = {
            grupo.lower(): [widget.item(i).text() for i in range(widget.count())]
            for grupo, widget in grupos_widgets.items()
        }

    table = ui.tab_def_pecas  # A tabela onde os delegates serão instalados
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setContextMenuPolicy(Qt.CustomContextMenu)
    # Certifica-se que o menu de contexto está configurado para usar a UI principal
    # Desconecta para evitar múltiplas conexões
    try:
        table.customContextMenuRequested.disconnect()
    except TypeError:  # Sinal não estava conectado
        pass
    table.customContextMenuRequested.connect(
        lambda pos: show_context_menu(ui, pos))

    # Instala o delegate para a coluna "Def_Peca" (coluna 2)
    # Passa ui, table (como parent), e o dicionário opcoes_por_grupo posicionalmente
    # Agora a função espera o dicionário gerado ou passado como argumento
    install_def_peca_delegate(ui, table, opcoes_por_grupo)

    # Instala o delegate visual/funcional para outras colunas editáveis
    # Mantém esta chamada com argumentos nomeados, pois o construtor de CelulaEdicaoDelegate espera (parent, ui)
    ui.tab_def_pecas.setItemDelegate(CelulaEdicaoDelegate(parent=table, ui=ui))

    # NOTA: A conexão itemChanged (Parte 12) não deve ser feita aqui.
    # Deve ser feita na inicialização principal da UI (ex: main.py)
    # para garantir que só é conectada uma vez.

# Parte 6: Delegate para a Coluna "Def_Peca" (adaptada para chamar a nova atualizar_dados_def_peca e orquestrador)


class DefPecaDelegate(QStyledItemDelegate):
    def __init__(self, parent, ui, opcoes_por_grupo):
        """
        Delegate para a coluna "Def_Peca" com QComboBox e lógica de atualização.
        """
        super().__init__(parent)  # Passa o parent para a superclasse
        self.opcoes_por_grupo = opcoes_por_grupo
        self.ui = ui  # Guarda o objeto ui para uso interno

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.setEditable(True)  # Permite escrever/procurar (completar)
        editor.setInsertPolicy(QComboBox.NoInsert)
        editor.setStyleSheet(
            """
            QComboBox {
                background-color: #f0f0f0;
                border: 1px solid #a0a0a0;
                padding-left: 4px;
            }
            QComboBox QAbstractItemView {
                selection-background-color: lightblue;
            }
            """
        )
        # NOTA: Não conectar sinais aqui (activated, currentTextChanged).
        # Conectar o sinal textActivated (quando o usuário seleciona um item ou pressiona Enter)
        # na função setEditorData.

        return editor

    def setEditorData(self, editor, index):
        # Desconectar sinais temporariamente para configurar o editor
        editor.blockSignals(True)

        current_text = index.data(Qt.DisplayRole)
        grupo = index.data(Qt.UserRole)
        grupo = grupo.lower() if grupo else ""
        opcoes = self.opcoes_por_grupo.get(grupo, [])
        editor.clear()
        editor.addItem("")  # Adicionar item vazio
        editor.addItems(opcoes)

        # Definir texto atual
        if current_text:
            pos = editor.findText(current_text, Qt.MatchFixedString)
            if pos >= 0:
                editor.setCurrentIndex(pos)
            else:
                # Adicionar o texto atual se não estiver na lista (útil para itens que foram apagados da lista mas estão na tabela)
                editor.setEditText(current_text)
                # editor.setCurrentIndex(0) # Ou definir para vazio
        else:
            editor.setCurrentIndex(0)  # Selecionar item vazio

        # Reconectar o sinal APENAS para textActivated
        # Este sinal é emitido quando o usuário escolhe um item da lista drop-down ou pressiona Enter.
        # Desconecta para evitar múltiplas conexões se o editor for reutilizado
        try:
            editor.textActivated.disconnect()
        except TypeError:
            pass  # Sinal não estava conectado
        editor.textActivated.connect(
            lambda text: self.handle_selection_committed(editor, index, text))

        editor.blockSignals(False)

    def setModelData(self, editor, model, index):
        # Este método é chamado quando a edição termina (usuário sai da célula).
        # A lógica de atualização de dados e chamada do orquestrador já foi tratada
        # no handler do sinal `textActivated` (handle_selection_committed).
        # Aqui, apenas definimos o valor no modelo.
        valor = editor.currentText()
        # Impede a edição se a linha estiver bloqueada (BLK)
        row = index.row()
        table = self.ui.tab_def_pecas
        blk_item = table.item(row, 12)
        if blk_item and blk_item.checkState() == Qt.Checked:
            # Se BLK, não salva a mudança feita no editor.
            # O valor original deve ter sido mantido pelo RevertModelCache no handle_selection_committed.
            # Apenas retorna para não sobrescrever.
            print(
                f"[INFO] Delegate DefPeca: setModelData - Linha {row+1} está bloqueada. Não salvando mudança.")
            return  # Não atualiza o modelo se BLK estiver marcado

        # Se não está bloqueado, salva a mudança normalmente
        model.setData(index, valor, Qt.EditRole)

    def handle_selection_committed(self, editor, index, text):
        """
        Função chamada quando o usuário seleciona um item no ComboBox ou pressiona Enter.
        Atualiza as colunas Mat_Default/Tab_Default e chama o orquestrador.
        """

        row = index.row()
        table = self.ui.tab_def_pecas

        # Impede a edição e notifica se a linha estiver bloqueada (BLK)
        blk_item = table.item(row, 12)
        if blk_item and blk_item.checkState() == Qt.Checked:
            QMessageBox.warning(
                editor.parent().window(),  # Usa a janela pai do editor (a janela principal) como parent
                "Linha Bloqueada",
                "Não é possível alterar a peça porque está marcada como BLK (editada manualmente)."
            )
            # Forçar o fecho do editor sem commit das mudanças feitas no editor
            self.closeEditor.emit(editor, QStyledItemDelegate.RevertModelCache)
            # Reconectar o sinal? Não é necessário, o editor será recriado/configurado na próxima edição.
            return  # Sai sem atualizar

        # Recupera o grupo associado, armazenado no Qt.UserRole
        grupo = index.data(Qt.UserRole)
        grupo = grupo.lower() if grupo else ""

        # Encontrar o item correspondente no QListWidget para obter Mat_Default e Tab_Default
        list_widgets = {
            "caixote": self.ui.listWidget_caixote_4,
            "ferragens": self.ui.listWidget_ferragens_4,
            "mao_obra": self.ui.listWidget_mao_obra_4,
            "paineis": self.ui.listWidget_paineis_4,
            "remates_guarnicoes": self.ui.listWidget_remates_guarnicoes_4,
            "sistemas_correr": self.ui.listWidget_sistemas_correr_4,
            "acabamentos": self.ui.listWidget_acabamentos_4
        }
        widget = list_widgets.get(grupo)
        novo_mat_default = ""
        novo_tab_default = ""
        if widget:
            for i in range(widget.count()):
                item_lista = widget.item(i)
                if item_lista.text().strip().upper() == text.strip().upper():
                    novo_mat_default = item_lista.data(Qt.UserRole + 1) or ""
                    novo_tab_default = item_lista.data(Qt.UserRole + 2) or ""
                    break
        else:
            print(
                f"[AVISO] Delegate DefPeca: Grupo '{grupo}' não encontrado nos mapeamentos QListWidget.")

        # Atualiza as colunas "Mat_Default" (índice 13) e "Tab_Default" (índice 14) no modelo
        # Desbloqueia sinais temporariamente para permitir que setData funcione sem recursão
        table.blockSignals(True)
        try:
            self.model().setData(self.model().index(row, 13), novo_mat_default, Qt.EditRole)
            self.model().setData(self.model().index(row, 14), novo_tab_default, Qt.EditRole)
        finally:
            table.blockSignals(False)

        # Força o ComboBox Mat_Default a ser reaplicado para esta linha para refletir o novo Tab_Default
        # Pode ser ineficiente, mas garante o ComboBox correto.
        aplicar_combobox_mat_default(self.ui)

        # --- CHAMA O ORQUESTRADOR PARA RECALCULAR TUDO ---
        # Isso garante que a linha alterada (e potencialmente outras dependentes)
        # seja processada, dados adicionais carregados, cálculos refeitos, etc.
        from modulo_orquestrador import atualizar_tudo
        print(
            f"[INFO] Delegate DefPeca: Chamando orquestrador após alteração na linha {row+1}.")
        atualizar_tudo(self.ui)

        # Opcional: Fechar o editor explicitamente
        self.commitData.emit(editor)
        self.closeEditor.emit(editor, QStyledItemDelegate.SubmitModelCache)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


# Parte 7: Delegate para Edição de Células (mantida com ajuste para BLK)
class CelulaEdicaoDelegate(QStyledItemDelegate):
    """
    Delegate visual e funcional para destacar a célula ativa com uma borda vermelha,
    e aceitar ENTER e setas (← →) como teclas de navegação + validação.
    """

    def __init__(self, parent, ui):
        super().__init__(parent)  # Passa o parent para a superclasse
        self.ui = ui  # Guarda o objeto ui para uso interno

    def createEditor(self, parent, option, index):
        col = index.column()
        row = index.row()
        table = self.ui.tab_def_pecas
        editor = QLineEdit(parent)
        editor.installEventFilter(self)  # Captura eventos de tecla
        return editor

    def eventFilter(self, editor, event):
        """
        Delegate para tratar edição de células na tabela 'tab_def_pecas'.
        Permite sempre edição das colunas de medidas (qt_und, comp, larg, esp) e
        aplica restrição de edição apenas às colunas 18-32 quando BLK está ativo.
        """
        # Trata tecla pressionada
        if event.type() == QEvent.KeyPress:
            key = event.key()
            table = editor.parent().parent()  # QTableWidget
            row = table.currentRow()
            col = table.currentColumn()

            # --- Tratamento original de navegação e validação ---
            if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Left, Qt.Key_Right):
                # Validação de fórmulas para colunas de medidas (Comp 6, Larg 7, Esp 8, QT_mod 4)
                if col in [IDX_QT_MOD, IDX_COMP, IDX_LARG, IDX_ESP]:
                    texto = editor.text().strip().upper()
                    header = table.horizontalHeaderItem(col)
                    header_text = header.text() if header else ""
                    if not validar_expressao_modulo(texto, row, header_text):
                        return True  # Impede salvar valor inválido

                if col == IDX_QT_MOD:
                    item_def = table.item(row, IDX_DEF_PECA)
                    if item_def and item_def.text().strip().upper() == "MODULO" and editor.text().strip():
                        QMessageBox.warning(
                            table.window(),
                            "Linha MODULO",
                            "QT_mod deve permanecer vazio. O valor usado será 1.")
                        editor.setText("")

                # Comitar dados e fechar editor
                self.commitData.emit(editor)
                self.closeEditor.emit(editor, QStyledItemDelegate.NoHint)

                # Navegação por teclas
                if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Right):
                    col += 1
                elif key == Qt.Key_Left:
                    col -= 1
                if 0 <= col < table.columnCount():
                    # Adiar a definição da célula atual para garantir que o itemChanged da célula anterior seja processado primeiro
                    QTimer.singleShot(
                        0, lambda: table.setCurrentCell(row, col))

                # Após editar (ENTER/Setas), o orquestrador será chamado
                # devido ao sinal cellChanged que despoletará on_cell_changed_for_blk_logic
                # e, se necessário, outras lógicas que chamam o orquestrador.
                # Para garantir que o orquestrador é chamado após edições de fórmulas,
                # podemos adicionar uma chamada aqui também, mas é melhor centralizar
                # no on_cell_changed_def_pecas ou no on_cell_changed_for_blk_logic
                # se essa mudança exigir recalculo geral.
                # Por agora, vamos confiar que o cellChanged fará o necessário.
                # Se a edição for numa coluna de fórmula, o modulo_quantidades já deve ser chamado
                # pelo on_cell_changed_def_pecas ou similar.
                if col in [IDX_QT_MOD, IDX_COMP, IDX_LARG, IDX_ESP]:
                    QTimer.singleShot(10, lambda: atualizar_tudo(
                        self.ui))  # Pequeno delay

                return True
        return super().eventFilter(editor, event)

    def paint(self, painter, option, index):
        # Desenha a célula com a cor de fundo e texto padrão
        super().paint(painter, option, index)

        # Se a célula tem foco, desenha uma borda vermelha
        if option.state & QStyle.State_HasFocus:
            pen = QPen(Qt.red)
            pen.setWidth(2)  # Largura da borda
            painter.setPen(pen)
            # Ajusta o retângulo para desenhar a borda dentro da célula
            painter.drawRect(option.rect.adjusted(1, 1, -1, -1))

    def setModelData(self, editor, model, index):
        # A EDIÇÃO É SEMPRE ACEITE, NÃO HÁ VERIFICAÇÃO DE BLK AQUI PARA IMPEDIR.
        # O sinal cellChanged (conectado a on_cell_changed_for_blk_logic)
        # tratará de aplicar a formatação verde e ativar BLK se a edição
        # for nas colunas 18-32.
        valor = editor.text()
        model.setData(index, valor, Qt.EditRole)
        # A formatação e ativação de BLK serão tratadas pelo cellChanged.
        # A chamada ao orquestrador, se necessária, também é despoletada pelo
        # cellChanged ou pelo eventFilter (para fórmulas).


# Parte 9: Insere automaticamente os componentes associados (refatorada para ser chamada pelo orquestrador)
def inserir_componentes_associados_para_linha(ui, linha_principal):
    """
    Chamada pelo orquestrador para processar uma linha principal e identificar
    e adicionar componentes associados a ela.

    - Consulta o Excel TAB_DEF_PECAS.XLSX com base no Def_Peca da linha_principal.
    - Obtém a lista de COMP_ASS_1..3.
    - Para cada componente associado encontrado, adiciona o seu nome a uma lista
      global/de contexto para inserção posterior.
    - Preenche as colunas 34-36 com os nomes encontrados.

    NÃO insere as linhas diretamente AQUI. A inserção será feita após a primeira
    iteração do orquestrador.
     Respeita a flag BLK (coluna 12). Se BLK estiver True, a busca no Excel
    para COMP_ASS_x é saltada, e apenas os valores *existentes* nas colunas 34-36
    são retornados.
    """
    table = ui.tab_def_pecas

    # Obtem o texto da peça principal (coluna 2)
    if linha_principal < 0 or linha_principal >= table.rowCount():
        print(
            f"[Erro] Linha principal inválida para componentes associados: {linha_principal}")
        return []  # Retorna lista vazia

    item_def_peca = table.item(linha_principal, 2)
    if item_def_peca is None:
        return []

    texto_peca = item_def_peca.text().strip().upper()
    # --- Verifica o checkbox BLK (coluna 12) na linha principal ---
    blk_item = table.item(linha_principal, 12)
    if blk_item and blk_item.checkState() == Qt.Checked:
        # Se a linha principal está bloqueada, salta a busca no Excel
        # e apenas lê os nomes dos associados que já estão nas colunas 34-36.
        print(
            f"[INFO] Linha {linha_principal+1} (Principal) está bloqueada (BLK=True). Saltando busca de componentes associados no Excel.")
        comps_existentes_na_linha = []
        for col_idx in [IDX_COMP_ASS_1, IDX_COMP_ASS_2, IDX_COMP_ASS_3]:
            comp_name = safe_item_text(table, linha_principal, col_idx).strip()
            if comp_name:
                comps_existentes_na_linha.append(comp_name)
        # print(f"[DEBUG] Linha {linha_principal+1} (BLK=True): Componentes associados lidos das células (34-36): {comps_existentes_na_linha}")
        return comps_existentes_na_linha  # Retorna o que estiver nas células 34-36

    # Se a linha NÃO está bloqueada, busca no Excel

    # Caminho do Excel
    caminho_base = ui.lineEdit_base_dados.text().strip()
    folder_base = os.path.dirname(caminho_base)
    excel_file = os.path.join(folder_base, "TAB_DEF_PECAS.XLSX")

    if not os.path.exists(excel_file):
        print(
            "[Erro] Ficheiro TAB_DEF_PECAS.XLSX não encontrado para componentes associados.")
        # Limpa colunas 34-36 na UI se o ficheiro Excel não existir
        table.blockSignals(True)
        try:
            for col_idx in [IDX_COMP_ASS_1, IDX_COMP_ASS_2, IDX_COMP_ASS_3]:
                set_item(table, linha_principal, col_idx, "")
        finally:
            table.blockSignals(False)
        return []  # Retorna lista vazia

    df = None
    try:
        df = pd.read_excel(excel_file, header=4)
    except Exception as e:
        print(
            f"[ERRO] Erro ao ler o ficheiro Excel '{excel_file}' para associados: {e}")
        # Limpa colunas 34-36 na UI em caso de erro na leitura do Excel
        table.blockSignals(True)
        try:
            for col_idx in [IDX_COMP_ASS_1, IDX_COMP_ASS_2, IDX_COMP_ASS_3]:
                set_item(table, linha_principal, col_idx, "")
        finally:
            table.blockSignals(False)
        return []  # Retorna lista vazia

    # Procurar a linha no Excel com o mesmo texto em 'DEF_PECA'
    # Usar str() e .str.strip().str.upper() para garantir que a comparação funciona mesmo se houver NaN ou tipos diferentes
    df['DEF_PECA_CLEAN'] = df.iloc[:, 0].astype(str).str.strip().str.upper()
    # Prefere a coluna 'DEF_PECA' se existir no Excel
    if "DEF_PECA" in df.columns:
        df['DEF_PECA_CLEAN'] = df['DEF_PECA'].astype(
            str).str.strip().str.upper()
    # Se a coluna 0 não tiver nome e a coluna 'DEF_PECA' existir, usar a nomeada
    elif "DEF_PECA" in df.columns and df.columns[0] != "DEF_PECA":
        df['DEF_PECA_CLEAN'] = df['DEF_PECA'].astype(
            str).str.strip().str.upper()
    # Caso contrário, usar a coluna 0 (original)
    else:
        df['DEF_PECA_CLEAN'] = df.iloc[:, 0].astype(
            str).str.strip().str.upper()

    linha_excel = df[df['DEF_PECA_CLEAN'] == texto_peca]

    if linha_excel.empty:
        # print(f"[DEBUG] Tipo de peça '{texto_peca}' não encontrado no Excel para buscar associados.")
        # Limpa as colunas 34-36 na UI se não encontrar no Excel
        table.blockSignals(True)
        try:
            for col_idx in [IDX_COMP_ASS_1, IDX_COMP_ASS_2, IDX_COMP_ASS_3]:
                set_item(table, linha_principal, col_idx, "")
        finally:
            table.blockSignals(False)
        return []  # Não encontrou no Excel, não há associados (automáticos)

    # Obter os componentes associados (colunas 5, 6, 7 no Excel base 1)
    # Indices DataFrame (header=4) são 4, 5, 6
    comp_col_names = ['COMP_ASS_1', 'COMP_ASS_2', 'COMP_ASS_3']
    # Pega a primeira linha correspondente
    row_excel_data = linha_excel.iloc[0]

    comps_a_inserir = []  # Lista para coletar nomes a retornar

    # Preenche nas colunas 34, 35, 36 da linha UI e coleta para a lista de inserção
    # Bloqueia sinais durante o preenchimento na linha UI
    table.blockSignals(True)
    try:
        for i, col_name in enumerate(comp_col_names):
            # Obtém o valor do DataFrame, tratando NaN e convertendo para string limpa
            # Use .get() para evitar KeyError se coluna faltar
            val = row_excel_data.get(col_name)
            val_str = str(val).strip() if pd.notna(val) and isinstance(
                val, str) else ""  # Trata NaN e tipos não string

            # Preenche a célula na UI
            col_idx_ui = IDX_COMP_ASS_1 + i
            set_item(table, linha_principal, col_idx_ui, val_str)

            # Se o valor for válido, adiciona à lista de componentes a inserir
            if val_str:  # Se a string não for vazia após strip
                comps_a_inserir.append(val_str)
        # print(f"[DEBUG] Linha {linha_principal+1}: Componentes associados lidos do Excel: {comps_a_inserir}")
    finally:
        table.blockSignals(False)  # Desbloqueia sinais

    # 💡 Aplica cor azul escura na célula Def_Peca do componente principal se houver associados
    item_def = table.item(linha_principal, 2)
    if item_def:
        # Verifica a cor atual para não sobrescrever a cor cinza do MODULO
        current_color = item_def.background().color()
        if current_color.name() != COLOR_MODULO_BG.name():  # Se não for a cor cinza do MODULO
            # Aplica a cor azul mais escura apenas se a linha tiver associados E não for um MODULO
            if comps_a_inserir:
                # Azul mais escuro para principal com associados
                item_def.setBackground(QColor(180, 200, 255))
            else:
                # Se não tem associados, garante que não fica com a cor azul mais escura
                # Mas não volta para branco, pois pode ser a cor de um item já existente que não tinha associados
                # A lógica de cor final para não-associados é tratada no orquestrador
                pass  # Não faz nada se não tem associados e não é MODULO
        else:
            # Se for um MODULO COM associados, pode adicionar tooltip
            if comps_a_inserir:
                old_tooltip = item_def.toolTip()  # Preserva tooltips existentes
                item_def.setToolTip(
                    f"MODULO com componentes associados: {', '.join(comps_a_inserir)}.\n" + old_tooltip)

    # Retorna a lista de nomes de componentes associados encontrados (do Excel ou das células se BLK)
    return comps_a_inserir


# Parte 11: Configura os QListWidget para funcionar com clique simples (mantida)
def configurar_selecao_qt_lists(ui):
    """
    Permite o clique simples para (des)marcar itens nos QListWidget de grupos de peças.
    """
    from PyQt5.QtWidgets import QAbstractItemView

    def tornar_listwidget_clickavel(list_widget):
        list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        list_widget.setSelectionBehavior(QAbstractItemView.SelectItems)

        def ao_clicar_item(item):
            # Verifica se o item é "checkable" antes de tentar mudar o estado
            if item.flags() & Qt.ItemIsUserCheckable:
                estado = Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
                item.setCheckState(estado)
            else:
                # Debug/Info se um item não é checkable
                print(f"[INFO] Item '{item.text()}' não é chekable.")

        # Desconecta para evitar múltiplas conexões se for chamado mais de uma vez
        try:
            list_widget.itemClicked.disconnect()
        except TypeError:
            pass
        list_widget.itemClicked.connect(ao_clicar_item)

    # Lista de todos os QListWidget a configurar
    list_widgets_a_configurar = [
        ui.listWidget_caixote_4,
        ui.listWidget_ferragens_4,
        ui.listWidget_mao_obra_4,
        ui.listWidget_paineis_4,
        ui.listWidget_remates_guarnicoes_4,
        ui.listWidget_sistemas_correr_4,
        ui.listWidget_acabamentos_4
    ]

    for lw in list_widgets_a_configurar:
        if lw is not None:  # Verifica se o objeto UI foi criado corretamente
            tornar_listwidget_clickavel(lw)
        else:
            print(
                "[AVISO] Objeto QListWidget não encontrado na UI durante a configuração.")


# Parte 12: Callback: on_item_changed_def_pecas (mantida com chamada ao orquestrador)
# Esta função está correta, mas precisa de garantir que o orquestrador é chamado no final
# se a mudança afetar cálculos dependentes. A chamada já foi adicionada no eventFilter
# do CelulaEdicaoDelegate. Para mudanças de ptab/pliq/desp/desconto, pode ser necessário
# também chamar o orquestrador ou uma função mais específica para atualizar custos.
# Por simplicidade e consistência, chamar atualizar_tudo no final DESTA função
# também garante que tudo é recalculado após QUALQUER mudança (exceto se BLK).
# No entanto, isto pode criar chamadas recursivas se atualizar_tudo também modificar itens.
# A melhor abordagem é que o delegate (no eventFilter e no setModelData) e
# o on_mat_default_changed chamem o orquestrador. A própria on_item_changed_def_pecas
# deve focar-se apenas em recalcular PliQ quando ptab/descontos mudam e reformatar.
# O orquestrador tratará do resto. A lógica de chamar o orquestrador já está nos delegates.
# Não é estritamente necessário adicionar outra chamada aqui, a menos que haja outras
# formas de items serem alterados (copy/paste? Programaticamente?).
# Vamos manter a versão onde a chamada ao orquestrador está nos Delegates/on_mat_default_changed.
# Se houver problemas, revisitamos.
# Variável global para controlar edições programáticas
_editando_programaticamente_def_pecas = False


def on_item_changed_def_pecas(item):
    """
    Callback chamado quando o conteúdo de uma célula muda (após setModelData).
    Aplica formatação imediata (€, %) para colunas específicas.
    """

    # print(f"[DEBUG ItemChanged] L{item.row()+1} C{item.column()+1}")
    # Manter a guarda para evitar qualquer processamento durante atualizações
    global _editando_programaticamente_def_pecas
    if not item:
        return

    table = item.tableWidget()
    if not table:
        return  # Segurança
    # Guardas contra re-entrada e edições programáticas/atualizações
    if _editando_programaticamente_def_pecas or \
       table.property("importando_dados") or \
       table.property("atualizando_tudo"):
        return

    _editando_programaticamente_def_pecas = True
    try:
        row = item.row()
        col = item.column()
        texto_atual = item.text()  # Texto como está na célula agora

        colunas_para_formatar = {
            IDX_PTAB: "moeda",
            IDX_PLIQ: "moeda",
            IDX_DES1PLUS: "percentual",
            IDX_DES1MINUS: "percentual",
            IDX_DESP: "percentual"
        }

        if col in colunas_para_formatar:
            tipo_formato = colunas_para_formatar[col]
            try:
                # Converte o texto atual (pode já estar formatado ou não) para número
                valor_num = converter_texto_para_valor(
                    texto_atual, tipo_formato)
                # Formata o valor numérico de volta para string formatada
                texto_formatado = ""
                if tipo_formato == "moeda":
                    texto_formatado = formatar_valor_moeda(valor_num)
                elif tipo_formato == "percentual":
                    texto_formatado = formatar_valor_percentual(valor_num)
                # Define o texto formatado de volta na célula *apenas se for diferente*
                # para evitar loops desnecessários.

                if texto_atual != texto_formatado:
                    # print(f"[Format ItemChanged] L{row+1} C{col+1}: Formatando '{texto_atual}' para '{texto_formatado}'")
                    item.setText(texto_formatado)  # Atualiza o texto da célula
            except Exception as e:
                print(f"[ERRO Format ItemChanged] L{row+1} C{col+1}: {e}")

    finally:
        _editando_programaticamente_def_pecas = False  # Libera flag para futuras edições


# Parte 13: Botão "Escolher" na coluna MP (mantida, usa escolher_material_item)
def on_mp_button_clicked(ui, row, nome_tabela):
    """
    Chamado quando o usuário clica no botão "Escolher" na coluna MP.
    Abre o diálogo de seleção de material, atualiza os dados da linha
    e aplica formatação visual nas colunas 18→32, ativando também o campo BLK.
    """
    # Importação local para evitar ciclo
    # from tabela_def_pecas_items import escolher_material_item # Esta função está neste módulo, não precisa importar
    from PyQt5.QtWidgets import QMessageBox

    # A função de formatação é importada no topo do módulo
    # from aplicar_formatacao_visual_blk import aplicar_ou_limpar_formatacao_blk

    # Chama a função que abre o diálogo e atualiza os dados na linha
    if escolher_material_item(ui, row):
        # print(f"[MP_BUTTON] Material escolhido para L{row+1}. Aplicando formatação 'escolher'.")
        # 1. Aplica a formatação e define tooltip PLIQ. A função também cuida de ATIVAR o BLK.
        aplicar_ou_limpar_formatacao_blk(
            ui.tab_def_pecas, row, aplicar=True, origem_pliq_tooltip="escolher")

        # 2. ATIVA o BLK explicitamente APÓS a formatação
        blk_item = ui.tab_def_pecas.item(row, IDX_BLK)
        if blk_item is None:
            blk_item = QTableWidgetItem()
            blk_item.setFlags(Qt.ItemIsUserCheckable |
                              Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            ui.tab_def_pecas.setItem(row, IDX_BLK, blk_item)

        # Ativar o check APENAS se não estiver já ativo, e bloquear sinais
        if blk_item.checkState() != Qt.Checked:
            old_signals = ui.tab_def_pecas.signalsBlocked()
            ui.tab_def_pecas.blockSignals(True)
            blk_item.setCheckState(Qt.Checked)
            ui.tab_def_pecas.blockSignals(old_signals)

        # print(f"[MP_BUTTON] Chamando orquestrador após seleção de material na linha {row+1}.")
        # 3. Chamar o orquestrador para recalcular tudo
        # Usar QTimer para garantir que a atualização ocorre após o evento atual
        QTimer.singleShot(10, lambda: atualizar_tudo(ui))


# Parte 14: Abre menu seleção de material a partir da tabela de matérias-primas (mantida com ajuste para BLK)
def escolher_material_item(ui, linha_tab):
    """
    Abre um diálogo de seleção de material para uma linha específica da tab_def_pecas.
    Atualiza os dados da linha com base no material selecionado.
    Retorna True se sucesso, False se cancelado/erro.
    A ativa o campo BLK (coluna 12) e formata as colunas 18-32.
    A ativação de BLK e formatação são feitas pela função chamadora (on_mp_button_clicked).
    """
    # Importação local
    from dados_gerais_materiais_escolher import MaterialSelectionDialog
    from PyQt5.QtWidgets import QMessageBox  # Importar aqui se não estiver global

    tbl = ui.tab_def_pecas

    # Bloqueia sinais para evitar que on_item_changed seja chamado várias vezes
    tbl.blockSignals(True)

    # --- Pré-filtro: Obter valores atuais de "tipo" e "família" da linha em tab_def_pecas (col 28 e 29) ---
    # Usar safe_item_text para garantir que pega o texto ou vazio
    pre_tipo = safe_item_text(tbl, linha_tab, 28).strip()
    pre_familia = safe_item_text(tbl, linha_tab, 29).strip()
    tbl.blockSignals(False)

    dialog = MaterialSelectionDialog(
        ui.tableWidget_materias_primas, pre_tipo, pre_familia)
    result = dialog.exec_()

    if result == dialog.Accepted:
        selected_row_mp = dialog.selected_row
        if selected_row_mp is None or selected_row_mp < 0:
            return False

        # Bloqueia sinais novamente para o preenchimento da linha principal
        tbl.blockSignals(True)
        try:

            # Mapeamento: (índice de origem na tabela Matérias-Primas do diálogo, índice de destino na tab_def_pecas)
            # Este mapeamento define QUAIS dados são copiados da tabela de Matérias-Primas
            # para a linha da tab_def_pecas quando um material é escolhido.
            col_map = {
                # REF_PHC (MP) -> ref_le (Peca)
                'ref_le': (3, 18),
                # Descrição Resumida (MP) -> descricao_no_orcamento (Peca)
                'descricao_no_orcamento': (5, 19),
                # Preço Tabela (MP) -> ptab (Peca)
                'ptab': (6, 20),
                # Preço Tabela (MP) -> pliq (Peca) - PliQ será recalculado depois
                'pliq': (6, 21),
                # Desc. Adicional (MP) -> des1plus (Peca)
                'des1plus': (7, 22),
                # Desc. Percentual (MP) -> des2_minus (Peca)
                'des2_minus': (8, 23),
                # Unidade (MP) -> und (Peca)
                'und': (10, 24),
                # Desperdício (%) (MP) -> desp (Peca)
                'desp': (11, 25),
                # Ref. Orla Fina (MP) -> corres_orla_0_4 (Peca)
                'corres_orla_0_4': (16, 26),
                # Ref. Orla Grossa (MP) -> corres_orla_1_0 (Peca)
                'corres_orla_1_0': (17, 27),
                # Tipo (MP) -> tipo (Peca)             'tipo': (18, 28),
                'tipo': (13, 28),
                # Família (MP) -> familia (Peca)      'familia': (19, 29),
                'familia': (14, 29),
                # Comp. MP (MP) -> comp_mp (Peca)      'comp_mp': (20, 30),
                'comp_mp': (19, 30),
                # Larg. MP (MP) -> larg_mp (Peca)      'larg_mp': (21, 31),
                'larg_mp': (20, 31),
                # Esp. MP (MP) -> esp_mp (Peca)
                'esp_mp': (12, 32)
                # A coluna 12 da tabela MP (esp_mp) também vai para a coluna 8 da tab_def_pecas ("Esp")
                # Mapeamento adicional para coluna 8: (12, 8)
            }

            # Adiciona a Espessura (coluna 8) ao mapeamento
            # Esp. MP (MP) -> Esp (Peca UI col 8)
            col_map['esp_peca_ui'] = (12, 8)

            # Copia os valores da linha selecionada na tabela de Matérias-Primas para a linha de tab_def_pecas
            # E formata valores monetários e percentuais
            for campo, (src_idx, tgt_idx) in col_map.items():
                valor_origem_item = dialog.table.item(selected_row_mp, src_idx)
                valor_texto = valor_origem_item.text() if valor_origem_item else ""
                # **Importante**: Converter e formatar aqui garante que os dados chegam formatados à tabela
                valor_num = converter_texto_para_valor(valor_texto,
                                                       'moeda' if tgt_idx in {20, 21} else
                                                       ('percentual' if tgt_idx in {22, 23, 25} else 'texto'))
                texto_formatado = ""
                if tgt_idx in {20, 21}:
                    texto_formatado = formatar_valor_moeda(valor_num)
                elif tgt_idx in {22, 23, 25}:
                    texto_formatado = formatar_valor_percentual(valor_num)
                else:
                    texto_formatado = valor_texto
                # Usa set_item com valor JÁ FORMATADO
                set_item(tbl, linha_tab, tgt_idx, texto_formatado)

            # Recalcular PliQ baseado nos valores JÁ FORMATADOS que foram copiados
            ptab_text_copiado = safe_item_text(tbl, linha_tab, IDX_PTAB)
            des1plus_text_copiado = safe_item_text(
                tbl, linha_tab, IDX_DES1PLUS)
            des2minus_text_copiado = safe_item_text(
                tbl, linha_tab, IDX_DES1MINUS)
            ptab_valor_num = converter_texto_para_valor(
                ptab_text_copiado, "moeda")
            des1plus_valor_num = converter_texto_para_valor(
                des1plus_text_copiado, "percentual")
            des2minus_valor_num = converter_texto_para_valor(
                des2minus_text_copiado, "percentual")
            novo_pliq_num = round(
                ptab_valor_num * (1 + des1plus_valor_num) * (1 - des2minus_valor_num), 2)
            set_item(tbl, linha_tab, IDX_PLIQ,
                     formatar_valor_moeda(novo_pliq_num))
            # Atualiza o tooltip de PLIQ com o valor formatado
        except Exception as e:
            print(f"[ERRO] escolher_material_item (L{linha_tab+1}): {e}")
            # import traceback; traceback.print_exc() # Para debug detalhado
            QMessageBox.critical(tbl.window(), "Erro",
                                 f"Erro ao aplicar material: {e}")
            return False  # Indica falha
        finally:
            tbl.blockSignals(False)
        return True  # Sucesso
    return False  # Indica que o diálogo foi cancelado


# Parte 15: Conexão principal do modulo
# Esta função conecta o botão "Inserir_Pecas_Selecionadas" e o sinal itemChanged.
# A conexão itemChanged deve estar aqui ou em main.py, apenas uma vez.
def conectar_inserir_def_pecas_tab_items(ui):
    """
    Conecta o botão 'Inserir_Pecas_Selecionadas' à função de inserção e o sinal itemChanged.
    A conexão do cellChanged para a lógica BLK agora é feita em main.py ou setup inicial.
    """
    print("[INFO] ------------------------>> Conectando funcionalidades da tabela de Definição de Peças.")
    # Conecta o botão de inserção de peças selecionadas
    try:
        # Desconecta para evitar duplicação de conexões se chamado mais de uma vez
        ui.Inserir_Pecas_Selecionadas.clicked.disconnect()
    except TypeError:  # Sinal não estava conectado
        pass
    ui.Inserir_Pecas_Selecionadas.clicked.connect(
        lambda: inserir_pecas_selecionadas(ui))
    # print("[INFO] Botão 'Inserir Peças Selecionadas' conectado.")


# Parte 16: Função Auxiliar para chaves na tab_modulo_medidas (Implementada Aqui)
def actualizar_ids_num_orc_ver_orc_tab_modulo_medidas(ui, ids_val, num_orc_val, ver_orc_val):
    """
    Atualiza os campos 'ids', 'num_orc', e 'ver_orc' na tabela tab_modulo_medidas
    (primeira linha, colunas 15, 16, 17) e define-os como não editáveis.
    """
    tbl = ui.tab_modulo_medidas

    # === INÍCIO MODIFICAÇÃO: Formatar ver_orc para definir no item da tabela UI ===
    # A formatação já deve vir do orcamento_items.py ao carregar/definir
    # o lineEdit_versao_orcamento. Apenas usamos o valor passado.
    # ver_orc_val já deve ser algo como "00", "01", etc.
    # Vamos manter a formatação aqui por segurança, caso seja chamado de outro sítio.
    ver_orc_formatado = "00"  # Valor por defeito formatado
    if ver_orc_val is not None:
        try:
            ver_orc_int = int(str(ver_orc_val).strip())
            ver_orc_formatado = f"{ver_orc_int:02d}"
        except (ValueError, TypeError):
            ver_orc_formatado = str(ver_orc_val).strip() if str(
                ver_orc_val).strip() else "00"
    # === FIM MODIFICAÇÃO ===

    # Garantir que existe pelo menos uma linha (assumimos a primeira)
    if tbl.rowCount() == 0:
        tbl.insertRow(0)

    row = 0  # Assuming only the first row is used for these identifiers

    # Define os textos nas células usando set_item e depois configura flags
    tbl.blockSignals(True)  # Prevent signals during update
    try:
        # Coluna 15: ids
        set_item(tbl, row, 15, ids_val)
        item_ids = tbl.item(row, 15)
        if item_ids:
            item_ids.setFlags(item_ids.flags() & ~Qt.ItemIsEditable)

        # Coluna 16: num_orc
        set_item(tbl, row, 16, num_orc_val)
        item_num = tbl.item(row, 16)
        if item_num:
            item_num.setFlags(item_num.flags() & ~Qt.ItemIsEditable)

        # Coluna 17: ver_orc
        set_item(tbl, row, 17, ver_orc_formatado)  # Usa a versão formatada
        item_ver = tbl.item(row, 17)
        if item_ver:
            item_ver.setFlags(item_ver.flags() & ~Qt.ItemIsEditable)

        # Optional: Set initial empty items for other columns if they don't exist
        # Garante que todas as colunas da primeira linha têm item (para evitar erros futuros)
        for col in range(tbl.columnCount()):
            if col not in [15, 16, 17]:  # Não sobrescrevemos as chaves que acabamos de definir
                item = tbl.item(row, col)  # Get item
                if item is None:
                    item = QTableWidgetItem("")  # Create new item
                    tbl.setItem(row, col, item)  # Correctly set new item
                # else: o item já existe, não faz nada

        print(
            f"[INFO] Tab_modulo_medidas chaves atualizadas: ids='{ids_val}', num='{num_orc_val}', ver='{ver_orc_formatado}'.")

    except IndexError:
        print("[ERRO] actualizar_ids_num_orc_ver_orc_tab_modulo_medidas: Índice de coluna fora do range. Verifique se a tabela tem colunas 15, 16, 17.")
    except Exception as e:
        print(
            f"[ERRO] actualizar_ids_num_orc_ver_orc_tab_modulo_medidas: Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
    finally:
        tbl.blockSignals(False)  # Re-enable signals


# Parte 8: show_context_menu (mantida)
def show_context_menu(ui, pos):
    """
    Exibe o menu de contexto para a tabela 'tab_def_pecas'.
    """
    # Importação local da função de orquestração para a ação de exclusão/inserção
    from modulo_orquestrador import atualizar_tudo

    table = ui.tab_def_pecas
    menu = QMenu()

    # Ações do menu
    action_delete = menu.addAction("Excluir Linha(s) Selecionada(s)")
    action_insert_above = menu.addAction("Inserir Linha Vazia Acima")
    action_insert_below = menu.addAction("Inserir Linha Vazia Abaixo")
    action_copy = menu.addAction(
        "Copiar Linha(s) (Não Implementado)")  # Manter como placeholder

    # Desabilitar ações se nenhuma linha estiver selecionada (exceto inserir no final)
    selected_rows = table.selectionModel().selectedRows()
    if not selected_rows:
        action_delete.setEnabled(False)
        action_insert_above.setEnabled(False)
        action_copy.setEnabled(False)  # Desabilitar copiar se nada selecionado

    # Executa o menu e espera pela ação do utilizador
    action = menu.exec_(table.viewport().mapToGlobal(pos))

    # Processa a ação selecionada
    if action == action_delete:
        if QMessageBox.question(table.window(), "Confirmar Exclusão", f"Deseja excluir {len(selected_rows)} linha(s) selecionada(s)?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            # Coleta os índices das linhas selecionadas e os remove (do último para o primeiro)
            for index in sorted(selected_rows, key=lambda x: x.row(), reverse=True):
                table.removeRow(index.row())

            # Após a exclusão, renumera os IDs e chama o orquestrador para reprocessar tudo (cálculos, etc.)
            update_ids(table)
            print(
                "[INFO] Menu Contexto: Chamando orquestrador após exclusão de linha(s).")
            atualizar_tudo(ui)  # Passa a referência da UI

    # __________

    elif action == action_insert_above:
        # Determina a linha de inserção (acima da primeira linha selecionada, ou no final se nada selecionado)
        current_row = selected_rows[0].row(
        ) if selected_rows else table.rowCount()
        table.setProperty("importando_dados", True)
        table.blockSignals(True)
        try:
            table.insertRow(current_row)
            # Inicializa colunas essenciais da nova linha vazia
            # Descricao_Livre, Def_Peca, Mat_Default, Tab_Default (col 0 é ID)
            for col in [1, 2, 13, 14]:
                set_item(table, current_row, col, "")
                item = table.item(current_row, col)
                if item:
                    if col == 2:
                        item.setFlags(item.flags() | Qt.ItemIsEditable)
                    else:
                        item.setFlags(Qt.ItemIsEnabled |
                                      Qt.ItemIsSelectable | Qt.ItemIsEditable)

            # Inicializa Checkboxes (Unchecked) para colunas importantes
            for col in [9, 10, 11, 12, 53, 59, 60]:
                chk = QTableWidgetItem()
                chk.setFlags(chk.flags() | Qt.ItemIsUserCheckable |
                             Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                chk.setCheckState(Qt.Unchecked)
                table.setItem(current_row, col, chk)

            # Inicializa colunas de IDs/Orcamento (15-17)
            set_item(table, current_row, 15,
                     ui.lineEdit_item_orcamento.text().strip())
            set_item(table, current_row, 16,
                     ui.lineEdit_num_orcamento.text().strip())
            set_item(table, current_row, 17,
                     ui.lineEdit_versao_orcamento.text().strip())
            item_ids = table.item(current_row, 15)
            if item_ids:
                item_ids.setFlags(item_ids.flags() & ~Qt.ItemIsEditable)
            item_num = table.item(current_row, 16)
            if item_num:
                item_num.setFlags(item_num.flags() & ~Qt.ItemIsEditable)
            item_ver = table.item(current_row, 17)
            if item_ver:
                item_ver.setFlags(item_ver.flags() & ~Qt.ItemIsEditable)

            # Inicializa o botão "Escolher" (coluna 33)
            btn = QPushButton("Escolher")
            btn.clicked.connect(
                lambda _, r=current_row: on_mp_button_clicked(ui, r, "tab_def_pecas"))
            table.setCellWidget(current_row, 33, btn)

            # Inicializa outras colunas numéricas/texto como vazias/0
            for col in range(3, 82):
                if col in [9, 10, 11, 12, 33, 53, 59, 60]:
                    continue
                set_item(table, current_row, col, "")
        finally:
            table.blockSignals(False)
            table.setProperty("importando_dados", False)

        # Após a inserção, renumera os IDs e chama o orquestrador
        update_ids(table)
        print(
            f"[INFO] Menu Contexto: Chamando orquestrador após inserção de linha vazia acima na linha {current_row+1}.")
        atualizar_tudo(ui)

    elif action == action_insert_below:
        # Determina a linha de inserção (abaixo da última linha selecionada, ou no final se nada selecionado)
        # Se selected_rows está vazio, currentRow() pode ser -1, então insere no final.
        current_row = selected_rows[-1].row() + \
            1 if selected_rows else table.rowCount()

        table.setProperty("importando_dados", True)
        table.blockSignals(True)
        try:
            table.insertRow(current_row)
            # Inicializa colunas essenciais da nova linha vazia (similar a inserir acima)
            for col in [1, 2, 13, 14]:
                set_item(table, current_row, col, "")
                item = table.item(current_row, col)
                if item:
                    if col == 2:
                        item.setFlags(item.flags() | Qt.ItemIsEditable)
                    else:
                        item.setFlags(Qt.ItemIsEnabled |
                                      Qt.ItemIsSelectable | Qt.ItemIsEditable)

            # Inicializa Checkboxes (Unchecked)
            for col in [9, 10, 11, 12, 53, 59, 60]:
                chk = QTableWidgetItem()
                chk.setFlags(Qt.ItemIsUserCheckable |
                             Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                chk.setCheckState(Qt.Unchecked)
                table.setItem(current_row, col, chk)

            # Inicializa colunas de IDs/Orcamento (15-17)
            set_item(table, current_row, 15,
                     ui.lineEdit_item_orcamento.text().strip())
            set_item(table, current_row, 16,
                     ui.lineEdit_num_orcamento.text().strip())
            set_item(table, current_row, 17,
                     ui.lineEdit_versao_orcamento.text().strip())
            item_ids = table.item(current_row, 15)
            if item_ids:
                item_ids.setFlags(item_ids.flags() & ~Qt.ItemIsEditable)
            item_num = table.item(current_row, 16)
            if item_num:
                item_num.setFlags(item_num.flags() & ~Qt.ItemIsEditable)
            item_ver = table.item(current_row, 17)
            if item_ver:
                item_ver.setFlags(item_ver.flags() & ~Qt.ItemIsEditable)

            # Inicializa o botão "Escolher" (coluna 33)
            btn = QPushButton("Escolher")
            btn.clicked.connect(
                lambda _, r=current_row: on_mp_button_clicked(ui, r, "tab_def_pecas"))
            table.setCellWidget(current_row, 33, btn)

            # Inicializa outras colunas numéricas/texto como vazias/0
            for col in range(3, 82):
                if col in [9, 10, 11, 12, 33, 53, 59, 60]:
                    continue
                set_item(table, current_row, col, "")
        finally:
            table.blockSignals(False)
            table.setProperty("importando_dados", False)

        # Após a inserção, renumera os IDs e chama o orquestrador␊
        update_ids(table)
        print(
            f"[INFO] Menu Contexto: Chamando orquestrador após inserção de linha vazia abaixo na linha {current_row+1}.")
        atualizar_tudo(ui)

    elif action == action_copy:
        # Placeholder para futura implementação
        print("Ação 'Copiar Linha(s)' selecionada. Funcionalidade a implementar.")

# Parte 3.1: install_def_peca_delegate (mantida, usa DefPecaDelegate)


def install_def_peca_delegate(ui, parent, opcoes_por_grupo=None):
    """
    Instala o delegate DefPecaDelegate para a coluna "Def_Peca" (coluna 2).
    """
    # 1) Se não foi passado, gera o dicionário de opções igual ao setup_context_menu
    if opcoes_por_grupo is None:
        grupos_widgets = {
            "caixote": ui.listWidget_caixote_4,
            "ferragens": ui.listWidget_ferragens_4,
            "mao_obra": ui.listWidget_mao_obra_4,
            "paineis": ui.listWidget_paineis_4,
            "remates_guarnicoes": ui.listWidget_remates_guarnicoes_4,
            "sistemas_correr": ui.listWidget_sistemas_correr_4,
            "acabamentos": ui.listWidget_acabamentos_4
        }
        opcoes_por_grupo = {
            grupo.lower(): [widget.item(i).text() for i in range(widget.count())]
            for grupo, widget in grupos_widgets.items()
        }

    # 2) Cria e instala o delegate
    delegate = DefPecaDelegate(parent, ui, opcoes_por_grupo)
    coluna_def_peca = 2  # coluna Def_Peca
    ui.tab_def_pecas.setItemDelegateForColumn(coluna_def_peca, delegate)
    # (Opcional) print("[INFO] Delegate instalado com opções:", opcoes_por_grupo.keys())

# Parte 6.1: CelulaEdicaoDelegate (mantida, já revisada)
# class CelulaEdicaoDelegate(QStyledItemDelegate): ...
