from __future__ import annotations

import importlib
import json
import logging
import os
import shutil
import struct
import subprocess
import tempfile
import zipfile
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

from Martelo_Orcamentos_V2.app.services import producao_processos as svc_producao_processos
from Martelo_Orcamentos_V2.app.services import producao_workflow as svc_producao_workflow
from Martelo_Orcamentos_V2.app.services.settings import get_setting, set_setting

logger = logging.getLogger(__name__)

KEY_PRODUCAO_CNC_SOURCE_ROOT = "producao_cnc_source_root"
KEY_PRODUCAO_MPR_ROOT = "producao_mpr_root"
KEY_PRODUCAO_CUTRITE_EXPORT_ROOT = "producao_cutrite_export_root"
KEY_PREPARACAO_REQUIRED_FILES_TEMPLATE = "producao_preparacao_required_files_user_{user_id}"

DEFAULT_PRODUCAO_CNC_SOURCE_ROOT = r"\\SERVER_LE\Homag_iX\_ProgramasCNC"
DEFAULT_PRODUCAO_MPR_ROOT = r"\\SERVER_LE\_Lanca_Encanto\Operador\FICHEIROS_MPR"
DEFAULT_PRODUCAO_CUTRITE_EXPORT_ROOT = (
    r"\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep_Producao\Cut_Rite_Exportacoes"
)

CONJ_PDF_FILENAME = "CONJ.pdf"
PROJETO_PRODUCAO_PDF_FILENAME = "2_Projeto_Producao.pdf"

STATUS_OK = "ok"
STATUS_MISSING = "missing"
STATUS_OUTDATED = "outdated"
STATUS_BLOCKED = "blocked"

ACTION_GENERATE_PROJETO_PDF = "generate_projeto_pdf"
ACTION_COPY_PROGRAMS_TO_WORK = "copy_programs_to_work"
ACTION_SEND_PROGRAMS_TO_MPR = "send_programs_to_mpr"
ACTION_COPY_CUTRITE_PDF_TO_WORK = "copy_cutrite_pdf_to_work"

A4_LANDSCAPE_WIDTH_PT, A4_LANDSCAPE_HEIGHT_PT = landscape(A4)
XL_PLACEMENT_MOVE_AND_SIZE = 1
XL_ORIENTATION_PORTRAIT = 1
XL_PAPER_A4 = 9
MSO_SHAPE_PICTURE_TYPES = {11, 13}
CADERNO_IMAGE_SHAPE_NAME = "IMOS_PNG_A17"
CADERNO_PLACE_IN_CELL_IDMSO_CANDIDATES = (
    "PicturePlaceInCell",
    "PicturesPlaceInCell",
    "PlacePictureInCell",
    "PictureFormatPlaceInCell",
    "PictureInCell",
)
CADERNO_WORKSHEET_CANDIDATES = ("CD&RP", "2_CAD_ENCARGOS")
CADERNO_PRINT_MACRO_NAME = "todos_setores"
DM_DUPLEX_FLAG = 0x1000
DMDUP_VERTICAL = 2


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
    cutrite_export_root: Optional[Path] = None
    imorder_root: Optional[Path] = None


@dataclass(frozen=True)
class CadernoEncargosPreparationResult:
    workbook_path: Path
    image_path: Path
    worksheet_name: str


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
    cutrite_export_root = Path(
        get_setting(db, KEY_PRODUCAO_CUTRITE_EXPORT_ROOT, DEFAULT_PRODUCAO_CUTRITE_EXPORT_ROOT)
        or DEFAULT_PRODUCAO_CUTRITE_EXPORT_ROOT
    )
    year_folder = mpr_root / f"{datetime.now().year}_MPR"
    work_programs_folder = work_folder / nome_enc_imos_clean
    imorder_root = Path(
        get_setting(
            db,
            svc_producao_processos.KEY_IMORDER_BASE_PATH,
            svc_producao_processos.DEFAULT_IMORDER_BASE_PATH,
        )
        or svc_producao_processos.DEFAULT_IMORDER_BASE_PATH
    )

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
        cutrite_export_root=cutrite_export_root,
        imorder_root=imorder_root,
    )


