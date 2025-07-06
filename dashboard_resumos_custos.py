# dashboard_resumos_custos.py
"""
Descrição:
Classe personalizada para desenhar o rodapé em cada página do PDF exportado,
incluindo data, número do orçamento, versão e numeração das páginas.
"""
"""
Descrição:
Converte um DataFrame do pandas para um QTableWidget PyQt5,
mantendo o formato, o alinhamento e ajustando visualmente a tabela.
"""
# Função: ajustar_tabela_resumo_placas
"""
Descrição:
Ajusta larguras de colunas e aplica rotação ao cabeçalho da tabela de placas,
para melhor visualização dos dados no QTableWidget.
"""
"""
Descrição:
Cria um gráfico de barras agrupadas para comparar custos teóricos
e reais (com desperdício) das placas usadas no orçamento.
Legendas longas são ajustadas para não ficarem cortadas.
"""
"""
Descrição:
Cria um gráfico de barras simples para mostrar o consumo total
de cada tipo de orla (metros lineares), com legendas otimizadas.
"""
"""
Descrição:
Gráfico genérico de barras simples para categorias e valores.
Serve para custos de ferragens, máquinas, etc. Otimiza as labels.
"""
"""
Descrição:
Widget principal do dashboard PyQt5. Organiza e exibe as tabelas
e gráficos para cada grupo de custos do orçamento. Permite exportar
tudo para PDF, com layout visual e rodapé.
"""
# Função: mostrar_dashboard_resumos
"""
Descrição:
Função que recebe o widget pai e o caminho do Excel, limpa o conteúdo atual
do widget e insere o dashboard do orçamento (PyQt5) pronto a ser usado.
"""
# Mostra os resumos de custos do Excel de cada orçamento como dashboard visual no PyQt5

#=============================================================================
#Resumo do Script: dashboard_resumos_custos.py
#=============================================================================
#Este módulo implementa um dashboard visual em PyQt5 para exibir resumos de custos de orçamentos a partir de ficheiros Excel. Permite:
#    - Ler e processar folhas de resumos de custos (placas, orlas, ferragens, máquinas, margens).
#    - Apresentar tabelas e gráficos interativos para cada grupo de custos.
#    - Exportar o dashboard completo (tabelas + gráficos) para PDF, com rodapé personalizado e paginação.
#    - Integrar facilmente numa aplicação PyQt5.
#Dependências: pandas, numpy, matplotlib, reportlab, PyQt5
#=============================================================================

# dashboard_resumos_custos.py

# dashboard_resumos_custos.py
"""
Dashboard de Resumos de Custos em PyQt5
- Mostra tabelas e gráficos de custos do orçamento.
- Exporta para PDF com layout limpo e colunas otimizadas.
- Tooltips informativos nos cabeçalhos.
"""

# dashboard_resumos_custos.py
"""
Dashboard visual de resumos de custos (PyQt5).
- Zero espaço desperdiçado.
- Tabelas e gráficos sempre otimizados e visíveis.
- Margens/Custos sempre em baixo, compactos.
- PDF exporta com todas colunas (incluindo N/Stock) visíveis.
"""

# dashboard_resumos_custos.py

"""
Dashboard visual e compacto de resumos de custos (PyQt5).
- Usa todo o espaço disponível.
- Abrevia os nomes das colunas e mostra tooltips.
- Margens/Custos sempre em baixo, bloco pequeno.
- Exporta para PDF com todas as colunas (incluindo N/Stock).
- Tabelas ajustadas à esquerda para máxima área útil.
"""

import os
import io
import pandas as pd
import numpy as np
from datetime import datetime
import textwrap

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QSizePolicy, QTableWidgetItem,
    QGridLayout, QGroupBox, QPushButton, QHeaderView, QFileDialog
)
from PyQt5.QtCore import Qt

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfgen import canvas

