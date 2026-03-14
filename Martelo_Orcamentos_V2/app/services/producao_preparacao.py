from __future__ import annotations

import json
import logging
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Iterable, Optional, Sequence

from PySide6 import QtCore, QtGui, QtPdf
from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from Martelo_Orcamentos_V2.app.services import producao_workflow as svc_producao_workflow
from Martelo_Orcamentos_V2.app.services.settings import get_setting, set_setting

logger = logging.getLogger(__name__)

KEY_PRODUCAO_CNC_SOURCE_ROOT = "producao_cnc_source_root"
KEY_PRODUCAO_MPR_ROOT = "producao_mpr_root"
KEY_PREPARACAO_REQUIRED_FILES_TEMPLATE = "producao_preparacao_required_files_user_{user_id}"

DEFAULT_PRODUCAO_CNC_SOURCE_ROOT = r"\\SERVER_LE\Homag_iX\_ProgramasCNC"
DEFAULT_PRODUCAO_MPR_ROOT = r"\\SERVER_LE\_Lanca_Encanto\Operador\FICHEIROS_MPR"

CONJ_PDF_FILENAME = "CONJ.pdf"
PROJETO_PRODUCAO_PDF_FILENAME = "2_Projeto_Producao.pdf"

STATUS_OK = "ok"
STATUS_MISSING = "missing"
STATUS_OUTDATED = "outdated"
STATUS_BLOCKED = "blocked"

ACTION_GENERATE_PROJETO_PDF = "generate_projeto_pdf"
ACTION_COPY_PROGRAMS_TO_WORK = "copy_programs_to_work"
ACTION_SEND_PROGRAMS_TO_MPR = "send_programs_to_mpr"

A4_LANDSCAPE_WIDTH_PT, A4_LANDSCAPE_HEIGHT_PT = landscape(A4)


@dataclass(frozen=True)
class ProducaoPreparacaoContext:
    processo: object
    work_folder: Path
    nome_enc_imos: str
    nome_plano_cut_rite: str
    cnc_source_root: Path
    cnc_source_folder: Path
    work_programs_folder: Path
    mpr_root: Path
    mpr_year_folder: Path
    mpr_programs_folder: Path
    conj_pdf_path: Path
    projeto_pdf_path: Path


@dataclass(frozen=True)
class FolderSnapshot:
    file_count: int
    latest_mtime: float

    @property
    def has_files(self) -> bool:
        return self.file_count > 0


@dataclass(frozen=True)
class ProducaoPreparacaoStatus:
    key: str
    label: str
    state: str
    detail: str
    required: bool = True
    configurable: bool = False
    action_key: str = ""
    action_label: str = ""

    @property
    def ok(self) -> bool:
        return self.state == STATUS_OK


@dataclass(frozen=True)
class _FileSpec:
    key: str
    label: str
    pattern: str
    source_patterns: tuple[str, ...] = ()


CONFIGURABLE_FILE_SPECS: tuple[_FileSpec, ...] = (
    _FileSpec(
        key="caderno_encargos",
        label="Caderno de Encargos (*.xlsm)",
        pattern="Caderno de Encargos_*.xlsm",
    ),
    _FileSpec(
        key="lista_material_pdf",
        label="Lista_Material_*.pdf",
        pattern="Lista_Material_*.pdf",
        source_patterns=("Lista_Material_*.xlsm", "Lista_Material_*.xlsx"),
    ),
    _FileSpec(
        key="ferragens_a4_pdf",
        label="1_List_FerragensA4.pdf",
        pattern="1_List_FerragensA4.pdf",
        source_patterns=("1_List_Ferragens.xlsx", "1_List_Ferragens.xlsm"),
    ),
    _FileSpec(
        key="projeto_pdf",
        label="2_Projeto_Producao.pdf",
        pattern=PROJETO_PRODUCAO_PDF_FILENAME,
        source_patterns=(CONJ_PDF_FILENAME,),
    ),
    _FileSpec(
        key="resumo_geral_pdf",
        label="3_Resumo_Geral_Encomenda.pdf",
        pattern="3_Resumo_Geral_Encomenda.pdf",
        source_patterns=("3_Resumo_Geral_Encomenda.xlsx", "3_Resumo_Geral_Encomenda.xlsm"),
    ),
    _FileSpec(
        key="etiqueta_palete_pdf",
        label="5_Etiqueta_Palete.pdf",
        pattern="5_Etiqueta_Palete.pdf",
        source_patterns=("5_Etiqueta_Palete_PDF.xlsx", "5_Etiqueta_Palete.xlsx", "5_Etiqueta_Palete.xlsm"),
    ),
    _FileSpec(
        key="resumo_ml_orlas_pdf",
        label="6_Resumo_ML_OrlasA4.pdf",
        pattern="6_Resumo_ML_OrlasA4.pdf",
        source_patterns=(
            "6_Resumo_ML_OrlasA4.xlsx",
            "6_Resumo_ML_OrlasA4.xlsm",
            "6_List_Ferragens_Integrador.xlsx",
            "6_List_Ferragens_Integrador.xlsm",
        ),
    ),
    _FileSpec(
        key="cutrite_pdf",
        label="Plano CUT-RITE (*.pdf)",
        pattern="",
    ),
    _FileSpec(
        key="conj_pdf",
        label="CONJ.pdf",
        pattern=CONJ_PDF_FILENAME,
    ),
)

