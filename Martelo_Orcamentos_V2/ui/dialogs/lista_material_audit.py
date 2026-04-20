from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtWidgets

from Martelo_Orcamentos_V2.app.services import producao_lista_material_audit as svc_audit

logger = logging.getLogger(__name__)


class ListaMaterialAuditDialog(QtWidgets.QDialog):
    CATEGORY_TITLES = {
        "estrutura": "Estrutura",
        "notas": "Notas",
        "materiais": "Materiais",
        "uniformizacao": "Uniformizacao",
        "orlas": "Orlas",
    }

    def __init__(
        self,
        *,
        db_session,
        work_folder: str,
        nome_enc_imos: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.db = db_session
        self.work_folder = str(work_folder or "").strip()
        self.nome_enc_imos = str(nome_enc_imos or "").strip()
        self.audit_result: Optional[svc_audit.AuditResult] = None
        self.config_root = svc_audit.resolve_config_root(self.db)
        self._tables: dict[str, QtWidgets.QTableWidget] = {}

        self.setWindowTitle("Auditoria Lista Material")
        self.resize(1440, 920)
        self.setMinimumSize(1240, 760)

        self._build_ui()
        self._prefill_workbook_path()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        intro = QtWidgets.QLabel(
            "Analise read-only do ficheiro Lista_Material_*.xlsm para detetar inconsistencias, variantes de notas, "
            "materiais e oportunidades de uniformizacao antes de enviar para producao / Cut Rite."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.lbl_config_root = QtWidgets.QLabel(f"Pasta configuracao externa: {self.config_root}")
        self.lbl_config_root.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.lbl_config_root.setWordWrap(True)
        layout.addWidget(self.lbl_config_root)

        file_row = QtWidgets.QHBoxLayout()
        self.ed_file = QtWidgets.QLineEdit(self)
        self.ed_file.setPlaceholderText("Escolha o ficheiro Lista_Material_*.xlsm")
        self.btn_choose = QtWidgets.QPushButton("Procurar...", self)
        self.btn_choose.clicked.connect(self._choose_file)
        self.btn_run = QtWidgets.QPushButton("Correr auditoria", self)
        self.btn_run.clicked.connect(self._run_audit)
        self.btn_export = QtWidgets.QPushButton("Exportar relatorio", self)
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self._export_report)
        self.btn_close = QtWidgets.QPushButton("Fechar", self)
        self.btn_close.clicked.connect(self.accept)
        file_row.addWidget(self.ed_file, 1)
        file_row.addWidget(self.btn_choose)
        file_row.addWidget(self.btn_run)
        file_row.addWidget(self.btn_export)
        file_row.addWidget(self.btn_close)
        layout.addLayout(file_row)

        filter_row = QtWidgets.QHBoxLayout()
        self.cb_severity = QtWidgets.QComboBox(self)
        self.cb_severity.addItem("Todas as severidades", "")
        self.cb_severity.addItem("Erro", "erro")
        self.cb_severity.addItem("Aviso", "aviso")
        self.cb_severity.addItem("Sugestao", "sugestao")
        self.cb_severity.addItem("Info", "info")
        self.cb_severity.currentIndexChanged.connect(self._render_result)
        self.cb_confidence = QtWidgets.QComboBox(self)
        self.cb_confidence.addItem("Todas as confiancas", "")
        self.cb_confidence.addItem("Alta", "high")
        self.cb_confidence.addItem("Media", "medium")
        self.cb_confidence.addItem("Baixa", "low")
        self.cb_confidence.currentIndexChanged.connect(self._render_result)
        filter_row.addWidget(QtWidgets.QLabel("Severidade:"))
        filter_row.addWidget(self.cb_severity)
        filter_row.addWidget(QtWidgets.QLabel("Confianca:"))
        filter_row.addWidget(self.cb_confidence)
        filter_row.addStretch(1)
        layout.addLayout(filter_row)

        self.tabs = QtWidgets.QTabWidget(self)
        self.txt_summary = QtWidgets.QTextEdit(self)
        self.txt_summary.setReadOnly(True)
        self.tabs.addTab(self.txt_summary, "Resumo")
        for category, title in self.CATEGORY_TITLES.items():
            table = QtWidgets.QTableWidget(self)
            table.setColumnCount(8)
            table.setHorizontalHeaderLabels(
                ["Severidade", "Confianca", "Regra", "Mensagem", "Sugestao", "Ocorrencias", "Linhas", "Exemplos"]
            )
            table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
            table.setAlternatingRowColors(True)
            table.verticalHeader().setVisible(False)
            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
            header.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
            header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(6, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(7, QtWidgets.QHeaderView.Stretch)
            self._tables[category] = table
            self.tabs.addTab(table, title)
        layout.addWidget(self.tabs, 1)

    def _prefill_workbook_path(self) -> None:
        if not self.work_folder:
            return
        try:
            path = svc_audit.resolve_workbook_for_audit(self.work_folder, nome_enc_imos=self.nome_enc_imos)
        except Exception:
            return
        self.ed_file.setText(str(path))

    def _choose_file(self) -> None:
        start_dir = self.work_folder or str(Path.home())
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Escolher Lista Material",
            start_dir,
            "Excel Lista Material (*.xlsm *.xlsx *.xls);;Todos os ficheiros (*.*)",
        )
        if file_path:
            self.ed_file.setText(file_path)

    def _run_audit(self) -> None:
        workbook_path = Path(self.ed_file.text().strip())
        if not workbook_path.is_file():
            QtWidgets.QMessageBox.warning(self, "Auditoria", "Escolha um ficheiro Excel valido.")
            return

        try:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            QtWidgets.QApplication.processEvents()
            self.config_root = svc_audit.resolve_config_root(self.db)
            self.audit_result = svc_audit.audit_lista_material_workbook(workbook_path, config_root=self.config_root)
        except Exception as exc:
            logger.exception("Falha na auditoria Lista Material: %s", exc)
            QtWidgets.QMessageBox.critical(
                self,
                "Auditoria",
                f"Nao foi possivel analisar o ficheiro.\n\nDetalhe: {exc}",
            )
            return
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

        self.lbl_config_root.setText(f"Pasta configuracao externa: {self.config_root}")
        self.btn_export.setEnabled(self.audit_result is not None)
        self._render_result()

    def _filtered_groups(self, category: str) -> list[svc_audit.IssueGroup]:
        if self.audit_result is None:
            return []
        severity_filter = str(self.cb_severity.currentData() or "").strip()
        confidence_filter = str(self.cb_confidence.currentData() or "").strip()
        groups = list(self.audit_result.groups_for_category(category))
        if severity_filter:
            groups = [group for group in groups if group.severity == severity_filter]
        if confidence_filter:
            groups = [group for group in groups if group.confidence == confidence_filter]
        return groups

    def _render_result(self) -> None:
        if self.audit_result is None:
            self.txt_summary.setPlainText("Execute a auditoria para ver o resultado.")
            for table in self._tables.values():
                table.setRowCount(0)
            return

        self.txt_summary.setPlainText(self._build_summary_text())
        for category, table in self._tables.items():
            groups = self._filtered_groups(category)
            table.setRowCount(len(groups))
            for row_index, group in enumerate(groups):
                values = [
                    group.severity,
                    group.confidence,
                    group.rule_id,
                    group.message,
                    group.suggestion,
                    str(group.occurrences),
                    ", ".join(str(value) for value in group.rows),
                    " | ".join(group.examples),
                ]
                for column_index, value in enumerate(values):
                    item = QtWidgets.QTableWidgetItem(value)
                    if column_index in (3, 4, 7):
                        item.setToolTip(value)
                    table.setItem(row_index, column_index, item)
                table.setRowHeight(row_index, 44)

    def _build_summary_text(self) -> str:
        assert self.audit_result is not None
        lines = [
            f"Ficheiro: {self.audit_result.source_path}",
            f"Folha: {self.audit_result.sheet_name}",
            f"Tabela: {self.audit_result.table_name or '<fallback cabecalho>'}",
            f"Fallback cabecalho: {'Sim' if self.audit_result.used_header_fallback else 'Nao'}",
            f"Linhas auditadas: {self.audit_result.total_rows}",
            f"Ocorrencias: {len(self.audit_result.issues)}",
            "",
            "Totais por severidade:",
            f"- erro: {self.audit_result.severity_totals.get('erro', 0)}",
            f"- aviso: {self.audit_result.severity_totals.get('aviso', 0)}",
            f"- sugestao: {self.audit_result.severity_totals.get('sugestao', 0)}",
            f"- info: {self.audit_result.severity_totals.get('info', 0)}",
            "",
            "Totais por confianca:",
            f"- high: {self.audit_result.confidence_totals.get('high', 0)}",
            f"- medium: {self.audit_result.confidence_totals.get('medium', 0)}",
            f"- low: {self.audit_result.confidence_totals.get('low', 0)}",
            "",
            "Grupos por categoria:",
        ]
        for category, title in self.CATEGORY_TITLES.items():
            lines.append(f"- {title}: {len(self._filtered_groups(category))}")
        return "\n".join(lines)

    def _export_report(self) -> None:
        if self.audit_result is None:
            return
        default_dir = str(self.audit_result.source_path.parent)
        default_name = f"{self.audit_result.source_path.stem}_auditoria.xlsx"
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Exportar relatorio auditoria",
            str(Path(default_dir) / default_name),
            "Excel (*.xlsx)",
        )
        if not file_path:
            return
        try:
            output_path = svc_audit.export_audit_report(self.audit_result, Path(file_path))
        except Exception as exc:
            logger.exception("Falha ao exportar relatorio da auditoria: %s", exc)
            QtWidgets.QMessageBox.critical(
                self,
                "Auditoria",
                f"Nao foi possivel exportar o relatorio.\n\nDetalhe: {exc}",
            )
            return
        QtWidgets.QMessageBox.information(self, "Auditoria", f"Relatorio exportado:\n{output_path}")
