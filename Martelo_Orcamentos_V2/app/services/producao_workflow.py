from __future__ import annotations

import base64
import json
import os
import subprocess
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
import tempfile
import re
import unicodedata
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from Martelo_Orcamentos_V2.app.models import Orcamento, Producao
from Martelo_Orcamentos_V2.app.services.clients import phc_simplex_validation_issue
from Martelo_Orcamentos_V2.app.services.modulos import pasta_imagens_base
from Martelo_Orcamentos_V2.app.services import producao_processos as svc_producao
from Martelo_Orcamentos_V2.app.services import phc_sql as svc_phc
from Martelo_Orcamentos_V2.app.services.settings import get_setting, set_setting
from Martelo_Orcamentos_V2.app.utils.date_utils import format_date_display, parse_date_value


@dataclass(frozen=True)
class SaveProcessoResult:
    processo: Producao
    was_created: bool
    message_title: str
    message_text: str


@dataclass(frozen=True)
class ProcessoActionContext:
    processo: Producao
    info_text: str
    folder_path: Optional[Path]


@dataclass(frozen=True)
class ProcessoFolderResult:
    processo: Producao
    base_dir: str
    path: Path


@dataclass(frozen=True)
class ListaMaterialImosContext:
    processo: Producao
    folder_path: Path
    template_path: Path
    output_path: Path
    values_b64: str


@dataclass(frozen=True)
class ExternalProcessPreparation:
    source: str
    ano: str
    num_enc: str
    tipo_pasta: str
    folder_root: str
    folder_tree: dict
    existing_keys: set[tuple[str, str]]
    versao_obra_next: str
    versao_plano_next: str
    reuse_versao_obra: str
    reuse_versao_plano: str
    should_prompt_versions: bool
    creation_payload: dict


@dataclass(frozen=True)
class OrcamentoConversionPreparation:
    orcamento: Orcamento
    enc_digits: str
    ano_orc: str
    versao_obra: str
    suggested_plano_default: str
    responsavel_default: Optional[str]


@dataclass(frozen=True)
class ProcessoFoldersContext:
    processo: Producao
    folder_root: str
    folder_tree: dict
    title_suffix: str


@dataclass(frozen=True)
class NovaVersaoPreparation:
    processo_atual: Producao
    existing_keys: set[tuple[str, str]]
    folder_root: str
    folder_tree: dict
    sug_obra_cutrite: str
    sug_plano_cutrite: str
    sug_obra_obra: str
    sug_plano_obra: str
    creation_data: dict


@dataclass(frozen=True)
class PHCStatusSyncChange:
    processo_id: int
    codigo_processo: str
    cliente: str
    estado_anterior: str
    estado_novo: str
    phc_estado: str


@dataclass(frozen=True)
class PHCStatusSyncIssue:
    processo_id: int
    codigo_processo: str
    responsavel: str
    reason: str
    martelo_ano: str
    martelo_num_enc_phc: str
    martelo_num_cliente_phc: str
    martelo_nome_cliente: str
    phc_anos: tuple[str, ...]
    phc_num_encs: tuple[str, ...]
    phc_num_clientes: tuple[str, ...]
    phc_nomes: tuple[str, ...]
    phc_estados: tuple[str, ...]


@dataclass(frozen=True)
class PHCStatusSyncResult:
    checked_total: int
    changed: tuple[PHCStatusSyncChange, ...]
    issues: tuple[PHCStatusSyncIssue, ...]
    skipped_daily: bool


@dataclass(frozen=True)
class PHCStatusUserIssue:
    issue: PHCStatusSyncIssue
    hidden: bool = False


@dataclass(frozen=True)
class PHCStatusUserIssueSummary:
    user_id: int
    username: str
    today: date
    total_count: int
    hidden_count: int
    items: list[PHCStatusUserIssue]


KEY_PRODUCAO_PHC_STATUS_LAST_SYNC_DATE = "producao_phc_status_last_sync_date"
KEY_PRODUCAO_PHC_STATUS_ISSUES_CACHE_DATE = "producao_phc_status_issues_cache_date"
KEY_PRODUCAO_PHC_STATUS_ISSUES_CACHE_JSON = "producao_phc_status_issues_cache_json"
AUTO_SHOW_PRODUCAO_PHC_STATUS_ISSUES_PREFIX = "producao_phc_status_issues_seen"
HIDDEN_PRODUCAO_PHC_STATUS_ISSUES_PREFIX = "producao_phc_status_issues_hidden"


def validate_processo_payload(data: dict) -> dict:
    payload = dict(data or {})
    payload["ano"] = str(payload.get("ano") or "").strip()
    payload["num_enc_phc"] = str(payload.get("num_enc_phc") or "").strip()

    if not payload["ano"] or not payload["num_enc_phc"]:
        raise ValueError("Ano e Num Enc PHC sao obrigatorios.")

    return payload


def _simplex_from_text(text: str) -> str:
    base = unicodedata.normalize("NFKD", text or "")
    base = "".join(ch for ch in base if not unicodedata.combining(ch))
    base = re.sub(r"[^A-Za-z0-9]+", "_", base)
    base = re.sub(r"_+", "_", base).strip("_").upper()
    return base or "CLIENTE"


def _normalize_match_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"\s+", " ", text).strip().upper()
    return text


def _normalize_match_number(value: object) -> str:
    text = str(value or "").strip()
    digits = re.sub(r"\D", "", text)
    if not digits:
        return text.upper()
    try:
        return str(int(digits))
    except Exception:
        stripped = digits.lstrip("0")
        return stripped or "0"


def _map_phc_status_to_martelo(value: object) -> Optional[str]:
    text = _normalize_match_text(value)
    if not text:
        return None
    if "ARQUIV" in text:
        return "Arquivado"
    if "FINALIZ" in text:
        return "Finalizado"
    return None


def _row_nome_phc(row: dict) -> str:
    return (
        str(row.get("CL_Nome") or "").strip()
        or str(row.get("BO_Nome") or "").strip()
        or str(row.get("BI_Nome") or "").strip()
    )