CONFIGURABLE_FILE_KEYS = tuple(spec.key for spec in CONFIGURABLE_FILE_SPECS)
ALWAYS_REQUIRED_KEYS = ("cnc_source", "cnc_work", "mpr_year", "mpr_sent")
CRITICAL_PENDING_KEYS = {
    "lista_material_pdf",
    "projeto_pdf",
    "cutrite_pdf",
    "cnc_work",
    "mpr_sent",
}


def list_configurable_preparacao_file_options() -> list[dict[str, str]]:
    return [{"key": spec.key, "label": spec.label} for spec in CONFIGURABLE_FILE_SPECS]


def get_preparacao_required_file_keys(db, user_id: Optional[int]) -> set[str]:
    if not user_id:
        return set(CONFIGURABLE_FILE_KEYS)
    raw = get_setting(db, KEY_PREPARACAO_REQUIRED_FILES_TEMPLATE.format(user_id=int(user_id)), None)
    if not raw:
        return set(CONFIGURABLE_FILE_KEYS)
    try:
        parsed = json.loads(raw)
    except Exception:
        logger.warning("Falha a ler preferencias de Preparacao para user_id=%s", user_id)
        return set(CONFIGURABLE_FILE_KEYS)
    if not isinstance(parsed, list):
        return set(CONFIGURABLE_FILE_KEYS)
    return {str(value).strip() for value in parsed if str(value).strip() in CONFIGURABLE_FILE_KEYS}


def set_preparacao_required_file_keys(db, user_id: int, keys: Iterable[str]) -> None:
    cleaned = sorted({str(value).strip() for value in keys if str(value).strip() in CONFIGURABLE_FILE_KEYS})
    set_setting(
        db,
        KEY_PREPARACAO_REQUIRED_FILES_TEMPLATE.format(user_id=int(user_id)),
        json.dumps(cleaned, ensure_ascii=True),
    )


def get_required_preparacao_keys(db, user_id: Optional[int]) -> set[str]:
    keys = set(get_preparacao_required_file_keys(db, user_id))
    keys.update(ALWAYS_REQUIRED_KEYS)
    return keys


def resolve_preparacao_context(
    db,
    *,
    current_id: Optional[int],
    pasta_servidor: str,
    nome_enc_imos: str,
    nome_plano_cut_rite: str = "",
) -> ProducaoPreparacaoContext:
    processo = svc_producao_workflow.load_processo_required(
        db,
        current_id,
        missing_selection_message="Selecione um processo de Producao.",
    )
    work_folder_text = str(pasta_servidor or "").strip()
    if not work_folder_text:
        raise ValueError("Pasta Servidor em falta no processo.")
    work_folder = Path(work_folder_text)
    nome_enc_imos_clean = str(nome_enc_imos or "").strip()
    if not nome_enc_imos_clean:
        raise ValueError("Nome Enc IMOS IX em falta no processo.")

    cnc_source_root = Path(
        get_setting(db, KEY_PRODUCAO_CNC_SOURCE_ROOT, DEFAULT_PRODUCAO_CNC_SOURCE_ROOT)
        or DEFAULT_PRODUCAO_CNC_SOURCE_ROOT
    )
    mpr_root = Path(
        get_setting(db, KEY_PRODUCAO_MPR_ROOT, DEFAULT_PRODUCAO_MPR_ROOT) or DEFAULT_PRODUCAO_MPR_ROOT
    )
    year_folder = mpr_root / f"{datetime.now().year}_MPR"
    work_programs_folder = work_folder / nome_enc_imos_clean

    return ProducaoPreparacaoContext(
        processo=processo,
        work_folder=work_folder,
        nome_enc_imos=nome_enc_imos_clean,
        nome_plano_cut_rite=str(nome_plano_cut_rite or "").strip(),
        cnc_source_root=cnc_source_root,
        cnc_source_folder=cnc_source_root / nome_enc_imos_clean,
        work_programs_folder=work_programs_folder,
        mpr_root=mpr_root,
        mpr_year_folder=year_folder,
        mpr_programs_folder=year_folder / nome_enc_imos_clean,
        conj_pdf_path=work_folder / CONJ_PDF_FILENAME,
        projeto_pdf_path=work_folder / PROJETO_PRODUCAO_PDF_FILENAME,
    )


