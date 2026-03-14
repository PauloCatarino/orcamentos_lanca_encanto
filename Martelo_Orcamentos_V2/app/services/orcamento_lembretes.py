from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
import json
import re
import unicodedata
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from Martelo_Orcamentos_V2.app.models import Client, Orcamento
from Martelo_Orcamentos_V2.app.services import orcamento_tasks as svc_tasks
from Martelo_Orcamentos_V2.app.services.orcamentos import resolve_orcamento_cliente_nome
from Martelo_Orcamentos_V2.app.services.settings import get_setting, set_setting
from Martelo_Orcamentos_V2.app.utils.date_utils import format_date_display, parse_date_value


DATE_RE = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{2}|\d{4})\b")
CODE_ONLY_RE = re.compile(r"^[A-Z0-9_./+\-\s]+$")
REF_ONLY_RE = re.compile(r"^(?:REF\.?\s*)?[A-Z0-9.+\-_/\s]+$", re.IGNORECASE)

AUTO_SHOW_PREFIX = "daily_orcamento_summary_seen"
HIDDEN_PREFIX = "daily_orcamento_hidden"
IGNORE_EXACT_TEXTS = {
    "cliente temporario",
}
ACTION_KEYWORDS = {
    "falta": 3,
    "validar": 3,
    "retificar": 3,
    "retificar medidas": 4,
    "desenhar": 3,
    "enviar": 2,
    "pedido": 2,
    "aguarda": 2,
    "aguardar": 2,
    "confirmar": 2,
    "aprovar": 2,
    "medidas": 2,
    "ligar": 2,
    "telefonar": 2,
    "email": 2,
    "sr manuel": 2,
}


@dataclass(slots=True)
class ReminderField:
    label: str
    text: str
    score: int
    matched_keywords: list[str] = field(default_factory=list)
    mentioned_dates: list[date] = field(default_factory=list)
    actionable: bool = False
    ignored: bool = False


@dataclass(slots=True)
class OrcamentoReminder:
    orcamento_id: int
    entry_kind: str
    ano: str
    num_orcamento: str
    versao: str
    cliente: str
    estado: str
    data_orcamento: str
    descricao: str
    localizacao: str
    details_text: str
    source_fields: list[str]
    matched_keywords: list[str]
    mentioned_dates: list[date]
    latest_note_date: Optional[date]
    actionable: bool
    score: int
    priority_rank: int
    priority_label: str
    overdue: bool
    today_match: bool
    task_id: Optional[int] = None
    task_status: Optional[str] = None
    task_due_date: Optional[date] = None
    hidden: bool = False


@dataclass(slots=True)
class DailyReminderSummary:
    user_id: int
    username: str
    today: date
    total_orcamentos: int
    total_with_notes: int
    task_count: int
    legacy_count: int
    actionable_count: int
    hidden_count: int
    items: list[OrcamentoReminder]


def _normalize_match_text(text: Optional[str]) -> str:
    raw = unicodedata.normalize("NFKD", str(text or ""))
    no_accents = "".join(ch for ch in raw if not unicodedata.combining(ch))
    return " ".join(no_accents.casefold().split())


def _clean_text(text: Optional[str]) -> str:
    if text is None:
        return ""
    cleaned = str(text).replace("\r", "\n")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _parse_note_dates(text: str) -> list[date]:
    dates: list[date] = []
    for day_txt, month_txt, year_txt in DATE_RE.findall(text or ""):
        try:
            year = int(year_txt)
            if len(year_txt) == 2:
                year += 2000
            elif year < 2000 or year > 2099:
                continue
            dates.append(date(year, int(month_txt), int(day_txt)))
        except ValueError:
            continue
    unique = sorted(set(dates))
    return unique


def _looks_like_reference(text: str) -> bool:
    compact = " ".join((text or "").split())
    if not compact:
        return False
    if compact in IGNORE_EXACT_TEXTS:
        return True
    if CODE_ONLY_RE.fullmatch(compact) and "_" in compact:
        return True
    if REF_ONLY_RE.fullmatch(compact) and ("REF" in compact.upper() or "+" in compact):
        return True
    return False


def _analyze_field(label: str, text: Optional[str]) -> Optional[ReminderField]:
    cleaned = _clean_text(text)
    if not cleaned:
        return None

    normalized = _normalize_match_text(cleaned)
    mentioned_dates = _parse_note_dates(cleaned)
    matched_keywords: list[str] = []
    score = 0
    for keyword, weight in ACTION_KEYWORDS.items():
        if keyword in normalized:
            matched_keywords.append(keyword)
            score += weight

    if mentioned_dates:
        score += 2

    ignored = normalized in IGNORE_EXACT_TEXTS
    actionable = bool(matched_keywords)

    if ignored:
        actionable = False
        score = 0

    if (not actionable) and _looks_like_reference(cleaned):
        return None

    return ReminderField(
        label=label,
        text=cleaned,
        score=score,
        matched_keywords=matched_keywords,
        mentioned_dates=mentioned_dates,
        actionable=actionable,
        ignored=ignored,
    )


