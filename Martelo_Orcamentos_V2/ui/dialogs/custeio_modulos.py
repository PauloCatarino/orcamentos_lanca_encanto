from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence
import re

from PySide6 import QtCore, QtGui, QtWidgets

from Martelo_Orcamentos_V2.app.services import modulos as svc_modulos


LINHA_HEADERS: Sequence[tuple[str, str]] = (
    ("descricao_livre", "Descricao_Livre"),
    ("def_peca", "Def_Peca"),
    ("qt_und", "QT_und"),
    ("comp", "Comp"),
    ("larg", "Larg"),
    ("esp", "Esp"),
)


def _montar_tabela_linhas(table: QtWidgets.QTableWidget, linhas: Sequence[Mapping[str, Any]]) -> None:
    table.clear()
    table.setColumnCount(len(LINHA_HEADERS))
    table.setHorizontalHeaderLabels([header for _, header in LINHA_HEADERS])
    table.setRowCount(len(linhas))
    for row_idx, row in enumerate(linhas):
        for col_idx, (key, _) in enumerate(LINHA_HEADERS):
            value = row.get(key)
            if value is None:
                text = ""
            else:
                text = str(value)
            item = QtWidgets.QTableWidgetItem(text)
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
            table.setItem(row_idx, col_idx, item)
    header = table.horizontalHeader()
    header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
    table.verticalHeader().setVisible(False)
    table.setAlternatingRowColors(True)


def _configurar_janela_dialog(dialog: QtWidgets.QDialog, *, default_width: int, default_height: int) -> None:
    """Aplica opções comuns de janela para dialogs grandes.

    - Garante botões minimizar/maximizar no Windows.
    - Ajusta o tamanho inicial para caber no ecrã (resoluções mais baixas).
    """

    dialog.setSizeGripEnabled(True)
    dialog.setWindowFlags(
        dialog.windowFlags()
        | QtCore.Qt.WindowMinimizeButtonHint
        | QtCore.Qt.WindowMaximizeButtonHint
        | QtCore.Qt.WindowCloseButtonHint
    )

    parent = dialog.parentWidget()
    screen = parent.screen() if parent is not None else None
    if not screen:
        screen = dialog.screen() or QtWidgets.QApplication.primaryScreen()
    if not screen:
        dialog.resize(default_width, default_height)
        return

    geo = screen.availableGeometry()
    # Deixar folga para bordas e para evitar "cortar" em ecrãs pequenos.
    margin = 80
    max_w = max(480, geo.width() - margin)
    max_h = max(360, geo.height() - margin)
    dialog.resize(min(default_width, max_w), min(default_height, max_h))
    dialog.setMaximumSize(geo.size())

    # Centrando e garantindo que fica dentro do ecrã.
    desired_pos = geo.center() - dialog.rect().center()
    x_max = geo.left() + max(0, geo.width() - dialog.width())
    y_max = geo.top() + max(0, geo.height() - dialog.height())
    x = max(geo.left(), min(desired_pos.x(), x_max))
    y = max(geo.top(), min(desired_pos.y(), y_max))
    dialog.move(x, y)