def _row_estado_phc_text(row: dict) -> str:
    return (
        str(row.get("Estado_PHC") or "").strip()
        or str(row.get("BO_Tabela1") or "").strip()
        or str(row.get("BI_Tabela1") or "").strip()
    )


def _summarize_candidate_values(rows: list[dict], extractor) -> tuple[str, ...]:
    values: list[str] = []
    seen: set[str] = set()
    for row in rows:
        raw = str(extractor(row) or "").strip()
        if not raw:
            continue
        key = _normalize_match_text(raw)
        if key in seen:
            continue
        seen.add(key)
        values.append(raw)
    return tuple(values)


def _build_phc_status_issue(
    proc: Producao,
    *,
    reason: str,
    rows: list[dict],
) -> PHCStatusSyncIssue:
    return PHCStatusSyncIssue(
        processo_id=int(getattr(proc, "id", 0) or 0),
        codigo_processo=str(getattr(proc, "codigo_processo", "") or "").strip(),
        responsavel=str(getattr(proc, "responsavel", "") or "").strip(),
        reason=reason,
        martelo_ano=str(getattr(proc, "ano", "") or "").strip(),
        martelo_num_enc_phc=str(getattr(proc, "num_enc_phc", "") or "").strip(),
        martelo_num_cliente_phc=str(getattr(proc, "num_cliente_phc", "") or "").strip(),
        martelo_nome_cliente=str(getattr(proc, "nome_cliente", "") or "").strip(),
        phc_anos=_summarize_candidate_values(rows, lambda row: row.get("Ano")),
        phc_num_encs=_summarize_candidate_values(rows, lambda row: row.get("Enc_No")),
        phc_num_clientes=_summarize_candidate_values(rows, lambda row: row.get("Num_PHC")),
        phc_nomes=_summarize_candidate_values(rows, _row_nome_phc),
        phc_estados=_summarize_candidate_values(rows, _row_estado_phc_text),
    )


def _find_direct_phc_status_row(proc: Producao, rows: list[dict]) -> Optional[dict]:
    proc_ano = str(getattr(proc, "ano", "") or "").strip()
    proc_enc = _normalize_match_number(getattr(proc, "num_enc_phc", None))
    proc_num_cliente = _normalize_match_number(getattr(proc, "num_cliente_phc", None))
    proc_nome = _normalize_match_text(getattr(proc, "nome_cliente", None))
    if not (proc_ano and proc_enc and proc_num_cliente and proc_nome):
        return None

    for row in rows:
        row_ano = str(row.get("Ano") or "").strip()
        row_enc = _normalize_match_number(row.get("Enc_No"))
        row_num_cliente = _normalize_match_number(row.get("Num_PHC"))
        row_nome = _normalize_match_text(_row_nome_phc(row))
        if row_ano != proc_ano:
            continue
        if row_enc != proc_enc:
            continue
        if row_num_cliente != proc_num_cliente:
            continue
        if row_nome != proc_nome:
            continue
        return row
    return None


def _serialize_phc_status_issue(issue: PHCStatusSyncIssue) -> dict:
    return {
        "processo_id": int(issue.processo_id),
        "codigo_processo": str(issue.codigo_processo or "").strip(),
        "responsavel": str(issue.responsavel or "").strip(),
        "reason": str(issue.reason or "").strip(),
        "martelo_ano": str(issue.martelo_ano or "").strip(),
        "martelo_num_enc_phc": str(issue.martelo_num_enc_phc or "").strip(),
        "martelo_num_cliente_phc": str(issue.martelo_num_cliente_phc or "").strip(),
        "martelo_nome_cliente": str(issue.martelo_nome_cliente or "").strip(),
        "phc_anos": list(issue.phc_anos),
        "phc_num_encs": list(issue.phc_num_encs),
        "phc_num_clientes": list(issue.phc_num_clientes),
        "phc_nomes": list(issue.phc_nomes),
        "phc_estados": list(issue.phc_estados),
    }


def _deserialize_phc_status_issue(payload: dict) -> Optional[PHCStatusSyncIssue]:
    if not isinstance(payload, dict):
        return None
    try:
        return PHCStatusSyncIssue(
            processo_id=int(payload.get("processo_id") or 0),
            codigo_processo=str(payload.get("codigo_processo") or "").strip(),
            responsavel=str(payload.get("responsavel") or "").strip(),
            reason=str(payload.get("reason") or "").strip(),
            martelo_ano=str(payload.get("martelo_ano") or "").strip(),
            martelo_num_enc_phc=str(payload.get("martelo_num_enc_phc") or "").strip(),
            martelo_num_cliente_phc=str(payload.get("martelo_num_cliente_phc") or "").strip(),
            martelo_nome_cliente=str(payload.get("martelo_nome_cliente") or "").strip(),
            phc_anos=tuple(str(value or "").strip() for value in (payload.get("phc_anos") or []) if str(value or "").strip()),
            phc_num_encs=tuple(
                str(value or "").strip() for value in (payload.get("phc_num_encs") or []) if str(value or "").strip()
            ),
            phc_num_clientes=tuple(
                str(value or "").strip()
                for value in (payload.get("phc_num_clientes") or [])
                if str(value or "").strip()
            ),
            phc_nomes=tuple(str(value or "").strip() for value in (payload.get("phc_nomes") or []) if str(value or "").strip()),
            phc_estados=tuple(
                str(value or "").strip() for value in (payload.get("phc_estados") or []) if str(value or "").strip()
            ),
        )
    except Exception:
        return None


def _cache_phc_status_issues(session: Session, *, issues: list[PHCStatusSyncIssue], today_text: str) -> None:
    payload = json.dumps([_serialize_phc_status_issue(issue) for issue in issues], ensure_ascii=False)
    set_setting(session, KEY_PRODUCAO_PHC_STATUS_ISSUES_CACHE_DATE, today_text)
    set_setting(session, KEY_PRODUCAO_PHC_STATUS_ISSUES_CACHE_JSON, payload)


def _phc_status_issue_hidden_setting_key(user_id: int) -> str:
    return f"{HIDDEN_PRODUCAO_PHC_STATUS_ISSUES_PREFIX}_{int(user_id)}"


