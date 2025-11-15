from __future__ import annotations

import html
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Tuple

from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtCore import Qt
from openpyxl import Workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.styles import Alignment, Border, Font, Side, PatternFill
from openpyxl.drawing.image import Image as XLImage
from openpyxl.worksheet.page import PageMargins
from openpyxl.worksheet.properties import PageSetupProperties

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
from Martelo_Orcamentos_V2.app.models import Client, Orcamento, OrcamentoItem
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

        # segundo separador placeholder
        placeholder = QtWidgets.QWidget()
        placeholder_layout = QtWidgets.QVBoxLayout(placeholder)
        placeholder_layout.addStretch(1)
        placeholder_layout.addWidget(
            QtWidgets.QLabel(
                "Resumo de consumos estará disponível em breve.",
                alignment=Qt.AlignCenter,
            )
        )
        placeholder_layout.addStretch(1)
        self.tab_widget.addTab(placeholder, "Resumo de Consumos")

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

    def _parse_description(self, text: Optional[str]) -> List[Tuple[str, str]]:
        """
        Converte o texto da descrição em uma lista de (tipo, conteúdo),
        onde tipo pode ser:
        - 'header'  : primeira linha (título do módulo)
        - 'header2' : linhas seguintes totalmente em maiúsculas (sub-títulos)
        - 'dash'    : linhas que começam por '-' (bullets normais)
        - 'star'    : linhas que começam por '*' (bullets especiais)
        - 'plain'   : resto

        Também trata descrições que vêm NUMA ÚNICA LINHA com
        " - " e " * " (ex:
        "ROUPEIRO ... - 2 Portas Abrir - 1 bloco 4 gavetas * Puxador ...").
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
        # CASO 2: tudo numa só linha -> separar por " - " e " * "
        # -------------------------------------------------
        # divide mantendo o delimitador (" - " ou " * ")
        parts = re.split(r"( - |\* )", norm)

        # se não encontrou nenhum separador, trata tudo como um header simples
        if len(parts) == 1:
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
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Exportar PDF", f"Falha ao exportar: {exc}")
            return
        QtWidgets.QMessageBox.information(self, "Exportar PDF", f"Relatório guardado em:\n{output_path}")


    def _build_workbook(self, output_path: Path) -> None:
        """
        Gera o ficheiro Excel do relatório de orçamento com layout
        semelhante ao PDF:

        - Cabeçalho com logótipo (se existir), dados do cliente à esquerda
          e título + nº orçamento + data à direita.
        - Tabela de items com cabeçalho cinzento e bordas finas.
        - Coluna Descrição com quebras de linha internas (ALT+ENTER) e
          altura da linha ajustada ao número de linhas.
        - Totais encostados à direita com caixa no SubTotal.
        """
        client = self._current_client
        orc = self._current_orcamento
        rows = self._current_items
        if not orc:
            raise ValueError("Nenhum orçamento disponível para exportar.")

        wb = Workbook()
        ws = wb.active
        ws.title = "Relatório"
        ws.page_setup.paperSize = ws.PAPERSIZE_A4
        ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
        ws.page_margins = PageMargins(left=0.25, right=0.25, top=0.35, bottom=0.35)
        # ajustar altura da linha 2 para o logótipo ficar visível
        ws.row_dimensions[2].height = 35

        # ---------------------------------------------------------
        # 1) LOGÓTIPO + dados do cliente (lado esquerdo)
        # ---------------------------------------------------------
        logo_path = self._resolve_logo_path()
        if logo_path:
            try:
                img = XLImage(str(logo_path))
                # tamanho aproximado para ficar como no PDF
                img.height = 70  # em pontos (aprox. 2,5 cm)
                img.width = 180
                ws.add_image(img, "A1")
            except Exception:
                # se der erro no logo não bloqueia o resto
                pass

        cliente_nome = getattr(client, "nome", "") or ""
        ws["A3"] = cliente_nome
        ws["A3"].font = Font(size=12, bold=True)
        ws["A4"] = getattr(client, "morada", "") or ""
        ws["A5"] = getattr(client, "email", "") or ""
        ws["A6"] = f"Telefone: {(getattr(client, 'telefone', '') or '')} | Telemóvel: {(getattr(client, 'telemovel', '') or '')}"
        ws["A7"] = f"N.º cliente PHC: {(client.num_cliente_phc if client else '')}"

        # ---------------------------------------------------------
        # 2) Cabeçalho à direita: título + nº orçamento + data
        # ---------------------------------------------------------
        ws.merge_cells("H1:J1")
        right_title = ws["H1"]
        right_title.value = "Relatório de Orçamento"
        right_title.font = Font(size=16, bold=True, color="103864")
        right_title.alignment = Alignment(horizontal="right", vertical="center")

        ws.merge_cells("H2:J2")
        num_cell = ws["H2"]
        num_cell.value = f"Nº Orçamento: {orc.num_orcamento or ''}_{self._format_versao(orc.versao)}"
        num_cell.font = Font(size=12, bold=True)
        num_cell.alignment = Alignment(horizontal="right")

        ws.merge_cells("H3:J3")
        date_cell = ws["H3"]
        date_cell.value = f"Data: {orc.data or ''}"
        date_cell.font = Font(color="5f6368")
        date_cell.alignment = Alignment(horizontal="right")

        # ---------------------------------------------------------
        # 3) Ref. cliente + Obra (linha azul/vermelha)
        # ---------------------------------------------------------
        ws.merge_cells("A8:E8")
        ref_cell = ws["A8"]
        ref_cell.value = f"Ref.: {orc.ref_cliente or '-'}"
        ref_cell.font = Font(size=12, bold=True, color="0a4ea1")

        ws.merge_cells("H8:J8")
        obra_cell = ws["H8"]
        obra_cell.value = f"Obra: {orc.obra or '-'}"
        obra_cell.font = Font(size=12, bold=True, color="d4111f")
        obra_cell.alignment = Alignment(horizontal="right")

        # ---------------------------------------------------------
        # 4) Cabeçalho da tabela de items
        # ---------------------------------------------------------
        headers = [
            "Item",
            "Código",
            "Descrição",
            "Alt",
            "Larg",
            "Prof",
            "Und",
            "Qt",
            "Preço Unit",
            "Preço Total",
        ]
        start_row = 10
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=start_row, column=col, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.fill = PatternFill("solid", fgColor="dfe5f2")

        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        # ---------------------------------------------------------
        # 5) Linhas da tabela de items
        #    -> coluna Descrição com ALT+ENTER (RichText + \n)
        #    -> altura da linha ajustada ao nº de linhas de descrição
        # ---------------------------------------------------------
        for row_offset, item in enumerate(rows, start=1):
            current_row = start_row + row_offset

            # Item e código
            c1 = ws.cell(row=current_row, column=1, value=item.item)
            c1.border = thin_border
            c1.alignment = Alignment(horizontal="center", vertical="center")

            c2 = ws.cell(row=current_row, column=2, value=item.codigo)
            c2.border = thin_border
            c2.alignment = Alignment(horizontal="center", vertical="center")

            # Descrição (RichText + quebras de linha internas)
            desc_cell = ws.cell(row=current_row, column=3)
            self._apply_description_to_cell(desc_cell, item.descricao)
            desc_cell.border = thin_border

            # Alt, Larg, Prof
            dims = [
                self._decimal_value(item.altura),
                self._decimal_value(item.largura),
                self._decimal_value(item.profundidade),
            ]
            for offset, value in enumerate(dims, start=4):
                c = ws.cell(row=current_row, column=offset, value=value)
                c.number_format = "0.0"
                c.border = thin_border
                c.alignment = Alignment(horizontal="center", vertical="center")

            # Unidade
            c_und = ws.cell(row=current_row, column=7, value=item.unidade)
            c_und.border = thin_border
            c_und.alignment = Alignment(horizontal="center", vertical="center")

            # Qt, preço unitário, preço total
            qt_val = self._decimal_value(item.qt)
            qt_cell = ws.cell(row=current_row, column=8, value=qt_val)
            qt_cell.number_format = "0.00"
            qt_cell.border = thin_border
            qt_cell.alignment = Alignment(horizontal="right", vertical="center")

            preco_unit_cell = ws.cell(row=current_row, column=9, value=self._decimal_value(item.preco_unitario))
            preco_unit_cell.number_format = "€ #,##0.00"
            preco_unit_cell.border = thin_border
            preco_unit_cell.alignment = Alignment(horizontal="right", vertical="center")

            preco_total_cell = ws.cell(row=current_row, column=10, value=self._decimal_value(item.preco_total))
            preco_total_cell.number_format = "€ #,##0.00"
            preco_total_cell.font = Font(bold=True)
            preco_total_cell.border = thin_border
            preco_total_cell.alignment = Alignment(horizontal="right", vertical="center")

            # ---- Altura dinâmica da linha em função do nº de linhas na descrição
            # reutilizamos o mesmo parser usado no PDF / preview
            num_lines = max(1, len(self._parse_description(item.descricao)))
            # base ~ 18 + 10 por cada linha adicional (ajusta se necessário)
            ws.row_dimensions[current_row].height = 18 + (num_lines - 1) * 10

        # ---------------------------------------------------------
        # 6) Totais à direita (SubTotal com caixa)
        # ---------------------------------------------------------
        totals_row = start_row + len(rows) + 2
        total_qt = sum((item.qt or Decimal("0")) for item in rows)
        subtotal = sum((item.preco_total or Decimal("0")) for item in rows)
        iva = subtotal * IVA_RATE
        total = subtotal + iva

        summary_col = 8  # começa em coluna H

        # linha Total Qt
        ws.merge_cells(start_row=totals_row, start_column=summary_col, end_row=totals_row, end_column=summary_col + 1)
        ws["H" + str(totals_row)].value = "Total Qt:"
        ws["H" + str(totals_row)].font = Font(bold=True)
        qt_cell = ws.cell(row=totals_row, column=summary_col + 2, value=float(total_qt))
        qt_cell.number_format = "0.00"
        qt_cell.font = Font(bold=True)
        qt_cell.alignment = Alignment(horizontal="right")

        # SubTotal com caixa
        subtotal_fill = PatternFill("solid", fgColor="dfe5f2")
        subtotal_border = Border(
            left=Side(style="medium", color="1d2f6f"),
            right=Side(style="medium", color="1d2f6f"),
            top=Side(style="medium", color="1d2f6f"),
            bottom=Side(style="medium", color="1d2f6f"),
        )
        for col in range(summary_col, summary_col + 3):
            cell = ws.cell(row=totals_row + 1, column=col)
            cell.fill = subtotal_fill
            cell.border = subtotal_border

        subtotal_label = ws.cell(row=totals_row + 1, column=summary_col, value="SubTotal:")
        subtotal_label.font = Font(bold=True, size=12, color="0a2b6d")
        subtotal_label.alignment = Alignment(horizontal="right")

        subtotal_value = ws.cell(row=totals_row + 1, column=summary_col + 2, value=float(subtotal))
        subtotal_value.number_format = "€ #,##0.00"
        subtotal_value.font = Font(bold=True, size=12, color="0a2b6d")
        subtotal_value.alignment = Alignment(horizontal="right")

        # IVA
        iva_label = ws.cell(row=totals_row + 2, column=summary_col, value="IVA (23%):")
        iva_label.font = Font(bold=True)
        iva_label.alignment = Alignment(horizontal="right")
        iva_cell = ws.cell(row=totals_row + 2, column=summary_col + 2, value=float(iva))
        iva_cell.number_format = "€ #,##0.00"
        iva_cell.alignment = Alignment(horizontal="right")

        # Total Geral
        total_label = ws.cell(row=totals_row + 3, column=summary_col, value="Total Geral:")
        total_label.font = Font(bold=True)
        total_label.alignment = Alignment(horizontal="right")
        total_cell = ws.cell(row=totals_row + 3, column=summary_col + 2, value=float(total))
        total_cell.number_format = "€ #,##0.00"
        total_cell.font = Font(bold=True, size=12)
        total_cell.alignment = Alignment(horizontal="right")

        # ---------------------------------------------------------
        # 7) Largura das colunas (proporções semelhantes ao PDF)
        # ---------------------------------------------------------
        widths = [6, 12, 45, 8, 8, 8, 6, 6, 14, 16]
        for idx, width in enumerate(widths, start=1):
            col_letter = chr(64 + idx)  # 1->A, 2->B, ...
            ws.column_dimensions[col_letter].width = width

        # ---------------------------------------------------------
        # 8) Configuração de impressão:
        #    - margens reduzidas
        #    - ajustar todas as colunas à largura de 1 página A4
        # ---------------------------------------------------------
        ws.page_margins = PageMargins(
            left=0.3,   # polegadas (~0,76 cm)
            right=0.3,
            top=0.5,
            bottom=0.5,
            header=0.0,
            footer=0.0,
        )
        # caber em 1 página na horizontal; altura livre (pode usar várias páginas)
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0

        wb.save(output_path)


    def _apply_description_to_cell(self, cell, text: Optional[str]) -> None:
        """
        Aplica a descrição na célula de Excel usando RichText:
        - 1ª linha (header/header2) em MAIÚSCULAS e a negrito
        - linhas que começam por '-' ou '*' em nova linha (ALT+ENTER)
          com um ligeiro "TAB" (4 espaços antes do símbolo)
        """
        entries = self._parse_description(text)
        if not entries:
            cell.value = ""
            return

        rich = CellRichText()
        for idx, (kind, content) in enumerate(entries):
            # ALT+ENTER entre cada bloco
            if idx > 0:
                rich.append(TextBlock(text="\n", font=InlineFont()))

            if kind in ("header", "header2"):
                # título em maiúsculas + negrito
                rich.append(TextBlock(text=content.upper(), font=InlineFont(b=True)))
            elif kind == "dash":
                # 4 espaços para simular TAB antes do '-'
                rich.append(TextBlock(text=f"    - {content}", font=InlineFont(i=True)))
            elif kind == "star":
                # 4 espaços para simular TAB antes do '*'
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