class SaveModuloDialog(QtWidgets.QDialog):
    def __init__(
        self,
        parent: QtWidgets.QWidget,
        session,
        current_user_id: Optional[int],
        linhas: Sequence[Mapping[str, Any]],
    ) -> None:
        super().__init__(parent)
        self.session = session
        self.current_user_id = current_user_id
        self._linhas = svc_modulos.limpar_linhas_para_modulo(linhas)
        self._imagem_path: Optional[str] = None
        self._scope = "user"
        self._modules_cache: Dict[str, List[Dict[str, Any]]] = {"user": [], "global": []}
        self._saved_modulo_id: Optional[int] = None

        self.setWindowTitle("Gravar Módulo de Peças")
        self._build_ui()
        _configurar_janela_dialog(self, default_width=980, default_height=640)
        self._load_modulos_scope()
        self._atualizar_preview()

    # UI -----------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.tabs = QtWidgets.QTabWidget()
        tab_user = QtWidgets.QWidget()
        tab_global = QtWidgets.QWidget()
        tab_user.setLayout(QtWidgets.QVBoxLayout())
        tab_user.layout().addWidget(QtWidgets.QLabel("Guardar módulo apenas para o utilizador atual."))
        tab_global.setLayout(QtWidgets.QVBoxLayout())
        tab_global.layout().addWidget(QtWidgets.QLabel("Guardar módulo na lista global (visível para todos)."))

        self.tabs.addTab(tab_user, "Utilizador")
        self.tabs.addTab(tab_global, "Global")
        self.tabs.currentChanged.connect(self._on_scope_changed)
        layout.addWidget(self.tabs)

        form_grid = QtWidgets.QGridLayout()
        form_grid.setVerticalSpacing(6)
        lbl_nome = QtWidgets.QLabel("Nome do Módulo:")
        self.ed_nome = QtWidgets.QLineEdit()
        self.ed_nome.setPlaceholderText("Ex: Módulo Base Cozinha 700mm")
        form_grid.addWidget(lbl_nome, 0, 0)
        form_grid.addWidget(self.ed_nome, 0, 1)

        lbl_existente = QtWidgets.QLabel("Selecionar Módulo Existente:")
        self.cmb_existente = QtWidgets.QComboBox()
        self.cmb_existente.addItem("Selecionar Módulo Existente...", None)
        self.cmb_existente.currentIndexChanged.connect(self._on_existing_changed)
        form_grid.addWidget(lbl_existente, 1, 0)
        form_grid.addWidget(self.cmb_existente, 1, 1)

        layout.addLayout(form_grid)

        layout.addWidget(QtWidgets.QLabel("Descrição (Opcional):"))
        self.txt_descricao = QtWidgets.QTextEdit()
        self.txt_descricao.setPlaceholderText("Detalhes sobre o módulo, utilização, etc.")
        self.txt_descricao.setTabChangesFocus(True)
        layout.addWidget(self.txt_descricao)

        body = QtWidgets.QHBoxLayout()
        body.setSpacing(12)

        linhas_box = QtWidgets.QVBoxLayout()
        linhas_box.addWidget(QtWidgets.QLabel(f"Resumo das {len(self._linhas)} peças a serem gravadas:"))
        self.tabela_linhas = QtWidgets.QTableWidget()
        linhas_box.addWidget(self.tabela_linhas, 1)
        body.addLayout(linhas_box, 3)

        imagem_box = QtWidgets.QVBoxLayout()
        self.lbl_imagem = QtWidgets.QLabel("Sem imagem")
        self.lbl_imagem.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_imagem.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.lbl_imagem.setMinimumSize(260, 240)
        imagem_box.addWidget(self.lbl_imagem, 1)

        btns_img = QtWidgets.QHBoxLayout()
        self.btn_escolher_imagem = QtWidgets.QPushButton("Escolher Imagem…")
        self.btn_remover_imagem = QtWidgets.QPushButton("Remover Imagem")
        self.btn_escolher_imagem.clicked.connect(self._on_choose_image)
        self.btn_remover_imagem.clicked.connect(self._on_remove_image)
        btns_img.addWidget(self.btn_escolher_imagem)
        btns_img.addWidget(self.btn_remover_imagem)
        imagem_box.addLayout(btns_img)

        body.addLayout(imagem_box, 2)
        layout.addLayout(body, 1)

        self.buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._on_accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    # Helpers ------------------------------------------------------------
    def _current_scope(self) -> str:
        return "global" if self.tabs.currentIndex() == 1 else "user"

    def _load_modulos_scope(self) -> None:
        scope = self._current_scope()
        try:
            self._modules_cache[scope] = svc_modulos.listar_modulos_por_scope(
                self.session, self.current_user_id, scope
            )
        except Exception:
            self._modules_cache[scope] = []
        self._rebuild_existing_combo()

    def _rebuild_existing_combo(self) -> None:
        scope = self._current_scope()
        modules = self._modules_cache.get(scope, [])
        current_id = self.cmb_existente.currentData()
        self.cmb_existente.blockSignals(True)
        self.cmb_existente.clear()
        self.cmb_existente.addItem("Selecionar Módulo Existente...", None)
        for mod in modules:
            owner = mod.get("owner_name") or ""
            label = mod["nome"]
            if scope == "global" and owner:
                label = f"{label} (por {owner})"
            self.cmb_existente.addItem(label, mod["id"])
        if current_id:
            idx = self.cmb_existente.findData(current_id)
            if idx >= 0:
                self.cmb_existente.setCurrentIndex(idx)
        self.cmb_existente.blockSignals(False)

    def _atualizar_preview(self) -> None:
        _montar_tabela_linhas(self.tabela_linhas, self._linhas)

    def _render_image(self, path: Optional[str]) -> None:
        if path and Path(path).is_file():
            pix = QtGui.QPixmap(path)
            if not pix.isNull():
                self._imagem_path = path
                self.lbl_imagem.setPixmap(pix.scaled(280, 280, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
                self.lbl_imagem.setToolTip(path)
                return
        self._imagem_path = None
        self.lbl_imagem.setPixmap(QtGui.QPixmap())
        self.lbl_imagem.setText("Sem imagem")
        self.lbl_imagem.setToolTip("")

    # Slots --------------------------------------------------------------
    def _on_scope_changed(self, index: int) -> None:
        self._scope = "global" if index == 1 else "user"
        self._load_modulos_scope()

    def _on_existing_changed(self, index: int) -> None:
        modulo_id = self.cmb_existente.itemData(index)
        if not modulo_id:
            return
        try:
            data = svc_modulos.carregar_modulo_completo(self.session, modulo_id)
        except Exception:
            data = None
        if not data:
            return
        self.ed_nome.setText(data.get("nome") or "")
        descricao = data.get("descricao") or ""
        self.txt_descricao.setPlainText(descricao)
        self._render_image(data.get("imagem_path"))

    def _on_choose_image(self) -> None:
        base_dir = svc_modulos.pasta_imagens_base(self.session)
        start_dir = Path(base_dir) if base_dir else Path.home()
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Selecionar imagem do módulo",
            str(start_dir),
            "Imagens (*.png *.jpg *.jpeg *.bmp *.gif);;Todos os ficheiros (*.*)",
        )
        if file_path:
            self._render_image(file_path)

    def _on_remove_image(self) -> None:
        self._render_image(None)

    def _on_accept(self) -> None:
        nome = (self.ed_nome.text() or "").strip()
        descricao = self.txt_descricao.toPlainText()
        if not nome:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Indique um nome para o módulo.")
            return
        modulo_id = self.cmb_existente.currentData()
        is_global = self._current_scope() == "global"
        try:
            modulo = svc_modulos.guardar_modulo(
                self.session,
                user_id=self.current_user_id,
                nome=nome,
                descricao=descricao,
                linhas=self._linhas,
                imagem_path=self._imagem_path,
                is_global=is_global,
                modulo_id=modulo_id,
            )
            self.session.commit()
        except Exception as exc:
            try:
                self.session.rollback()
            except Exception:
                pass
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao gravar módulo: {exc}")
            return
        self._saved_modulo_id = modulo.id
        self.accept()

    # Public API ---------------------------------------------------------
    def saved_modulo_id(self) -> Optional[int]:
        return self._saved_modulo_id


class ImportModuloDialog(QtWidgets.QDialog):
    def __init__(
        self,
        parent: QtWidgets.QWidget,
        session,
        current_user_id: Optional[int],
    ) -> None:
        super().__init__(parent)
        self.session = session
        self.current_user_id = current_user_id
        self._scope = "user"
        self._modules: List[Dict[str, Any]] = []
        self._module_data_cache: Dict[int, Dict[str, Any]] = {}
        self._selected_rows: List[Dict[str, Any]] = []

        self.setWindowTitle("Importar Módulo Guardado")
        self._build_ui()
        _configurar_janela_dialog(self, default_width=1200, default_height=900)
        self._load_modules()
        self._rebuild_list()

    # UI -----------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(QtWidgets.QWidget(), "Utilizador")
        self.tabs.addTab(QtWidgets.QWidget(), "Global")
        self.tabs.currentChanged.connect(self._on_scope_changed)
        layout.addWidget(self.tabs)

        search_row = QtWidgets.QHBoxLayout()
        lbl_search = QtWidgets.QLabel("Pesquisar módulos (use % para separar palavras):")
        self.edit_search = QtWidgets.QLineEdit()
        self.edit_search.textChanged.connect(self._rebuild_list)
        search_row.addWidget(lbl_search)
        search_row.addWidget(self.edit_search, 1)
        layout.addLayout(search_row)

        body = QtWidgets.QHBoxLayout()
        body.setSpacing(12)

        left = QtWidgets.QVBoxLayout()
        self.list_modulos = QtWidgets.QListWidget()
        self.list_modulos.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.list_modulos.setIconSize(QtCore.QSize(96, 96))
        self.list_modulos.setSpacing(4)
        self.list_modulos.itemSelectionChanged.connect(self._on_selection_changed)
        left.addWidget(self.list_modulos, 1)
        body.addLayout(left, 1)

        right = QtWidgets.QVBoxLayout()
        self.lbl_nome = QtWidgets.QLabel("Nome:")
        font_bold = self.lbl_nome.font()
        font_bold.setBold(True)
        self.lbl_nome.setFont(font_bold)
        right.addWidget(self.lbl_nome)

        self.txt_descricao = QtWidgets.QTextEdit()
        self.txt_descricao.setReadOnly(True)
        self.txt_descricao.setMinimumHeight(80)
        right.addWidget(self.txt_descricao)

        right_img_row = QtWidgets.QHBoxLayout()
        self.lbl_imagem = QtWidgets.QLabel("Sem imagem")
        self.lbl_imagem.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_imagem.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.lbl_imagem.setMinimumSize(220, 220)
        self.lbl_imagem.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        right_img_row.addWidget(self.lbl_imagem, 1)
        right.addLayout(right_img_row)

        right.addWidget(QtWidgets.QLabel("Peças do módulo selecionado:"))
        self.tabela_linhas = QtWidgets.QTableWidget()
        self.tabela_linhas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.tabela_linhas.setMinimumHeight(160)
        right.addWidget(self.tabela_linhas, 1)

        body.addLayout(right, 2)
        layout.addLayout(body, 1)

        self.buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Open | QtWidgets.QDialogButtonBox.Cancel)
        self.buttons.button(QtWidgets.QDialogButtonBox.Open).setText("Importar Módulo")
        self.buttons.accepted.connect(self._on_accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    # Helpers ------------------------------------------------------------
    def _load_modules(self) -> None:
        scope = self._scope
        try:
            self._modules = svc_modulos.listar_modulos_por_scope(self.session, self.current_user_id, scope)
        except Exception:
            self._modules = []

    def _filter_modules(self) -> List[Dict[str, Any]]:
        query = (self.edit_search.text() or "").casefold()
        tokens = [tok for tok in re.split(r"[\s%]+", query) if tok]
        if not tokens:
            return list(self._modules)
        filtered: List[Dict[str, Any]] = []
        for mod in self._modules:
            hay = f"{mod.get('nome','')} {mod.get('descricao','')}".casefold()
            if all(tok in hay for tok in tokens):
                filtered.append(mod)
        return filtered

    def _rebuild_list(self) -> None:
        mods = self._filter_modules()
        self.list_modulos.blockSignals(True)
        self.list_modulos.clear()
        for mod in mods:
            text = mod.get("nome") or "Sem nome"
            item = QtWidgets.QListWidgetItem(text)
            item.setData(QtCore.Qt.UserRole, mod.get("id"))
            img_path = mod.get("imagem_path")
            if img_path and Path(img_path).is_file():
                pix = QtGui.QPixmap(img_path)
                if not pix.isNull():
                    thumb = pix.scaled(96, 96, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                    item.setIcon(QtGui.QIcon(thumb))
                    item.setSizeHint(QtCore.QSize(140, 110))
                else:
                    item.setSizeHint(QtCore.QSize(140, 64))
            else:
                item.setSizeHint(QtCore.QSize(140, 64))
            self.list_modulos.addItem(item)
        self.list_modulos.blockSignals(False)
        self._update_details(None)
        self._update_buttons()

    def _update_buttons(self) -> None:
        has_selection = bool(self.list_modulos.selectedItems())
        self.buttons.button(QtWidgets.QDialogButtonBox.Open).setEnabled(has_selection)

    def _selected_ids(self) -> List[int]:
        ids: List[int] = []
        for item in self.list_modulos.selectedItems():
            modulo_id = item.data(QtCore.Qt.UserRole)
            if modulo_id:
                ids.append(int(modulo_id))
        return ids

    def _update_details(self, modulo_id: Optional[int]) -> None:
        if modulo_id is None:
            self.lbl_nome.setText("Nome:")
            self.txt_descricao.clear()
            self._render_image(None)
            _montar_tabela_linhas(self.tabela_linhas, [])
            return
        data = self._module_data_cache.get(modulo_id)
        if data is None:
            try:
                data = svc_modulos.carregar_modulo_completo(self.session, modulo_id)
            except Exception:
                data = None
            if data:
                self._module_data_cache[modulo_id] = data
        if not data:
            self.lbl_nome.setText("Nome:")
            self.txt_descricao.clear()
            self._render_image(None)
            _montar_tabela_linhas(self.tabela_linhas, [])
            return
        self.lbl_nome.setText(f"Nome: {data.get('nome')}")
        self.txt_descricao.setPlainText(data.get("descricao") or "")
        self._render_image(data.get("imagem_path"))
        _montar_tabela_linhas(self.tabela_linhas, data.get("linhas") or [])

    def _render_image(self, path: Optional[str]) -> None:
        if path and Path(path).is_file():
            pix = QtGui.QPixmap(path)
            if not pix.isNull():
                self.lbl_imagem.setPixmap(pix.scaled(260, 260, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
                self.lbl_imagem.setToolTip(path)
                return
        self.lbl_imagem.setPixmap(QtGui.QPixmap())
        self.lbl_imagem.setText("Sem imagem")
        self.lbl_imagem.setToolTip("")

    # Slots --------------------------------------------------------------
    def _on_scope_changed(self, index: int) -> None:
        self._scope = "global" if index == 1 else "user"
        self._load_modules()
        self._rebuild_list()

    def _on_selection_changed(self) -> None:
        ids = self._selected_ids()
        first_id = ids[0] if ids else None
        self._update_details(first_id)
        self._update_buttons()

    def _on_accept(self) -> None:
        ids = self._selected_ids()
        if not ids:
            QtWidgets.QMessageBox.information(self, "Informação", "Selecione pelo menos um módulo.")
            return
        aggregated: List[Dict[str, Any]] = []
        for modulo_id in ids:
            data = self._module_data_cache.get(modulo_id)
            if data is None:
                try:
                    data = svc_modulos.carregar_modulo_completo(self.session, modulo_id)
                except Exception:
                    data = None
                if data:
                    self._module_data_cache[modulo_id] = data
            if not data:
                continue
            linhas = svc_modulos.preparar_linhas_para_importacao(
                data.get("linhas") or [],
                imagem_path=data.get("imagem_path"),
            )
            aggregated.extend(linhas)
        if not aggregated:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Nenhuma linha disponível para importar.")
            return
        self._selected_rows = aggregated
        self.accept()

    # Public API ---------------------------------------------------------
    def linhas_importadas(self) -> List[Dict[str, Any]]:
        return list(self._selected_rows)


class GerenciadorModulosDialog(QtWidgets.QDialog):
    """Permite renomear e editar descrição/imagem de módulos guardados (Utilizador/Global)."""

    def __init__(
        self,
        parent: QtWidgets.QWidget,
        session,
        current_user_id: Optional[int],
    ) -> None:
        super().__init__(parent)
        self.session = session
        self.current_user_id = current_user_id
        self._scope = "user"
        self._modules: List[Dict[str, Any]] = []
        self._module_data_cache: Dict[int, Dict[str, Any]] = {}
        self._selected_modulo_id: Optional[int] = None
        self._imagem_path: Optional[str] = None

        self.setWindowTitle("Gerenciador de Módulos")
        self._build_ui()
        _configurar_janela_dialog(self, default_width=1250, default_height=980)
        self._load_modules()
        self._rebuild_list()
        self._set_editor_enabled(False)

    # UI -----------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(QtWidgets.QWidget(), "Utilizador")
        self.tabs.addTab(QtWidgets.QWidget(), "Global")
        self.tabs.currentChanged.connect(self._on_scope_changed)
        layout.addWidget(self.tabs)

        search_row = QtWidgets.QHBoxLayout()
        lbl_search = QtWidgets.QLabel("Pesquisar módulos (use % para separar palavras):")
        self.edit_search = QtWidgets.QLineEdit()
        self.edit_search.setPlaceholderText("Ex: cozinha % 700")
        self.edit_search.textChanged.connect(self._rebuild_list)
        search_row.addWidget(lbl_search)
        search_row.addWidget(self.edit_search, 1)
        layout.addLayout(search_row)

        body = QtWidgets.QHBoxLayout()
        body.setSpacing(12)

        # Lista (esquerda)
        left = QtWidgets.QVBoxLayout()
        self.list_modulos = QtWidgets.QListWidget()
        self.list_modulos.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.list_modulos.setIconSize(QtCore.QSize(72, 72))
        self.list_modulos.setSpacing(4)
        self.list_modulos.itemSelectionChanged.connect(self._on_selection_changed)
        left.addWidget(self.list_modulos, 1)
        body.addLayout(left, 1)

        # Editor (direita)
        right = QtWidgets.QVBoxLayout()

        form = QtWidgets.QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)

        self.lbl_id = QtWidgets.QLabel("ID: -")
        self.lbl_id.setStyleSheet("color:#666;")

        self.ed_nome = QtWidgets.QLineEdit()
        self.ed_nome.setPlaceholderText("Nome do módulo")

        self.txt_descricao = QtWidgets.QTextEdit()
        self.txt_descricao.setPlaceholderText("Descrição do módulo (opcional)")
        self.txt_descricao.setTabChangesFocus(True)
        self.txt_descricao.setMinimumHeight(110)

        form.addWidget(QtWidgets.QLabel("Nome:"), 0, 0)
        form.addWidget(self.ed_nome, 0, 1, 1, 3)
        form.addWidget(self.lbl_id, 0, 4)

        form.addWidget(QtWidgets.QLabel("Descrição:"), 1, 0, QtCore.Qt.AlignTop)
        form.addWidget(self.txt_descricao, 1, 1, 1, 4)

        right.addLayout(form)

        img_row = QtWidgets.QHBoxLayout()
        img_row.setSpacing(10)
        self.lbl_imagem = QtWidgets.QLabel("Sem imagem")
        self.lbl_imagem.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_imagem.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.lbl_imagem.setMinimumSize(220, 200)
        self.lbl_imagem.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        img_row.addWidget(self.lbl_imagem, 2)

        img_btns = QtWidgets.QVBoxLayout()
        self.btn_escolher_imagem = QtWidgets.QPushButton("Escolher Imagem…")
        self.btn_escolher_imagem.setToolTip("Selecionar/alterar imagem do módulo.")
        self.btn_remover_imagem = QtWidgets.QPushButton("Remover Imagem")
        self.btn_remover_imagem.setToolTip("Remover a imagem associada ao módulo.")
        self.btn_escolher_imagem.clicked.connect(self._on_choose_image)
        self.btn_remover_imagem.clicked.connect(self._on_remove_image)
        img_btns.addWidget(self.btn_escolher_imagem)
        img_btns.addWidget(self.btn_remover_imagem)
        img_btns.addStretch(1)
        img_row.addLayout(img_btns, 1)
        right.addLayout(img_row, 3)

        right.addWidget(QtWidgets.QLabel("Peças do módulo (preview):"))
        self.tabela_linhas = QtWidgets.QTableWidget()
        self.tabela_linhas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.tabela_linhas.setMinimumHeight(160)
        right.addWidget(self.tabela_linhas, 2)

        body.addLayout(right, 2)
        layout.addLayout(body, 1)

        self.buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Close)
        self.btn_save = self.buttons.button(QtWidgets.QDialogButtonBox.Save)
        self.btn_save.setText("Guardar Alterações")
        self.btn_save.setToolTip(
            "Guardar alterações (nome/descrição/imagem) do módulo selecionado."
        )
        self.btn_move_to_global = self.buttons.addButton("Enviar p/ Global", QtWidgets.QDialogButtonBox.ActionRole)
        self.btn_move_to_global.setToolTip("Mover o módulo para Global (fica disponível para todos os utilizadores).")
        self.btn_move_to_user = self.buttons.addButton("Enviar p/ Utilizador", QtWidgets.QDialogButtonBox.ActionRole)
        self.btn_move_to_user.setToolTip("Mover o módulo para Utilizador (apenas disponível para o utilizador atual).")
        self.btn_delete = self.buttons.addButton("Eliminar", QtWidgets.QDialogButtonBox.DestructiveRole)
        self.btn_delete.setToolTip("Eliminar módulo selecionado (ação irreversível).")

        self.btn_save.clicked.connect(self._on_save)
        self.btn_move_to_global.clicked.connect(self._on_move_to_global)
        self.btn_move_to_user.clicked.connect(self._on_move_to_user)
        self.btn_delete.clicked.connect(self._on_delete)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    # Helpers ------------------------------------------------------------
    def _current_scope(self) -> str:
        return "global" if self.tabs.currentIndex() == 1 else "user"

    def _load_modules(self) -> None:
        self._scope = self._current_scope()
        try:
            self._modules = svc_modulos.listar_modulos_por_scope(self.session, self.current_user_id, self._scope)
        except Exception:
            self._modules = []

    def _filter_modules(self) -> List[Dict[str, Any]]:
        query = (self.edit_search.text() or "").casefold()
        tokens = [tok for tok in re.split(r"[\s%]+", query) if tok]
        if not tokens:
            return list(self._modules)
        filtered: List[Dict[str, Any]] = []
        for mod in self._modules:
            hay = f"{mod.get('nome','')} {mod.get('descricao','')}".casefold()
            if all(tok in hay for tok in tokens):
                filtered.append(mod)
        return filtered

    def _rebuild_list(self) -> None:
        selected_id = self._selected_modulo_id
        mods = self._filter_modules()
        self.list_modulos.blockSignals(True)
        self.list_modulos.clear()
        for mod in mods:
            text = mod.get("nome") or "Sem nome"
            owner = (mod.get("owner_name") or "").strip()
            if self._scope == "global" and owner:
                text = f"{text} (por {owner})"
            item = QtWidgets.QListWidgetItem(text)
            item.setData(QtCore.Qt.UserRole, mod.get("id"))
            img_path = mod.get("imagem_path")
            if img_path and Path(img_path).is_file():
                pix = QtGui.QPixmap(img_path)
                if not pix.isNull():
                    thumb = pix.scaled(72, 72, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                    item.setIcon(QtGui.QIcon(thumb))
            self.list_modulos.addItem(item)
        self.list_modulos.blockSignals(False)

        # Restaurar seleção
        if selected_id:
            for idx in range(self.list_modulos.count()):
                it = self.list_modulos.item(idx)
                if it and it.data(QtCore.Qt.UserRole) == selected_id:
                    self.list_modulos.setCurrentRow(idx)
                    break
        self._update_buttons()

    def _update_buttons(self) -> None:
        has_sel = bool(self.list_modulos.selectedItems())
        self.btn_save.setEnabled(has_sel)
        self.btn_delete.setEnabled(has_sel)
        # mover depende do separador atual
        self.btn_move_to_global.setEnabled(has_sel and self._scope == "user")
        self.btn_move_to_user.setEnabled(has_sel and self._scope == "global")

    def _selected_id(self) -> Optional[int]:
        items = self.list_modulos.selectedItems()
        if not items:
            return None
        modulo_id = items[0].data(QtCore.Qt.UserRole)
        return int(modulo_id) if modulo_id else None

    def _set_editor_enabled(self, enabled: bool) -> None:
        for w in (self.ed_nome, self.txt_descricao, self.btn_escolher_imagem, self.btn_remover_imagem, self.tabela_linhas):
            w.setEnabled(enabled)

    def _render_image(self, path: Optional[str]) -> None:
        if path and Path(path).is_file():
            pix = QtGui.QPixmap(path)
            if not pix.isNull():
                self._imagem_path = path
                # escala para o tamanho do label (evita imagem "cortada")
                target = self.lbl_imagem.size()
                tw = max(int(target.width()), 1)
                th = max(int(target.height()), 1)
                if tw < 50 or th < 50:
                    tw, th = 360, 320
                self.lbl_imagem.setPixmap(pix.scaled(tw, th, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
                self.lbl_imagem.setToolTip(path)
                return
        self._imagem_path = None
        self.lbl_imagem.setPixmap(QtGui.QPixmap())
        self.lbl_imagem.setText("Sem imagem")
        self.lbl_imagem.setToolTip("")

    def _load_modulo_details(self, modulo_id: int) -> None:
        data = self._module_data_cache.get(modulo_id)
        if data is None:
            try:
                data = svc_modulos.carregar_modulo_completo(self.session, modulo_id)
            except Exception:
                data = None
            if data:
                self._module_data_cache[modulo_id] = data
        if not data:
            self.lbl_id.setText("ID: -")
            self.ed_nome.clear()
            self.txt_descricao.clear()
            self._render_image(None)
            _montar_tabela_linhas(self.tabela_linhas, [])
            self._set_editor_enabled(False)
            return

        self.lbl_id.setText(f"ID: {data.get('id')}")
        self.ed_nome.setText(data.get("nome") or "")
        self.txt_descricao.setPlainText(data.get("descricao") or "")
        self._render_image(data.get("imagem_path"))
        _montar_tabela_linhas(self.tabela_linhas, data.get("linhas") or [])
        self._set_editor_enabled(True)

    # Slots --------------------------------------------------------------
    def _on_scope_changed(self, index: int) -> None:
        self._module_data_cache.clear()
        self._load_modules()
        self._rebuild_list()
        self._set_editor_enabled(False)

    def _on_selection_changed(self) -> None:
        modulo_id = self._selected_id()
        self._selected_modulo_id = modulo_id
        if not modulo_id:
            self._set_editor_enabled(False)
            self._update_buttons()
            return
        self._load_modulo_details(modulo_id)
        self._update_buttons()

    def _on_choose_image(self) -> None:
        base_dir = svc_modulos.pasta_imagens_base(self.session)
        start_dir = Path(base_dir) if base_dir else Path.home()
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Selecionar imagem do módulo",
            str(start_dir),
            "Imagens (*.png *.jpg *.jpeg *.bmp *.gif);;Todos os ficheiros (*.*)",
        )
        if file_path:
            self._render_image(file_path)

    def _on_remove_image(self) -> None:
        self._render_image(None)

    def _on_save(self) -> None:
        modulo_id = self._selected_modulo_id
        if not modulo_id:
            return
        nome = (self.ed_nome.text() or "").strip()
        descricao = self.txt_descricao.toPlainText()
        if not nome:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Indique um nome para o módulo.")
            return
        is_global = self._current_scope() == "global"
        try:
            svc_modulos.atualizar_modulo_metadata(
                self.session,
                modulo_id=modulo_id,
                user_id=self.current_user_id,
                nome=nome,
                descricao=descricao,
                imagem_path=self._imagem_path,
                is_global=is_global,
            )
            self.session.commit()
        except Exception as exc:
            try:
                self.session.rollback()
            except Exception:
                pass
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao guardar alterações: {exc}")
            return

        # Atualizar lista e cache
        self._module_data_cache.pop(modulo_id, None)
        self._load_modules()
        self._rebuild_list()
        QtWidgets.QMessageBox.information(self, "Sucesso", "Módulo atualizado com sucesso.")

    def _move_modulo(self, *, target_scope: str) -> None:
        modulo_id = self._selected_modulo_id
        if not modulo_id:
            return
        target_scope = (target_scope or "").lower()
        if target_scope not in {"user", "global"}:
            return

        nome = (self.ed_nome.text() or "").strip()
        descricao = self.txt_descricao.toPlainText()
        if not nome:
            QtWidgets.QMessageBox.warning(self, "Aviso", "Indique um nome para o módulo.")
            return

        is_global_target = target_scope == "global"
        if is_global_target:
            msg = (
                "Enviar este módulo para Global?\n\n"
                "O módulo ficará disponível para todos os utilizadores."
            )
        else:
            msg = (
                "Enviar este módulo para Utilizador?\n\n"
                "O módulo deixará de estar disponível no separador Global (para outros utilizadores)."
            )
        resp = QtWidgets.QMessageBox.question(self, "Confirmar", msg)
        if resp != QtWidgets.QMessageBox.Yes:
            return

        try:
            svc_modulos.atualizar_modulo_metadata(
                self.session,
                modulo_id=modulo_id,
                user_id=self.current_user_id,
                nome=nome,
                descricao=descricao,
                imagem_path=self._imagem_path,
                is_global=is_global_target,
            )
            self.session.commit()
        except Exception as exc:
            try:
                self.session.rollback()
            except Exception:
                pass
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao mover módulo: {exc}")
            return

        # refresh e trocar separador
        self._module_data_cache.pop(modulo_id, None)
        self._selected_modulo_id = modulo_id
        if is_global_target:
            self.tabs.setCurrentIndex(1)
        else:
            self.tabs.setCurrentIndex(0)
        self._load_modules()
        self._rebuild_list()
        QtWidgets.QMessageBox.information(self, "Sucesso", "Módulo movido com sucesso.")

    def _on_move_to_global(self) -> None:
        self._move_modulo(target_scope="global")

    def _on_move_to_user(self) -> None:
        self._move_modulo(target_scope="user")

    def _on_delete(self) -> None:
        modulo_id = self._selected_modulo_id
        if not modulo_id:
            return
        nome = (self.ed_nome.text() or "").strip() or "(sem nome)"
        if self._scope == "global":
            msg = (
                f"Eliminar o módulo '{nome}'?\n\n"
                "Atenção: é um módulo Global e ficará indisponível para todos os utilizadores.\n"
                "Esta ação não pode ser desfeita."
            )
        else:
            msg = (
                f"Eliminar o módulo '{nome}'?\n\n"
                "Esta ação não pode ser desfeita."
            )
        resp = QtWidgets.QMessageBox.question(self, "Confirmar eliminação", msg)
        if resp != QtWidgets.QMessageBox.Yes:
            return
        try:
            svc_modulos.eliminar_modulo(self.session, modulo_id=modulo_id, user_id=self.current_user_id)
            self.session.commit()
        except Exception as exc:
            try:
                self.session.rollback()
            except Exception:
                pass
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao eliminar módulo: {exc}")
            return

        self._module_data_cache.pop(modulo_id, None)
        self._selected_modulo_id = None
        self.ed_nome.clear()
        self.txt_descricao.clear()
        self._render_image(None)
        _montar_tabela_linhas(self.tabela_linhas, [])
        self._set_editor_enabled(False)
        self._load_modules()
        self._rebuild_list()
        QtWidgets.QMessageBox.information(self, "Sucesso", "Módulo eliminado com sucesso.")
