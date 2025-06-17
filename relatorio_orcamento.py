# relatorio_orcamento.py

"""Gerador dos relatórios de orçamento em PDF e Excel.

Este módulo recolhe os dados preenchidos na interface gráfica, calcula os
totais do orçamento e exporta duas versões do relatório:
 - PDF criado com ReportLab, incluindo uma tabela de itens e um rodapé com
   data, número orçamento e versão e paginação 1/2 ; 2/2.
 - Ficheiro Excel produzido com xlsxwriter contendo os mesmos dados.

A função :func:`gerar_relatorio_orcamento` coordena o processo de preenchimento
e geração dos ficheiros.
"""

import os
from PyQt5 import QtWidgets
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import ( SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
import xlsxwriter
from db_connection import obter_cursor

from orcamentos import _gerar_nome_pasta_orcamento

def _parse_float(value: str) -> float:
    """Converts a string to float, handling thousands separators and currency symbols."""
    if not value:
        return 0.0
    
    txt = str(value).strip()
    print(f"DEBUG _parse_float: valor original='{txt}'")
    
    # Remove símbolos de moeda e espaços
    txt = txt.replace('€', '').replace('$', '').replace('\xa0', '').replace(' ', '')
    print(f"DEBUG _parse_float: após remover símbolos='{txt}'")
    
    # Se contém vírgula, assumimos formato português/europeu (1.234,56)
    if ',' in txt:
        # Separa a parte decimal
        partes = txt.split(',')
        if len(partes) == 2:
            # Remove pontos da parte inteira (separadores de milhares)
            parte_inteira = partes[0].replace('.', '')
            parte_decimal = partes[1]
            txt = f"{parte_inteira}.{parte_decimal}"
            print(f"DEBUG _parse_float: formato europeu convertido='{txt}'")
    else:
        # Se não tem vírgula, pode ser formato americano ou número simples
        # Apenas remove pontos se houver mais de um (separadores de milhares)
        pontos = txt.count('.')
        if pontos > 1:
            # Remove todos os pontos exceto o último
            partes = txt.split('.')
            txt = ''.join(partes[:-1]) + '.' + partes[-1]
            print(f"DEBUG _parse_float: múltiplos pontos corrigidos='{txt}'")
    
    try:
        resultado = float(txt)
        print(f"DEBUG _parse_float: resultado final={resultado}")
        return resultado
    except ValueError as e:
        print(f"DEBUG _parse_float: erro ao converter '{txt}': {e}")
        return 0.0

def _first_text(*widgets) -> str:
    """Return the first non-empty text from given widgets."""
    for w in widgets:
        if w is not None:
            txt = w.text()
            if txt:
                return txt
    return ""

def _obter_dados_cliente(cliente_id: str):
    """Retorna dados do cliente a partir do id."""
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

def preencher_campos_relatorio(ui: QtWidgets.QWidget) -> None:
    """Preenche a aba de relatório com os dados atuais do orçamento."""
    # Dados do cliente
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



    print(f"Nome cliente: {ui.lineEdit_nome_cliente_3.text()}")
    
  
    print(f"Morada cliente: {ui.lineEdit_morada_cliente_3.text()}")
    
   
    print(f"Email cliente: {ui.lineEdit_email_cliente_3.text()}")
    
   
    print(f"Num cliente PHC: {ui.lineEdit_num_cliente_phc_3.text()}")
    
   
    print(f"Telefone: {ui.lineEdit_telefone_3.text()}")
    
   
    print(f"Telemóvel: {ui.lineEdit_telemovel_3.text()}")

    # Dados do orçamento
    data_orc = ui.lineEdit_data.text()
    num_orc = ui.lineEdit_num_orcamento.text()
    ver_orc = ui.lineEdit_versao_orcamento.text()

    ui.label_data_orcamento_2.setText(data_orc)
    ui.label_data_2.setText(data_orc)
    ui.label_num_orcamento_2.setText(num_orc)
    ui.label_num_orcamento_3.setText(num_orc)
    ui.label_ver_orcamento_2.setText(ver_orc)
    ui.label_ver_orcamento_3.setText(ver_orc)

    # Itens do orçamento
    src = ui.tableWidget_artigos
    dst = ui.tableWidget_Items_Linha_Relatorio
    n = src.rowCount()
    dst.setRowCount(n)
    # Copia colunas 1-10 da tabela de artigos (ignora a coluna 0 "id_item")
    for i in range(n):
        for c in range(10):
            item = src.item(i, c + 1)
            txt = item.text() if item else ""
            dst.setItem(i, c, QtWidgets.QTableWidgetItem(txt))

    # Totais
    total_qt = 0.0
    subtotal = 0.0
    print(f"Iniciando cálculo de totais. Número de linhas: {n}")

    for i in range(n):
        qt_item = dst.item(i, 7)
        pt_item = dst.item(i, 9)  # Nota: mudei de coluna 10 para 9 - verificar se está correto
        
        qt_text = qt_item.text() if qt_item else ""
        pt_text = pt_item.text() if pt_item else ""
        
        print(f"Linha {i}: QT raw='{qt_text}', PT raw='{pt_text}'")
        
        qt = _parse_float(qt_text)
        pt = _parse_float(pt_text)
        
        print(f"Linha {i}: QT parsed={qt}, PT_preco total parsed={pt}")
        
        total_qt += qt
        subtotal += pt
        
        print(f"Linha {i}: total_qt acumulado={total_qt}, subtotal acumulado={subtotal}")

    print(f"Totais finais: total_qt={total_qt}, subtotal={subtotal}")

    ui.label_total_qt_2.setText(f"Total QT: {total_qt:g}")
    ui.label_subtotal_2.setText(f"Subtotal: {subtotal:,.2f}")
    ui.label_iva_2.setText("IVA: 23%")
    total_geral = subtotal * 1.23
    print(f"Total geral calculado: {total_geral}")
    ui.label_total_geral_2.setText(f"Total Geral: {total_geral:,.2f}")
    ui.label_paginacao_2.setText("1/1")


def gera_pdf(ui: QtWidgets.QWidget, caminho: str) -> None:
    """Gera um PDF com os dados do relatório."""
    doc = SimpleDocTemplate(
        caminho,
        pagesize=A4,
        leftMargin=10,
        rightMargin=10,
        topMargin=10,
        bottomMargin=50,
    )   # Margens folha a4
    styles = getSampleStyleSheet()

    elems = []
    elems.append(Paragraph("Relatório de Orçamento", styles["Heading1"]))
    elems.append(Paragraph(
        f"Data: {ui.label_data_orcamento_2.text()}", styles["Normal"]
    ))
    elems.append(
        Paragraph(
            f"Orcamento: {ui.label_num_orcamento_2.text()}_{ui.label_ver_orcamento_2.text()}",
            styles["Normal"],
        )
    )
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
    # Nomes para colunas apresentar no Relatorio PDF
    headers = [
        "Item",
        "Codigo",
        "Descrição",
        "Alt",
        "Larg",
        "Prof",
        "Und",
        "Qt",
        "Preco Unit",
        "Preco Total",
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
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elems.append(table)
    elems.append(Spacer(1, 12))
    right_style = ParagraphStyle(
        "right", parent=styles["Normal"], alignment=2
    )
    total_style = ParagraphStyle(
        "total", parent=right_style, fontSize=12, leading=14
    )
    elems.append(Paragraph(ui.label_total_qt_2.text(), right_style))
    elems.append(Paragraph(ui.label_subtotal_2.text(), right_style))
    elems.append(Paragraph(ui.label_iva_2.text(), right_style))
    elems.append(Paragraph(ui.label_total_geral_2.text(), total_style))

    doc.build(
        elems,
        canvasmaker=lambda *a, **kw: FooterCanvas(
            ui.label_data_orcamento_2.text(),
            f"{ui.label_num_orcamento_2.text()}_{ui.label_ver_orcamento_2.text()}",
            *a,
            **kw,
        ),
    )


def gera_excel(ui: QtWidgets.QWidget, caminho: str) -> None:
    """Gera um ficheiro Excel com a tabela de itens."""
    wb = xlsxwriter.Workbook(caminho)
    ws = wb.add_worksheet("Relatório")

    headers = [
        "Item",
        "Codigo",
        "Descricao",
        "Altura",
        "Largura",
        "Profundidade",
        "Und",
        "QT",
        "Preco_Unit",
        "Preco_Total",
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


def _obter_caminho_pasta_orcamento(ui: QtWidgets.QWidget) -> str:
    """Obtém (e cria, se necessário) o caminho onde guardar os relatórios."""
    caminho_base = ui.lineEdit_orcamentos.text().strip()
    ano = ui.lineEdit_ano.text().strip()
    num = ui.lineEdit_num_orcamento_2.text().strip()
    nome_cliente = ui.lineEdit_nome_cliente_2.text().strip()
    versao = ui.lineEdit_versao.text().strip()
    nome_pasta = _gerar_nome_pasta_orcamento(num, nome_cliente)
    pasta = os.path.join(caminho_base, ano, nome_pasta)
    if versao != "00":
        pasta = os.path.join(pasta, versao)
    os.makedirs(pasta, exist_ok=True)
    return pasta


def exportar_relatorio(ui: QtWidgets.QWidget) -> None:
    """Gera os ficheiros PDF e Excel na pasta do orçamento."""
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


def gerar_relatorio_orcamento(ui: QtWidgets.QWidget) -> None:
    """Fluxo completo de geração do relatório."""
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




# Se executares este ficheiro diretamente:
if __name__ == "__main__":
    from orcamentos_le_layout import Ui_MainWindow
    app = QtWidgets.QApplication([])
    main_win = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(main_win)
    ui.pushButton_Export_PDF_Relatorio.clicked.connect(lambda: gerar_relatorio_orcamento(ui))
    main_win.show()
    app.exec_()