# ========= ABREVIAÇÕES E TOOLTIPS =========
ABREV_COLUNAS = {
    "ref_le": "Ref.",
    "descricao_no_orcamento": "Descrição",
    "pliq": "P.Liq",
    "und": "Und",
    "desp": "Desp.",
    "comp_mp": "Comp.",
    "larg_mp": "Larg.",
    "esp_mp": "Esp.",
    "qt_placas_utilizadas": "Qt.Placa",
    "area_placa": "Área",
    "m2_consumidos": "m² Usad.",
    "custo_mp_total": "C.MP Tot",
    "custo_placas_utilizadas": "C.Placa Usad.",
    "nao_stock": "N/Stock",
    "qt_total": "Qt.",
    "spp_ml_total": "ML Sup.",
    "custo_mp_und": "C.MP Und",
    "ref_orla": "Ref.",
    "espessura_orla": "Esp.",
    "largura_orla": "Larg.",
    "ml_total": "ML Tot.",
    "custo_total": "Custo Tot",
    "Operação": "Op.",
    "Custo Total (€)": "C. Tot.",
    "ML Corte": "ML Corte",
    "ML Orlado": "ML Orl.",
    "Nº Peças": "Nº Peças",
    "Tipo": "Tipo",
    "Percentagem (%)": "%",
    "Valor (€)": "€"
}
TOOLTIPS_COLUNAS = {
    "Ref.": "Referência do material/componente",
    "Descrição": "Descrição detalhada",
    "P.Liq": "Peso líquido",
    "Und": "Unidade",
    "Desp.": "Desperdício",
    "Comp.": "Comprimento",
    "Larg.": "Largura",
    "Esp.": "Espessura",
    "Qt.Placa": "Quantidade de placas",
    "Área": "Área da placa (m²)",
    "m² Usad.": "Metros quadrados consumidos",
    "C.MP Tot": "Custo total da matéria-prima",
    "C.Placa Usad.": "Custo das placas usadas",
    "N/Stock": "Não existe em stock",
    "Qt.": "Quantidade",
    "ML Sup.": "Metros lineares de suporte",
    "C.MP Und": "Custo MP unidade",
    "Custo Tot": "Custo total",
    "Op.": "Operação/máquina",
    "C. Tot.": "Custo total",
    "ML Corte": "Metros lineares cortados",
    "ML Orl.": "Metros lineares orlados",
    "Nº Peças": "Número de peças",
    "%": "Percentagem",
    "€": "Valor em euros"
}

def abreviar_colunas(df):
    """Retorna dataframe com colunas abreviadas + lista de nomes."""
    novas_cols = [ABREV_COLUNAS.get(c, c) for c in df.columns]
    df_abrev = df.copy()
    df_abrev.columns = novas_cols
    return df_abrev, novas_cols

