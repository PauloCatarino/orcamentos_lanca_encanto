# ui/pages/materias_primas.py







from __future__ import annotations















import os







import subprocess







import sys







from decimal import Decimal







from typing import List







from pathlib import Path















from PySide6 import QtCore, QtWidgets, QtGui







from PySide6.QtCore import Qt, QTimer







from PySide6.QtWidgets import QHeaderView, QMessageBox, QStyle















from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.services import pesquisa_ia as svc_ia






from Martelo_Orcamentos_V2.app.services.materias_primas import (







    DEFAULT_MATERIAS_BASE_PATH,







    KEY_MATERIAS_BASE_PATH,







    get_all_columns,







    get_base_path,







    get_user_layout,







    import_materias_primas,







    list_materias_primas,







    save_user_layout,







)















from Martelo_Orcamentos_V2.app.services.settings import get_setting







from ..models.qt_table import SimpleTableModel















# ----------------- helpers de formatação -----------------







def _format_decimal(value, places: int = 2) -> str:







    """Decimal com N casas, usado como fallback geral."""







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


def _excel_like_icon(size: int = 16) -> QtGui.QIcon:
    pixmap = QtGui.QPixmap(size, size)
    pixmap.fill(QtCore.Qt.transparent)

    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

    rect = QtCore.QRectF(1, 1, size - 2, size - 2)
    painter.setPen(QtGui.QPen(QtGui.QColor("#1F6F43"), 1))
    painter.setBrush(QtGui.QColor("#217346"))
    painter.drawRoundedRect(rect, 2.5, 2.5)

    fold = QtGui.QPolygonF(
        [
            QtCore.QPointF(size - 5.5, 1.5),
            QtCore.QPointF(size - 1.5, 1.5),
            QtCore.QPointF(size - 1.5, 5.5),
        ]
    )
    painter.setPen(QtCore.Qt.NoPen)
    painter.setBrush(QtGui.QColor("#DFF1E5"))
    painter.drawPolygon(fold)

    painter.setPen(QtGui.QPen(QtGui.QColor("white"), 2))
    painter.drawLine(int(size * 0.28), int(size * 0.32), int(size * 0.48), int(size * 0.50))
    painter.drawLine(int(size * 0.48), int(size * 0.50), int(size * 0.28), int(size * 0.68))
    painter.drawLine(int(size * 0.56), int(size * 0.32), int(size * 0.76), int(size * 0.32))
    painter.drawLine(int(size * 0.56), int(size * 0.50), int(size * 0.76), int(size * 0.50))
    painter.drawLine(int(size * 0.56), int(size * 0.68), int(size * 0.76), int(size * 0.68))
    painter.end()

    return QtGui.QIcon(pixmap)















def _fmt_eur(v) -> str:







    """Moeda em euros com 2 casas (ex.: 12.36€)."""







    if v in (None, ""):







        return ""







    d = Decimal(str(v))







    return f"{d:.2f}€"















def _fmt_pct(v) -> str:







    """Percentagem com 2 casas (assume base fracionária: 0.10 → 10.00%)."""







    if v in (None, ""):







        return ""







    d = Decimal(str(v)) * Decimal("100")







    return f"{d:.2f}%"























def _fmt_stock(v) -> str:







    if v in (None, ""):







        return "0"







    try:







        return "1" if Decimal(str(v)) >= 1 else "0"







    except Exception:







        return "0"























def _fmt_int(v) -> str:







    """Inteiro sem casas (para dimensões de placas)."""







    if v in (None, ""):







        return ""







    try:







        d = Decimal(str(v))







        return f"{int(d)}"







    except Exception:







        try:







            return f"{int(float(v))}"







        except Exception:







            return str(v)















# ----------------- diálogo de colunas -----------------







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















