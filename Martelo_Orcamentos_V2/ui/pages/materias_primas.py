from __future__ import annotations

import os
import subprocess
import sys
from decimal import Decimal
from typing import List
from pathlib import Path  # <-- adicionar

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHeaderView, QMessageBox, QStyle

from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.services.materias_primas import (
    DEFAULT_MATERIAS_BASE_PATH,
    KEY_MATERIAS_BASE_PATH,
    get_all_columns,
    get_base_path,
    get_user_columns,
    import_materias_primas,
    list_materias_primas,
    set_user_columns,
)
from Martelo_Orcamentos_V2.app.services.settings import get_setting
from ..models.qt_table import SimpleTableModel


def _format_decimal(value, places: int = 2) -> str:
    if value in (None, ""):
        return ""
    try:
        dec = Decimal(str(value))
        return f"{dec:.{places}f}"
    except Exception:
        try:
            return f"{float(value):.{places}f}"
        except Exception:
            return str(value)


class ColumnSelectorDialog(QtWidgets.QDialog):
    def __init__(self, columns: List[str], selected: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Colunas visíveis")
        self.setModal(True)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Escolha as colunas que deseja visualizar:"))
        self.list = QtWidgets.QListWidget()
        self.list.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        for header in columns:
            item = QtWidgets.QListWidgetItem(header)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Checked if header in selected else QtCore.Qt.Unchecked)
            self.list.addItem(item)
        layout.addWidget(self.list)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_columns(self) -> List[str]:
        result: List[str] = []
        for index in range(self.list.count()):
            item = self.list.item(index)
            if item.checkState() == QtCore.Qt.Checked:
                result.append(item.text())
        return result


