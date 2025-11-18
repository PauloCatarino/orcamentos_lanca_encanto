from __future__ import annotations

import html
import re
import shutil
import tempfile
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Tuple, Any

from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtCore import Qt
from openpyxl import Workbook, load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.styles import Alignment, Border, Font, Side, PatternFill
from openpyxl.drawing.image import Image as XLImage
from openpyxl.worksheet.page import PageMargins
from openpyxl.worksheet.properties import PageSetupProperties
try:
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure

    MATPLOTLIB_AVAILABLE = True
except Exception:
    PdfPages = FigureCanvas = Figure = None
    MATPLOTLIB_AVAILABLE = False

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    REPORTLAB_AVAILABLE = True

    class NumberedFooterCanvas(rl_canvas.Canvas):
        """
        Canvas que guarda os estados das páginas e desenha o rodapé com
        a data, o número do orçamento e a numeração X/Y.
        Implementação testada e estável (padrão recomendado).
        """
        def __init__(self, *args, footer_info: Optional[dict] = None, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_page_states = []
            self.footer_info = footer_info or {}

        def showPage(self):
            # 1) Guarda o estado da página atual (conteúdo já desenhado)
            self._saved_page_states.append(dict(self.__dict__))

            # 2) NÃO grava a página agora; apenas "começa" uma nova página em memória
            #    _startPage() prepara uma nova página, mas não escreve nada no PDF.
            self._startPage()

        def save(self):
            # Agora sim, no final, percorremos todos os estados gravados
            num_pages = len(self._saved_page_states)

            for state in self._saved_page_states:
                # Recupera o estado da página
                self.__dict__.update(state)

                # Desenha o rodapé para esta página
                self._draw_footer(num_pages)

                # Grava a página no PDF (agora com rodapé)
                rl_canvas.Canvas.showPage(self)

            # Por fim, chama o save original para fechar o ficheiro
            rl_canvas.Canvas.save(self)

        def _draw_footer(self, page_count: int):
            # posição vertical do rodapé (ajusta se quiseres mais acima/baixo)
            width, _ = self._pagesize
            y = 6 * mm
            self.setFont("Helvetica", 9)

            # esquerda: apenas a data (sem "Data:")
            self.drawString(18 * mm, y, f"{self.footer_info.get('data', '')}")

            # centro: nº orçamento + versão
            self.drawCentredString(width / 2, y, self.footer_info.get("numero", ""))

            # direita: nº página / total
            self.drawRightString(width - 18 * mm, y, f"{self._pageNumber}/{page_count}")


except Exception:
    colors = A4 = ParagraphStyle = getSampleStyleSheet = mm = Image = Paragraph = SimpleDocTemplate = Spacer = Table = TableStyle = NumberedFooterCanvas = None
    REPORTLAB_AVAILABLE = False
from sqlalchemy import select

from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.models import Client, Orcamento, OrcamentoItem, CusteioItem
from Martelo_Orcamentos_V2.app.services.settings import get_setting
from Martelo_Orcamentos_V2.ui.models.qt_table import SimpleTableModel


IVA_RATE = Decimal("0.23")
KEY_BASE_PATH = "base_path_orcamentos"
KEY_ORC_DB_BASE = "base_path_dados_orcamento"
DEFAULT_BASE_PATH = r"\\server_le\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\MARTELO_ORCAMENTOS_V2"
DEFAULT_BASE_DADOS_ORC = r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\Base_Dados_Orcamento"


class RichTextDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> None:
        text = index.data(Qt.DisplayRole)
        if not isinstance(text, str):
            super().paint(painter, option, index)
            return
        painter.save()
        doc = QtGui.QTextDocument()
        doc.setDefaultFont(option.font)
        doc.setHtml(text)
        ctx = QtGui.QAbstractTextDocumentLayout.PaintContext()
        if option.state & QtWidgets.QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            ctx.palette.setColor(QtGui.QPalette.Text, option.palette.highlightedText().color())
        painter.translate(option.rect.topLeft())
        doc.setTextWidth(option.rect.width())
        doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(self, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> QtCore.QSize:
        text = index.data(Qt.DisplayRole)
        if not isinstance(text, str):
            return super().sizeHint(option, index)
        doc = QtGui.QTextDocument()
        doc.setDefaultFont(option.font)
        doc.setHtml(text)
        width = option.rect.width() if option.rect.width() > 0 else 400
        doc.setTextWidth(width)
        size = doc.size().toSize()
        return QtCore.QSize(int(doc.idealWidth()), size.height())


class BoldValueDelegate(QtWidgets.QStyledItemDelegate):
    def initStyleOption(self, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> None:
        super().initStyleOption(option, index)
        font = option.font
        font.setBold(True)
        option.font = font


@dataclass
class ItemPreview:
    item: str
    codigo: str
    descricao: str
    altura: Optional[Decimal]
    largura: Optional[Decimal]
    profundidade: Optional[Decimal]
    unidade: str
    qt: Optional[Decimal]
    preco_unitario: Optional[Decimal]
    preco_total: Optional[Decimal]


def _fmt_decimal(value: Optional[Decimal], decimals: int = 2) -> str:
    if value in (None, ""):
        return ""
    try:
        number = Decimal(value)
    except Exception:
        return str(value)
    fmt = f"{{0:.{decimals}f}}"
    return fmt.format(number)


def _fmt_currency(value: Optional[Decimal]) -> str:
    if value in (None, ""):
        return ""
    try:
        number = Decimal(value)
    except Exception:
        return str(value)
    return f"{number:.2f} €"


class RelatoriosPage(QtWidgets.QWidget):
    """Página dedicada aos relatórios de orçamento."""

    def __init__(self, parent=None, *, current_user=None):
        super().__init__(parent)
        self.current_user = current_user
        self.current_orcamento_id: Optional[int] = None
        self._current_orcamento: Optional[Orcamento] = None
        self._current_client: Optional[Client] = None
        self._current_items: List[ItemPreview] = []
        self._dashboard_data = {"placas": [], "orlas": [], "ferr": [], "maq": []}
        self._dash_info_labels: dict[str, QtWidgets.QLabel] = {}

        self._setup_ui()

    # ------------------------------------------------------------------ UI SETUP
    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        self.tab_widget = QtWidgets.QTabWidget()
        layout.addWidget(self.tab_widget, 1)

        self.tab_orcamento = QtWidgets.QWidget()
        self.tab_widget.addTab(self.tab_orcamento, "Relatório de Orçamento")

        tab_layout = QtWidgets.QVBoxLayout(self.tab_orcamento)
        tab_layout.setContentsMargins(4, 4, 4, 4)
        tab_layout.setSpacing(8)

        top_row = QtWidgets.QHBoxLayout()
        tab_layout.addLayout(top_row)

        self.client_box = QtWidgets.QGroupBox("Dados do Cliente")
        client_form = QtWidgets.QFormLayout(self.client_box)
        client_form.setSpacing(4)
        self.lbl_cliente_nome = QtWidgets.QLabel("-")
        self.lbl_cliente_morada = QtWidgets.QLabel("-")
        self.lbl_cliente_morada.setWordWrap(True)
        self.lbl_cliente_email = QtWidgets.QLabel("-")
        self.lbl_cliente_phc = QtWidgets.QLabel("-")
        self.lbl_cliente_tel = QtWidgets.QLabel("-")
        self.lbl_cliente_telemovel = QtWidgets.QLabel("-")
        for lbl in (
            self.lbl_cliente_nome,
            self.lbl_cliente_morada,
            self.lbl_cliente_email,
            self.lbl_cliente_phc,
            self.lbl_cliente_tel,
            self.lbl_cliente_telemovel,
        ):
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

        client_form.addRow("Nome:", self.lbl_cliente_nome)
        client_form.addRow("Morada:", self.lbl_cliente_morada)
        client_form.addRow("Email:", self.lbl_cliente_email)
        client_form.addRow("N.º Cliente PHC:", self.lbl_cliente_phc)
        client_form.addRow("Telefone:", self.lbl_cliente_tel)
        client_form.addRow("Telemóvel:", self.lbl_cliente_telemovel)
        top_row.addWidget(self.client_box, 3)

        self.orc_box = QtWidgets.QGroupBox("Identificação do Orçamento")
        orc_form = QtWidgets.QFormLayout(self.orc_box)
        orc_form.setSpacing(4)
        self.lbl_orc_data = QtWidgets.QLabel("-")
        self.lbl_orc_num = QtWidgets.QLabel("-")
        self.lbl_orc_versao = QtWidgets.QLabel("-")
        self.lbl_orc_obra = QtWidgets.QLabel("-")
        self.lbl_orc_ref = QtWidgets.QLabel("-")
        self.lbl_orc_obra.setWordWrap(True)
        for lbl in (self.lbl_orc_data, self.lbl_orc_num, self.lbl_orc_versao, self.lbl_orc_obra, self.lbl_orc_ref):
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        orc_form.addRow("Data:", self.lbl_orc_data)
        orc_form.addRow("N.º Orçamento:", self.lbl_orc_num)
        orc_form.addRow("Versão:", self.lbl_orc_versao)
        orc_form.addRow("Obra:", self.lbl_orc_obra)
        orc_form.addRow("Ref. Cliente:", self.lbl_orc_ref)
        top_row.addWidget(self.orc_box, 2)

        actions_box = QtWidgets.QGroupBox("Ações")
        actions_layout = QtWidgets.QVBoxLayout(actions_box)
        self.btn_preview = QtWidgets.QPushButton("Gerar Orçamento Pre-Visualização")
        self.btn_export_excel = QtWidgets.QPushButton("Exportar para Excel")
        self.btn_export_pdf = QtWidgets.QPushButton("Exportar para PDF")
        actions_layout.addWidget(self.btn_preview)
        actions_layout.addWidget(self.btn_export_excel)
        actions_layout.addWidget(self.btn_export_pdf)
        actions_layout.addStretch(1)
        top_row.addWidget(actions_box, 1)

        self.btn_preview.clicked.connect(self.refresh_preview)
        self.btn_export_excel.clicked.connect(self.export_to_excel)
        self.btn_export_pdf.clicked.connect(self.export_to_pdf)

        # tabela de itens
        self.table = QtWidgets.QTableView()
        self.table_model = SimpleTableModel(
            columns=[
                ("Item", "item"),
                ("Código", "codigo"),
                ("Descrição", "descricao_html", lambda v: v or ""),
                ("Altura", "altura", lambda v: _fmt_decimal(v, 1)),
                ("Largura", "largura", lambda v: _fmt_decimal(v, 1)),
                ("Profundidade", "profundidade", lambda v: _fmt_decimal(v, 1)),
                ("Unidade", "unidade"),
                ("Qt", "qt", lambda v: _fmt_decimal(v, 2)),
                ("Preço Unitário", "preco_unitario", _fmt_currency),
                ("Preço Total", "preco_total", _fmt_currency),
            ]
        )
        self.table.setModel(self.table_model)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Interactive)
        self.table.setColumnWidth(2, 450)
        for idx in range(3, 9):
            header.setSectionResizeMode(idx, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(9, QtWidgets.QHeaderView.ResizeToContents)
        self.table.verticalHeader().setDefaultSectionSize(80)
        self.table.setStyleSheet(
            """
            QTableView {
                gridline-color: #b5b5b5;
                selection-background-color: #e0f0ff;
                font-size: 12px;
            }
            """
        )
        self.table.setItemDelegateForColumn(2, RichTextDelegate(self.table))
        self.table.setItemDelegateForColumn(9, BoldValueDelegate(self.table))
        header.sectionResized.connect(self._on_header_resized)
        tab_layout.addWidget(self.table, 1)

        totals_frame = QtWidgets.QFrame()
        totals_layout = QtWidgets.QGridLayout(totals_frame)
        totals_layout.setContentsMargins(0, 0, 0, 0)
        totals_layout.setHorizontalSpacing(16)
        totals_layout.setVerticalSpacing(2)
        self.lbl_total_qt = QtWidgets.QLabel("Total Qt: 0")
        self.lbl_subtotal = QtWidgets.QLabel("Subtotal: 0.00 €")
        self.lbl_iva = QtWidgets.QLabel("IVA (23%): 0.00 €")
        self.lbl_total_geral = QtWidgets.QLabel("Total Geral: 0.00 €")
        bold_font = self.lbl_total_geral.font()
        bold_font.setBold(True)
        self.lbl_total_geral.setFont(bold_font)
        totals_layout.addWidget(self.lbl_total_qt, 0, 0, alignment=Qt.AlignRight)
        totals_layout.addWidget(self.lbl_subtotal, 0, 1, alignment=Qt.AlignRight)
        totals_layout.addWidget(self.lbl_iva, 1, 0, alignment=Qt.AlignRight)
        totals_layout.addWidget(self.lbl_total_geral, 1, 1, alignment=Qt.AlignRight)
        tab_layout.addWidget(totals_frame, 0, alignment=Qt.AlignRight)

        # segundo separador: dashboard de consumos
        self.tab_dashboard = QtWidgets.QWidget()
        self._build_dashboard_tab(self.tab_dashboard)
        self.tab_widget.addTab(self.tab_dashboard, "Resumo de Consumos")

        self._update_actions_enabled(False)

    # ------------------------------------------------------------------ DATA FLOW
    def set_orcamento(self, orcamento_id: Optional[int]) -> None:
        self.current_orcamento_id = orcamento_id
        has_orc = orcamento_id is not None
        if not has_orc:
            self._clear_preview()
        self._update_actions_enabled(has_orc)

    def refresh_preview(self) -> None:
        if not self.current_orcamento_id:
            QtWidgets.QMessageBox.information(self, "Relatórios", "Selecione um orçamento para gerar o relatório.")
            return
        try:
            self._load_from_db(self.current_orcamento_id)
            self._apply_to_ui()
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Relatórios", f"Falha ao gerar pré-visualização: {exc}")

    def _load_from_db(self, orcamento_id: int) -> None:
        with SessionLocal() as session:
            orcamento = session.get(Orcamento, orcamento_id)
            if not orcamento:
                raise ValueError("Orçamento não encontrado.")
            client = session.get(Client, orcamento.client_id) if orcamento.client_id else None
            stmt = (
                select(OrcamentoItem)
                .where(OrcamentoItem.id_orcamento == orcamento_id)
                .order_by(OrcamentoItem.item_ord)
            )
            items = session.execute(stmt).scalars().all()

        parsed_rows: List[ItemPreview] = []
        for it in items:
            parsed_rows.append(
                ItemPreview(
                    item=str(it.item or ""),
                    codigo=str(it.codigo or ""),
                    descricao=str(it.descricao or ""),
                    altura=Decimal(it.altura) if it.altura is not None else None,
                    largura=Decimal(it.largura) if it.largura is not None else None,
                    profundidade=Decimal(it.profundidade) if it.profundidade is not None else None,
                    unidade=str(it.und or ""),
                    qt=Decimal(it.qt) if it.qt is not None else None,
                    preco_unitario=Decimal(it.preco_unitario) if it.preco_unitario is not None else None,
                    preco_total=Decimal(it.preco_total) if it.preco_total is not None else None,
                )
            )

        self._current_orcamento = orcamento
        self._current_client = client
        self._current_items = parsed_rows

    def _apply_to_ui(self) -> None:
        client = self._current_client
        orc = self._current_orcamento
        items = self._current_items
        if not orc:
            self._clear_preview()
            return

        def label_text(value: Optional[str]) -> str:
            text = str(value or "").strip()
            return text if text else "-"

        self.lbl_cliente_nome.setText(label_text(getattr(client, "nome", None)))
        self.lbl_cliente_morada.setText(label_text(getattr(client, "morada", None)))
        self.lbl_cliente_email.setText(label_text(getattr(client, "email", None)))
        self.lbl_cliente_phc.setText(label_text(getattr(client, "num_cliente_phc", None)))
        self.lbl_cliente_tel.setText(label_text(getattr(client, "telefone", None)))
        self.lbl_cliente_telemovel.setText(label_text(getattr(client, "telemovel", None)))

        self.lbl_orc_data.setText(label_text(orc.data))
        self.lbl_orc_num.setText(label_text(orc.num_orcamento))
        self.lbl_orc_versao.setText(label_text(self._format_versao(orc.versao)))
        self.lbl_orc_obra.setText(label_text(orc.obra))
        self.lbl_orc_ref.setText(label_text(getattr(orc, "ref_cliente", None)))

        table_rows = [
            {
                "item": item.item,
                "codigo": item.codigo,
                "descricao_html": self._format_description_preview(item.descricao),
                "altura": item.altura,
                "largura": item.largura,
                "profundidade": item.profundidade,
                "unidade": item.unidade,
                "qt": item.qt,
                "preco_unitario": item.preco_unitario,
                "preco_total": item.preco_total,
            }
            for item in items
        ]
        self.table_model.set_rows(table_rows)
        QtCore.QTimer.singleShot(0, self._update_row_heights)

        total_qt = sum((row.qt or Decimal("0")) for row in items)
        subtotal = sum((row.preco_total or Decimal("0")) for row in items)
        iva = subtotal * IVA_RATE
        total = subtotal + iva

        self.lbl_total_qt.setText(f"Total Qt: {_fmt_decimal(total_qt, 2) or '0'}")
        self.lbl_subtotal.setText(f"Subtotal: {_fmt_currency(subtotal)}")
        self.lbl_iva.setText(f"IVA (23%): {_fmt_currency(iva)}")
        self.lbl_total_geral.setText(f"Total Geral: {_fmt_currency(total)}")
        self._refresh_dashboard()

    def _parse_description(self, text: Optional[str]) -> List[Tuple[str, str]]:
        """
        Converte o texto da descrição em uma lista de (tipo, conteúdo),
        onde tipo pode ser:
        - 'header'  : primeira linha (título do módulo)
        - 'header2' : linhas seguintes totalmente em maiúsculas (sub-títulos)
        - 'dash'    : linhas que começam por '-' (bullets normais)
        - 'star'    : linhas que começam por '*' (bullets especiais)
        - 'plain'   : resto

        Trata também descrições que vêm NUMA ÚNICA LINHA e/ou que começam
        por '-' ou '*' (separando corretamente em bullets).
        """
        lines: List[Tuple[str, str]] = []
        if not text:
            return lines

        # Normalizar quebras de linha
        norm = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        if not norm:
            return lines

        # -------------------------------------------------
        # CASO 1: já existem quebras de linha -> usa-as
        # -------------------------------------------------
        if "\n" in norm:
            raw_lines = norm.splitlines()
            for idx, raw in enumerate(raw_lines):
                stripped = raw.strip()
                if not stripped:
                    continue

                lstripped = raw.lstrip()

                # 1ª linha é sempre o cabeçalho principal
                if idx == 0:
                    lines.append(("header", stripped))
                    continue

                # Bullets
                if lstripped.startswith("-"):
                    lines.append(("dash", lstripped[1:].strip() or stripped))
                elif lstripped.startswith("*"):
                    lines.append(("star", lstripped[1:].strip() or stripped))
                else:
                    # Linha toda em maiúsculas -> "sub-header"
                    letters = [ch for ch in stripped if ch.isalpha()]
                    if letters and stripped.upper() == stripped:
                        lines.append(("header2", stripped))
                    else:
                        lines.append(("plain", stripped))
            return lines

        # -------------------------------------------------
        # CASO 2: tudo numa só linha -> tratar bullets mesmo assim
        #         (verifica se começa por '-' ou '*', ou tem " - " / " * ")
        # -------------------------------------------------
        # Se começa por '-' ou '*', capturar todos os bullets com regex
        first_nonspace = norm.lstrip()[0] if norm.lstrip() else ""
        if first_nonspace in ("-", "*"):
            # encontra todos os blocos "- texto" ou "* texto"
            for m in re.finditer(r'([-*])\s*([^-*]+?)(?=(?:\s[-*]\s)|$)', norm):
                bullet = m.group(1)
                content = m.group(2).strip()
                if not content:
                    continue
                kind = "star" if bullet == "*" else "dash"
                lines.append((kind, content))
            return lines

        # Caso tenha separadores " - " ou " * " mas não comece com bullet:
        parts = re.split(r'( - |\* )', norm)
        if len(parts) == 1:
            # sem separadores: tratar tudo como header
            lines.append(("header", norm))
            return lines

        # primeira parte antes de qualquer "-" ou "*" é o header
        header_text = parts[0].strip()
        if header_text:
            lines.append(("header", header_text))

        # restantes vêm aos pares: [delim, conteúdo, delim, conteúdo, ...]
        for i in range(1, len(parts), 2):
            delim = parts[i]
            if i + 1 >= len(parts):
                break
            content = parts[i + 1].strip()
            if not content:
                continue

            if "*" in delim:
                lines.append(("star", content))
            else:
                lines.append(("dash", content))

        return lines

    def _format_description_preview(self, text: Optional[str]) -> str:
        entries = self._parse_description(text)
        if not entries:
            return ""
        html_parts: List[str] = []
        for kind, content in entries:
            safe_text = html.escape(content)
            if kind in ("header", "header2"):
                html_parts.append(
                    f"<div style='font-weight:bold;text-transform:uppercase'>{safe_text.upper()}</div>"
                )
            elif kind == "dash":
                html_parts.append(
                    f"<div style='font-style:italic;margin-left:10px'>- {safe_text}</div>"
                )
            elif kind == "star":
                html_parts.append(
                    "<div style='font-style:italic;text-decoration:underline;"
                    "background-color:#d6f6c8;color:#095c1b;padding:1px 2px;margin-left:10px;'>* "
                    f"{safe_text}</div>"
                )
            else:
                html_parts.append(f"<div>{safe_text}</div>")
        return "".join(html_parts)

    def _clear_preview(self) -> None:
        for lbl in (
            self.lbl_cliente_nome,
            self.lbl_cliente_morada,
            self.lbl_cliente_email,
            self.lbl_cliente_phc,
            self.lbl_cliente_tel,
            self.lbl_cliente_telemovel,
            self.lbl_orc_data,
            self.lbl_orc_num,
            self.lbl_orc_versao,
            self.lbl_orc_obra,
            self.lbl_orc_ref,
        ):
            lbl.setText("-")
        self.table_model.set_rows([])
        self._update_row_heights()
        self.lbl_total_qt.setText("Total Qt: 0")
        self.lbl_subtotal.setText("Subtotal: 0.00 €")
        self.lbl_iva.setText("IVA (23%): 0.00 €")
        self.lbl_total_geral.setText("Total Geral: 0.00 €")

    def _update_actions_enabled(self, enabled: bool) -> None:
        self.btn_preview.setEnabled(enabled)
        self.btn_export_excel.setEnabled(enabled)
        self.btn_export_pdf.setEnabled(enabled)

    # ---------------------- DASHBOARD ----------------------
    def _wrap_in_group(self, title: str, widget: QtWidgets.QWidget) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox(title)
        lay = QtWidgets.QVBoxLayout(box)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.addWidget(widget)
        return box

    def _create_canvas(self) -> Tuple[Any, Any]:
        fig = Figure(figsize=(5, 3))
        ax = fig.add_subplot(111)
        canvas = FigureCanvas(fig)
        return canvas, ax

    def _build_dashboard_tab(self, parent: QtWidgets.QWidget) -> None:
        if not MATPLOTLIB_AVAILABLE:
            layout = QtWidgets.QVBoxLayout(parent)
            layout.addStretch(1)
            layout.addWidget(
                QtWidgets.QLabel(
                    "Dashboard indisponível: instale 'matplotlib' para ver gráficos.",
                    alignment=Qt.AlignCenter,
                )
            )
            layout.addStretch(1)
            return
        outer = QtWidgets.QVBoxLayout(parent)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # barra de info orçamento
        info_frame = QtWidgets.QFrame()
        info_layout = QtWidgets.QHBoxLayout(info_frame)
        info_layout.setContentsMargins(4, 2, 4, 2)
        info_layout.setSpacing(12)
        def _mk_info(label: str) -> QtWidgets.QLabel:
            lbl = QtWidgets.QLabel("-")
            lbl.setStyleSheet("font-weight: bold;")
            title = QtWidgets.QLabel(label)
            title.setStyleSheet("color: #555;")
            container = QtWidgets.QHBoxLayout()
            w = QtWidgets.QWidget()
            container.setSpacing(4)
            container.setContentsMargins(0, 0, 0, 0)
            container.addWidget(title)
            container.addWidget(lbl)
            container.addStretch(1)
            w.setLayout(container)
            info_layout.addWidget(w)
            return lbl
        self._dash_info_labels = {
            "ano": _mk_info("Ano:"),
            "cliente": _mk_info("Cliente:"),
            "orc": _mk_info("Nº Orçamento:"),
            "versao": _mk_info("Versão:"),
            "user": _mk_info("Utilizador:"),
        }
        info_layout.addStretch(1)
        layout.addWidget(info_frame)

        actions = QtWidgets.QHBoxLayout()
        self.btn_dash_refresh = QtWidgets.QPushButton("Atualizar Dashboard")
        self.btn_dash_export = QtWidgets.QPushButton("Exportar Dashboard para PDF")
        actions.addWidget(self.btn_dash_refresh)
        actions.addStretch(1)
        actions.addWidget(self.btn_dash_export)
        layout.addLayout(actions)

        # tabelas principais (mais altura)
        top_split = QtWidgets.QSplitter(Qt.Horizontal)
        self.tbl_dash_placas = QtWidgets.QTableView()
        self.tbl_dash_orlas = QtWidgets.QTableView()
        top_split.addWidget(self._wrap_in_group("Resumo de Placas", self.tbl_dash_placas))
        top_split.addWidget(self._wrap_in_group("Resumo de Orlas", self.tbl_dash_orlas))
        top_split.setStretchFactor(0, 1)
        top_split.setStretchFactor(1, 1)
        layout.addWidget(top_split, 3)

        mid_split = QtWidgets.QSplitter(Qt.Horizontal)
        self.tbl_dash_ferr = QtWidgets.QTableView()
        self.tbl_dash_maq = QtWidgets.QTableView()
        mid_split.addWidget(self._wrap_in_group("Resumo de Ferragens", self.tbl_dash_ferr))
        mid_split.addWidget(self._wrap_in_group("Resumo de Máquinas / MO", self.tbl_dash_maq))
        mid_split.setStretchFactor(0, 1)
        mid_split.setStretchFactor(1, 1)
        layout.addWidget(mid_split, 3)

        bottom_split = QtWidgets.QSplitter(Qt.Horizontal)
        self.canvas_placas, self.ax_placas = self._create_canvas()
        self.canvas_orlas, self.ax_orlas = self._create_canvas()
        for c in (self.canvas_placas, self.canvas_orlas):
            c.setMinimumHeight(1075)
        bottom_split.addWidget(self._wrap_in_group("Comparativo de Custos por Placa", self.canvas_placas))
        bottom_split.addWidget(self._wrap_in_group("Consumo de Orlas (ml)", self.canvas_orlas))
        bottom_split.setStretchFactor(0, 1)
        bottom_split.setStretchFactor(1, 1)
        layout.addWidget(bottom_split, 3)

        bottom2_split = QtWidgets.QSplitter(Qt.Horizontal)
        self.canvas_ferr, self.ax_ferr = self._create_canvas()
        self.canvas_ops, self.ax_ops = self._create_canvas()
        self.canvas_pie, self.ax_pie = self._create_canvas()
        for c in (self.canvas_ferr, self.canvas_ops, self.canvas_pie):
            c.setMinimumHeight(875)
        bottom2_split.addWidget(self._wrap_in_group("Custos por Ferragem", self.canvas_ferr))
        bottom2_split.addWidget(self._wrap_in_group("Custos por Operação", self.canvas_ops))
        layout.addWidget(bottom2_split, 3)

        pie_box = self._wrap_in_group("Distribuição de Custos (Placas / Orlas / Ferragens / Máquinas)", self.canvas_pie)
        layout.addWidget(pie_box, 2)
        bottom2_split.setStretchFactor(0, 1)
        bottom2_split.setStretchFactor(1, 1)
        layout.addWidget(pie_box, 2)

        self.btn_dash_refresh.clicked.connect(self._refresh_dashboard)
        self.btn_dash_export.clicked.connect(self._export_dashboard_pdf)

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _compute_resumos_dashboard(self) -> dict:
        result = {"placas": [], "orlas": [], "ferr": [], "maq": []}
        orc = self._current_orcamento
        if not orc:
            return result
        try:
            with SessionLocal() as session:
                cust_rows = (
                    session.query(CusteioItem)
                    .filter(CusteioItem.orcamento_id == orc.id, CusteioItem.versao == orc.versao)
                    .order_by(CusteioItem.ordem)
                    .all()
                )
        except Exception:
            return result

        def _orla_width_from_esp(esp_val: float) -> float:
            try:
                esp = float(esp_val)
            except Exception:
                return 0.0
            if esp <= 0:
                return 0.0
            if esp < 20:
                return 23.0
            if esp < 31:
                return 35.0
            if esp < 40:
                return 45.0
            return 60.0

        # ------------ Placas ------------
        placas_map: dict[tuple, dict] = {}
        for ci in cust_rows:
            und = (ci.und or "").upper()
            if und != "M2":
                continue
            comp_mp = float(ci.comp_mp or 0)
            larg_mp = float(ci.larg_mp or 0)
            desp = float(ci.desp or 0)
            qt_total = float(ci.qt_total or 0)
            pliq = float(ci.pliq or 0)
            area_placa = (comp_mp / 1000.0) * (larg_mp / 1000.0) if comp_mp and larg_mp else 0
            m2_total_pecas = float(ci.area_m2_und or 0) * qt_total
            m2_consumidos = m2_total_pecas * (1 + desp)
            ratio = area_placa and m2_consumidos / area_placa or 0
            qt_placas = int(ratio) if ratio and ratio.is_integer() else int(ratio) + 1 if ratio else 0
            custo_placas_utilizadas = qt_placas * area_placa * pliq
            key = (ci.ref_le, ci.descricao_no_orcamento)
            if key not in placas_map:
                placas_map[key] = {
                    "ref_le": ci.ref_le,
                    "descricao_no_orcamento": ci.descricao_no_orcamento,
                    "pliq": pliq,
                    "und": und,
                    "desp": desp,
                    "comp_mp": comp_mp,
                    "larg_mp": larg_mp,
                    "esp_mp": float(ci.esp_mp or 0),
                    "qt_placas_utilizadas": 0.0,
                    "area_placa": area_placa,
                    "m2_consumidos": 0.0,
                    "m2_total_pecas": 0.0,
                    "custo_mp_total": 0.0,
                    "custo_placas_utilizadas": 0.0,
                }
            placas_map[key]["qt_placas_utilizadas"] += qt_placas
            placas_map[key]["m2_consumidos"] += m2_consumidos
            placas_map[key]["m2_total_pecas"] += m2_total_pecas
            placas_map[key]["custo_mp_total"] += float(ci.custo_mp_total or 0)
            placas_map[key]["custo_placas_utilizadas"] += custo_placas_utilizadas
        result["placas"] = list(placas_map.values())

        # ------------ Orlas ------------
        orlas_map: dict[tuple, dict] = {}
        for ci in cust_rows:
            qt_total = float(ci.qt_total or 0)
            largura_orla = _orla_width_from_esp(getattr(ci, "esp_res", None) or getattr(ci, "esp_mp", None))
            ref_map = {
                1: getattr(ci, "orl_0_4", None) or getattr(ci, "corres_orla_0_4", None) or "",
                2: getattr(ci, "orl_1_0", None) or getattr(ci, "corres_orla_1_0", None) or "",
            }
            sides = [
                (getattr(ci, "orl_c1", 0), getattr(ci, "ml_orl_c1", 0), getattr(ci, "custo_orl_c1", 0)),
                (getattr(ci, "orl_c2", 0), getattr(ci, "ml_orl_c2", 0), getattr(ci, "custo_orl_c2", 0)),
                (getattr(ci, "orl_l1", 0), getattr(ci, "ml_orl_l1", 0), getattr(ci, "custo_orl_l1", 0)),
                (getattr(ci, "orl_l2", 0), getattr(ci, "ml_orl_l2", 0), getattr(ci, "custo_orl_l2", 0)),
            ]
            for code_raw, ml_raw, custo_raw in sides:
                try:
                    code_val = float(code_raw or 0)
                except Exception:
                    code_val = 0.0
                if code_val <= 0:
                    continue
                if code_val >= 0.9:
                    code = 2
                    esp_descr = "1.0mm"
                else:
                    code = 1
                    esp_descr = "0.4mm"
                ref_orl = ref_map.get(code) or ""
                if not ref_orl:
                    continue
                ml_val = float(ml_raw or 0) * qt_total
                custo_val = float(custo_raw or 0) * qt_total
                if ml_val == 0 and custo_val == 0:
                    continue
                key = (ref_orl, ci.descricao_no_orcamento, esp_descr)
                if key not in orlas_map:
                    orlas_map[key] = {
                        "ref_orla": ref_orl,
                        "descricao_material": ci.descricao_no_orcamento,
                        "espessura_orla": esp_descr,
                        "largura_orla": largura_orla,
                        "ml_total": 0.0,
                        "custo_total": 0.0,
                    }
                orlas_map[key]["ml_total"] += ml_val
                orlas_map[key]["custo_total"] += custo_val
        result["orlas"] = list(orlas_map.values())

        # ------------ Ferragens ------------
        ferr_map: dict[tuple, dict] = {}
        for ci in cust_rows:
            ref = (ci.ref_le or "").upper()
            if not ref.startswith("FER"):
                continue
            key = (ci.ref_le, ci.descricao_no_orcamento)
            qt_total = float(ci.qt_total or 0)
            spp_ml_total = float(ci.spp_ml_und or 0) * qt_total
            if key not in ferr_map:
                ferr_map[key] = {
                    "ref_le": ci.ref_le,
                    "descricao_no_orcamento": ci.descricao_no_orcamento,
                    "pliq": float(ci.pliq or 0),
                    "und": ci.und,
                    "desp": float(ci.desp or 0),
                    "comp_mp": float(ci.comp_mp or 0),
                    "larg_mp": float(ci.larg_mp or 0),
                    "esp_mp": float(ci.esp_mp or 0),
                    "qt_total": 0.0,
                    "spp_ml_total": 0.0,
                    "custo_mp_und": float(ci.custo_mp_und or 0),
                    "custo_mp_total": 0.0,
                }
            ferr_map[key]["qt_total"] += qt_total
            ferr_map[key]["spp_ml_total"] += spp_ml_total
            ferr_map[key]["custo_mp_total"] += float(ci.custo_mp_total or 0)
        result["ferr"] = list(ferr_map.values())

        # ------------ Máquinas / MO ------------
        def get_cost(filter_attr: str) -> float:
            return sum(
                float(getattr(ci, f"{filter_attr}_und") or 0) * float(ci.qt_total or 0)
                for ci in cust_rows
                if getattr(ci, filter_attr) and float(getattr(ci, filter_attr) or 0) > 0
            )

        def get_ml_corte() -> float:
            total = 0.0
            for ci in cust_rows:
                if float(ci.cp01_sec or 0) <= 0:
                    continue
                total += ((float(ci.comp_res or 0) * 2 + float(ci.larg_res or 0) * 2) * float(ci.qt_total or 0)) / 1000.0
            return round(total, 2)

        def get_ml_orla() -> float:
            total = 0.0
            for ci in cust_rows:
                if float(ci.cp02_orl or 0) <= 0:
                    continue
                total += sum(float(x or 0) for x in [
                    getattr(ci, "ml_orl_c1", 0),
                    getattr(ci, "ml_orl_c2", 0),
                    getattr(ci, "ml_orl_l1", 0),
                    getattr(ci, "ml_orl_l2", 0),
                ]) * float(ci.qt_total or 0)
            return round(total, 2)

        maq_rows = []
        maq_rows.append({
            "operacao": "Seccionadora (Corte)",
            "custo_total": round(get_cost("cp01_sec"), 2),
            "ml_corte": get_ml_corte(),
            "ml_orlado": "",
            "num_pecas": int(sum(float(ci.qt_total or 0) for ci in cust_rows if float(ci.cp01_sec or 0) > 0)),
        })
        maq_rows.append({
            "operacao": "Orladora (Orlagem)",
            "custo_total": round(get_cost("cp02_orl"), 2),
            "ml_corte": "",
            "ml_orlado": get_ml_orla(),
            "num_pecas": int(sum(float(ci.qt_total or 0) for ci in cust_rows if float(ci.cp02_orl or 0) > 0)),
        })
        maq_rows.append({
            "operacao": "CNC (Mecanizações)",
            "custo_total": round(get_cost("cp03_cnc"), 2),
            "ml_corte": "",
            "ml_orlado": "",
            "num_pecas": int(sum(float(ci.qt_total or 0) for ci in cust_rows if float(ci.cp03_cnc or 0) > 0)),
        })
        maq_rows.append({
            "operacao": "ABD (Mecanizações)",
            "custo_total": round(get_cost("cp04_abd"), 2),
            "ml_corte": "",
            "ml_orlado": "",
            "num_pecas": int(sum(float(ci.qt_total or 0) for ci in cust_rows if float(ci.cp04_abd or 0) > 0)),
        })
        maq_rows.append({"operacao": "Prensa (Montagem)", "custo_total": round(get_cost("cp05_prensa"), 2), "ml_corte": "", "ml_orlado": "", "num_pecas": ""})
        maq_rows.append({"operacao": "Esquadrejadora (Cortes Manuais)", "custo_total": round(get_cost("cp06_esquad"), 2), "ml_corte": "", "ml_orlado": "", "num_pecas": ""})
        maq_rows.append({"operacao": "Embalamento (Paletização)", "custo_total": round(get_cost("cp07_embalagem"), 2), "ml_corte": "", "ml_orlado": "", "num_pecas": ""})
        maq_rows.append({"operacao": "Mão de Obra (MO geral)", "custo_total": round(get_cost("cp08_mao_de_obra"), 2), "ml_corte": "", "ml_orlado": "", "num_pecas": ""})
        result["maq"] = maq_rows
        return result

    def _refresh_dashboard(self) -> None:
        if not MATPLOTLIB_AVAILABLE:
            QtWidgets.QMessageBox.information(self, "Resumo de Consumos", "Instale 'matplotlib' para usar o dashboard.")
            return
        orc = self._current_orcamento
        cli = self._current_client
        if self._dash_info_labels:
            self._dash_info_labels["ano"].setText(str(getattr(orc, "ano", "") or "-"))
            self._dash_info_labels["cliente"].setText(str(getattr(cli, "nome", "") or "-"))
            self._dash_info_labels["orc"].setText(str(getattr(orc, "num_orcamento", "") or "-"))
            self._dash_info_labels["versao"].setText(self._format_versao(getattr(orc, "versao", "")) if orc else "-")
            self._dash_info_labels["user"].setText(str(getattr(self.current_user, "username", "") or "-"))
        try:
            self._dashboard_data = self._compute_resumos_dashboard()
            self._update_dashboard_ui()
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Resumo de Consumos", f"Falha ao atualizar dashboard: {exc}")

    def _update_dashboard_ui(self) -> None:
        data = self._dashboard_data or {}
        # tabelas
        def fmt_auto(v):
            if v is None or v == "":
                return ""
            try:
                val = float(v)
            except Exception:
                return v
            if abs(val - round(val)) < 0.005:
                return f"{round(val):.0f}"
            if abs(val*10 - round(val*10)) < 0.05:
                return f"{val:.1f}"
            return f"{val:.2f}"

        def fmt_unit(unit: str, decimals: Optional[int] = None):
            def _f(v):
                if v is None or v == "":
                    return ""
                try:
                    num = float(v)
                except Exception:
                    return v
                if decimals is None:
                    try:
                        val = float(f"{num:.2f}")
                    except Exception:
                        val = num
                    if abs(val - round(val)) < 0.005:
                        txt = f"{round(val):.0f}"
                    elif abs(val * 10 - round(val * 10)) < 0.05:
                        txt = f"{val:.1f}"
                    else:
                        txt = f"{val:.2f}"
                else:
                    txt = f"{num:.{decimals}f}"
                return f"{txt} {unit}" if unit else txt
            return _f

        moedas = fmt_unit("€", 2)
        m2_fmt = fmt_unit("m2", 2)
        ml_fmt = fmt_unit("ml", 2)
        mm_fmt = fmt_unit("mm", 0)

        placas_cols = [
            ("Ref.", "ref_le"),
            ("Descrição", "descricao_no_orcamento"),
            ("P.Liq", "pliq", moedas),
            ("Und", "und"),
            ("Desp.", "desp", fmt_auto),
            ("Comp.", "comp_mp", mm_fmt),
            ("Larg.", "larg_mp", mm_fmt),
            ("Esp.", "esp_mp", mm_fmt),
            ("Qt.Pla.", "qt_placas_utilizadas", fmt_auto),
            ("Área", "area_placa", m2_fmt),
            ("m2 Usad.", "m2_consumidos", m2_fmt),
            ("m2_total_pecas", "m2_total_pecas", m2_fmt),
            ("C.MP Tot", "custo_mp_total", moedas),
            ("C.Placa Usad.", "custo_placas_utilizadas", moedas),
        ]
        orlas_cols = [
            ("Ref. Orla", "ref_orla"),
            ("Descr. Mat.", "descricao_material"),
            ("Esp.", "espessura_orla"),
            ("Larg.", "largura_orla", mm_fmt),
            ("ML Tot.", "ml_total", ml_fmt),
            ("Custo Tot", "custo_total", moedas),
        ]
        ferr_cols = [
            ("Ref.", "ref_le"),
            ("Descrição", "descricao_no_orcamento"),
            ("P.Liq", "pliq", moedas),
            ("Und", "und"),
            ("Desp.", "desp", fmt_auto),
            ("Comp.", "comp_mp", mm_fmt),
            ("Larg.", "larg_mp", mm_fmt),
            ("Esp.", "esp_mp", mm_fmt),
            ("Qt", "qt_total", fmt_auto),
            ("ML Sup.", "spp_ml_total", ml_fmt),
            ("Custo Und", "custo_mp_und", moedas),
            ("Custo Tot", "custo_mp_total", moedas),
        ]
        maq_cols = [
            ("Operação", "operacao"),
            ("Custo Total (€)", "custo_total", moedas),
            ("ML Corte", "ml_corte", ml_fmt),
            ("ML Orlado", "ml_orlado", ml_fmt),
            ("Nº Peças", "num_pecas", fmt_auto),
        ]

        self.tbl_dash_placas.setModel(SimpleTableModel(data.get("placas", []), placas_cols, self.tbl_dash_placas))
        self.tbl_dash_orlas.setModel(SimpleTableModel(data.get("orlas", []), orlas_cols, self.tbl_dash_orlas))
        self.tbl_dash_ferr.setModel(SimpleTableModel(data.get("ferr", []), ferr_cols, self.tbl_dash_ferr))
        self.tbl_dash_maq.setModel(SimpleTableModel(data.get("maq", []), maq_cols, self.tbl_dash_maq))

        tooltips = {
            "Resumo de Placas": "Placas (M2): área usada, despesa, custo teórico (C.MP Tot) e custo real consumido (C.Placa Usad.). Origem: custeio_items.",
            "Resumo de Orlas": "Orlas por referência/espessura, ML total e custo total. Origem: custeio_items (ml_orl_*, custo_total_orla).",
            "Resumo de Ferragens": "Ferragens com quantidades/ML/custos unitário e total. Origem: custeio_items (custo_mp_total, spp_ml_und).",
            "Resumo de Máquinas / MO": "Custos por operação e ML corte/orlado; nº peças processadas. Origem: custeio_items (cp01..cp08).",
        }
        for tbl, title in (
            (self.tbl_dash_placas, "Resumo de Placas"),
            (self.tbl_dash_orlas, "Resumo de Orlas"),
            (self.tbl_dash_ferr, "Resumo de Ferragens"),
            (self.tbl_dash_maq, "Resumo de Máquinas / MO"),
        ):
            tbl.setAlternatingRowColors(True)
            header = tbl.horizontalHeader()
            font = header.font()
            font.setBold(True)
            header.setFont(font)
            header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
            header.setStretchLastSection(False)
            tbl.verticalHeader().setVisible(False)
            tbl.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
            tbl.setMinimumHeight(460)
            if title in tooltips:
                header.setToolTip(tooltips[title])

        # gráficos
        self._plot_dashboard_charts()

    def _plot_dashboard_charts(self) -> None:
        data = self._dashboard_data or {}
        def wrap_label(text: str, max_len: int = 18) -> str:
            if not text:
                return ""
            if len(text) <= max_len:
                return text
            parts = text.split()
            lines = []
            current = ""
            for p in parts:
                if len(current) + len(p) + 1 <= max_len:
                    current = f"{current} {p}".strip()
                else:
                    if current:
                        lines.append(current)
                    current = p
            if current:
                lines.append(current)
            return "\n".join(lines) if lines else text

        # Placas
        placas = data.get("placas", [])
        self.ax_placas.clear()
        if placas:
            labels = [wrap_label(p.get("descricao_no_orcamento") or p.get("ref_le") or "") for p in placas]
            x = list(range(len(labels)))
            teor = [float(p.get("custo_mp_total", 0) or 0) for p in placas]
            real = [float(p.get("custo_placas_utilizadas", 0) or 0) for p in placas]
            width = 0.35
            self.ax_placas.bar([xi - width / 2 for xi in x], teor, width=width, label="Custo Teórico", color="#7ec0ee")
            self.ax_placas.bar([xi + width / 2 for xi in x], real, width=width, label="Custo Real", color="#ef5350")
            self.ax_placas.set_xticks(x)
            self.ax_placas.set_xticklabels(labels, rotation=20, ha="right")
            self.ax_placas.set_ylabel("Custo (€)")
            self.ax_placas.tick_params(axis="x", labelsize=8)
            self.ax_placas.tick_params(axis="y", labelsize=8)
            self.ax_placas.legend(fontsize=9)
            for xi, val in zip(x, real):
                self.ax_placas.text(xi + width / 2, val, f"{val:.2f}", ha="center", va="bottom", fontsize=8)
            self.ax_placas.set_title("Comparativo de Custos por Placa")
        else:
            self.ax_placas.text(0.5, 0.5, "Sem dados", ha="center", va="center")
        self.canvas_placas.draw_idle()

        # Orlas
        orlas = data.get("orlas", [])
        self.ax_orlas.clear()
        if orlas:
            labels = [wrap_label(f"{o.get('ref_orla','')} ({o.get('espessura_orla','')})") for o in orlas]
            x = list(range(len(labels)))
            ml = [float(o.get("ml_total", 0) or 0) for o in orlas]
            bars = self.ax_orlas.bar(x, ml, color="#ffa726")
            self.ax_orlas.set_xticks(x)
            self.ax_orlas.set_xticklabels(labels, rotation=25, ha="right")
            self.ax_orlas.set_ylabel("Metros Lineares (ml)")
            self.ax_orlas.tick_params(axis="x", labelsize=8)
            self.ax_orlas.tick_params(axis="y", labelsize=8)
            self.ax_orlas.set_title("Consumo de Orlas (ml)")
            for rect, val in zip(bars, ml):
                self.ax_orlas.text(rect.get_x() + rect.get_width() / 2, rect.get_height(), f"{val:.2f}", ha="center", va="bottom", fontsize=8)
        else:
            self.ax_orlas.text(0.5, 0.5, "Sem dados", ha="center", va="center")
        self.canvas_orlas.draw_idle()

        # Ferragens
        ferr = data.get("ferr", [])
        self.ax_ferr.clear()
        if ferr:
            labels = [wrap_label(f.get("descricao_no_orcamento") or f.get("ref_le") or "") for f in ferr]
            x = list(range(len(labels)))
            custos = [float(f.get("custo_mp_total", 0) or 0) for f in ferr]
            bars = self.ax_ferr.bar(x, custos, color="#ef5350")
            self.ax_ferr.set_xticks(x)
            self.ax_ferr.set_xticklabels(labels, rotation=25, ha="right")
            self.ax_ferr.set_ylabel("Custo (€)")
            self.ax_ferr.tick_params(axis="x", labelsize=8)
            self.ax_ferr.tick_params(axis="y", labelsize=8)
            self.ax_ferr.set_title("Custos por Ferragem")
            for rect, val in zip(bars, custos):
                self.ax_ferr.text(rect.get_x() + rect.get_width() / 2, rect.get_height(), f"{val:.2f}", ha="center", va="bottom", fontsize=8)
        else:
            self.ax_ferr.text(0.5, 0.5, "Sem dados", ha="center", va="center")
        self.canvas_ferr.draw_idle()

        # Operações
        maq = data.get("maq", [])
        self.ax_ops.clear()
        if maq:
            labels = [wrap_label(m.get("operacao", "")) for m in maq]
            x = list(range(len(labels)))
            custos = [float(m.get("custo_total", 0) or 0) for m in maq]
            bars = self.ax_ops.bar(x, custos, color="#42a5f5")
            self.ax_ops.set_xticks(x)
            self.ax_ops.set_xticklabels(labels, rotation=20, ha="right")
            self.ax_ops.set_ylabel("Custo (€)")
            self.ax_ops.tick_params(axis="x", labelsize=8)
            self.ax_ops.tick_params(axis="y", labelsize=8)
            self.ax_ops.set_title("Custos por Operação")
            for rect, val in zip(bars, custos):
                self.ax_ops.text(rect.get_x() + rect.get_width() / 2, rect.get_height(), f"{val:.2f}", ha="center", va="bottom", fontsize=8)
        else:
            self.ax_ops.text(0.5, 0.5, "Sem dados", ha="center", va="center")
        self.canvas_ops.draw_idle()

        # Pizza
        self.ax_pie.clear()
        total_placas = sum(float(p.get("custo_placas_utilizadas", 0) or 0) for p in placas)
        total_orlas = sum(float(o.get("custo_total", 0) or 0) for o in orlas)
        total_ferr = sum(float(f.get("custo_mp_total", 0) or 0) for f in ferr)
        total_maq = sum(float(m.get("custo_total", 0) or 0) for m in maq)
        valores = [total_placas, total_orlas, total_ferr, total_maq]
        labels_pie = ["Placas", "Orlas", "Ferragens", "Máquinas/MO"]
        if sum(valores) > 0:
            wedges, texts, autotexts = self.ax_pie.pie(valores, labels=labels_pie, autopct="%1.1f%%", startangle=90, pctdistance=0.8)
            for t in texts + autotexts:
                t.set_fontsize(8)
            self.ax_pie.set_title("Distribuição de Custos")
            # tabela ao lado com valores em €
            total_sum = sum(valores)
            table_data = [["Tipo", "€", "%"]]
            for label, val in zip(labels_pie, valores):
                pct = (val / total_sum * 100) if total_sum else 0
                table_data.append([label, f"{val:.2f}", f"{pct:.1f}%"])
            table = self.ax_pie.table(cellText=table_data, colWidths=[0.55, 0.45, 0.35], cellLoc="center", bbox=[1.25, 0.15, 0.8, 0.7])
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            for (row, col), cell in table.get_celld().items():
                if row == 0:
                    cell.set_text_props(weight="bold")
        else:
            self.ax_pie.text(0.5, 0.5, "Sem dados", ha="center", va="center")
        self.canvas_pie.draw_idle()

    def _export_dashboard_pdf(self) -> None:
        if not MATPLOTLIB_AVAILABLE:
            QtWidgets.QMessageBox.information(self, "Dashboard", "Instale 'matplotlib' para exportar o dashboard.")
            return
        if not self._current_orcamento:
            QtWidgets.QMessageBox.information(self, "Dashboard", "Selecione um orçamento.")
            return
        # garantir dados atualizados
        self._refresh_dashboard()
        data = self._dashboard_data or {}
        orc = self._current_orcamento
        client = self._current_client
        try:
            export_dir = self._determine_export_folder(orc, client)
            export_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Dashboard", f"Falha ao preparar pasta: {exc}")
            return
        fname = f"Resumo_Custos_Dashboard_{orc.num_orcamento or 'ORC'}_{self._format_versao(orc.versao)}.pdf"
        dest = export_dir / fname

        header_line = f"Ano: {getattr(orc, 'ano', '') or '-'}  |  Cliente: {(getattr(client, 'nome', '') or '-')}  |  Nº Orçamento: {orc.num_orcamento or ''}  |  Versão: {self._format_versao(orc.versao)}  |  Utilizador: {getattr(self.current_user, 'username', '') or '-'}"
        today = QtCore.QDate.currentDate().toString("dd/MM/yyyy")

        def add_header_footer(fig: Figure, page_idx: int, total: int) -> None:
            fig.text(0.02, 0.98, header_line, va="top", ha="left", fontsize=9, fontweight="bold")
            fig.text(0.02, 0.02, today, ha="left", va="bottom", fontsize=8)
            fig.text(0.98, 0.02, f"{page_idx}/{total}", ha="right", va="bottom", fontsize=8)

        # Definir novamente colunas/formatos para uso no PDF (evita NameError)
        def fmt_auto(v):
            if v is None or v == "":
                return ""
            try:
                val = float(v)
            except Exception:
                return v
            if abs(val - round(val)) < 0.005:
                return f"{round(val):.0f}"
            if abs(val * 10 - round(val * 10)) < 0.05:
                return f"{val:.1f}"
            return f"{val:.2f}"

        def fmt_unit(unit: str, decimals: Optional[int] = None):
            def _f(v):
                if v is None or v == "":
                    return ""
                try:
                    num = float(v)
                except Exception:
                    return v
                if decimals is None:
                    if abs(num - round(num)) < 0.005:
                        txt = f"{round(num):.0f}"
                    elif abs(num * 10 - round(num * 10)) < 0.05:
                        txt = f"{num:.1f}"
                    else:
                        txt = f"{num:.2f}"
                else:
                    txt = f"{num:.{decimals}f}"
                return f"{txt} {unit}" if unit else txt
            return _f

        moedas = fmt_unit("€", 2)
        m2_fmt = fmt_unit("m2", 2)
        ml_fmt = fmt_unit("ml", 2)
        mm_fmt = fmt_unit("mm", 0)

        placas_cols = [
            ("Ref.", "ref_le", None),
            ("Descrição", "descricao_no_orcamento", None),
            ("P.Liq", "pliq", moedas),
            ("Und", "und", None),
            ("Desp.", "desp", fmt_auto),
            ("Comp.", "comp_mp", mm_fmt),
            ("Larg.", "larg_mp", mm_fmt),
            ("Esp.", "esp_mp", mm_fmt),
            ("Qt.Pla.", "qt_placas_utilizadas", fmt_auto),
            ("Área", "area_placa", m2_fmt),
            ("m2 Usad.", "m2_consumidos", m2_fmt),
            ("m2_total_pecas", "m2_total_pecas", m2_fmt),
            ("C.MP Tot", "custo_mp_total", moedas),
            ("C.Placa Usad.", "custo_placas_utilizadas", moedas),
        ]
        orlas_cols = [
            ("Ref. Orla", "ref_orla", None),
            ("Descr. Mat.", "descricao_material", None),
            ("Esp.", "espessura_orla", None),
            ("Larg.", "largura_orla", mm_fmt),
            ("ML Tot.", "ml_total", ml_fmt),
            ("Custo Tot", "custo_total", moedas),
        ]
        ferr_cols = [
            ("Ref.", "ref_le", None),
            ("Descrição", "descricao_no_orcamento", None),
            ("P.Liq", "pliq", moedas),
            ("Und", "und", None),
            ("Desp.", "desp", fmt_auto),
            ("Comp.", "comp_mp", mm_fmt),
            ("Larg.", "larg_mp", mm_fmt),
            ("Esp.", "esp_mp", mm_fmt),
            ("Qt", "qt_total", fmt_auto),
            ("ML Sup.", "spp_ml_total", ml_fmt),
            ("Custo Und", "custo_mp_und", moedas),
            ("Custo Tot", "custo_mp_total", moedas),
        ]
        maq_cols = [
            ("Operação", "operacao", None),
            ("Custo Total (€)", "custo_total", moedas),
            ("ML Corte", "ml_corte", ml_fmt),
            ("ML Orlado", "ml_orlado", ml_fmt),
            ("Nº Peças", "num_pecas", fmt_auto),
        ]

        # Páginas de gráficos: 2 gráficos por página
        def build_chart_page(pairs: List[Tuple[str, List[Any], str]]) -> Figure:
            fig = Figure(figsize=(11.7, 8.3))
            fig.subplots_adjust(top=0.9, hspace=0.4, wspace=0.25, left=0.08, right=0.95)
            axes = [fig.add_subplot(121), fig.add_subplot(122)]
            def wrap_label(text: str, max_len: int = 18) -> str:
                if not text:
                    return ""
                if len(text) <= max_len:
                    return text
                parts = text.split()
                lines = []
                current = ""
                for p in parts:
                    if len(current) + len(p) + 1 <= max_len:
                        current = f"{current} {p}".strip()
                    else:
                        if current:
                            lines.append(current)
                        current = p
                if current:
                    lines.append(current)
                return "\n".join(lines) if lines else text
            for ax, (chart_type, dataset, title_txt) in zip(axes, pairs):
                if chart_type == "placas":
                    lbls = [wrap_label(p.get("descricao_no_orcamento") or p.get("ref_le") or "") for p in dataset]
                    xvals = list(range(len(lbls)))
                    teor = [float(p.get("custo_mp_total", 0) or 0) for p in dataset]
                    real = [float(p.get("custo_placas_utilizadas", 0) or 0) for p in dataset]
                    width = 0.35
                    ax.bar([xi - width / 2 for xi in xvals], teor, width=width, label="Custo Teórico", color="#7ec0ee")
                    ax.bar([xi + width / 2 for xi in xvals], real, width=width, label="Custo Real", color="#ef5350")
                    ax.set_xticks(xvals)
                    ax.set_xticklabels(lbls, rotation=20, ha="right", fontsize=7)
                    ax.set_ylabel("Custo (€)", fontsize=9)
                    ax.tick_params(axis="y", labelsize=8)
                    ax.legend(fontsize=8)
                    ax.set_title(title_txt, fontsize=11, fontweight="bold")
                elif chart_type == "orlas":
                    lbls = [wrap_label(f"{o.get('ref_orla','')} ({o.get('espessura_orla','')})") for o in dataset]
                    xvals = list(range(len(lbls)))
                    vals = [float(o.get("ml_total", 0) or 0) for o in dataset]
                    bars = ax.bar(xvals, vals, color="#ffa726")
                    ax.set_xticks(xvals)
                    ax.set_xticklabels(lbls, rotation=25, ha="right", fontsize=7)
                    ax.set_ylabel("Metros Lineares (ml)", fontsize=9)
                    ax.tick_params(axis="y", labelsize=8)
                    ax.set_title(title_txt, fontsize=11, fontweight="bold")
                    for rect, val in zip(bars, vals):
                        ax.text(rect.get_x() + rect.get_width() / 2, rect.get_height(), f"{val:.2f}", ha="center", va="bottom", fontsize=7)
                elif chart_type == "ferr":
                    lbls = [wrap_label(f.get("descricao_no_orcamento") or f.get("ref_le") or "", 22) for f in dataset]
                    xvals = list(range(len(lbls)))
                    vals = [float(f.get("custo_mp_total", 0) or 0) for f in dataset]
                    bars = ax.bar(xvals, vals, color="#ef5350")
                    ax.set_xticks(xvals)
                    ax.set_xticklabels(lbls, rotation=25, ha="right", fontsize=7)
                    ax.set_ylabel("Custo (€)", fontsize=9)
                    ax.tick_params(axis="y", labelsize=8)
                    ax.set_title(title_txt, fontsize=11, fontweight="bold")
                    for rect, val in zip(bars, vals):
                        ax.text(rect.get_x() + rect.get_width() / 2, rect.get_height(), f"{val:.2f}", ha="center", va="bottom", fontsize=7)
                elif chart_type == "ops":
                    lbls = [wrap_label(m.get("operacao", ""), 20) for m in dataset]
                    xvals = list(range(len(lbls)))
                    vals = [float(m.get("custo_total", 0) or 0) for m in dataset]
                    bars = ax.bar(xvals, vals, color="#42a5f5")
                    ax.set_xticks(xvals)
                    ax.set_xticklabels(lbls, rotation=20, ha="right", fontsize=7)
                    ax.set_ylabel("Custo (€)", fontsize=9)
                    ax.tick_params(axis="y", labelsize=8)
                    ax.set_title(title_txt, fontsize=11, fontweight="bold")
                    for rect, val in zip(bars, vals):
                        ax.text(rect.get_x() + rect.get_width() / 2, rect.get_height(), f"{val:.2f}", ha="center", va="bottom", fontsize=7)
                elif chart_type == "pie":
                    total_placas = sum(float(p.get("custo_placas_utilizadas", 0) or 0) for p in dataset or [])
                    total_orlas = sum(float(o.get("custo_total", 0) or 0) for o in data.get("orlas", []))
                    total_ferr = sum(float(f.get("custo_mp_total", 0) or 0) for f in data.get("ferr", []))
                    total_maq = sum(float(m.get("custo_total", 0) or 0) for m in data.get("maq", []))
                    valores_local = [total_placas, total_orlas, total_ferr, total_maq]
                    labels_pie = ["Placas", "Orlas", "Ferragens", "Máquinas/MO"]
                    if sum(valores_local) > 0:
                        wedges, texts, autotexts = ax.pie(valores_local, labels=labels_pie, autopct="%1.1f%%", startangle=90, pctdistance=0.8)
                        for t in texts + autotexts:
                            t.set_fontsize(7)
                        total_sum = sum(valores_local)
                        table_data = [["Tipo", "€", "%"]]
                        for lbl, val in zip(labels_pie, valores_local):
                            pct = (val / total_sum * 100) if total_sum else 0
                            table_data.append([lbl, f"{val:.2f}", f"{pct:.1f}%"])
                        table = ax.table(cellText=table_data, colWidths=[0.6, 0.5, 0.4], cellLoc="center", bbox=[1.3, 0.1, 0.85, 0.8])
                        table.auto_set_font_size(False)
                        table.set_fontsize(8)
                        for (row, col), cell in table.get_celld().items():
                            if row == 0:
                                cell.set_text_props(weight="bold")
                        ax.set_title(title_txt, fontsize=11, fontweight="bold")
                    else:
                        ax.text(0.5, 0.5, "Sem dados", ha="center", va="center")
            return fig

        fig1 = build_chart_page([
            ("placas", data.get("placas", []), "Comparativo de Custos por Placa"),
            ("orlas", data.get("orlas", []), "Consumo de Orlas (ml)"),
        ])
        fig2 = build_chart_page([
            ("ferr", data.get("ferr", []), "Custos por Ferragem"),
            ("ops", data.get("maq", []), "Custos por Operação"),
        ])

        add_header_footer(fig1, 1, 3)

        # Página de tabelas Placas / Orlas
        def build_table_fig(title: str, headers_rows: List[Tuple[str, List[List[str]]]]) -> Figure:
            """
            Constrói uma figura com 1 coluna e N linhas (cada linha = um 'Resumo ...')
            Ajusta dinamicamente top / hspace / pad do título para evitar sobreposição
            entre o suptitle (título da figura) e os títulos dos subplots.
            """
            fig = Figure(figsize=(11.7, 8.3))

            # --- Parâmetros dinâmicos para evitar sobreposição ---
            n_blocks = len(headers_rows)
            # Se tivermos 2 (ou mais) blocos, precisamos de mais espaço no topo
            if n_blocks >= 2:
                top = 0.75         # área de subplot termina mais em baixo -> mais folga acima
                suptitle_y = 0.92  # suptitle colocado abaixo do header (header está ~0.98)
                hspace = 0.50      # mais espaço entre blocos
                title_pad = 12     # distância do título do subplot ao conteúdo (padrão/ligeramente menor)
                suptitle_fontsize = 13  # ligeiramente menor para ocupar menos espaço vertical
            else:
                # caso 1 bloco; espaços mais modestos
                top = 0.92
                suptitle_y = 0.96
                hspace = 0.25
                title_pad = 14
                suptitle_fontsize = 14

            # Aplica os ajustes de layout
            fig.subplots_adjust(top=top, left=0.03, right=0.97, hspace=hspace)

            # Criar grid para N blocos (1 coluna)
            gs = fig.add_gridspec(n_blocks, 1)

            for idx, (title_sub, rows) in enumerate(headers_rows):
                ax = fig.add_subplot(gs[idx, 0])
                ax.axis("off")
                if not rows:
                    ax.text(0.5, 0.5, "Sem dados", ha="center", va="center")
                    continue

                header = rows[0]
                body = rows[1:]

                # usa width_map definido no scope exterior (mantive a lógica original)
                widths = width_map.get(title_sub)
                if widths:
                    total = sum(widths)
                    col_widths = [w / total for w in widths]
                else:
                    col_widths = None

                # cria a tabela (igual à implementação anterior)
                table = ax.table(cellText=body, colLabels=header, loc="upper center", cellLoc="center", colWidths=col_widths)
                table.auto_set_font_size(False)
                table.set_fontsize(7)
                for key, cell in table.get_celld().items():
                    if key[0] == 0:
                        cell.set_text_props(weight="bold")

                # Define o título do subplot COM UM PAD MAIOR para afastar do conteúdo
                ax.set_title(title_sub, fontsize=10, fontweight="bold", pad=title_pad)

            # Suptitle (título geral) posicionado mais baixo quando há vários blocos
            fig.suptitle(title, fontsize=11, fontweight="bold", y=suptitle_y)

            return fig

        def to_table_rows(data_list: list, cols: list) -> list:
            header = [c[0] for c in cols]
            rows = [header]
            for row in data_list:
                rows.append([(c[2](row.get(c[1])) if len(c) > 2 and callable(c[2]) else row.get(c[1], "")) for c in cols])
            return rows
        width_map = {
            "Resumo de Placas": [0.7, 3.0, 0.7, 0.5, 0.5, 0.8, 0.8, 0.6, 0.6, 0.7, 0.8, 0.8, 1.0, 1.0],
            "Resumo de Orlas": [0.9, 2.5, 0.7, 0.7, 0.8, 0.8],
            "Resumo de Ferragens": [0.9, 2.8, 0.6, 0.5, 0.5, 0.7, 0.7, 0.6, 0.6, 0.7, 0.8, 0.9],
            "Resumo de Máquinas / MO": [1.6, 0.9, 0.9, 0.9, 0.7],
        }

        rows_placas = to_table_rows(data.get("placas", []), placas_cols)
        rows_orlas = to_table_rows(data.get("orlas", []), orlas_cols)
        fig_tables1 = build_table_fig("Tabelas - Placas e Orlas", [("Resumo de Placas", rows_placas), ("Resumo de Orlas", rows_orlas)])

        rows_ferr = to_table_rows(data.get("ferr", []), ferr_cols)
        rows_maq = to_table_rows(data.get("maq", []), maq_cols)
        fig_tables2 = build_table_fig("Tabelas - Ferragens e Máquinas/MO", [("Resumo de Ferragens", rows_ferr), ("Resumo de Máquinas / MO", rows_maq)])

        add_header_footer(fig1, 1, 4)
        add_header_footer(fig2, 2, 4)
        add_header_footer(fig_tables1, 3, 4)
        add_header_footer(fig_tables2, 4, 4)

        with PdfPages(dest) as pdf:
            pdf.savefig(fig1)
            pdf.savefig(fig2)
            pdf.savefig(fig_tables1)
            pdf.savefig(fig_tables2)

        QtWidgets.QMessageBox.information(self, "Dashboard", f"Dashboard guardado em:\n{dest}")

    def _on_header_resized(self, section: int, _old: int, _new: int) -> None:
        if section == 2:
            QtCore.QTimer.singleShot(0, self._update_row_heights)

    def _update_row_heights(self) -> None:
        vh = self.table.verticalHeader()
        if vh is None:
            return
        model = self.table_model
        row_count = model.rowCount()
        if row_count <= 0:
            vh.setDefaultSectionSize(80)
            return
        width = max(150, self.table.columnWidth(2) - 12)
        doc = QtGui.QTextDocument()
        doc.setDefaultFont(self.table.font())
        for row in range(row_count):
            index = model.index(row, 2)
            html_text = index.data(Qt.DisplayRole) or ""
            doc.setHtml(html_text)
            doc.setTextWidth(width)
            height = doc.size().height() + 24
            vh.resizeSection(row, max(70, int(height)))

    # ------------------------------------------------------------------ EXPORT
    def export_to_excel(self) -> None:
        if not self.current_orcamento_id:
            QtWidgets.QMessageBox.information(self, "Relatórios", "Selecione um orçamento antes de exportar.")
            return
        if not self._current_orcamento or not self._current_items:
            self.refresh_preview()
            if not self._current_orcamento or not self._current_items:
                return

        orc = self._current_orcamento
        client = self._current_client
        num = orc.num_orcamento or "orcamento"
        ver = self._format_versao(orc.versao)
        default_name = f"{num}_{ver}.xlsx"
        export_dir = self._determine_export_folder(orc, client)
        try:
            export_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Exportar Excel", f"Falha ao preparar pasta do orçamento: {exc}")
            return
        file_path = export_dir / default_name
        try:
            self._build_workbook(file_path)
            self._export_resumo_custos(file_path.parent, orc, client)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Exportar Excel", f"Falha ao exportar: {exc}")
            return

        QtWidgets.QMessageBox.information(self, "Exportar Excel", f"Relatório guardado em:\n{file_path}")

    def _determine_export_folder(self, orc: Orcamento, client: Optional[Client]) -> Path:
        base_path = Path(self._get_setting_value(KEY_BASE_PATH, DEFAULT_BASE_PATH))
        ano = str(orc.ano or "")
        cliente_nome = (getattr(client, "nome_simplex", None) or getattr(client, "nome", None) or "CLIENTE")
        safe_cliente = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in cliente_nome.upper().replace(" ", "_"))
        pasta = f"{orc.num_orcamento or 'ORC'}_{safe_cliente}"
        versao = self._format_versao(orc.versao)
        return base_path / ano / pasta / versao

    def _get_setting_value(self, key: str, default: str) -> str:
        try:
            with SessionLocal() as session:
                return get_setting(session, key, default) or default
        except Exception:
            return default

    def _resolve_logo_path(self) -> Optional[Path]:
        base = self._get_setting_value(KEY_ORC_DB_BASE, DEFAULT_BASE_DADOS_ORC)
        candidate = Path(base) / "LE_Logotipo.png"
        return candidate if candidate.exists() else None

    @staticmethod
    def _safe_number(value) -> float:
        try:
            return float(value)
        except Exception:
            return 0.0

    def export_to_pdf(self) -> None:
        if not REPORTLAB_AVAILABLE:
            QtWidgets.QMessageBox.warning(
                self,
                "Exportar PDF",
                "Biblioteca reportlab não encontrada. Instale com 'pip install reportlab'.",
            )
            return
        if not self.current_orcamento_id:
            QtWidgets.QMessageBox.information(self, "Relatórios", "Selecione um orçamento antes de exportar.")
            return
        if not self._current_orcamento or not self._current_items:
            self.refresh_preview()
            if not self._current_orcamento or not self._current_items:
                return
        orc = self._current_orcamento
        client = self._current_client
        export_dir = self._determine_export_folder(orc, client)
        try:
            export_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Exportar PDF", f"Falha ao preparar pasta do orçamento: {exc}")
            return
        output_path = export_dir / f"{orc.num_orcamento or 'orcamento'}_{self._format_versao(orc.versao)}.pdf"
        try:
            self._build_pdf(output_path)
            self._export_resumo_custos(export_dir, orc, client)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Exportar PDF", f"Falha ao exportar: {exc}")
            return
        QtWidgets.QMessageBox.information(self, "Exportar PDF", f"Relatório guardado em:\n{output_path}")


    def _build_workbook(self, output_path: Path) -> None:
        """
        Gera o ficheiro Excel (usando xlsxwriter) com formatação semelhante ao PDF.
        Formato da coluna "Descrição":
        - 1.ª linha: título em MAIÚSCULAS e NEGRITO
        - linhas seguintes: cada '-' ou '*' em nova linha (ALT+ENTER) e em ITÁLICO
        - usa write_rich_string para manter formatação por sub-trecho da célula
        """
        # validações iniciais
        client = self._current_client
        orc = self._current_orcamento
        rows = self._current_items
        if not orc:
            raise ValueError("Nenhum orçamento disponível para exportar.")

        import xlsxwriter
        # Pillow opcional para dimensionar imagem com precisão
        try:
            from PIL import Image as PILImage
            PIL_AVAILABLE = True
        except Exception:
            PIL_AVAILABLE = False

        # cria workbook / worksheet
        wb = xlsxwriter.Workbook(str(output_path))
        ws = wb.add_worksheet("Relatório")

        # ----------------------------
        # FORMATOS (bordas nas células da tabela; totais sem borda)
        # ----------------------------
        azul_escuro = '#184ca7'
        fmt_title = wb.add_format({'bold': True, 'font_size': 15, 'align': 'center', 'valign': 'vcenter'})
        fmt_cliente = wb.add_format({'bold': True, 'font_size': 12, 'align': 'left', 'valign': 'vcenter'})
        fmt_info = wb.add_format({'bold': True, 'font_size': 12, 'align': 'right', 'valign': 'vcenter'})
        fmt_small = wb.add_format({'font_size': 10, 'align': 'left', 'valign': 'vcenter'})

        fmt_header = wb.add_format({'bold': True, 'bg_color': '#D9D9D9', 'align': 'center', 'border': 1, 'valign': 'vcenter', 'font_size': 9})
        fmt_cell = wb.add_format({'align': 'center', 'font_size': 10, 'border': 1, 'valign': 'vcenter'})

        # descrição: título e sublinhas (ambos com borda para manter consistência)
        fmt_descr_titulo = wb.add_format({'bold': True, 'font_size': 11, 'align': 'left', 'valign': 'top', 'border': 1})
        fmt_descr_sub = wb.add_format({'italic': True, 'font_size': 10, 'align': 'left', 'valign': 'top', 'border': 1})
        fmt_descr_container = wb.add_format({'border': 1, 'text_wrap': True, 'valign': 'top'})

        # formatos números com borda
        fmt_number = wb.add_format({'num_format': '0.00', 'align': 'right', 'border': 1, 'valign': 'vcenter'})
        fmt_money = wb.add_format({'num_format': '€ #,##0.00', 'align': 'right', 'valign': 'vcenter', 'border': 1})
        fmt_money_bold = wb.add_format({'num_format': '€ #,##0.00', 'align': 'right', 'bold': True, 'valign': 'vcenter', 'border': 1})

        # formato para linha padrão (só border) - usado como default da linha
        fmt_row_border = wb.add_format({'border': 1})
        # formatos para totais (sem borda) - o utilizador pediu sem limites
        fmt_total_label_nb = wb.add_format({'align': 'right', 'bold': True, 'font_size': 10, 'valign': 'vcenter', 'border': 0})
        fmt_total_val_nb = wb.add_format({'align': 'right', 'bold': True, 'font_size': 11, 'color': '#002060', 'valign': 'vcenter', 'border': 0})
        fmt_money_nb = wb.add_format({'num_format': '€ #,##0.00', 'align': 'right', 'valign': 'vcenter', 'border': 0})

        # formato Data (linha 3) alinhada à direita
        fmt_date_right = wb.add_format({'font_size': 10, 'align': 'right', 'valign': 'vcenter', 'border': 0})

        # ----------------------------
        # MARGENS / FIT / LINHA 2 = 50
        # ----------------------------
        ws.set_margins(left=0.2, right=0.2, top=0.2, bottom=0.25)
        ws.fit_to_pages(1, 0)
        ws.set_row(1, 50)  # linha 2 altura = 50

        # ----------------------------
        # LOGO - dimensões pedidas: largura 12.32 cm, altura 5.61 cm
        # ----------------------------
        logo_path = self._resolve_logo_path()
        if logo_path:
            try:
                desired_w_cm = 13.32
                desired_h_cm = 5.61
                if PIL_AVAILABLE:
                    pil_img = PILImage.open(str(logo_path))
                    img_w_px, img_h_px = pil_img.size
                    dpi = 96.0
                    desired_w_px = (desired_w_cm / 2.54) * dpi
                    desired_h_px = (desired_h_cm / 2.54) * dpi
                    x_scale = desired_w_px / img_w_px
                    y_scale = desired_h_px / img_h_px
                    ws.insert_image(0, 0, str(logo_path), {
                        'x_scale': x_scale, 'y_scale': y_scale, 'x_offset': 8, 'y_offset': 6, 'positioning': 1
                    })
                else:
                    # fallback - valores aproximados
                    ws.insert_image(0, 0, str(logo_path), {
                        'x_scale': 0.18 * (4.05/4.05), 'y_scale': 0.18 * (2.2/2.2), 'x_offset': 8, 'y_offset': 6, 'positioning': 1
                    })
            except Exception:
                pass

        # ----------------------------
        # CABEÇALHO (cliente / título / nº / data)
        # ----------------------------
        cliente_nome = (getattr(client, "nome", "") or "").upper()
        ws.merge_range(2, 0, 2, 2, cliente_nome, fmt_cliente)            # linha 3
        ws.merge_range(0, 3, 0, 9, "Relatório de Orçamento", fmt_title)  # título
        ws.merge_range(1, 3, 1, 9, f"Nº Orçamento: {orc.num_orcamento or ''}_{self._format_versao(orc.versao)}", fmt_info)
        ws.merge_range(2, 3, 2, 9, f"Data: {orc.data or ''}", fmt_date_right)

        ws.merge_range(3, 0, 3, 2, getattr(client, "morada", "") or "", fmt_small)
        ws.merge_range(4, 0, 4, 2, getattr(client, "email", "") or "", fmt_small)
        contactos = f"Telefone: {(getattr(client,'telefone','') or '')}  |  Telemóvel: {(getattr(client,'telemovel','') or '')}"
        ws.merge_range(5, 0, 5, 2, contactos, fmt_small)

        ws.merge_range(6, 0, 6, 2, f"Ref.: {orc.ref_cliente or '-'}", wb.add_format({'bold': True, 'font_size': 12, 'font_color': azul_escuro, 'border': 0}))
        ws.merge_range(6, 3, 6, 9, f"Obra: {orc.obra or '-'}", wb.add_format({'bold': True, 'font_size': 12, 'font_color': 'red', 'align': 'right', 'border': 0}))

        # ----------------------------
        # CABEÇALHO TABELA
        # ----------------------------
        headers = ["Item", "Código", "Descrição", "Alt", "Larg", "Prof", "Und", "Qt", "Preço Unit", "Preço Total"]
        start_row = 9
        for col, h in enumerate(headers):
            ws.write(start_row, col, h, fmt_header)

        col_widths = [6, 12, 44, 8, 8, 8, 6, 6, 14, 16]
        for idx, w in enumerate(col_widths):
            ws.set_column(idx, idx, w)

        # ----------------------------
        # ESCREVER ITENS
        # - Antes de escrever a linha definimos um formato de linha com borda (fmt_row_border)
        # - Construímos o write_rich_string para a descrição (título + bullets)
        # - Ajustamos a altura da linha com base no nº de linhas exibidas
        # ----------------------------
        row = start_row + 1
        for item in rows:
            # parse da descrição para linhas (usa _parse_description do mesmo ficheiro)
            entries = self._parse_description(item.descricao)
            # construir "linetexts" para saber quantas linhas vamos mostrar
            text_lines = []
            if entries:
                # primeira linha (header)
                text_lines.append(entries[0][1].upper())
                for kind, text in entries[1:]:
                    if kind == 'dash':
                        text_lines.append(f"- {text}")
                    elif kind == 'star':
                        text_lines.append(f"* {text}")
                    elif kind == 'header2':
                        text_lines.append(text.upper())
                    else:
                        text_lines.append(text)
            else:
                text_lines = [""]

            # calcular altura (cada linha ~14 pontos); base 20 para 1 linha
            num_lines = max(1, len(text_lines))
            line_height = max(20, 14 * num_lines)

            # definir apenas a altura da linha (sem aplicar formato a toda a linha)
            # assim evitamos que células vazias à direita apareçam com borda
            ws.set_row(row, line_height)

            # escrever Item e Código (formato com borda)
            ws.write(row, 0, item.item, fmt_cell)
            ws.write(row, 1, item.codigo, fmt_cell)

            # Descrição -> preparar argumentos para write_rich_string
            if not entries:
                ws.write(row, 2, "", fmt_descr_container)
            else:
                # Se apenas existe o header, evita warning do xlsxwriter
                if len(entries) == 1:
                    ws.write(row, 2, entries[0][1].upper(), fmt_descr_titulo)
                else:
                    rich_args = []
                    # 1ª entrada - título em uppercase + negrito
                    rich_args.append(fmt_descr_titulo)
                    rich_args.append(entries[0][1].upper())

                    # restantes entradas - cada uma em nova linha com formatação
                    for kind, text in entries[1:]:
                        rich_args.append('\n')
                        if kind == 'dash':
                            rich_args.append(fmt_descr_sub)
                            rich_args.append(f"- {text}")
                        elif kind == 'star':
                            rich_args.append(fmt_descr_sub)
                            rich_args.append(f"* {text}")
                        elif kind == 'header2':
                            rich_args.append(fmt_descr_titulo)
                            rich_args.append(str(text).upper())
                        else:
                            rich_args.append(fmt_descr_sub)
                            rich_args.append(text)

                    # escreve usando write_rich_string e garante container format (borda + wrap)
                    try:
                        ws.write_rich_string(row, 2, *rich_args, fmt_descr_container)
                    except Exception:
                        joined = "\n".join(
                            [entries[0][1].upper()]
                            + [("- " + t) if k == 'dash' else ("* " + t) if k == 'star' else t for k, t in entries[1:]]
                        )
                        ws.write(row, 2, joined, fmt_descr_container)

            # Alt / Larg / Prof
            ws.write_number(row, 3, float(item.altura) if item.altura is not None else None, fmt_cell)
            ws.write_number(row, 4, float(item.largura) if item.largura is not None else None, fmt_cell)
            ws.write_number(row, 5, float(item.profundidade) if item.profundidade is not None else None, fmt_cell)

            # Unidade
            ws.write(row, 6, item.unidade, fmt_cell)

            # Qt / Preço Unit / Preço Total (com borda)
            ws.write_number(row, 7, float(item.qt) if item.qt is not None else 0.0, fmt_number)
            ws.write_number(row, 8, float(item.preco_unitario) if item.preco_unitario is not None else 0.0, fmt_money)
            ws.write_number(row, 9, float(item.preco_total) if item.preco_total is not None else 0.0, fmt_money_bold)

            row += 1

        # ----------------------------
        # TOTAIS (coluna I=8 labels, J=9 valores) - SEM bordas
        # ----------------------------
        totals_row = row + 1
        total_qt = sum((item.qt or Decimal("0")) for item in rows)
        subtotal = sum((item.preco_total or Decimal("0")) for item in rows)
        iva = subtotal * IVA_RATE
        total = subtotal + iva

        ws.write(totals_row, 8, "Total Qt:", fmt_total_label_nb)
        ws.write_number(totals_row, 9, float(total_qt), fmt_total_val_nb)

        ws.write(totals_row + 1, 8, "SubTotal:", fmt_total_label_nb)
        ws.write_number(totals_row + 1, 9, float(subtotal), fmt_total_val_nb)

        ws.write(totals_row + 2, 8, "IVA (23%):", fmt_total_label_nb)
        ws.write_number(totals_row + 2, 9, float(iva), fmt_total_val_nb)

        ws.write(totals_row + 3, 8, "Total Geral:", fmt_total_label_nb)
        ws.write_number(totals_row + 3, 9, float(total), fmt_money_nb)

        # fechar workbook
        wb.close()

    def _export_resumo_custos(self, export_dir: Path, orc: Orcamento, client: Optional[Client]) -> None:
        """
        Gera 'Resumo_Custos_<num>_<ver>.xlsx' a partir do modelo MODELO_Resumo_Custos.xlsx
        (na pasta Base Dados Orçamento) preenchendo o separador 'Resumo Geral' com os
        registos da tabela custeio_items para este orçamento/versão.
        """

        col_order = [
            "id",
            "descricao_livre",
            "def_peca",
            "descricao",
            "qt_total",
            "comp_res",
            "larg_res",
            "esp_res",
            "mps",
            "mo",
            "orla",
            "blk",
            "nst",
            "mat_default",
            "acabamento_sup",
            "acabamento_inf",
            "ref_le",
            "descricao_no_orcamento",
            "pliq",
            "und",
            "desp",
            "orl_0_4",
            "orl_1_0",
            "tipo",
            "familia",
            "comp_mp",
            "larg_mp",
            "esp_mp",
            "orl_c1",
            "orl_c2",
            "orl_l1",
            "orl_l2",
            "ml_orl_c1",
            "ml_orl_c2",
            "ml_orl_l1",
            "ml_orl_l2",
            "custo_orl_c1",
            "custo_orl_c2",
            "custo_orl_l1",
            "custo_orl_l2",
            "gravar_modulo",
            "custo_total_orla",
            "soma_total_ml_orla",
            "area_m2_und",
            "perimetro_und",
            "spp_ml_und",
            "cp01_sec",
            "cp01_sec_und",
            "cp02_orl",
            "cp02_orl_und",
            "cp03_cnc",
            "cp03_cnc_und",
            "cp04_abd",
            "cp04_abd_und",
            "cp05_prensa",
            "cp05_prensa_und",
            "cp06_esquad",
            "cp06_esquad_und",
            "cp07_embalagem",
            "cp07_embalagem_und",
            "cp08_mao_de_obra",
            "cp08_mao_de_obra_und",
            "cp09_colagem",
            "cp09_colagem_und",
            "custo_mp_und",
            "custo_mp_total",
            "soma_custo_orla_total",
            "soma_custo_und",
            "soma_custo_total",
            "soma_custo_acb",
        ]

        base_dados_path = Path(self._get_setting_value(KEY_ORC_DB_BASE, DEFAULT_BASE_DADOS_ORC))
        template_candidates = [
            base_dados_path / "MODELO_Resumo_Custos.xlsx",
            base_dados_path / "MODELO_Resumo_Custos_V2.xlsx",
        ]
        template_path = next((p for p in template_candidates if p.exists()), None)
        if not template_path:
            QtWidgets.QMessageBox.warning(
                self,
                "Resumo Custos",
                "Modelo não encontrado (procure MODELO_Resumo_Custos.xlsx).",
            )
            return

        nome_base = f"Resumo_Custos_{orc.num_orcamento or 'orcamento'}_{self._format_versao(orc.versao)}.xlsx"
        destino = export_dir / nome_base
        try:
            shutil.copyfile(template_path, destino)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Resumo Custos", f"Falha ao copiar modelo: {exc}")
            return

        try:
            wb = load_workbook(destino)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Resumo Custos", f"Não foi possível abrir o modelo: {exc}")
            return

        ws = wb["Resumo Geral"] if "Resumo Geral" in wb.sheetnames else wb.active
        if ws.max_row > 1:
            ws.delete_rows(2, ws.max_row)
        # garantimos cabeçalho com a ordem correta
        for col_idx, name in enumerate(col_order, start=1):
            ws.cell(row=1, column=col_idx, value=name)
        # remove colunas excedentes do modelo antigo
        if ws.max_column > len(col_order):
            ws.delete_cols(len(col_order) + 1, ws.max_column - len(col_order))

        try:
            with SessionLocal() as session:
                cust_rows = (
                    session.query(CusteioItem)
                    .filter(CusteioItem.orcamento_id == orc.id, CusteioItem.versao == orc.versao)
                    .order_by(CusteioItem.ordem)
                    .all()
                )
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Resumo Custos", f"Falha ao carregar custeio: {exc}")
            return

        def _val(obj, attr):
            v = getattr(obj, attr, None)
            if isinstance(v, Decimal):
                try:
                    return float(v)
                except Exception:
                    return None
            if isinstance(v, bool):
                return 1 if v else 0
            return v

        row_idx = 2
        for c_item in cust_rows:
            for col_idx, attr in enumerate(col_order, start=1):
                ws.cell(row=row_idx, column=col_idx, value=_val(c_item, attr))
            row_idx += 1

        def _orla_width_from_esp(esp_val: float) -> float:
            """Devolve a largura de orla (mm) segundo a espessura da peça."""
            try:
                esp = float(esp_val)
            except Exception:
                return 0.0
            if esp <= 0:
                return 0.0
            if esp < 20:
                return 23.0
            if esp < 31:
                return 35.0
            if esp < 40:
                return 45.0
            return 60.0

        def _espessura_orla(ci) -> str:
            """Determina espessura da orla a partir das colunas orl_*."""
            for attr in ("orl_c1", "orl_c2", "orl_l1", "orl_l2"):
                try:
                    val = float(getattr(ci, attr, 0) or 0)
                except Exception:
                    val = 0
                if val <= 0:
                    continue
                if val == 1:
                    return "0.4mm"
                if val == 2:
                    return "1.0mm"
                return f"{val:.1f}mm"
            if getattr(ci, "orl_0_4", None):
                return "0.4mm"
            if getattr(ci, "orl_1_0", None):
                return "1.0mm"
            return ""

        def _ref_orla(ci) -> str:
            return (
                getattr(ci, "orl_0_4", None)
                or getattr(ci, "orl_1_0", None)
                or getattr(ci, "corres_orla_0_4", None)
                or getattr(ci, "corres_orla_1_0", None)
                or ""
            )

        def write_table(sheet_name: str, headers: list, rows: list) -> None:
            # cria/limpa folha e grava
            if sheet_name in wb.sheetnames:
                ws_out = wb[sheet_name]
                ws_out.delete_rows(1, ws_out.max_row)
            else:
                ws_out = wb.create_sheet(sheet_name)
            if not rows:
                for col, h in enumerate(headers, start=1):
                    ws_out.cell(row=1, column=col, value=h)
                return
            ws_out.append(headers)
            for r in rows:
                ws_out.append(r)

        # ------------------- Resumo Placas -------------------
        placas_header = [
            "ref_le", "descricao_no_orcamento", "pliq", "und", "desp",
            "comp_mp", "larg_mp", "esp_mp", "qt_placas_utilizadas",
            "area_placa", "m2_consumidos", "m2_total_pecas",
            "custo_mp_total", "custo_placas_utilizadas", "nao_stock",
        ]
        placas_map: dict[tuple, dict] = {}
        for c_item in cust_rows:
            und = (c_item.und or "").upper()
            if und != "M2":
                continue
            comp_mp = float(c_item.comp_mp or 0)
            larg_mp = float(c_item.larg_mp or 0)
            desp = float(c_item.desp or 0)
            qt_total = float(c_item.qt_total or 0)
            pliq = float(c_item.pliq or 0)
            area_placa = (comp_mp / 1000.0) * (larg_mp / 1000.0) if comp_mp and larg_mp else 0
            m2_total_pecas = float(c_item.area_m2_und or 0) * qt_total
            m2_consumidos = m2_total_pecas * (1 + desp)
            ratio = area_placa and m2_consumidos / area_placa or 0
            qt_placas = int(ratio) if ratio.is_integer() else int(ratio) + 1
            custo_placas_utilizadas = qt_placas * area_placa * pliq

            key = (c_item.ref_le, c_item.descricao_no_orcamento)
            if key not in placas_map:
                placas_map[key] = {
                    "ref_le": c_item.ref_le,
                    "descricao_no_orcamento": c_item.descricao_no_orcamento,
                    "pliq": pliq,
                    "und": und,
                    "desp": desp,
                    "comp_mp": comp_mp,
                    "larg_mp": larg_mp,
                    "esp_mp": float(c_item.esp_mp or 0),
                    "qt_placas_utilizadas": 0.0,
                    "area_placa": area_placa,
                    "m2_consumidos": 0.0,
                    "m2_total_pecas": 0.0,
                    "custo_mp_total": 0.0,
                    "custo_placas_utilizadas": 0.0,
                    "nao_stock": "",
                }
            placas_map[key]["qt_placas_utilizadas"] += qt_placas
            placas_map[key]["m2_consumidos"] += m2_consumidos
            placas_map[key]["m2_total_pecas"] += m2_total_pecas
            placas_map[key]["custo_mp_total"] += float(c_item.custo_mp_total or 0)
            placas_map[key]["custo_placas_utilizadas"] += custo_placas_utilizadas

        placas_rows = [
            [
                v["ref_le"],
                v["descricao_no_orcamento"],
                v["pliq"],
                v["und"],
                v["desp"],
                v["comp_mp"],
                v["larg_mp"],
                v["esp_mp"],
                int(v["qt_placas_utilizadas"]),
                round(v["area_placa"], 3),
                round(v["m2_consumidos"], 3),
                round(v["m2_total_pecas"], 3),
                round(v["custo_mp_total"], 2),
                round(v["custo_placas_utilizadas"], 2),
                v["nao_stock"],
            ]
            for v in placas_map.values()
        ]
        write_table("Resumo Placas", placas_header, placas_rows)

        # ------------------- Resumo Orlas -------------------
        orlas_header = ["ref_orla", "descricao_material", "espessura_orla", "largura_orla", "ml_total", "custo_total"]
        orlas_map: dict[tuple, dict] = {}
        for c_item in cust_rows:
            qt_total = float(c_item.qt_total or 0)
            largura_orla = _orla_width_from_esp(getattr(c_item, "esp_res", None) or getattr(c_item, "esp_mp", None))

            ref_map = {
                1: getattr(c_item, "orl_0_4", None) or getattr(c_item, "corres_orla_0_4", None) or "",
                2: getattr(c_item, "orl_1_0", None) or getattr(c_item, "corres_orla_1_0", None) or "",
            }
            sides = [
                (getattr(c_item, "orl_c1", 0), getattr(c_item, "ml_orl_c1", 0), getattr(c_item, "custo_orl_c1", 0)),
                (getattr(c_item, "orl_c2", 0), getattr(c_item, "ml_orl_c2", 0), getattr(c_item, "custo_orl_c2", 0)),
                (getattr(c_item, "orl_l1", 0), getattr(c_item, "ml_orl_l1", 0), getattr(c_item, "custo_orl_l1", 0)),
                (getattr(c_item, "orl_l2", 0), getattr(c_item, "ml_orl_l2", 0), getattr(c_item, "custo_orl_l2", 0)),
            ]

            for code_raw, ml_raw, custo_raw in sides:
                try:
                    code_val = float(code_raw or 0)
                except Exception:
                    code_val = 0.0
                if code_val <= 0:
                    continue  # sem orla neste lado

                # código 0.4 -> orla fina; código 1 -> orla grossa (1mm)
                if code_val >= 0.9:
                    code = 2  # grossa 1.0mm
                    esp_descr = "1.0mm"
                else:
                    code = 1  # fina 0.4mm
                    esp_descr = "0.4mm"

                ref_orl = ref_map.get(code) or ""
                if not ref_orl:
                    continue

                ml_val = float(ml_raw or 0) * qt_total
                custo_val = float(custo_raw or 0) * qt_total
                if ml_val == 0 and custo_val == 0:
                    continue

                key = (ref_orl, c_item.descricao_no_orcamento, esp_descr)
                if key not in orlas_map:
                    orlas_map[key] = {
                        "ref_orla": ref_orl,
                        "descricao_material": c_item.descricao_no_orcamento,
                        "espessura_orla": esp_descr,
                        "largura_orla": largura_orla,
                        "ml_total": 0.0,
                        "custo_total": 0.0,
                    }
                orlas_map[key]["ml_total"] += ml_val
                orlas_map[key]["custo_total"] += custo_val

        orlas_rows = [
            [
                v["ref_orla"],
                v["descricao_material"],
                v["espessura_orla"],
                v["largura_orla"],
                round(v["ml_total"], 2),
                round(v["custo_total"], 2),
            ]
            for v in orlas_map.values()
        ]
        write_table("Resumo Orlas", orlas_header, orlas_rows)

        # ------------------- Resumo Ferragens -------------------
        ferr_header = ["ref_le", "descricao_no_orcamento", "pliq", "und", "desp", "comp_mp", "larg_mp", "esp_mp", "qt_total", "spp_ml_total", "custo_mp_und", "custo_mp_total"]
        ferr_map: dict[tuple, dict] = {}
        for c_item in cust_rows:
            ref = (c_item.ref_le or "").upper()
            if not ref.startswith("FER"):
                continue
            key = (c_item.ref_le, c_item.descricao_no_orcamento)
            qt_total = float(c_item.qt_total or 0)
            spp_ml_total = float(c_item.spp_ml_und or 0) * qt_total
            if key not in ferr_map:
                ferr_map[key] = {
                    "ref_le": c_item.ref_le,
                    "descricao_no_orcamento": c_item.descricao_no_orcamento,
                    "pliq": float(c_item.pliq or 0),
                    "und": c_item.und,
                    "desp": float(c_item.desp or 0),
                    "comp_mp": float(c_item.comp_mp or 0),
                    "larg_mp": float(c_item.larg_mp or 0),
                    "esp_mp": float(c_item.esp_mp or 0),
                    "qt_total": 0.0,
                    "spp_ml_total": 0.0,
                    "custo_mp_und": float(c_item.custo_mp_und or 0),
                    "custo_mp_total": 0.0,
                }
            ferr_map[key]["qt_total"] += qt_total
            ferr_map[key]["spp_ml_total"] += spp_ml_total
            ferr_map[key]["custo_mp_total"] += float(c_item.custo_mp_total or 0)

        ferr_rows = [
            [
                v["ref_le"],
                v["descricao_no_orcamento"],
                v["pliq"],
                v["und"],
                v["desp"],
                v["comp_mp"],
                v["larg_mp"],
                v["esp_mp"],
                round(v["qt_total"], 2),
                round(v["spp_ml_total"], 2),
                v["custo_mp_und"],
                round(v["custo_mp_total"], 2),
            ]
            for v in ferr_map.values()
        ]
        write_table("Resumo Ferragens", ferr_header, ferr_rows)

        # ------------------- Resumo Maquinas_MO -------------------
        maq_rows = []
        maq_header = ["Operação", "Custo Total (€)", "ML Corte", "ML Orlado", "Nº Peças"]
        # custos por tipo
        def get_cost(filter_attr):
            return sum(float(getattr(ci, f"{filter_attr}_und") or 0) * float(ci.qt_total or 0) for ci in cust_rows if getattr(ci, filter_attr) and float(getattr(ci, filter_attr) or 0) > 0)
        def get_ml_corte():
            total = 0.0
            for ci in cust_rows:
                if float(ci.cp01_sec or 0) <= 0:
                    continue
                total += ((float(ci.comp_res or 0) * 2 + float(ci.larg_res or 0) * 2) * float(ci.qt_total or 0)) / 1000.0
            return round(total, 2)
        def get_ml_orla():
            total = 0.0
            for ci in cust_rows:
                if float(ci.cp02_orl or 0) <= 0:
                    continue
                total += sum(float(x or 0) for x in [getattr(ci, "ml_orl_c1", 0), getattr(ci, "ml_orl_c2", 0), getattr(ci, "ml_orl_l1", 0), getattr(ci, "ml_orl_l2", 0)]) * float(ci.qt_total or 0)
            return round(total, 2)
        maq_rows.append(["Seccionadora (Corte)", round(get_cost("cp01_sec"), 2), get_ml_corte(), "", int(sum(float(ci.qt_total or 0) for ci in cust_rows if float(ci.cp01_sec or 0) > 0))])
        maq_rows.append(["Orladora (Orlagem)", round(get_cost("cp02_orl"), 2), "", get_ml_orla(), int(sum(float(ci.qt_total or 0) for ci in cust_rows if float(ci.cp02_orl or 0) > 0))])
        maq_rows.append(["CNC (Mecanizações)", round(get_cost("cp03_cnc"), 2), "", "", int(sum(float(ci.qt_total or 0) for ci in cust_rows if float(ci.cp03_cnc or 0) > 0))])
        maq_rows.append(["ABD (Mecanizações)", round(get_cost("cp04_abd"), 2), "", "", int(sum(float(ci.qt_total or 0) for ci in cust_rows if float(ci.cp04_abd or 0) > 0))])
        maq_rows.append(["Prensa (Montagem)", round(get_cost("cp05_prensa"), 2), "", "", ""])
        maq_rows.append(["Esquadrejadora (Cortes Manuais)", round(get_cost("cp06_esquad"), 2), "", "", ""])
        maq_rows.append(["Embalamento (Paletização)", round(get_cost("cp07_embalagem"), 2), "", "", ""])
        maq_rows.append(["Mão de Obra (MO geral)", round(get_cost("cp08_mao_de_obra"), 2), "", "", ""])
        write_table("Resumo Maquinas_MO", maq_header, maq_rows)

        try:
            wb.save(destino)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Resumo Custos", f"Falha ao gravar resumo: {exc}")


    def _apply_description_to_cell(self, cell, text: Optional[str]) -> None:
        """
        Aplica a descrição na célula de Excel usando RichText:
        - 1ª linha (header/header2) em MAIÚSCULAS e a negrito
        - linhas que começam por '-' ou '*' em nova linha (ALT+ENTER)
        com um ligeiro "TAB" (4 espaços antes do símbolo) e em itálico
        """
        entries = self._parse_description(text)
        if not entries:
            cell.value = ""
            return

        rich = CellRichText()
        for idx, (kind, content) in enumerate(entries):
            # ALT+ENTER entre cada bloco (mantém tudo na mesma célula)
            if idx > 0:
                rich.append(TextBlock(text="\n", font=InlineFont()))

            if kind in ("header", "header2"):
                # título em maiúsculas + negrito
                rich.append(TextBlock(text=content.upper(), font=InlineFont(b=True)))
            elif kind == "dash":
                # 4 espaços para simular TAB antes do '-'; texto em itálico
                rich.append(TextBlock(text=f"    - {content}", font=InlineFont(i=True)))
            elif kind == "star":
                # 4 espaços p/ simular TAB antes do '*'; texto em itálico
                rich.append(TextBlock(text=f"    * {content}", font=InlineFont(i=True)))
            else:
                rich.append(TextBlock(text=content, font=InlineFont()))

        cell.value = rich
        cell.alignment = Alignment(vertical="top", horizontal="left", wrap_text=True)

    def _build_pdf(self, output_path: Path) -> None:
        """
        Gera o PDF do orçamento com layout ajustado:
        - margens em mm coerentes com as colWidths
        - colunas redesenhadas (descrição maior)
        - fontes e paddings ajustados para caber melhor na tabela
        - totais alinhados mais à direita
        """
        client = self._current_client
        orc = self._current_orcamento
        rows = self._current_items
        if not orc:
            raise ValueError("Nenhum orçamento disponível.")

        # --------------------------
        # Parâmetros de layout (fáceis de ajustar)
        # --------------------------
        left_margin = 5 * mm        # margem esquerda (mm -> pontos)
        right_margin = 5 * mm       # margem direita
        top_margin = 1 * mm
        bottom_margin = 1 * mm # margem inferior pequena para rodapé mais baixo

        # Tamanhos de fontes e leading
        HEADER_FONT_SIZE = 16
        HEADER_TABLE_FONTSIZE = 9   # <--- reduzido (cabeçalho da tabela)
        BODY_FONTSIZE = 9
        DESC_LEADING = 11

        # col_widths em mm que somam a largura útil da página:
        # A4 = 210 mm, largura útil = 210 - left - right
        # 210 - 5 - 5 = 200 mm
        # ajuste: descrição maior (80 mm) para caber melhor
        col_widths_mm = [9, 20, 80, 10, 11, 11, 11, 11, 18, 19]  # soma = 200 mm
        # converter para pontos (reportlab usa pontos internamente)
        col_widths = [w * mm for w in col_widths_mm]

        # --------------------------
        # Styles
        # --------------------------
        styles = getSampleStyleSheet()
        # info_style mais compacto para poupar espaço vertical
        info_style = ParagraphStyle("info", parent=styles["Normal"], fontSize=9, leading=11, spaceAfter=2)
        header_style = ParagraphStyle("header", parent=styles["Heading1"], alignment=2, fontSize=HEADER_FONT_SIZE, textColor=colors.HexColor("#133a63"))
        desc_style = ParagraphStyle("desc", parent=styles["Normal"], fontSize=BODY_FONTSIZE, leading=DESC_LEADING, spaceAfter=2)
        price_style = ParagraphStyle("price", parent=styles["Normal"], alignment=2, fontSize=BODY_FONTSIZE, leading=DESC_LEADING)

        # -------------------------------------------------------------------------------------
        # Criar o doc (precisamos do doc para obter doc.width/doc.height antes de construir story)
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            topMargin=top_margin,
            bottomMargin=bottom_margin,
            leftMargin=left_margin,
            rightMargin=right_margin,
        )

        # ------------------------------------------------------------------
        # Header: left_table (cliente) e right_table (titulo + nº/data)
        # ------------------------------------------------------------------
        left_elements: List = []
        logo_path = self._resolve_logo_path()
        if logo_path:
            try:
                img = Image(str(logo_path))
                img.drawHeight = 10 * mm
                img.drawWidth = 32 * mm
                left_elements.append([img])
            except Exception:
                pass

        client_name = getattr(client, "nome", "") or ""
        contact_lines = [
            getattr(client, "morada", "") or "",
            getattr(client, "email", "") or "",
            f"Telefone: {getattr(client, 'telefone', '') or ''} | Telemóvel: {getattr(client, 'telemovel', '') or ''} | N.º cliente PHC: {getattr(client, 'num_cliente_phc', '') or ''}",
        ]
        left_elements.append([Paragraph(f"<font size=12><b>{client_name}</b></font>", info_style)])
        left_elements.append([Paragraph("<br/>".join(filter(None, contact_lines)), info_style)])
        left_table = Table(left_elements, colWidths=[80 * mm])
        left_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), -8 * mm),
        ]))

        right_title = Paragraph("<font color='#103864' size=16><b>Relatório de Orçamento</b></font>", header_style)
        right_info = Paragraph(
            f"<font size=12>Nº Orçamento: <b>{orc.num_orcamento or ''}_{self._format_versao(orc.versao)}</b></font><br/>"
            f"<font color='#5f6368'>Data: {orc.data or ''}</font>",
            info_style,
        )
        right_table = Table([[right_title], [Spacer(1, 3 * mm)], [right_info]], colWidths=[80 * mm])
        right_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ]))

        header_table = Table([[left_table, right_table]], colWidths=[100 * mm, 80 * mm])
        header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))

        # ref / obra
        ref_para = Paragraph(f"<font color='#0a4ea1' size=12><b>Ref.: {orc.ref_cliente or '-'} </b></font>", info_style)
        obra_para = Paragraph(f"<font color='#d4111f' size=12><b>Obra: {orc.obra or '-'}</b></font>", ParagraphStyle("obra", parent=info_style, alignment=2))
        ref_table = Table([[ref_para, obra_para]], colWidths=[98 * mm, 76 * mm])
        ref_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (0, -1), -10 * mm),
            ("LEFTPADDING", (1, 0), (1, 0), -30),
            ("ALIGN", (1, 0), (1, 0), "LEFT"),
        ]))

        # ------------------------------------------------------------------
        # Construir a tabela de items (mas ainda NÃO a adicionamos ao story)
        # ------------------------------------------------------------------
        headers = ["Item", "Código", "Descrição", "Alt", "Larg", "Prof", "Und", "Qt", "Preço Unit", "Preço Total"]
        data = [headers]
        for item in rows:
            desc_para = Paragraph(self._format_description_pdf(item.descricao), desc_style)
            data.append([
                item.item, item.codigo, desc_para,
                _fmt_decimal(item.altura, 0), _fmt_decimal(item.largura, 0), _fmt_decimal(item.profundidade, 0),
                item.unidade, _fmt_decimal(item.qt, 2), _fmt_currency(item.preco_unitario),
                Paragraph(f"<b>{_fmt_currency(item.preco_total)}</b>", price_style),
            ])

        # paddings iniciais (vamos poder reduzir dinamicamente)
        pad_left = 3
        pad_right = 4
        pad_top = 2
        pad_bottom = 2

        def make_table_style(pl=pad_left, pr=pad_right, pt=pad_top, pb=pad_bottom):
            style = TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d7dce2")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), HEADER_TABLE_FONTSIZE),
                ("FONTSIZE", (0, 1), (-1, -1), BODY_FONTSIZE),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 1), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), pl),
                ("RIGHTPADDING", (0, 0), (-1, -1), pr),
                ("TOPPADDING", (0, 0), (-1, -1), pt),
                ("BOTTOMPADDING", (0, 0), (-1, -1), pb),
                ("ALIGN", (3, 1), (5, -1), "CENTER"),
                ("ALIGN", (7, 1), (8, -1), "RIGHT"),
                ("ALIGN", (9, 1), (9, -1), "RIGHT"),
            ])
            return style

        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(make_table_style())

        # ------------------------------------------------------------------
        # Resumo / totais (SubTotal: com colon conforme pediste)
        # ------------------------------------------------------------------
        total_qt = sum((item.qt or Decimal("0")) for item in rows)
        subtotal = sum((item.preco_total or Decimal("0")) for item in rows)
        iva = subtotal * IVA_RATE
        total = subtotal + iva

        # estilos para labels (right) e valores (right)
        label_right = ParagraphStyle("label_right", parent=styles["Normal"], alignment=2, fontSize=BODY_FONTSIZE, leading=DESC_LEADING)
        value_right = ParagraphStyle("value_right", parent=styles["Normal"], alignment=2, fontSize=BODY_FONTSIZE, leading=DESC_LEADING)

        # construir summary com Paragraphs — evita que HTML apareça em texto cru
        summary_col1 = 18 * mm
        summary_col2 = 30 * mm

        summary_table = Table(
            [
                [Paragraph("Total Qt.:", label_right), Paragraph(f"<b>{_fmt_decimal(total_qt, 2)}</b>", value_right)],
                [Paragraph("<font color='#0a2b6d'><b>SubTotal:</b></font>", label_right), Paragraph(f"<b>{_fmt_currency(subtotal)}</b>", value_right)],
                [Paragraph("IVA (23%):", label_right), Paragraph(f"{_fmt_currency(iva)}", value_right)],
                [Paragraph("Total Geral:", label_right), Paragraph(f"<b>{_fmt_currency(total)}</b>", value_right)],
            ],
            colWidths=[summary_col1, summary_col2],
        )

        # estilo para summary: alinhar tudo à direita, paddings reduzidos, box só no SUBTOTAL VALOR
        summary_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 1),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),  # garantir valores bem encostados à direita
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                    ("BOX", (1, 1), (1, 1), 1, colors.HexColor("#1d2f6f")),
                    ("BACKGROUND", (1, 1), (1, 1), colors.HexColor("#dfe5f2")),
                ]
            )
        )
        summary_table.hAlign = "RIGHT"

        # Posicionar o summary exactamente à direita (push_right controla o "encaixe")
        page_width, _ = A4
        usable_width = page_width - left_margin - right_margin
        summary_width = summary_col1 + summary_col2
        left_space = usable_width - summary_width
        push_right = 12 * mm   # podes ajustar (aumenta este valor para encostar mais)
        left_space = max(0, left_space - push_right)

        container = Table([[ "", summary_table ]], colWidths=[left_space, summary_width])
        container.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (0, 0), 0),
                    ("RIGHTPADDING", (0, 0), (0, 0), 0),
                    ("LEFTPADDING", (1, 0), (1, 0), 0),
                    ("RIGHTPADDING", (1, 0), (1, 0), 0),
                ]
            )
        )

        # -------------------------------------------------------------------------------------
        #   Checagem de alturas: se tudo couber numa página, adicionamos; se faltar pouco,
        #   reduzimos paddings da tabela para forçar a caber numa página (evita página em branco).
        # -------------------------------------------------------------------------------------
        # obter alturas com wrap
        page_w = doc.width
        page_h = doc.height

        # calcular alturas dos blocos
        h_header = header_table.wrap(page_w, page_h)[1]
        h_ref = ref_table.wrap(page_w, page_h)[1]
        # pequeno spacer antes da tabela (6 pts)
        spacer1 = 6
        # obter altura da tabela com paddings actuais
        table_h = table.wrap(page_w, page_h)[1]
        # summary height
        summary_h = container.wrap(page_w, page_h)[1]
        total_needed = h_header + h_ref + spacer1 + table_h + spacer1 + summary_h

        # Se excede a página por poucos pontos, vamos reduzir os paddings gradualmente
        max_iterations = 6
        iter_count = 0
        # versão mais agressiva para reduzir paddings e forçar caber numa página
        max_iterations = 12
        iter_count = 0
        # reduzir em 1–2 pontos por iteração até um limite
        while total_needed > page_h and iter_count < max_iterations:
            pad_left = max(0, pad_left - 2)
            pad_right = max(0, pad_right - 2)
            pad_top = max(0, pad_top - 1)
            pad_bottom = max(0, pad_bottom - 1)
            table.setStyle(make_table_style(pl=pad_left, pr=pad_right, pt=pad_top, pb=pad_bottom))
            table_h = table.wrap(page_w, page_h)[1]
            total_needed = h_header + h_ref + spacer1 + table_h + spacer1 + summary_h
            iter_count += 1

        # Se continuar a ser maior que a página, deixamos partir em 2 páginas (cenário com muitos itens)
        # Agora construímos o story definitivo.
        story: List = []
        story.append(header_table)
        story.append(ref_table)
        story.append(Spacer(1, 6))
        story.append(table)
        story.append(Spacer(1, 6))
        story.append(container)

        # -------------------------------------------------------------------------------------
        # Construir documento com NumberedFooterCanvas (mantém rodapé com página X/Y)
        # -------------------------------------------------------------------------------------
        footer_info = {"data": orc.data or "", "numero": f"{orc.num_orcamento or ''}_{self._format_versao(orc.versao)}"}
        doc.build(story, canvasmaker=lambda *args, **kwargs: NumberedFooterCanvas(*args, footer_info=footer_info, **kwargs))


    def _format_description_pdf(self, text: Optional[str]) -> str:
        entries = self._parse_description(text)
        if not entries:
            return ""
        parts: List[str] = []
        for kind, content in entries:
            safe = html.escape(content)
            if kind in ("header", "header2"):
                parts.append(f"<b>{safe.upper()}</b>")
            elif kind == "dash":
                parts.append(f"<i>- {safe}</i>")
            elif kind == "star":
                parts.append(f"<i><u><font color='#0a5c0a'>* {safe}</font></u></i>")
            else:
                parts.append(safe)
        return "<br/>".join(parts)

    @staticmethod
    def _format_versao(value: Optional[str]) -> str:
        if value in (None, ""):
            return "00"
        try:
            return f"{int(str(value)) :02d}"
        except Exception:
            return str(value)

    @staticmethod
    def _decimal_value(value: Optional[Decimal]) -> Optional[float]:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except Exception:
            return None
