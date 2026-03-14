from __future__ import annotations

import datetime
import os
import shutil
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from Martelo_Orcamentos_V2.app.models import Client, Orcamento
from Martelo_Orcamentos_V2.app.services.orcamentos import create_orcamento, delete_orcamento, duplicate_orcamento_version


@dataclass(frozen=True)
class OrcamentoDuplicateMatchRow:
    id: str
    ano: str
    num_orcamento: str
    versao: str
    cliente: str
    ref_cliente: str
    data: str
    estado: str
    obra: str


@dataclass(frozen=True)
class OrcamentoSaveRequest:
    cliente_item: object
    client_id: int
    owner_user_id: Optional[int]
    ano_txt: str
    num_orcamento: str
    versao_txt: str
    ref_cliente_txt: Optional[str]
    data_value: str
    status_text: str
    enc_phc: Optional[str]
    obra: Optional[str]
    preco_val: object
    descricao_orcamento: Optional[str]
    localizacao: Optional[str]
    info_1: Optional[str]
    info_2: Optional[str]


@dataclass(frozen=True)
class OrcamentoSaveResult:
    orcamento: Orcamento
    was_new: bool
    manual_flag: bool


def find_ref_cliente_matches(db: Session, ref_cliente: Optional[str]) -> list[Orcamento]:
    ref = str(ref_cliente or "").strip()
    if not ref:
        return []
    return db.execute(select(Orcamento).where(Orcamento.ref_cliente == ref)).scalars().all()


def _format_identity(*, year_text: str, seq_text: str, version_text: str, format_version) -> tuple[str, str]:
    yy = str(year_text or "").strip()[-2:]
    seq = str(seq_text or "").strip().zfill(4)
    return f"{yy}{seq}", format_version(version_text)


def prepare_orcamento_save_request(
    *,
    cliente_item,
    consumidor_final_id: Optional[int],
    owner_user_id: Optional[int],
    year_text: str,
    seq_text: str,
    version_text: str,
    format_version,
    ref_cliente_text: str,
    data_value: str,
    status_text: str,
    enc_phc: Optional[str],
    obra: Optional[str],
    preco_val,
    descricao_orcamento: Optional[str],
    localizacao: Optional[str],
    info_1: Optional[str],
    info_2: Optional[str],
) -> OrcamentoSaveRequest:
    if not cliente_item:
        raise ValueError("Selecione um cliente.")
    if getattr(cliente_item, "is_temp", False) and not consumidor_final_id:
        raise ValueError(
            "Nao foi encontrado o cliente 'CONSUMIDOR FINAL' no PHC.\n"
            "Atualize os clientes (menu Clientes -> Atualizar PHC)."
        )
    client_id = int(getattr(cliente_item, "id", 0) or 0)
    if not client_id:
        raise ValueError("Cliente invalido.")

    ano_txt = str(year_text or "").strip()
    if len(ano_txt) != 4 or not ano_txt.isdigit():
        raise ValueError("Indique um ano valido (AAAA).")

    num_orcamento, versao_txt = _format_identity(
        year_text=ano_txt,
        seq_text=seq_text,
        version_text=version_text,
        format_version=format_version,
    )

    return OrcamentoSaveRequest(
        cliente_item=cliente_item,
        client_id=client_id,
        owner_user_id=int(owner_user_id) if owner_user_id not in (None, "") else None,
        ano_txt=ano_txt,
        num_orcamento=num_orcamento,
        versao_txt=versao_txt,
        ref_cliente_txt=str(ref_cliente_text or "").strip() or None,
        data_value=data_value,
        status_text=str(status_text or ""),
        enc_phc=enc_phc,
        obra=obra,
        preco_val=preco_val,
        descricao_orcamento=descricao_orcamento,
        localizacao=localizacao,
        info_1=info_1,
        info_2=info_2,
    )