# Dialogo de Pesquisa IA
class PesquisaIADialog(QtWidgets.QDialog):

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Pesquisa IA - Materias Primas")
        self.resize(1800, 1300)
        self.setMinimumWidth(1400)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        form_row = QtWidgets.QHBoxLayout()
        form_row.addWidget(QtWidgets.QLabel("Pesquisa:"))
        self.ed_query = QtWidgets.QLineEdit()
        self.ed_query.setPlaceholderText("Digite termos a pesquisar nos catálogos/ficheiros curados…")
        form_row.addWidget(self.ed_query, 1)

        form_row.addWidget(QtWidgets.QLabel("Top:"))
        self.sp_top = QtWidgets.QSpinBox()
        self.sp_top.setRange(1, 50)
        self.sp_top.setValue(10)
        form_row.addWidget(self.sp_top)

        self.btn_search = QtWidgets.QPushButton("Pesquisar")
        self.btn_search.clicked.connect(self._on_search)
        form_row.addWidget(self.btn_search)

        layout.addLayout(form_row)

        self.table = QtWidgets.QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Score", "Fornecedor", "Ficheiro", "Página", "Snippet", "Caminho"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        header.setDefaultSectionSize(150)
        header.resizeSection(0, 80)
        header.resizeSection(1, 140)
        header.resizeSection(2, 240)
        header.resizeSection(3, 60)
        header.resizeSection(4, 420)
        header.resizeSection(5, 280)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self._open_selected)
        layout.addWidget(self.table, 1)

        btn_open = QtWidgets.QPushButton("Abrir ficheiro selecionado")
        btn_open.clicked.connect(self._open_selected)
        layout.addWidget(btn_open)

        # Resultados específicos do Excel 12_Placas_Referencias_COMPLETO.xlsx
        self.lbl_excel = QtWidgets.QLabel("Resultados (12_Placas_Referencias_COMPLETO.xlsx)")
        self.lbl_excel.setStyleSheet("font-weight: 600; color: #333;")
        layout.addWidget(self.lbl_excel)

        self.table_excel = QtWidgets.QTableWidget(0, 4)
        self.table_excel.setHorizontalHeaderLabels(["Score", "Folha", "Linha", "Conteúdo"])
        header_x = self.table_excel.horizontalHeader()
        header_x.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        header_x.resizeSection(0, 70)
        header_x.resizeSection(1, 160)
        header_x.resizeSection(2, 80)
        header_x.resizeSection(3, 900)
        self.table_excel.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table_excel.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table_excel, 1)

        self.btn_open_excel = QtWidgets.QPushButton("Abrir ficheiro Excel de referências")
        self.btn_open_excel.clicked.connect(self._open_excel_file)
        layout.addWidget(self.btn_open_excel)

        self.summary = QtWidgets.QTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setMinimumHeight(80)
        self.summary.setStyleSheet("color:#333;")
        layout.addWidget(self.summary)

        self.btn_ia_answer = QtWidgets.QPushButton("Gerar resposta IA")
        self.btn_ia_answer.clicked.connect(self.on_generate_answer)
        layout.addWidget(self.btn_ia_answer)

        self.lbl_status = QtWidgets.QLabel("")
        self.lbl_status.setStyleSheet("color:#555;")
        layout.addWidget(self.lbl_status)

    def _set_status(self, text: str) -> None:
        self.lbl_status.setText(text)

    def _on_search(self) -> None:
        query = (self.ed_query.text() or "").strip()
        if not query:
            self._set_status("Indique um texto para pesquisar.")
            return
        top_k = int(self.sp_top.value())
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            results = svc_ia.buscar(self.db, query, top_k=top_k)
            excel_results = svc_ia.buscar_excel(self.db, query, top_k=top_k)
        except Exception as exc:
            results = []
            excel_results = []
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha na pesquisa IA: {exc}")
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

        # Reordenar dando bónus para matches literais
        tokens = [t for t in query.lower().split() if t]
        if tokens and results:
            for r in results:
                hay = f"{r.get('snippet','')} {r.get('ficheiro','')}".lower()
                if all(tok in hay for tok in tokens):
                    r["score"] = float(r.get("score", 0.0)) + 0.2
                elif any(tok in hay for tok in tokens):
                    r["score"] = float(r.get("score", 0.0)) + 0.1
            results.sort(key=lambda x: x.get("score", 0.0), reverse=True)

        self.table.setRowCount(0)
        for row in results:
            r = self.table.rowCount()
            self.table.insertRow(r)
            itm_score = QtWidgets.QTableWidgetItem(f"{row.get('score',0):.4f}")
            itm_for = QtWidgets.QTableWidgetItem(row.get("fornecedor") or "")
            itm_file = QtWidgets.QTableWidgetItem(row.get("ficheiro") or "")
            itm_page = QtWidgets.QTableWidgetItem(str(row.get("pagina") or ""))
            itm_snip = QtWidgets.QTableWidgetItem(row.get("snippet") or "")
            itm_path = QtWidgets.QTableWidgetItem(row.get("caminho") or "")

            # Tooltips com conteúdo completo
            full_snip = row.get("snippet") or ""
            if full_snip:
                itm_snip.setToolTip(full_snip)
            full_path = row.get("caminho") or ""
            if full_path:
                itm_path.setToolTip(full_path)
            if row.get("ficheiro"):
                itm_file.setToolTip(row.get("ficheiro"))

            self.table.setItem(r, 0, itm_score)
            self.table.setItem(r, 1, itm_for)
            self.table.setItem(r, 2, itm_file)
            self.table.setItem(r, 3, itm_page)
            self.table.setItem(r, 4, itm_snip)
            self.table.setItem(r, 5, itm_path)
        self.table.resizeColumnsToContents()

        # Excel results table
        self._fill_excel_results(excel_results)

        self._set_status(f"{len(results)} resultado(s) IA | {len(excel_results)} linha(s) Excel.")
        self._update_summary(results, tokens, excel_results)

    def _update_summary(self, results: list, tokens: list[str], excel_results: list[dict] | None = None) -> None:
        tokens = [t for t in tokens if t]
        # prefer resultados cujo snippet contém todos os tokens; senão usa top 3
        filtered = []
        for r in results:
            hay = f"{r.get('snippet','')} {r.get('ficheiro','')}".lower()
            if all(tok in hay for tok in tokens):
                filtered.append(r)
        use_results = filtered if filtered else results

        parts = []
        for idx, row in enumerate(use_results[:3], 1):
            snip = row.get("snippet") or ""
            file = row.get("ficheiro") or ""
            page = row.get("pagina") or ""
            parts.append(f"{idx}) [{file} pág. {page}] {snip}")

        # se nada relevante em IA, tentar excel
        if not parts and excel_results:
            for idx, row in enumerate(excel_results[:3], 1):
                snip = row.get("snippet") or ""
                folha = row.get("folha") or ""
                linha = row.get("linha") or ""
                parts.append(f"{idx}) [Excel {folha} linha {linha}] {snip}")

        if not parts:
            self.summary.setPlainText("")
            return

        text = "\n\n".join(parts)
        if tokens:
            import re
            html = text.replace("\n", "<br>")
            for tok in tokens:
                pattern = re.compile(re.escape(tok), re.IGNORECASE)
                html = pattern.sub(lambda m: f"<b>{m.group(0)}</b>", html)
            self.summary.setHtml(html)
        else:
            self.summary.setPlainText(text)

    def _collect_table_results(self, max_rows: int = 10) -> list[dict]:
        items: list[dict] = []
        rows = min(self.table.rowCount(), max_rows)
        for r in range(rows):
            items.append({
                "score": self.table.item(r, 0).text() if self.table.item(r, 0) else "",
                "fornecedor": self.table.item(r, 1).text() if self.table.item(r, 1) else "",
                "ficheiro": self.table.item(r, 2).text() if self.table.item(r, 2) else "",
                "pagina": self.table.item(r, 3).text() if self.table.item(r, 3) else "",
                "snippet": self.table.item(r, 4).text() if self.table.item(r, 4) else "",
            })
        return items

    def _collect_excel_rows(self, max_rows: int = 10) -> list[dict]:
        items: list[dict] = []
        rows = min(self.table_excel.rowCount(), max_rows)
        if rows == 0:
            return items
        headers = [self.table_excel.horizontalHeaderItem(c).text() for c in range(self.table_excel.columnCount())]
        for r in range(rows):
            row_data = {}
            for c, h in enumerate(headers):
                cell = self.table_excel.item(r, c)
                row_data[h] = cell.text() if cell else ""
            items.append(row_data)
        return items

    def _build_text_answer(self, query: str) -> str:
        ia_rows = self._collect_table_results(max_rows=5)
        excel_rows = self._collect_excel_rows(max_rows=5)
        if not ia_rows and not excel_rows:
            return f"Não encontrei resultados claros para: {query!r}."

        partes = [f"Resumo da pesquisa por {query!r}:"]
        if ia_rows:
            refs = {r.get('ficheiro') for r in ia_rows if r.get('ficheiro')}
            fornecedores = {r.get('fornecedor') for r in ia_rows if r.get('fornecedor')}
            partes.append(f"- Resultados IA: {len(ia_rows)} linha(s).")
            if fornecedores:
                partes.append(f"  Fornecedores: {', '.join(sorted(fornecedores))}.")
            if refs:
                partes.append(f"  Ficheiros: {', '.join(sorted(refs))}.")
            partes.append("  Exemplos:")
            for r in ia_rows:
                partes.append(f"    • {r.get('ficheiro')} pág.{r.get('pagina')} – {r.get('snippet')[:160]}")

        if excel_rows:
            partes.append(f"- Resultados Excel: {len(excel_rows)} linha(s).")
            # tentar colunas mais comuns
            refs = {row.get("Ref") or row.get("Referência") for row in excel_rows if (row.get('Ref') or row.get('Referência'))}
            fornecedores = {row.get("Fornecedor") for row in excel_rows if row.get("Fornecedor")}
            if refs:
                partes.append(f"  Referências: {', '.join(sorted(refs))}.")
            if fornecedores:
                partes.append(f"  Fornecedores: {', '.join(sorted(fornecedores))}.")
            partes.append("  Exemplos:")
            for row in excel_rows:
                partes.append(
                    f"    • Ref {row.get('Ref') or row.get('Referência') or ''} – {row.get('Nome') or row.get('Nome Design') or row.get('Descrição','')}"
                    f" (folha {row.get('Folha','?')}, linha {row.get('Linha','?')})."
                )

        return "\n".join(partes)

    def on_generate_answer(self) -> None:
        query = (self.ed_query.text() or "").strip()
        if not query:
            QtWidgets.QMessageBox.information(self, "Info", "Escreva uma pergunta antes de gerar resposta.")
            return

        # Primeiro: gerar um resumo estruturado (sem depender do modelo)
        resposta_base = self._build_text_answer(query)

        # Se quiseres ainda polir com o modelo local/openai, mantém a chamada abaixo.
        # Caso contrário, mostramos já o texto mais estruturado.
        try:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            try:
                resposta = svc_ia.gerar_resposta(self.db, query, [{"snippet": resposta_base}], prefer_local=True)
            except Exception:
                resposta = resposta_base
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

        self.summary.setPlainText(resposta or resposta_base)

    def _open_selected(self) -> None:
        selection = self.table.selectionModel()
        if not selection:
            return
        idxs = selection.selectedRows()
        if not idxs:
            return
        row = idxs[0].row()
        path_item = self.table.item(row, 5)
        if not path_item:
            return
        path = path_item.text()
        if not path:
            return
        try:
            if Path(path).exists():
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                QtWidgets.QMessageBox.information(self, "Caminho", f"Caminho não existe:\n{path}")
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Erro", f"Não foi possível abrir o ficheiro:\n{path}\n\n{exc}")

    def _open_excel_file(self) -> None:
        path = svc_ia.ia_excel_path(self.db)
        if not Path(path).exists():
            QtWidgets.QMessageBox.warning(self, "Aviso", f"Ficheiro não encontrado:\n{path}")
            return
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Aviso", f"Não foi possível abrir o ficheiro:\n{exc}")

    def _fill_excel_results(self, excel_results: list[dict]) -> None:
        # Definir ordem de colunas prioritárias
        preferred = [
            "SEPARADOR",
            "SEP",
            "id",
            "Referência",
            "Referencia",
            "Ref",
            "ST",
            "Nome Design",
            "Grupo",
            "Tipo Produto",
            "Observações",
            "Esp 8mm",
            "Preço Tabela 8mm",
            "Esp 19mm",
            "Preço Tabela 19mm",
            "Fornecedor",
            "Ref",
            "Codigo Barras",
            "customer code",
            "Descrição",
            "und",
            "box",
            "Preço",
        ]

        # descobrir todas as colunas presentes
        cols_set = []
        for row in excel_results:
            data = row.get("row_data") or {}
            for k in data.keys():
                if k not in cols_set:
                    cols_set.append(k)
        ordered_cols = [c for c in preferred if c in cols_set]
        for c in cols_set:
            if c not in ordered_cols:
                ordered_cols.append(c)

        # montar tabela
        headers = ["Score", "Folha", "Linha"] + ordered_cols
        self.table_excel.setColumnCount(len(headers))
        self.table_excel.setHorizontalHeaderLabels(headers)
        self.table_excel.setRowCount(0)

        for row in excel_results:
            r = self.table_excel.rowCount()
            self.table_excel.insertRow(r)
            items = [
                QtWidgets.QTableWidgetItem(f"{row.get('score',0):.3f}"),
                QtWidgets.QTableWidgetItem(str(row.get("folha",""))),
                QtWidgets.QTableWidgetItem(str(row.get("linha",""))),
            ]
            data = row.get("row_data") or {}
            for col in ordered_cols:
                val = data.get(col, "")
                items.append(QtWidgets.QTableWidgetItem(str(val)))
            for c, itm in enumerate(items):
                itm.setToolTip(itm.text())
                self.table_excel.setItem(r, c, itm)
        self.table_excel.resizeColumnsToContents()
        self.table_excel.resizeRowsToContents()

