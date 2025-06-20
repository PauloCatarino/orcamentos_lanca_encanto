# =============================================================================
# relatorio_orcamento.py
# =============================================================================
# Geração de relatórios de orçamento (PDF e Excel)
# - Preenche os dados do orçamento na interface (cliente, totais, tabela de itens).
# - Gera ficheiros PDF (com ReportLab) e Excel (com xlsxwriter) prontos a enviar ao cliente.
# - Integra-se com as funções de dashboard/resumos de custos.
# - Permite gerir pasta de cada orçamento e garantir organização dos ficheiros.

# Este módulo recolhe os dados preenchidos na interface gráfica, calcula os
# totais do orçamento e exporta duas versões do relatório:
# - PDF criado com ReportLab, incluindo uma tabela de itens e um rodapé com
#   data, número orçamento e versão e paginação 1/2 ; 2/2.
# - Ficheiro Excel produzido com xlsxwriter contendo os mesmos dados.
#
# A função :func:`gerar_relatorio_orcamento` coordena o processo de preenchimento
# e geração dos ficheiros.
# =============================================================================

import os
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QHeaderView, QMessageBox, QVBoxLayout
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
import xlsxwriter
from db_connection import obter_cursor

from orcamentos import _gerar_nome_pasta_orcamento
from resumo_consumos import gerar_resumos_excel

# =============================================================================
# Função: _parse_float
# =============================================================================
# Converte um texto (com símbolo € ou separadores de milhares) para float,
# garantindo compatibilidade entre formatos (pt/EN).
# =============================================================================
def _parse_float(value: str) -> float:
    if not value:
        return 0.0
    txt = str(value).strip()
    txt = txt.replace('€', '').replace('$', '').replace('\xa0', '').replace(' ', '')
    # Tratamento de formatos tipo '1.234,56' ou '1,234.56'
    if ',' in txt:
        partes = txt.split(',')
        if len(partes) == 2:
            parte_inteira = partes[0].replace('.', '')
            parte_decimal = partes[1]
            txt = f"{parte_inteira}.{parte_decimal}"
    else:
        pontos = txt.count('.')
        if pontos > 1:
            partes = txt.split('.')
            txt = ''.join(partes[:-1]) + '.' + partes[-1]
    try:
        return float(txt)
    except ValueError:
        return 0.0

# =============================================================================
# Função: _first_text
# =============================================================================
# Retorna o primeiro texto preenchido de uma lista de widgets.
# Usado para buscar dados de cliente da interface (procurando por vários campos).
# =============================================================================
def _first_text(*widgets) -> str:
    for w in widgets:
        if w is not None:
            txt = w.text()
            if txt:
                return txt
    return ""

# =============================================================================
# Função: _obter_dados_cliente
# =============================================================================
# Consulta a base de dados pelo ID do cliente e devolve os dados para o relatório.
# =============================================================================
def _obter_dados_cliente(cliente_id: str):
    if not cliente_id:
        return None
    try:
        with obter_cursor() as cur:
            cur.execute(
                "SELECT nome, morada, email, numero_cliente_phc, telefone, telemovel FROM clientes WHERE id=%s",
                (cliente_id,),
            )
            return cur.fetchone()
    except Exception as e:
        print(f"Erro ao obter dados do cliente {cliente_id}: {e}")
        return None