def collect_preparacao_statuses(
    context: ProducaoPreparacaoContext,
    *,
    required_keys: Optional[set[str]] = None,
) -> list[ProducaoPreparacaoStatus]:
    required = set(required_keys or set(CONFIGURABLE_FILE_KEYS) | set(ALWAYS_REQUIRED_KEYS))
    statuses = [
        _build_file_status(context, spec, True)
        for spec in CONFIGURABLE_FILE_SPECS
        if spec.key in required
    ]
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


def copy_cutrite_pdf_para_obra(context: ProducaoPreparacaoContext) -> Path:
    target_path = _resolve_cutrite_work_pdf_path(context)
    source_path = _resolve_cutrite_export_pdf_path(context)
    if target_path is None or source_path is None:
        raise ValueError("Nome Plano CUT-RITE em falta no processo.")
    if not source_path.exists():
        raise ValueError(f"PDF exportado do CUT-RITE em falta:\n{source_path}")
    context.work_folder.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)
    return target_path


def resolve_caderno_encargos_path(context: ProducaoPreparacaoContext) -> Optional[Path]:
    matches = sorted(context.work_folder.glob("Caderno de Encargos_*.xlsm"))
    return matches[0] if matches else None


def prepare_caderno_encargos_workbook(
    context: ProducaoPreparacaoContext,
    *,
    workbook_path: Optional[Path] = None,
) -> CadernoEncargosPreparationResult:
    target_path = Path(workbook_path) if workbook_path is not None else resolve_caderno_encargos_path(context)
    if target_path is None or not target_path.exists():
        raise ValueError(f"Caderno de Encargos em falta:\n{context.work_folder}\\Caderno de Encargos_*.xlsm")

    image_path = _resolve_latest_imos_png_path(context)
    worksheet_name = _prepare_caderno_encargos_with_excel(
        workbook_path=target_path,
        image_path=image_path,
        run_print_macro=False,
        copies=1,
    )
    return CadernoEncargosPreparationResult(
        workbook_path=target_path,
        image_path=image_path,
        worksheet_name=worksheet_name,
    )


def print_caderno_encargos_workbook(
    context: ProducaoPreparacaoContext,
    *,
    copies: int = 1,
    workbook_path: Optional[Path] = None,
) -> CadernoEncargosPreparationResult:
    target_path = Path(workbook_path) if workbook_path is not None else resolve_caderno_encargos_path(context)
    if target_path is None or not target_path.exists():
        raise ValueError(f"Caderno de Encargos em falta:\n{context.work_folder}\\Caderno de Encargos_*.xlsm")

    image_path = _resolve_latest_imos_png_path(context)
    worksheet_name = _prepare_caderno_encargos_with_excel(
        workbook_path=target_path,
        image_path=image_path,
        run_print_macro=True,
        copies=max(1, int(copies or 1)),
    )
    return CadernoEncargosPreparationResult(
        workbook_path=target_path,
        image_path=image_path,
        worksheet_name=worksheet_name,
    )