# ----------------- página -----------------






class MateriasPrimasPage(QtWidgets.QWidget):







    def __init__(self, parent=None, current_user=None):







        super().__init__(parent)







        self.current_user = current_user







        self.db = SessionLocal()















        # Metadados de colunas vindos do serviço (header, attr, kind...)







        self.columns_meta = list(get_all_columns())







        self.user_id = getattr(self.current_user, "id", None)







        layout_pref = get_user_layout(self.db, self.user_id)







        self.visible_columns = list(layout_pref.visible)







        self.column_order = list(layout_pref.order)







        self.column_widths = dict(layout_pref.widths)







        if not self.visible_columns:







            self.visible_columns = [col.header for col in self.columns_meta]







        if not self.column_order:







            self.column_order = [col.header for col in self.columns_meta]







        if not self.column_widths:







            self.column_widths = {}















        # Pesquisar com pequeno debounce







        self._search_timer = QTimer(self)







        self._search_timer.setSingleShot(True)







        self._search_timer.timeout.connect(self.refresh_table)















        style = self.style()















        # ---- Barra superior ----







        header_widget = QtWidgets.QWidget()







        header_layout = QtWidgets.QHBoxLayout(header_widget)







        header_layout.setContentsMargins(0, 0, 0, 0)







        header_layout.setSpacing(8)















        self.search_edit = QtWidgets.QLineEdit()







        self.search_edit.setPlaceholderText("Pesquisar matérias primas… use % para multi-termos")







        self.search_edit.textChanged.connect(self.on_search_text_changed)
        self.search_edit.textChanged.connect(self._update_clear_search_button)

        self.btn_clear_search = QtWidgets.QToolButton()
        self.btn_clear_search.setIcon(style.standardIcon(QStyle.SP_DialogResetButton))
        self.btn_clear_search.setToolTip("Limpar pesquisa e mostrar todas as matérias primas")
        self.btn_clear_search.setAutoRaise(True)
        self.btn_clear_search.clicked.connect(self._clear_search)















        btn_open = QtWidgets.QPushButton("Abrir Excel")







        btn_open.setIcon(_excel_like_icon())
        btn_open.setIconSize(QtCore.QSize(16, 16))







        btn_open.clicked.connect(self.on_open_excel)















        btn_refresh = QtWidgets.QPushButton("Atualizar Importação")
        btn_ingest = QtWidgets.QPushButton("Atualizar IA")







        btn_refresh.setIcon(style.standardIcon(QStyle.SP_BrowserReload))
        btn_ingest.setIcon(style.standardIcon(QStyle.SP_BrowserReload))
        btn_refresh.setToolTip("Recarregar tabela de mat‚rias primas a partir do Excel configurado.")
        btn_ingest.setToolTip("Executar ingest_profundo.py (atualiza embeddings IA com novos ficheiros).")







        btn_refresh.clicked.connect(self.on_import_excel)
        btn_ingest.clicked.connect(self._handle_run_ingest_ia)















        btn_columns = QtWidgets.QPushButton("Colunas")







        btn_columns.setIcon(style.standardIcon(QStyle.SP_FileDialogDetailedView))







        btn_columns.clicked.connect(self.on_choose_columns)















        btn_save_layout = QtWidgets.QPushButton("Gravar Layout")
        self.btn_ia_search = QtWidgets.QPushButton("Pesquisa IA")






        btn_save_layout.setIcon(style.standardIcon(QStyle.SP_DialogSaveButton))
        btn_save_layout.setToolTip("Gravar a disposição atual das colunas. Atalho: Ctrl+G.")
        self.btn_ia_search.setIcon(style.standardIcon(QStyle.SP_FileDialogContentsView))






        btn_save_layout.clicked.connect(self.on_save_layout)
        self._shortcut_save = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+G"), self)
        self._shortcut_save.setContext(Qt.WidgetWithChildrenShortcut)
        self._shortcut_save.activated.connect(self.on_save_layout)
        self.btn_ia_search.clicked.connect(self.on_open_ia_search)














        self.lbl_path = QtWidgets.QLabel(self._current_excel_path())







        self.lbl_path.setStyleSheet("color: #555;")







        self.lbl_path.setTextInteractionFlags(Qt.TextSelectableByMouse)















        header_layout.addWidget(QtWidgets.QLabel("Pesquisa:"))







        header_layout.addWidget(self.search_edit, 1)
        header_layout.addWidget(self.btn_clear_search)







        header_layout.addWidget(btn_open)







        header_layout.addWidget(btn_refresh)
        header_layout.addWidget(btn_ingest)







        header_layout.addWidget(btn_columns)







        header_layout.addWidget(btn_save_layout)
        header_layout.addWidget(self.btn_ia_search)






        header_layout.addWidget(self.lbl_path, 1)
        self._update_clear_search_button()















        # ---- Modelo + Proxy (para ordenar por valor cru) ----







        model_columns = []







        for col in self.columns_meta:



            fmt = None



            if col.header in ("PRECO_TABELA", "PLIQ"):



                fmt = _fmt_eur



            elif col.header in ("MARGEM", "DESCONTO", "DESP"):



                fmt = _fmt_pct



            elif col.header == "STOCK":



                fmt = _fmt_stock



            elif col.header in ("COMP_MP", "LARG_MP", "ESP_MP"):



                fmt = _fmt_int



            elif getattr(col, "kind", None) == "numeric":



                fmt = lambda v, p=2: _format_decimal(v, p)



            model_columns.append((col.header, col.attr, fmt))















        self.model = SimpleTableModel(columns=model_columns)















        self.proxy = QtCore.QSortFilterProxyModel(self)







        self.proxy.setSourceModel(self.model)







        self.proxy.setSortRole(Qt.UserRole)  # usa valor cru







        self.proxy.setDynamicSortFilter(True)















        # ---- Tabela ----







        self.table = QtWidgets.QTableView(self)







        self.table.setModel(self.proxy)







        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)







        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)







        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)







        self.table.doubleClicked.connect(self._show_readonly_message)







        self.table.setWordWrap(True)







        self.table.setAlternatingRowColors(True)







        self.table.setSortingEnabled(True)  # ativa ordenação por cabeçalho















        header = self.table.horizontalHeader()







        header.setSectionResizeMode(QHeaderView.Interactive)







        header.setStretchLastSection(False)







        header_font = header.font()







        header_font.setBold(True)







        header.setFont(header_font)







        header.setSortIndicatorShown(True)















        # Larguras iniciais (mantidas, ajusta à vontade)







        default_widths = {







            "ID_MP": 90,







            "REF_PHC": 100,







            "REF_FORNECEDOR": 120,







            "Ref_LE": 100,







            "DESCRICAO_do_PHC": 220,







            "DESCRICAO_no_ORCAMENTO": 500,







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







        if not getattr(self, "column_widths", None):







            self.column_widths = {}







        for key, value in default_widths.items():







            self.column_widths.setdefault(key, value)







        for index, column in enumerate(self.columns_meta):







            width = self.column_widths.get(column.header)







            if width:







                header.resizeSection(index, width)















        self.table.verticalHeader().setDefaultSectionSize(24)







        self.table.setFocusPolicy(Qt.NoFocus)















        # Layout final







        layout = QtWidgets.QVBoxLayout(self)







        layout.setContentsMargins(6, 6, 6, 6)







        layout.setSpacing(8)







        layout.addWidget(header_widget)







        layout.addWidget(self.table, 1)















        # Primeira carga







        self.refresh_table()















    # ----------------- ações -----------------







    def _current_excel_path(self) -> str:







        try:







            base = get_base_path(self.db)







        except Exception:







            base = DEFAULT_MATERIAS_BASE_PATH







        return str(Path(base) / MATERIA_PRIMA_FILENAME)




    def on_open_ia_search(self) -> None:

        dlg = PesquisaIADialog(self.db, self)

        dlg.exec()














    def on_search_text_changed(self, _text: str) -> None:







        self._search_timer.start(300)















    def _update_clear_search_button(self) -> None:
        btn = getattr(self, "btn_clear_search", None)
        ed = getattr(self, "search_edit", None)
        if btn is None or ed is None:
            return
        btn.setEnabled(bool(ed.text().strip()))

    def _clear_search(self) -> None:
        if not hasattr(self, "search_edit"):
            return
        block = self.search_edit.blockSignals(True)
        try:
            self.search_edit.clear()
        finally:
            self.search_edit.blockSignals(block)
        if hasattr(self, "_search_timer"):
            self._search_timer.stop()
        self._update_clear_search_button()
        self.refresh_table()

    def refresh_table(self) -> None:

        rows = list_materias_primas(self.db, self.search_edit.text())

        self.model.set_rows(rows)

        self._apply_user_layout()

        self.table.sortByColumn(0, Qt.AscendingOrder)



    def _apply_user_layout(self) -> None:







        header = self.table.horizontalHeader()







        header.setSectionsMovable(True)







        header.blockSignals(True)







        if not getattr(self, "column_order", None):







            self.column_order = [col.header for col in self.columns_meta]







        if not getattr(self, "visible_columns", None):







            self.visible_columns = [col.header for col in self.columns_meta]







        logical_map = {col.header: index for index, col in enumerate(self.columns_meta)}







        for target_position, header_name in enumerate(self.column_order):







            logical = logical_map.get(header_name)







            if logical is None:







                continue







            current_visual = header.visualIndex(logical)







            if current_visual == -1 or current_visual == target_position:







                continue







            header.moveSection(current_visual, target_position)







        visible_set = set(self.visible_columns)







        for logical, column in enumerate(self.columns_meta):







            self.table.setColumnHidden(logical, column.header not in visible_set)







        for logical, column in enumerate(self.columns_meta):







            width = self.column_widths.get(column.header) if hasattr(self, "column_widths") else None







            if width:







                self.table.setColumnWidth(logical, width)







        header.blockSignals(False)















    def _current_layout_state(self) -> dict:







        header = self.table.horizontalHeader()







        order_pairs = []







        for logical, column in enumerate(self.columns_meta):







            visual = header.visualIndex(logical)







            if visual >= 0:







                order_pairs.append((visual, column.header))







        order_pairs.sort(key=lambda item: item[0])







        order = [name for _, name in order_pairs]







        if not order:







            order = [col.header for col in self.columns_meta]







        visible = [column.header for index, column in enumerate(self.columns_meta) if not self.table.isColumnHidden(index)]







        widths = {column.header: header.sectionSize(index) for index, column in enumerate(self.columns_meta)}







        return {"visible": visible, "order": order, "widths": widths}















    def on_save_layout(self) -> None:







        if not self.user_id:







            QMessageBox.information(self, "Informação", "Preferências de colunas são específicas por utilizador.")







            return







        state = self._current_layout_state()







        try:







            save_user_layout(







                self.db,







                self.user_id,







                visible=state["visible"],







                order=state["order"],







                widths=state["widths"],







            )







            self.db.commit()







            self.visible_columns = state["visible"]







            self.column_order = state["order"]







            self.column_widths = state["widths"]







            QMessageBox.information(self, "Sucesso", "Layout gravado para o utilizador atual.")







        except Exception as exc:







            self.db.rollback()







            QMessageBox.critical(self, "Erro", f"Falha ao gravar layout: {exc}")















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















    def _handle_run_ingest_ia(self) -> None:
        if (
            QtWidgets.QMessageBox.question(
                self,
                "Atualizar IA",
                "Executar ingestão dos ficheiros em Pesquisa_Profunda_IA?\n(Isto pode demorar alguns minutos.)",
            )
            != QtWidgets.QMessageBox.Yes
        ):
            return
        try:
            # __file__ -> .../Martelo_Orcamentos_V2/ui/pages/materias_primas.py
            # repo_root -> raiz do projeto (contém scripts/)
            repo_root = Path(__file__).resolve().parents[3]
            script_path = repo_root / "scripts" / "ingest_profundo.py"
            emb_dir = svc_ia.ia_embeddings_path(self.db)
            base_dir = svc_ia.ia_base_path(self.db)
            cmd = [
                sys.executable,
                str(script_path),
                "--base",
                str(base_dir),
                "--embeddings",
                str(emb_dir),
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_root, timeout=240)
            if proc.returncode == 0:
                index_path = Path(emb_dir) / svc_ia.FAISS_FILENAME
                if not index_path.exists():
                    hint = (
                        "Indice FAISS nao foi criado.\n\n"
                        f"Caminho: {index_path}\n\n"
                        "Sugestao: verifique 'Pasta Embeddings IA' nas Configuracoes e use um caminho partilhado "
                        f"(ex: {svc_ia.DEFAULT_IA_SHARED_PATH}). Depois execute 'Atualizar IA' novamente."
                    )
                    QtWidgets.QMessageBox.warning(self, "Aviso", hint)
                msg = proc.stdout.strip() or "Ingestão concluída."
                QtWidgets.QMessageBox.information(self, "Ingestão IA", msg[-4000:])
            else:
                err = proc.stderr.strip() or proc.stdout.strip()
                QtWidgets.QMessageBox.critical(self, "Erro na Ingestão", f"Falha ao executar ingest_profundo.py:\n{err}")
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Não foi possível executar ingest_profundo.py:\n{exc}")

    def on_choose_columns(self) -> None:







        headers = [col.header for col in self.columns_meta]







        dialog = ColumnSelectorDialog(headers, list(self.visible_columns), self)







        if dialog.exec() == QtWidgets.QDialog.Accepted:







            selected = dialog.selected_columns()







            if not selected:







                QMessageBox.information(self, "Informação", "Selecione pelo menos uma coluna.")







                return







            self.visible_columns = selected







            # Ajusta visibilidade imediatamente; o utilizador deve clicar em 'Gravar Layout' para persistir.







            self._apply_user_layout()















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















# Nome do ficheiro Excel esperado







MATERIA_PRIMA_FILENAME = "TAB_MATERIAS_PRIMAS.xlsm"







# Nome da folha dentro do Excel







MATERIA_PRIMA_SHEETNAME = "MAT_PRIMAS"





