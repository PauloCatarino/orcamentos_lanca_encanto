from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PySide6 import QtCore, QtGui
from PySide6.QtCore import QPointF, QRectF, QSize, QSizeF, Qt


def build_external_names(
    *,
    ano: str,
    num_enc: str,
    versao_obra: str,
    versao_plano: str,
    nome_simplex: str | None,
    nome_cliente: str | None,
    ref_cliente: str | None,
    plano_builder: Callable[..., str],
    imos_builder: Callable[..., str],
) -> tuple[str, str]:
    if not ano or not num_enc:
        return "", ""
    try:
        plano = plano_builder(
            ano,
            num_enc,
            versao_obra,
            versao_plano,
            nome_cliente_simplex=nome_simplex,
            nome_cliente=nome_cliente,
            ref_cliente=ref_cliente,
        )
    except Exception:
        plano = ""
    try:
        enc = imos_builder(
            ano,
            num_enc,
            versao_obra,
            nome_cliente_simplex=nome_simplex,
            nome_cliente=nome_cliente,
            ref_cliente=ref_cliente,
        )
    except Exception:
        enc = ""
    return plano, enc


def find_imos_ix_image_path(base_dir: str, nome_enc: str) -> Optional[Path]:
    base = str(base_dir or "").strip()
    nome = str(nome_enc or "").strip()
    if not base or not nome:
        return None
    folder = Path(base) / nome
    candidates = (
        folder / f"{nome}.png",
        folder / f"{nome}.PNG",
    )
    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate
        except Exception:
            continue
    return None


def build_folder_preview_text(folder_path: str, limit: int = 25) -> str:
    path = Path(folder_path or "")
    if not folder_path:
        return ""
    if not path.exists() or not path.is_dir():
        return "Pasta nao encontrada."

    entries = []
    for index, entry in enumerate(path.iterdir()):
        if index >= limit:
            entries.append("... (mais ficheiros)")
            break
        marker = "[DIR]" if entry.is_dir() else ""
        entries.append(f"{entry.name} {marker}".strip())
    if not entries:
        return "Pasta vazia."
    return "Conteudo da pasta:\n" + "\n".join(entries)


def load_scaled_pixmap(path: str, target_size: QtCore.QSize) -> Optional[QtGui.QPixmap]:
    pix = QtGui.QPixmap(path)
    if pix.isNull():
        return None
    return pix.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def render_pdf_preview_image(pdf_doc, path: str, target_size: QtCore.QSize) -> Optional[QtGui.QImage]:
    if pdf_doc is None:
        return None
    status = pdf_doc.load(path)
    ok_status = {getattr(pdf_doc.Status, "Ready", None), getattr(pdf_doc.Status, "NoError", None)}
    ok_status = {value for value in ok_status if value is not None}
    if ok_status and status not in ok_status:
        return None
    if pdf_doc.pageCount() <= 0:
        return None
    page_size = pdf_doc.pagePointSize(0)
    if page_size.width() <= 0 or page_size.height() <= 0:
        return None

    effective_size = target_size
    if effective_size.width() < 10 or effective_size.height() < 10:
        effective_size = QtCore.QSize(320, 260)

    scale = min(effective_size.width() / page_size.width(), effective_size.height() / page_size.height())
    image_size = QSize(int(page_size.width() * scale), int(page_size.height() * scale))

    try:
        rendered = pdf_doc.render(0, image_size)
    except TypeError:
        rendered = None
    except Exception:
        rendered = None
    if isinstance(rendered, QtGui.QImage) and not rendered.isNull():
        return rendered

    image = QtGui.QImage(image_size, QtGui.QImage.Format_ARGB32)
    image.fill(Qt.white)
    supports_flags = False
    flags = 0
    try:
        from PySide6.QtPdf import QPdfDocument

        if hasattr(QPdfDocument, "RenderFlags"):
            flags = QPdfDocument.RenderFlags(0)
            supports_flags = True
    except Exception:
        flags = 0
        supports_flags = False
    painter = QtGui.QPainter(image)
    try:
        rect = QRectF(QPointF(0, 0), QSizeF(image_size))
        if supports_flags:
            pdf_doc.render(0, painter, rect, flags)
        else:
            pdf_doc.render(0, painter, rect)
    finally:
        painter.end()
    return image