def check_orcamento_save_conflicts(
    db: Session,
    *,
    current_id: Optional[int],
    request: OrcamentoSaveRequest,
) -> tuple[list[Orcamento], bool]:
    if current_id is not None:
        return [], False
    matches = find_ref_cliente_matches(db, request.ref_cliente_txt) if request.ref_cliente_txt else []
    exists = orcamento_identity_exists(
        db,
        ano=request.ano_txt,
        num_orcamento=request.num_orcamento,
        versao=request.versao_txt,
    )
    return matches, exists


def orcamento_identity_exists(db: Session, *, ano: str, num_orcamento: str, versao: str) -> bool:
    existing = db.execute(
        select(Orcamento.id).where(
            and_(
                Orcamento.ano == str(ano),
                Orcamento.num_orcamento == str(num_orcamento),
                Orcamento.versao == str(versao),
            )
        )
    ).scalar_one_or_none()
    return existing is not None


def load_orcamento_with_client(db: Session, orcamento_id: Optional[int]) -> tuple[Optional[Orcamento], Optional[Client]]:
    if not orcamento_id:
        return None, None

    orcamento = db.get(Orcamento, orcamento_id)
    if not orcamento:
        return None, None

    client = db.get(Client, getattr(orcamento, "client_id", None)) if getattr(orcamento, "client_id", None) else None
    return orcamento, client


def build_ref_cliente_match_rows(db: Session, matches: list[Orcamento]) -> list[OrcamentoDuplicateMatchRow]:
    rows: list[OrcamentoDuplicateMatchRow] = []
    for row in matches:
        client = db.get(Client, getattr(row, "client_id", None)) if getattr(row, "client_id", None) else None
        cliente_nome = str(getattr(client, "nome", None) or getattr(row, "cliente_nome", None) or "").strip()
        rows.append(
            OrcamentoDuplicateMatchRow(
                id=str(getattr(row, "id", None) or ""),
                ano=str(getattr(row, "ano", None) or ""),
                num_orcamento=str(getattr(row, "num_orcamento", None) or ""),
                versao=str(getattr(row, "versao", None) or ""),
                cliente=cliente_nome,
                ref_cliente=str(getattr(row, "ref_cliente", None) or ""),
                data=str(getattr(row, "data", None) or ""),
                estado=str(getattr(row, "status", None) or ""),
                obra=str(getattr(row, "obra", None) or ""),
            )
        )
    return rows


def delete_orcamento_record(db: Session, orcamento_id: int) -> None:
    delete_orcamento(db, orcamento_id)


def duplicate_orcamento_record(db: Session, orcamento_id: int, *, created_by: Optional[int] = None) -> Orcamento:
    return duplicate_orcamento_version(db, orcamento_id, created_by=created_by)


def build_orcamento_version_dir(
    *,
    base_path: str,
    ano,
    num_orc,
    simplex: str,
    versao,
    format_version,
) -> str:
    yy_path = os.path.join(str(base_path), str(ano))
    pasta = f"{num_orc}_{simplex}"
    ver_dir = format_version(versao)
    return os.path.join(yy_path, pasta, ver_dir)


def list_candidate_orcamento_dirs(*, yy_path: str, num_orc, expected_dir: str) -> list[str]:
    candidates: list[str] = []
    if os.path.isdir(expected_dir):
        candidates.append(expected_dir)
        return candidates
    prefix = f"{num_orc}_"
    try:
        with os.scandir(yy_path) as entries:
            for entry in entries:
                if entry.is_dir() and entry.name.startswith(prefix):
                    candidates.append(entry.path)
    except Exception:
        return candidates
    return candidates


