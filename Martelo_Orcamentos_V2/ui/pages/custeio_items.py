from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

from PySide6 import QtCore, QtGui, QtWidgets

from Martelo_Orcamentos_V2.app.models import OrcamentoItem
from Martelo_Orcamentos_V2.app.services import custeio_items as svc_custeio
from Martelo_Orcamentos_V2.app.db import SessionLocal 


class CusteioTreeFilterProxy(QtCore.QSortFilterProxyModel):
    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._only_checked = False
        self.setRecursiveFilteringEnabled(False)
        self.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.setFilterKeyColumn(0)

    def set_only_checked(self, enabled: bool) -> None:
        if self._only_checked == enabled:
            return
        self._only_checked = enabled
        self.invalidateFilter()

    def only_checked(self) -> bool:
        return self._only_checked

    def filterAcceptsRow(self, source_row: int, source_parent: QtCore.QModelIndex) -> bool:  # type: ignore[override]
        index = self.sourceModel().index(source_row, 0, source_parent)
        if not index.isValid():
            return False

        visible_by_text = self._matches_filter(index)
        visible_by_children = self._has_descendant_matching(index)
        if not (visible_by_text or visible_by_children):
            return False

        if not self._only_checked:
            return True

        if self._has_checked(index):
            return True

        return False

    # ------------------------------------------------------------------
    def _filter_pattern(self) -> Optional[QtCore.QRegularExpression]:
        pattern = self.filterRegularExpression()
        return pattern if pattern and pattern.pattern() else None

    def _matches_filter(self, index: QtCore.QModelIndex) -> bool:
        regex = self._filter_pattern()
        if regex is None:
            return True
        text = index.data(QtCore.Qt.DisplayRole) or ""
        return bool(regex.match(str(text)))

    def _has_descendant_matching(self, index: QtCore.QModelIndex) -> bool:
        model = self.sourceModel()
        row_count = model.rowCount(index)
        for row in range(row_count):
            child = model.index(row, 0, index)
            if not child.isValid():
                continue
            if self._matches_filter(child):
                return True
            if self._has_descendant_matching(child):
                return True
        return False

    def _has_checked(self, index: QtCore.QModelIndex) -> bool:
        item = self._item_from_index(index)
        if item is None:
            return False
        if item.checkState() == QtCore.Qt.Checked:
            return True
        row_count = item.rowCount()
        for row in range(row_count):
            child = item.child(row)
            if child is None:
                continue
            if self._has_checked(child.index()):
                return True
        return False

    def _item_from_index(self, index: QtCore.QModelIndex) -> Optional[QtGui.QStandardItem]:
        if not index.isValid():
            return None
        source_index = index
        if isinstance(self.sourceModel(), QtGui.QStandardItemModel):
            model: QtGui.QStandardItemModel = self.sourceModel()  # type: ignore[assignment]
            return model.itemFromIndex(source_index)
        return None