def _build_file_status(
    context: ProducaoPreparacaoContext,
    spec: _FileSpec,
    is_required: bool,
) -> ProducaoPreparacaoStatus:
    path = _resolve_spec_path(context, spec)
    source_paths = _resolve_source_paths(context, spec)
    if spec.key == "projeto_pdf":
        action_key = ACTION_GENERATE_PROJETO_PDF
        action_label = "Gerar"
    elif spec.key == "cutrite_pdf":
        action_key = ACTION_COPY_CUTRITE_PDF_TO_WORK
        action_label = "Copiar"
    else:
        action_key = ""
        action_label = ""

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

    if spec.key == "caderno_encargos":
        try:
            prepared = prepare_caderno_encargos_workbook(context, workbook_path=path)
        except Exception as exc:
            return ProducaoPreparacaoStatus(
                key=spec.key,
                label=spec.label,
                state=STATUS_BLOCKED,
                detail=f"{path}\nFalha ao preparar o Caderno de Encargos: {exc}",
                required=is_required,
                configurable=True,
            )
        return ProducaoPreparacaoStatus(
            key=spec.key,
            label=spec.label,
            state=STATUS_OK,
            detail=(
                f"{prepared.workbook_path}\n"
                f"Imagem IMOS inserida em {prepared.worksheet_name}!A17: {prepared.image_path}"
            ),
            required=is_required,
            configurable=True,
        )

    if spec.key == "lista_material_pdf":
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
        return _resolve_cutrite_work_pdf_path(context)
    if spec.key == "conj_pdf":
        return context.conj_pdf_path
    if spec.key == "projeto_pdf":
        return context.projeto_pdf_path

    matches = sorted(context.work_folder.glob(spec.pattern))
    return matches[0] if matches else None


def _resolve_source_paths(context: ProducaoPreparacaoContext, spec: _FileSpec) -> list[Path]:
    if spec.key == "cutrite_pdf":
        source_path = _resolve_cutrite_export_pdf_path(context)
        return [source_path] if source_path is not None and source_path.exists() else []
    if spec.key == "projeto_pdf":
        return [context.conj_pdf_path] if context.conj_pdf_path.exists() else []

    paths: list[Path] = []
    for pattern in spec.source_patterns:
        paths.extend(sorted(context.work_folder.glob(pattern)))
    return paths


def _missing_file_detail(context: ProducaoPreparacaoContext, spec: _FileSpec) -> str:
    if spec.key == "cutrite_pdf":
        target_path = _resolve_cutrite_work_pdf_path(context)
        export_path = _resolve_cutrite_export_pdf_path(context)
        if target_path is None:
            return "Nome Plano CUT-RITE em falta no processo."
        detail = f"{target_path} (em falta)"
        if export_path is not None:
            detail += f"\nOrigem CUT-RITE esperada: {export_path}"
        return detail
    return f"{context.work_folder}\\{spec.pattern} (em falta)"


def _cutrite_pdf_filename(nome_plano_cut_rite: str) -> str:
    name = str(nome_plano_cut_rite or "").strip()
    if not name:
        return ""
    return name if name.casefold().endswith(".pdf") else f"{name}.pdf"


def _resolve_cutrite_work_pdf_path(context: ProducaoPreparacaoContext) -> Optional[Path]:
    filename = _cutrite_pdf_filename(context.nome_plano_cut_rite)
    if not filename:
        return None
    return context.work_folder / filename


def _resolve_cutrite_export_pdf_path(context: ProducaoPreparacaoContext) -> Optional[Path]:
    filename = _cutrite_pdf_filename(context.nome_plano_cut_rite)
    if not filename:
        return None
    export_root = Path(context.cutrite_export_root or DEFAULT_PRODUCAO_CUTRITE_EXPORT_ROOT)
    return export_root / filename


def _resolve_latest_imos_png_path(context: ProducaoPreparacaoContext) -> Path:
    imorder_root = Path(context.imorder_root or svc_producao_processos.DEFAULT_IMORDER_BASE_PATH)
    if not imorder_root.exists() or not imorder_root.is_dir():
        raise ValueError(f"Pasta base Imorder nao encontrada:\n{imorder_root}")

    folder_candidates: list[Path] = []
    exact_folder = imorder_root / str(context.nome_enc_imos or "").strip()
    if exact_folder.exists() and exact_folder.is_dir():
        folder_candidates.append(exact_folder)

    nome_key = str(context.nome_enc_imos or "").strip().casefold()
    if nome_key:
        for entry in imorder_root.iterdir():
            try:
                if not entry.is_dir():
                    continue
            except Exception:
                continue
            if nome_key in entry.name.casefold() and entry not in folder_candidates:
                folder_candidates.append(entry)

    if not folder_candidates:
        raise ValueError(
            "Nao encontrei a pasta da obra no Imorder.\n\n"
            f"Nome esperado: {context.nome_enc_imos}\n"
            f"Base: {imorder_root}"
        )

    folder_candidates.sort(key=lambda path: _safe_mtime(path), reverse=True)
    for folder in folder_candidates:
        png_paths = [
            path
            for path in list(folder.glob("*.png")) + list(folder.glob("*.PNG"))
            if path.is_file()
        ]
        if not png_paths:
            continue
        png_paths.sort(key=lambda path: _safe_mtime(path), reverse=True)
        return png_paths[0]

    raise ValueError(
        "Nao encontrei nenhum ficheiro PNG na pasta IMOS da obra.\n\n"
        f"Pastas verificadas: {', '.join(str(path) for path in folder_candidates[:5])}"
    )


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