def _priority_for_item(score: int, actionable: bool, note_dates: list[date], today: date) -> tuple[int, str, bool, bool]:
    if not actionable:
        return 0, "Informativa", False, False

    overdue = any(d < today for d in note_dates)
    today_match = any(d == today for d in note_dates)
    if overdue or today_match or score >= 6:
        return 3, "Alta", overdue, today_match
    if score >= 3 or note_dates:
        return 2, "Media", overdue, today_match
    return 1, "Baixa", overdue, today_match


def _priority_for_task_due_date(due_date: date, today: date) -> tuple[int, str, bool, bool, int]:
    if due_date < today:
        return 3, "Alta", True, False, 8
    if due_date == today:
        return 3, "Alta", False, True, 7
    if (due_date - today).days <= 2:
        return 2, "Media", False, False, 5
    return 1, "Baixa", False, False, 3


def _compose_details(actionable_fields: list[ReminderField], fallback_fields: list[ReminderField]) -> tuple[str, list[str]]:
    chosen = actionable_fields or fallback_fields
    source_fields: list[str] = []
    details_parts: list[str] = []
    for field in chosen:
        source_fields.append(field.label)
        details_parts.append(f"{field.label}: {field.text}")
    return "\n\n".join(details_parts), source_fields


def _format_versao(value: Optional[str]) -> str:
    text = str(value or "").strip()
    if text.isdigit():
        return f"{int(text):02d}"
    return text or "01"


def _parse_orcamento_date(text: Optional[str]) -> tuple[int, date]:
    parsed = parse_date_value(text)
    return (1, parsed) if parsed is not None else (0, date.min)


