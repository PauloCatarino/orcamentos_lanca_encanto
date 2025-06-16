# gerador_relatorios.py
# -*- coding: utf-8 -*-
"""Geração de relatórios do orçamento em PDF e Excel.

Este módulo contém funções para exportar o resumo do orçamento para
ficheiros PDF e Excel. Utiliza a biblioteca ``fpdf2`` para o PDF e
pandas para o Excel.
"""

from datetime import datetime
import os
from typing import Tuple

import pandas as pd
from fpdf import FPDF


class OrcamentoPDF(FPDF):
    """Classe auxiliar para configurar cabeçalho e rodapé do PDF."""

    def __init__(self, num_orc: str, ver_orc: str, data_str: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        # Permite usar caracteres como "€" com as fontes core
        # cp1252 inclui o símbolo do Euro e evita o erro de codificação
        self.core_fonts_encoding = "cp1252"
        self.num_orc = num_orc
        self.ver_orc = ver_orc
        self.data_str = data_str

    def header(self):
        """Desenha o cabeçalho com o logótipo e informações da empresa."""
        # Logótipo no canto superior direito (caso exista)
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            self.image(logo_path, x=170, y=8, w=30)
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, "Lança Encanto, Lda", ln=1, align="R")
        self.ln(5)

    def footer(self):
        """Desenha o rodapé com data, número do orçamento e paginação."""
        self.set_y(-15)
        self.set_font("Helvetica", size=8)
        # Data no canto esquerdo
        self.cell(60, 10, self.data_str, 0, 0, "L")
        # Número e versão no centro
        self.cell(60, 10, f"{self.num_orc}_{self.ver_orc}", 0, 0, "C")
        # Paginação no canto direito
        self.cell(0, 10, f"{self.page_no()}/{{nb}}", 0, 0, "R")


def _obter_texto(item):
    return item.text() if item else ""


def gerar_relatorio_orcamento(ui) -> Tuple[str, str]:
    """Gera ficheiros PDF e Excel com o resumo do orçamento.

    Parâmetros
    ----------
    ui : :class:`Ui_MainWindow`
        Instância da interface principal com os dados preenchidos.

    Retorna
    -------
    tuple
        Caminhos completos do ficheiro PDF e do ficheiro Excel gerados.
    """
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    ver_orc = ui.lineEdit_versao_orcamento.text().strip()
    nome_cliente = ui.lineEdit_nome_cliente.text().strip()
    pasta_base = ui.lineEdit_orcamentos.text().strip()

    pasta_orc = os.path.join(pasta_base, f"{num_orc}_{ver_orc}")
    os.makedirs(pasta_orc, exist_ok=True)

    tabela = ui.tableWidget_artigos
    dados = []
    for row in range(tabela.rowCount()):
        dados.append({
            "Codigo": _obter_texto(tabela.item(row, 1)),
            "Descricao": _obter_texto(tabela.item(row, 2)),
            "Quantidade": _obter_texto(tabela.item(row, 7)),
            "Preco_Unitario": _obter_texto(tabela.item(row, 8)),
            "Preco_Total": _obter_texto(tabela.item(row, 9)),
        })

    df = pd.DataFrame(dados)

    def _to_float(valor):
        try:
            return float(str(valor).replace(",", "."))
        except ValueError:
            return 0.0

    subtotal = df["Preco_Total"].apply(_to_float).sum()
    total_qt = df["Quantidade"].apply(_to_float).sum()
    iva = subtotal * 0.23
    total = subtotal + iva

    caminho_excel = os.path.join(pasta_orc, f"Relatorio_{num_orc}_{ver_orc}.xlsx")
    df.to_excel(caminho_excel, index=False)

    pdf = OrcamentoPDF(num_orc, ver_orc, datetime.now().strftime("%d/%m/%Y"))
    pdf.alias_nb_pages()
    # Utiliza codificação cp1252 para permitir o símbolo do Euro
    pdf.core_fonts_encoding = "cp1252"
    pdf.add_page()

    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, f"Cliente: {nome_cliente}", ln=1)
    pdf.cell(0, 10, f"Orçamento Nº {num_orc} - Versão {ver_orc}", ln=1)
    pdf.ln(5)

    # Cabeçalho da tabela
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(30, 8, "Código", 1)
    pdf.cell(90, 8, "Descrição", 1)
    pdf.cell(20, 8, "Qt", 1, align="R")
    pdf.cell(25, 8, "P.Unit", 1, align="R")
    pdf.cell(25, 8, "Total", 1, ln=1, align="R")

    pdf.set_font("Helvetica", size=10)
    for _, row in df.iterrows():
        pdf.cell(30, 8, str(row["Codigo"]), 1)
        pdf.cell(90, 8, str(row["Descricao"]), 1)
        pdf.cell(20, 8, str(row["Quantidade"]), 1, align="R")
        pdf.cell(25, 8, str(row["Preco_Unitario"]), 1, align="R")
        pdf.cell(25, 8, str(row["Preco_Total"]), 1, ln=1, align="R")

    pdf.ln(5)
    pdf.cell(140, 8, "Subtotal", 1)
    pdf.cell(25, 8, f"{subtotal:.2f}", 1, ln=1, align="R")
    pdf.cell(140, 8, "IVA (23%)", 1)
    pdf.cell(25, 8, f"{iva:.2f}", 1, ln=1, align="R")
    pdf.cell(140, 8, "Total", 1)
    pdf.cell(25, 8, f"{total:.2f}", 1, ln=1, align="R")

    caminho_pdf = os.path.join(pasta_orc, f"Relatorio_{num_orc}_{ver_orc}.pdf")
    pdf.output(caminho_pdf)

    return caminho_pdf, caminho_excel