def _safe_mtime(path: Path) -> float:
    try:
        return float(path.stat().st_mtime)
    except Exception:
        return 0.0


def _prepare_caderno_encargos_with_excel(
    *,
    workbook_path: Path,
    image_path: Path,
    run_print_macro: bool,
    copies: int,
) -> str:
    try:
        win32_client = importlib.import_module("win32com.client")
        pythoncom = importlib.import_module("pythoncom")
    except Exception as exc:
        raise RuntimeError(
            "A preparacao/impressao do Caderno de Encargos requer o pacote 'pywin32' instalado."
        ) from exc

    worksheet_name = _prepare_caderno_encargos_with_powershell(
        workbook_path=workbook_path,
        image_path=image_path,
    )
    workbook_name = workbook_path.name
    if not _workbook_has_in_cell_picture_data(workbook_path):
        raise RuntimeError(
            "O Excel nao gravou a imagem IMOS como 'na celula'. "
            "A imagem flutuante foi mantida e a preparacao foi interrompida."
        )

    _force_caderno_duplex_long_edge(workbook_path)

    if run_print_macro:
        pythoncom.CoInitialize()
        excel = None
        workbook = None
        try:
            excel = win32_client.DispatchEx("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False
            try:
                excel.AutomationSecurity = 1
            except Exception:
                pass

            workbook = excel.Workbooks.Open(str(workbook_path))
            worksheet = _resolve_caderno_worksheet(workbook)
            worksheet.Activate()
            for _ in range(max(1, copies)):
                _run_excel_macro(excel, workbook_name, CADERNO_PRINT_MACRO_NAME)
        finally:
            if workbook is not None:
                try:
                    workbook.Close(False)
                except Exception:
                    pass
            if excel is not None:
                try:
                    excel.Quit()
                except Exception:
                    pass
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

    return worksheet_name


def _prepare_caderno_encargos_with_powershell(
    *,
    workbook_path: Path,
    image_path: Path,
) -> str:
    script_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".ps1", delete=False) as handle:
            handle.write(_caderno_prepare_ps_script())
            script_path = handle.name

        cmd = [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-STA",
            "-File",
            script_path,
            str(workbook_path),
            str(image_path),
        ]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
            creationflags=creationflags,
        )
        if result.returncode != 0:
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            detail = "\n".join(part for part in (stderr, stdout) if part)
            raise RuntimeError(detail or f"Codigo de saida: {result.returncode}")

        worksheet_name = (result.stdout or "").strip().splitlines()
        return worksheet_name[-1].strip() if worksheet_name else CADERNO_WORKSHEET_CANDIDATES[0]
    finally:
        if script_path:
            try:
                os.unlink(script_path)
            except Exception:
                pass