def find_existing_orcamento_folder(
    *,
    base_path: str,
    ano,
    num_orc,
    simplex: str,
    versao,
    format_version,
) -> Optional[str]:
    if not (base_path and ano and num_orc):
        return None

    yy_path = os.path.join(str(base_path), str(ano))
    if not os.path.isdir(yy_path):
        return None

    expected_dir = os.path.join(yy_path, f"{num_orc}_{simplex}")
    ver_dir = format_version(versao)
    alt_ver = str(versao or "").strip()

    if os.path.isdir(expected_dir):
        dir_ver = os.path.join(expected_dir, ver_dir)
        alt_dir_ver = os.path.join(expected_dir, alt_ver) if alt_ver else ""
        if os.path.isdir(dir_ver):
            return dir_ver
        if alt_dir_ver and os.path.isdir(alt_dir_ver):
            return alt_dir_ver
        return expected_dir

    prefix = f"{num_orc}_"
    fallback_base = None
    try:
        with os.scandir(yy_path) as entries:
            for entry in entries:
                if not (entry.is_dir() and entry.name.startswith(prefix)):
                    continue
                base_dir = entry.path
                dir_ver = os.path.join(base_dir, ver_dir)
                alt_dir_ver = os.path.join(base_dir, alt_ver) if alt_ver else ""
                if os.path.isdir(dir_ver):
                    return dir_ver
                if alt_dir_ver and os.path.isdir(alt_dir_ver):
                    return alt_dir_ver
                fallback_base = fallback_base or base_dir
    except Exception:
        return None

    if fallback_base and os.path.isdir(fallback_base):
        return fallback_base
    return None


def create_orcamento_folder(
    *,
    base_path: str,
    ano,
    num_orc,
    simplex: str,
    versao,
    format_version,
) -> str:
    dir_ver = build_orcamento_version_dir(
        base_path=base_path,
        ano=ano,
        num_orc=num_orc,
        simplex=simplex,
        versao=versao,
        format_version=format_version,
    )
    os.makedirs(dir_ver, exist_ok=True)
    return dir_ver


def delete_orcamento_folders(
    *,
    base_path: str,
    ano,
    num_orc,
    simplex: str,
    versao,
    format_version,
) -> list[str]:
    yy_path = os.path.join(str(base_path), str(ano))
    expected_dir = os.path.join(yy_path, f"{num_orc}_{simplex}")
    candidate_orc_dirs = list_candidate_orcamento_dirs(
        yy_path=yy_path,
        num_orc=num_orc,
        expected_dir=expected_dir,
    )

    removed: list[str] = []
    ver_dir = format_version(versao)
    alt_ver = str(versao or "").strip()
    for base_dir in dict.fromkeys(candidate_orc_dirs):
        removed_any = False
        for path in dict.fromkeys([os.path.join(base_dir, ver_dir), os.path.join(base_dir, alt_ver) if alt_ver else ""]):
            if not path:
                continue
            if os.path.isdir(path):
                shutil.rmtree(path)
                removed.append(path)
                removed_any = True
        if removed_any:
            try:
                if os.path.isdir(base_dir) and not os.listdir(base_dir):
                    os.rmdir(base_dir)
            except Exception:
                pass
    return removed


def get_or_create_orcamento_target(
    db: Session,
    *,
    current_id: Optional[int],
    ano: str,
    num_orcamento: str,
    versao: str,
    cliente_item,
    client_id: int,
    created_by: Optional[int],
    owner_user_id: Optional[int],
) -> tuple[Orcamento, bool]:
    if current_id is None:
        created = create_orcamento(
            db,
            ano=ano,
            num_orcamento=num_orcamento,
            versao=versao,
            cliente_nome=getattr(cliente_item, "nome", ""),
            client_id=client_id,
            created_by=owner_user_id if owner_user_id is not None else created_by,
        )
        created.client_id = client_id
        return created, True

    existing = db.get(Orcamento, current_id)
    if not existing:
        raise ValueError("Registo nao encontrado.")
    existing.client_id = client_id
    if owner_user_id is not None:
        existing.created_by = owner_user_id
    return existing, False


def _determine_manual_price_flag(*, is_new: bool, preco_val, preco_manual_changed: bool, existing_manual_flag: bool) -> bool:
    if is_new:
        return preco_val is not None
    if preco_manual_changed:
        return True
    return bool(existing_manual_flag)


