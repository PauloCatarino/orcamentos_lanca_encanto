from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from Martelo_Orcamentos_V2.app.models import Client, Orcamento, OrcamentoTask
from Martelo_Orcamentos_V2.app.models.user import User
from Martelo_Orcamentos_V2.app.utils.date_utils import format_date_display, parse_date_value


TASK_STATUS_PENDING = "Pendente"
TASK_STATUS_COMPLETED = "Concluida"
TASK_STATUS_SUSPENDED = "Suspensa"

TASK_STATUS_VALUES = (
    TASK_STATUS_PENDING,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_SUSPENDED,
)


@dataclass(frozen=True)
class UserChoice:
    id: int
    username: str


@dataclass(frozen=True)
class OrcamentoTaskRow:
    id: int
    orcamento_id: int
    texto: str
    assigned_user_id: Optional[int]
    assigned_username: str
    due_date: date
    due_date_text: str
    status: str
    created_at_text: str
    updated_at_text: str
    overdue: bool
    due_today: bool


@dataclass(frozen=True)
class OrcamentoTaskReminderRow:
    task: OrcamentoTask
    orcamento: Orcamento
    client: Optional[Client]
    assigned_username: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_status(value: str) -> str:
    text = str(value or "").strip().casefold()
    if text == TASK_STATUS_PENDING.casefold():
        return TASK_STATUS_PENDING
    if text == TASK_STATUS_COMPLETED.casefold():
        return TASK_STATUS_COMPLETED
    if text == TASK_STATUS_SUSPENDED.casefold():
        return TASK_STATUS_SUSPENDED
    raise ValueError("Estado de tarefa invalido.")


def _require_orcamento(db: Session, orcamento_id: int) -> Orcamento:
    orcamento = db.get(Orcamento, int(orcamento_id))
    if not orcamento:
        raise ValueError("Orcamento nao encontrado.")
    return orcamento


def _require_user(db: Session, user_id: Optional[int]) -> Optional[User]:
    if user_id in (None, ""):
        return None
    user = db.get(User, int(user_id))
    if not user:
        raise ValueError("Utilizador da tarefa nao encontrado.")
    return user


def _normalize_task_payload(
    *,
    texto: str,
    assigned_user_id: Optional[int],
    due_date,
    status: str,
) -> tuple[str, Optional[int], date, str]:
    text = " ".join(str(texto or "").split())
    if not text:
        raise ValueError("Indique o texto da tarefa.")

    parsed_due = parse_date_value(due_date)
    if parsed_due is None:
        raise ValueError("Indique uma data limite valida.")

    normalized_status = _normalize_status(status)
    if assigned_user_id in (None, ""):
        raise ValueError("Selecione o utilizador responsavel pela tarefa.")
    user_id = int(assigned_user_id)
    return text, user_id, parsed_due, normalized_status


def list_active_user_choices(db: Session) -> list[UserChoice]:
    users = (
        db.query(User)
        .filter(User.is_active == True)  # noqa: E712
        .order_by(User.username)
        .all()
    )
    choices: list[UserChoice] = []
    for user in users:
        username = str(getattr(user, "username", "") or "").strip()
        if username:
            choices.append(UserChoice(id=int(user.id), username=username))
    return choices


def list_orcamento_task_rows(db: Session, *, orcamento_id: int, include_closed: bool = True) -> list[OrcamentoTaskRow]:
    stmt = (
        select(OrcamentoTask, User)
        .outerjoin(User, OrcamentoTask.assigned_user_id == User.id)
        .where(OrcamentoTask.orcamento_id == int(orcamento_id))
        .order_by(OrcamentoTask.due_date.asc(), OrcamentoTask.updated_at.desc(), OrcamentoTask.id.desc())
    )
    rows = db.execute(stmt).all()
    today = date.today()
    task_rows: list[OrcamentoTaskRow] = []
    for task, user in rows:
        status = _normalize_status(getattr(task, "status", TASK_STATUS_PENDING))
        if (not include_closed) and status != TASK_STATUS_PENDING:
            continue
        due = getattr(task, "due_date", None) or today
        updated_at = getattr(task, "updated_at", None)
        created_at = getattr(task, "created_at", None)
        task_rows.append(
            OrcamentoTaskRow(
                id=int(task.id),
                orcamento_id=int(task.orcamento_id),
                texto=str(getattr(task, "texto", "") or "").strip(),
                assigned_user_id=int(user.id) if user and getattr(user, "id", None) is not None else None,
                assigned_username=str(getattr(user, "username", "") or "").strip(),
                due_date=due,
                due_date_text=format_date_display(due),
                status=status,
                created_at_text=created_at.strftime("%d-%m-%Y %H:%M") if isinstance(created_at, datetime) else "",
                updated_at_text=updated_at.strftime("%d-%m-%Y %H:%M") if isinstance(updated_at, datetime) else "",
                overdue=due < today and status == TASK_STATUS_PENDING,
                due_today=due == today and status == TASK_STATUS_PENDING,
            )
        )
    return task_rows


