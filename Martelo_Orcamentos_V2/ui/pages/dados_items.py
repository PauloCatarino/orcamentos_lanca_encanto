from __future__ import annotations

from functools import partial
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from PySide6 import QtCore, QtWidgets

from Martelo_Orcamentos_V2.app.models import OrcamentoItem
from sqlalchemy.orm import Session
from Martelo_Orcamentos_V2.app.services import dados_items as svc_di
from Martelo_Orcamentos_V2.app.services import dados_gerais as svc_dg

from .dados_gerais import DadosGeraisPage, PREVIEW_COLUMNS, _format_preview_value


def _extract_rows_from_payload(
    origin: str,
    payload: Optional[Mapping[str, Any]],
    menu: str,
) -> List[Dict[str, Any]]:
    rows: Sequence[Mapping[str, Any]] = []

    if not payload:
        return []

    if origin == "global":
        candidate = payload.get("linhas")
        if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes)):
            rows = [row for row in candidate if isinstance(row, Mapping)]
        else:
            candidate = payload.get(menu)
            if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes)):
                rows = [row for row in candidate if isinstance(row, Mapping)]
    else:
        candidate = payload.get(menu, [])
        if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes)):
            rows = [row for row in candidate if isinstance(row, Mapping)]

    return [dict(row) for row in rows]


class DadosItemsPage(DadosGeraisPage):
    def __init__(self, parent=None, current_user=None):
        super().__init__(
            parent=parent,
            current_user=current_user,
            svc_module=svc_di,
            page_title="Dados Items",
            save_button_text="Guardar Dados Items",
            import_button_text="Importar Dados Items",
            import_multi_button_text="Importar Multi Dados Items",
        )
        self.current_orcamento_id: Optional[int] = None
        self.current_item_id: Optional[int] = None

    # ------------------------------------------------------------------ Integration
    def load_item(self, orcamento_id: int, item_id: Optional[int]) -> None:
        self.current_orcamento_id = orcamento_id
        self.current_item_id = item_id

        if not item_id:
            self.context = None
            self._reset_tables()
            self.lbl_title.setText(self.page_title)
            self._update_dimensions_labels(visible=False)
            return

        try:
            super().load_orcamento(orcamento_id, item_id=item_id)
        except Exception as exc:  # pragma: no cover - UI feedback
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar Dados Items: {exc}")
            self._reset_tables()
            self._update_dimensions_labels(visible=False)
            return

        self._update_item_header(item_id)

    def _reset_tables(self) -> None:
        for model in self.models.values():
            model.load_rows([])
            model._reindex()

        self._update_dimensions_labels(visible=False)




    def _update_item_header(self, item_id: int) -> None:
        item: Optional[OrcamentoItem] = self.session.get(OrcamentoItem, item_id)
        if not item:
            self.lbl_title.setText(self.page_title)
            self._update_dimensions_labels(visible=False)
            return
        numero = getattr(item, "item_ord", None) or getattr(item, "item", None) or item_id
        descricao = (item.descricao or "").strip()
        if descricao:
            self.lbl_title.setText(f"{self.page_title} - Item {numero}: {descricao}")
        else:
            self.lbl_title.setText(f"{self.page_title} - Item {numero}")
        self._update_dimensions_labels(
            altura=getattr(item, "altura", None),
            largura=getattr(item, "largura", None),
            profundidade=getattr(item, "profundidade", None),
            visible=True,
        )

    def _post_table_setup(self, key: str) -> None:  # type: ignore[override]
        super()._post_table_setup(key)
        table = self.tables.get(key)
        model = self.models.get(key)
        if not table or not model:
            return
        for col_idx, spec in enumerate(model.columns):
            field = getattr(spec, "field", "") or ""
            if field.lower().startswith("reserva"):
                table.setColumnHidden(col_idx, True)

    # ------------------------------------------------------------------ Local models

    # ------------------------------------------------------------------ Local models
    def on_guardar_modelo(self, key: str) -> None:  # type: ignore[override]
        if not self.context:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhum item selecionado.")
            return

        linhas = self.models[key].export_rows()
        if not linhas:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nao existem linhas para guardar.")
            return

        nome, ok = QtWidgets.QInputDialog.getText(self, "Guardar Dados Items", "Nome do modelo:")
        if not ok:
            return
        nome = nome.strip()
        if not nome:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nome invalido.")
            return

        existentes = {
            modelo.nome_modelo: modelo
            for modelo in svc_di.listar_modelos(
                self.session,
                orcamento_id=self.context.orcamento_id,
                item_id=self.context.item_id,
            )
        }
        replace_id: Optional[int] = None
        if nome in existentes:
            resp = QtWidgets.QMessageBox.question(
                self,
                "Confirmar",
                "Ja existe um modelo com este nome. Pretende substitui-lo?",
            )
            if resp != QtWidgets.QMessageBox.StandardButton.Yes:
                return
            replace_id = existentes[nome].id

        try:
            payload = {key: linhas}
            svc_di.guardar_modelo(
                self.session,
                self.context,
                nome,
                payload,
                replace_model_id=replace_id,
            )
            QtWidgets.QMessageBox.information(self, "Sucesso", "Dados Items guardados.")
        except Exception as exc:  # pragma: no cover - UI feedback
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao guardar: {exc}")

    def on_importar_modelo(self, key: str) -> None:  # type: ignore[override]
        if not self.context:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhum item selecionado.")
            return

        dialog = ImportarDadosItemsDialog(
            session=self.session,
            context=self.context,
            tipo_menu=key,
            current_user=self.current_user,
            parent=self,
        )
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return

        rows = dialog.selected_rows()
        if not rows:
            return

        replace = dialog.replace_existing()

        self._apply_imported_rows(key, rows, replace=replace)

    def _extract_rows_for_import(
        self,
        origin: str,
        linhas_por_menu: Mapping[str, Sequence[Mapping[str, Any]]],
        menu: str,
    ) -> List[Dict[str, Any]]:
        return _extract_rows_from_payload(origin, linhas_por_menu, menu)

    def on_importar_multi_modelos(self) -> None:  # type: ignore[override]
        if not self.context:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhum item selecionado.")
            return

        dialog = ImportarMultiDadosItemsDialog(
            session=self.session,
            context=self.context,
            current_user=self.current_user,
            parent=self,
        )
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return

        selections = dialog.selected_models()
        if not selections:
            return

        user_id = getattr(self.current_user, "id", None)
        for menu, info in selections.items():
            origin, model_id, replace = info

            try:
                if origin == "local":
                    linhas_por_menu = svc_di.carregar_modelo(self.session, model_id)
                else:
                    linhas_por_menu = svc_dg.carregar_modelo(self.session, model_id, user_id=user_id)
            except Exception as exc:  # pragma: no cover
                QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao importar {menu}: {exc}")
                continue

            linhas = self._extract_rows_for_import(origin, linhas_por_menu, menu)
            self._apply_imported_rows(menu, linhas, replace=replace)