def collect_preparacao_statuses(
    context: ProducaoPreparacaoContext,
    *,
    required_keys: Optional[set[str]] = None,
) -> list[ProducaoPreparacaoStatus]:
    required = set(required_keys or set(CONFIGURABLE_FILE_KEYS) | set(ALWAYS_REQUIRED_KEYS))
    statuses = [_build_file_status(context, spec, spec.key in required) for spec in CONFIGURABLE_FILE_SPECS]
    statuses.extend(_build_cnc_statuses(context, required))
    statuses.append(_build_ready_status(statuses, required))
    return statuses


def build_pending_preparacao_labels(
    context: ProducaoPreparacaoContext,
    *,
    required_keys: Optional[set[str]] = None,
    critical_only: bool = True,
) -> list[str]:
    keys = set(required_keys or set(CONFIGURABLE_FILE_KEYS) | set(ALWAYS_REQUIRED_KEYS))
    if critical_only:
        keys = {key for key in keys if key in CRITICAL_PENDING_KEYS}
    pending: list[str] = []
    for status in collect_preparacao_statuses(context, required_keys=required_keys):
        if status.key == "obra_pronta":
            continue
        if status.key in keys and not status.ok:
            pending.append(status.label)
    return pending


def generate_projeto_producao_pdf(context: ProducaoPreparacaoContext) -> Path:
    if not context.conj_pdf_path.exists():
        raise ValueError(f"CONJ.pdf em falta:\n{context.conj_pdf_path}")

    try:
        _generate_projeto_pdf_vector(context.conj_pdf_path, context.projeto_pdf_path, max_pages=2)
    except Exception as exc:
        logger.warning("Fallback para raster no 2_Projeto_Producao.pdf: %s", exc)
        page_images = _extract_conj_page_images(context.conj_pdf_path, max_pages=2)
        _render_images_to_a4_pdf(page_images, context.projeto_pdf_path)
    return context.projeto_pdf_path


def copy_programas_para_obra(context: ProducaoPreparacaoContext) -> Path:
    if not context.cnc_source_folder.exists():
        raise ValueError(f"Pasta de origem IMOS em falta:\n{context.cnc_source_folder}")
    _replace_tree(context.cnc_source_folder, context.work_programs_folder)
    return context.work_programs_folder


def send_programas_para_mpr(context: ProducaoPreparacaoContext) -> Path:
    if not context.work_programs_folder.exists():
        raise ValueError(f"Pasta de programas na obra em falta:\n{context.work_programs_folder}")
    context.mpr_year_folder.mkdir(parents=True, exist_ok=True)
    _replace_tree(context.work_programs_folder, context.mpr_programs_folder)
    return context.mpr_programs_folder