def _phc_status_issue_seen_setting_key(user_id: int) -> str:
    return f"{AUTO_SHOW_PRODUCAO_PHC_STATUS_ISSUES_PREFIX}_{int(user_id)}"


def get_hidden_producao_phc_issue_ids(db: Session, *, user_id: int) -> set[int]:
    raw = get_setting(db, _phc_status_issue_hidden_setting_key(user_id), "[]")
    try:
        parsed = json.loads(raw or "[]")
    except Exception:
        parsed = []
    hidden_ids: set[int] = set()
    if isinstance(parsed, list):
        for value in parsed:
            try:
                hidden_ids.add(int(value))
            except Exception:
                continue
    return hidden_ids


def set_producao_phc_issue_hidden(db: Session, *, user_id: int, processo_id: int, hidden: bool) -> None:
    hidden_ids = get_hidden_producao_phc_issue_ids(db, user_id=user_id)
    target_id = int(processo_id)
    if hidden:
        hidden_ids.add(target_id)
    else:
        hidden_ids.discard(target_id)
    set_setting(db, _phc_status_issue_hidden_setting_key(user_id), json.dumps(sorted(hidden_ids)))


def should_auto_show_producao_phc_issues(db: Session, *, user_id: int, today: Optional[date] = None) -> bool:
    current_day = (today or date.today()).isoformat()
    last_seen = get_setting(db, _phc_status_issue_seen_setting_key(user_id), "")
    return str(last_seen or "").strip() != current_day


def mark_producao_phc_issues_seen(db: Session, *, user_id: int, today: Optional[date] = None) -> None:
    set_setting(db, _phc_status_issue_seen_setting_key(user_id), (today or date.today()).isoformat())


def load_cached_phc_status_issues(db: Session, *, today: Optional[date] = None) -> tuple[PHCStatusSyncIssue, ...]:
    current_day = (today or date.today()).isoformat()
    cached_day = str(get_setting(db, KEY_PRODUCAO_PHC_STATUS_ISSUES_CACHE_DATE, "") or "").strip()
    if cached_day != current_day:
        return ()

    raw = get_setting(db, KEY_PRODUCAO_PHC_STATUS_ISSUES_CACHE_JSON, "[]")
    try:
        parsed = json.loads(raw or "[]")
    except Exception:
        parsed = []

    items: list[PHCStatusSyncIssue] = []
    if isinstance(parsed, list):
        for payload in parsed:
            issue = _deserialize_phc_status_issue(payload)
            if issue is not None:
                items.append(issue)

    items.sort(key=lambda issue: (issue.codigo_processo.casefold(), issue.processo_id))
    return tuple(items)


def build_user_phc_status_issue_summary(
    db: Session,
    *,
    user_id: int,
    username: str,
    today: Optional[date] = None,
    include_hidden: bool = False,
) -> PHCStatusUserIssueSummary:
    current_day = today or date.today()
    username_key = _normalize_match_text(username)
    hidden_ids = get_hidden_producao_phc_issue_ids(db, user_id=user_id)
    cached_issues = load_cached_phc_status_issues(db, today=current_day)

    items: list[PHCStatusUserIssue] = []
    total_count = 0
    hidden_count = 0
    for issue in cached_issues:
        if username_key:
            issue_responsavel = _normalize_match_text(issue.responsavel)
            if issue_responsavel != username_key:
                continue
        elif str(issue.responsavel or "").strip():
            continue

        total_count += 1
        is_hidden = int(issue.processo_id) in hidden_ids
        if is_hidden:
            hidden_count += 1
        if is_hidden and not include_hidden:
            continue
        items.append(PHCStatusUserIssue(issue=issue, hidden=is_hidden))

    items.sort(key=lambda entry: (1 if entry.hidden else 0, entry.issue.codigo_processo.casefold(), entry.issue.processo_id))
    return PHCStatusUserIssueSummary(
        user_id=int(user_id),
        username=str(username or "").strip(),
        today=current_day,
        total_count=total_count,
        hidden_count=hidden_count,
        items=items,
    )


