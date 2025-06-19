# dashboard_resumos_custos.py
# Mostra os resumos de custos do Excel de cada orçamento como dashboard visual no PyQt5

import os
import pandas as pd
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QTableWidgetItem, QTabWidget, QWidget, QVBoxLayout, QLabel, QTableWidget, QSizePolicy

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from dashboard_resumos_custos import *  # noqa

# -------------------------------------------------------------
# Função para criar QTableWidget a partir de um DataFrame
# -------------------------------------------------------------
def dataframe_para_qtablewidget(df: pd.DataFrame) -> QTableWidget:
    table = QTableWidget()
    table.setRowCount(len(df))
    table.setColumnCount(len(df.columns))
    table.setHorizontalHeaderLabels(df.columns)
    for i in range(len(df)):
        for j in range(len(df.columns)):
            valor = str(df.iat[i, j])
            item = QTableWidgetItem(valor)
            table.setItem(i, j, item)
    table.resizeColumnsToContents()
    table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    return table

# -------------------------------------------------------------
# Função para gerar um gráfico matplotlib como widget Qt
# -------------------------------------------------------------
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=2.7, dpi=100):
        fig, self.ax = plt.subplots(figsize=(width, height), dpi=dpi)
        super(MplCanvas, self).__init__(fig)

def criar_grafico_barras(df, coluna_categoria, coluna_valor, titulo="", cor="tab:blue"):
    # Remove linhas sem valores
    df = df.dropna(subset=[coluna_categoria, coluna_valor])
    fig = plt.figure(figsize=(6, 2.7))
    ax = fig.add_subplot(111)
    barras = ax.bar(df[coluna_categoria].astype(str), df[coluna_valor].astype(float), color=cor)
    ax.set_title(titulo)
    ax.set_ylabel(coluna_valor)
    plt.xticks(rotation=30)
    plt.tight_layout()
    # Mostra os valores nas barras
    for bar in barras:
        altura = bar.get_height()
        ax.annotate(f'{altura:.1f}', xy=(bar.get_x() + bar.get_width() / 2, altura),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=8)
    return fig