# ========= RODAPÉ PDF =========
class FooterCanvas(canvas.Canvas):
    def __init__(self, num_orc_ver, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.num_orc_ver = num_orc_ver
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_footer(page_count)
            super().showPage()
        super().save()

    def draw_footer(self, page_count):
        self.saveState()
        self.setFont('Helvetica', 9)
        data_hoje = datetime.now().strftime("%d/%m/%Y")
        page_num = self.getPageNumber()
        self.drawString(25, 20, data_hoje)
        self.drawCentredString(landscape(A4)[0] / 2, 20, self.num_orc_ver)
        self.drawRightString(landscape(A4)[0] - 28, 20, f"Página {page_num} / {page_count}")
        self.restoreState()

# ========= LARGURAS PDF (colunas e margem reduzida) =========
def colwidths_pdf(cols_abrev):
    """Largura apropriada para cada coluna, incluindo N/Stock."""
    larguras = []
    for c in cols_abrev:
        if c in ["Descrição", "Op."]:
            larguras.append(198)
        elif c in ["Ref."]:
            larguras.append(56)
        elif c in ["N/Stock"]:
            larguras.append(47)
        elif "Custo" in c or "Valor" in c or "C. Tot." in c:
            larguras.append(63)
        elif c in ["Área", "m² Usad."]:
            larguras.append(49)
        else:
            larguras.append(44)
    return larguras

# ========= DataFrame → QTableWidget (com tooltips) =========
def dataframe_para_qtablewidget(df: pd.DataFrame) -> QTableWidget:
    if df is None or df.empty:
        table = QTableWidget(1, 1)
        table.setItem(0, 0, QTableWidgetItem("Sem dados para exibir."))
        return table
    df_abrev, colunas_abreviadas = abreviar_colunas(df)
    table = QTableWidget(len(df_abrev), len(colunas_abreviadas))
    table.setHorizontalHeaderLabels(colunas_abreviadas)
    header = table.horizontalHeader()
    for i, col_abrev in enumerate(colunas_abreviadas):
        item = QTableWidgetItem(col_abrev)
        tooltip = TOOLTIPS_COLUNAS.get(col_abrev, col_abrev)
        item.setToolTip(tooltip)
        table.setHorizontalHeaderItem(i, item)
        header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
    for i in range(len(df_abrev)):
        for j in range(len(colunas_abreviadas)):
            valor = df_abrev.iat[i, j]
            valor_str = "" if pd.isna(valor) else f"{valor:,.2f}" if isinstance(valor, (int, float)) else str(valor)
            item = QTableWidgetItem(valor_str)
            if isinstance(valor, (int, float)):
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(i, j, item)
    table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    table.verticalHeader().setVisible(False)
    table.setAlternatingRowColors(True)
    table.horizontalHeader().setFixedHeight(30)
    table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    return table

# ========= GRÁFICOS (Expanding) =========
def criar_grafico_placas(df):
    if df is None or df.empty:
        return None
    df_plot = df[['descricao_no_orcamento', 'custo_mp_total', 'custo_placas_utilizadas']].copy()
    for col in ['custo_mp_total', 'custo_placas_utilizadas']:
        df_plot[col] = pd.to_numeric(df_plot[col], errors='coerce').fillna(0)
    colors_barras = ['#F44336' if real > teor else '#4CAF50'
                     for real, teor in zip(df_plot['custo_placas_utilizadas'], df_plot['custo_mp_total'])]
    x = np.arange(len(df_plot['descricao_no_orcamento']))
    width = 0.35
    fig, ax = plt.subplots(figsize=(9.2, 5.7), dpi=100)
    ax.bar(x - width/2, df_plot['custo_mp_total'], width, label='Custo Teórico', color='skyblue', edgecolor='black', zorder=3)
    ax.bar(x + width/2, df_plot['custo_placas_utilizadas'], width, label='Custo Real', color=colors_barras, edgecolor='black', zorder=3)
    ax.set_ylabel('Custo (€)', fontsize=10)
    ax.set_title('Comparativo de Custos por Placa', fontweight='bold', fontsize=12)
    ax.set_xticks(x)
    wrapped_labels = [textwrap.fill(l, 28) for l in df_plot['descricao_no_orcamento'].astype(str)]
    ax.set_xticklabels(wrapped_labels, rotation=30, ha='right', fontsize=8)
    fig.subplots_adjust(bottom=0.33)
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.6, zorder=0)
    fig.tight_layout()
    return fig

def criar_grafico_orlas(df):
    if df is None or df.empty:
        return None
    df_plot = df.copy()
    df_plot['label'] = df_plot['ref_orla'].astype(str) + ' (' + df_plot['espessura_orla'].astype(str) + ', ' + df_plot['largura_orla'].astype(int).astype(str) + 'mm)'
    fig, ax = plt.subplots(figsize=(9.2, 5.7), dpi=100)
    bars = ax.bar(df_plot['label'], pd.to_numeric(df_plot['ml_total'], errors='coerce'), color='orange', edgecolor='black', zorder=3)
    ax.set_ylabel('Metros Lineares (ml)', fontsize=10)
    ax.set_title('Consumo de Orlas (ml)', fontweight='bold', fontsize=12)
    wrapped_labels = [textwrap.fill(l, 25) for l in df_plot['label'].astype(str)]
    ax.set_xticks(np.arange(len(wrapped_labels)))
    ax.set_xticklabels(wrapped_labels, rotation=30, ha='right', fontsize=8)
    fig.subplots_adjust(bottom=0.33)
    ax.grid(axis='y', linestyle='--', alpha=0.6, zorder=0)
    ax.bar_label(bars, fmt='%.2f', fontsize=7, padding=2)
    fig.tight_layout()
    return fig