def build_daily_summary(
    db: Session,
    *,
    user_id: int,
    username: str,
    today: Optional[date] = None,
    include_hidden: bool = False,
) -> DailyReminderSummary:
    today = today or date.today()
    hidden_ids = get_hidden_orcamento_ids(db, user_id=user_id)
    task_rows = svc_tasks.list_open_task_reminders(db, user_id=int(user_id))
    task_orcamento_ids = {int(row.task.orcamento_id) for row in task_rows}

    stmt = (
        select(Orcamento, Client)
        .outerjoin(Client, Orcamento.client_id == Client.id)
        .where(
            or_(
                Orcamento.created_by == int(user_id),
                (Orcamento.created_by.is_(None) & (Orcamento.updated_by == int(user_id))),
            )
        )
        .order_by(Orcamento.updated_at.desc(), Orcamento.id.desc())
    )
    rows = db.execute(stmt).all()

    reminders: list[OrcamentoReminder] = []
    total_with_notes = 0
    task_count = 0
    legacy_count = 0
    hidden_count = 0
    tracked_orcamento_ids = set(task_orcamento_ids)

    for task_row in task_rows:
        task = task_row.task
        orcamento = task_row.orcamento
        client = task_row.client
        tracked_orcamento_ids.add(int(orcamento.id))
        task_count += 1
        priority_rank, priority_label, overdue, today_match, score = _priority_for_task_due_date(task.due_date, today)
        reminders.append(
            OrcamentoReminder(
                orcamento_id=int(orcamento.id),
                entry_kind="task",
                ano=str(getattr(orcamento, "ano", "") or ""),
                num_orcamento=str(getattr(orcamento, "num_orcamento", "") or ""),
                versao=_format_versao(getattr(orcamento, "versao", None)),
                cliente=resolve_orcamento_cliente_nome(db, orcamento, client=client),
                estado=svc_tasks.TASK_STATUS_PENDING,
                data_orcamento=format_date_display(getattr(orcamento, "data", None))
                or str(getattr(orcamento, "data", "") or ""),
                descricao=_clean_text(getattr(orcamento, "descricao_orcamento", None)),
                localizacao=str(getattr(orcamento, "localizacao", "") or ""),
                details_text=str(getattr(task, "texto", "") or "").strip(),
                source_fields=["Tarefa"],
                matched_keywords=[],
                mentioned_dates=[task.due_date],
                latest_note_date=task.due_date,
                actionable=True,
                score=score,
                priority_rank=priority_rank,
                priority_label=priority_label,
                overdue=overdue,
                today_match=today_match,
                task_id=int(task.id),
                task_status=str(getattr(task, "status", svc_tasks.TASK_STATUS_PENDING) or svc_tasks.TASK_STATUS_PENDING),
                task_due_date=task.due_date,
                hidden=False,
            )
        )

    for orcamento, client in rows:
        tracked_orcamento_ids.add(int(orcamento.id))
        if int(orcamento.id) in task_orcamento_ids:
            continue
        analyzed_fields = [
            field
            for field in (
                _analyze_field("Info 1", getattr(orcamento, "info_1", None)),
                _analyze_field("Info 2", getattr(orcamento, "info_2", None)),
                _analyze_field("Notas", getattr(orcamento, "notas", None)),
            )
            if field is not None and not field.ignored
        ]
        if not analyzed_fields:
            continue

        total_with_notes += 1
        legacy_count += 1
        actionable_fields = [field for field in analyzed_fields if field.actionable]
        detail_text, source_fields = _compose_details(actionable_fields, analyzed_fields)

        matched_keywords = sorted({kw for field in actionable_fields for kw in field.matched_keywords})
        note_dates = sorted({dt for field in actionable_fields for dt in field.mentioned_dates})
        score = sum(field.score for field in actionable_fields)
        actionable = bool(actionable_fields)
        priority_rank, priority_label, overdue, today_match = _priority_for_item(score, actionable, note_dates, today)
        latest_note_date = max(note_dates) if note_dates else None
        is_hidden = int(orcamento.id) in hidden_ids
        if is_hidden:
            hidden_count += 1
        if is_hidden and not include_hidden:
            continue

        reminders.append(
            OrcamentoReminder(
                orcamento_id=int(orcamento.id),
                entry_kind="legacy",
                ano=str(getattr(orcamento, "ano", "") or ""),
                num_orcamento=str(getattr(orcamento, "num_orcamento", "") or ""),
                versao=_format_versao(getattr(orcamento, "versao", None)),
                cliente=resolve_orcamento_cliente_nome(db, orcamento, client=client),
                estado=str(getattr(orcamento, "status", "") or ""),
                data_orcamento=format_date_display(getattr(orcamento, "data", None))
                or str(getattr(orcamento, "data", "") or ""),
                descricao=_clean_text(getattr(orcamento, "descricao_orcamento", None)),
                localizacao=str(getattr(orcamento, "localizacao", "") or ""),
                details_text=detail_text,
                source_fields=source_fields,
                matched_keywords=matched_keywords,
                mentioned_dates=note_dates,
                latest_note_date=latest_note_date,
                actionable=actionable,
                score=score,
                priority_rank=priority_rank,
                priority_label=priority_label,
                overdue=overdue,
                today_match=today_match,
                hidden=is_hidden,
            )
        )

    reminders.sort(
        key=lambda item: (
            1 if item.hidden else 0,
            -item.priority_rank,
            0 if item.overdue or item.today_match else 1,
            item.latest_note_date or date.max,
            -_parse_orcamento_date(item.data_orcamento)[0],
            _parse_orcamento_date(item.data_orcamento)[1],
            -(int(item.ano) if str(item.ano).isdigit() else 0),
            -(int(item.num_orcamento) if str(item.num_orcamento).isdigit() else 0),
        )
    )

    actionable_count = sum(1 for item in reminders if item.actionable)
    return DailyReminderSummary(
        user_id=int(user_id),
        username=str(username or ""),
        today=today,
        total_orcamentos=len(tracked_orcamento_ids),
        total_with_notes=total_with_notes,
        task_count=task_count,
        legacy_count=legacy_count,
        actionable_count=actionable_count,
        hidden_count=hidden_count,
        items=reminders,
    )


def _auto_show_setting_key(user_id: int) -> str:
    return f"{AUTO_SHOW_PREFIX}_{int(user_id)}"


def _hidden_setting_key(user_id: int) -> str:
    return f"{HIDDEN_PREFIX}_{int(user_id)}"


def get_hidden_orcamento_ids(db: Session, *, user_id: int) -> set[int]:
    raw = get_setting(db, _hidden_setting_key(user_id), "[]")
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


def set_orcamento_hidden(db: Session, *, user_id: int, orcamento_id: int, hidden: bool) -> None:
    hidden_ids = get_hidden_orcamento_ids(db, user_id=user_id)
    oid = int(orcamento_id)
    if hidden:
        hidden_ids.add(oid)
    else:
        hidden_ids.discard(oid)
    payload = json.dumps(sorted(hidden_ids))
    set_setting(db, _hidden_setting_key(user_id), payload)


def should_auto_show_today(db: Session, *, user_id: int, today: Optional[date] = None) -> bool:
    current_day = (today or date.today()).isoformat()
    last_seen = get_setting(db, _auto_show_setting_key(user_id), "")
    return str(last_seen or "").strip() != current_day


def mark_auto_show_seen(db: Session, *, user_id: int, today: Optional[date] = None) -> None:
    set_setting(db, _auto_show_setting_key(user_id), (today or date.today()).isoformat())
