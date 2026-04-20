from __future__ import annotations

import logging
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from Martelo_Orcamentos_V2.app.services import feature_flags as svc_features
from Martelo_Orcamentos_V2.app.services import producao_preparacao as svc_producao_preparacao
from Martelo_Orcamentos_V2.ui.dialogs.lista_material_audit import ListaMaterialAuditDialog

logger = logging.getLogger(__name__)


class PreparacaoPreferencesDialog(QtWidgets.QDialog):
    def __init__(self, *, db_session, current_user_id: Optional[int], parent=None) -> None:
        super().__init__(parent)
        self.db = db_session
        self.current_user_id = current_user_id
        self.setWindowTitle("Preferencias da Preparacao")
        self.resize(560, 460)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        info = QtWidgets.QLabel(
            "Escolha as validacoes deste utilizador que devem aparecer no painel de Preparacao de Producao.\n"
            "As validacoes dos programas CNC mantem-se sempre visiveis e obrigatorias."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.list_widget = QtWidgets.QListWidget(self)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        layout.addWidget(self.list_widget, 1)

        self._load_options()

        row = QtWidgets.QHBoxLayout()
        self.btn_all = QtWidgets.QPushButton("Selecionar tudo", self)
        self.btn_all.clicked.connect(lambda: self._set_all(QtCore.Qt.Checked))
        self.btn_none = QtWidgets.QPushButton("Limpar", self)
        self.btn_none.clicked.connect(lambda: self._set_all(QtCore.Qt.Unchecked))
        row.addWidget(self.btn_all)
        row.addWidget(self.btn_none)
        row.addStretch(1)
        layout.addLayout(row)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if not self.current_user_id:
            self.list_widget.setEnabled(False)
            self.btn_all.setEnabled(False)
            self.btn_none.setEnabled(False)
            info.setText(
                "Nao foi possivel identificar o utilizador atual. As preferencias por utilizador nao podem ser gravadas."
            )

    def _load_options(self) -> None:
        selected = svc_producao_preparacao.get_preparacao_required_file_keys(self.db, self.current_user_id)
        for option in svc_producao_preparacao.list_configurable_preparacao_file_options():
            item = QtWidgets.QListWidgetItem(option["label"])
            item.setData(QtCore.Qt.UserRole, option["key"])
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Checked if option["key"] in selected else QtCore.Qt.Unchecked)
            self.list_widget.addItem(item)

    def _set_all(self, state: QtCore.Qt.CheckState) -> None:
        for row in range(self.list_widget.count()):
            self.list_widget.item(row).setCheckState(state)

    def _selected_keys(self) -> list[str]:
        keys: list[str] = []
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if item.checkState() == QtCore.Qt.Checked:
                keys.append(str(item.data(QtCore.Qt.UserRole) or "").strip())
        return keys

    def _on_accept(self) -> None:
        if not self.current_user_id:
            self.accept()
            return
        try:
            svc_producao_preparacao.set_preparacao_required_file_keys(
                self.db,
                int(self.current_user_id),
                self._selected_keys(),
            )
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(
                self,
                "Preferencias",
                f"Nao foi possivel gravar as preferencias de preparacao.\n\nDetalhe: {exc}",
            )
            return
        self.accept()