def sync_producao_statuses_from_phc(
    session: Session,
    *,
    current_user_id: Optional[int] = None,
    force: bool = False,
    today: Optional[date] = None,
) -> PHCStatusSyncResult:
    today_text = (today or date.today()).isoformat()
    last_sync = str(get_setting(session, KEY_PRODUCAO_PHC_STATUS_LAST_SYNC_DATE, "") or "").strip()
    if not force and last_sync == today_text:
        return PHCStatusSyncResult(checked_total=0, changed=(), issues=(), skipped_daily=True)

    processes = session.execute(
        select(Producao)
        .where(
            Producao.tipo_pasta == svc_producao.DEFAULT_PASTA_ENCOMENDA,
            Producao.num_enc_phc.is_not(None),
            Producao.ano.is_not(None),
        )
        .where((Producao.estado.is_(None)) | (Producao.estado != "Arquivado"))
        .order_by(Producao.id.desc())
    ).scalars().all()

    years = sorted({str(getattr(proc, "ano", "") or "").strip() for proc in processes if str(getattr(proc, "ano", "") or "").strip()})
    phc_rows_all: list[dict] = []
    for year in years:
        phc_rows_all.extend(
            svc_phc.query_phc_estado_debug_rows(
                session,
                ano=year,
                max_rows=0,
            )
        )

    rows_by_year_enc: dict[tuple[str, str], list[dict]] = {}
    rows_by_enc: dict[str, list[dict]] = {}
    for row in phc_rows_all:
        row_year = str(row.get("Ano") or "").strip()
        row_enc = str(row.get("Enc_No") or "").strip()
        if row_year and row_enc:
            rows_by_year_enc.setdefault((row_year, row_enc), []).append(row)
        if row_enc:
            rows_by_enc.setdefault(row_enc, []).append(row)

    changed: list[PHCStatusSyncChange] = []
    issues: list[PHCStatusSyncIssue] = []
    checked_total = 0

    for proc in processes:
        checked_total += 1
        proc_ano = str(getattr(proc, "ano", "") or "").strip()
        proc_enc = str(getattr(proc, "num_enc_phc", "") or "").strip()
        proc_num_cliente = str(getattr(proc, "num_cliente_phc", "") or "").strip()
        proc_nome = str(getattr(proc, "nome_cliente", "") or "").strip()

        if not (proc_ano and proc_enc):
            issues.append(
                _build_phc_status_issue(
                    proc,
                    reason="Campos do Martelo em falta para consultar o PHC (Ano e/ou Num Enc PHC).",
                    rows=[],
                )
            )
            continue

        rows = rows_by_year_enc.get((proc_ano, _normalize_match_number(proc_enc)), [])
        if not rows:
            rows = rows_by_year_enc.get((proc_ano, proc_enc), [])

        if not (proc_ano and proc_enc and proc_num_cliente and proc_nome):
            fallback_rows = rows_by_enc.get(_normalize_match_number(proc_enc), []) or rows_by_enc.get(proc_enc, [])
            issues.append(
                _build_phc_status_issue(
                    proc,
                    reason="Campos do Martelo em falta para validar com seguranca (Ano, Num Enc PHC, Num cliente PHC e Nome Cliente).",
                    rows=fallback_rows or rows,
                )
            )
            continue

        match_row = _find_direct_phc_status_row(proc, rows)
        if match_row is None:
            fallback_rows = rows_by_enc.get(_normalize_match_number(proc_enc), []) or rows_by_enc.get(proc_enc, [])
            issues.append(
                _build_phc_status_issue(
                    proc,
                    reason="Nao foi encontrada correspondencia direta entre Martelo e PHC para esta encomenda.",
                    rows=fallback_rows or rows,
                )
            )
            continue

        phc_estado = _row_estado_phc_text(match_row)
        novo_estado = _map_phc_status_to_martelo(phc_estado)
        if not novo_estado:
            continue

        estado_atual = str(getattr(proc, "estado", "") or "").strip()
        if estado_atual == novo_estado:
            continue

        proc.estado = novo_estado
        if current_user_id is not None:
            proc.updated_by = current_user_id
        session.add(proc)
        changed.append(
            PHCStatusSyncChange(
                processo_id=int(getattr(proc, "id", 0) or 0),
                codigo_processo=str(getattr(proc, "codigo_processo", "") or "").strip(),
                cliente=proc_nome,
                estado_anterior=estado_atual or "(vazio)",
                estado_novo=novo_estado,
                phc_estado=phc_estado,
            )
        )

    set_setting(session, KEY_PRODUCAO_PHC_STATUS_LAST_SYNC_DATE, today_text)
    _cache_phc_status_issues(session, issues=issues, today_text=today_text)
    session.flush()
    return PHCStatusSyncResult(
        checked_total=checked_total,
        changed=tuple(changed),
        issues=tuple(issues),
        skipped_daily=False,
    )


def load_processo_required(
    session: Session,
    current_id: Optional[int],
    *,
    missing_selection_message: str = "Selecione um processo.",
) -> Producao:
    if not current_id:
        raise ValueError(missing_selection_message)

    processo = svc_producao.obter_processo(session, current_id)
    if not processo:
        raise ValueError("Processo nao encontrado.")
    return processo


def build_processo_action_context(
    session: Session,
    current_id: Optional[int],
    *,
    missing_selection_message: str = "Selecione um processo.",
) -> ProcessoActionContext:
    processo = load_processo_required(
        session,
        current_id,
        missing_selection_message=missing_selection_message,
    )
    info = f"{getattr(processo, 'codigo_processo', '') or ''} - {getattr(processo, 'nome_cliente_simplex', None) or getattr(processo, 'nome_cliente', None) or ''}"
    folder_text = str(getattr(processo, "pasta_servidor", "") or "").strip()
    folder = Path(folder_text) if folder_text else None
    return ProcessoActionContext(
        processo=processo,
        info_text=info,
        folder_path=folder,
    )


def delete_processo(
    session: Session,
    current_id: Optional[int],
    *,
    delete_folder: bool,
) -> ProcessoActionContext:
    context = build_processo_action_context(session, current_id)
    if delete_folder and context.folder_path and context.folder_path.exists():
        shutil.rmtree(context.folder_path, ignore_errors=False)
    svc_producao.eliminar_processo(session, int(current_id))
    return context


def _resolve_base_dir(session: Session, current_base_dir: str) -> str:
    return get_setting(
        session,
        getattr(svc_producao, "KEY_PRODUCAO_BASE_PATH", "base_path_producao"),
        current_base_dir,
    ) or current_base_dir


def create_processo_folder(
    session: Session,
    current_id: Optional[int],
    *,
    current_base_dir: str,
    tipo_pasta: Optional[str],
) -> ProcessoFolderResult:
    processo = load_processo_required(
        session,
        current_id,
        missing_selection_message="Grave primeiro o processo antes de criar pasta.",
    )
    base_dir = _resolve_base_dir(session, current_base_dir)
    path = svc_producao.criar_pasta_para_processo(
        session,
        int(current_id),
        base_dir=base_dir,
        tipo_pasta=tipo_pasta,
        pasta_nome_custom=None,
    )
    return ProcessoFolderResult(processo=processo, base_dir=base_dir, path=Path(path))


def open_processo_folder(
    session: Session,
    current_id: Optional[int],
    *,
    current_base_dir: str,
    tipo_pasta: Optional[str],
) -> ProcessoFolderResult:
    processo = load_processo_required(session, current_id)
    base_dir = _resolve_base_dir(session, current_base_dir)
    path = svc_producao.abrir_pasta_para_processo(
        session,
        int(current_id),
        base_dir=base_dir,
        tipo_pasta=tipo_pasta,
        pasta_nome_custom=None,
    )
    return ProcessoFolderResult(processo=processo, base_dir=base_dir, path=Path(path))


def resolve_pdf_manager_target(session: Session, current_id: Optional[int]) -> Producao:
    processo = load_processo_required(session, current_id)
    if not getattr(processo, "pasta_servidor", None):
        raise ValueError(
            "Pasta Servidor em falta.\n\nUse 'Criar Pasta' para gerar a pasta da obra no servidor."
        )
    return processo


