# dashboard_resumos_custos.py
# Mostra os resumos de custos do Excel de cada orçamento como dashboard visual no PyQt5

# =============================================================================
# Este módulo permite:
#   - Ler ficheiros Excel com resumos de custos por orçamento.
#   - Apresentar dashboards visuais e tabelas com os custos de placas, orlas, ferragens, máquinas e margens.
#   - Gerar gráficos automáticos para cada grupo de custos (matplotlib).
#   - Exportar o dashboard inteiro (tabelas + gráficos) para PDF, com rodapé personalizado e paginação.
#   - Integrar facilmente numa aplicação PyQt5.
#
# Dependências: pandas, numpy, matplotlib, reportlab, PyQt5
# =============================================================================

import os
import io
import pandas as pd
import numpy as np
from datetime import datetime
import textwrap

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QSizePolicy, QTableWidgetItem, 
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

# =============================================================================
# Classe FooterCanvas
# =============================================================================
# Descrição:
# Classe personalizada para desenhar o rodapé do PDF exportado, mostrando
# data, nº do orçamento, versão e numeração das páginas.
# =============================================================================
class FooterCanvas(canvas.Canvas):
    """Classe personalizada para desenhar o rodapé em cada página do PDF."""
    def __init__(self, num_orc_ver, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.num_orc_ver = num_orc_ver
        self._saved_page_states = []

    def showPage(self):
        # Guarda o estado de cada página antes de passar à seguinte
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        # Ao terminar, desenha o rodapé em todas as páginas antes de gravar
        page_count = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_footer(page_count)
            super().showPage()
        super().save()

    def draw_footer(self, page_count):
        # Desenha o rodapé com data, orçamento/versão e nº da página
        self.saveState()
        self.setFont('Helvetica', 9)
        data_hoje = datetime.now().strftime("%d/%m/%Y")
        page_num = self.getPageNumber()
        
        # Desenha os elementos do rodapé
        self.drawString(30, 20, data_hoje)
        self.drawCentredString(landscape(A4)[0] / 2, 20, self.num_orc_ver)
        self.drawRightString(landscape(A4)[0] - 30, 20, f"Página {page_num} / {page_count}")
        
        self.restoreState()

# =============================================================================
# Função: dataframe_para_qtablewidget
# =============================================================================
# Descrição:
# Converte um DataFrame do pandas para um QTableWidget PyQt5,
# mantendo o formato, o alinhamento e ajustando visualmente a tabela.
# =============================================================================

def dataframe_para_qtablewidget(df: pd.DataFrame) -> QTableWidget:
    """Converte um DataFrame do Pandas para um QTableWidget bem formatado."""
    if df is None or df.empty:
        table = QTableWidget(1, 1); table.setItem(0, 0, QTableWidgetItem("Sem dados para exibir.")); return table
    table = QTableWidget(len(df), len(df.columns))
    table.setHorizontalHeaderLabels(df.columns.astype(str))
    for i in range(len(df)):
        for j in range(len(df.columns)):
            valor = df.iat[i, j]
            if pd.isna(valor):
                valor_str = ""
            elif isinstance(valor, (int, float)):
                valor_str = f"{valor:,.2f}"
            else:
                valor_str = str(valor)
            item = QTableWidgetItem(valor_str)
            if isinstance(valor, (int, float)):
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(i, j, item)
    table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    table.setAlternatingRowColors(True)
    table.setFixedHeight(table.horizontalHeader().height() + table.rowHeight(0) * (table.rowCount() + 1) + 2)
    return table

# =============================================================================
# Função: criar_grafico_placas
# =============================================================================
# Descrição:
# Cria um gráfico de barras agrupadas para comparar custos teóricos
# e reais (com desperdício) das placas usadas no orçamento.
# Legendas longas são ajustadas para não ficarem cortadas.
# =============================================================================
def criar_grafico_placas(df):
    """Cria um gráfico de barras agrupado para comparar custos de placas."""
    if df is None or df.empty:
        return None
    df_plot = df[['descricao_no_orcamento', 'custo_mp_total', 'custo_placas_utilizadas']].copy()
    for col in ['custo_mp_total', 'custo_placas_utilizadas']:
        df_plot[col] = pd.to_numeric(df_plot[col], errors='coerce').fillna(0)
    
    # Define a cor da barra com base na comparação: Vermelho se custo real > teórico, Verde caso contrário.
    colors = ['#F44336' if real > custo else '#4CAF50' for real, custo in zip(df_plot['custo_placas_utilizadas'], df_plot['custo_mp_total'])]
    
    x = np.arange(len(df_plot['descricao_no_orcamento']))
    width = 0.35
    # Aumentar a altura do gráfico para dar espaço às labels
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=100)

    ax.bar(x - width/2, df_plot['custo_mp_total'], width, label='Custo Teórico', color='skyblue', edgecolor='black', zorder=3)
    ax.bar(x + width/2, df_plot['custo_placas_utilizadas'], width, label='Custo Real (c/ Desperdício)', color=colors, edgecolor='black', zorder=3)

    ax.set_ylabel('Custo (€)', fontsize=10)
    ax.set_title('Comparativo de Custos por Placa', fontweight='bold', fontsize=13)
    ax.set_xticks(x)

    # MAIS ESPAÇO PARA CADA LABEL (quebra em linhas maiores)
    wrapped_labels = [textwrap.fill(l, 30) for l in df_plot['descricao_no_orcamento'].astype(str)]
    ax.set_xticklabels(wrapped_labels, rotation=30, ha='right', fontsize=9)

    # MAIS ESPAÇO EM BAIXO PARA NÃO CORTAR AS LEGENDAS
    fig.subplots_adjust(bottom=0.30)

    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.6, zorder=0)
    fig.tight_layout()
    return fig