class ProducaoPreparacaoDialog(QtWidgets.QDialog):
    def __init__(
        self,
        *,
        db_session,
        current_id: Optional[int],
        pasta_servidor: str,
        nome_enc_imos: str,
        nome_plano_cut_rite: str,
        current_user_id: Optional[int] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.db = db_session
        self.current_id = current_id
        self.pasta_servidor = pasta_servidor
        self.nome_enc_imos = nome_enc_imos
        self.nome_plano_cut_rite = nome_plano_cut_rite
        self.current_user_id = current_user_id
        self.context: Optional[svc_producao_preparacao.ProducaoPreparacaoContext] = None
        self.statuses: list[svc_producao_preparacao.ProducaoPreparacaoStatus] = []
        self.required_keys: set[str] = set()
        self._lista_material_audit_enabled = svc_features.has_feature(
            self.db,
            self.current_user_id,
            svc_features.FEATURE_LISTA_MATERIAL_AUDIT,
        )

        self.setWindowTitle("Preparacao de Producao")
        self.resize(1560, 980)
        self.setMinimumSize(1420, 880)

        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        intro = QtWidgets.QLabel(
            "Painel de preparacao da obra para Producao.\n"
            "Permite validar o que ja foi feito e executar passos operacionais da pasta da obra."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        context_group = QtWidgets.QGroupBox("Contexto", self)
        context_layout = QtWidgets.QFormLayout(context_group)
        self.lbl_context_processo = QtWidgets.QLabel("-")
        self.lbl_context_pasta = QtWidgets.QLabel("-")
        self.lbl_context_nome_enc = QtWidgets.QLabel("-")
        self.lbl_context_plano = QtWidgets.QLabel("-")
        for widget in (
            self.lbl_context_processo,
            self.lbl_context_pasta,
            self.lbl_context_nome_enc,
            self.lbl_context_plano,
        ):
            widget.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            widget.setWordWrap(True)
        context_layout.addRow("Processo:", self.lbl_context_processo)
        context_layout.addRow("Pasta da obra:", self.lbl_context_pasta)
        context_layout.addRow("Nome Enc IMOS IX:", self.lbl_context_nome_enc)
        context_layout.addRow("Nome Plano CUT-RITE:", self.lbl_context_plano)
        layout.addWidget(context_group)

        self.lbl_summary = QtWidgets.QLabel(self)
        self.lbl_summary.setWordWrap(True)
        layout.addWidget(self.lbl_summary)

        self.tbl_status = QtWidgets.QTableWidget(self)
        self.tbl_status.setColumnCount(4)
        self.tbl_status.setHorizontalHeaderLabels(["Acao", "Validacao", "Estado", "Detalhe"])
        self.tbl_status.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tbl_status.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl_status.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tbl_status.setAlternatingRowColors(True)
        self.tbl_status.setWordWrap(True)
        self.tbl_status.verticalHeader().setVisible(False)
        header = self.tbl_status.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        layout.addWidget(self.tbl_status, 1)

        buttons = QtWidgets.QHBoxLayout()
        self.btn_refresh = QtWidgets.QPushButton("Atualizar", self)
        self.btn_refresh.clicked.connect(self._refresh)
        self.btn_lista_material_audit = QtWidgets.QPushButton("Auditar Lista Material...", self)
        self.btn_lista_material_audit.clicked.connect(self._open_lista_material_audit)
        self.btn_lista_material_audit.setVisible(self._lista_material_audit_enabled)
        self.btn_preferences = QtWidgets.QPushButton("Preferencias...", self)
        self.btn_preferences.clicked.connect(self._open_preferences)
        self.btn_preferences.setEnabled(bool(self.current_user_id))
        self.btn_close = QtWidgets.QPushButton("Fechar", self)
        self.btn_close.clicked.connect(self.accept)
        buttons.addWidget(self.btn_refresh)
        if self._lista_material_audit_enabled:
            buttons.addWidget(self.btn_lista_material_audit)
        buttons.addWidget(self.btn_preferences)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_close)
        layout.addLayout(buttons)

    def _refresh(self) -> None:
        self.required_keys = svc_producao_preparacao.get_required_preparacao_keys(self.db, self.current_user_id)
        self.context = svc_producao_preparacao.resolve_preparacao_context(
            self.db,
            current_id=self.current_id,
            pasta_servidor=self.pasta_servidor,
            nome_enc_imos=self.nome_enc_imos,
            nome_plano_cut_rite=self.nome_plano_cut_rite,
        )
        self.statuses = svc_producao_preparacao.collect_preparacao_statuses(
            self.context,
            required_keys=self.required_keys,
        )
        self._render_context()
        self._render_summary()
        self._render_statuses()

    def _render_context(self) -> None:
        if self.context is None:
            return
        processo_label = (
            str(getattr(self.context.processo, "codigo_processo", "") or "").strip()
            or str(getattr(self.context.processo, "id", "") or "").strip()
            or "-"
        )
        self.lbl_context_processo.setText(processo_label)
        self.lbl_context_pasta.setText(str(self.context.work_folder))
        self.lbl_context_nome_enc.setText(self.context.nome_enc_imos or "-")
        self.lbl_context_plano.setText(self.context.nome_plano_cut_rite or "-")

    def _render_summary(self) -> None:
        required_pending = [
            status.label
            for status in self.statuses
            if status.key != "obra_pronta" and status.required and not status.ok
        ]

        if required_pending:
            text = "Pendencias obrigatorias atuais:\n- " + "\n- ".join(required_pending)
        else:
            text = "Sem pendencias obrigatorias detetadas nesta preparacao."
        self.lbl_summary.setText(text)

    def _render_statuses(self) -> None:
        self.tbl_status.setRowCount(len(self.statuses))
        for row, status in enumerate(self.statuses):
            self.tbl_status.setCellWidget(row, 0, self._build_action_widget(status))

            label_item = QtWidgets.QTableWidgetItem(status.label)
            label_item.setToolTip(self._validation_tooltip(status))

            state_item = QtWidgets.QTableWidgetItem(self._state_text(status))
            state_item.setIcon(self._state_icon(status))
            state_item.setForeground(self._state_brush(status))

            detail_item = QtWidgets.QTableWidgetItem(status.detail)
            detail_item.setToolTip(status.detail)

            self.tbl_status.setItem(row, 1, label_item)
            self.tbl_status.setItem(row, 2, state_item)
            self.tbl_status.setItem(row, 3, detail_item)
            self.tbl_status.setRowHeight(row, 46)

    def _build_action_widget(
        self,
        status: svc_producao_preparacao.ProducaoPreparacaoStatus,
    ) -> QtWidgets.QWidget:
        container = QtWidgets.QWidget(self.tbl_status)
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        if status.action_key:
            check = QtWidgets.QCheckBox(container)
            check.setToolTip(status.action_label or "Executar")
            check.stateChanged.connect(
                lambda state, action_key=status.action_key, action_label=status.action_label, checkbox=check: self._on_action_checked(
                    checkbox,
                    action_key,
                    action_label or "Executar",
                    state,
                )
            )
            layout.addWidget(check)
        return container

    def _validation_tooltip(
        self,
        status: svc_producao_preparacao.ProducaoPreparacaoStatus,
    ) -> str:
        descriptions = {
            "caderno_encargos": "Valida se existe o Excel Caderno de Encargos (*.xlsm) e prepara-o automaticamente com a imagem do IMOS no separador CD&RP.",
            "lista_material_pdf": "Valida apenas se existe na pasta da obra o ficheiro Lista_Material_*.pdf.",
            "ferragens_a4_pdf": "Valida se existe o PDF 1_List_FerragensA4.pdf na pasta da obra.",
            "projeto_pdf": "Valida se o ficheiro 2_Projeto_Producao.pdf foi gerado a partir do CONJ.pdf em formato A4 horizontal.",
            "resumo_geral_pdf": "Valida se existe o PDF 3_Resumo_Geral_Encomenda.pdf na pasta da obra.",
            "etiqueta_palete_pdf": "Valida se existe o PDF 5_Etiqueta_Palete.pdf na pasta da obra.",
            "resumo_ml_orlas_pdf": "Valida se existe o PDF 6_Resumo_ML_OrlasA4.pdf na pasta da obra.",
            "cutrite_pdf": "Valida se existe na pasta da obra o PDF exportado do plano CUT-RITE com o nome definido no campo 'Nome Plano CUT-RITE'.",
            "conj_pdf": "Valida se existe o ficheiro CONJ.pdf na pasta da obra.",
            "cnc_source": "Valida se a pasta de programas CNC existe na origem IMOS e mostra a quantidade de ficheiros encontrada.",
            "cnc_work": "Valida se os programas CNC ja foram copiados para a pasta da obra e se estao atualizados face a origem IMOS.",
            "mpr_year": "Valida se a pasta anual de destino dos programas CNC para as maquinas esta disponivel na rede.",
            "mpr_sent": "Valida se os programas CNC da obra ja foram enviados para a pasta MPR e se estao atualizados face a pasta da obra.",
            "obra_pronta": "Resumo final da preparacao. A obra fica pronta quando todas as validacoes obrigatorias estiverem OK.",
        }
        details = [descriptions.get(status.key, status.label)]
        details.append("Obrigatorio." if status.required else "Opcional para este utilizador.")
        if status.action_key:
            action_text = status.action_label or "Executar"
            details.append(f"Marque a coluna Acao para {action_text.lower()} este passo.")
        return "\n".join(details)

    def _state_text(self, status: svc_producao_preparacao.ProducaoPreparacaoStatus) -> str:
        if status.state == svc_producao_preparacao.STATUS_OK:
            return "OK"
        if status.state == svc_producao_preparacao.STATUS_MISSING:
            return "Pendente"
        if status.state == svc_producao_preparacao.STATUS_OUTDATED:
            return "Desatualizado"
        return "Bloqueado"

    def _state_icon(self, status: svc_producao_preparacao.ProducaoPreparacaoStatus) -> QtGui.QIcon:
        style = self.style()
        if status.state == svc_producao_preparacao.STATUS_OK:
            return style.standardIcon(QtWidgets.QStyle.SP_DialogApplyButton)
        if status.state == svc_producao_preparacao.STATUS_OUTDATED:
            return style.standardIcon(QtWidgets.QStyle.SP_MessageBoxWarning)
        if status.state == svc_producao_preparacao.STATUS_MISSING:
            return style.standardIcon(QtWidgets.QStyle.SP_MessageBoxWarning)
        return style.standardIcon(QtWidgets.QStyle.SP_MessageBoxCritical)

    def _state_brush(self, status: svc_producao_preparacao.ProducaoPreparacaoStatus) -> QtGui.QBrush:
        if status.state == svc_producao_preparacao.STATUS_OK:
            return QtGui.QBrush(QtGui.QColor("#2E7D32"))
        if status.state == svc_producao_preparacao.STATUS_OUTDATED:
            return QtGui.QBrush(QtGui.QColor("#B36B00"))
        if status.state == svc_producao_preparacao.STATUS_MISSING:
            return QtGui.QBrush(QtGui.QColor("#B36B00"))
        return QtGui.QBrush(QtGui.QColor("#C62828"))

    def _on_action_checked(
        self,
        checkbox: QtWidgets.QCheckBox,
        action_key: str,
        action_label: str,
        state,
    ) -> None:
        current_state = getattr(state, "value", state)
        checked_state = getattr(QtCore.Qt.CheckState.Checked, "value", QtCore.Qt.CheckState.Checked)
        if current_state != checked_state:
            return
        if self.context is None:
            checkbox.blockSignals(True)
            checkbox.setChecked(False)
            checkbox.blockSignals(False)
            return

        try:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            QtWidgets.QApplication.processEvents()
            if action_key == svc_producao_preparacao.ACTION_GENERATE_PROJETO_PDF:
                path = svc_producao_preparacao.generate_projeto_producao_pdf(self.context)
                message = f"PDF gerado com sucesso.\n\n{path}"
            elif action_key == svc_producao_preparacao.ACTION_COPY_CUTRITE_PDF_TO_WORK:
                path = svc_producao_preparacao.copy_cutrite_pdf_para_obra(self.context)
                message = f"PDF do plano CUT-RITE copiado para a pasta da obra.\n\n{path}"
            elif action_key == svc_producao_preparacao.ACTION_COPY_PROGRAMS_TO_WORK:
                path = svc_producao_preparacao.copy_programas_para_obra(self.context)
                message = f"Programas CNC copiados para a obra.\n\n{path}"
            elif action_key == svc_producao_preparacao.ACTION_SEND_PROGRAMS_TO_MPR:
                path = svc_producao_preparacao.send_programas_para_mpr(self.context)
                message = f"Programas CNC enviados para CNC.\n\n{path}"
            else:
                raise RuntimeError(f"Acao de preparacao desconhecida: {action_key}")
            QtWidgets.QMessageBox.information(self, "Preparacao", message)
        except Exception as exc:
            logger.exception("Falha na acao de preparacao '%s': %s", action_key, exc)
            QtWidgets.QMessageBox.critical(
                self,
                "Preparacao",
                f"Nao foi possivel executar '{action_label}'.\n\nDetalhe: {exc}",
            )
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
            checkbox.blockSignals(True)
            checkbox.setChecked(False)
            checkbox.blockSignals(False)
            self._refresh()

    def _open_preferences(self) -> None:
        dialog = PreparacaoPreferencesDialog(
            db_session=self.db,
            current_user_id=self.current_user_id,
            parent=self,
        )
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            self._refresh()

    def _open_lista_material_audit(self) -> None:
        dialog = ListaMaterialAuditDialog(
            db_session=self.db,
            work_folder=str(self.context.work_folder if self.context is not None else self.pasta_servidor),
            nome_enc_imos=self.nome_enc_imos,
            parent=self,
        )
        dialog.exec()