def build_processo_folders_context(session: Session, current_id: Optional[int]) -> ProcessoFoldersContext:
    processo = load_processo_required(session, current_id)
    ano = getattr(processo, "ano", None)
    num_enc = getattr(processo, "num_enc_phc", None)
    if not ano or not num_enc:
        raise ValueError("Processo sem Ano ou Num Enc PHC.")

    tipo_pasta = getattr(processo, "tipo_pasta", None)
    folder_root, folder_tree = svc_producao.listar_pastas_enc_arvore(
        session,
        ano=ano,
        num_enc_phc=num_enc,
        tipo_pasta=tipo_pasta,
    )
    title_suffix = str(getattr(processo, "codigo_processo", "") or "").strip() or str(num_enc)
    return ProcessoFoldersContext(
        processo=processo,
        folder_root=folder_root,
        folder_tree=folder_tree,
        title_suffix=title_suffix,
    )


def prepare_external_process_creation(
    session: Session,
    *,
    result_data: dict,
    responsavel_default: Optional[str],
) -> ExternalProcessPreparation:
    source = str((result_data or {}).get("source") or "").lower().strip()
    if source not in {"phc", "streamlit"}:
        raise ValueError("A origem selecionada ainda esta em desenvolvimento.")

    tipo_pasta = (
        svc_producao.DEFAULT_PASTA_ENCOMENDA_FINAL
        if source == "streamlit"
        else svc_producao.DEFAULT_PASTA_ENCOMENDA
    )
    ano = str((result_data or {}).get("ano") or "").strip() or datetime.now().strftime("%Y")
    num_enc = str((result_data or {}).get("num_enc_phc") or "").strip()
    if not num_enc:
        raise ValueError("Num_Enc_PHC em falta.")

    existing_db = svc_producao.listar_versoes_processo(session, ano=ano, num_enc_phc=num_enc)
    vv_fs: set[str] = set()
    fs_pairs: set[tuple[str, str]] = set()
    try:
        vv_fs = svc_producao.listar_versoes_obra_em_pastas(
            session,
            ano=ano,
            num_enc_phc=num_enc,
            tipo_pasta=tipo_pasta,
        )
        for vv in vv_fs:
            for pp in svc_producao.listar_versoes_plano_em_pastas(
                session,
                ano=ano,
                num_enc_phc=num_enc,
                versao_obra=vv,
                tipo_pasta=tipo_pasta,
            ):
                fs_pairs.add((vv, pp))
    except Exception:
        fs_pairs = set()

    try:
        folder_root, folder_tree = svc_producao.listar_pastas_enc_arvore(
            session,
            ano=ano,
            num_enc_phc=num_enc,
            tipo_pasta=tipo_pasta,
        )
    except Exception:
        folder_root, folder_tree = "", {}

    existing_db_norm = {
        (svc_producao._two_digit(vv), svc_producao._two_digit(pp))
        for vv, pp in (existing_db or set())
    }
    fs_pairs_norm = {(svc_producao._two_digit(vv), svc_producao._two_digit(pp)) for vv, pp in fs_pairs}
    vv_fs_norm = {svc_producao._two_digit(vv) for vv in vv_fs}

    versao_obra_next = svc_producao.sugerir_proxima_versao_obra(
        session,
        ano=ano,
        num_enc_phc=num_enc,
        requested="01",
        tipo_pasta=tipo_pasta,
    )
    versao_plano_next = svc_producao.sugerir_proxima_versao_plano(
        session,
        ano=ano,
        num_enc_phc=num_enc,
        versao_obra=versao_obra_next,
        requested="01",
        tipo_pasta=tipo_pasta,
    )

    if fs_pairs_norm - existing_db_norm:
        reuse_vv, reuse_pp = sorted(fs_pairs_norm - existing_db_norm)[0]
    elif vv_fs_norm:
        reuse_vv = sorted(vv_fs_norm)[0]
        reuse_pp = svc_producao.sugerir_proxima_versao_plano(
            session,
            ano=ano,
            num_enc_phc=num_enc,
            versao_obra=reuse_vv,
            requested="01",
            tipo_pasta=tipo_pasta,
        )
    else:
        reuse_vv, reuse_pp = versao_obra_next, versao_plano_next

    creation_payload = {
        "tipo_pasta": tipo_pasta,
        "criar_pasta": False,
        "responsavel": (responsavel_default or "").strip() or None,
        "estado": "Planeamento",
        "nome_cliente": str((result_data or {}).get("nome_cliente") or "").strip(),
        "nome_cliente_simplex": str((result_data or {}).get("nome_cliente_simplex") or "").strip(),
        "num_cliente_phc": str((result_data or {}).get("num_cliente_phc") or "").strip(),
        "ref_cliente": str((result_data or {}).get("ref_cliente") or "").strip(),
        "descricao_artigos": str((result_data or {}).get("descricao_artigos") or "").strip(),
        "data_inicio": str((result_data or {}).get("data_inicio") or "").strip(),
        "data_entrega": str((result_data or {}).get("data_entrega") or "").strip(),
        "pasta_servidor": "",
    }

    return ExternalProcessPreparation(
        source=source,
        ano=ano,
        num_enc=num_enc,
        tipo_pasta=tipo_pasta,
        folder_root=folder_root,
        folder_tree=folder_tree,
        existing_keys=existing_db_norm,
        versao_obra_next=versao_obra_next,
        versao_plano_next=versao_plano_next,
        reuse_versao_obra=reuse_vv,
        reuse_versao_plano=reuse_pp,
        should_prompt_versions=bool(folder_tree or fs_pairs_norm or vv_fs_norm),
        creation_payload=creation_payload,
    )


def create_external_process(
    session: Session,
    *,
    preparation: ExternalProcessPreparation,
    versao_obra: str,
    versao_plano: str,
    current_user_id: Optional[int],
) -> Producao:
    payload = dict(preparation.creation_payload)
    return svc_producao.criar_processo(
        session,
        ano=preparation.ano,
        num_enc_phc=preparation.num_enc,
        versao_obra=versao_obra,
        versao_plano=versao_plano,
        current_user_id=current_user_id,
        **payload,
    )