# =============================================================================
# Função: criar_grafico_orlas
# =============================================================================
# Descrição:
# Cria um gráfico de barras simples para mostrar o consumo total
# de cada tipo de orla (metros lineares), com legendas otimizadas.
# =============================================================================
def criar_grafico_orlas(df):
    """Cria um gráfico de barras para o consumo de orlas."""
    if df is None or df.empty:
        return None
    df_plot = df.copy()
    df_plot['label'] = df_plot['ref_orla'].astype(str) + ' (' + df_plot['espessura_orla'].astype(str) + ', ' + df_plot['largura_orla'].astype(int).astype(str) + 'mm)'
    
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=100)
    bars = ax.bar(df_plot['label'], pd.to_numeric(df_plot['ml_total'], errors='coerce'), color='orange', edgecolor='black', zorder=3)
    ax.set_ylabel('Metros Lineares (ml)', fontsize=10)
    ax.set_title('Consumo de Orlas (ml)', fontweight='bold', fontsize=13)

    # Rotaciona e quebra label, ajusta fonte e margem inferior
    wrapped_labels = [textwrap.fill(l, 30) for l in df_plot['label'].astype(str)]
    ax.set_xticks(np.arange(len(wrapped_labels)))
    ax.set_xticklabels(wrapped_labels, rotation=30, ha='right', fontsize=9)
    fig.subplots_adjust(bottom=0.30)
    
    ax.grid(axis='y', linestyle='--', alpha=0.6, zorder=0)
    ax.bar_label(bars, fmt='%.2f', fontsize=8, padding=3)
    fig.tight_layout()
    return fig

