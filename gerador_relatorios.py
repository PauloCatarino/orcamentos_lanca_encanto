# gerador_relatorios.py

import os
from PyQt5 import  QtWidgets
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import xlsxwriter

def preencher_campos_relatorio(ui: QtWidgets.QWidget) -> None:
    """Preenche a aba de relatório com os dados atuais do orçamento."""
    # Dados do cliente
    ui.lineEdit_nome_cliente_3.setText(ui.lineEdit_nome_cliente.text())
    ui.lineEdit_morada_cliente_3.setText(ui.lineEdit_morada_cliente.text())
    ui.lineEdit_email_cliente_3.setText(ui.lineEdit_email_cliente.text())
    ui.lineEdit_num_cliente_phc_3.setText(ui.lineEdit_num_cliente_phc.text())
    ui.lineEdit_telefone_3.setText(ui.lineEdit_telefone.text())
    ui.lineEdit_telemovel_3.setText(ui.lineEdit_telemovel.text())

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
    for i in range(n):
        for c in range(10):
            item = src.item(i, c)
            txt = item.text() if item else ""
            dst.setItem(i, c, QtWidgets.QTableWidgetItem(txt))

    # Totais
    total_qt = 0
    subtotal = 0.0
    for i in range(n):
        qt_item = dst.item(i, 7)
        pt_item = dst.item(i, 9)
        qt = float(qt_item.text()) if qt_item else 0
        pt = float(pt_item.text()) if pt_item else 0
        total_qt += qt
        subtotal += pt

    ui.label_total_qt_2.setText(f"Total QT: {total_qt:g}")
    ui.label_subtotal_2.setText(f"Subtotal: {subtotal:,.2f}")
    ui.label_iva_2.setText("IVA: 23%")
    total_geral = subtotal * 1.23
    ui.label_total_geral_2.setText(f"Total Geral: {total_geral:,.2f}")
    ui.label_paginacao_2.setText("1/1")


def gera_pdf(ui: QtWidgets.QWidget, caminho: str) -> None:
    """Cria um PDF simples com algumas informações do relatório."""
    c = canvas.Canvas(caminho, pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, h - 50, "Relatório de Orçamento")
    c.setFont("Helvetica", 10)
    c.drawString(40, h - 70, ui.label_data_orcamento_2.text())
    c.drawString(
        200,
        h - 70,
        f"{ui.label_num_orcamento_2.text()} / {ui.label_ver_orcamento_2.text()}",
    )
    c.showPage()
    c.save()


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
    ws.write(row_total + 1, 7, float(ui.label_total_qt_2.text().split(":")[1]))
    ws.write(
        row_total + 2,
        9,
        float(ui.label_subtotal_2.text().split(":")[1].replace(",", "")),
    )
    ws.write(
        row_total + 3,
        9,
        float(ui.label_total_geral_2.text().split(":")[1].replace(",", "")),
    )
    wb.close()


def exportar_relatorio(ui: QtWidgets.QWidget) -> None:
    """Gera os ficheiros PDF e Excel numa pasta específica."""
    num = ui.label_num_orcamento_2.text()
    ver = ui.label_ver_orcamento_2.text()
    pasta = os.path.join("orcamentos", f"{num}_{ver}")
    os.makedirs(pasta, exist_ok=True)

    pdf_path = os.path.join(pasta, f"{num}_{ver}.pdf")
    xls_path = os.path.join(pasta, f"{num}_{ver}.xlsx")

    gera_pdf(ui, pdf_path)
    gera_excel(ui, xls_path)

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
