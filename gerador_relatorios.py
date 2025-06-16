# gerador_relatorios.py

import os
from datetime import datetime

from PyQt5 import uic, QtWidgets
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import xlsxwriter


class GeradorRelatorios(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # 1) carrega o .ui que definimos (o layout do relatório)
        uic.loadUi("orcamentos_le_layout.ui", self)

        # 2) liga o botão de exportar ao handler
        self.pushButton_Export_PDF_Relatorio.clicked.connect(self.on_export_pdf_excel)

    def on_export_pdf_excel(self):
        # antes de exportar, garante que todos os campos estão atualizados
        self.preencher_campos_relatorio()

        # cria as pastas de saída (por ex: ./orcamentos/<numero>_<versao>/)
        num = self.label_num_orcamento_2.text()
        ver = self.label_ver_orcamento_2.text()
        pasta = os.path.join("orcamentos", f"{num}_{ver}")
        os.makedirs(pasta, exist_ok=True)

        # gera PDF e Excel
        pdf_path = os.path.join(pasta, f"{num}_{ver}.pdf")
        xls_path = os.path.join(pasta, f"{num}_{ver}.xlsx")
        self.gera_pdf(pdf_path)
        self.gera_excel(xls_path)

        QtWidgets.QMessageBox.information(self, "Sucesso",
            f"Relatório exportado como:\n• PDF: {pdf_path}\n• Excel: {xls_path}")

    def preencher_campos_relatorio(self):
        """Puxa dados dos outros separadores para este relatório."""

        # --- DADOS DO CLIENTE ---
        # supõe que os LineEdits do separador Clientes têm estes objectNames:
        nome = self.lineEdit_nome_cliente.text()
        morada = self.lineEdit_morada_cliente.text()
        email = self.lineEdit_email_cliente.text()
        num_phc = self.lineEdit_num_cliente_phc.text()
        tel = self.lineEdit_telefone.text()
        telm = self.lineEdit_telemovel.text()

        # preenche o groupBox_dados_cliente_3
        self.lineEdit_nome_cliente_3.setText(nome)
        self.lineEdit_morada_cliente_3.setText(morada)
        self.lineEdit_email_cliente_3.setText(email)
        self.lineEdit_num_cliente_phc_3.setText(num_phc)
        self.lineEdit_telefone_3.setText(tel)
        self.lineEdit_telemovel_3.setText(telm)

        # --- DADOS DO ORÇAMENTO (Consulta Orcamentos) ---
        data_orc = self.lineEdit_data.text()            # campo lineEdit_data no separador "Consulta Orcamentos"
        num_orc = self.lineEdit_num_orcamento.text()    # idem
        ver_orc = self.lineEdit_versao_orcamento.text() # idem

        self.label_data_orcamento_2.setText(data_orc)
        self.label_num_orcamento_2.setText(num_orc)
        self.label_ver_orcamento_2.setText(ver_orc)

        # --- ITENS DO ORÇAMENTO (Tabela no separador Orcamento) ---
        # lê a tabela de artigos (tableWidget_artigos) e copia para tableWidget_Items_Linha_Relatorio
        tw_src = self.tableWidget_artigos
        tw_dst = self.tableWidget_Items_Linha_Relatorio

        linhas = tw_src.rowCount()
        tw_dst.setRowCount(linhas)

        for i in range(linhas):
            # colunas: 0=Item,1=Codigo,2=Descricao,3=Altura,4=Largura,5=Profundidade,
            # 6=Und,7=QT,8=Preco_Unit,9=Preco_Total
            for col in range(10):
                valor = tw_src.item(i, col).text() if tw_src.item(i, col) else ""
                tw_dst.setItem(i, col, QtWidgets.QTableWidgetItem(valor))

        # --- CÁLCULOS DOS TOTAIS ---
        total_qt = 0
        subtotal = 0.0

        for i in range(linhas):
            qt = float(tw_dst.item(i, 7).text() or 0)
            pt = float(tw_dst.item(i, 9).text() or 0)
            total_qt += qt
            subtotal += pt

        # preenche os labels
        self.label_total_qt_2.setText(f"Total QT: {total_qt:g}")
        self.label_subtotal_2.setText(f"Subtotal: {subtotal:,.2f}")
        self.label_iva_2.setText("IVA: 23%")
        total_geral = subtotal * 1.23
        self.label_total_geral_2.setText(f"Total Geral: {total_geral:,.2f}")

        # --- RODAPÉ A4 ---
        # data no canto inferior esquerdo
        self.label_data_2.setText(self.lineEdit_data.text())

        # número de páginas (por agora fixa 1/1; se quiseres cálculo real, divide nºlinhas por linhas_por_página)
        self.label_paginacao_2.setText("1/1")

    def gera_pdf(self, caminho):
        """Gera um PDF simples com ReportLab usando o layout A4."""
        c = canvas.Canvas(caminho, pagesize=A4)
        width, height = A4

        # cabeçalho (logo + título)
        # c.drawImage(":/images/logo.png", width - 150, height - 80, width=120, height=60)

        # desenha as strings dos labels no PDF diretamente como exemplo
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, height - 50, "Relatório de Orçamento")

        # desenha o conteúdo dos campos principais
        c.setFont("Helvetica", 10)
        c.drawString(40, height - 80, self.label_data_orcamento_2.text())
        c.drawString(200, height - 80, self.label_num_orcamento_2.text())
        c.drawString(300, height - 80, self.label_ver_orcamento_2.text())

        # TODO: mais desenho de tabelas, totais, rodapé etc.

        c.showPage()
        c.save()

    def gera_excel(self, caminho):
        """Gera um .xlsx com os mesmos dados."""
        wb = xlsxwriter.Workbook(caminho)
        ws = wb.add_worksheet("Relatorio")

        # escreve cabeçalhos
        headers = ["Item", "Codigo", "Descricao", "Altura", "Largura",
                   "Profundidade", "Und", "QT", "Preco_Unit", "Preco_Total"]
        for c, h in enumerate(headers):
            ws.write(0, c, h)

        # escrê â linhas
        tw = self.tableWidget_Items_Linha_Relatorio
        for r in range(tw.rowCount()):
            for c in range(tw.columnCount()):
                texto = tw.item(r, c).text() if tw.item(r, c) else ""
                ws.write(r+1, c, texto)

        # totais ao fundo
        ws.write(r+2, 6, "Total QT")
        ws.write(r+2, 7, float(self.label_total_qt_2.text().split(":")[1]))
        ws.write(r+3, 8, "Subtotal")
        ws.write(r+3, 9, float(self.label_subtotal_2.text().split(":")[1].replace(",","")))
        ws.write(r+4, 8, "Total Geral")
        ws.write(r+4, 9, float(self.label_total_geral_2.text().split(":")[1].replace(",","")))

        wb.close()


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = GeradorRelatorios()
    window.show()
    app.exec_()
