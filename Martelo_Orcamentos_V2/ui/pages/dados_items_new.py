from typing import Any, Dict, List, Optional
from PySide6 import QtWidgets
from PySide6.QtCore import Qt

from ..widgets.dados_table_view import DadosTableView
from ...app.services import dados_materiais

class DadosItemsPage(QtWidgets.QWidget):
    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self.current_user = current_user
        self.context = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # Tabela de Materiais
        group_materiais = QtWidgets.QGroupBox("Materiais")
        group_layout = QtWidgets.QVBoxLayout()
        group_materiais.setLayout(group_layout)

        self.materiais_table = DadosTableView(self)
        self.materiais_table.setup_columns([
            {"field": "ref_le", "label": "Ref LE", "width": 100, "editable": True},
            {"field": "descricao", "label": "Descrição", "width": 200, "editable": True},
            {"field": "ptab", "label": "P.Tab", "width": 100, "editable": True},
            {"field": "pliq", "label": "P.Liq", "width": 100, "editable": True},
            {"field": "nao_stock", "label": "Não Stock", "width": 80, "type": "bool"},
        ])
        group_layout.addWidget(self.materiais_table)

        buttons_layout = QtWidgets.QHBoxLayout()
        self.btn_save = QtWidgets.QPushButton("Guardar")
        self.btn_save.clicked.connect(self._on_save)
        buttons_layout.addWidget(self.btn_save)
        buttons_layout.addStretch()

        layout.addWidget(group_materiais)
        layout.addLayout(buttons_layout)

    def load_data(self, db_session, orcamento_id: int):
        self.context = {"orcamento_id": orcamento_id}
        dados = dados_materiais.load_dados_materiais(db_session, self.context)
        self.materiais_table.load_data(dados)

    def _on_save(self):
        if not self.context:
            return
        
        dados = self.materiais_table.get_data()
        dados_materiais.save_dados_materiais(self.session, dados, self.context)
        QtWidgets.QMessageBox.information(self, "Sucesso", "Dados guardados com sucesso.")