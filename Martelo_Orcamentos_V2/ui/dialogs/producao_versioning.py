from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt


class NovaVersaoProcessoDialog(QtWidgets.QDialog):
    def __init__(
        self,
        *,
        parent=None,
        versao_obra_sug_cutrite: str,
        versao_plano_sug_cutrite: str,
        versao_obra_sug_obra: str,
        versao_plano_sug_obra: str,
        existing_keys: set[tuple[str, str]],
        folder_root: str | None = None,
        folder_tree: dict[str, dict[str, list[str]]] | None = None,
        window_title: str | None = None,
        intro_text: str | None = None,
        label_sug_cutrite: str | None = None,
        label_sug_obra: str | None = None,
        tooltip_sug_cutrite: str | None = None,
        tooltip_sug_obra: str | None = None,
    ):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowTitle(window_title or "Nova Versao Processo")
        self.resize(820, 520)

        self._existing = {
            (self._norm_two_digits(vv), self._norm_two_digits(pp)) for vv, pp in (existing_keys or set())
        }
        self._folder_root = str(folder_root or "").strip()
        self._folder_tree = folder_tree or {}
        self._result: Optional[tuple[str, str]] = None
        self._blink_state = False

        layout = QtWidgets.QVBoxLayout(self)

        intro = QtWidgets.QLabel(
            intro_text
            or "Cria uma nova versao mantendo os dados atuais.\n"
            "Confirme as versoes para evitar duplicados."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        sug_row = QtWidgets.QHBoxLayout()
        self.btn_sug_cutrite = QtWidgets.QPushButton(label_sug_cutrite or "Sugestao CUT-RITE")
        self.btn_sug_cutrite.setToolTip(
            tooltip_sug_cutrite or "Mantem a Versao Obra e incrementa a Versao CutRite."
        )
        self.btn_sug_obra = QtWidgets.QPushButton(label_sug_obra or "Sugestao Obra")
        self.btn_sug_obra.setToolTip(
            tooltip_sug_obra or "Incrementa a Versao Obra e sugere Versao CutRite=01."
        )
        sug_row.addWidget(self.btn_sug_cutrite)
        sug_row.addWidget(self.btn_sug_obra)
        sug_row.addStretch(1)
        layout.addLayout(sug_row)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(Qt.AlignRight)
        self.ed_ver_obra = QtWidgets.QLineEdit()
        self.ed_ver_plano = QtWidgets.QLineEdit()
        for ed in (self.ed_ver_obra, self.ed_ver_plano):
            ed.setMaxLength(2)
            ed.setFixedWidth(60)
            ed.setAlignment(Qt.AlignCenter)
            ed.setValidator(QtGui.QIntValidator(1, 99, self))
        self.ed_ver_obra.setToolTip("Versao Obra (VV) - 2 digitos (01..99).")
        self.ed_ver_plano.setToolTip("Versao CutRite (PP) - 2 digitos (01..99).")
        form.addRow("Versao Obra:", self.ed_ver_obra)
        form.addRow("Versao CutRite:", self.ed_ver_plano)
        layout.addLayout(form)

        self.lbl_status = QtWidgets.QLabel("")
        self.lbl_status.setStyleSheet("color:#b00020;")
        layout.addWidget(self.lbl_status)

        grp = QtWidgets.QGroupBox("Pastas existentes (Servidor)")
        grp_layout = QtWidgets.QVBoxLayout(grp)
        if self._folder_root:
            lbl_root = QtWidgets.QLabel(self._folder_root)
            lbl_root.setTextInteractionFlags(Qt.TextSelectableByMouse)
            lbl_root.setStyleSheet("color:#555;")
            grp_layout.addWidget(lbl_root)

        self.tree = QtWidgets.QTreeWidget(grp)
        self.tree.setHeaderHidden(True)
        self.tree.setAlternatingRowColors(True)
        grp_layout.addWidget(self.tree, 1)
        layout.addWidget(grp, 1)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._sug_cutrite = (
            self._norm_two_digits(versao_obra_sug_cutrite),
            self._norm_two_digits(versao_plano_sug_cutrite),
        )
        self._sug_obra = (
            self._norm_two_digits(versao_obra_sug_obra),
            self._norm_two_digits(versao_plano_sug_obra),
        )

        self.btn_sug_cutrite.clicked.connect(lambda: self._apply(self._sug_cutrite))
        self.btn_sug_obra.clicked.connect(lambda: self._apply(self._sug_obra))
        self.ed_ver_obra.textChanged.connect(self._refresh_status)
        self.ed_ver_plano.textChanged.connect(self._refresh_status)
        self.ed_ver_obra.editingFinished.connect(self._format_inputs)
        self.ed_ver_plano.editingFinished.connect(self._format_inputs)

        self._apply(self._sug_cutrite)
        self._populate_tree()
        self._start_blink()

    @staticmethod
    def _norm_two_digits(value: str) -> str:
        text = str(value or "").strip()
        if text.isdigit():
            return f"{int(text):02d}"
        return (text[:2] if len(text) >= 2 else text.zfill(2)) or "01"

    def _populate_tree(self) -> None:
        self.tree.clear()
        if not self._folder_tree:
            item = QtWidgets.QTreeWidgetItem(["(sem pastas encontradas)"])
            self.tree.addTopLevelItem(item)
            self.tree.expandAll()
            return

        for seg1, seg2_map in self._folder_tree.items():
            it1 = QtWidgets.QTreeWidgetItem([seg1])
            self.tree.addTopLevelItem(it1)
            for seg2, seg3_list in seg2_map.items():
                it2 = QtWidgets.QTreeWidgetItem([seg2])
                it1.addChild(it2)
                for seg3 in seg3_list:
                    it2.addChild(QtWidgets.QTreeWidgetItem([seg3]))

        try:
            self.tree.expandToDepth(1)
        except Exception:
            self.tree.expandAll()

    def _apply(self, values: tuple[str, str]) -> None:
        vv, pp = values
        self.ed_ver_obra.setText(self._norm_two_digits(vv))
        self.ed_ver_plano.setText(self._norm_two_digits(pp))
        self._refresh_status()

    def _format_inputs(self) -> None:
        self.ed_ver_obra.setText(self._norm_two_digits(self.ed_ver_obra.text()))
        self.ed_ver_plano.setText(self._norm_two_digits(self.ed_ver_plano.text()))

    def _refresh_status(self) -> None:
        vv = self._norm_two_digits(self.ed_ver_obra.text())
        pp = self._norm_two_digits(self.ed_ver_plano.text())
        if (vv, pp) in self._existing:
            self.lbl_status.setText("Ja existe um processo com esta versao (VV/PP).")
        else:
            self.lbl_status.setText("")

    def _on_accept(self) -> None:
        self._format_inputs()
        vv = self._norm_two_digits(self.ed_ver_obra.text())
        pp = self._norm_two_digits(self.ed_ver_plano.text())
        if (vv, pp) in self._existing:
            QtWidgets.QMessageBox.warning(self, "Duplicado", "Ja existe um processo com esta versao (VV/PP).")
            return
        self._result = (vv, pp)
        self.accept()

    def values(self) -> tuple[str, str]:
        return self._result or (
            self._norm_two_digits(self.ed_ver_obra.text()),
            self._norm_two_digits(self.ed_ver_plano.text()),
        )

    def _start_blink(self) -> None:
        self._blink_timer = QtCore.QTimer(self)
        self._blink_timer.timeout.connect(self._blink_tick)
        self._blink_timer.start(350)

    def _blink_tick(self) -> None:
        self._blink_state = not self._blink_state
        style = "background:#fff3cd; border:1px solid #f0ad4e;" if self._blink_state else ""
        self.ed_ver_obra.setStyleSheet(style)
        self.ed_ver_plano.setStyleSheet(style)

    def closeEvent(self, event):  # noqa: N802
        try:
            if hasattr(self, "_blink_timer") and self._blink_timer:
                self._blink_timer.stop()
        except Exception:
            pass
        super().closeEvent(event)


class PastasExistentesDialog(QtWidgets.QDialog):
    def __init__(
        self,
        *,
        parent=None,
        folder_root: str | None = None,
        folder_tree: dict[str, dict[str, list[str]]] | None = None,
        title_suffix: str | None = None,
    ):
        super().__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        title = "Pastas existentes (Servidor)"
        if title_suffix:
            title = f"{title} - {title_suffix}"
        self.setWindowTitle(title)
        self.resize(720, 520)

        self._folder_root = str(folder_root or "").strip()
        self._folder_tree = folder_tree or {}

        layout = QtWidgets.QVBoxLayout(self)

        if self._folder_root:
            lbl_root = QtWidgets.QLabel(self._folder_root)
            lbl_root.setTextInteractionFlags(Qt.TextSelectableByMouse)
            lbl_root.setStyleSheet("color:#555;")
            layout.addWidget(lbl_root)

        self.tree = QtWidgets.QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.setAlternatingRowColors(True)
        layout.addWidget(self.tree, 1)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self._populate_tree()

    def _populate_tree(self) -> None:
        self.tree.clear()
        if not self._folder_tree:
            item = QtWidgets.QTreeWidgetItem(["(sem pastas encontradas)"])
            self.tree.addTopLevelItem(item)
            try:
                self.tree.expandAll()
            except Exception:
                pass
            return

        for seg1, seg2_map in self._folder_tree.items():
            it1 = QtWidgets.QTreeWidgetItem([seg1])
            self.tree.addTopLevelItem(it1)
            for seg2, seg3_list in seg2_map.items():
                it2 = QtWidgets.QTreeWidgetItem([seg2])
                it1.addChild(it2)
                for seg3 in seg3_list:
                    it2.addChild(QtWidgets.QTreeWidgetItem([seg3]))

        try:
            self.tree.expandToDepth(1)
        except Exception:
            self.tree.expandAll()
