from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from PySide6 import QtCore, QtWidgets

from Martelo_Orcamentos_V2.app.models import OrcamentoItem
from sqlalchemy.orm import Session
from Martelo_Orcamentos_V2.app.services import dados_items as svc_di
from Martelo_Orcamentos_V2.app.services import dados_gerais as svc_dg

from .dados_gerais import DadosGeraisPage


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

        source = dialog.selected_source()
        if not source:
            return
        origin, model_id = source
        replace = dialog.replace_existing()

        try:
            if origin == "local":
                linhas_por_menu = svc_di.carregar_modelo(self.session, model_id)
            else:
                user_id = getattr(self.current_user, "id", None)
                linhas_por_menu = svc_dg.carregar_modelo(self.session, model_id, user_id=user_id)
        except Exception as exc:  # pragma: no cover
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao importar: {exc}")
            return

        linhas = self._extract_rows_for_import(origin, linhas_por_menu, key)
        self._apply_imported_rows(key, linhas, replace=replace)

    def _extract_rows_for_import(
        self,
        origin: str,
        linhas_por_menu: Mapping[str, Sequence[Mapping[str, Any]]],
        menu: str,
    ) -> List[Dict[str, Any]]:
        rows: Sequence[Mapping[str, Any]] = []
        if origin == "global":
            candidate = linhas_por_menu.get("linhas")
            if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes)):
                rows = [row for row in candidate if isinstance(row, Mapping)]
            else:
                candidate = linhas_por_menu.get(menu)
                if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes)):
                    rows = [row for row in candidate if isinstance(row, Mapping)]
        else:
            candidate = linhas_por_menu.get(menu, [])
            if isinstance(candidate, Sequence) and not isinstance(candidate, (str, bytes)):
                rows = [row for row in candidate if isinstance(row, Mapping)]
        return [dict(row) for row in rows]

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
        self._selected: Optional[Tuple[str, int]] = None

        self.setWindowTitle("Importar Dados Items")
        self.resize(700, 500)

        layout = QtWidgets.QVBoxLayout(self)

        tabs = QtWidgets.QTabWidget(self)
        layout.addWidget(tabs, 1)

        self.list_local = QtWidgets.QListWidget()
        self.list_global = QtWidgets.QListWidget()

        tabs.addTab(self.list_local, "Dados Items")
        tabs.addTab(self.list_global, "Dados Gerais")

        self.replace_check = QtWidgets.QCheckBox("Substituir linhas atuais", checked=True)
        layout.addWidget(self.replace_check)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._populate_lists()

    def _populate_lists(self) -> None:
        local_models = svc_di.listar_modelos(
            self.session,
            orcamento_id=self.context.orcamento_id,
            item_id=self.context.item_id,
        )
        for model in local_models:
            item = QtWidgets.QListWidgetItem(model.nome_modelo)
            item.setData(QtCore.Qt.UserRole, ("local", model.id))
            self.list_local.addItem(item)

        user_id = getattr(self.current_user, "id", None)
        global_models = svc_dg.listar_modelos(self.session, user_id=user_id, tipo_menu=self.tipo_menu)
        for model in global_models:
            item = QtWidgets.QListWidgetItem(model.nome_modelo)
            item.setData(QtCore.Qt.UserRole, ("global", model.id))
            self.list_global.addItem(item)

    def _on_accept(self) -> None:
        widget = None
        if self.list_local.currentItem():
            widget = self.list_local.currentItem()
        elif self.list_global.currentItem():
            widget = self.list_global.currentItem()
        if not widget:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Selecione um modelo para importar.")
            return
        data = widget.data(QtCore.Qt.UserRole)
        self._selected = data
        self.accept()

    def selected_source(self) -> Optional[Tuple[str, int]]:
        return self._selected

    def replace_existing(self) -> bool:
        return self.replace_check.isChecked()


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
