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

        # 1) carrega o .ui do relatório
        uic.loadUi("orcamentos_le_layout.ui", self)

        # 2) conecta o botão a um novo handler que preenche e pergunta
        self.pushButton_Export_PDF_Relatorio.clicked.connect(self.handle_export_clicked)

    def handle_export_clicked(self):
        """
        Ao clicar:
        1) Preenche campos com dados atuais
        2) Pergunta se quer gerar PDF & Excel
        3) Se sim, chama o export
        """
        # 1) Preenche os campos do relatório
        self.preencher_campos_relatorio()

        # 2) Pergunta ao utilizador
        resp = QtWidgets.QMessageBox.question(
            self,
            "Confirmar geração",
            "Campos preenchidos.\nDeseja gerar o PDF e o Excel agora?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.Yes
        )
        if resp == QtWidgets.QMessageBox.Yes:
            # 3) Gera e guarda
            self.exportar_relatorio()

    def preencher_campos_relatorio(self):
        """Preenche todos os widgets do separador Relatorio_Orcamento_2."""
        # --- Dados do Cliente (vindos do separador Cliente) ---
        nome = self.lineEdit_nome_cliente.text()
        morada = self.lineEdit_morada_cliente.text()
        email = self.lineEdit_email_cliente.text()
        num_phc = self.lineEdit_num_cliente_phc.text()
        telefone = self.lineEdit_telefone.text()
        telemovel = self.lineEdit_telemovel.text()

        # Estes campos foram criados no relatório (_3)
        self.lineEdit_nome_cliente_3.setText(nome)
        self.lineEdit_morada_cliente_3.setText(morada)
        self.lineEdit_email_cliente_3.setText(email)
        self.lineEdit_num_cliente_phc_3.setText(num_phc)
        self.lineEdit_telefone_3.setText(telefone)
        self.lineEdit_telemovel_3.setText(telemovel)

        # --- Dados do Orcamento (Consulta Orcamentos) ---
        data_orc = self.lineEdit_data.text()
        num_orc = self.lineEdit_num_orcamento.text()
        ver_orc = self.lineEdit_versao_orcamento.text()

        self.label_data_orcamento_2.setText(data_orc)
        self.label_data_2.setText(data_orc)  # rodapé esquerdo
        self.label_num_orcamento_2.setText(num_orc)
        self.label_num_orcamento_3.setText(num_orc)  # rodapé centro
        self.label_ver_orcamento_2.setText(ver_orc)
        self.label_ver_orcamento_3.setText(ver_orc)  # rodapé centro

        # --- Itens do Orçamento (tabela do separador Orcamento) ---
        src = self.tableWidget_artigos
        dst = self.tableWidget_Items_Linha_Relatorio
        n = src.rowCount()
        dst.setRowCount(n)

        for i in range(n):
            for c in range(10):  # 10 colunas
                item = src.item(i, c)
                text = item.text() if item else ""
                dst.setItem(i, c, QtWidgets.QTableWidgetItem(text))

        # --- Cálculo dos totais ---
        total_qt = 0
        subtotal = 0.0
        for i in range(n):
            qt = float(dst.item(i, 7).text() or 0)
            pt = float(dst.item(i, 9).text() or 0)
            total_qt += qt
            subtotal += pt

        # preenche labels
        self.label_total_qt_2.setText(f"Total QT: {total_qt:g}")
        self.label_subtotal_2.setText(f"Subtotal: {subtotal:,.2f}")
        self.label_iva_2.setText("IVA: 23%")
        total_geral = subtotal * 1.23
        self.label_total_geral_2.setText(f"Total Geral: {total_geral:,.2f}")

        # --- Paginação (exemplo estático) ---
        # Se futura lógica dividir em várias páginas, atualiza aqui
        self.label_paginacao_2.setText("1/1")

    def exportar_relatorio(self):
        """Cria a pasta e gera PDF + Excel."""
        num = self.label_num_orcamento_2.text()
        ver = self.label_ver_orcamento_2.text()
        pasta = os.path.join("orcamentos", f"{num}_{ver}")
        os.makedirs(pasta, exist_ok=True)

        pdf_path = os.path.join(pasta, f"{num}_{ver}.pdf")
        xls_path = os.path.join(pasta, f"{num}_{ver}.xlsx")

        self.gera_pdf(pdf_path)
        self.gera_excel(xls_path)

        QtWidgets.QMessageBox.information(
            self, "Gerado",
            f"Arquivos gerados:\n• {pdf_path}\n• {xls_path}"
        )

    def gera_pdf(self, caminho):
        """Gera um PDF básico (podemos estender conforme layout)."""
        c = canvas.Canvas(caminho, pagesize=A4)
        w, h = A4

        # Cabeçalho
        c.setFont("Helvetica-Bold", 14)
        c.drawString(40, h-50, "Relatório de Orçamento")
        c.setFont("Helvetica", 10)
        c.drawString(40, h-70, self.label_data_orcamento_2.text())
        c.drawString(200, h-70, self.label_num_orcamento_2.text() + " / " + self.label_ver_orcamento_2.text())

        # TODO: desenhar tabela e rodapé completo

        c.showPage()
        c.save()

    def gera_excel(self, caminho):
        """Gera um .xlsx com os mesmos dados."""
        wb = xlsxwriter.Workbook(caminho)
        ws = wb.add_worksheet("Relatório")

        headers = ["Item","Codigo","Descricao","Altura","Largura",
                   "Profundidade","Und","QT","Preco_Unit","Preco_Total"]
        for col, h in enumerate(headers):
            ws.write(0, col, h)

        tw = self.tableWidget_Items_Linha_Relatorio
        for r in range(tw.rowCount()):
            for c in range(tw.columnCount()):
                txt = tw.item(r, c).text() if tw.item(r, c) else ""
                ws.write(r+1, c, txt)

        # Totais no Excel
        ws.write(r+2, 7, float(self.label_total_qt_2.text().split(":")[1]))
        ws.write(r+3, 9, float(self.label_subtotal_2.text().split(":")[1].replace(",", "")))
        ws.write(r+4, 9, float(self.label_total_geral_2.text().split(":")[1].replace(",", "")))

        wb.close()


# Se quiseres um entry-point de função:
def gerar_relatorio_orcamento():
    """
    Função para invocar desde o main.py, se preferires:
    from gerador_relatorios import gerar_relatorio_orcamento
    """
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    gerador = GeradorRelatorios()
    gerador.handle_export_clicked()


# Se executares este ficheiro diretamente:
if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    janela = GeradorRelatorios()
    janela.show()
    app.exec_()