# =============================================================================
# Classe FooterCanvas
# =============================================================================
# Canvas customizado para desenhar o rodapé do PDF (data, nº orçamento/versão, página).
# =============================================================================
class FooterCanvas(canvas.Canvas):
    def __init__(self, data_str: str, num_ver: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_str = data_str
        self.num_ver = num_ver
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_footer(page_count)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def _draw_footer(self, page_count: int):
        width, _ = A4
        self.setFont("Helvetica", 9)
        page_num = self.getPageNumber()
        footer = f"{self.data_str}   {self.num_ver}   {page_num}/{page_count}"
        self.drawCentredString(width / 2, 20, footer)

# =============================================================================
# Função: preencher_campos_relatorio
# =============================================================================
# Preenche na interface (UI) todos os campos do relatório, incluindo:
# - Dados de cliente (nome, morada, contacto, etc.)
# - Dados do orçamento (nº, versão, data)
# - Tabela de itens do orçamento
# - Cálculo de totais, subtotal, total geral, etc.
# =============================================================================
def preencher_campos_relatorio(ui: QtWidgets.QWidget) -> None:
    c
    cliente_id = _first_text(
        getattr(ui, "lineEdit_id_cliente", None),
        getattr(ui, "lineEdit_idCliente_noOrc", None),
    )
    dados_cli = _obter_dados_cliente(cliente_id)
    if dados_cli:
        nome, morada, email, num_phc, tel, telm = dados_cli
        ui.lineEdit_nome_cliente_3.setText(nome or "")
        ui.lineEdit_morada_cliente_3.setText(morada or "")
        ui.lineEdit_email_cliente_3.setText(email or "")
        ui.lineEdit_num_cliente_phc_3.setText(num_phc or "")
        ui.lineEdit_telefone_3.setText(tel or "")
        ui.lineEdit_telemovel_3.setText(telm or "")
    else:
        ui.lineEdit_nome_cliente_3.setText(
            _first_text(getattr(ui, "lineEdit_nome_cliente", None))
        )
        ui.lineEdit_morada_cliente_3.setText(
            _first_text(getattr(ui, "lineEdit_morada_cliente", None))
        )
        ui.lineEdit_email_cliente_3.setText(
            _first_text(getattr(ui, "lineEdit_email_cliente", None))
        )
        ui.lineEdit_num_cliente_phc_3.setText(
            _first_text(getattr(ui, "lineEdit_num_cliente_phc", None))
        )
        ui.lineEdit_telefone_3.setText(
            _first_text(getattr(ui, "lineEdit_telefone", None))
        )
        ui.lineEdit_telemovel_3.setText(
            _first_text(getattr(ui, "lineEdit_telemovel", None))
        )

    # 2. Preencher dados do orçamento
    data_orc = ui.lineEdit_data.text()
    num_orc = ui.lineEdit_num_orcamento.text()
    ver_orc = ui.lineEdit_versao_orcamento.text()
    ui.label_data_orcamento_2.setText(data_orc)
    ui.label_data_2.setText(data_orc)
    ui.label_num_orcamento_2.setText(num_orc)
    ui.label_num_orcamento_3.setText(num_orc)
    ui.label_ver_orcamento_2.setText(ver_orc)
    ui.label_ver_orcamento_3.setText(ver_orc)

    # 3. Copiar tabela de artigos para tabela de relatório
    src = ui.tableWidget_artigos
    dst = ui.tableWidget_Items_Linha_Relatorio
    n = src.rowCount()
    dst.setRowCount(n)
    for i in range(n):
        for c in range(10):  # Colunas 1-10 (ignora coluna 0: id_item)
            item = src.item(i, c + 1)
            txt = item.text() if item else ""
            dst.setItem(i, c, QtWidgets.QTableWidgetItem(txt))

    # 4. Ajustar colunas e linhas para visualização
    larguras = [60, 100, 1600, 80, 80, 80, 60, 80, 150, 151]
    header = dst.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.Interactive)
    for idx, largura in enumerate(larguras):
        if idx < dst.columnCount():
            dst.setColumnWidth(idx, largura)
    dst.setWordWrap(True)
    dst.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    dst.resizeRowsToContents()

    # 5. Calcular totais (quantidade, subtotal, total geral)
    total_qt = 0.0
    subtotal = 0.0
    for i in range(n):
        qt_item = dst.item(i, 7)
        pt_item = dst.item(i, 9)
        qt_text = qt_item.text() if qt_item else ""
        pt_text = pt_item.text() if pt_item else ""
        qt = _parse_float(qt_text)
        pt = _parse_float(pt_text)
        total_qt += qt
        subtotal += pt
    ui.label_total_qt_2.setText(f"Total QT: {total_qt:g}")
    ui.label_subtotal_2.setText(f"Subtotal: {subtotal:,.2f}")
    ui.label_iva_2.setText("IVA: 23%")
    total_geral = subtotal * 1.23
    ui.label_total_geral_2.setText(f"Total Geral: {total_geral:,.2f}")
    ui.label_paginacao_2.setText("1/1")

