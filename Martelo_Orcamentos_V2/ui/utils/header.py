from __future__ import annotations

from html import escape
from typing import Optional

from PySide6 import QtCore, QtWidgets, QtGui


def init_highlight_label(label: QtWidgets.QLabel) -> None:
    """Prepare header highlight label with consistent styling."""
    label.setText("")
    label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
    label.setWordWrap(False)
    label.setVisible(False)
    label.setIndent(4)
    font = label.font()
    font.setBold(True)
    font.setPointSize(font.pointSize() + 1)
    label.setFont(font)

    palette = label.palette()
    base_role = QtGui.QPalette.Link if hasattr(QtGui.QPalette, "Link") else QtGui.QPalette.WindowText
    palette.setColor(base_role, QtGui.QColor("#1f3b73"))
    label.setPalette(palette)


def _styled_span(value: str, *, size: Optional[int] = None, weight: int = 600) -> str:
    if not value:
        return ""
    style = []
    if size is not None:
        style.append(f"font-size:{size}pt")
    if weight:
        style.append(f"font-weight:{weight}")
    style_str = ";".join(style)
    return f"<span style='{style_str}'>{escape(value)}</span>"


def build_highlight_html(
    *,
    cliente: Optional[str] = None,
    numero: Optional[str] = None,
    versao: Optional[str] = None,
    ano: Optional[str] = None,
    utilizador: Optional[str] = None,
) -> str:
    """Return formatted rich-text for the shared header highlight."""
    cliente_html = _styled_span(cliente or "", size=14)
    numero_html = _styled_span(numero or "", size=14)
    versao_html = _styled_span(versao or "", size=14)
    ano_html = _styled_span(ano or "", size=9, weight=500)
    user_html = _styled_span(utilizador or "", size=9, weight=500)

    parts = []
    if ano_html:
        parts.append(f"Ano: {ano_html}")

    mid_chunks = []
    if cliente_html:
        mid_chunks.append(f"Cliente: {cliente_html}")
    if numero_html:
        mid_chunks.append(f"Nº Orçamento: {numero_html}")
    if versao_html:
        mid_chunks.append(f"Versão: {versao_html}")
    if mid_chunks:
        parts.append(" | ".join(mid_chunks))

    if user_html:
        parts.append(f"Utilizador: {user_html}")

    return "  |  ".join(parts)


def apply_highlight_text(
    label: QtWidgets.QLabel,
    *,
    cliente: Optional[str] = None,
    numero: Optional[str] = None,
    versao: Optional[str] = None,
    ano: Optional[str] = None,
    utilizador: Optional[str] = None,
) -> None:
    """Set label text using the shared highlight formatting."""
    if label is None:
        return
    html = build_highlight_html(
        cliente=cliente,
        numero=numero,
        versao=versao,
        ano=ano,
        utilizador=utilizador,
    )
    label.setTextFormat(QtCore.Qt.RichText)
    label.setText(html)
    label.setVisible(bool(html))
    if not html:
        label.clear()