# =============================================================================
# Função: criar_grafico_simples
# =============================================================================
# Descrição:
# Gráfico genérico de barras simples para categorias e valores.
# Serve para custos de ferragens, máquinas, etc. Otimiza as labels.
# =============================================================================
def criar_grafico_simples(df, col_cat, col_val, titulo, cor, ylabel='Custo (€)'):
    """Cria um gráfico de barras simples para uma categoria e um valor."""
    if df is None or df.empty:
        return None
    df_plot = df[[col_cat, col_val]].copy()
    if df_plot[col_val].dtype == 'object':
        df_plot[col_val] = df_plot[col_val].astype(str).str.replace('%', '', regex=False).str.replace(',', '.', regex=False)
    df_plot[col_val] = pd.to_numeric(df_plot[col_val], errors='coerce').fillna(0)
    if df_plot[col_val].sum() == 0:
        return None

    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=100)
    ax.bar(df_plot[col_cat].astype(str), df_plot[col_val], color=cor, edgecolor='black', zorder=3)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(titulo, fontweight='bold', fontsize=13)
    # Rotaciona, quebra label, ajusta fonte e margem inferior
    wrapped_labels = [textwrap.fill(l, 30) for l in df_plot[col_cat].astype(str)]
    ax.set_xticks(np.arange(len(wrapped_labels)))
    ax.set_xticklabels(wrapped_labels, rotation=30, ha='right', fontsize=9)
    fig.subplots_adjust(bottom=0.30)
    ax.grid(axis='y', linestyle='--', alpha=0.6, zorder=0)
    fig.tight_layout()
    return fig


# =============================================================================
# Classe Principal: DashboardResumoCustos
# =============================================================================
# Descrição:
# Widget principal do dashboard PyQt5. Organiza e exibe as tabelas
# e gráficos para cada grupo de custos do orçamento. Permite exportar
# tudo para PDF, com layout visual e rodapé.
# =============================================================================

