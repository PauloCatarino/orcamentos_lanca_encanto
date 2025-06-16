# gerador_relatorios.py
# -*- coding: utf-8 -*-
"""Geração de relatórios do orçamento em PDF e Excel.

Este módulo contém funções para exportar o resumo do orçamento para
ficheiros PDF e Excel. Utiliza a biblioteca ``fpdf2`` para o PDF e
pandas para o Excel.
"""

from PyQt5.QtWidgets import QTableWidgetItem
from datetime import datetime
import os
import sys
import subprocess
import re
from typing import Tuple, List

import pandas as pd
from fpdf import FPDF


class OrcamentoPDF(FPDF):
    """Classe auxiliar para configurar cabeçalho e rodapé do PDF."""

    def __init__(self, num_orc: str, ver_orc: str, data_str: str, cliente_info: List[str]):
        super().__init__(orientation="P", unit="mm", format="A4")
        # Se disponível, ativa a codificação cp1252 para permitir caracteres
        # como o símbolo do Euro. Em versões antigas do ``fpdf`` este atributo
        # não existe e a biblioteca limita-se ao latin-1.
        if hasattr(self, "core_fonts_encoding"):
            self.core_fonts_encoding = "cp1252"
        self.num_orc = num_orc
        self.ver_orc = ver_orc
        self.data_str = data_str
        self.cliente_info = cliente_info
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        """Desenha o cabeçalho com o logótipo e dados do cliente."""
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            self.image(logo_path, x=170, y=8, w=30)
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 10, "Lança Encanto, Lda", ln=1, align="R")
        self.set_font("Helvetica", size=9)
        for linha in self.cliente_info:
            self.cell(0, 5, linha, ln=1)
        self.ln(2)

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