def criar_grafico_simples(df, col_cat, col_val, titulo, cor, ylabel='Custo (€)'):
    if df is None or df.empty:
        return None
    df_plot = df[[col_cat, col_val]].copy()
    if df_plot[col_val].dtype == 'object':
        df_plot[col_val] = df_plot[col_val].astype(str).str.replace('%', '', regex=False).str.replace(',', '.', regex=False)
    df_plot[col_val] = pd.to_numeric(df_plot[col_val], errors='coerce').fillna(0)
    if df_plot[col_val].sum() == 0:
        return None
    fig, ax = plt.subplots(figsize=(9.2, 5.7), dpi=100)
    ax.bar(df_plot[col_cat].astype(str), df_plot[col_val], color=cor, edgecolor='black', zorder=3)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(titulo, fontweight='bold', fontsize=12)
    wrapped_labels = [textwrap.fill(l, 28) for l in df_plot[col_cat].astype(str)]
    ax.set_xticks(np.arange(len(wrapped_labels)))
    ax.set_xticklabels(wrapped_labels, rotation=30, ha='right', fontsize=8)
    fig.subplots_adjust(bottom=0.33)
    ax.grid(axis='y', linestyle='--', alpha=0.6, zorder=0)
    fig.tight_layout()
    return fig

# ========= DASHBOARD PRINCIPAL =========
class DashboardResumoCustos(QWidget):
    """Dashboard compacto, sem espaços desperdiçados, e margens/custos sempre em baixo."""
    def __init__(self, excel_path, parent=None):
        super().__init__(parent)
        self.excel_path = excel_path
        self.num_orc, self.versao = self.extrair_orc_ver()
        self.dfs = {}
        self.init_ui()

    def extrair_orc_ver(self):
        base_name = os.path.basename(self.excel_path)
        parts = base_name.replace("Resumo_Custos_", "").replace(".xlsx", "").split('_')
        return (parts[0], parts[1]) if len(parts) >= 2 else ("?", "?")

    def init_ui(self):
        # Margens mínimas, ocupa o máximo possível da área útil
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)

        export_button = QPushButton("Exportar Dashboard para PDF")
        export_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogSaveButton))
        export_button.clicked.connect(self.exportar_pdf)
        main_layout.addWidget(export_button, 0, Qt.AlignRight)

        # Grid compacto
        grid_layout = QGridLayout()
        grid_layout.setVerticalSpacing(2)
        grid_layout.setHorizontalSpacing(4)

        # Carrega todos os DataFrames necessários
        self.dfs['Placas'] = self.ler_df("Resumo Placas")
        self.dfs['Orlas'] = self.ler_df("Resumo Orlas")
        self.dfs['Ferragens'] = self.ler_df("Resumo Ferragens")
        self.dfs['Maquinas_MO'] = self.ler_df("Resumo Maquinas_MO")
        self.dfs['Margens'] = self.ler_df("Resumo Margens")

        # Blocos principais (Expanding), exceto Margens/Custos (Minimum)
        placas_box = self.criar_groupbox("Resumo de Placas", self.dfs['Placas'], criar_grafico_placas, expandir=True)
        orlas_box = self.criar_groupbox("Resumo de Orlas", self.dfs['Orlas'], criar_grafico_orlas, expandir=True)
        ferragens_box = self.criar_groupbox("Resumo de Ferragens", self.dfs['Ferragens'],
            lambda df: criar_grafico_simples(df, 'descricao_no_orcamento', 'custo_mp_total', 'Custos por Ferragem', '#F44336'), expandir=True)
        maquinas_box = self.criar_groupbox("Resumo de Máquinas e Mão de Obra", self.dfs['Maquinas_MO'],
            lambda df: criar_grafico_simples(df, 'Operação', 'Custo Total (€)', 'Custos por Operação', '#2196F3'), expandir=True)
        margens_box = self.criar_groupbox("Resumo de Margens e Custos", self.dfs['Margens'], func_grafico=None, expandir=False)
        margens_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Layout sem espaços mortos
        grid_layout.addWidget(placas_box, 0, 0)
        grid_layout.addWidget(orlas_box, 0, 1)
        grid_layout.addWidget(ferragens_box, 1, 0)
        grid_layout.addWidget(maquinas_box, 1, 1)
        grid_layout.addWidget(margens_box, 2, 0, 1, 2)
        grid_layout.setRowStretch(0, 3)
        grid_layout.setRowStretch(1, 3)
        grid_layout.setRowStretch(2, 1)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)
        main_layout.addLayout(grid_layout)
        self.setLayout(main_layout)

    def criar_groupbox(self, titulo, df, func_grafico=None, expandir=True):
        groupBox = QGroupBox(titulo)
        groupBox.setStyleSheet("QGroupBox { font-weight: bold; }")
        layout = QVBoxLayout()
        tabela = dataframe_para_qtablewidget(df)
        if expandir:
            tabela.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        else:
            tabela.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout.addWidget(tabela, stretch=2 if expandir else 1)
        if func_grafico:
            figura_grafico = func_grafico(df)
            if figura_grafico:
                canvas = FigureCanvas(figura_grafico)
                canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                layout.addWidget(canvas, stretch=3)
        groupBox.setLayout(layout)
        return groupBox

    def ler_df(self, sheet):
        if not os.path.exists(self.excel_path):
            return pd.DataFrame()
        try:
            return pd.read_excel(self.excel_path, sheet_name=sheet)
        except Exception as e:
            print(f"[Dashboard] Erro ao ler a folha '{sheet}': {e}")
            QtWidgets.QMessageBox.warning(self, "Erro ao ler Excel", f"Não foi possível ler a folha '{sheet}'.\nErro: {e}")
            return pd.DataFrame()

    def exportar_pdf(self):
        default_path = os.path.join(os.path.dirname(self.excel_path), f"Dashboard_Custos_{self.num_orc}_{self.versao}.pdf")
        path, _ = QFileDialog.getSaveFileName(self, "Guardar Dashboard PDF", default_path, "PDF Files (*.pdf)")
        if not path:
            return

        doc = SimpleDocTemplate(path, pagesize=landscape(A4), leftMargin=18, rightMargin=30, topMargin=30, bottomMargin=48)
        story = []
        styles = getSampleStyleSheet()
        story.append(Paragraph(f"Dashboard de Custos - Orçamento {self.num_orc} / Versão {self.versao}", styles['h1']))

        graficos_funcs = {
            "Placas": criar_grafico_placas,
            "Orlas": criar_grafico_orlas,
            "Ferragens": lambda df: criar_grafico_simples(df, 'descricao_no_orcamento', 'custo_mp_total', 'Custos por Ferragem', '#F44336'),
            "Maquinas_MO": lambda df: criar_grafico_simples(df, 'Operação', 'Custo Total (€)', 'Custos por Operação', '#2196F3')
        }

        for key, df in self.dfs.items():
            if df is None or df.empty:
                continue
            story.append(PageBreak())
            story.append(Paragraph(f"Resumo de {key.replace('_', ' ')}", styles['h2']))
            story.append(Spacer(1, 7))
            df_abrev, col_abrev = abreviar_colunas(df.fillna(''))
            df_str = df_abrev.apply(lambda col: col.map(lambda x: f"{x:,.2f}" if isinstance(x, (int, float)) else str(x)))
            # Ajuste visual da coluna 'N/Stock'
            data = [col_abrev] + df_str.values.tolist()
            col_widths = colwidths_pdf(col_abrev)
            # Preencher N/Stock por ✓
            try:
                idx_nstock = col_abrev.index("N/Stock")
                for row in data[1:]:
                    row[idx_nstock] = "✓" if str(row[idx_nstock]).strip().lower() in ["1", "sim", "x", "✓"] else ""
            except Exception:
                pass
            table = Table(data, colWidths=col_widths, hAlign='LEFT', repeatRows=1)
            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('WORDWRAP', (0, 0), (-1, -1))
            ])
            table.setStyle(style)
            story.append(table)
            if key in graficos_funcs:
                fig = graficos_funcs.get(key)(df)
                if fig:
                    img_buffer = io.BytesIO()
                    fig.savefig(img_buffer, format='png', dpi=150)
                    plt.close(fig)
                    img_buffer.seek(0)
                    story.append(Spacer(1, 10))
                    story.append(Image(img_buffer, width=470, height=235))
        doc.build(story, canvasmaker=lambda *a, **kw: FooterCanvas(f"Orçamento {self.num_orc} / Versão {self.versao}", *a, **kw))
        QtWidgets.QMessageBox.information(self, "Sucesso", f"Dashboard exportado para:\n{path}")

# ========= INTEGRAÇÃO PRINCIPAL =========
def mostrar_dashboard_resumos(parent_widget, excel_path):
    # Remove widgets antigos e mostra novo dashboard
    if parent_widget.layout() is not None:
        while parent_widget.layout().count():
            child = parent_widget.layout().takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    else:
        parent_widget.setLayout(QVBoxLayout(parent_widget))
    dashboard = DashboardResumoCustos(excel_path)
    parent_widget.layout().addWidget(dashboard)