def prepare_nova_versao(
    session: Session,
    *,
    current_id: Optional[int],
    data: dict,
) -> NovaVersaoPreparation:
    if not current_id:
        raise ValueError("Selecione um processo para criar uma nova versao.")

    payload = dict(data or {})
    if not payload.get("ano") or not payload.get("num_enc_phc"):
        raise ValueError("Ano e Num Enc PHC sao obrigatorios.")

    processo_atual = load_processo_required(session, current_id)
    ano = str(payload.get("ano") or "")
    num_enc = str(payload.get("num_enc_phc") or "")
    ver_obra_atual = str(payload.get("versao_obra") or "01")
    ver_plano_atual = str(payload.get("versao_plano") or "01")
    tipo_pasta = getattr(processo_atual, "tipo_pasta", None)

    existing = svc_producao.listar_versoes_processo(session, ano=ano, num_enc_phc=num_enc)
    try:
        vv_fs = svc_producao.listar_versoes_obra_em_pastas(
            session,
            ano=ano,
            num_enc_phc=num_enc,
            tipo_pasta=tipo_pasta,
        )
        fs_pairs: set[tuple[str, str]] = set()
        for vv in vv_fs:
            for pp in svc_producao.listar_versoes_plano_em_pastas(
                session,
                ano=ano,
                num_enc_phc=num_enc,
                versao_obra=vv,
                tipo_pasta=tipo_pasta,
            ):
                fs_pairs.add((vv, pp))
        existing |= fs_pairs
    except Exception:
        pass

    folder_root, folder_tree = svc_producao.listar_pastas_enc_arvore(
        session,
        ano=ano,
        num_enc_phc=num_enc,
        tipo_pasta=tipo_pasta,
    )
    try:
        req_plano = str(int(ver_plano_atual) + 1) if ver_plano_atual.strip().isdigit() else None
    except Exception:
        req_plano = None
    sug_plano_cutrite = svc_producao.sugerir_proxima_versao_plano(
        session,
        ano=ano,
        num_enc_phc=num_enc,
        versao_obra=ver_obra_atual,
        requested=req_plano,
        tipo_pasta=tipo_pasta,
    )
    sug_obra_cutrite = svc_producao._two_digit(ver_obra_atual)

    try:
        req_obra = str(int(ver_obra_atual) + 1) if ver_obra_atual.strip().isdigit() else None
    except Exception:
        req_obra = None
    sug_obra_obra = svc_producao.sugerir_proxima_versao_obra(
        session,
        ano=ano,
        num_enc_phc=num_enc,
        requested=req_obra,
        tipo_pasta=tipo_pasta,
    )
    sug_plano_obra = svc_producao.sugerir_proxima_versao_plano(
        session,
        ano=ano,
        num_enc_phc=num_enc,
        versao_obra=sug_obra_obra,
        requested="01",
        tipo_pasta=tipo_pasta,
    )

    creation_data = dict(payload)
    creation_data["pasta_servidor"] = ""
    creation_data["orcamento_id"] = getattr(processo_atual, "orcamento_id", None)
    creation_data["client_id"] = getattr(processo_atual, "client_id", None)

    return NovaVersaoPreparation(
        processo_atual=processo_atual,
        existing_keys=existing,
        folder_root=folder_root,
        folder_tree=folder_tree,
        sug_obra_cutrite=sug_obra_cutrite,
        sug_plano_cutrite=sug_plano_cutrite,
        sug_obra_obra=sug_obra_obra,
        sug_plano_obra=sug_plano_obra,
        creation_data=creation_data,
    )


def create_nova_versao(
    session: Session,
    *,
    preparation: NovaVersaoPreparation,
    versao_obra: str,
    versao_plano: str,
    current_user_id: Optional[int],
) -> Producao:
    data = dict(preparation.creation_data)
    data["versao_obra"] = versao_obra
    data["versao_plano"] = versao_plano
    return svc_producao.criar_processo(
        session,
        ano=data.pop("ano"),
        num_enc_phc=data.pop("num_enc_phc"),
        versao_obra=data.pop("versao_obra"),
        versao_plano=data.pop("versao_plano"),
        criar_pasta=False,
        current_user_id=current_user_id,
        **data,
    )


def prepare_orcamento_conversion(
    session: Session,
    *,
    orcamento_id: int,
    responsavel_default: Optional[str],
) -> OrcamentoConversionPreparation:
    orcamento = session.get(Orcamento, int(orcamento_id))
    if not orcamento:
        raise ValueError("Orcamento selecionado nao encontrado.")
    if not getattr(orcamento, "enc_phc", None):
        raise ValueError(
            "Nao e possivel converter o orcamento para Producao porque ainda nao existe o Num Enc PHC (enc_phc).\n\n"
            "Preencha o Num Enc PHC no orcamento e tente novamente."
        )

    enc_digits = "".join(ch for ch in str(getattr(orcamento, "enc_phc", "") or "") if ch.isdigit())
    if not enc_digits:
        raise ValueError("Num Enc PHC invalido.")

    ano_orc = str(getattr(orcamento, "ano", None) or datetime.now().year)
    versao_obra = str(getattr(orcamento, "versao", None) or "01")
    suggested_plano_default = svc_producao.sugerir_proxima_versao_plano(
        session,
        ano=ano_orc,
        num_enc_phc=enc_digits,
        versao_obra=versao_obra,
        requested="01",
        tipo_pasta=svc_producao.DEFAULT_PASTA_ENCOMENDA,
    )
    return OrcamentoConversionPreparation(
        orcamento=orcamento,
        enc_digits=enc_digits,
        ano_orc=ano_orc,
        versao_obra=versao_obra,
        suggested_plano_default=str(suggested_plano_default or "01"),
        responsavel_default=(responsavel_default or "").strip() or None,
    )