# =============================================================================
# Função: gera_pdf
# =============================================================================
# Gera um ficheiro PDF com todos os dados do orçamento, incluindo:
# - Cabeçalho, dados do cliente, tabela de itens, totais e rodapé paginado.
# =============================================================================
def gera_pdf(ui: QtWidgets.QWidget, caminho: str) -> None:
    doc = SimpleDocTemplate(
        caminho, pagesize=A4,
        leftMargin=10, rightMargin=10, topMargin=10, bottomMargin=50
    )
    styles = getSampleStyleSheet()
    elems = []
    elems.append(Paragraph("Relatório de Orçamento", styles["Heading1"]))
    elems.append(Paragraph(f"Data: {ui.label_data_orcamento_2.text()}", styles["Normal"]))
    elems.append(Paragraph(
        f"Orcamento: {ui.label_num_orcamento_2.text()}_{ui.label_ver_orcamento_2.text()}",
        styles["Normal"],
    ))
    elems.append(Spacer(1, 12))
    dados_cli = [
        f"Nome: {ui.lineEdit_nome_cliente_3.text()}",
        f"Morada: {ui.lineEdit_morada_cliente_3.text()}",
        f"Email: {ui.lineEdit_email_cliente_3.text()}",
        f"Nº Cliente PHC: {ui.lineEdit_num_cliente_phc_3.text()}",
        f"Telefone: {ui.lineEdit_telefone_3.text()}  Telemóvel: {ui.lineEdit_telemovel_3.text()}",
    ]
    for d in dados_cli:
        elems.append(Paragraph(d, styles["Normal"]))
    elems.append(Spacer(1, 12))
    headers = [
        "Item", "Codigo", "Descrição", "Alt", "Larg", "Prof",
        "Und", "Qt", "Preco Unit", "Preco Total"
    ]
    data = [headers]
    tw = ui.tableWidget_Items_Linha_Relatorio
    for r in range(tw.rowCount()):
        row = []
        for c in range(tw.columnCount()):
            itm = tw.item(r, c)
            txt = itm.text() if itm else ""
            if c == 2:
                lines = txt.splitlines()
                if lines:
                    first, *rest = lines
                    formatted = f"<b>{first}</b>"
                    if rest:
                        formatted += "<br/><i>" + "<br/>".join(l.strip("\t-") for l in rest) + "</i>"
                    row.append(Paragraph(formatted, styles["Normal"]))
                else:
                    row.append("")
            elif c == 9:
                row.append(Paragraph(f"<b>{txt}</b>", styles["Normal"]))
            else:
                row.append(txt)
        data.append(row)
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),
        ])
    )
    elems.append(table)
    elems.append(Spacer(1, 12))
    right_style = ParagraphStyle("right", parent=styles["Normal"], alignment=2)
    total_style = ParagraphStyle("total", parent=right_style, fontSize=12, leading=14)
    elems.append(Paragraph(ui.label_total_qt_2.text(), right_style))
    elems.append(Paragraph(ui.label_subtotal_2.text(), right_style))
    elems.append(Paragraph(ui.label_iva_2.text(), right_style))
    elems.append(Paragraph(ui.label_total_geral_2.text(), total_style))
    doc.build(
        elems,
        canvasmaker=lambda *a, **kw: FooterCanvas(
            ui.label_data_orcamento_2.text(),
            f"{ui.label_num_orcamento_2.text()}_{ui.label_ver_orcamento_2.text()}",
            *a, **kw,
        ),
    )