def _merge_orcamento_extras(
    extras,
    *,
    manual_flag: bool,
    cliente_item,
    preco_manual_key: str,
    temp_client_id_key: str,
    temp_client_name_key: str,
) -> dict | None:
    data = dict(extras or {})
    if manual_flag:
        data[preco_manual_key] = True
    else:
        data.pop(preco_manual_key, None)

    if getattr(cliente_item, "is_temp", False):
        if getattr(cliente_item, "temp_id", None) is not None:
            data[temp_client_id_key] = cliente_item.temp_id
        else:
            data.pop(temp_client_id_key, None)
        data[temp_client_name_key] = getattr(cliente_item, "nome", None)
    else:
        data.pop(temp_client_id_key, None)
        data.pop(temp_client_name_key, None)
    return data or None


def save_orcamento_request(
    db: Session,
    *,
    current_id: Optional[int],
    request: OrcamentoSaveRequest,
    created_by: Optional[int],
    preco_manual_changed: bool,
    existing_manual_flag: bool,
    existing_extras,
    preco_manual_key: str,
    temp_client_id_key: str,
    temp_client_name_key: str,
    updated_at: Optional[datetime.datetime] = None,
) -> OrcamentoSaveResult:
    orcamento, was_new = get_or_create_orcamento_target(
        db,
        current_id=current_id,
        ano=request.ano_txt,
        num_orcamento=request.num_orcamento,
        versao=request.versao_txt,
        cliente_item=request.cliente_item,
        client_id=request.client_id,
        created_by=created_by,
        owner_user_id=request.owner_user_id,
    )
    manual_flag = _determine_manual_price_flag(
        is_new=was_new,
        preco_val=request.preco_val,
        preco_manual_changed=preco_manual_changed,
        existing_manual_flag=existing_manual_flag,
    )
    extras = _merge_orcamento_extras(
        existing_extras,
        manual_flag=manual_flag,
        cliente_item=request.cliente_item,
        preco_manual_key=preco_manual_key,
        temp_client_id_key=temp_client_id_key,
        temp_client_name_key=temp_client_name_key,
    )
    apply_orcamento_form_updates(
        orcamento,
        data_value=request.data_value,
        status=request.status_text,
        enc_phc=request.enc_phc,
        ref_cliente=request.ref_cliente_txt,
        obra=request.obra,
        preco_total=request.preco_val,
        manual_flag=manual_flag,
        extras=extras,
        descricao_orcamento=request.descricao_orcamento,
        localizacao=request.localizacao,
        info_1=request.info_1,
        info_2=request.info_2,
        updated_by=created_by,
        updated_at=updated_at,
    )
    return OrcamentoSaveResult(
        orcamento=orcamento,
        was_new=was_new,
        manual_flag=manual_flag,
    )


def apply_orcamento_form_updates(
    orcamento: Orcamento,
    *,
    data_value: str,
    status: str,
    enc_phc: Optional[str],
    ref_cliente: Optional[str],
    obra: Optional[str],
    preco_total,
    manual_flag: bool,
    extras,
    descricao_orcamento: Optional[str],
    localizacao: Optional[str],
    info_1: Optional[str],
    info_2: Optional[str],
    updated_by: Optional[int] = None,
    updated_at: Optional[datetime.datetime] = None,
) -> Orcamento:
    orcamento.data = data_value
    orcamento.status = status
    orcamento.enc_phc = enc_phc
    orcamento.ref_cliente = ref_cliente
    orcamento.obra = obra
    orcamento.preco_total = preco_total
    orcamento.preco_total_manual = 1 if manual_flag else 0
    orcamento.preco_atualizado_em = updated_at or datetime.datetime.now()
    orcamento.extras = extras
    orcamento.descricao_orcamento = descricao_orcamento
    orcamento.localizacao = localizacao
    orcamento.info_1 = info_1
    orcamento.info_2 = info_2
    if updated_by is not None:
        orcamento.updated_by = updated_by
    return orcamento
