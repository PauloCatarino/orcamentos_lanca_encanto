#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dados_gerais_ferragens.py
=========================
Módulo específico para configurar a tabela de Dados Gerais de Ferragens.
Neste módulo são definidas:
  - A estrutura das colunas (FERRAGENS_COLUNAS) e das linhas (FERRAGENS_LINHAS);
  - A criação/configuração da tabela no banco de dados MySQL e na interface;
  - As funções dos botões Guardar, Importar e Limpar, seguindo a mesma lógica
    aplicada à Tab_Material (ex.: para Materiais).
  
Certifique-se de que o módulo "db_connection.py" esteja devidamente configurado para 
retornar uma conexão MySQL.
"""
import mysql.connector # Para capturar erros específicos
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLineEdit, QComboBox, QHeaderView)
from PyQt5.QtCore import Qt
# Obtém a conexão MySQL via o módulo de conexão

# Funções para criação/configuração de tabelas de dados gerais (delegadas para um módulo base)
from dados_gerais_base import criar_tabela_dados_gerais, configurar_tabela_dados_gerais_ui, get_distinct_values
# Diálogo de seleção de material (usado para filtrar/selecionar ferragens a partir da tabela de matérias-primas)
from dados_gerais_materiais_escolher import MaterialSelectionDialog
from utils import (formatar_valor_moeda, formatar_valor_percentual, original_pliq_values, converter_texto_para_valor, get_distinct_values_with_filter, install_header_width_menu)
# Lista de colunas a limpar definida em dados_gerais_mp.py
from dados_gerais_mp import COLUNAS_LIMPAR_FERRAGENS

# Definição das colunas para a tabela de Ferragens
FERRAGENS_COLUNAS = [
    {'nome': 'ferragens', 'tipo': 'TEXT', 'visivel': True, 'editavel': False},
    {'nome': 'descricao', 'tipo': 'TEXT', 'visivel': True, 'editavel': True},
    {'nome': 'id_fer', 'tipo': 'INTEGER', 'visivel': False},
    {'nome': 'num_orc', 'tipo': 'INTEGER', 'visivel': False},
    {'nome': 'ver_orc', 'tipo': 'INTEGER', 'visivel': False},
    {'nome': 'ref_le', 'tipo': 'TEXT', 'visivel': True, 'editavel': False},
    {'nome': 'descricao_no_orcamento', 'tipo': 'TEXT', 'visivel': True, 'editavel': True},
    {'nome': 'ptab', 'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'pliq', 'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'desc1_plus', 'tipo': 'REAL', 'visivel': True, 'editavel': True, 'header': 'Margem'},
    {'nome': 'desc2_minus', 'tipo': 'REAL', 'visivel': True, 'editavel': True, 'header': 'Desconto'},
    {'nome': 'und', 'tipo': 'TEXT', 'visivel': True, 'editavel': True},
    {'nome': 'desp', 'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'corres_orla_0_4', 'tipo': 'TEXT', 'visivel': True, 'editavel': True},
    {'nome': 'corres_orla_1_0', 'tipo': 'TEXT', 'visivel': True, 'editavel': True},
    {'nome': 'tipo', 'tipo': 'TEXT', 'visivel': True, 'editavel': True, 'combobox': True, 'opcoes': lambda: get_distinct_values_with_filter("TIPO", "FAMILIA", "FERRAGENS")},
    {'nome': 'familia', 'tipo': 'TEXT', 'visivel': True, 'editavel': True, 'combobox': True, 'opcoes': lambda: ["FERRAGENS"]},
    {'nome': 'comp_mp', 'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'larg_mp', 'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'esp_mp', 'tipo': 'REAL', 'visivel': True, 'editavel': True},
    {'nome': 'MP', 'tipo': 'TEXT', 'visivel': True, 'botao': True, 'texto_botao': 'Escolher', 'funcao_botao': None}
]
# Para facilitar a visualização das larguras, segue o mapeamento das colunas com seus nomes:
# (índice, nome, largura)
FERRAGENS_COLUNAS_LARGURAS = [
    (0,  'ferragens',            200),
    (1,  'descricao',            200),
    (2,  'id_fer',                50),
    (3,  'num_orc',              110),
    (4,  'ver_orc',               50),
    (5,  'ref_le',               100),
    (6,  'descricao_no_orcamento', 400),
    (7,  'ptab',                  60),
    (8,  'pliq',                  60),
    (9,  'desc1_plus',            60),
    (10, 'desc2_minus',           60),
    (11, 'und',                   50),
    (12, 'desp',                  50),
    (13, 'corres_orla_0_4',      180),
    (14, 'corres_orla_1_0',      110),
    (15, 'tipo',                 120),
    (16, 'familia',              120),
    (17, 'comp_mp',               90),
    (18, 'larg_mp',               90),
    (19, 'esp_mp',                90),
    (20, 'MP',                   100),
]

# Definição dos nomes das linhas para a tabela de Ferragens
FERRAGENS_LINHAS = [
    'Fer_Dobradica_1', 'Fer_Dobradica_2',
    'Fer_Suporte Prateleira_1', 'Fer_Suporte Prateleira_2', 'Fer_Suporte Varao', 'Fer_Varao_SPP','Fer_Perfil_SPP', 'Fer_Terminais',
    'Fer_Rodape_PVC', 'Fer_Pes_1', 'Fer_Pes_2', 'Fer_Grampas', 'Fer_Corredica_1',
    'Fer_Corredica_2', 'Fer_Corredica_3', 'Fer_Puxador STD', 'Fer_Puxador Fresado J', 'Fer_Puxador_SPP_1',
    'Fer_Puxador_SPP_2', 'Fer_Puxador_SPP_3', 'Fer_Sistema_Basculante_1',
    'Fer_Sistema_Basculante_2', 'Fer_Balde Lixo', 'Fer_Canto Cozinha_1', 'Fer_Canto Cozinha_2', 'Fer_Porta Talheres', 'Fer_Porta Calcas',
    'Fer_Fundo Aluminio', 'Fer_Calha Led', 'Fer_Fita Led', 'Fer_Transformador Led', 'Fer_Cabos Led_1', 'Fer_Cabos Led_2',
    'Fer_Sensor Led_1', 'Fer_Sensor Led_2', 'Fer_Iluminacao_1', 'Fer_Iluminacao_2', 'Fer_Iluminacao_3', 'Fer_Ferragem_Diversas',
    'Fer_Acessorio_1', 'Fer_Acessorio_2',
    'Fer_Acessorio_3', 'Fer_Acessorio_4', 'Fer_Acessorio_5', 'Fer_Acessorio_6',
    'Fer_Acessorio_7', 'Fer_Acessorio_8_SPP'
]

def escolher_ferragens(ui, linha_tab, nome_tabela):
    """
    Abre um diálogo para seleção de ferragens a partir da tabela de matérias-primas,
    aplicando pré-filtros para 'tipo' e 'familia' se definidos.
    Após a seleção, mapeia os dados da linha selecionada para a linha da Tab_Ferragens
    e recalcula 'pliq' utilizando a fórmula:
         pliq = (PRECO_TABELA*(1-DESC2_MINUS))*(1+DESC1_PLUS)
    
    Retorna True se um material for selecionado; caso contrário, retorna False.
    """
    from PyQt5.QtWidgets import QTableWidgetItem, QDialog
    tbl_ferragens = getattr(ui, 'Tab_Ferragens')
    tbl_ferragens.blockSignals(True)
    
    # Obtém pré-filtros (TIPO e FAMILIA) se disponíveis
    tipo_col_idx = next((i for i, col in enumerate(FERRAGENS_COLUNAS) if col['nome'] == 'tipo'), None)
    familia_col_idx = next((i for i, col in enumerate(FERRAGENS_COLUNAS) if col['nome'] == 'familia'), None)
    pre_tipo = (tbl_ferragens.cellWidget(linha_tab, tipo_col_idx).currentText()
                if (tipo_col_idx is not None and tbl_ferragens.cellWidget(linha_tab, tipo_col_idx))
                else "")
    pre_familia = (tbl_ferragens.cellWidget(linha_tab, familia_col_idx).currentText()
                   if (familia_col_idx is not None and tbl_ferragens.cellWidget(linha_tab, familia_col_idx))
                   else "")
    
    dialog = MaterialSelectionDialog(ui.tableWidget_materias_primas, pre_tipo, pre_familia)
    if dialog.exec_() == QDialog.Accepted:
        row_idx = dialog.selected_row
        # Mapeamento: (source_index na tabela de matérias-primas, target_index na Tab_Ferragens)
        col_map = {
            'ref_le': (3, 5),
            'descricao_no_orcamento': (5, 6),
            'ptab': (6, 7),
            'desc1_plus': (7, 9),
            'desc2_minus': (8, 10),
            'und': (10, 11),
            'desp': (11, 12),
            'corres_orla_0_4': (16, 13),
            'corres_orla_1_0': (17, 14),
            'comp_mp': (19, 17),
            'larg_mp': (20, 18),
            'esp_mp': (12, 19)
        }
        # Limpa os campos de destino na linha selecionada da Tab_Ferragens
        for campo, (src_idx, tgt_idx) in col_map.items():
            tbl_ferragens.setItem(linha_tab, tgt_idx, QTableWidgetItem(""))

        def set_item(row, col_idx, texto):
            item = tbl_ferragens.item(row, col_idx)
            if not item:
                from PyQt5.QtWidgets import QTableWidgetItem
                item = QTableWidgetItem()
                tbl_ferragens.setItem(row, col_idx, item)
            item.setText(texto)

        ptab_valor = 0.0
        dplus = 0.0
        dminus = 0.0      
        # Mapeia os dados da linha selecionada na tabela de matérias-primas para a Tab_Ferragens
        for campo, (source_idx, target_idx) in col_map.items():
            valor = ""
            cell = dialog.table.item(row_idx, source_idx)
            if cell:
                valor = cell.text()
            set_item(linha_tab, target_idx, valor)
            if campo == 'ptab':
                ptab_valor = converter_texto_para_valor(valor, "moeda")
            elif campo == 'desc1_plus':
                dplus = converter_texto_para_valor(valor, "percentual")
            elif campo == 'desc2_minus':
                dminus = converter_texto_para_valor(valor, "percentual")
        novo_pliq = round((ptab_valor * (1 - dminus)) * (1 + dplus), 2)
        set_item(linha_tab, 8, formatar_valor_moeda(novo_pliq))
        
        tbl_ferragens.blockSignals(False)
        return True
    tbl_ferragens.blockSignals(False)
    return False

def definir_larguras_tab_ferragens(ui):
    """
    Define larguras padrão para cada coluna da Tab_Ferragens,
    mas só aplica se ainda não existirem larguras gravadas pelo utilizador.
    Permite ajuste manual e ativa persistência.
    """
    tabela = ui.Tab_Ferragens
    header = tabela.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.Interactive)  # Permite ajuste manual!
    header.setStretchLastSection(False)

    # Ativa persistência de larguras (usa QSettings)
    from utils import enable_column_width_persistence
    enable_column_width_persistence(tabela, "Tab_Ferragens_column_widths")

    # Só define larguras por defeito se ainda não existirem larguras gravadas
    from PyQt5.QtCore import QSettings
    settings = QSettings("LANCA ENCANTO", "Orcamentos")
    key = "Tab_Ferragens_column_widths"
    stored_widths = settings.value(key)

    if not stored_widths:
        larguras = [l[2] if isinstance(l, tuple) else l for l in FERRAGENS_COLUNAS_LARGURAS]
        num_cols = tabela.columnCount()
        if len(larguras) < num_cols:
            larguras += [100] * (num_cols - len(larguras))
        for idx in range(num_cols):
            tabela.setColumnWidth(idx, larguras[idx])

def on_mp_button_clicked(ui, row, nome_tabela):
    """
    Função chamada quando o botão "Escolher" (na coluna MP) é clicado na Tab_Ferragens.
    Abre o diálogo para seleção de ferragens e exibe uma mensagem informando o resultado.
    """
    if escolher_ferragens(ui, row, nome_tabela):
        QMessageBox.information(None, "Ferragens", f"Ferragens selecionado para a linha {row+1}.")

for col in FERRAGENS_COLUNAS:
    if col['nome'] == 'MP':
        col['funcao_botao'] = on_mp_button_clicked

def configurar_ferragens_ui(ui):
    """
    Configura a tabela de Dados Gerais para Ferragens:
      - Cria a tabela no banco de dados (se ainda não existir) usando as definições.
      - Configura o QTableWidget (widget 'Tab_Ferragens') conforme os parâmetros definidos.
    """
    #print("DEBUG: Executando configurar_ferragens_ui para ferragens.")
    criar_tabela_dados_gerais('ferragens', FERRAGENS_COLUNAS, FERRAGENS_LINHAS)
    # Configura a tabela de Dados Gerais na interface na coluna familia preenche com 'FERRAGENS' & coluna tipo com valores predefinidos exemplo: 'DOBRADICAS', 'SUPORTE_PRATELEIRA', etc.
    configurar_tabela_dados_gerais_ui(ui, 'ferragens', FERRAGENS_COLUNAS, FERRAGENS_LINHAS)
    definir_larguras_tab_ferragens(ui)
    install_header_width_menu(ui.Tab_Ferragens)

    from utils import apply_row_selection_style
    tabela = ui.Tab_Ferragens
    familia_idx = next((i for i, c in enumerate(FERRAGENS_COLUNAS) if c['nome'] == 'familia'), None)
    tipo_idx = next((i for i, c in enumerate(FERRAGENS_COLUNAS) if c['nome'] == 'tipo'), None)
    tipo_padrao = {
        'Fer_Dobradica_1': 'DOBRADICAS',
        'Fer_Dobradica_2': 'DOBRADICAS',
        'Fer_Suporte Prateleira_1': 'SUPORTE PRATELEIRA',
        'Fer_Suporte Prateleira_2': 'SUPORTE PRATELEIRA',
        'Fer_Suporte Varao': 'SUPORTE VARAO',
        'Fer_Varao_SPP': 'SPP',
        'Fer_Rodape_PVC': 'RODAPE',
        'Fer_Suporte Varao': 'SUPORTE VARAO',
        'Fer_Varao_SPP': 'SPP',
        'Fer_Perfil_SPP': 'SUPORTE VARAO',
        'Fer_Terminais': 'SPP',
        'Fer_Rodape_PVC': 'RODAPE',
        'Fer_Pes_1': 'PES',
        'Fer_Pes_2': 'PES',
        'Fer_Grampas': 'PES',
        'Fer_Corredica_1': 'CORREDICAS',
        'Fer_Corredica_2': 'CORREDICAS',
        'Fer_Corredica_3': 'CORREDICAS',
        'Fer_Puxador STD': 'PUXADOR',
        'Fer_Puxador Fresado J': 'PUXADOR',
        'Fer_Puxador_SPP_1': 'SPP',
        'Fer_Puxador_SPP_2': 'SPP',
        'Fer_Puxador_SPP_3': 'SPP',
        'Fer_Sistema_Basculante_1': 'ACESSORIOS',
        'Fer_Sistema_Basculante_2': 'ACESSORIOS',
        'Fer_Balde Lixo': 'ACESSORIOS',
        'Fer_Canto Cozinha_1': 'ACESSORIOS',
        'Fer_Canto Cozinha_2': 'ACESSORIOS',
        'Fer_Porta Talheres': 'ACESSORIOS',
        'Fer_Porta Calcas': 'ACESSORIOS',
        'Fer_Fundo Aluminio': 'ACESSORIOS',
        'Fer_Calha Led': 'ILUMINACAO',
        'Fer_Fita Led': 'ILUMINACAO',
        'Fer_Transformador Led': 'ILUMINACAO',
        'Fer_Cabos Led_1': 'ILUMINACAO',
        'Fer_Cabos Led_2': 'ILUMINACAO',
        'Fer_Sensor Led_1': 'ILUMINACAO',
        'Fer_Sensor Led_2': 'ILUMINACAO',
        'Fer_Iluminacao_1': 'ILUMINACAO',
        'Fer_Iluminacao_2': 'ILUMINACAO',
        'Fer_Iluminacao_3': 'ILUMINACAO',
        'Fer_Ferragem_Diversas': 'FERRAGENS',
        'Fer_Acessorio_1': 'ACESSORIOS',
        'Fer_Acessorio_2': 'ACESSORIOS',
        'Fer_Acessorio_3': 'ACESSORIOS',
        'Fer_Acessorio_4': 'ACESSORIOS',
        'Fer_Acessorio_5': 'ACESSORIOS',
        'Fer_Acessorio_6': 'ACESSORIOS',
        'Fer_Acessorio_7': 'ACESSORIOS'
    }
    for r, nome in enumerate(FERRAGENS_LINHAS):
        if familia_idx is not None:
            combo = tabela.cellWidget(r, familia_idx)
            if isinstance(combo, QComboBox):
                idx = combo.findText('FERRAGENS')
                if idx >= 0:
                    combo.setCurrentIndex(idx)
        if tipo_idx is not None:
            combo = tabela.cellWidget(r, tipo_idx)
            if isinstance(combo, QComboBox):
                padrao = tipo_padrao.get(nome, '')
                idx = combo.findText(padrao)
                if idx >= 0 and padrao:
                    combo.setCurrentIndex(idx)
                else:
                    combo.setCurrentIndex(-1)
    apply_row_selection_style(tabela)

def on_item_changed_ferragens(item):
    """
    Trata as alterações na tabela de Ferragens.
    Se o usuário editar os campos 'ptab' (col. 7), 'desc1_plus' (col. 9) ou 'desc2_minus' (col. 10),
    recalcula o valor de 'pliq' (col. 8) usando a fórmula:
         pliq = (PRECO_TABELA*(1-DESC2_MINUS))*(1+DESC1_PLUS)
    Aplica também formatação de moeda para 'pliq' e formatação percentual para os descontos.
    """
    if not item:
        return

    table = item.tableWidget()
    if table.property("importando"):
        return

    row = item.row()
    col = item.column()

    if col in [7, 9, 10]:
        try:
            ptab_item = table.item(row, 7)
            ptab_text = ptab_item.text() if ptab_item else "0"
            ptab_valor = converter_texto_para_valor(ptab_text, "moeda")
            
            desc1_item = table.item(row, 9)
            desc2_item = table.item(row, 10)
            desc1_text = desc1_item.text() if desc1_item else "0%"
            desc2_text = desc2_item.text() if desc2_item else "0%"
            dplus = converter_texto_para_valor(desc1_text, "percentual")
            dminus = converter_texto_para_valor(desc2_text, "percentual")
            # Recalcula PLIQ usando a fórmula:
            # PLIQ = (PRECO_TABELA*(1-DESC2_MINUS))*(1+DESC1_PLUS)           
            novo_pliq = round((ptab_valor * (1 - dminus)) * (1 + dplus), 2)
        except Exception:
            novo_pliq = 0.0

        table.blockSignals(True)
        pliq_item = table.item(row, 8)
        if not pliq_item:
            from PyQt5.QtWidgets import QTableWidgetItem
            pliq_item = QTableWidgetItem()
            table.setItem(row, 8, pliq_item)
        pliq_item.setText(formatar_valor_moeda(novo_pliq))
        table.blockSignals(False)

        # Se o usuário editou uma das porcentagens, formata a célula como percentual
        if col == 9:
            table.blockSignals(True)
            item.setText(formatar_valor_percentual(dplus))
            table.blockSignals(False)
        elif col == 10:
            table.blockSignals(True)
            item.setText(formatar_valor_percentual(dminus))
            table.blockSignals(False)
        if col == 7:
            table.blockSignals(True)
            item.setText(formatar_valor_moeda(ptab_valor))
            table.blockSignals(False)
    elif col == 8:
        # Se PLIQ for editado diretamente, apenas formata como moeda
        try:
            novo_valor = float(item.text().replace("€", "").replace(",", ".").strip())
        except Exception:
            novo_valor = 0.0
        table.blockSignals(True)
        item.setText(f"{novo_valor:.2f}€")
        table.blockSignals(False)
