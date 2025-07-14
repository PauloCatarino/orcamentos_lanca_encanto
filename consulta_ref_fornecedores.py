# -*- coding: utf-8 -*-

# consulta_ref_fornecedores.py
# Este módulo implementa uma interface gráfica para pesquisa de referências

import sys
import os
import math
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QCheckBox, QMessageBox, QDialog
)
from PyQt5.QtCore import Qt

# 1. Função para obter caminho do ficheiro Excel a partir do configuracoes.py
def obter_caminho_excel():
    """
    Obtém o caminho completo do ficheiro Excel a partir da tabela de configurações (MySQL).
    Assume que caminho_base_dados já contém o caminho correto da pasta BASE (não a subpasta).
    """
    try:
        import mysql.connector
        from db_connection import obter_cursor

        NOME_EXCEL = "Placas_Referencias_COMPLETO.xlsx"
        SUBPASTA_EXCEL = "TABELAS_MAT_EGGER_SONAE"

        # Busca caminho_base_dados ao MySQL
        caminho_base = None
        with obter_cursor() as cursor:
            cursor.execute("SELECT caminho_base_dados FROM configuracoes LIMIT 1")
            resultado = cursor.fetchone()
            if resultado and resultado[0]:
                caminho_base = resultado[0].strip()
            else:
                raise FileNotFoundError("Não existe valor para caminho_base_dados nas configurações.")

        caminho_base = caminho_base.rstrip("\\/")
        # Adiciona a subpasta e o ficheiro
        caminho_excel = os.path.join(caminho_base, SUBPASTA_EXCEL, NOME_EXCEL)
        # print("DEBUG: Procurando ficheiro Excel em:", caminho_excel) #Faz um print do caminho do ficheiro Excel "Placas_Referencias_COMPLETO.xlsx" QUE ESTÁ DENTRO A SUBPAPSTA "TABELAS_MAT_EGGER_SONAE"

        if not os.path.exists(caminho_excel):
            raise FileNotFoundError(f"Ficheiro Excel não encontrado em: {caminho_excel}")

        return caminho_excel
    except Exception as e:
        raise FileNotFoundError(f"Erro ao obter caminho do ficheiro Excel: {e}")

# 2. Função para ler todos os separadores do Excel (header=3 -> linha 4 é cabeçalho)
def ler_excel_todas_sheets(ficheiro_excel):
    sheets = pd.read_excel(ficheiro_excel, sheet_name=None, header=3)
    return sheets

# 3. Função de pesquisa multitexto
def pesquisar_multitexto(dfs, termos, ignorar_maiusculas=True):
    resultados = []
    termos_procura = [t.strip() for t in termos.replace('%', ' ').split()]
    for separador, df in dfs.items():
        for idx, row in df.iterrows():
            texto_linha = ' '.join([str(x) for x in row.values])
            if ignorar_maiusculas:
                texto_linha = texto_linha.lower()
                termos_procura_lower = [t.lower() for t in termos_procura]
                match = all(t in texto_linha for t in termos_procura_lower)
            else:
                match = all(t in texto_linha for t in termos_procura)
            if match:
                # Constrói resultado mostrando sempre separador
                resultado = row.to_dict()
                resultado['SEPARADOR'] = separador
                resultados.append(resultado)
    if resultados:
        return pd.DataFrame(resultados)
    else:
        return pd.DataFrame()  # vazio