def _build_file_status(
    context: ProducaoPreparacaoContext,
    spec: _FileSpec,
    is_required: bool,
) -> ProducaoPreparacaoStatus:
    path = _resolve_spec_path(context, spec)
    source_paths = _resolve_source_paths(context, spec)
    action_key = ACTION_GENERATE_PROJETO_PDF if spec.key == "projeto_pdf" else ""
    action_label = "Gerar" if action_key else ""

    if spec.key == "cutrite_pdf" and not context.nome_plano_cut_rite:
        return ProducaoPreparacaoStatus(
            key=spec.key,
            label=spec.label,
            state=STATUS_BLOCKED,
            detail="Nome Plano CUT-RITE em falta no processo.",
            required=is_required,
            configurable=True,
        )

    if path is None or not path.exists():
        detail = _missing_file_detail(context, spec)
        if source_paths:
            detail += "\nOrigem detetada: " + ", ".join(str(source) for source in source_paths[:3])
        return ProducaoPreparacaoStatus(
            key=spec.key,
            label=spec.label,
            state=STATUS_MISSING,
            detail=detail,
            required=is_required,
            configurable=True,
            action_key=action_key,
            action_label=action_label,
        )

    newest_source = _newest_existing(source_paths)
    if newest_source and newest_source.stat().st_mtime > path.stat().st_mtime + 1:
        return ProducaoPreparacaoStatus(
            key=spec.key,
            label=spec.label,
            state=STATUS_OUTDATED,
            detail=(
                f"{path}\nDesatualizado face a {newest_source.name} "
                f"({ _fmt_ts(newest_source.stat().st_mtime) } > { _fmt_ts(path.stat().st_mtime) })"
            ),
            required=is_required,
            configurable=True,
            action_key=action_key,
            action_label=action_label,
        )

    return ProducaoPreparacaoStatus(
        key=spec.key,
        label=spec.label,
        state=STATUS_OK,
        detail=str(path),
        required=is_required,
        configurable=True,
        action_key=action_key,
        action_label=action_label,
    )


def _build_cnc_statuses(
    context: ProducaoPreparacaoContext,
    required_keys: set[str],
) -> list[ProducaoPreparacaoStatus]:
    statuses: list[ProducaoPreparacaoStatus] = []
    source_snapshot = _snapshot_tree(context.cnc_source_folder)
    work_snapshot = _snapshot_tree(context.work_programs_folder)
    mpr_snapshot = _snapshot_tree(context.mpr_programs_folder)

    if source_snapshot is None:
        statuses.append(
            ProducaoPreparacaoStatus(
                key="cnc_source",
                label="Programas CNC na origem IMOS",
                state=STATUS_MISSING,
                detail=f"{context.cnc_source_folder} (em falta)",
                required="cnc_source" in required_keys,
            )
        )
    else:
        statuses.append(
            ProducaoPreparacaoStatus(
                key="cnc_source",
                label="Programas CNC na origem IMOS",
                state=STATUS_OK,
                detail=_folder_detail(context.cnc_source_folder, source_snapshot),
                required="cnc_source" in required_keys,
            )
        )

    if source_snapshot is None:
        work_state = STATUS_BLOCKED
        work_detail = f"Origem IMOS em falta:\n{context.cnc_source_folder}"
    elif work_snapshot is None:
        work_state = STATUS_MISSING
        work_detail = (
            f"{context.work_programs_folder} (em falta)\nOrigem encontrada mas nao copiada para a obra."
        )
    elif _snapshot_is_older(work_snapshot, source_snapshot):
        work_state = STATUS_OUTDATED
        work_detail = (
            f"{_folder_detail(context.work_programs_folder, work_snapshot)}\n"
            f"Desatualizada face a {context.cnc_source_folder}"
        )
    else:
        work_state = STATUS_OK
        work_detail = _folder_detail(context.work_programs_folder, work_snapshot)

    statuses.append(
        ProducaoPreparacaoStatus(
            key="cnc_work",
            label="Programas CNC copiados para a obra",
            state=work_state,
            detail=work_detail,
            required="cnc_work" in required_keys,
            action_key=ACTION_COPY_PROGRAMS_TO_WORK,
            action_label="Copiar",
        )
    )

    year_state = STATUS_OK if context.mpr_year_folder.exists() else STATUS_MISSING
    statuses.append(
        ProducaoPreparacaoStatus(
            key="mpr_year",
            label="Pasta anual MPR disponivel",
            state=year_state,
            detail=str(context.mpr_year_folder) if year_state == STATUS_OK else f"{context.mpr_year_folder} (em falta)",
            required="mpr_year" in required_keys,
        )
    )

    if year_state != STATUS_OK:
        mpr_state = STATUS_BLOCKED
        mpr_detail = f"Pasta anual MPR em falta:\n{context.mpr_year_folder}"
    elif work_snapshot is None:
        mpr_state = STATUS_BLOCKED
        mpr_detail = f"Pasta de programas na obra em falta:\n{context.work_programs_folder}"
    elif mpr_snapshot is None:
        mpr_state = STATUS_MISSING
        mpr_detail = (
            f"{context.mpr_programs_folder} (em falta)\n"
            "Pasta copiada para a obra mas ainda nao enviada para CNC."
        )
    elif _snapshot_is_older(mpr_snapshot, work_snapshot):
        mpr_state = STATUS_OUTDATED
        mpr_detail = (
            f"{_folder_detail(context.mpr_programs_folder, mpr_snapshot)}\n"
            f"Desatualizada face a {context.work_programs_folder}"
        )
    else:
        mpr_state = STATUS_OK
        mpr_detail = _folder_detail(context.mpr_programs_folder, mpr_snapshot)

    statuses.append(
        ProducaoPreparacaoStatus(
            key="mpr_sent",
            label="Programas CNC enviados para CNC",
            state=mpr_state,
            detail=mpr_detail,
            required="mpr_sent" in required_keys,
            action_key=ACTION_SEND_PROGRAMS_TO_MPR,
            action_label="Enviar",
        )
    )
    return statuses