def _caderno_prepare_ps_script() -> str:
    return r"""
param(
    [Parameter(Mandatory = $true)][string]$WorkbookPath,
    [Parameter(Mandatory = $true)][string]$ImagePath
)

$ErrorActionPreference = 'Stop'

function Get-CadernoWorksheet($Workbook) {
    foreach ($candidate in @('CD&RP', '2_CAD_ENCARGOS')) {
        try {
            return $Workbook.Worksheets.Item($candidate)
        } catch {
        }
    }
    for ($index = 1; $index -le $Workbook.Worksheets.Count; $index++) {
        $worksheet = $Workbook.Worksheets.Item($index)
        $name = [string]$worksheet.Name
        if ($name.ToLower().Contains('cd&rp') -or $name.ToLower().Contains('cad')) {
            return $worksheet
        }
    }
    return $Workbook.Worksheets.Item(1)
}

function Remove-CadernoFloatingPictures($Worksheet) {
    for ($index = $Worksheet.Shapes.Count; $index -ge 1; $index--) {
        try {
            $shape = $Worksheet.Shapes.Item($index)
        } catch {
            continue
        }

        $shapeType = 0
        try {
            $shapeType = [int]$shape.Type
        } catch {
            $shapeType = 0
        }
        if ($shapeType -notin @(11, 13)) {
            continue
        }
        try {
            $shape.Delete()
        } catch {
        }
    }
}

$excel = $null
$workbook = $null
$worksheetName = 'CD&RP'
try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    try {
        $excel.AutomationSecurity = 3
    } catch {
    }

    $workbook = $excel.Workbooks.Open($WorkbookPath)
    $worksheet = Get-CadernoWorksheet $workbook
    $worksheet.Activate() | Out-Null
    $worksheet.PageSetup.Orientation = 1
    $worksheet.PageSetup.PaperSize = 9
    $target = $worksheet.Range('A17').MergeArea
    $left = [double]$target.Left
    $top = [double]$target.Top
    $width = [double]$target.Width
    $height = [double]$target.Height
    $shape = $worksheet.Shapes.AddPicture(
        $ImagePath,
        $false,
        $true,
        $left,
        $top,
        $width,
        $height
    )
    $shape.Name = 'IMOS_PNG_A17'
    try {
        $shape.AlternativeText = 'IMOS_PNG_A17'
    } catch {
    }
    try {
        $shape.Placement = 1
    } catch {
    }
    try {
        $shape.PrintObject = $true
    } catch {
    }
    try {
        $shape.ZOrder(0)
    } catch {
    }

    $shape.Select() | Out-Null
    $shape.PlacePictureInCell()
    $worksheetName = [string]$worksheet.Name
    $workbook.Save()
} finally {
    if ($workbook -ne $null) {
        try {
            $workbook.Close($false)
        } catch {
        }
    }
    if ($excel -ne $null) {
        try {
            $excel.Quit()
        } catch {
        }
    }
}

$excel = $null
$workbook = $null
try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    try {
        $excel.AutomationSecurity = 3
    } catch {
    }

    $workbook = $excel.Workbooks.Open($WorkbookPath)
    $worksheet = Get-CadernoWorksheet $workbook
    $worksheet.Activate() | Out-Null
    Remove-CadernoFloatingPictures $worksheet
    $worksheetName = [string]$worksheet.Name
    $workbook.Save()
} finally {
    if ($workbook -ne $null) {
        try {
            $workbook.Close($false)
        } catch {
        }
    }
    if ($excel -ne $null) {
        try {
            $excel.Quit()
        } catch {
        }
    }
}

Write-Output $worksheetName
"""


def _resolve_caderno_worksheet(workbook):
    for candidate in CADERNO_WORKSHEET_CANDIDATES:
        try:
            return workbook.Worksheets(candidate)
        except Exception:
            continue

    for index in range(1, int(workbook.Worksheets.Count) + 1):
        worksheet = workbook.Worksheets(index)
        worksheet_name = str(getattr(worksheet, "Name", "") or "").strip().casefold()
        if "cd&rp" in worksheet_name or "cad" in worksheet_name:
            return worksheet

    return workbook.Worksheets(1)


def _resolve_caderno_target_range(worksheet):
    anchor = worksheet.Range("A17")
    try:
        if bool(anchor.MergeCells):
            return anchor.MergeArea
    except Exception:
        pass
    return worksheet.Range("A17:O24")


