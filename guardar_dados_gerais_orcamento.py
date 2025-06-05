#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Módulo: guardar_dados_gerais_orcamento.py

Descrição:
Este módulo implementa a funcionalidade de guardar os dados gerais de um orçamento,
associando os dados das 4 abas (materiais, ferragens, sistemas_correr e acabamentos)
ao orçamento atual (num_orc + ver_orc). Se já existirem registros para o orçamento,
o usuário é questionado se deseja substituí-los. Os dados são extraídos do QTableWidget,
e os valores apresentados com formatação (ex.: "12,36€", "6%") são convertidos para seus
respectivos valores numéricos (raw) antes de serem gravados no banco de dados MySQL.

Como usar:
1. Salve este código em um arquivo chamado guardar_dados_gerais_orcamento.py.
2. No módulo onde o botão “Guardar para este Orçamento Dados Gerais” está definido (por exemplo,
   dados_gerais_materiais.py), importe a função:
       from guardar_dados_gerais_orcamento import guardar_dados_gerais_orcamento
3. Conecte o clique do botão à função, por exemplo:
       btn_guardar_orcamento.clicked.connect(lambda: guardar_dados_gerais_orcamento(ui))
   
Certifique-se de que o módulo "orcamentos" possua a função get_connection() devidamente configurada.
"""


'''
from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem
from orcamentos import get_connection  # Certifique-se de que este módulo está corretamente configurado.
from utils import converter_texto_para_valor

def get_cell_value(table, row, col):
    """
    Retorna o valor (texto) da célula na linha e coluna indicadas.
    Se existir um widget na célula (por exemplo, QComboBox), retorna o seu texto.
    """
    widget = table.cellWidget(row, col)
    if widget is not None:
        if hasattr(widget, "currentText"):
            return widget.currentText().strip()
        else:
            return str(widget.text()).strip()
    else:
        item = table.item(row, col)
        return item.text().strip() if item is not None else ""

def guardar_por_tabela(parent, nome_tabela, table_widget, mapping, col_names):
    """
    Salva os dados do QTableWidget da aba correspondente à tabela <nome_tabela> na base de dados,
    associando os dados ao orçamento atual (num_orc e ver_orc).

    Parâmetros:
      parent: o main_window (QMainWindow) que contém a interface; usaremos parent.ui para acesso aos widgets.
      nome_tabela: string (ex.: "materiais", "ferragens", "sistemas_correr", "acabamentos").
      table_widget: QTableWidget da respectiva aba.
      mapping: dicionário que mapeia os nomes dos campos do banco (exceto num_orc e ver_orc)
               para o índice da coluna no QTableWidget.
      col_names: lista com os nomes das colunas a serem inseridas no banco, na ordem desejada.
                 Os campos "num_orc" e "ver_orc" são preenchidos com os valores do orçamento.
    """
    ui = parent.ui
    # Obter os valores de num_orc e ver_orc a partir dos widgets da aba Orçamento
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    ver_orc = ui.lineEdit_versao_orcamento.text().strip()
    if not num_orc or not ver_orc:
        QMessageBox.warning(parent, "Aviso", "Os campos 'Num Orçamento' e 'Versão' devem estar preenchidos!")
        return False

    # Verificar se já existem registros para este orçamento na tabela
    conn = get_connection()
    cur = conn.cursor()
    query_check = f"SELECT COUNT(*) FROM dados_gerais_{nome_tabela} WHERE num_orc=%s AND ver_orc=%s"
    cur.execute(query_check, (num_orc, ver_orc))
    count = cur.fetchone()[0]
    if count > 0:
        resposta = QMessageBox.question(
            parent,
            "Dados já existentes",
            f"Já existem {count} registro(s) para este orçamento na tabela '{nome_tabela}'.\nDeseja substituir?",
            QMessageBox.Yes | QMessageBox.No
        )
        if resposta == QMessageBox.No:
            conn.close()
            return False
        else:
            # Excluir registros existentes
            query_delete = f"DELETE FROM dados_gerais_{nome_tabela} WHERE num_orc=%s AND ver_orc=%s"
            cur.execute(query_delete, (num_orc, ver_orc))
            conn.commit()

    # Percorrer cada linha do QTableWidget e montar os dados para inserção
    num_rows = table_widget.rowCount()
    dados = []
     # Conjuntos dos campos que devem ser convertidos para float
    campos_moeda = {"ptab", "pliq", "comp_mp", "larg_mp", "esp_mp"}
    campos_percentual = {"desc1_plus", "desc2_minus", "desp"}
    for row in range(num_rows):
        registro = []
        for campo in col_names:
            if campo == "num_orc":
                registro.append(num_orc)
            elif campo == "ver_orc":
                registro.append(ver_orc)
            else:
                # Pega o índice da coluna do QTableWidget a partir do mapping
                idx = mapping.get(campo)
                if idx is not None:
                    valor = get_cell_value(table_widget, row, idx)
                    # Se o campo for numérico, converte o valor removendo símbolos e usando ponto decimal
                    if campo in campos_moeda:
                        try:
                            valor = converter_texto_para_valor(valor, "moeda")
                        except Exception:
                            valor = 0.0
                    elif campo in campos_percentual:
                        try:
                            valor = converter_texto_para_valor(valor, "percentual")
                        except Exception:
                            valor = 0.0
                    registro.append(valor)
                else:
                    # Se não estiver no mapping, grava vazio
                    registro.append("")
        dados.append(tuple(registro))

    # Preparar a query de inserção
    placeholders = ", ".join(["%s"] * len(col_names))
    col_names_str = ", ".join(col_names)
    query_insert = f"INSERT INTO dados_gerais_{nome_tabela} ({col_names_str}) VALUES ({placeholders})"
    try:
        cur.executemany(query_insert, dados)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        QMessageBox.critical(parent, "Erro", f"Erro ao guardar dados na tabela '{nome_tabela}': {e}")
        return False

def guardar_dados_gerais_orcamento(parent):
    """
    Função principal que guarda os dados gerais de um orçamento, associando os dados
    de cada uma das 4 abas (materiais, ferragens, sistemas_correr, acabamentos) ao orçamento
    atual (num_orc + ver_orc). Para cada tabela, chama a função auxiliar guardar_por_tabela()
    com o mapeamento específico de índices e nomes de colunas.
    """
    ui = parent.ui
    sucesso = True

    # Mapeamento e nomes de colunas para a aba Materiais
    mapping_materiais = {
        "descricao": 1,     # col 1 do QTableWidget
        #"id_mat": 2,            # col 2
        "ref_le": 5,            # col 5
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
        "larg_mp":18,
        "esp_mp": 19
    }
    col_names_materiais = [
        "descricao", "num_orc", "ver_orc",
        "ref_le", "descricao_no_orcamento", "ptab", "pliq",
        "desc1_plus", "desc2_minus", "und", "desp",
        "corres_orla_0_4", "corres_orla_1_0", "tipo", "familia",
        "comp_mp", "larg_mp", "esp_mp"
    ]
    if not guardar_por_tabela(parent, "materiais", ui.Tab_Material, mapping_materiais, col_names_materiais):
        sucesso = False

    # Mapeamento e nomes de colunas para a aba Ferragens
    mapping_ferragens = {
        "descricao": 1,
        #"id_fer": 2,
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
        "larg_mp":18,
        "esp_mp": 19
    }
    col_names_ferragens = [
        "descricao", "num_orc", "ver_orc",
        "ref_le", "descricao_no_orcamento", "ptab", "pliq",
        "desc1_plus", "desc2_minus", "und", "desp",
        "corres_orla_0_4", "corres_orla_1_0", "tipo", "familia",
        "comp_mp", "larg_mp", "esp_mp"
    ]
    if not guardar_por_tabela(parent, "ferragens", ui.Tab_Ferragens, mapping_ferragens, col_names_ferragens):
        sucesso = False

    # Mapeamento e nomes de colunas para a aba Sistemas de Correr
    mapping_sistemas_correr = {
        "descricao": 1,
        #"id_sc": 2,
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
        "larg_mp":18,
        "esp_mp": 19
    }
    col_names_sistemas_correr = [
        "descricao", "num_orc", "ver_orc",
        "ref_le", "descricao_no_orcamento", "ptab", "pliq",
        "desc1_plus", "desc2_minus", "und", "desp",
        "corres_orla_0_4", "corres_orla_1_0", "tipo", "familia",
        "comp_mp", "larg_mp", "esp_mp"
    ]
    if not guardar_por_tabela(parent, "sistemas_correr", ui.Tab_Sistemas_Correr, mapping_sistemas_correr, col_names_sistemas_correr):
        sucesso = False

    # Mapeamento e nomes de colunas para a aba Acabamentos
    mapping_acabamentos = {
        "descricao": 1,
        #"id_acb": 2,
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
        "larg_mp":18,
        "esp_mp": 19
    }
    col_names_acabamentos = [
        "descricao", "num_orc", "ver_orc",
        "ref_le", "descricao_no_orcamento", "ptab", "pliq",
        "desc1_plus", "desc2_minus", "und", "desp",
        "corres_orla_0_4", "corres_orla_1_0", "tipo", "familia",
        "comp_mp", "larg_mp", "esp_mp"
    ]
    if not guardar_por_tabela(parent, "acabamentos", ui.Tab_Acabamentos, mapping_acabamentos, col_names_acabamentos):
        sucesso = False

    if sucesso:
        QMessageBox.information(parent, "Sucesso", "Dados gerais do orçamento guardados com sucesso em todas as tabelas.")
    else:
        QMessageBox.warning(parent, "Aviso", "Ocorreu algum problema ao guardar os dados gerais do orçamento.")

'''