class DashboardResumoCustos(QWidget):
    """Widget que organiza e exibe todos os resumos e gráficos."""
    def __init__(self, excel_path, parent=None):
        super().__init__(parent)
        self.excel_path = excel_path
        self.num_orc, self.versao = self.extrair_orc_ver()
        self.dfs = {}
        self.init_ui()

    def extrair_orc_ver(self):
        # Extrai o nº do orçamento e versão a partir do nome do ficheiro Excel
        base_name = os.path.basename(self.excel_path)
        parts = base_name.replace("Resumo_Custos_", "").replace(".xlsx", "").split('_')
        return (parts[0], parts[1]) if len(parts) >= 2 else ("?", "?")

    def init_ui(self):
        # Cria o layout principal do dashboard
        main_layout = QVBoxLayout(self)
        
        export_button = QPushButton("Exportar Dashboard para PDF")
        export_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogSaveButton))
        export_button.clicked.connect(self.exportar_pdf)
        main_layout.addWidget(export_button, 0, Qt.AlignRight)

        grid_layout = QGridLayout(); grid_layout.setSpacing(15)

        self.dfs['Placas'] = self.ler_df("Resumo Placas")
        self.dfs['Orlas'] = self.ler_df("Resumo Orlas")
        self.dfs['Ferragens'] = self.ler_df("Resumo Ferragens")
        self.dfs['Maquinas_MO'] = self.ler_df("Resumo Maquinas_MO")
        self.dfs['Margens'] = self.ler_df("Resumo Margens")
         # Adiciona cada bloco (GroupBox) ao layout

        placas_box = self.criar_groupbox("Resumo de Placas", self.dfs['Placas'], criar_grafico_placas)
        orlas_box = self.criar_groupbox("Resumo de Orlas", self.dfs['Orlas'], criar_grafico_orlas)
        ferragens_box = self.criar_groupbox("Resumo de Ferragens", self.dfs['Ferragens'], lambda df: criar_grafico_simples(df, 'descricao_no_orcamento', 'custo_mp_total', 'Custos por Ferragem', '#F44336'))
        maquinas_box = self.criar_groupbox("Resumo de Máquinas e Mão de Obra", self.dfs['Maquinas_MO'], lambda df: criar_grafico_simples(df, 'Operação', 'Custo Total (€)', 'Custos por Operação', '#2196F3'))
        margens_box = self.criar_groupbox("Resumo de Margens e Custos", self.dfs['Margens'], func_grafico=None)

        # MELHORIA: Reduzir a altura máxima do GroupBox das margens
        margens_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        grid_layout.addWidget(placas_box, 0, 0); grid_layout.addWidget(orlas_box, 0, 1)
        grid_layout.addWidget(ferragens_box, 1, 0); grid_layout.addWidget(maquinas_box, 1, 1)
        grid_layout.addWidget(margens_box, 2, 0, 1, 2)

        main_layout.addLayout(grid_layout)
        self.setLayout(main_layout)

    def criar_groupbox(self, titulo, df, func_grafico=None):
        # Cria um bloco visual (GroupBox) com tabela + gráfico
        groupBox = QGroupBox(titulo)
        groupBox.setStyleSheet("QGroupBox { font-weight: bold; }")
        layout = QVBoxLayout()
        tabela = dataframe_para_qtablewidget(df)
        layout.addWidget(tabela)
        if func_grafico:
            figura_grafico = func_grafico(df)
            if figura_grafico:
                layout.addWidget(FigureCanvas(figura_grafico))
        groupBox.setLayout(layout)
        return groupBox

    def ler_df(self, sheet):
        # Lê uma folha do Excel para DataFrame (ou devolve vazio)
        if not os.path.exists(self.excel_path):
            return pd.DataFrame()
        try:
            return pd.read_excel(self.excel_path, sheet_name=sheet)
        except Exception as e:
            print(f"[Dashboard] Erro ao ler a folha '{sheet}': {e}")
            QtWidgets.QMessageBox.warning(self, "Erro ao ler Excel", f"Não foi possível ler a folha '{sheet}'.\nErro: {e}")
            return pd.DataFrame()

    def exportar_pdf(self):
        # Exporta todo o dashboard (tabelas + gráficos) para PDF visual
        default_path = os.path.join(os.path.dirname(self.excel_path), f"Dashboard_Custos_{self.num_orc}_{self.versao}.pdf")
        path, _ = QFileDialog.getSaveFileName(self, "Guardar Dashboard PDF", default_path, "PDF Files (*.pdf)")
        if not path:
            return

        doc = SimpleDocTemplate(path, pagesize=landscape(A4), leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=50)
        story = []
        styles = getSampleStyleSheet()
        
        story.append(Paragraph(f"Dashboard de Custos - Orçamento {self.num_orc} / Versão {self.versao}", styles['h1']))

        graficos_funcs = {
            "Placas": criar_grafico_placas,
            "Orlas": criar_grafico_orlas,
            "Ferragens": lambda df: criar_grafico_simples(df, 'descricao_no_orcamento', 'custo_mp_total', 'Custos por Ferragem', '#F44336'),
            "Maquinas_MO": lambda df: criar_grafico_simples(df, 'Operação', 'Custo Total (€)', 'Custos por Operação', '#2196F3'),
            }

        for key, df in self.dfs.items():
            if df.empty:
                continue
            story.append(PageBreak())
            story.append(Paragraph(f"Resumo de {key}", styles['h2']))
            story.append(Spacer(1, 12))

            
            # CORREÇÃO para remover 'nan' do PDF
            df_pdf = df.fillna('')
            df_str = df_pdf.apply(lambda col: col.map(lambda x: f"{x:,.2f}" if isinstance(x, (int, float)) else str(x)))
            
            data = [df_str.columns.tolist()] + df_str.values.tolist()
            table = Table(data, hAlign='LEFT', repeatRows=1)
            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('WORDWRAP', (0, 0), (-1, -1)),
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
                    story.append(Spacer(1, 12))
                    story.append(Image(img_buffer, width=500, height=250))

        doc.build(story, canvasmaker=lambda *a, **kw: FooterCanvas(f"Orçamento {self.num_orc} / Versão {self.versao}", *a, **kw))
        QtWidgets.QMessageBox.information(self, "Sucesso", f"Dashboard exportado para:\n{path}")

# =============================================================================
# Função de integração principal
# =============================================================================
# Descrição:
# Função que recebe o widget pai e o caminho do Excel, limpa o conteúdo atual
# do widget e insere o dashboard do orçamento (PyQt5) pronto a ser usado.
# =============================================================================
def mostrar_dashboard_resumos(parent_widget, excel_path):
    if parent_widget.layout() is not None:
        while parent_widget.layout().count():
            child = parent_widget.layout().takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    else:
        parent_widget.setLayout(QVBoxLayout(parent_widget))
    dashboard = DashboardResumoCustos(excel_path)
    parent_widget.layout().addWidget(dashboard)