# =============================================================================
# Função: gera_excel
# =============================================================================
# Gera um ficheiro Excel com a tabela de itens e totais do orçamento.
# =============================================================================
def gera_excel(ui: QtWidgets.QWidget, caminho: str) -> None:
    wb = xlsxwriter.Workbook(caminho)
    ws = wb.add_worksheet("Relatório")
    headers = [
        "Item", "Codigo", "Descricao", "Altura", "Largura", "Profundidade",
        "Und", "QT", "Preco_Unit", "Preco_Total"
    ]
    for col, h in enumerate(headers):
        ws.write(0, col, h)
    tw = ui.tableWidget_Items_Linha_Relatorio
    for r in range(tw.rowCount()):
        for c in range(tw.columnCount()):
            item = tw.item(r, c)
            txt = item.text() if item else ""
            ws.write(r + 1, c, txt)
    row_total = tw.rowCount()
    qt_text = ui.label_total_qt_2.text().split(":", 1)[-1]
    subtotal_text = ui.label_subtotal_2.text().split(":", 1)[-1]
    total_geral_text = ui.label_total_geral_2.text().split(":", 1)[-1]
    ws.write(row_total + 1, 7, _parse_float(qt_text))
    ws.write(row_total + 2, 9, _parse_float(subtotal_text.replace(",", "")))
    ws.write(row_total + 3, 9, _parse_float(total_geral_text.replace(",", "")))
    wb.close()

# =============================================================================
# Função: _obter_caminho_pasta_orcamento
# =============================================================================
# Devolve o caminho onde guardar relatórios para este orçamento/versão.
# Garante que as pastas existem (versão '00' e a versão atual).
# =============================================================================
def _obter_caminho_pasta_orcamento(ui: QtWidgets.QWidget) -> str:
    caminho_base = ui.lineEdit_orcamentos.text().strip()
    ano = ui.lineEdit_ano.text().strip()
    num = ui.lineEdit_num_orcamento_2.text().strip()
    nome_cliente = ui.lineEdit_nome_cliente_2.text().strip()
    versao = ui.lineEdit_versao.text().strip()
    nome_pasta = _gerar_nome_pasta_orcamento(num, nome_cliente)
    pasta_mae = os.path.join(caminho_base, ano, nome_pasta)
    pasta_versao = os.path.join(pasta_mae, versao)
    # Cria pastas se necessário
    if versao != "00":
        os.makedirs(os.path.join(pasta_mae, "00"), exist_ok=True)
    os.makedirs(pasta_versao, exist_ok=True)
    return pasta_versao

# =============================================================================
# Função: exportar_relatorio
# =============================================================================
# Gera os ficheiros PDF e Excel do orçamento na pasta correta.
# Mostra mensagem ao utilizador no final.
# =============================================================================
def exportar_relatorio(ui: QtWidgets.QWidget) -> None:
    pasta = _obter_caminho_pasta_orcamento(ui)
    num = ui.label_num_orcamento_2.text()
    ver = ui.label_ver_orcamento_2.text()
    pdf_path = os.path.join(pasta, f"{num}_{ver}.pdf")
    xls_path = os.path.join(pasta, f"{num}_{ver}.xlsx")
    gera_pdf(ui, pdf_path)
    gera_excel(ui, xls_path)
    print(f"Relatórios guardados em:\nPDF: {pdf_path}\nXLSX: {xls_path}")
    QtWidgets.QMessageBox.information(
        getattr(ui, "tabWidget_orcamento", None),
        "Gerado",
        f"Arquivos gerados:\n• {pdf_path}\n• {xls_path}",
    )