def _phc_date_to_martelo(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    parsed = parse_date_value(raw.replace(".", "-"))
    if parsed is not None:
        return format_date_display(parsed)
    return raw.replace(".", "-")


def create_process_from_orcamento_conversion(
    session: Session,
    *,
    preparation: OrcamentoConversionPreparation,
    versao_plano: str,
    current_user_id: Optional[int],
) -> Producao:
    rows_phc = svc_phc.query_phc_encomenda_itens(
        session,
        num_enc_phc=preparation.enc_digits,
        ano=preparation.ano_orc,
    )
    if not rows_phc:
        raise ValueError(
            "Nao foi encontrada nenhuma encomenda no PHC para este Num Enc PHC.\n\n"
            "Verifique se o Num Enc PHC do orcamento esta correto e se existe no PHC."
        )

    base = rows_phc[0] or {}
    nome_cliente = str(base.get("Cliente") or "").strip()
    nome_simplex = str(base.get("Cliente_Abreviado") or "").strip()
    num_cliente_phc = str(base.get("Num_PHC") or "").strip()
    ref_cliente = str(base.get("Ref_Cliente") or "").strip()
    validation_issue = phc_simplex_validation_issue(
        cliente_nome=nome_cliente,
        num_phc=num_cliente_phc,
        simplex=nome_simplex,
        action_label="criar o processo",
    )
    if validation_issue:
        raise ValueError(validation_issue[1])

    seen: set[str] = set()
    descr_list: list[str] = []
    for row in rows_phc:
        descricao = str(row.get("Descricao_Artigo") or "").strip()
        if not descricao or descricao in seen:
            continue
        seen.add(descricao)
        descr_list.append(descricao)
    descricao_artigos = "\n".join(descr_list).strip()

    data_inicio = _phc_date_to_martelo(str(base.get("Data_Encomenda") or "").strip())
    data_entrega = _phc_date_to_martelo(str(base.get("Data_Entrega") or "").strip())
    ano_proc = str(base.get("Ano") or preparation.ano_orc or datetime.now().year).strip()
    ver_plano_final = svc_producao.sugerir_proxima_versao_plano(
        session,
        ano=ano_proc,
        num_enc_phc=preparation.enc_digits,
        versao_obra=preparation.versao_obra,
        requested=versao_plano or preparation.suggested_plano_default or "01",
        tipo_pasta=svc_producao.DEFAULT_PASTA_ENCOMENDA,
    )

    orc = preparation.orcamento
    return svc_producao.criar_processo(
        session,
        ano=ano_proc,
        num_enc_phc=preparation.enc_digits,
        versao_obra=preparation.versao_obra,
        versao_plano=ver_plano_final,
        criar_pasta=False,
        current_user_id=current_user_id,
        responsavel=preparation.responsavel_default,
        estado="Planeamento",
        tipo_pasta=svc_producao.DEFAULT_PASTA_ENCOMENDA,
        orcamento_id=getattr(orc, "id", None),
        client_id=getattr(orc, "client_id", None),
        num_orcamento=getattr(orc, "num_orcamento", None),
        versao_orc=getattr(orc, "versao", None),
        obra=getattr(orc, "obra", None),
        localizacao=getattr(orc, "localizacao", None),
        descricao_orcamento=getattr(orc, "descricao_orcamento", None),
        preco_total=getattr(orc, "preco_total", None),
        pasta_servidor="",
        nome_cliente=nome_cliente,
        nome_cliente_simplex=nome_simplex,
        num_cliente_phc=num_cliente_phc,
        ref_cliente=ref_cliente,
        descricao_artigos=descricao_artigos,
        data_inicio=data_inicio,
        data_entrega=data_entrega,
    )


def prepare_lista_material_imos(
    session: Session,
    *,
    current_id: Optional[int],
    pasta_servidor: str,
    nome_enc_imos: str,
    values: dict,
) -> ListaMaterialImosContext:
    processo = load_processo_required(session, current_id)

    pasta_txt = str(pasta_servidor or "").strip()
    if not pasta_txt:
        raise ValueError("Pasta Servidor em falta.\n\nUse 'Criar Pasta' para gerar a pasta da obra no servidor.")

    folder_path = Path(pasta_txt)
    if not folder_path.exists() or not folder_path.is_dir():
        raise ValueError(f"Pasta Servidor nao encontrada:\n{folder_path}")

    nome_enc_txt = str(nome_enc_imos or "").strip()
    if not nome_enc_txt:
        raise ValueError("Nome Enc IMOS IX em falta.")

    template_path = Path(pasta_imagens_base(session) or "") / "Lista_Material_IMOS_MARTELO.xltm"
    if not template_path.is_file():
        raise ValueError(f"Modelo Excel nao encontrado:\n{template_path}")

    output_path = folder_path / f"Lista_Material_{nome_enc_txt}.xlsm"
    values_json = json.dumps(dict(values or {}), ensure_ascii=False)
    values_b64 = base64.b64encode(values_json.encode("utf-8")).decode("ascii")

    return ListaMaterialImosContext(
        processo=processo,
        folder_path=folder_path,
        template_path=template_path,
        output_path=output_path,
        values_b64=values_b64,
    )


def _lista_material_imos_ps_script() -> str:
    return r"""
param(
  [Parameter(Mandatory=$true)][string]$TemplatePath,
  [Parameter(Mandatory=$true)][string]$OutputPath,
  [Parameter(Mandatory=$true)][string]$ValuesB64
)
$ErrorActionPreference = 'Stop'

$valuesJson = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($ValuesB64))
$v = $valuesJson | ConvertFrom-Json

function To-OADate([string]$text) {
  if (-not $text) { return $null }
  try {
    $dt = [datetime]::ParseExact($text, 'dd-MM-yyyy', $null)
    return $dt.ToOADate()
  } catch { return $null }
}

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
try { $excel.AutomationSecurity = 3 } catch { }

try {
  $m = [Type]::Missing
  $args = @($TemplatePath, 0, $true, $m, $m, $m, $m, $m, $m, $m, $m, $m, $m, $m, 1)
  $wb = $excel.Workbooks.GetType().InvokeMember('Open', [System.Reflection.BindingFlags]::InvokeMethod, $null, $excel.Workbooks, $args)
  try {
    $ws = $null
    foreach ($sn in @('DEFENICOES','DEFINICOES')) {
      try { $ws = $wb.Worksheets.Item($sn); break } catch { }
    }
    if ($ws -eq $null) { $ws = $wb.Worksheets.Item(1) }

    $ws.Range('B3').Value2 = [string]$v.RESPONSAVEL
    $ws.Range('C3').Value2 = [string]$v.REF_CLIENTE
    $ws.Range('D3').Value2 = [string]$v.OBRA
    $ws.Range('E3').Value2 = [string]$v.NOME_ENC_IMOS_IX
    $ws.Range('F3').Value2 = [string]$v.NUM_CLIENTE_PHC
    $ws.Range('G3').Value2 = [string]$v.NOME_CLIENTE
    $ws.Range('H3').Value2 = [string]$v.NOME_CLIENTE_SIMPLEX
    $ws.Range('I3').Value2 = [string]$v.LOCALIZACAO
    $desc = [string]$v.DESCRICAO_PRODUCAO
    if ($desc -eq '') { $desc = [string]$v.DESCRICAO_ARTIGOS }
    $ws.Range('J3').Value2 = $desc
    $ws.Range('K3').Value2 = [string]$v.MATERIAIS

    $qtd = $null
    if ($v.QTD -ne $null -and [string]$v.QTD -ne '') { try { $qtd = [string]([double]([string]$v.QTD).Replace(',', '.')) } catch { $qtd = [string]$v.QTD } }
    $ws.Range('L3').Value2 = if ($qtd -eq $null) { '' } else { $qtd }

    $ws.Range('M3').Value2 = [string]$v.PLANO_CORTE

    $dtEnd = To-OADate ([string]$v.DATA_CONCLUSAO)
    $dtIni = To-OADate ([string]$v.DATA_INICIO)
    $ws.Range('N3').Value2 = if ($dtEnd -eq $null) { '' } else { [string]$dtEnd }
    $ws.Range('O3').Value2 = if ($dtIni -eq $null) { '' } else { [string]$dtIni }
    try { $ws.Range('N3').NumberFormatLocal = 'dd-mm-aaaa' } catch { $ws.Range('N3').NumberFormat = 'dd-mm-yyyy' }
    try { $ws.Range('O3').NumberFormatLocal = 'dd-mm-aaaa' } catch { $ws.Range('O3').NumberFormat = 'dd-mm-yyyy' }

    $ws.Range('P3').Value2 = [string]$v.ENC_PHC

    if (Test-Path -LiteralPath $OutputPath) { Remove-Item -LiteralPath $OutputPath -Force }
    $wb.SaveAs($OutputPath, 52)

    try {
      $wsCut = $wb.Worksheets.Item('LISTAGEM_CUT_RITE')
      $lo = $wsCut.ListObjects.Item('Tabela_Cut_Rite')
      $rangeAddr = $lo.Range.Address(0,0)
      $styleName = $lo.TableStyle
      $formulas = @{}
      for ($i = 1; $i -le $lo.ListColumns.Count; $i++) {
        $col = $lo.ListColumns.Item($i)
        $colName = [string]$col.Name
        $f = $null
        try {
          if ($col.DataBodyRange -ne $null) {
            $val = $col.DataBodyRange.Formula
            if ($val -is [System.Array]) { $f = $val.GetValue(1,1) } else { $f = $val }
          }
        } catch { }
        if ($f -ne $null -and [string]$f -ne '') { $formulas[$colName] = [string]$f }
        [Runtime.InteropServices.Marshal]::ReleaseComObject($col) | Out-Null
      }

      $lo.Unlist() | Out-Null
      [Runtime.InteropServices.Marshal]::ReleaseComObject($lo) | Out-Null

      $newLo = $wsCut.ListObjects.Add(1, $wsCut.Range($rangeAddr), $null, 1)
      $newLo.Name = 'Tabela_Cut_Rite'
      try { $newLo.TableStyle = $styleName } catch { }

      foreach ($k in $formulas.Keys) {
        try {
          $c = $newLo.ListColumns.Item($k)
          if ($c.DataBodyRange -ne $null) { $c.DataBodyRange.Formula = $formulas[$k] }
          [Runtime.InteropServices.Marshal]::ReleaseComObject($c) | Out-Null
        } catch { }
      }
      [Runtime.InteropServices.Marshal]::ReleaseComObject($newLo) | Out-Null
      [Runtime.InteropServices.Marshal]::ReleaseComObject($wsCut) | Out-Null

      $wb.Save() | Out-Null
    } catch { }
  } finally {
    $wb.Close($false) | Out-Null
    [Runtime.InteropServices.Marshal]::ReleaseComObject($wb) | Out-Null
  }
} finally {
  $excel.Quit() | Out-Null
  [Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
  [GC]::Collect()
  [GC]::WaitForPendingFinalizers()
}
"""


def execute_lista_material_imos(context: ListaMaterialImosContext, *, timeout_seconds: int = 240) -> Path:
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".ps1", delete=False) as tf:
            tf.write(_lista_material_imos_ps_script())
            temp_path = tf.name

        cmd = [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-STA",
            "-File",
            temp_path,
            str(context.template_path),
            str(context.output_path),
            context.values_b64,
        ]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
            creationflags=creationflags,
        )
        if result.returncode != 0:
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            detail = "\n".join([s for s in (stderr, stdout) if s])
            raise RuntimeError(detail or f"Codigo de saida: {result.returncode}")
        return context.output_path
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except Exception:
                pass


def save_processo(
    session: Session,
    *,
    current_id: Optional[int],
    data: dict,
    current_user_id: Optional[int] = None,
) -> SaveProcessoResult:
    payload = validate_processo_payload(data)

    if current_id is None:
        create_payload = dict(payload)
        processo = svc_producao.criar_processo(
            session,
            ano=create_payload.pop("ano"),
            num_enc_phc=create_payload.pop("num_enc_phc"),
            versao_obra=create_payload.pop("versao_obra"),
            versao_plano=create_payload.pop("versao_plano"),
            current_user_id=current_user_id,
            **create_payload,
        )
        return SaveProcessoResult(
            processo=processo,
            was_created=True,
            message_title="Criado",
            message_text=f"Processo criado: {processo.codigo_processo}",
        )

    processo = svc_producao.atualizar_processo(
        session,
        current_id,
        data=payload,
        current_user_id=current_user_id,
    )
    return SaveProcessoResult(
        processo=processo,
        was_created=False,
        message_title="Guardado",
        message_text=f"Processo atualizado: {processo.codigo_processo}",
    )
