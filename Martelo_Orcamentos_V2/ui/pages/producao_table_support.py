from __future__ import annotations

from typing import Iterable

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStyle


def normalize_filter_text(text: str) -> str:
    value = (text or "").strip()
    return "" if value.casefold() == "todos" else value


def build_search_status_text(*, search: str, has_rows: bool) -> str:
    term = (search or "").strip()
    if term and not has_rows:
        return "Texto pesquisado nao foi encontrado nos dados registados."
    return ""


def build_producao_table_rows(rows: Iterable) -> tuple[list[dict], list[str], list[str]]:
    data: list[dict] = []
    client_names = set()
    responsavel_names = set()
    for row in rows:
        data.append(
            {
                "id": row.id,
                "ano": row.ano,
                "estado": row.estado,
                "responsavel": row.responsavel,
                "codigo_processo": row.codigo_processo,
                "num_enc_phc": row.num_enc_phc,
                "versao_obra": row.versao_obra,
                "versao_plano": row.versao_plano,
                "nome_cliente": row.nome_cliente,
                "ref_cliente": row.ref_cliente,
                "obra": row.obra,
                "data_inicio": row.data_inicio,
                "data_entrega": row.data_entrega,
                "qt_artigos": row.qt_artigos,
                "preco_total": row.preco_total,
                "descricao_producao": row.descricao_producao,
            }
        )
        if row.nome_cliente:
            client_names.add(row.nome_cliente)
        if row.responsavel:
            responsavel_names.add(row.responsavel)
    return data, sorted(client_names), sorted(responsavel_names)


def sync_filter_combo(combo: QtWidgets.QComboBox, values: list[str], current_text: str) -> None:
    current = (current_text or "").strip()
    current_norm = current.casefold()
    combo.blockSignals(True)
    combo.clear()
    combo.addItem("Todos", "")
    for value in values:
        combo.addItem(value, value)
    if current and current_norm != "todos" and current not in values:
        combo.addItem(current, current)
    combo.setCurrentText(current)
    combo.blockSignals(False)


class ProcessoExpandDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, *, parent=None, on_expand=None):
        super().__init__(parent)
        self._on_expand = on_expand

    @staticmethod
    def _icon_rect(option: QtWidgets.QStyleOptionViewItem) -> QtCore.QRect:
        rect = option.rect
        size = max(10, min(14, rect.height() - 6))
        x = rect.x() + 4
        y = rect.y() + max(2, int((rect.height() - size) / 2))
        return QtCore.QRect(x, y, size, size)

    @staticmethod
    def _draw_plus_icon(
        painter: QtGui.QPainter, rect: QtCore.QRect, option: QtWidgets.QStyleOptionViewItem
    ) -> None:
        painter.save()
        try:
            painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
            selected = bool(option.state & QStyle.State_Selected)
            border = option.palette.color(QtGui.QPalette.HighlightedText if selected else QtGui.QPalette.Mid)
            fill = (
                option.palette.color(QtGui.QPalette.Highlight).lighter(135)
                if selected
                else option.palette.color(QtGui.QPalette.Base)
            )
            painter.setPen(QtGui.QPen(border, 1))
            painter.setBrush(QtGui.QBrush(fill))
            painter.drawRect(rect.adjusted(0, 0, -1, -1))

            cx = rect.center().x()
            cy = rect.center().y()
            pad = max(2, int(rect.width() / 4))
            painter.setPen(
                QtGui.QPen(option.palette.color(QtGui.QPalette.HighlightedText if selected else QtGui.QPalette.Text), 1)
            )
            painter.drawLine(rect.left() + pad, cy, rect.right() - pad, cy)
            painter.drawLine(cx, rect.top() + pad, cx, rect.bottom() - pad)
        finally:
            painter.restore()

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> None:
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        widget = opt.widget
        style = widget.style() if widget is not None else QtWidgets.QApplication.style()

        painter.save()
        try:
            style.drawPrimitive(QStyle.PE_PanelItemViewItem, opt, painter, widget)
            icon_rect = self._icon_rect(opt)
            self._draw_plus_icon(painter, icon_rect, opt)

            text_rect = QtCore.QRect(opt.rect)
            text_rect.setLeft(icon_rect.right() + 8)
            text_rect.setRight(text_rect.right() - 2)

            text = opt.text or ""
            elided = opt.fontMetrics.elidedText(text, Qt.ElideRight, max(0, text_rect.width()))
            selected = bool(opt.state & QStyle.State_Selected)
            color_role = QtGui.QPalette.HighlightedText if selected else QtGui.QPalette.Text
            style.drawItemText(
                painter,
                text_rect,
                int(Qt.AlignVCenter | Qt.AlignLeft),
                opt.palette,
                bool(opt.state & QStyle.State_Enabled),
                elided,
                color_role,
            )
        finally:
            painter.restore()

    def editorEvent(
        self,
        event: QtCore.QEvent,
        model: QtCore.QAbstractItemModel,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> bool:
        if event.type() == QtCore.QEvent.MouseButtonRelease:
            try:
                mouse = event  # type: ignore[assignment]
                if getattr(mouse, "button", None) and mouse.button() != Qt.LeftButton:  # type: ignore[attr-defined]
                    return False
                icon_rect = self._icon_rect(option)
                if icon_rect.contains(mouse.pos()):  # type: ignore[attr-defined]
                    if callable(self._on_expand):
                        self._on_expand(index)
                    return True
            except Exception:
                return False
        return super().editorEvent(event, model, option, index)