class MateriasPrimasPage(QtWidgets.QWidget):
    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self.current_user = current_user
        self.db = SessionLocal()
        self.columns_meta = list(get_all_columns())
        user_id = getattr(self.current_user, "id", None)
        self.visible_columns = get_user_columns(self.db, user_id)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self.refresh_table)

        style = self.style()

        header_widget = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Pesquisar matérias primas… use % para multi-termos")
        self.search_edit.textChanged.connect(self.on_search_text_changed)

        btn_open = QtWidgets.QPushButton("Abrir Excel")
        btn_open.setIcon(style.standardIcon(QStyle.SP_DialogOpenButton))
        btn_open.clicked.connect(self.on_open_excel)

        btn_refresh = QtWidgets.QPushButton("Atualizar Importação")
        btn_refresh.setIcon(style.standardIcon(QStyle.SP_BrowserReload))
        btn_refresh.clicked.connect(self.on_import_excel)

        btn_columns = QtWidgets.QPushButton("Colunas…")
        btn_columns.setIcon(style.standardIcon(QStyle.SP_FileDialogDetailedView))
        btn_columns.clicked.connect(self.on_choose_columns)

        self.lbl_path = QtWidgets.QLabel(self._current_excel_path())
        self.lbl_path.setStyleSheet("color: #555;")
        self.lbl_path.setTextInteractionFlags(Qt.TextSelectableByMouse)

        header_layout.addWidget(QtWidgets.QLabel("Pesquisa:"))
        header_layout.addWidget(self.search_edit, 1)
        header_layout.addWidget(btn_open)
        header_layout.addWidget(btn_refresh)
        header_layout.addWidget(btn_columns)
        header_layout.addWidget(self.lbl_path, 1)

        model_columns = []
        for col in self.columns_meta:
            formatter = _format_decimal if col.kind == "numeric" else None
            model_columns.append((col.header, col.attr, formatter))

        self.model = SimpleTableModel(columns=model_columns)

        self.table = QtWidgets.QTableView(self)
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self._show_readonly_message)
        self.table.setWordWrap(True)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)
        header_font = header.font()
        header_font.setBold(True)
        header.setFont(header_font)

        self.column_widths = {
            "ID_MP": 90,
            "REF_PHC": 100,
            "REF_FORNECEDOR": 120,
            "Ref_LE": 100,
            "DESCRICAO_do_PHC": 220,
            "DESCRICAO_no_ORCAMENTO": 260,
            "PRECO_TABELA": 110,
            "MARGEM": 90,
            "DESCONTO": 90,
            "PLIQ": 110,
            "UND": 60,
            "DESP": 80,
            "COMP_MP": 100,
            "LARG_MP": 100,
            "ESP_MP": 100,
            "TIPO": 110,
            "FAMILIA": 120,
            "COR": 100,
            "ORL_0.4": 90,
            "ORL_1.0": 90,
            "COR_REF_MATERIAL": 140,
            "NOME_FORNECEDOR": 160,
            "NOME_FABRICANTE": 160,
            "DATA_ULTIMO_PRECO": 140,
            "APLICACAO": 130,
            "STOCK": 90,
            "NOTAS_2": 160,
            "NOTAS_3": 160,
            "NOTAS_4": 160,
        }
        for index, column in enumerate(self.columns_meta):
            width = self.column_widths.get(column.header)
            if width:
                header.resizeSection(index, width)

        self.table.verticalHeader().setDefaultSectionSize(24)
        self.table.setFocusPolicy(Qt.NoFocus)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)
        layout.addWidget(header_widget)
        layout.addWidget(self.table, 1)

        self.refresh_table()

    def _current_excel_path(self) -> str:
        try:
            base = get_base_path(self.db)
        except Exception:
            base = DEFAULT_MATERIAS_BASE_PATH
        return str(Path(base) / MATERIA_PRIMA_FILENAME)

    def on_search_text_changed(self, _text: str) -> None:
        self._search_timer.start(300)

    def refresh_table(self) -> None:
        rows = list_materias_primas(self.db, self.search_edit.text())
        self.model.set_rows(rows)
        self._apply_column_visibility()

    def _apply_column_visibility(self) -> None:
        header_names = [col.header for col in self.columns_meta]
        for index, header in enumerate(header_names):
            self.table.setColumnHidden(index, header not in self.visible_columns)

    def on_import_excel(self) -> None:
        try:
            inserted = import_materias_primas(self.db)
            self.db.commit()
            QMessageBox.information(self, "Concluído", f"Tabela atualizada com {inserted} registos.")
            self.lbl_path.setText(self._current_excel_path())
            self.refresh_table()
        except Exception as exc:
            self.db.rollback()
            QMessageBox.critical(self, "Erro", f"Falha ao importar dados: {exc}")

    def on_open_excel(self) -> None:
        path = Path(self._current_excel_path())
        if not path.exists():
            QMessageBox.warning(self, "Aviso", f"Ficheiro não encontrado:\n{path}")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            QMessageBox.critical(self, "Erro", f"Não foi possível abrir o ficheiro:\n{exc}")

    def on_choose_columns(self) -> None:
        headers = [col.header for col in self.columns_meta]
        dialog = ColumnSelectorDialog(headers, list(self.visible_columns), self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            selected = dialog.selected_columns()
            if not selected:
                QMessageBox.information(self, "Informação", "Selecione pelo menos uma coluna.")
                return
            self.visible_columns = selected
            user_id = getattr(self.current_user, "id", None)
            if user_id:
                try:
                    set_user_columns(self.db, user_id, self.visible_columns)
                    self.db.commit()
                except Exception as exc:
                    self.db.rollback()
                    QMessageBox.warning(self, "Aviso", f"Não foi possível gravar preferências: {exc}")
            self._apply_column_visibility()

    def _show_readonly_message(self) -> None:
        QMessageBox.information(
            self,
            "Informação",
            "A tabela de matérias primas é apenas para consulta.\n"
            "Atualize os dados editando o ficheiro Excel e carregando novamente."
        )

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        try:
            self.db.close()
        finally:
            super().closeEvent(event)


MATERIA_PRIMA_FILENAME = "TAB_MATERIAS_PRIMAS.xlsm"