class CusteioItemsPage(QtWidgets.QWidget):
    CATEGORY_ROLE = QtCore.Qt.UserRole + 1

    def __init__(self, parent=None, current_user=None):
        super().__init__(parent)
        self.current_user = current_user
        self.session = SessionLocal()
        self.context = None

        self._updating_checks = False

        self._setup_ui()
        self._populate_tree()
        self._update_summary()

    # ------------------------------------------------------------------ UI setup
    def _setup_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # Header ---------------------------------------------------------
        header = QtWidgets.QWidget(self)
        grid = QtWidgets.QGridLayout(header)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(4)

        self.lbl_title = QtWidgets.QLabel("Custeio dos Items")
        title_font = self.lbl_title.font()
        title_font.setBold(True)
        title_font.setPointSize(title_font.pointSize() + 2)
        self.lbl_title.setFont(title_font)

        grid.addWidget(self.lbl_title, 0, 0, 1, 4)

        self.lbl_item = QtWidgets.QLabel("-")
        self.lbl_descr = QtWidgets.QLabel("-")
        self.lbl_cliente = QtWidgets.QLabel("-")
        self.lbl_utilizador = QtWidgets.QLabel("-")
        self.lbl_ano = QtWidgets.QLabel("-")
        self.lbl_num = QtWidgets.QLabel("-")
        self.lbl_ver = QtWidgets.QLabel("-")
        self.lbl_altura = QtWidgets.QLabel("-")
        self.lbl_largura = QtWidgets.QLabel("-")
        self.lbl_profundidade = QtWidgets.QLabel("-")

        grid.addWidget(QtWidgets.QLabel("Item:"), 1, 0)
        grid.addWidget(self.lbl_item, 1, 1)
        grid.addWidget(QtWidgets.QLabel("Descrição:"), 1, 2)
        grid.addWidget(self.lbl_descr, 1, 3)

        row2 = QtWidgets.QHBoxLayout()
        row2.setSpacing(12)
        row2.addWidget(QtWidgets.QLabel("Cliente:"))
        row2.addWidget(self.lbl_cliente)
        row2.addSpacing(16)
        row2.addWidget(QtWidgets.QLabel("Utilizador:"))
        row2.addWidget(self.lbl_utilizador)
        row2.addSpacing(16)
        row2.addWidget(QtWidgets.QLabel("Ano:"))
        row2.addWidget(self.lbl_ano)
        row2.addSpacing(16)
        row2.addWidget(QtWidgets.QLabel("N.º Orçamento:"))
        row2.addWidget(self.lbl_num)
        row2.addSpacing(16)
        row2.addWidget(QtWidgets.QLabel("Versão:"))
        row2.addWidget(self.lbl_ver)
        row2.addStretch(1)
        grid.addLayout(row2, 2, 0, 1, 4)

        row3 = QtWidgets.QHBoxLayout()
        row3.setSpacing(12)
        row3.addWidget(QtWidgets.QLabel("Altura:"))
        row3.addWidget(self.lbl_altura)
        row3.addSpacing(16)
        row3.addWidget(QtWidgets.QLabel("Largura:"))
        row3.addWidget(self.lbl_largura)
        row3.addSpacing(16)
        row3.addWidget(QtWidgets.QLabel("Profundidade:"))
        row3.addWidget(self.lbl_profundidade)
        row3.addStretch(1)
        grid.addLayout(row3, 3, 0, 1, 4)

        root.addWidget(header)

        # Splitter -------------------------------------------------------
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter, 1)

        # Left panel -----------------------------------------------------
        panel_left = QtWidgets.QWidget(splitter)
        panel_layout = QtWidgets.QVBoxLayout(panel_left)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(6)

        search_layout = QtWidgets.QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(4)

        self.edit_search = QtWidgets.QLineEdit()
        self.edit_search.setPlaceholderText("Buscar… (Ctrl+F)")
        self.edit_search.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.edit_search, 1)

        self.btn_clear_search = QtWidgets.QToolButton()
        self.btn_clear_search.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogResetButton))
        self.btn_clear_search.setToolTip("Limpar pesquisa e seleção")
        self.btn_clear_search.clicked.connect(self._on_clear_filters)
        search_layout.addWidget(self.btn_clear_search)

        panel_layout.addLayout(search_layout)

        controls_layout = QtWidgets.QHBoxLayout()
        controls_layout.setSpacing(6)

        self.btn_expand = QtWidgets.QToolButton()
        self.btn_expand.setText("Expandir")
        self.btn_expand.clicked.connect(self._on_expand_all)
        controls_layout.addWidget(self.btn_expand)

        self.btn_collapse = QtWidgets.QToolButton()
        self.btn_collapse.setText("Colapsar")
        self.btn_collapse.clicked.connect(self._on_collapse_all)
        controls_layout.addWidget(self.btn_collapse)

        self.chk_selected_only = QtWidgets.QCheckBox("Só selecionados")
        self.chk_selected_only.toggled.connect(self._on_selected_only_toggled)
        controls_layout.addWidget(self.chk_selected_only)

        controls_layout.addStretch(1)
        panel_layout.addLayout(controls_layout)

        self.tree_model = QtGui.QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["Peças"])
        self.tree_model.itemChanged.connect(self._on_tree_item_changed)

        self.proxy_model = CusteioTreeFilterProxy(self)
        self.proxy_model.setSourceModel(self.tree_model)

        self.tree = QtWidgets.QTreeView()
        self.tree.setModel(self.proxy_model)
        self.tree.setUniformRowHeights(True)
        self.tree.setHeaderHidden(False)
        self.tree.setAnimated(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tree.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)

        panel_layout.addWidget(self.tree, 1)

        footer_layout = QtWidgets.QHBoxLayout()
        footer_layout.setSpacing(12)

        self.lbl_summary = QtWidgets.QLabel("Selecionados: 0")
        footer_layout.addWidget(self.lbl_summary)
        footer_layout.addStretch(1)

        panel_layout.addLayout(footer_layout)

        self.btn_add = QtWidgets.QPushButton("Adicionar Seleções")
        self.btn_add.setDefault(True)
        self.btn_add.clicked.connect(self._on_add_selected)
        panel_layout.addWidget(self.btn_add)

        splitter.addWidget(panel_left)

        # Right panel ----------------------------------------------------
        panel_right = QtWidgets.QWidget(splitter)
        right_layout = QtWidgets.QVBoxLayout(panel_right)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(8)

        placeholder = QtWidgets.QLabel(
            "Área de trabalho do custeio (tab_def_pecas) em desenvolvimento.\n"
            "Selecione peças no painel à esquerda para futuras operações."
        )
        placeholder.setAlignment(QtCore.Qt.AlignCenter)
        placeholder.setStyleSheet("color: #777777; font-style: italic;")
        right_layout.addWidget(placeholder, 1)

        splitter.addWidget(panel_right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        # Shortcuts ------------------------------------------------------
        shortcut_find = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+F"), self)
        shortcut_find.activated.connect(self.edit_search.setFocus)

    # ------------------------------------------------------------------ Tree creation
    def _populate_tree(self) -> None:
        self.tree_model.blockSignals(True)
        self.tree_model.removeRows(0, self.tree_model.rowCount())

        definition = svc_custeio.obter_arvore()
        for node in definition:
            item = self._create_item(node, parent_path=())
            if item is not None:
                self.tree_model.appendRow(item)

        self.tree_model.blockSignals(False)
        self.tree.expandToDepth(0)

    def _create_item(self, node: Dict[str, Any], parent_path: Sequence[str]) -> Optional[QtGui.QStandardItem]:
        label = str(node.get("label", "")).strip()
        if not label:
            return None

        item = QtGui.QStandardItem(label)
        item.setEditable(False)
        item.setCheckable(True)
        item.setCheckState(QtCore.Qt.Unchecked)

        path = tuple(parent_path) + (label,)
        item.setData(" > ".join(path), self.CATEGORY_ROLE)

        children = node.get("children") or []
        if children:
            item.setTristate(True)
            icon = self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon)
            item.setIcon(icon)
            for child in children:
                child_item = self._create_item(child, parent_path=path)
                if child_item is not None:
                    item.appendRow(child_item)
        else:
            icon = self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon)
            item.setIcon(icon)

        return item

    # ------------------------------------------------------------------ Header helpers
    def _reset_header(self) -> None:
        self.lbl_item.setText("-")
        self.lbl_descr.setText("-")
        self.lbl_cliente.setText("-")
        self.lbl_utilizador.setText("-")
        self.lbl_ano.setText("-")
        self.lbl_num.setText("-")
        self.lbl_ver.setText("-")
        self.lbl_altura.setText("-")
        self.lbl_largura.setText("-")
        self.lbl_profundidade.setText("-")

    def _update_header_from_item(self, item_id: Optional[int]) -> None:
        self._reset_header()
        if not item_id:
            return

        item: Optional[OrcamentoItem] = self.session.get(OrcamentoItem, item_id)
        if not item:
            return

        numero = getattr(item, "item_ord", None) or getattr(item, "item", None) or item_id
        self.lbl_item.setText(str(numero))
        descricao = (item.descricao or "").strip()
        self.lbl_descr.setText(descricao or "-")

        self.lbl_altura.setText(self._format_dim(getattr(item, "altura", None)))
        self.lbl_largura.setText(self._format_dim(getattr(item, "largura", None)))
        self.lbl_profundidade.setText(self._format_dim(getattr(item, "profundidade", None)))

    def _format_dim(self, value: Any) -> str:
        try:
            if value in (None, ""):
                return "-"
            return f"{float(value):.1f} mm"
        except Exception:
            return str(value)

    # ------------------------------------------------------------------ Slots
    def _on_expand_all(self) -> None:
        self.tree.expandAll()

    def _on_collapse_all(self) -> None:
        self.tree.collapseAll()
        self.tree.expandToDepth(0)

    def _on_selected_only_toggled(self, checked: bool) -> None:
        self.proxy_model.set_only_checked(checked)
        self.tree.expandAll()
        if not checked:
            self.tree.expandToDepth(0)

    def _on_search_changed(self, text: str) -> None:
        expression = QtCore.QRegularExpression(QtCore.QRegularExpression.escape(text), QtCore.QRegularExpression.CaseInsensitiveOption)
        self.proxy_model.setFilterRegularExpression(expression)
        self.tree.expandAll()
        if not text:
            self.tree.expandToDepth(0)

    def _on_clear_filters(self) -> None:
        self.edit_search.clear()
        self.chk_selected_only.setChecked(False)
        self._clear_all_checks()
        self.tree.expandToDepth(0)

    def _clear_all_checks(self) -> None:
        self._updating_checks = True
        try:
            for row in range(self.tree_model.rowCount()):
                item = self.tree_model.item(row, 0)
                if item is not None:
                    item.setCheckState(QtCore.Qt.Unchecked)
        finally:
            self._updating_checks = False
        self._update_summary()

    def _on_tree_item_changed(self, item: QtGui.QStandardItem) -> None:
        if self._updating_checks:
            return

        self._updating_checks = True
        try:
            if item.hasChildren():
                self._propagate_to_children(item, item.checkState())
            self._update_parent_state(item)
        finally:
            self._updating_checks = False
        self._update_summary()

    def _propagate_to_children(self, item: QtGui.QStandardItem, state: QtCore.Qt.CheckState) -> None:
        for row in range(item.rowCount()):
            child = item.child(row)
            if child is None:
                continue
            child.setCheckState(state)
            if child.hasChildren():
                self._propagate_to_children(child, state)

    def _update_parent_state(self, item: QtGui.QStandardItem) -> None:
        parent = item.parent()
        if parent is None:
            return

        checked = 0
        partial = False
        total = parent.rowCount()
        for row in range(total):
            child = parent.child(row)
            if child is None:
                continue
            state = child.checkState()
            if state == QtCore.Qt.PartiallyChecked:
                partial = True
            elif state == QtCore.Qt.Checked:
                checked += 1

        if partial:
            parent.setCheckState(QtCore.Qt.PartiallyChecked)
        else:
            if checked == 0:
                parent.setCheckState(QtCore.Qt.Unchecked)
            elif checked == total:
                parent.setCheckState(QtCore.Qt.Checked)
            else:
                parent.setCheckState(QtCore.Qt.PartiallyChecked)

        self._update_parent_state(parent)

    def _on_add_selected(self) -> None:
        items = self._gather_checked_items()
        if not items:
            QtWidgets.QMessageBox.information(self, "Informação", "Nenhuma peça selecionada.")
            return
        summary = "\n".join(items[:15])
        if len(items) > 15:
            summary += f"\n… (+{len(items) - 15} linhas)"
        QtWidgets.QMessageBox.information(
            self,
            "Peças selecionadas",
            f"{len(items)} peça(s) selecionada(s):\n\n{summary}",
        )

    # ------------------------------------------------------------------ Helpers
    def _gather_checked_items(self) -> List[str]:
        collected: List[str] = []
        for row in range(self.tree_model.rowCount()):
            item = self.tree_model.item(row, 0)
            if item:
                collected.extend(self._collect_from_item(item))
        return collected

    def _collect_from_item(self, item: QtGui.QStandardItem) -> List[str]:
        if item.rowCount() == 0:
            if item.checkState() == QtCore.Qt.Checked:
                value = item.data(self.CATEGORY_ROLE)
                return [str(value)]
            return []

        results: List[str] = []
        for row in range(item.rowCount()):
            child = item.child(row)
            if child:
                results.extend(self._collect_from_item(child))
        return results

    def _update_summary(self) -> None:
        count = len(self._gather_checked_items())
        self.lbl_summary.setText(f"Selecionados: {count}")

    # ------------------------------------------------------------------ Public API
    def load_item(self, orcamento_id: int, item_id: Optional[int]) -> None:
        if not orcamento_id:
            self.context = None
            self._reset_header()
            return

        try:
            self.context = svc_custeio.carregar_contexto(self.session, orcamento_id, item_id=item_id)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar dados do orçamento: {exc}")
            self.context = None
            self._reset_header()
            return

        ctx = self.context
        self.lbl_cliente.setText(str(ctx.cliente_id or "-"))
        self.lbl_utilizador.setText(str(ctx.user_id or "-"))
        self.lbl_ano.setText(str(ctx.ano or "-"))
        self.lbl_num.setText(str(ctx.num_orcamento or "-"))
        self.lbl_ver.setText(str(ctx.versao or "-"))

        self._update_header_from_item(item_id)

    def clear_context(self) -> None:
        self.context = None
        self._reset_header()
        self._clear_all_checks()

