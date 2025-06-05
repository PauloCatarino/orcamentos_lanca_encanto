# -*- coding: utf-8 -*-
"""
apagar_orcamento_le_layout.py
=============================
Este módulo define a interface gráfica (UI) para o diálogo de exclusão de orçamentos.
Funcionalidades:
  - Exibe informações sobre o orçamento a ser excluído (nome e versão).
  - Permite ao usuário escolher se deseja eliminar o orçamento da base de dados
    e/ou a pasta associada.
  - Apresenta botões para confirmar (OK) ou cancelar a operação.
  
Observação:
  Este módulo é gerado automaticamente pelo PyQt5 UI Code Generator (pyuic5) e
  não realiza operações de banco de dados. As alterações realizadas aqui são apenas
  referentes à interface e à documentação.
"""

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(375, 240)
        self.verticalLayout = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        
        # Título do diálogo
        self.label_titulo = QtWidgets.QLabel(Dialog)
        self.label_titulo.setObjectName("label_titulo")
        self.verticalLayout.addWidget(self.label_titulo)
        
        # Exibição do nome do orçamento
        self.label_nome_orcamento = QtWidgets.QLabel(Dialog)
        self.label_nome_orcamento.setObjectName("label_nome_orcamento")
        self.verticalLayout.addWidget(self.label_nome_orcamento)
        
        # Exibição da versão do orçamento
        self.label_versao_orcamento = QtWidgets.QLabel(Dialog)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_versao_orcamento.setFont(font)
        self.label_versao_orcamento.setObjectName("label_versao_orcamento")
        self.verticalLayout.addWidget(self.label_versao_orcamento)
        
        # Checkbox para eliminar o orçamento do banco de dados
        self.checkBox_apagar_bd = QtWidgets.QCheckBox(Dialog)
        font = QtGui.QFont()
        font.setPointSize(9)
        self.checkBox_apagar_bd.setFont(font)
        self.checkBox_apagar_bd.setObjectName("checkBox_apagar_bd")
        self.verticalLayout.addWidget(self.checkBox_apagar_bd)
        
        # Checkbox para eliminar a pasta do orçamento
        self.checkBox_apagar_pasta = QtWidgets.QCheckBox(Dialog)
        font = QtGui.QFont()
        font.setPointSize(9)
        self.checkBox_apagar_pasta.setFont(font)
        self.checkBox_apagar_pasta.setObjectName("checkBox_apagar_pasta")
        self.verticalLayout.addWidget(self.checkBox_apagar_pasta)
        
        # Layout horizontal para os botões de ação
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.pushButton_ok = QtWidgets.QPushButton(Dialog)
        self.pushButton_ok.setObjectName("pushButton_ok")
        self.horizontalLayout.addWidget(self.pushButton_ok)
        self.pushButton_cancel = QtWidgets.QPushButton(Dialog)
        self.pushButton_cancel.setObjectName("pushButton_cancel")
        self.horizontalLayout.addWidget(self.pushButton_cancel)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Eliminar Orçamento"))
        self.label_titulo.setText(_translate("Dialog", "Tem certeza que deseja eliminar este orçamento?"))
        self.label_nome_orcamento.setText(_translate("Dialog", "Nome do orçamento: --"))
        self.label_versao_orcamento.setText(_translate("Dialog", "Versão do orçamento: --"))
        self.checkBox_apagar_bd.setText(_translate("Dialog", "Eliminar da base de dados"))
        self.checkBox_apagar_pasta.setText(_translate("Dialog", "Eliminar a pasta do orçamento"))
        self.pushButton_ok.setText(_translate("Dialog", "OK"))
        self.pushButton_cancel.setText(_translate("Dialog", "Cancelar"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Dialog = QtWidgets.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(Dialog)
    Dialog.show()
    sys.exit(app.exec_())