def _replace_caderno_imos_picture(excel, worksheet, image_path: Path) -> None:
    target = _resolve_caderno_target_range(worksheet)
    shape = worksheet.Shapes.AddPicture(
        str(image_path),
        False,
        True,
        float(target.Left),
        float(target.Top),
        float(target.Width),
        float(target.Height),
    )
    shape.Name = CADERNO_IMAGE_SHAPE_NAME
    try:
        shape.AlternativeText = CADERNO_IMAGE_SHAPE_NAME
    except Exception:
        pass
    try:
        shape.Placement = XL_PLACEMENT_MOVE_AND_SIZE
    except Exception:
        pass
    try:
        shape.PrintObject = True
    except Exception:
        pass
    try:
        shape.ZOrder(0)
    except Exception:
        pass
    if _try_place_caderno_picture_in_cell(excel, shape):
        return

    try:
        shape.Delete()
    except Exception:
        pass
    raise RuntimeError("O Excel nao conseguiu converter a imagem IMOS para 'Colocar na Celula'.")


def _try_place_caderno_picture_in_cell(excel, shape) -> bool:
    try:
        shape.Select()
    except Exception:
        pass
    try:
        shape.PlacePictureInCell()
        logger.info("Excel converteu a imagem IMOS para 'Colocar na Celula' via Shape.PlacePictureInCell().")
        return True
    except Exception as exc:
        logger.warning(
            "Shape.PlacePictureInCell() falhou para a imagem IMOS. "
            "Vou tentar fallback por idMso. Erro: %s",
            exc,
        )

    command_bars = getattr(excel, "CommandBars", None)
    if command_bars is None:
        return False

    last_error = None
    for candidate in CADERNO_PLACE_IN_CELL_IDMSO_CANDIDATES:
        try:
            shape.Select()
        except Exception:
            pass
        try:
            command_bars.ExecuteMso(candidate)
            logger.info("Excel converteu a imagem IMOS para 'Colocar na Celula' com idMso=%s", candidate)
            return True
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        logger.warning(
            "Nao foi possivel executar o comando nativo do Excel para 'Colocar na Celula'. "
            "A imagem IMOS ficara como shape ajustada ao intervalo alvo. Ultimo erro: %s",
            last_error,
        )
    return False


def _delete_caderno_previous_shapes(worksheet, target_range, *, delete_main: bool) -> None:
    for index in range(int(worksheet.Shapes.Count), 0, -1):
        try:
            shape = worksheet.Shapes(index)
        except Exception:
            continue

        shape_name = str(getattr(shape, "Name", "") or "").strip().casefold()
        alternative = str(getattr(shape, "AlternativeText", "") or "").strip().casefold()
        if shape_name == CADERNO_IMAGE_SHAPE_NAME.casefold() or alternative == CADERNO_IMAGE_SHAPE_NAME.casefold():
            if delete_main:
                try:
                    shape.Delete()
                except Exception:
                    pass
            continue

        try:
            shape_type = int(shape.Type)
        except Exception:
            shape_type = 0
        if shape_type not in MSO_SHAPE_PICTURE_TYPES:
            continue

        if delete_main and _shape_overlaps_target(shape, target_range):
            try:
                shape.Delete()
            except Exception:
                pass
            continue

        try:
            is_thumbnail = float(shape.Width) < 60 and float(shape.Height) < 60 and float(shape.Top) < float(target_range.Top)
        except Exception:
            is_thumbnail = False
        if is_thumbnail:
            try:
                shape.Delete()
            except Exception:
                pass


def _shape_overlaps_target(shape, target_range) -> bool:
    try:
        shape_left = float(shape.Left)
        shape_top = float(shape.Top)
        shape_right = shape_left + float(shape.Width)
        shape_bottom = shape_top + float(shape.Height)
        target_left = float(target_range.Left)
        target_top = float(target_range.Top)
        target_right = target_left + float(target_range.Width)
        target_bottom = target_top + float(target_range.Height)
    except Exception:
        return False

    return (
        shape_left < target_right
        and shape_right > target_left
        and shape_top < target_bottom
        and shape_bottom > target_top
    )