def _obter_texto(item: "QTableWidgetItem") -> str:
    """Return the text of a cell, converting None to an empty string."""

    text = item.text() if item else ""
    text = text.strip()
    # FPDF 1.x only suporta Latin-1. Para evitar erros de codificação, o símbolo
    # do Euro é substituído por "EUR" quando não for possível usar cp1252.
    return text.replace("€", "EUR")


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
    num_orc = ui.lineEdit_num_orcamento_2.text().strip()
    ver_orc = ui.lineEdit_versao.text().strip()
    nome_cliente = ui.lineEdit_nome_cliente_2.text().strip()
    ano = ui.lineEdit_ano.text().strip()
    pasta_base = ui.lineEdit_orcamentos.text().strip()

    def _gerar_nome_pasta_orcamento(num_orcamento: str, nome_cli: str) -> str:
        nome_cli_seguro = re.sub(r'[\\/*?:"<>|]+', '', nome_cli.strip().upper().replace(' ', '_'))
        return f"{num_orcamento}_{nome_cli_seguro}"

    nome_pasta = _gerar_nome_pasta_orcamento(num_orc, nome_cliente)
    pasta_orc = os.path.join(pasta_base, ano, nome_pasta)
    if ver_orc != "00":
        pasta_orc = os.path.join(pasta_orc, ver_orc)
    os.makedirs(pasta_orc, exist_ok=True)

    tabela = ui.tableWidget_artigos
    headers = [
        "Item",
        "Codigo",
        "Descricao",
        "Altura",
        "Largura",
        "Profundidade",
        "Und",
        "QT",
        "Preco_Unitario",
        "Preco_Total",
    ]
    col_map = dict(zip(headers, range(10)))
    dados = []
    for row in range(tabela.rowCount()):
        reg = {}
        for h, idx in col_map.items():
            reg[h] = _obter_texto(tabela.item(row, idx))
        dados.append(reg)

    df = pd.DataFrame(dados, columns=headers)

    def _to_float(valor):
        try:
            return float(str(valor).replace(",", "."))
        except ValueError:
            return 0.0

    subtotal = df["Preco_Total"].apply(_to_float).sum()
    total_qt = df["QT"].apply(_to_float).sum()
    iva = subtotal * 0.23
    total = subtotal + iva

    df_totais = pd.DataFrame([
        {"Item": "Total QT", "QT": total_qt},
        {"Item": "Subtotal", "Preco_Total": subtotal},
        {"Item": "IVA (23%)", "Preco_Total": iva},
        {"Item": "Total", "Preco_Total": total},
    ])

    caminho_excel = os.path.join(pasta_orc, f"Relatorio_{num_orc}_{ver_orc}.xlsx")
    pd.concat([df, df_totais], ignore_index=True).to_excel(caminho_excel, index=False)

    cliente_info = [
        ui.lineEdit_nome_cliente.text().strip(),
        ui.lineEdit_morada_cliente.text().strip(),
        ui.lineEdit_email_cliente.text().strip(),
        ui.lineEdit_num_cliente_phc.text().strip(),
        ui.lineEdit_telefone.text().strip(),
        ui.lineEdit_telemovel.text().strip(),
    ]

    pdf = OrcamentoPDF(
        num_orc,
        ver_orc,
        datetime.now().strftime("%d/%m/%Y"),
        cliente_info,
    )
    pdf.alias_nb_pages()
    # Se a biblioteca suportar, define a codificação cp1252 para que o símbolo
    # do Euro seja aceite. Caso contrário, os textos já foram limpos em
    # ``_obter_texto``.
    if hasattr(pdf, "core_fonts_encoding"):
        pdf.core_fonts_encoding = "cp1252"
    pdf.add_page()

    # Cabeçalho da tabela
    pdf.set_font("Helvetica", "B", 8)
    col_widths = [10, 25, 70, 18, 18, 22, 12, 12, 22, 22]
    for header, width in zip(headers, col_widths):
        pdf.cell(width, 8, header, 1, 0, "C")
    pdf.ln()

    line_height = 5
    for _, row in df.iterrows():
        desc_lines = str(row["Descricao"]).splitlines() or [""]
        row_height = line_height * max(1, len(desc_lines))

        pdf.set_font("Helvetica", size=8)
        pdf.cell(col_widths[0], row_height, str(row["Item"]), 1)
        pdf.cell(col_widths[1], row_height, str(row["Codigo"]), 1)

        x_desc = pdf.get_x()
        y_desc = pdf.get_y()
        pdf.set_font("Helvetica", "B", 9)
        pdf.multi_cell(col_widths[2], line_height, desc_lines[0], border="LTR")
        for line in desc_lines[1:-1]:
            pdf.set_font("Helvetica", "I", 8)
            pdf.multi_cell(col_widths[2], line_height, line.lstrip(), border="LR")
        if len(desc_lines) > 1:
            pdf.set_font("Helvetica", "I", 8)
            pdf.multi_cell(col_widths[2], line_height, desc_lines[-1].lstrip(), border="LBR")
        else:
            pdf.set_y(y_desc)
            pdf.set_x(x_desc)
            pdf.set_font("Helvetica", "B", 9)
            pdf.multi_cell(col_widths[2], row_height, desc_lines[0], border=1)

        pdf.set_xy(x_desc + col_widths[2], y_desc)
        pdf.set_font("Helvetica", size=8)
        pdf.cell(col_widths[3], row_height, str(row["Altura"]), 1, 0, "R")
        pdf.cell(col_widths[4], row_height, str(row["Largura"]), 1, 0, "R")
        pdf.cell(col_widths[5], row_height, str(row["Profundidade"]), 1, 0, "R")
        pdf.cell(col_widths[6], row_height, str(row["Und"]), 1, 0, "C")
        pdf.cell(col_widths[7], row_height, str(row["QT"]), 1, 0, "R")
        pdf.cell(col_widths[8], row_height, str(row["Preco_Unitario"]), 1, 0, "R")
        pdf.cell(col_widths[9], row_height, str(row["Preco_Total"]), 1, 0, "R")
        pdf.ln(row_height)

    # Linha com total de quantidades
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(sum(col_widths[:7]), 8, "Total QT", 1)
    pdf.cell(col_widths[7], 8, f"{total_qt}", 1, 0, "R")
    pdf.cell(col_widths[8], 8, "", 1)
    pdf.cell(col_widths[9], 8, "", 1, ln=1)

    pdf.ln(5)
    label_width = sum(col_widths[:-1])
    pdf.cell(label_width, 8, "Subtotal", 1)
    pdf.cell(col_widths[-1], 8, f"{subtotal:.2f}", 1, ln=1, align="R")
    pdf.cell(label_width, 8, "IVA (23%)", 1)
    pdf.cell(col_widths[-1], 8, f"{iva:.2f}", 1, ln=1, align="R")
    pdf.cell(label_width, 8, "Total", 1)
    pdf.cell(col_widths[-1], 8, f"{total:.2f}", 1, ln=1, align="R")

    caminho_pdf = os.path.join(pasta_orc, f"Relatorio_{num_orc}_{ver_orc}.pdf")
    print(f"[INFO] O PDF será guardado em: {caminho_pdf}")
    print(f"[INFO] O Excel será guardado em: {caminho_excel}")
    pdf.output(caminho_pdf)

    print(f"[INFO] PDF gerado em: {caminho_pdf}")
    print(f"[INFO] Excel gerado em: {caminho_excel}")

    # Abre o PDF automaticamente para visualização, se possível
    try:
        if os.name == "nt":
            os.startfile(caminho_pdf)
        elif sys.platform == "darwin":
            subprocess.run(["open", caminho_pdf], check=False)
        else:
            subprocess.run(["xdg-open", caminho_pdf], check=False)
    except Exception as exc:
        print(f"[AVISO] Não foi possível abrir o PDF automaticamente: {exc}")

    return caminho_pdf, caminho_excel