# =============================================================================
# Função: gerar_relatorio_orcamento
# =============================================================================
# Processo completo: preenche os campos, pergunta ao utilizador e gera os ficheiros.
# =============================================================================
def gerar_relatorio_orcamento(ui: QtWidgets.QWidget) -> None:
    preencher_campos_relatorio(ui)
    resp = QtWidgets.QMessageBox.question(
        getattr(ui, "tabWidget_orcamento", None),
        "Confirmar geração",
        "Campos preenchidos.\nDeseja gerar o PDF e o Excel agora?",
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        QtWidgets.QMessageBox.Yes,
    )
    if resp == QtWidgets.QMessageBox.Yes:
        exportar_relatorio(ui)

# =============================================================================
# Função: on_gerar_relatorio_consumos_clicked
# =============================================================================
# Handler para o botão 'Gerar Relatório de Consumos'.
# Gera o ficheiro Excel de resumo, mostra dashboard e seleciona o separador correto.
# =============================================================================
def on_gerar_relatorio_consumos_clicked(ui):
    print("===> Handler chamado!")
    try:
        pasta_orcamento = _obter_caminho_pasta_orcamento(ui)
        if not pasta_orcamento or not os.path.exists(pasta_orcamento):
            QMessageBox.warning(None, "Caminho Inválido", f"A pasta do orçamento não foi encontrada ou não pôde ser criada:\n{pasta_orcamento}")
            return
    except Exception as e:
        QMessageBox.critical(None, "Erro Crítico", f"Falha ao obter o caminho da pasta do orçamento:\n{e}")
        return
    num_orcamento = ui.lineEdit_num_orcamento_2.text().strip()
    versao = ui.lineEdit_versao.text().strip()
    if not num_orcamento or not versao:
        QMessageBox.warning(None, "Dados Incompletos", "Por favor, preencha o número do orçamento e a versão antes de gerar o relatório.")
        return
    nome_ficheiro_excel = f"Resumo_Custos_{num_orcamento}_{versao}.xlsx"
    caminho_completo_excel = os.path.join(pasta_orcamento, nome_ficheiro_excel)
    try:
        from resumo_consumos import gerar_resumos_excel
        print(f"===> A gerar resumos para o ficheiro: {caminho_completo_excel}")
        gerar_resumos_excel(caminho_completo_excel, num_orcamento, versao)
    except Exception as e:
        QMessageBox.critical(None, "Erro", f"Erro ao gerar o ficheiro Excel de resumos:\n{e}")
        import traceback
        traceback.print_exc()
        return
    try:
        from dashboard_resumos_custos import mostrar_dashboard_resumos
        print(f"===> A gerar dashboard com dados de: {caminho_completo_excel}")
        if not os.path.exists(caminho_completo_excel):
            QMessageBox.warning(None, "Ficheiro não encontrado", f"O ficheiro de resumos não foi encontrado após a tentativa de criação:\n{caminho_completo_excel}")
            return
        mostrar_dashboard_resumos(ui.frame_resumos, caminho_completo_excel)
        ui.tabWidget_orcamento.setCurrentWidget(ui.tab_relatorios)
        ui.Relatorio_Orcamento_2.setCurrentWidget(ui.Resumo_Consumos_Orcamento_2)
    except Exception as e:
        QMessageBox.critical(None, "Erro de Dashboard", f"Ocorreu um erro ao exibir o dashboard:\n{e}")
        import traceback
        traceback.print_exc()

# =============================================================================
# Main para testes: Executa o fluxo todo se correr diretamente este ficheiro
# =============================================================================
if __name__ == "__main__":
    from orcamentos_le_layout import Ui_MainWindow
    app = QtWidgets.QApplication([])
    main_win = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(main_win)
    if ui.frame_resumos.layout() is None:
        layout_resumos = QVBoxLayout(ui.frame_resumos)
        ui.frame_resumos.setLayout(layout_resumos)
    ui.pushButton_Export_PDF_Relatorio.clicked.connect(lambda: gerar_relatorio_orcamento(ui))
    ui.pushButton_Gerar_Relatorio_Consumos.clicked.connect(lambda: on_gerar_relatorio_consumos_clicked(ui))
    main_win.show()
    app.exec_()
