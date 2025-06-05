#!/usr/bin/env python
# -*- coding: utf-8 -*-

# possivelmente este modulo nao está aser implementado pode ser eliminado 21-03-2025


"""
Módulo: configurar_guardar_dados_items_orcamento.py

Descrição:
  Este módulo configura e grava os Dados dos Itens do Orçamento para as tabelas dos itens
  (Materiais, Ferragens, Sistemas Correr e Acabamentos). Para cada orçamento, usando os campos
  'num_orc', 'ver_orc' e o identificador do item (ex.: id_mat, id_fer, id_sc, id_acb),
  a função verifica se já existem dados salvos na respectiva tabela. Caso existam, os carrega na
  interface; caso contrário, preenche os campos fixos. Essa funcionalidade é acionada ao clicar
  nos botões de guardar dados para cada item do orçamento.
  
  Além disso, o módulo cria as tabelas de dados dos itens no banco de dados, se ainda não existirem.
  
Autor: Paulo Catarino
Data: 19/03/2025
"""

from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem
from orcamentos import get_connection
from utils import converter_texto_para_valor, formatar_valor_moeda, formatar_valor_percentual
import math

# =============================================================================================
# Função para criar a tabela na Base Dados ->de Dados Items Materiais, se ela ainda não existir
# ============================================================================================
def criar_tabela_dados_items_materiais():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dados_items_materiais (
            id INT AUTO_INCREMENT PRIMARY KEY,
            num_orc VARCHAR(50),
            ver_orc VARCHAR(10),
            id_mat VARCHAR(50),
            material TEXT,
            descricao TEXT,
            ref_le TEXT,
            descricao_no_orcamento TEXT,
            ptab REAL,
            pliq REAL,
            desc1_plus REAL,
            desc2_minus REAL,
            und TEXT,
            desp REAL,
            corres_orla_0_4 TEXT,
            corres_orla_1_0 TEXT,
            tipo TEXT,
            familia TEXT,
            comp_mp REAL,
            larg_mp REAL,
            esp_mp REAL,
            UNIQUE(num_orc, ver_orc, id_mat)
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


# =============================================================================================
# Função para criar a tabela na Base Dados ->de Dados Items Ferragens, se ela ainda não existir
# ============================================================================================
def criar_tabela_dados_items_ferragens():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dados_items_ferragens (
            id INT AUTO_INCREMENT PRIMARY KEY,
            num_orc VARCHAR(50),
            ver_orc VARCHAR(10),
            id_fer VARCHAR(50),
            material TEXT,
            descricao TEXT,
            ref_le TEXT,
            descricao_no_orcamento TEXT,
            ptab REAL,
            pliq REAL,
            desc1_plus REAL,
            desc2_minus REAL,
            und TEXT,
            desp REAL,
            corres_orla_0_4 TEXT,
            corres_orla_1_0 TEXT,
            tipo TEXT,
            familia TEXT,
            comp_mp REAL,
            larg_mp REAL,
            esp_mp REAL,
            UNIQUE(num_orc, ver_orc, id_fer)
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

# =============================================================================================
# Função para criar a tabela na Base Dados ->de Dados Items Sistemas Correr, se ela ainda não existir
# ============================================================================================
def criar_tabela_dados_items_sistemas_correr():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dados_items_sistemas_correr (
            id INT AUTO_INCREMENT PRIMARY KEY,
            num_orc VARCHAR(50),
            ver_orc VARCHAR(10),
            id_sc VARCHAR(50),
            material TEXT,
            descricao TEXT,
            ref_le TEXT,
            descricao_no_orcamento TEXT,
            ptab REAL,
            pliq REAL,
            desc1_plus REAL,
            desc2_minus REAL,
            und TEXT,
            desp REAL,
            corres_orla_0_4 TEXT,
            corres_orla_1_0 TEXT,
            tipo TEXT,
            familia TEXT,
            comp_mp REAL,
            larg_mp REAL,
            esp_mp REAL,
            UNIQUE(num_orc, ver_orc, id_sc)
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

# =============================================================================================
# Função para criar a tabela na Base Dados ->de Dados Items Acabamentos, se ela ainda não existir
# ============================================================================================
def criar_tabela_dados_items_acabamentos():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dados_items_acabamentos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            num_orc VARCHAR(50),
            ver_orc VARCHAR(10),
            id_acb VARCHAR(50),
            material TEXT,
            descricao TEXT,
            ref_le TEXT,
            descricao_no_orcamento TEXT,
            ptab REAL,
            pliq REAL,
            desc1_plus REAL,
            desc2_minus REAL,
            und TEXT,
            desp REAL,
            corres_orla_0_4 TEXT,
            corres_orla_1_0 TEXT,
            tipo TEXT,
            familia TEXT,
            comp_mp REAL,
            larg_mp REAL,
            esp_mp REAL,
            UNIQUE(num_orc, ver_orc, id_acb)
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

# Função genérica para guardar os dados dos itens do orçamento.
def guardar_dados_item_orcamento(tab_widget, num_orc, ver_orc, id_item, mapping, tabela_db):
    """
    Parâmetros:
      tab_widget: QTableWidget (por exemplo, Tab_Ferragens_11)
      num_orc: número do orçamento (string)
      ver_orc: versão do orçamento (string)
      id_item: identificador do item (ex: id_mat, id_fer, id_sc ou id_acb)
      mapping: dicionário que mapeia os nomes dos campos para os índices da tabela
      tabela_db: nome da tabela no banco de dados (string)
    """
    num_rows = tab_widget.rowCount()
    # Ordem dos campos para inserção no DB
    keys_order = ['num_orc', 'ver_orc', 'id_item', 'linha', 'material', 'descricao', 'ref_le',
                  'descricao_no_orcamento', 'ptab', 'pliq', 'desc1_plus', 'desc2_minus',
                  'und', 'desp', 'corres_orla_0_4', 'corres_orla_1_0', 'tipo', 'familia',
                  'comp_mp', 'larg_mp', 'esp_mp']
    # Conjuntos para conversão de valores formatados
    campos_moeda = {"ptab", "pliq", "comp_mp", "larg_mp", "esp_mp"}
    campos_percentual = {"desc1_plus", "desc2_minus", "desp"}
    dados = []
    for row in range(num_rows):
        row_data = []
        # Campos fixos provenientes dos line edits
        row_data.append(num_orc)
        row_data.append(ver_orc)
        row_data.append(id_item)
        row_data.append(str(row))
        for key in ['material', 'descricao', 'ref_le', 'descricao_no_orcamento',
                    'ptab', 'pliq', 'desc1_plus', 'desc2_minus', 'und', 'desp',
                    'corres_orla_0_4', 'corres_orla_1_0', 'tipo', 'familia',
                    'comp_mp', 'larg_mp', 'esp_mp']:
            col_idx = mapping.get(key, None)
            valor = ""
            if col_idx is not None:
                cell = tab_widget.item(row, col_idx)
                valor = cell.text() if cell is not None else ""
            if key in campos_moeda:
                try:
                    valor = converter_texto_para_valor(valor, "moeda")
                except:
                    valor = 0.0
            elif key in campos_percentual:
                try:
                    valor = converter_texto_para_valor(valor, "percentual")
                except:
                    valor = 0.0
            row_data.append(valor)
        dados.append(tuple(row_data))
    try:
        conn = get_connection()
        cur = conn.cursor()
        # Verifica se já existem registros para (num_orc, ver_orc, id_item)
        query_check = f"SELECT COUNT(*) FROM {tabela_db} WHERE num_orc=%s AND ver_orc=%s AND id_item=%s"
        cur.execute(query_check, (num_orc, ver_orc, id_item))
        count = cur.fetchone()[0]
        if count > 0:
            resposta = QMessageBox.question(
                None,
                "Dados já existentes",
                "Já existem dados para este item. Deseja substituí-los?",
                QMessageBox.Yes | QMessageBox.No
            )
            if resposta == QMessageBox.No:
                conn.close()
                return
            else:
                query_delete = f"DELETE FROM {tabela_db} WHERE num_orc=%s AND ver_orc=%s AND id_item=%s"
                cur.execute(query_delete, (num_orc, ver_orc, id_item))
                conn.commit()
        col_names = ['num_orc', 'ver_orc', 'id_item', 'linha', 'material', 'descricao', 'ref_le',
                     'descricao_no_orcamento', 'ptab', 'pliq', 'desc1_plus', 'desc2_minus',
                     'und', 'desp', 'corres_orla_0_4', 'corres_orla_1_0', 'tipo', 'familia',
                     'comp_mp', 'larg_mp', 'esp_mp']
        placeholders = ", ".join(["%s"] * len(col_names))
        query_insert = f"INSERT INTO {tabela_db} ({', '.join(col_names)}) VALUES ({placeholders})"
        for row_data in dados:
            cur.execute(query_insert, row_data)
        conn.commit()
        QMessageBox.information(None, "Sucesso", "Dados do item salvos com sucesso!")
    except Exception as e:
        QMessageBox.critical(None, "Erro", f"Erro ao salvar os dados: {e}")
    finally:
        cur.close()
        conn.close()