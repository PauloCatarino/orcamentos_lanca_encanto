from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from PySide6 import QtCore, QtGui, QtWidgets

try:
    from PySide6.QtPdf import QPdfDocument
except Exception:  # pragma: no cover - optional dependency
    QPdfDocument = None

from Martelo_Orcamentos_V2.app.services import producao_processos as svc_producao
from Martelo_Orcamentos_V2.app.services import pdf_printer
from Martelo_Orcamentos_V2.ui.models.qt_table import SimpleTableModel
from Martelo_Orcamentos_V2.ui.workers.pdf_scanner_worker import PDFScannerWorker


class ProducaoPDFManagerDialog(QtWidgets.QDialog):
    def __init__(self, *, session, producao, parent=None):
        super().__init__(parent)
        self.session = session
        self.producao = producao
        self._scan_thread: Optional[QtCore.QThread] = None
        self._scan_worker: Optional[PDFScannerWorker] = None
        self._syncing_a4_a3 = False
        self._preview_doc = None
        self._preview_buffer: Optional[QtCore.QBuffer] = None
        self._preview_path: Optional[str] = None

        self.setWindowTitle("Imprimir PDFs")
        self.resize(1650, 980)
        self.setMinimumWidth(1400)
        self.setMinimumHeight(900)
        self._build_ui()
        self._start_scan()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.addSpacing(12)

        header_row = QtWidgets.QHBoxLayout()
        left_header = QtWidgets.QVBoxLayout()
        lbl_proc = QtWidgets.QLabel(f"Processo: {getattr(self.producao, 'codigo_processo', '-')}")
        lbl_proc.setStyleSheet("font-weight:bold;")
        left_header.addWidget(lbl_proc)

        path = str(getattr(self.producao, "pasta_servidor", "") or "")
        self.lbl_path = QtWidgets.QLabel(path or "(pasta servidor nao definida)")
        self.lbl_path.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.lbl_path.setWordWrap(True)
        self.lbl_path.setStyleSheet("color:#666;")
        left_header.addWidget(self.lbl_path)
        header_row.addLayout(left_header, 1)

        preview_box = QtWidgets.QGroupBox("Pre-visualizacao PDF")
        preview_box.setMinimumWidth(560)
        preview_layout = QtWidgets.QVBoxLayout(preview_box)
        self.lbl_preview = QtWidgets.QLabel("Selecione um PDF na tabela.")
        self.lbl_preview.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_preview.setFrameShape(QtWidgets.QFrame.Box)
        self.lbl_preview.setStyleSheet("background:#fafafa; color:#555;")
        self.lbl_preview.setMinimumSize(540, 320)
        self.lbl_preview.setScaledContents(False)
        self.lbl_preview_name = QtWidgets.QLabel("")
        self.lbl_preview_name.setStyleSheet("color:#666;")
        preview_layout.addWidget(self.lbl_preview, 1)
        preview_layout.addWidget(self.lbl_preview_name)
        header_row.addWidget(preview_box)
        layout.addLayout(header_row)

        buttons = QtWidgets.QHBoxLayout()
        self.btn_reload = QtWidgets.QPushButton("Recarregar")
        self.btn_reload.clicked.connect(self._start_scan)
        self.btn_reload.setToolTip("Recarregar a lista de PDFs da pasta do processo.")
        self.btn_save = QtWidgets.QPushButton("Guardar Config")
        self.btn_save.clicked.connect(self._on_save_config)
        self.btn_save.setToolTip("Guardar configuracoes de impressao (em desenvolvimento).")
        self.btn_history = QtWidgets.QPushButton("Historico")
        self.btn_history.clicked.connect(self._on_history)
        self.btn_history.setToolTip("Mostrar historico de impressoes (em desenvolvimento).")
        self.btn_print = QtWidgets.QPushButton("Imprimir Selecionados")
        self.btn_print.clicked.connect(self._on_print_selected)
        self.btn_print.setToolTip("Enviar os PDFs selecionados para impressao.")
        buttons.addWidget(self.btn_reload)
        buttons.addWidget(self.btn_save)
        buttons.addWidget(self.btn_history)
        buttons.addWidget(self.btn_print)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.lbl_status = QtWidgets.QLabel("")
        self.lbl_status.setStyleSheet("color:#555;")
        selection_row = QtWidgets.QHBoxLayout()
        self.btn_select_all = QtWidgets.QPushButton("Selecionar tudo")
        self.btn_select_all.setToolTip("Selecionar todos os PDFs.")
        self.btn_select_all.clicked.connect(lambda: self._set_all_selected(True))
        self.btn_select_none = QtWidgets.QPushButton("Limpar selecao")
        self.btn_select_none.setToolTip("Desmarcar todos os PDFs.")
        self.btn_select_none.clicked.connect(lambda: self._set_all_selected(False))
        selection_row.addWidget(self.btn_select_all)
        selection_row.addWidget(self.btn_select_none)
        selection_row.addStretch(1)
        selection_row.addWidget(self.lbl_status)
        layout.addLayout(selection_row)

        self.table = QtWidgets.QTableView(self)
        self.model = SimpleTableModel(
            columns=[
                {"header": "", "attr": "selected", "type": "bool", "editable": True},
                ("Prioridade", "priority"),
                ("PDF", "file_name"),
                ("Categoria", "category"),
                ("Origem", "origin"),
                ("Qt", "quantity"),
                {"header": "A4", "attr": "is_a4", "type": "bool", "editable": True},
                {"header": "A3", "attr": "is_a3", "type": "bool", "editable": True},
                ("Orientacao", "orientation"),
                ("Paginas", "page_range"),
                {"header": "Duplex", "attr": "double_sided", "type": "bool", "editable": True},
                ("Cor", "color_mode"),
            ]
        )
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSortingEnabled(True)
        self.table.setItemDelegateForColumn(8, _OrientationDelegate(self.table))
        self.model.dataChanged.connect(self._on_table_data_changed)
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table, 1)
        self._apply_column_sizes()

        btn_close = QtWidgets.QPushButton("Fechar")
        btn_close.clicked.connect(self.reject)
        btn_close.setToolTip("Fechar a janela de impressao.")
        layout.addWidget(btn_close, alignment=QtCore.Qt.AlignRight)

    def _start_scan(self) -> None:
        if self._scan_thread:
            try:
                if self._scan_thread.isRunning():
                    return
            except RuntimeError:
                self._scan_thread = None
        folder = str(getattr(self.producao, "pasta_servidor", "") or "")
        if not folder:
            self._set_status("Pasta servidor nao definida.")
            self.model.set_rows([])
            return

        self._set_status("A procurar PDFs...")
        self.btn_print.setEnabled(False)
        self.btn_reload.setEnabled(False)

        cut_rite = self._calc_nome_plano_cut_rite()
        imos = self._calc_nome_enc_imos_ix()

        worker = PDFScannerWorker(
            folder_path=folder,
            nome_plano_cut_rite=cut_rite,
            nome_enc_imos_ix=imos,
            recursive=False,
        )
        thread = QtCore.QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_scan_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_scan_thread_finished)
        self._scan_worker = worker
        self._scan_thread = thread
        thread.start()

    def _on_scan_finished(self, rows: Sequence[dict], error: str) -> None:
        if error:
            self._set_status(f"Erro a procurar PDFs: {error}")
            self.model.set_rows([])
            self._update_preview(None)
        else:
            normalized = self._normalize_rows(rows)
            self.model.set_rows(normalized)
            self._set_status(f"{len(normalized)} PDF(s) encontrados.")
            self._apply_column_sizes()
            self._select_first_row()
        self.btn_print.setEnabled(True)
        self.btn_reload.setEnabled(True)

    def _normalize_rows(self, rows: Sequence[dict]) -> list[dict]:
        normalized: list[dict] = []
        for row in rows:
            paper = str(row.get("paper_size") or "A4").upper()
            is_a3 = paper == "A3"
            is_a4 = not is_a3
            orientation = str(row.get("orientation") or "vertical").strip()
            orientation_norm = "Horizontal" if orientation.lower().startswith("h") else "Vertical"
            normalized.append(
                {
                    **row,
                    "is_a4": is_a4,
                    "is_a3": is_a3,
                    "orientation": orientation_norm,
                }
            )
        return normalized

    def _on_scan_thread_finished(self) -> None:
        self._scan_thread = None
        self._scan_worker = None

    def _apply_column_sizes(self) -> None:
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        widths = {
            0: 36,   # select
            1: 80,   # prioridade
            2: 320,  # PDF
            3: 180,  # categoria
            4: 90,   # origem
            5: 50,   # qt
            6: 40,   # A4
            7: 40,   # A3
            8: 110,  # orientacao
            9: 80,   # paginas
            10: 60,  # duplex
            11: 70,  # cor
        }
        for col, width in widths.items():
            try:
                header.resizeSection(col, width)
            except Exception:
                continue
        header.setStretchLastSection(True)

    def _set_all_selected(self, selected: bool) -> None:
        if self.model.rowCount() <= 0:
            return
        for row in range(self.model.rowCount()):
            row_data = self.model.row(row)
            if isinstance(row_data, dict):
                row_data["selected"] = bool(selected)
        left = self.model.index(0, 0)
        right = self.model.index(self.model.rowCount() - 1, 0)
        self.model.dataChanged.emit(left, right)

    def _select_first_row(self) -> None:
        if self.model.rowCount() <= 0:
            self._update_preview(None)
            return
        self.table.selectRow(0)
        self._update_preview_for_row(0)

    def _on_selection_changed(self, *_args) -> None:
        selection = self.table.selectionModel()
        if not selection:
            self._update_preview(None)
            return
        rows = selection.selectedRows()
        if not rows:
            self._update_preview(None)
            return
        self._update_preview_for_row(rows[0].row())

    def _update_preview_for_row(self, row: int) -> None:
        row_data = self.model.row(row)
        if not isinstance(row_data, dict):
            self._update_preview(None)
            return
        self._update_preview(str(row_data.get("file_path") or ""))

    def _update_preview(self, path: Optional[str]) -> None:
        if path and path == self._preview_path and self._preview_doc and self._preview_doc.pageCount() > 0:
            self._render_preview()
            return
        self._preview_path = path if path else None
        self._preview_buffer = None
        if not path:
            self.lbl_preview.setPixmap(QtGui.QPixmap())
            self.lbl_preview.setText("Selecione um PDF na tabela.")
            self.lbl_preview_name.setText("")
            return
        pdf_path = Path(path)
        if not pdf_path.is_file():
            self.lbl_preview.setPixmap(QtGui.QPixmap())
            self.lbl_preview.setText("PDF nao encontrado.")
            self.lbl_preview_name.setText(str(pdf_path.name))
            return
        self.lbl_preview_name.setText(pdf_path.name)
        if QPdfDocument is None:
            self.lbl_preview.setPixmap(QtGui.QPixmap())
            self.lbl_preview.setText("Pre-visualizacao PDF indisponivel.")
            return
        if self._preview_doc is None:
            self._preview_doc = QPdfDocument(self)
        if self._load_preview_document(pdf_path):
            if self._render_preview():
                return
        self.lbl_preview.setPixmap(QtGui.QPixmap())
        self.lbl_preview.setText("PDF selecionado (sem preview).")

    def _load_preview_document(self, pdf_path: Path) -> bool:
        if QPdfDocument is None:
            return False
        self._preview_doc.load(str(pdf_path))
        if self._preview_doc.pageCount() > 0:
            return True
        try:
            data = pdf_path.read_bytes()
        except Exception:
            return False
        buffer = QtCore.QBuffer(self)
        buffer.setData(QtCore.QByteArray(data))
        buffer.open(QtCore.QIODevice.ReadOnly)
        self._preview_buffer = buffer
        self._preview_doc.load(buffer)
        return self._preview_doc.pageCount() > 0

    def _render_preview(self) -> bool:
        if QPdfDocument is None:
            return False
        if self._preview_doc is None or self._preview_doc.pageCount() <= 0:
            return False
        page_size = self._preview_doc.pagePointSize(0)
        if page_size.width() <= 0 or page_size.height() <= 0:
            return False
        target = self.lbl_preview.size()
        if target.width() < 10 or target.height() < 10:
            target = QtCore.QSize(420, 300)
        scale = min(target.width() / page_size.width(), target.height() / page_size.height())
        img_size = QtCore.QSize(int(page_size.width() * scale), int(page_size.height() * scale))
        image = QtGui.QImage(img_size, QtGui.QImage.Format_ARGB32)
        image.fill(QtCore.Qt.white)
        rendered = None
        try:
            rendered = self._preview_doc.render(0, img_size)
        except TypeError:
            rendered = None
        except Exception:
            rendered = None
        if isinstance(rendered, QtGui.QImage) and not rendered.isNull():
            self.lbl_preview.setPixmap(QtGui.QPixmap.fromImage(rendered))
            self.lbl_preview.setText("")
            return True

        supports_flags = False
        flags = 0
        try:
            if QPdfDocument is not None and hasattr(QPdfDocument, "RenderFlags"):
                flags = QPdfDocument.RenderFlags(0)
                supports_flags = True
        except Exception:
            flags = 0
            supports_flags = False
        painter = QtGui.QPainter(image)
        try:
            rect = QtCore.QRectF(QtCore.QPointF(0, 0), QtCore.QSizeF(img_size))
            if supports_flags:
                self._preview_doc.render(0, painter, rect, flags)
            else:
                self._preview_doc.render(0, painter, rect)
        finally:
            painter.end()
        self.lbl_preview.setPixmap(QtGui.QPixmap.fromImage(image))
        self.lbl_preview.setText("")
        return True

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if self._preview_path:
            self._update_preview(self._preview_path)

    def _on_table_data_changed(
        self,
        top_left: QtCore.QModelIndex,
        bottom_right: QtCore.QModelIndex,
        _roles=None,
    ) -> None:
        if self._syncing_a4_a3:
            return
        self._syncing_a4_a3 = True
        try:
            for row in range(top_left.row(), bottom_right.row() + 1):
                row_data = self.model.row(row)
                if not isinstance(row_data, dict):
                    continue
                if row_data.get("is_a3"):
                    row_data["is_a4"] = False
                    row_data["paper_size"] = "A3"
                elif row_data.get("is_a4"):
                    row_data["is_a3"] = False
                    row_data["paper_size"] = "A4"
                else:
                    row_data["is_a4"] = True
                    row_data["paper_size"] = "A4"
                self._emit_row_changed(row)
        finally:
            self._syncing_a4_a3 = False

    def _emit_row_changed(self, row: int) -> None:
        if row < 0 or row >= self.model.rowCount():
            return
        left = self.model.index(row, 0)
        right = self.model.index(row, self.model.columnCount() - 1)
        self.model.dataChanged.emit(left, right)

    def _on_print_selected(self) -> None:
        rows = [r for r in self.model._rows if isinstance(r, dict) and r.get("selected")]
        if not rows:
            QtWidgets.QMessageBox.information(self, "Imprimir PDFs", "Nenhum PDF selecionado.")
            return
        sumatra = pdf_printer.resolve_sumatra_path(self.session)
        if sumatra is None:
            if any(_paper_mismatch(row) for row in rows):
                QtWidgets.QMessageBox.information(
                    self,
                    "Imprimir PDFs",
                    "SumatraPDF nao encontrado. Para imprimir A4 quando o PDF esta em A3,\n"
                    "instale o SumatraPDF ou configure o caminho em Settings.\n"
                    "A impressao vai usar o leitor PDF predefinido.",
                )
        for row in rows:
            row["paper_size"] = "A3" if row.get("is_a3") else "A4"
            row["quantity"] = _safe_int(row.get("quantity"), default=1)
            row["orientation"] = str(row.get("orientation") or "vertical")
            row["page_range"] = str(row.get("page_range") or "all")
            row["double_sided"] = bool(row.get("double_sided"))
            row["color_mode"] = str(row.get("color_mode") or "color")

        pdf_printer.print_pdf_batch(rows, db=self.session)
        QtWidgets.QMessageBox.information(self, "Imprimir PDFs", "Impressao enviada para a fila.")

    def _on_save_config(self) -> None:
        QtWidgets.QMessageBox.information(self, "Guardar Config", "Funcionalidade em desenvolvimento.")

    def _on_history(self) -> None:
        QtWidgets.QMessageBox.information(self, "Historico", "Funcionalidade em desenvolvimento.")

    def _set_status(self, text: str) -> None:
        self.lbl_status.setText(text or "")

    def _calc_nome_plano_cut_rite(self) -> Optional[str]:
        try:
            return svc_producao.gerar_nome_plano_cut_rite(
                getattr(self.producao, "ano", ""),
                getattr(self.producao, "num_enc_phc", ""),
                getattr(self.producao, "versao_obra", ""),
                getattr(self.producao, "versao_plano", ""),
                nome_cliente_simplex=getattr(self.producao, "nome_cliente_simplex", None),
                nome_cliente=getattr(self.producao, "nome_cliente", None),
                ref_cliente=getattr(self.producao, "ref_cliente", None),
            )
        except Exception:
            return None

    def _calc_nome_enc_imos_ix(self) -> Optional[str]:
        try:
            return svc_producao.gerar_nome_enc_imos_ix(
                getattr(self.producao, "ano", ""),
                getattr(self.producao, "num_enc_phc", ""),
                getattr(self.producao, "versao_obra", ""),
                nome_cliente_simplex=getattr(self.producao, "nome_cliente_simplex", None),
                nome_cliente=getattr(self.producao, "nome_cliente", None),
                ref_cliente=getattr(self.producao, "ref_cliente", None),
            )
        except Exception:
            return None


def _safe_int(value, *, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(str(value).replace(",", ".")))
    except Exception:
        return default


def _paper_mismatch(row: dict) -> bool:
    page_size = str(row.get("page_size") or "").upper()
    paper_size = str(row.get("paper_size") or "").upper()
    if not page_size or not paper_size:
        return False
    return page_size != paper_size


class _OrientationDelegate(QtWidgets.QStyledItemDelegate):
    def createEditor(self, parent, option, index):  # type: ignore[override]
        editor = QtWidgets.QComboBox(parent)
        editor.addItems(["Horizontal", "Vertical"])
        return editor

    def setEditorData(self, editor, index):  # type: ignore[override]
        value = str(index.data(QtCore.Qt.EditRole) or "")
        idx = editor.findText(value)
        if idx < 0:
            value = value.strip().lower()
            for i in range(editor.count()):
                if editor.itemText(i).lower() == value:
                    idx = i
                    break
        if idx < 0:
            idx = editor.findText("Horizontal")
        if idx < 0:
            idx = 0
        editor.setCurrentIndex(idx)

    def setModelData(self, editor, model, index):  # type: ignore[override]
        model.setData(index, editor.currentText(), QtCore.Qt.EditRole)