# -------------------------------------------------------------
# Widget Dashboard Principal (tabs e gráficos)
# -------------------------------------------------------------
class DashboardResumoCustos(QWidget):
    """
    Widget principal para mostrar os resumos por tab + gráficos.
    """
    def __init__(self, excel_path, parent=None):
        super().__init__(parent)
        self.excel_path = excel_path
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget(self)

        # --- Placas
        self.tab_placas = QWidget()
        layout_placas = QVBoxLayout(self.tab_placas)
        df_placas = self.ler_df("Resumo Placas")
        tabela_placas = dataframe_para_qtablewidget(df_placas)
        layout_placas.addWidget(QLabel("Resumo de Placas (m2 e custos):"))
        layout_placas.addWidget(tabela_placas)
        # Gráfico de barras com custos das placas
        if not df_placas.empty and 'descricao_no_orcamento' in df_placas and 'custo_placas_utilizadas' in df_placas:
            fig = criar_grafico_barras(df_placas, "descricao_no_orcamento", "custo_placas_utilizadas", "Custos por Placa", cor="tab:green")
            canvas = FigureCanvas(fig)
            layout_placas.addWidget(canvas)
        self.tabs.addTab(self.tab_placas, "Placas")

        # --- Orlas
        self.tab_orlas = QWidget()
        layout_orlas = QVBoxLayout(self.tab_orlas)
        df_orlas = self.ler_df("Resumo Orlas")
        tabela_orlas = dataframe_para_qtablewidget(df_orlas)
        layout_orlas.addWidget(QLabel("Resumo de Orlas (ml e custos):"))
        layout_orlas.addWidget(tabela_orlas)
        if not df_orlas.empty and 'ref_orla' in df_orlas and 'custo_total' in df_orlas:
            fig = criar_grafico_barras(df_orlas, "ref_orla", "custo_total", "Custos por Orla", cor="tab:orange")
            canvas = FigureCanvas(fig)
            layout_orlas.addWidget(canvas)
        self.tabs.addTab(self.tab_orlas, "Orlas")

        # --- Ferragens
        self.tab_ferragens = QWidget()
        layout_ferragens = QVBoxLayout(self.tab_ferragens)
        df_ferragens = self.ler_df("Resumo Ferragens")
        tabela_ferragens = dataframe_para_qtablewidget(df_ferragens)
        layout_ferragens.addWidget(QLabel("Resumo de Ferragens:"))
        layout_ferragens.addWidget(tabela_ferragens)
        if not df_ferragens.empty and 'descricao_no_orcamento' in df_ferragens and 'custo_mp_total' in df_ferragens:
            fig = criar_grafico_barras(df_ferragens, "descricao_no_orcamento", "custo_mp_total", "Custos por Ferragem", cor="tab:red")
            canvas = FigureCanvas(fig)
            layout_ferragens.addWidget(canvas)
        self.tabs.addTab(self.tab_ferragens, "Ferragens")

        # --- Máquinas/MO
        self.tab_maquinas = QWidget()
        layout_maquinas = QVBoxLayout(self.tab_maquinas)
        df_maquinas = self.ler_df("Resumo Maquinas_MO")
        tabela_maquinas = dataframe_para_qtablewidget(df_maquinas)
        layout_maquinas.addWidget(QLabel("Resumo Máquinas/Mão de Obra:"))
        layout_maquinas.addWidget(tabela_maquinas)
        if not df_maquinas.empty and 'Operação' in df_maquinas and 'Custo Total (€)' in df_maquinas:
            fig = criar_grafico_barras(df_maquinas, "Operação", "Custo Total (€)", "Custos por Operação", cor="tab:blue")
            canvas = FigureCanvas(fig)
            layout_maquinas.addWidget(canvas)
        self.tabs.addTab(self.tab_maquinas, "Máquinas/MO")

        # --- Margens
        self.tab_margens = QWidget()
        layout_margens = QVBoxLayout(self.tab_margens)
        df_margens = self.ler_df("Resumo Margens")
        tabela_margens = dataframe_para_qtablewidget(df_margens)
        layout_margens.addWidget(QLabel("Margens e Custos Administrativos:"))
        layout_margens.addWidget(tabela_margens)
        self.tabs.addTab(self.tab_margens, "Margens/Admin")

        layout.addWidget(self.tabs)

    def ler_df(self, sheet):
        """
        Lê o separador do Excel.
        """
        if not os.path.exists(self.excel_path):
            return pd.DataFrame()
        try:
            df = pd.read_excel(self.excel_path, sheet_name=sheet)
            return df
        except Exception as e:
            print(f"[dashboard_resumos_custos] Erro ao ler {sheet}: {e}")
            return pd.DataFrame()

# -------------------------------------------------------------
# Função utilitária para abrir o dashboard no separador Qt
# -------------------------------------------------------------
def mostrar_dashboard_resumos(parent_widget, excel_path):
    """
    Mostra o dashboard visual de custos no widget pai.
    parent_widget: o widget Qt (QWidget, QVBoxLayout ou frame) onde o dashboard vai ser apresentado
    excel_path: caminho para o Excel de resumos do orçamento selecionado
    """
    # Limpa widgets antigos se existirem (importante para recarregar)
    for i in reversed(range(parent_widget.layout().count())):
        widget = parent_widget.layout().itemAt(i).widget()
        if widget is not None:
            widget.setParent(None)
    dashboard = DashboardResumoCustos(excel_path)
    parent_widget.layout().addWidget(dashboard)

# -------------------------------------------------------------
# EXEMPLO DE INTEGRAÇÃO:  
# No handler do botão pushButton_Gerar_Relatorio_Consumos, 
# DEPOIS de gerar o excel, chama:
#     mostrar_dashboard_resumos(ui.frame_resumos, path_excel)
# onde ui.frame_resumos é um QFrame/QWidget do separador "Resumo_Consumos_Orcamento_2"
# -------------------------------------------------------------