def _build_ready_status(
    statuses: Sequence[ProducaoPreparacaoStatus],
    required_keys: set[str],
) -> ProducaoPreparacaoStatus:
    pending = [status for status in statuses if status.key in required_keys and not status.ok]
    if pending:
        detail = "Faltas/Bloqueios: " + ", ".join(status.label for status in pending[:6])
        if len(pending) > 6:
            detail += ", ..."
        return ProducaoPreparacaoStatus(
            key="obra_pronta",
            label="Obra pronta para Producao",
            state=STATUS_BLOCKED,
            detail=detail,
            required=False,
        )
    return ProducaoPreparacaoStatus(
        key="obra_pronta",
        label="Obra pronta para Producao",
        state=STATUS_OK,
        detail="Todos os ficheiros e passos obrigatorios desta preparacao estao concluidos.",
        required=False,
    )


def _resolve_spec_path(context: ProducaoPreparacaoContext, spec: _FileSpec) -> Optional[Path]:
    if spec.key == "cutrite_pdf":
        if not context.nome_plano_cut_rite:
            return None
        return context.work_folder / f"{context.nome_plano_cut_rite}.pdf"
    if spec.key == "conj_pdf":
        return context.conj_pdf_path
    if spec.key == "projeto_pdf":
        return context.projeto_pdf_path

    matches = sorted(context.work_folder.glob(spec.pattern))
    return matches[0] if matches else None


def _resolve_source_paths(context: ProducaoPreparacaoContext, spec: _FileSpec) -> list[Path]:
    if spec.key == "projeto_pdf":
        return [context.conj_pdf_path] if context.conj_pdf_path.exists() else []

    paths: list[Path] = []
    for pattern in spec.source_patterns:
        paths.extend(sorted(context.work_folder.glob(pattern)))
    return paths


def _missing_file_detail(context: ProducaoPreparacaoContext, spec: _FileSpec) -> str:
    if spec.key == "cutrite_pdf":
        return str(context.work_folder / f"{context.nome_plano_cut_rite}.pdf")
    return f"{context.work_folder}\\{spec.pattern} (em falta)"


def _newest_existing(paths: Iterable[Path]) -> Optional[Path]:
    existing = [path for path in paths if path.exists()]
    if not existing:
        return None
    return max(existing, key=lambda path: path.stat().st_mtime)


def _snapshot_tree(folder: Path) -> Optional[FolderSnapshot]:
    if not folder.exists() or not folder.is_dir():
        return None
    file_count = 0
    latest = 0.0
    for path in folder.rglob("*"):
        if not path.is_file():
            continue
        file_count += 1
        try:
            latest = max(latest, path.stat().st_mtime)
        except OSError:
            continue
    return FolderSnapshot(file_count=file_count, latest_mtime=latest)


def _snapshot_is_older(target: FolderSnapshot, reference: FolderSnapshot) -> bool:
    if not target.has_files:
        return True
    if reference.file_count > target.file_count:
        return True
    return reference.latest_mtime > target.latest_mtime + 1


def _folder_detail(folder: Path, snapshot: FolderSnapshot) -> str:
    return f"{folder} ({snapshot.file_count} ficheiro(s); atualizacao { _fmt_ts(snapshot.latest_mtime) })"


def _fmt_ts(value: float) -> str:
    if not value:
        return "-"
    return datetime.fromtimestamp(value).strftime("%d-%m-%Y %H:%M")


def _replace_tree(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)