def create_orcamento_task(
    db: Session,
    *,
    orcamento_id: int,
    texto: str,
    assigned_user_id: Optional[int],
    due_date,
    created_by: Optional[int],
    status: str = TASK_STATUS_PENDING,
) -> OrcamentoTask:
    _require_orcamento(db, orcamento_id)
    text, user_id, parsed_due, normalized_status = _normalize_task_payload(
        texto=texto,
        assigned_user_id=assigned_user_id,
        due_date=due_date,
        status=status,
    )
    _require_user(db, user_id)
    task = OrcamentoTask(
        orcamento_id=int(orcamento_id),
        texto=text,
        assigned_user_id=user_id,
        due_date=parsed_due,
        status=normalized_status,
        created_by=created_by,
        updated_by=created_by,
        completed_at=_utc_now() if normalized_status == TASK_STATUS_COMPLETED else None,
    )
    db.add(task)
    db.flush()
    return task


def update_orcamento_task(
    db: Session,
    *,
    task_id: int,
    texto: str,
    assigned_user_id: Optional[int],
    due_date,
    status: str,
    updated_by: Optional[int],
) -> OrcamentoTask:
    task = db.get(OrcamentoTask, int(task_id))
    if not task:
        raise ValueError("Tarefa nao encontrada.")
    text, user_id, parsed_due, normalized_status = _normalize_task_payload(
        texto=texto,
        assigned_user_id=assigned_user_id,
        due_date=due_date,
        status=status,
    )
    _require_user(db, user_id)
    task.texto = text
    task.assigned_user_id = user_id
    task.due_date = parsed_due
    task.status = normalized_status
    task.updated_by = updated_by
    task.completed_at = _utc_now() if normalized_status == TASK_STATUS_COMPLETED else None
    db.flush()
    return task


def set_orcamento_task_status(
    db: Session,
    *,
    task_id: int,
    status: str,
    updated_by: Optional[int],
) -> OrcamentoTask:
    task = db.get(OrcamentoTask, int(task_id))
    if not task:
        raise ValueError("Tarefa nao encontrada.")
    normalized_status = _normalize_status(status)
    task.status = normalized_status
    task.updated_by = updated_by
    task.completed_at = _utc_now() if normalized_status == TASK_STATUS_COMPLETED else None
    db.flush()
    return task


def delete_orcamento_task(db: Session, *, task_id: int) -> None:
    task = db.get(OrcamentoTask, int(task_id))
    if not task:
        raise ValueError("Tarefa nao encontrada.")
    db.delete(task)
    db.flush()


def list_open_task_reminders(db: Session, *, user_id: int) -> list[OrcamentoTaskReminderRow]:
    stmt = (
        select(OrcamentoTask, Orcamento, Client, User)
        .join(Orcamento, OrcamentoTask.orcamento_id == Orcamento.id)
        .outerjoin(Client, Orcamento.client_id == Client.id)
        .outerjoin(User, OrcamentoTask.assigned_user_id == User.id)
        .where(
            OrcamentoTask.assigned_user_id == int(user_id),
            OrcamentoTask.status == TASK_STATUS_PENDING,
        )
        .order_by(OrcamentoTask.due_date.asc(), OrcamentoTask.updated_at.desc(), OrcamentoTask.id.desc())
    )
    rows = db.execute(stmt).all()
    reminders: list[OrcamentoTaskReminderRow] = []
    for task, orcamento, client, user in rows:
        reminders.append(
            OrcamentoTaskReminderRow(
                task=task,
                orcamento=orcamento,
                client=client,
                assigned_username=str(getattr(user, "username", "") or "").strip(),
            )
        )
    return reminders
