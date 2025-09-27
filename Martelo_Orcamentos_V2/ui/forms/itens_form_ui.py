# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'itens_form.ui'
##
## Created by: Qt User Interface Compiler version 6.9.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QSpacerItem, QTableView, QTextEdit,
    QVBoxLayout, QWidget)

class Ui_FormItens(object):
    def setupUi(self, FormItens):
        if not FormItens.objectName():
            FormItens.setObjectName(u"FormItens")
        FormItens.resize(1756, 1222)
        self.verticalLayoutMain = QVBoxLayout(FormItens)
        self.verticalLayoutMain.setSpacing(6)
        self.verticalLayoutMain.setObjectName(u"verticalLayoutMain")
        self.verticalLayoutMain.setContentsMargins(4, 4, 4, 4)
        self.header = QFrame(FormItens)
        self.header.setObjectName(u"header")
        self.header.setFrameShape(QFrame.Shape.StyledPanel)
        self.headerVLayout = QVBoxLayout(self.header)
        self.headerVLayout.setSpacing(2)
        self.headerVLayout.setObjectName(u"headerVLayout")
        self.headerVLayout.setContentsMargins(4, 4, 4, 4)
        self.headerRowA = QHBoxLayout()
        self.headerRowA.setSpacing(12)
        self.headerRowA.setObjectName(u"headerRowA")
        self.layout_cliente = QHBoxLayout()
        self.layout_cliente.setSpacing(4)
        self.layout_cliente.setObjectName(u"layout_cliente")
        self.layout_cliente.setContentsMargins(0, 0, 0, 0)
        self.lbl_cliente = QLabel(self.header)
        self.lbl_cliente.setObjectName(u"lbl_cliente")
        self.lbl_cliente.setMinimumSize(QSize(50, 0))

        self.layout_cliente.addWidget(self.lbl_cliente)

        self.lbl_cliente_val = QLabel(self.header)
        self.lbl_cliente_val.setObjectName(u"lbl_cliente_val")
        self.lbl_cliente_val.setMinimumSize(QSize(300, 0))

        self.layout_cliente.addWidget(self.lbl_cliente_val)


        self.headerRowA.addLayout(self.layout_cliente)

        self.layout_user = QHBoxLayout()
        self.layout_user.setSpacing(4)
        self.layout_user.setObjectName(u"layout_user")
        self.layout_user.setContentsMargins(0, 0, 0, 0)
        self.lbl_user = QLabel(self.header)
        self.lbl_user.setObjectName(u"lbl_user")

        self.layout_user.addWidget(self.lbl_user)

        self.lbl_user_val = QLabel(self.header)
        self.lbl_user_val.setObjectName(u"lbl_user_val")
        self.lbl_user_val.setMinimumSize(QSize(180, 0))

        self.layout_user.addWidget(self.lbl_user_val)


        self.headerRowA.addLayout(self.layout_user)

        self.headerSpacerA = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.headerRowA.addItem(self.headerSpacerA)


        self.headerVLayout.addLayout(self.headerRowA)

        self.headerRowB = QHBoxLayout()
        self.headerRowB.setSpacing(12)
        self.headerRowB.setObjectName(u"headerRowB")
        self.layout_ano = QHBoxLayout()
        self.layout_ano.setSpacing(4)
        self.layout_ano.setObjectName(u"layout_ano")
        self.layout_ano.setContentsMargins(0, 0, 0, 0)
        self.lbl_ano = QLabel(self.header)
        self.lbl_ano.setObjectName(u"lbl_ano")
        self.lbl_ano.setMinimumSize(QSize(30, 0))

        self.layout_ano.addWidget(self.lbl_ano)

        self.lbl_ano_val = QLabel(self.header)
        self.lbl_ano_val.setObjectName(u"lbl_ano_val")
        self.lbl_ano_val.setMinimumSize(QSize(60, 0))

        self.layout_ano.addWidget(self.lbl_ano_val)


        self.headerRowB.addLayout(self.layout_ano)

        self.layout_num = QHBoxLayout()
        self.layout_num.setSpacing(4)
        self.layout_num.setObjectName(u"layout_num")
        self.layout_num.setContentsMargins(0, 0, 0, 0)
        self.lbl_num = QLabel(self.header)
        self.lbl_num.setObjectName(u"lbl_num")

        self.layout_num.addWidget(self.lbl_num)

        self.lbl_num_val = QLabel(self.header)
        self.lbl_num_val.setObjectName(u"lbl_num_val")
        self.lbl_num_val.setMinimumSize(QSize(120, 0))

        self.layout_num.addWidget(self.lbl_num_val)


        self.headerRowB.addLayout(self.layout_num)

        self.layout_ver = QHBoxLayout()
        self.layout_ver.setSpacing(4)
        self.layout_ver.setObjectName(u"layout_ver")
        self.layout_ver.setContentsMargins(0, 0, 0, 0)
        self.lbl_ver = QLabel(self.header)
        self.lbl_ver.setObjectName(u"lbl_ver")
        self.lbl_ver.setMinimumSize(QSize(50, 0))

        self.layout_ver.addWidget(self.lbl_ver)

        self.lbl_ver_val = QLabel(self.header)
        self.lbl_ver_val.setObjectName(u"lbl_ver_val")
        self.lbl_ver_val.setMinimumSize(QSize(40, 0))

        self.layout_ver.addWidget(self.lbl_ver_val)


        self.headerRowB.addLayout(self.layout_ver)

        self.headerSpacerB = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.headerRowB.addItem(self.headerSpacerB)


        self.headerVLayout.addLayout(self.headerRowB)


        self.verticalLayoutMain.addWidget(self.header)

        self.form_frame = QFrame(FormItens)
        self.form_frame.setObjectName(u"form_frame")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.form_frame.sizePolicy().hasHeightForWidth())
        self.form_frame.setSizePolicy(sizePolicy)
        self.form_frame.setMinimumSize(QSize(0, 80))
        self.form_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.gridLayout = QGridLayout(self.form_frame)
        self.gridLayout.setObjectName(u"gridLayout")
        self.layout_codigo = QHBoxLayout()
        self.layout_codigo.setSpacing(4)
        self.layout_codigo.setObjectName(u"layout_codigo")
        self.layout_codigo.setContentsMargins(0, 0, 0, 0)
        self.lbl_codigo = QLabel(self.form_frame)
        self.lbl_codigo.setObjectName(u"lbl_codigo")

        self.layout_codigo.addWidget(self.lbl_codigo)

        self.edit_codigo = QLineEdit(self.form_frame)
        self.edit_codigo.setObjectName(u"edit_codigo")
        self.edit_codigo.setMinimumSize(QSize(180, 24))
        self.edit_codigo.setMaximumSize(QSize(180, 24))

        self.layout_codigo.addWidget(self.edit_codigo)


        self.gridLayout.addLayout(self.layout_codigo, 0, 3, 1, 1)

        self.layout_profundidade = QHBoxLayout()
        self.layout_profundidade.setSpacing(4)
        self.layout_profundidade.setObjectName(u"layout_profundidade")
        self.layout_profundidade.setContentsMargins(0, 0, 0, 0)
        self.lbl_profundidade = QLabel(self.form_frame)
        self.lbl_profundidade.setObjectName(u"lbl_profundidade")

        self.layout_profundidade.addWidget(self.lbl_profundidade)

        self.edit_profundidade = QLineEdit(self.form_frame)
        self.edit_profundidade.setObjectName(u"edit_profundidade")
        self.edit_profundidade.setMinimumSize(QSize(70, 24))
        self.edit_profundidade.setMaximumSize(QSize(90, 24))

        self.layout_profundidade.addWidget(self.edit_profundidade)


        self.gridLayout.addLayout(self.layout_profundidade, 0, 6, 1, 1)

        self.edit_item = QLineEdit(self.form_frame)
        self.edit_item.setObjectName(u"edit_item")
        self.edit_item.setMinimumSize(QSize(40, 24))
        self.edit_item.setMaximumSize(QSize(70, 24))
        self.edit_item.setReadOnly(True)

        self.gridLayout.addWidget(self.edit_item, 0, 1, 1, 1)

        self.layout_qt = QHBoxLayout()
        self.layout_qt.setSpacing(4)
        self.layout_qt.setObjectName(u"layout_qt")
        self.layout_qt.setContentsMargins(0, 0, 0, 0)
        self.lbl_qt = QLabel(self.form_frame)
        self.lbl_qt.setObjectName(u"lbl_qt")

        self.layout_qt.addWidget(self.lbl_qt)

        self.edit_qt = QLineEdit(self.form_frame)
        self.edit_qt.setObjectName(u"edit_qt")
        self.edit_qt.setMinimumSize(QSize(50, 24))
        self.edit_qt.setMaximumSize(QSize(70, 24))

        self.layout_qt.addWidget(self.edit_qt)


        self.gridLayout.addLayout(self.layout_qt, 0, 7, 1, 1)

        self.lbl_item = QLabel(self.form_frame)
        self.lbl_item.setObjectName(u"lbl_item")

        self.gridLayout.addWidget(self.lbl_item, 0, 0, 1, 1)

        self.rowSpacer = QSpacerItem(776, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.rowSpacer, 0, 9, 1, 1)

        self.layout_und = QHBoxLayout()
        self.layout_und.setSpacing(4)
        self.layout_und.setObjectName(u"layout_und")
        self.layout_und.setContentsMargins(0, 0, 0, 0)
        self.lbl_und = QLabel(self.form_frame)
        self.lbl_und.setObjectName(u"lbl_und")

        self.layout_und.addWidget(self.lbl_und)

        self.edit_und = QLineEdit(self.form_frame)
        self.edit_und.setObjectName(u"edit_und")
        self.edit_und.setMinimumSize(QSize(50, 24))
        self.edit_und.setMaximumSize(QSize(80, 24))

        self.layout_und.addWidget(self.edit_und)


        self.gridLayout.addLayout(self.layout_und, 0, 8, 1, 1)

        self.layout_altura = QHBoxLayout()
        self.layout_altura.setSpacing(4)
        self.layout_altura.setObjectName(u"layout_altura")
        self.layout_altura.setContentsMargins(0, 0, 0, 0)
        self.lbl_altura = QLabel(self.form_frame)
        self.lbl_altura.setObjectName(u"lbl_altura")

        self.layout_altura.addWidget(self.lbl_altura)

        self.edit_altura = QLineEdit(self.form_frame)
        self.edit_altura.setObjectName(u"edit_altura")
        self.edit_altura.setMinimumSize(QSize(60, 24))
        self.edit_altura.setMaximumSize(QSize(80, 24))

        self.layout_altura.addWidget(self.edit_altura)


        self.gridLayout.addLayout(self.layout_altura, 0, 4, 1, 1)

        self.edit_descricao = QTextEdit(self.form_frame)
        self.edit_descricao.setObjectName(u"edit_descricao")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.edit_descricao.sizePolicy().hasHeightForWidth())
        self.edit_descricao.setSizePolicy(sizePolicy1)
        self.edit_descricao.setMinimumSize(QSize(300, 100))
        self.edit_descricao.setMaximumSize(QSize(16777215, 150))

        self.gridLayout.addWidget(self.edit_descricao, 1, 2, 1, 7)

        self.lbl_descricao = QLabel(self.form_frame)
        self.lbl_descricao.setObjectName(u"lbl_descricao")

        self.gridLayout.addWidget(self.lbl_descricao, 1, 0, 1, 2)

        self.layout_largura = QHBoxLayout()
        self.layout_largura.setSpacing(4)
        self.layout_largura.setObjectName(u"layout_largura")
        self.layout_largura.setContentsMargins(0, 0, 0, 0)
        self.lbl_largura = QLabel(self.form_frame)
        self.lbl_largura.setObjectName(u"lbl_largura")

        self.layout_largura.addWidget(self.lbl_largura)

        self.edit_largura = QLineEdit(self.form_frame)
        self.edit_largura.setObjectName(u"edit_largura")
        self.edit_largura.setMinimumSize(QSize(60, 24))
        self.edit_largura.setMaximumSize(QSize(80, 24))

        self.layout_largura.addWidget(self.edit_largura)


        self.gridLayout.addLayout(self.layout_largura, 0, 5, 1, 1)


        self.verticalLayoutMain.addWidget(self.form_frame)

        self.buttonsLayout = QHBoxLayout()
        self.buttonsLayout.setSpacing(8)
        self.buttonsLayout.setObjectName(u"buttonsLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.buttonsLayout.addItem(self.horizontalSpacer)

        self.btn_add = QPushButton(FormItens)
        self.btn_add.setObjectName(u"btn_add")

        self.buttonsLayout.addWidget(self.btn_add)

        self.btn_save = QPushButton(FormItens)
        self.btn_save.setObjectName(u"btn_save")

        self.buttonsLayout.addWidget(self.btn_save)

        self.btn_del = QPushButton(FormItens)
        self.btn_del.setObjectName(u"btn_del")

        self.buttonsLayout.addWidget(self.btn_del)

        self.btn_expand = QPushButton(FormItens)
        self.btn_expand.setObjectName(u"btn_expand")

        self.buttonsLayout.addWidget(self.btn_expand)

        self.btn_collapse = QPushButton(FormItens)
        self.btn_collapse.setObjectName(u"btn_collapse")

        self.buttonsLayout.addWidget(self.btn_collapse)

        self.btn_up = QPushButton(FormItens)
        self.btn_up.setObjectName(u"btn_up")

        self.buttonsLayout.addWidget(self.btn_up)

        self.btn_dn = QPushButton(FormItens)
        self.btn_dn.setObjectName(u"btn_dn")

        self.buttonsLayout.addWidget(self.btn_dn)


        self.verticalLayoutMain.addLayout(self.buttonsLayout)

        self.table = QTableView(FormItens)
        self.table.setObjectName(u"table")
        self.table.setAlternatingRowColors(True)

        self.verticalLayoutMain.addWidget(self.table)


        self.retranslateUi(FormItens)

        QMetaObject.connectSlotsByName(FormItens)
    # setupUi

    def retranslateUi(self, FormItens):
        FormItens.setWindowTitle(QCoreApplication.translate("FormItens", u"Itens", None))
        self.lbl_cliente.setText(QCoreApplication.translate("FormItens", u"Cliente:", None))
        self.lbl_cliente_val.setText("")
        self.lbl_user.setText(QCoreApplication.translate("FormItens", u"Utilizador:", None))
        self.lbl_user_val.setText("")
        self.lbl_ano.setText(QCoreApplication.translate("FormItens", u"Ano:", None))
        self.lbl_ano_val.setText("")
        self.lbl_num.setText(QCoreApplication.translate("FormItens", u"N\u00ba Or\u00e7amento:", None))
        self.lbl_num_val.setText("")
        self.lbl_ver.setText(QCoreApplication.translate("FormItens", u"Vers\u00e3o:", None))
        self.lbl_ver_val.setText("")
        self.lbl_codigo.setText(QCoreApplication.translate("FormItens", u"C\u00f3digo", None))
        self.lbl_profundidade.setText(QCoreApplication.translate("FormItens", u"Profundidade", None))
        self.lbl_qt.setText(QCoreApplication.translate("FormItens", u"Qt", None))
        self.edit_qt.setPlaceholderText(QCoreApplication.translate("FormItens", u"1", None))
        self.lbl_item.setText(QCoreApplication.translate("FormItens", u"Item", None))
        self.lbl_und.setText(QCoreApplication.translate("FormItens", u"Und", None))
        self.edit_und.setText(QCoreApplication.translate("FormItens", u"und", None))
        self.lbl_altura.setText(QCoreApplication.translate("FormItens", u"Altura", None))
        self.edit_descricao.setPlaceholderText(QCoreApplication.translate("FormItens", u"Descri\u00e7\u00e3o do item...", None))
        self.lbl_descricao.setText(QCoreApplication.translate("FormItens", u"Descri\u00e7\u00e3o", None))
        self.lbl_largura.setText(QCoreApplication.translate("FormItens", u"Largura", None))
        self.btn_add.setText(QCoreApplication.translate("FormItens", u"Inserir Novo Item", None))
        self.btn_save.setText(QCoreApplication.translate("FormItens", u"Gravar Item", None))
        self.btn_del.setText(QCoreApplication.translate("FormItens", u"Eliminar Item", None))
        self.btn_expand.setText(QCoreApplication.translate("FormItens", u"Expandir", None))
        self.btn_collapse.setText(QCoreApplication.translate("FormItens", u"Colapsar", None))
        self.btn_up.setText(QCoreApplication.translate("FormItens", u"\u2191", None))
        self.btn_dn.setText(QCoreApplication.translate("FormItens", u"\u2193", None))
    # retranslateUi