def _generate_projeto_pdf_vector(source_pdf_path: Path, output_pdf_path: Path, *, max_pages: int) -> None:
    local_source = _materialize_local_pdf(source_pdf_path)
    reader = PdfReader(str(local_source))
    writer = PdfWriter()

    total_pages = min(max_pages, len(reader.pages))
    if total_pages <= 0:
        raise RuntimeError(f"PDF sem paginas: {source_pdf_path}")

    for index in range(total_pages):
        source_page = reader.pages[index]
        width = float(source_page.mediabox.width)
        height = float(source_page.mediabox.height)
        if width <= 0 or height <= 0:
            continue

        scale = min(A4_LANDSCAPE_WIDTH_PT / width, A4_LANDSCAPE_HEIGHT_PT / height)
        scaled_width = width * scale
        scaled_height = height * scale
        translate_x = (A4_LANDSCAPE_WIDTH_PT - scaled_width) / 2 - float(source_page.mediabox.left) * scale
        translate_y = (A4_LANDSCAPE_HEIGHT_PT - scaled_height) / 2 - float(source_page.mediabox.bottom) * scale

        page = writer.add_blank_page(A4_LANDSCAPE_WIDTH_PT, A4_LANDSCAPE_HEIGHT_PT)
        page.merge_transformed_page(
            source_page,
            Transformation().scale(scale).translate(translate_x, translate_y),
        )

    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    with output_pdf_path.open("wb") as handle:
        writer.write(handle)


def _qpdf_load_ok(status, expected_ok) -> bool:
    if status == expected_ok:
        return True
    name = str(getattr(status, "name", "") or "").strip().lower()
    if name in {"none_", "none", "ok"}:
        return True
    return False


def _extract_conj_page_images(source_pdf_path: Path, *, max_pages: int = 2) -> list[QtGui.QImage]:
    local_source = _materialize_local_pdf(source_pdf_path)
    document = QtPdf.QPdfDocument()
    status = document.load(str(local_source))
    if not _qpdf_load_ok(status, QtPdf.QPdfDocument.Error.None_):
        raise RuntimeError(f"Nao foi possivel abrir o PDF de origem: {source_pdf_path}")

    page_count = min(max_pages, document.pageCount())
    if page_count <= 0:
        raise RuntimeError(f"PDF sem paginas disponiveis: {source_pdf_path}")

    images: list[QtGui.QImage] = []
    for index in range(page_count):
        page_size = document.pagePointSize(index)
        target_size = QtCore.QSize(
            max(1, int(page_size.width() * 1.5)),
            max(1, int(page_size.height() * 1.5)),
        )
        image = document.render(index, target_size)
        if image.isNull():
            raise RuntimeError(f"Falha a renderizar a pagina {index + 1} do PDF: {source_pdf_path}")
        images.append(image)
    return images


def _render_images_to_a4_pdf(images: Sequence[QtGui.QImage], output_pdf_path: Path) -> None:
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(output_pdf_path), pagesize=(A4_LANDSCAPE_WIDTH_PT, A4_LANDSCAPE_HEIGHT_PT))
    for image in images:
        img_reader, img_width, img_height = _image_reader_from_qimage(image)
        scale = min(A4_LANDSCAPE_WIDTH_PT / img_width, A4_LANDSCAPE_HEIGHT_PT / img_height)
        draw_width = img_width * scale
        draw_height = img_height * scale
        draw_x = (A4_LANDSCAPE_WIDTH_PT - draw_width) / 2
        draw_y = (A4_LANDSCAPE_HEIGHT_PT - draw_height) / 2
        pdf.drawImage(img_reader, draw_x, draw_y, draw_width, draw_height, preserveAspectRatio=True, mask="auto")
        pdf.showPage()
    pdf.save()


def _image_reader_from_qimage(image: QtGui.QImage):
    byte_array = QtCore.QByteArray()
    buffer = QtCore.QBuffer(byte_array)
    buffer.open(QtCore.QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    return ImageReader(BytesIO(bytes(byte_array))), image.width(), image.height()


def _materialize_local_pdf(source_pdf_path: Path) -> Path:
    source_path = Path(source_pdf_path)
    if not source_path.exists():
        raise RuntimeError(f"Nao foi possivel abrir o PDF de origem: {source_pdf_path}")
    if not str(source_path).startswith("\\\\"):
        return source_path
    temp_dir = Path(tempfile.mkdtemp(prefix="martelo_preparacao_pdf_"))
    temp_path = temp_dir / source_path.name
    shutil.copy2(source_path, temp_path)
    return temp_path
