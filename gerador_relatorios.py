# gerador_relatorios.py

import os
from PyQt5 import  QtWidgets
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import ( SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,)
from reportlab.lib.styles import getSampleStyleSheet
import xlsxwriter
from orcamentos import _gerar_nome_pasta_orcamento

def _parse_float(value: str) -> float:
    """Converts a string to float, handling thousands separators."""
    if not value:
        return 0.0
    txt = str(value).strip()
    txt = txt.replace('\xa0', '').replace(' ', '')  # remove spaces/nbsp
    txt = txt.replace('.', '').replace(',', '.')
    try:
        return float(txt)
    except ValueError:
        return 0.0

def _first_text(*widgets) -> str:
    """Return the first non-empty text from given widgets."""
    for w in widgets:
        if w is not None:
            txt = w.text()
            if txt:
                return txt
    return ""

def preencher_campos_relatorio(ui: QtWidgets.QWidget) -> None:
    """Preenche a aba de relatório com os dados atuais do orçamento."""
    # Dados do cliente
    ui.lineEdit_nome_cliente_3.setText(
        _first_text( getattr(ui, "lineEdit_nome_cliente", None))
    )
    print(f"Nome cliente: {ui.lineEdit_nome_cliente_3.text()}")
    
    ui.lineEdit_morada_cliente_3.setText(
        _first_text(getattr(ui, "lineEdit_morada_cliente", None))
    )
    print(f"Morada cliente: {ui.lineEdit_morada_cliente_3.text()}")
    
    ui.lineEdit_email_cliente_3.setText(
        _first_text(getattr(ui, "lineEdit_email_cliente", None))
    )
    print(f"Email cliente: {ui.lineEdit_email_cliente_3.text()}")
    
    ui.lineEdit_num_cliente_phc_3.setText(
        _first_text(getattr(ui, "lineEdit_num_cliente_phc", None))
    )
    print(f"Num cliente PHC: {ui.lineEdit_num_cliente_phc_3.text()}")
    
    ui.lineEdit_telefone_3.setText(
        _first_text(getattr(ui, "lineEdit_telefone", None))
    )
    print(f"Telefone: {ui.lineEdit_telefone_3.text()}")
    
    ui.lineEdit_telemovel_3.setText(
        _first_text(getattr(ui, "lineEdit_telemovel", None))
    )
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
    for i in range(n):
        qt_item = dst.item(i, 7)
        pt_item = dst.item(i, 9)
        qt = _parse_float(qt_item.text() if qt_item else "")
        pt = _parse_float(pt_item.text() if pt_item else "")
        total_qt += qt
        subtotal += pt

    ui.label_total_qt_2.setText(f"Total QT: {total_qt:g}")
    ui.label_subtotal_2.setText(f"Subtotal: {subtotal:,.2f}")
    ui.label_iva_2.setText("IVA: 23%")
    total_geral = subtotal * 1.23
    ui.label_total_geral_2.setText(f"Total Geral: {total_geral:,.2f}")
    ui.label_paginacao_2.setText("1/1")


def gera_pdf(ui: QtWidgets.QWidget, caminho: str) -> None:
    """Gera um PDF com os dados do relatório."""
    doc = SimpleDocTemplate(caminho, pagesize=A4)
    styles = getSampleStyleSheet()

    elems = []
    elems.append(Paragraph("Relatório de Orçamento", styles["Heading1"]))
    elems.append(Paragraph(
        f"Data: {ui.label_data_orcamento_2.text()}", styles["Normal"]
    ))
    elems.append(
        Paragraph(
            f"Número: {ui.label_num_orcamento_2.text()} / {ui.label_ver_orcamento_2.text()}",
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

    headers = [
        "Item",
        "Codigo",
        "Descrição",
        "Altura",
        "Largura",
        "Profundidade",
        "Und",
        "QT",
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
            ]
        )
    )
    elems.append(table)
    elems.append(Spacer(1, 12))
    elems.append(Paragraph(ui.label_total_qt_2.text(), styles["Normal"]))
    elems.append(Paragraph(ui.label_subtotal_2.text(), styles["Normal"]))
    elems.append(Paragraph(ui.label_iva_2.text(), styles["Normal"]))
    elems.append(Paragraph(ui.label_total_geral_2.text(), styles["Normal"]))

    doc.build(elems)


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