class ImportarDadosItemsDialog(QtWidgets.QDialog):
    ORIGINS: Tuple[str, str] = ("local", "global")

    def __init__(
        self,
        session: Session,
        context: svc_di.DadosItemsContext,
        tipo_menu: str,
        current_user=None,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent)
        self.session = session
        self.context = context
        self.tipo_menu = tipo_menu
        self.current_user = current_user

        self._selected_source: Optional[Tuple[str, int]] = None
        self._selected_rows: List[Dict[str, Any]] = []

        self.setWindowTitle("Importar Dados Items")
        self.resize(1100, 650)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.tabs = QtWidgets.QTabWidget(self)
        layout.addWidget(self.tabs, 1)

        self.models: Dict[str, List[Any]] = {origin: [] for origin in self.ORIGINS}
        self.models_list: Dict[str, QtWidgets.QListWidget] = {}
        self.tables: Dict[str, QtWidgets.QTableWidget] = {}
        self.display_lines: Dict[str, List[Dict[str, Any]]] = {origin: [] for origin in self.ORIGINS}
        self.current_model_id: Dict[str, Optional[int]] = {origin: None for origin in self.ORIGINS}

        titles = {
            "local": "Dados Items",
            "global": "Dados Gerais",
        }

        for origin in self.ORIGINS:
            page = QtWidgets.QWidget()
            page_layout = QtWidgets.QVBoxLayout(page)
            page_layout.setContentsMargins(0, 0, 0, 0)
            page_layout.setSpacing(6)

            splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, page)
            splitter.setChildrenCollapsible(False)

            list_widget = QtWidgets.QListWidget()
            list_widget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
            list_container = QtWidgets.QWidget()
            list_layout = QtWidgets.QVBoxLayout(list_container)
            list_layout.setContentsMargins(0, 0, 0, 0)
            list_layout.addWidget(list_widget)
            splitter.addWidget(list_container)

            table = QtWidgets.QTableWidget()
            table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
            table.setAlternatingRowColors(True)
            splitter.addWidget(table)

            splitter.setStretchFactor(0, 1)
            splitter.setStretchFactor(1, 2)

            page_layout.addWidget(splitter, 1)
            self.tabs.addTab(page, titles[origin])

            list_widget.itemSelectionChanged.connect(partial(self._on_model_selected, origin))

            self.models_list[origin] = list_widget
            self.tables[origin] = table

        controls_layout = QtWidgets.QHBoxLayout()
        self.btn_select_all = QtWidgets.QPushButton("Selecionar Tudo")
        self.btn_clear_selection = QtWidgets.QPushButton("Limpar Selecao")
        self.btn_select_all.clicked.connect(self._select_all_current)
        self.btn_clear_selection.clicked.connect(self._clear_selection_current)
        controls_layout.addWidget(self.btn_select_all)
        controls_layout.addWidget(self.btn_clear_selection)
        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        options_layout = QtWidgets.QHBoxLayout()
        self.radio_replace = QtWidgets.QRadioButton("Substituir linhas atuais")
        self.radio_replace.setChecked(True)
        self.radio_append = QtWidgets.QRadioButton("Adicionar / mesclar")
        options_layout.addWidget(self.radio_replace)
        options_layout.addWidget(self.radio_append)
        options_layout.addStretch()
        layout.addLayout(options_layout)

        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.tabs.currentChanged.connect(lambda _: self._update_controls_state())

        self._populate_models("local")
        self._populate_models("global")

        if self.models_list["local"].count():
            self.models_list["local"].setCurrentRow(0)
        elif self.models_list["global"].count():
            self.tabs.setCurrentIndex(1)
            self.models_list["global"].setCurrentRow(0)

        self._update_controls_state()

    def _populate_models(self, origin: str) -> None:
        list_widget = self.models_list[origin]
        list_widget.blockSignals(True)
        list_widget.clear()
        try:
            if origin == "local":
                models = svc_di.listar_modelos(
                    self.session,
                    orcamento_id=self.context.orcamento_id,
                    item_id=self.context.item_id,
                )
            else:
                user_id = getattr(self.current_user, "id", None)
                models = (
                    svc_dg.listar_modelos(self.session, user_id=user_id, tipo_menu=self.tipo_menu)
                    if user_id
                    else []
                )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar modelos: {exc}")
            models = []
        finally:
            list_widget.blockSignals(False)

        self.models[origin] = models

        list_widget.blockSignals(True)
        for model in models:
            item = QtWidgets.QListWidgetItem(self._model_display(model))
            item.setData(QtCore.Qt.UserRole, getattr(model, "id", None))
            list_widget.addItem(item)
        list_widget.blockSignals(False)

        self.display_lines[origin] = []
        self.current_model_id[origin] = None

        table = self.tables[origin]
        table.setRowCount(0)
        table.setColumnCount(0)

    def _model_display(self, model: Any) -> str:
        display = getattr(model, "nome_modelo", str(model))
        created = getattr(model, "created_at", None)
        if created:
            try:
                display += f" ({created})"
            except Exception:
                pass
        return display

    def _on_model_selected(self, origin: str) -> None:
        list_widget = self.models_list[origin]
        item = list_widget.currentItem()
        if not item:
            self.display_lines[origin] = []
            self.current_model_id[origin] = None
            table = self.tables[origin]
            table.setRowCount(0)
            table.setColumnCount(0)
            self._update_controls_state()
            return

        model_id = item.data(QtCore.Qt.UserRole)
        payload = self._load_model_payload(origin, model_id)

        rows = _extract_rows_from_payload(origin, payload, self.tipo_menu)
        self.display_lines[origin] = self._filtered_lines(rows)
        self.current_model_id[origin] = model_id
        self._populate_table(origin)
        self._update_controls_state()

    def _load_model_payload(self, origin: str, model_id: Optional[int]) -> Optional[Mapping[str, Any]]:
        if model_id is None:
            return None
        try:
            if origin == "local":
                return svc_di.carregar_modelo(self.session, model_id)
            user_id = getattr(self.current_user, "id", None)
            return svc_dg.carregar_modelo(self.session, model_id, user_id=user_id)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar modelo: {exc}")
            return None

    def _filtered_lines(self, rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        return [dict(row) for row in rows if isinstance(row, Mapping)]

    def _populate_table(self, origin: str) -> None:
        table = self.tables[origin]
        rows = self.display_lines.get(origin, [])
        columns = PREVIEW_COLUMNS.get(self.tipo_menu, PREVIEW_COLUMNS["ferragens"])

        table.clear()
        table.setColumnCount(len(columns) + 1)
        table.setRowCount(len(rows))
        table.setHorizontalHeaderLabels(["Importar"] + [col[0] for col in columns])

        for row_idx, row_data in enumerate(rows):
            check_item = QtWidgets.QTableWidgetItem()
            check_item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            check_item.setCheckState(QtCore.Qt.Checked)
            table.setItem(row_idx, 0, check_item)

            for col_idx, (_, key, kind) in enumerate(columns, start=1):
                value = _format_preview_value(kind, row_data.get(key))
                item = QtWidgets.QTableWidgetItem(value)
                item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                table.setItem(row_idx, col_idx, item)

        if rows:
            table.resizeColumnsToContents()

    def _current_origin(self) -> str:
        index = self.tabs.currentIndex()
        if 0 <= index < len(self.ORIGINS):
            return self.ORIGINS[index]
        return self.ORIGINS[0]

    def _set_all_checks(self, origin: str, state: QtCore.Qt.CheckState) -> None:
        table = self.tables.get(origin)
        if not table:
            return
        for row_idx in range(table.rowCount()):
            item = table.item(row_idx, 0)
            if item:
                item.setCheckState(state)

    def _select_all_current(self) -> None:
        self._set_all_checks(self._current_origin(), QtCore.Qt.Checked)

    def _clear_selection_current(self) -> None:
        self._set_all_checks(self._current_origin(), QtCore.Qt.Unchecked)

    def _collect_selected_rows(self, origin: str) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        table = self.tables.get(origin)
        display = self.display_lines.get(origin, [])
        if not table or not display:
            return rows
        for row_idx in range(table.rowCount()):
            item = table.item(row_idx, 0)
            if item and item.checkState() == QtCore.Qt.Checked:
                try:
                    rows.append(dict(display[row_idx]))
                except IndexError:
                    continue
        return rows

    def _update_controls_state(self) -> None:
        origin = self._current_origin()
        table = self.tables.get(origin)
        has_rows = bool(table and table.rowCount())
        self.btn_select_all.setEnabled(has_rows)
        self.btn_clear_selection.setEnabled(has_rows)

    def selected_source(self) -> Optional[Tuple[str, int]]:
        return self._selected_source

    def selected_rows(self) -> List[Dict[str, Any]]:
        return [dict(row) for row in self._selected_rows]

    def replace_existing(self) -> bool:
        return self.radio_replace.isChecked()

    def accept(self) -> None:
        origin = self._current_origin()
        model_id = self.current_model_id.get(origin)
        if not model_id:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione um modelo para importar.")
            return

        rows = self._collect_selected_rows(origin)
        if not rows:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione pelo menos uma linha para importar.")
            return

        self._selected_source = (origin, model_id)
        self._selected_rows = rows
        super().accept()


class ImportarMultiDadosItemsDialog(QtWidgets.QDialog):
    def __init__(
        self,
        session: Session,
        context: svc_di.DadosItemsContext,
        current_user=None,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent)
        self.session = session
        self.context = context
        self.current_user = current_user
        self.selections: Dict[str, Tuple[str, int, bool]] = {}

        self.setWindowTitle("Importar Multi Dados Items")
        self.resize(620, 480)

        layout = QtWidgets.QVBoxLayout(self)

        self.sections: Dict[str, Dict[str, Any]] = {}

        for menu, titulo in (
            (svc_di.MENU_MATERIAIS, "Materiais"),
            (svc_di.MENU_FERRAGENS, "Ferragens"),
            (svc_di.MENU_SIS_CORRER, "Sistemas Correr"),
            (svc_di.MENU_ACABAMENTOS, "Acabamentos"),
        ):
            box = QtWidgets.QGroupBox(titulo)
            box_layout = QtWidgets.QHBoxLayout(box)

            combo = QtWidgets.QComboBox()
            combo.addItem("(nenhum)", None)
            for model in svc_di.listar_modelos(
                self.session,
                orcamento_id=self.context.orcamento_id,
                item_id=self.context.item_id,
            ):
                combo.addItem(f"Local - {model.nome_modelo}", ("local", model.id))

            user_id = getattr(self.current_user, "id", None)
            for model in svc_dg.listar_modelos(self.session, user_id=user_id, tipo_menu=menu):
                combo.addItem(f"Global - {model.nome_modelo}", ("global", model.id))

            replace_check = QtWidgets.QCheckBox("Substituir", checked=True)

            box_layout.addWidget(combo, 1)
            box_layout.addWidget(replace_check)

            layout.addWidget(box)
            self.sections[menu] = {"combo": combo, "replace": replace_check}

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        selections: Dict[str, Tuple[str, int, bool]] = {}
        for menu, widgets in self.sections.items():
            combo: QtWidgets.QComboBox = widgets["combo"]
            data = combo.currentData()
            if not data:
                continue
            origin, model_id = data
            replace = widgets["replace"].isChecked()
            selections[menu] = (origin, model_id, replace)
        if not selections:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione pelo menos um modelo.")
            return
        self.selections = selections
        self.accept()

    def selected_models(self) -> Dict[str, Tuple[str, int, bool]]:
        return self.selections
