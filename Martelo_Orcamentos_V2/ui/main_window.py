from typing import Optional

import logging
from PySide6 import QtWidgets
from PySide6.QtCore import Qt

from .pages.orcamentos import OrcamentosPage
from .pages.itens import ItensPage
from .pages.materias_primas import MateriasPrimasPage
from .pages.clientes import ClientesPage
from .pages.dados_gerais import DadosGeraisPage
from .pages.dados_items import DadosItemsPage
from .pages.custeio_items import CusteioItemsPage
from .pages.relatorios import RelatoriosPage
from .pages.settings import SettingsPage


logger = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.setWindowTitle("Martelo Orçamentos V2")
        self.resize(1200, 800)

        self.current_orcamento_id: Optional[int] = None
        self.current_item_id: Optional[int] = None

        self.nav = QtWidgets.QTreeWidget()
        self.nav.setHeaderHidden(True)
        self.nav.setExpandsOnDoubleClick(False)
        self.nav.setRootIsDecorated(True)
        self.nav.setFixedWidth(240)
        self._nav_items = {}
        self._nav_base_point_size = self.nav.font().pointSize()
        self._nav_active_delta = 1

        # Orçamentos group
        orc_node = QtWidgets.QTreeWidgetItem(["Orçamentos"])
        orc_node.setData(0, Qt.UserRole, 0)
        self.nav.addTopLevelItem(orc_node)
        self._nav_items["orcamentos"] = orc_node

        def _add_child(parent, text, stack_index, key):
            item = QtWidgets.QTreeWidgetItem([text])
            item.setData(0, Qt.UserRole, stack_index)
            parent.addChild(item)
            self._nav_items[key] = item
            return item

        _add_child(orc_node, "Items", 1, "items")
        _add_child(orc_node, "Dados Gerais", 4, "dados_gerais")
        _add_child(orc_node, "Dados Items", 5, "dados_items")
        _add_child(orc_node, "Custeio dos Items", 6, "custeio")
        _add_child(orc_node, "Relatórios", 7, "relatorios")
        orc_node.setExpanded(True)

        # Add standalone entries
        materias_node = QtWidgets.QTreeWidgetItem(["Matérias Primas"])
        materias_node.setData(0, Qt.UserRole, 2)
        self.nav.addTopLevelItem(materias_node)
        self._nav_items["materias"] = materias_node

        clientes_node = QtWidgets.QTreeWidgetItem(["Clientes"])
        clientes_node.setData(0, Qt.UserRole, 3)
        self.nav.addTopLevelItem(clientes_node)
        self._nav_items["clientes"] = clientes_node

        configuracoes_node = QtWidgets.QTreeWidgetItem(["Configurações"])
        configuracoes_node.setData(0, Qt.UserRole, 8)
        self.nav.addTopLevelItem(configuracoes_node)
        self._nav_items["configuracoes"] = configuracoes_node
        self.nav.expandAll()
        self._reset_all_nav_item_styles()

        self.stack = QtWidgets.QStackedWidget()

        self.pg_orc = OrcamentosPage(current_user=self.current_user)
        self.pg_itens = ItensPage(current_user=self.current_user)
        self.pg_itens.item_selected.connect(self.on_item_selected)
        self.pg_itens.production_mode_changed.connect(self.on_production_mode_changed)
        self.pg_materias = MateriasPrimasPage(current_user=self.current_user)
        self.pg_clientes = ClientesPage()
        self.pg_dados = DadosGeraisPage(current_user=self.current_user)
        self.pg_dados_items = DadosItemsPage(current_user=self.current_user)
        self.pg_custeio = CusteioItemsPage(current_user=self.current_user)
        self.pg_custeio.item_context_changed.connect(self.on_custeio_item_changed)
        self.pg_relatorios = RelatoriosPage(current_user=self.current_user)

        self.stack.addWidget(self.pg_orc)
        self.stack.addWidget(self.pg_itens)
        self.stack.addWidget(self.pg_materias)
        self.stack.addWidget(self.pg_clientes)
        self.stack.addWidget(self.pg_dados)
        self.stack.addWidget(self.pg_dados_items)
        self.stack.addWidget(self.pg_custeio)
        self.stack.addWidget(self.pg_relatorios)
        self.pg_settings = SettingsPage(current_user=self.current_user)
        self.pg_settings.margens_updated.connect(self.pg_itens.refresh_margem_defaults)
        self.stack.addWidget(self.pg_settings)

        self.nav.currentItemChanged.connect(self.on_nav_changed)
        self.pg_orc.orcamento_aberto.connect(self.on_abrir_orcamento)

        self.nav.setCurrentItem(self._nav_items["orcamentos"])
        self.stack.setCurrentIndex(0)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(central)
        layout.addWidget(self.nav)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

    def on_abrir_orcamento(self, orcamento_id: int):
        if self.current_orcamento_id:
            if not self.pg_custeio.auto_save_if_dirty():
                return
        self.current_orcamento_id = orcamento_id
        self.current_item_id = None
        self.pg_itens.load_orcamento(orcamento_id)
        self.pg_dados.load_orcamento(orcamento_id)
        self.pg_dados_items.load_item(orcamento_id, None)
        self.pg_custeio.load_item(orcamento_id, None)
        self.pg_settings.set_orcamento_context(orcamento_id)
        self.pg_relatorios.set_orcamento(orcamento_id)

        target_item = self._nav_items.get("items")
        if target_item and self.nav.currentItem() is not target_item:
            self.nav.blockSignals(True)
            self.nav.setCurrentItem(target_item)
            self.nav.blockSignals(False)
        self.stack.setCurrentIndex(1)

    def on_nav_changed(self, current: Optional[QtWidgets.QTreeWidgetItem], previous: Optional[QtWidgets.QTreeWidgetItem]):
        if current is None:
            return
        index = current.data(0, Qt.UserRole)
        if index is None:
            # select first child if available
            if current.childCount():
                child = current.child(0)
                self.nav.blockSignals(True)
                self.nav.setCurrentItem(child)
                self.nav.blockSignals(False)
            return
        current_index = self.stack.currentIndex()
        if current_index == 6 and index != 6:
            if not self.pg_custeio.auto_save_if_dirty():
                self.nav.blockSignals(True)
                if previous:
                    self.nav.setCurrentItem(previous)
                self.nav.blockSignals(False)
                self.stack.setCurrentIndex(current_index)
                return
        parent = current.parent()
        if parent:
            parent.setExpanded(True)
        self.stack.setCurrentIndex(index)
        if previous is not None:
            self._set_nav_item_style(previous, active=False)
        self._set_nav_item_style(current, active=True)

        if index == 0:
            self.pg_orc.reload_clients()
        elif index == 4 and self.current_orcamento_id:
            self.pg_dados.load_orcamento(self.current_orcamento_id)
        elif index == 5 and self.current_orcamento_id:
            self.pg_dados_items.load_item(self.current_orcamento_id, self.current_item_id)
        elif index == 6 and self.current_orcamento_id:
            self.pg_custeio.load_item(self.current_orcamento_id, self.current_item_id)
        elif index == 7 and self.current_orcamento_id:
            self.pg_relatorios.refresh_preview()
        elif index == 8 and self.current_orcamento_id:
            self.pg_settings.refresh_producao_mode()

    def on_item_selected(self, item_id: Optional[int]):
        if self.current_orcamento_id:
            if not self.pg_custeio.auto_save_if_dirty():
                return
        self.current_item_id = item_id
        if not self.current_orcamento_id:
            return
        self.pg_dados_items.load_item(self.current_orcamento_id, item_id)
        self.pg_custeio.load_item(self.current_orcamento_id, item_id)

    def on_production_mode_changed(self, modo: str):
        self.pg_settings.update_producao_mode_display(modo)
        if hasattr(self.pg_custeio, "on_production_mode_changed"):
            try:
                self.pg_custeio.on_production_mode_changed(modo)
            except Exception as exc:
                logger.exception("Falha ao atualizar modo de producao no custeio: %s", exc)

    def on_custeio_item_changed(self, item_id: Optional[int]):
        if self.current_orcamento_id is None:
            return
        changed = item_id != self.current_item_id
        self.current_item_id = item_id
        if changed or self.stack.currentIndex() == 5:
            self.pg_dados_items.load_item(self.current_orcamento_id, item_id)
        if self.pg_itens and hasattr(self.pg_itens, "focus_item"):
            self.pg_itens.focus_item(item_id)

    def _reset_all_nav_item_styles(self) -> None:
        def reset_item(item: QtWidgets.QTreeWidgetItem) -> None:
            self._set_nav_item_style(item, active=False)
            for idx in range(item.childCount()):
                reset_item(item.child(idx))

        for idx in range(self.nav.topLevelItemCount()):
            reset_item(self.nav.topLevelItem(idx))

    def _set_nav_item_style(self, item: Optional[QtWidgets.QTreeWidgetItem], *, active: bool) -> None:
        if item is None:
            return
        font = item.font(0)
        font.setBold(active)
        font.setPointSize(self._nav_base_point_size + (self._nav_active_delta if active else 0))
        item.setFont(0, font)