def _cleanup_caderno_floating_shapes(workbook_path: Path) -> None:
    try:
        win32_client = importlib.import_module("win32com.client")
        pythoncom = importlib.import_module("pythoncom")
    except Exception as exc:
        raise RuntimeError(
            "A limpeza final do Caderno de Encargos requer o pacote 'pywin32' instalado."
        ) from exc

    pythoncom.CoInitialize()
    excel = None
    workbook = None
    try:
        excel = win32_client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        workbook = excel.Workbooks.Open(str(workbook_path))
        worksheet = _resolve_caderno_worksheet(workbook)
        worksheet.Activate()
        target = _resolve_caderno_target_range(worksheet)
        _delete_caderno_previous_shapes(worksheet, target, delete_main=True)
        workbook.Save()
    finally:
        if workbook is not None:
            try:
                workbook.Close(False)
            except Exception:
                pass
        if excel is not None:
            try:
                excel.Quit()
            except Exception:
                pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def _workbook_has_in_cell_picture_data(workbook_path: Path) -> bool:
    if not workbook_path.exists():
        return False

    try:
        with zipfile.ZipFile(workbook_path, "r") as archive:
            return archive.getinfo("xl/richData/rdrichvalue.xml") is not None
    except KeyError:
        return False
    except Exception:
        return False


def _configure_caderno_page_setup(worksheet) -> None:
    page_setup = worksheet.PageSetup
    try:
        page_setup.Orientation = XL_ORIENTATION_PORTRAIT
    except Exception:
        pass
    try:
        page_setup.PaperSize = XL_PAPER_A4
    except Exception:
        pass


def _force_caderno_duplex_long_edge(workbook_path: Path) -> None:
    if not workbook_path.exists():
        raise ValueError(f"Caderno de Encargos nao encontrado:\n{workbook_path}")

    temp_path = workbook_path.with_name(f"{workbook_path.stem}__tmp_duplex{workbook_path.suffix}")
    patched_any = False
    with zipfile.ZipFile(workbook_path, "r") as src_zip, zipfile.ZipFile(temp_path, "w") as dst_zip:
        for info in src_zip.infolist():
            data = src_zip.read(info.filename)
            if info.filename.startswith("xl/printerSettings/") and info.filename.lower().endswith(".bin"):
                patched = _patch_printer_settings_blob(data)
                if patched is not None:
                    data = patched
                    patched_any = True
            dst_zip.writestr(info, data)

    if patched_any:
        shutil.move(str(temp_path), str(workbook_path))
        return

    try:
        temp_path.unlink(missing_ok=True)
    except Exception:
        pass
    raise RuntimeError(
        "Nao foi possivel localizar a configuracao de impressao interna do Caderno de Encargos para ativar duplex."
    )


def _patch_printer_settings_blob(data: bytes) -> Optional[bytes]:
    if not data or len(data) < 96:
        return None

    blob = bytearray(data)
    try:
        dm_fields = struct.unpack_from("<I", blob, 72)[0]
        dm_size = struct.unpack_from("<H", blob, 68)[0]
    except struct.error:
        return None

    if dm_size < 96:
        return None

    dm_fields |= DM_DUPLEX_FLAG
    try:
        struct.pack_into("<I", blob, 72, dm_fields)
        struct.pack_into("<h", blob, 94, DMDUP_VERTICAL)
    except struct.error:
        return None
    return bytes(blob)


def _run_excel_macro(excel, workbook_name: str, macro_name: str) -> None:
    candidates = (
        macro_name,
        f"{workbook_name}!{macro_name}",
        f"'{workbook_name}'!{macro_name}",
    )
    last_error = None
    for candidate in candidates:
        try:
            excel.Run(candidate)
            return
        except Exception as exc:
            last_error = exc
    if last_error is not None:
        raise RuntimeError(f"Falha ao executar a macro '{macro_name}': {last_error}") from last_error


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