# 4. Classe principal da interface
class JanelaPesquisa(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pesquisa Multitexto de Referências")
        self.resize(1900, 400) # Ajusta tamanho do menu 'Pesquisa Multitexto de referencias' conforme necessário
        self.layout = QVBoxLayout(self)

        # Campo de pesquisa
        layout_pesquisa = QHBoxLayout()
        self.edit_pesquisa = QLineEdit()
        self.edit_pesquisa.setPlaceholderText("Ex: EGGER%BRANCO%ST19 ou peça")
        self.btn_pesquisar = QPushButton("Pesquisar")
        self.chk_ignore_case = QCheckBox("Ignorar maiúsculas/minúsculas")
        self.chk_ignore_case.setChecked(True)
        layout_pesquisa.addWidget(QLabel("Pesquisar:"))
        layout_pesquisa.addWidget(self.edit_pesquisa)
        layout_pesquisa.addWidget(self.chk_ignore_case)
        layout_pesquisa.addWidget(self.btn_pesquisar)

        # Info resultados
        self.lbl_resultados = QLabel("")
        self.lbl_resultados.setStyleSheet("color: gray")

        # Tabela resultados
        self.tabela = QTableWidget()
        self.tabela.setColumnCount(0)
        self.tabela.setRowCount(0)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setSelectionMode(QTableWidget.SingleSelection)

        # Layout principal
        self.layout.addLayout(layout_pesquisa)
        self.layout.addWidget(self.lbl_resultados)
        self.layout.addWidget(self.tabela)

        # Ligações
        self.btn_pesquisar.clicked.connect(self.fazer_pesquisa)

        # Carrega Excel só uma vez para performance
        try:
            caminho_excel = obter_caminho_excel()
            self.dfs = ler_excel_todas_sheets(caminho_excel)
            self.lbl_resultados.setText(f"Excel carregado: {os.path.basename(caminho_excel)} ({len(self.dfs)} separadores)")
        except Exception as e:
            QMessageBox.critical(self, "Erro ao abrir Excel", str(e))
            self.dfs = {}

    def fazer_pesquisa(self):
        termos = self.edit_pesquisa.text().strip()
        if not termos:
            QMessageBox.warning(self, "Atenção", "Introduz um termo de pesquisa.")
            return
        ignorar_case = self.chk_ignore_case.isChecked()
        df_result = pesquisar_multitexto(self.dfs, termos, ignorar_case)
        if not df_result.empty:
            # Mostra os resultados na tabela
            self.mostrar_resultados(df_result)
            n_resultados = len(df_result)
            fornecedores = df_result["SEPARADOR"].unique()
            self.lbl_resultados.setText(f"Encontrados {n_resultados} resultados em {len(fornecedores)} fornecedores.")
        else:
            self.tabela.clear()
            self.tabela.setRowCount(0)
            self.lbl_resultados.setText("Nenhum resultado encontrado.")

    def mostrar_resultados(self, df):
        # Define colunas a mostrar (ajusta conforme dados reais)
        colunas_base = list(df.columns)
        # Garante que 'SEPARADOR' aparece nas primeiras colunas
        if "SEPARADOR" in colunas_base:
            colunas_base.remove("SEPARADOR")
            colunas = ["SEPARADOR"] + colunas_base
        else:
            colunas = colunas_base
        self.tabela.setColumnCount(len(colunas))
        self.tabela.setHorizontalHeaderLabels(colunas)
        self.tabela.setRowCount(len(df))
        # Antes do método/módulo, define quais são as colunas de preço pelo nome:
        COLUNAS_PRECO = ["PRECO_TABELA", "PLIQ", "PREÇO", "PREÇO (€)", "PRECO"]  # Adapta consoante nomes do teu Excel

        for i, (_, row) in enumerate(df.iterrows()):
            for j, col in enumerate(colunas):
                # Obtem valor real
                valor = row[col] if col in row else ""
                # Tratar 'nan' e None
                if pd.isna(valor) or str(valor).lower() == "nan":
                    texto = ""
                # Formatar preços (float) para xx.xx€
                elif any(preco_nome in col.upper() for preco_nome in ["PRECO", "PREÇO", "PLIQ"]):
                    try:
                        v = float(valor)
                        texto = f"{v:.2f}€"
                    except:
                        texto = str(valor)
                else:
                    texto = str(valor)
                self.tabela.setItem(i, j, QTableWidgetItem(texto))
        self.tabela.resizeColumnsToContents()

# 5. Executa a aplicação
if __name__ == "__main__":
    app = QApplication(sys.argv)
    janela = JanelaPesquisa()
    janela.show()
    sys.exit(app.exec_())
