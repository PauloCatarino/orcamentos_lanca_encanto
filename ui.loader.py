#  ui.loader.py

"""Carregamento simples de um ficheiro ``.ui`` produzido no QtDesigner.

Este módulo demonstra como abrir o ficheiro ``resumo_consumos.ui`` e
ligar eventuais botões. Serve como ponto de partida para a interface do
Resumo de Consumos.
"""
from __future__ import annotations

from PySide6 import QtCore, QtWidgets, QtUiTools
import sys


class MainWindow(QtWidgets.QMainWindow):
    """Janela principal do Resumo de Consumos."""

    def __init__(self) -> None:
        super().__init__()
        loader = QtUiTools.QUiLoader()
        ui_file = QtCore.QFile("resumo_consumos.ui")
        ui_file.open(QtCore.QFile.ReadOnly)
        self.ui = loader.load(ui_file, self)
        ui_file.close()

        # Aqui ligamos sinais aos botões caso existam
        # ex.: self.ui.pushButton_exportar.clicked.connect(self.exportar_excel)

    def exportar_excel(self) -> None:
        """Exemplo de método a ligar a um botão de exportação."""
        print("Exportar para Excel ainda não implementado")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec())