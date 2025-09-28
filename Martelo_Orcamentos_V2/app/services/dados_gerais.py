from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models import (
    Client,
    DadosGeraisAcabamento,
    DadosGeraisFerragem,
    DadosGeraisMaterial,
    DadosGeraisModelo,
    DadosGeraisModeloItem,
    DadosGeraisSistemaCorrer,
    Orcamento,
    User,
)

MATERIAIS_GRUPOS: Sequence[str] = (
    "Costas",
    "Laterais",
    "Divisórias",
    "Tetos",
    "Fundos",
    "Prateleiras Fixas",
    "Prateleiras Amovíveis",
    "Prateleiras Parede",
    "Prateleiras",
    "Portas Abrir",
    "Portas Correr",
    "Painéis",
    "Laterais Acabamento",
    "Tetos Acabamento",
    "Fundos Acabamento",
    "Costas Acabamento",
    "Prateleiras Acabamento",
    "Painéis Acabamento",
    "Remates Verticais",
    "Remates Horizontais",
    "Guarnições Produzidas",
    "Enchimentos Guarnições",
    "Rodapé AGL",
    "Gaveta Frente",
    "Gaveta Caixa",
    "Gaveta Fundo",
    "Prumos",
    "Travessas",
    "Material_Livre_1",
    "Material_Livre_2",
    "Material_Livre_3",
    "Material_Livre_4",
    "Material_Livre_5",
    "Material_Livre_6",
    "Material_Livre_7",
    "Material_Livre_8",
    "Material_Livre_9",
    "Material_Livre_10",
    "Espelho",
    "Vidro",
)

LEGACY_MATERIAIS_GRUPOS: Sequence[str] = (
    "Mat_Costas",
    "Mat_Laterais",
    "Mat_Divisorias",
    "Mat_Tetos",
    "Mat_Fundos",
    "Mat_Prat_Fixas",
    "Mat_Prat_Amoviveis",
    "Mat_Portas_Abrir",
    "Mat_Laterais_Acabamento",
    "Mat_Fundos_Acabamento",
    "Mat_Costas_Acabamento",
    "Mat_Tampos_Acabamento",
    "Mat_Remates_Verticais",
    "Mat_Remates_Horizontais",
    "Mat_Guarnicoes_Verticais",
    "Mat_Guarnicoes_Horizontais",
    "Mat_Enchimentos_Guarnicao",
    "Mat_Rodape_AGL",
    "Mat_Gavetas_Frentes",
    "Mat_Gavetas_Caixa",
    "Mat_Gavetas_Fundo",
    "Mat_Livre_1",
    "Mat_Livre_2",
    "Mat_Livre_3",
    "Mat_Livre_4",
    "Mat_Livre_5",
    "Mat_Livre_6",
    "Mat_Livre_7",
    "Mat_Livre_8",
    "Mat_Livre_9",
    "Mat_Livre_10",
)

LEGACY_TO_NEW = {old: new for old, new in zip(LEGACY_MATERIAIS_GRUPOS, MATERIAIS_GRUPOS)}

MENU_MATERIAIS = "materiais"
MENU_FERRAGENS = "ferragens"
MENU_SIS_CORRER = "sistemas_correr"
MENU_ACABAMENTOS = "acabamentos"

MENU_FIELDS: Dict[str, Sequence[str]] = {
    MENU_MATERIAIS: (
        "grupo_material",
        "descricao",
        "ref_le",
        "descricao_material",
        "preco_tab",
        "preco_liq",
        "margem",
        "desconto",
        "und",
        "desp",
        "orl_0_4",
        "orl_1_0",
        "tipo",
        "familia",
        "comp_mp",
        "larg_mp",
        "esp_mp",
        "id_mp",
        "nao_stock",
        "reserva_1",
        "reserva_2",
        "reserva_3",
    ),
    MENU_FERRAGENS: (
        "categoria",
        "descricao",
        "referencia",
        "fornecedor",
        "preco_tab",
        "preco_liq",
        "margem",
        "desconto",
        "und",
        "qt",
        "nao_stock",
        "reserva_1",
        "reserva_2",
        "reserva_3",
    ),
    MENU_SIS_CORRER: (
        "categoria",
        "descricao",
        "referencia",
        "fornecedor",
        "preco_tab",
        "preco_liq",
        "margem",
        "desconto",
        "und",
        "qt",
        "nao_stock",
        "reserva_1",
        "reserva_2",
        "reserva_3",
    ),
    MENU_ACABAMENTOS: (
        "categoria",
        "descricao",
        "referencia",
        "fornecedor",
        "preco_tab",
        "preco_liq",
        "margem",
        "desconto",
        "und",
        "qt",
        "nao_stock",
        "reserva_1",
        "reserva_2",
        "reserva_3",
    ),
}

MENU_FIELD_TYPES: Dict[str, Dict[str, Sequence[str]]] = {
    MENU_MATERIAIS: {
        "money": ("preco_tab", "preco_liq"),
        "percent": ("margem", "desconto", "desp"),
        "integer": ("comp_mp", "larg_mp", "esp_mp"),
        "decimal": (),
        "bool": ("nao_stock",),
    },
    MENU_FERRAGENS: {
        "money": ("preco_tab", "preco_liq"),
        "percent": ("margem", "desconto"),
        "integer": (),
        "decimal": ("qt",),
        "bool": ("nao_stock",),
    },
    MENU_SIS_CORRER: {
        "money": ("preco_tab", "preco_liq"),
        "percent": ("margem", "desconto"),
        "integer": (),
        "decimal": ("qt",),
        "bool": ("nao_stock",),
    },
    MENU_ACABAMENTOS: {
        "money": ("preco_tab", "preco_liq"),
        "percent": ("margem", "desconto"),
        "integer": (),
        "decimal": ("qt",),
        "bool": ("nao_stock",),
    },
}

MODEL_MAP = {
    MENU_MATERIAIS: DadosGeraisMaterial,
    MENU_FERRAGENS: DadosGeraisFerragem,
    MENU_SIS_CORRER: DadosGeraisSistemaCorrer,
    MENU_ACABAMENTOS: DadosGeraisAcabamento,
}

DECIMAL_ZERO = Decimal("0")
HUNDRED = Decimal("100")


@dataclass
class DadosGeraisContext:
    orcamento_id: int
    cliente_id: int
    ano: str
    num_orcamento: str
    versao: str
    user_id: Optional[int]

    @property
    def chave(self) -> str:
        return f"{self.ano}-{self.num_orcamento}-{self.versao}"


@dataclass
class ModeloResumo:
    id: int
    nome_modelo: str
    tipo_menu: str
    created_at: Optional[str]
    linhas: int


def _normalize_grupo_material(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    return LEGACY_TO_NEW.get(value, value)


def _json_ready(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


def _value(row: Any, attr: str):
    if isinstance(row, dict):
        return row.get(attr)
    return getattr(row, attr, None)


def _ensure_decimal(value: Any) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    text_value = str(value).strip()
    if not text_value:
        return None
    text_value = text_value.replace("%", "").replace("€", "").replace(" ", "")
    text_value = text_value.replace(",", ".")
    try:
        dec = Decimal(text_value)
        return dec.quantize(Decimal("0.0001"))
    except Exception:
        return None


def _ensure_percent(value: Any) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    text_value = str(value).strip()
    if not text_value:
        return None
    text_value = text_value.replace("%", "").replace(" ", "")
    text_value = text_value.replace(",", ".")
    try:
        dec = Decimal(text_value)
    except Exception:
        return None
    if dec > 1:
        dec = dec / HUNDRED
    return dec.quantize(Decimal("0.0001"))


def calcular_preco_liq(preco_tab: Any, margem: Any, desconto: Any) -> Optional[Decimal]:
    p = _ensure_decimal(preco_tab)
    if p is None:
        return None
    m = _ensure_percent(margem) or DECIMAL_ZERO
    d = _ensure_percent(desconto) or DECIMAL_ZERO
    total = (p * (Decimal("1") - d)) * (Decimal("1") + m)
    return total.quantize(Decimal("0.0001"))


def _coerce_field(menu: str, field: str, value: Any) -> Any:
    if value in (None, ""):
        return None
    types = MENU_FIELD_TYPES[menu]
    if field in types["money"]:
        return _ensure_decimal(value)
    if field in types["percent"]:
        return _ensure_percent(value)
    if field in types["integer"]:
        try:
            return int(Decimal(str(value)))
        except Exception:
            return None
    if field in types["decimal"]:
        return _ensure_decimal(value)
    if field in types["bool"]:
        if isinstance(value, str):
            value = value.strip().lower()
            if value in ("true", "sim", "yes", "1"):
                return True
            if value in ("false", "nao", "não", "no", "0"):
                return False
        if isinstance(value, (int, float, Decimal)):
            try:
                return bool(Decimal(str(value)))
            except Exception:
                return False
        return bool(value)
    return value


def carregar_contexto(db: Session, orcamento_id: int) -> DadosGeraisContext:
    orc = db.get(Orcamento, orcamento_id)
    if not orc:
        raise ValueError("Orçamento não encontrado")
    if not orc.client_id:
        raise ValueError("Orçamento sem cliente associado")
    cliente = db.get(Client, orc.client_id)
    if not cliente:
        raise ValueError("Cliente associado não encontrado")
    user = db.get(User, orc.created_by) if orc.created_by else None
    versao = str(orc.versao or "")
    if versao.isdigit():
        versao = f"{int(versao):02d}"
    return DadosGeraisContext(
        orcamento_id=orcamento_id,
        cliente_id=cliente.id,
        ano=str(orc.ano or ""),
        num_orcamento=str(orc.num_orcamento or ""),
        versao=versao,
        user_id=getattr(user, "id", None),
    )


def _row_to_dict(menu: str, row: Any) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "id": getattr(row, "id", None),
        "ordem": getattr(row, "ordem", 0) or 0,
    }
    for field in MENU_FIELDS[menu]:
        raw = _value(row, field)
        coerced = _coerce_field(menu, field, raw)
        if menu == MENU_MATERIAIS and field == "grupo_material":
            coerced = _normalize_grupo_material(coerced)
        if menu == MENU_MATERIAIS and field == "familia":
            coerced = coerced or "PLACAS"
        result[field] = coerced
    return result


def _default_material_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for ordem, nome in enumerate(MATERIAIS_GRUPOS):
        rows.append(
            {
                "id": None,
                "ordem": ordem,
                "grupo_material": nome,
                "descricao": None,
                "ref_le": None,
                "descricao_material": None,
                "preco_tab": None,
                "preco_liq": None,
                "margem": None,
                "desconto": None,
                "und": None,
                "desp": None,
                "orl_0_4": None,
                "orl_1_0": None,
                "tipo": None,
                "familia": "PLACAS",
                "comp_mp": None,
                "larg_mp": None,
                "esp_mp": None,
                "id_mp": None,
                "nao_stock": False,
                "reserva_1": None,
                "reserva_2": None,
                "reserva_3": None,
            }
        )
    return rows


def carregar_dados_gerais(db: Session, ctx: DadosGeraisContext) -> Dict[str, List[Dict[str, Any]]]:
    data: Dict[str, List[Dict[str, Any]]] = {}
    for menu, model in MODEL_MAP.items():
        stmt = (
            select(model)
            .where(
                model.cliente_id == ctx.cliente_id,
                model.ano == ctx.ano,
                model.num_orcamento == ctx.num_orcamento,
                model.versao == ctx.versao,
            )
            .order_by(model.ordem, model.id)
        )
        rows = db.execute(stmt).scalars().all()
        data[menu] = [_row_to_dict(menu, row) for row in rows]
    if not data.get(MENU_MATERIAIS):
        data[MENU_MATERIAIS] = _default_material_rows()
    return data


def _normalize_row(menu: str, ctx: DadosGeraisContext, row: Mapping[str, Any], ordem: int) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "cliente_id": ctx.cliente_id,
        "user_id": ctx.user_id,
        "ano": ctx.ano,
        "num_orcamento": ctx.num_orcamento,
        "versao": ctx.versao,
        "ordem": ordem,
    }
    for field in MENU_FIELDS[menu]:
        value = row.get(field)
        if menu == MENU_MATERIAIS and field == "grupo_material":
            value = _normalize_grupo_material(value)
        if menu == MENU_MATERIAIS and field == "familia":
            value = value or "PLACAS"
        coerced = _coerce_field(menu, field, value)
        if menu == MENU_MATERIAIS and field == "preco_liq" and coerced is None:
            coerced = calcular_preco_liq(row.get("preco_tab"), row.get("margem"), row.get("desconto"))
        payload[field] = coerced
    if menu != MENU_MATERIAIS:
        if payload.get("preco_liq") is None:
            payload["preco_liq"] = calcular_preco_liq(row.get("preco_tab"), row.get("margem"), row.get("desconto"))
    return payload


def guardar_dados_gerais(db: Session, ctx: DadosGeraisContext, data: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
    for menu, rows in data.items():
        model = MODEL_MAP.get(menu)
        if not model:
            continue
        db.execute(
            delete(model).where(
                model.cliente_id == ctx.cliente_id,
                model.ano == ctx.ano,
                model.num_orcamento == ctx.num_orcamento,
                model.versao == ctx.versao,
            )
        )
        if not rows:
            continue
        for ordem, row in enumerate(rows):
            payload = _normalize_row(menu, ctx, row, ordem)
            db.add(model(**payload))
    db.flush()


def _prepare_model_line(menu: str, row: Mapping[str, Any], ordem: int) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {"ordem": ordem}
    for field in MENU_FIELDS[menu]:
        value = row.get(field)
        if menu == MENU_MATERIAIS and field == "grupo_material":
            value = _normalize_grupo_material(value)
        if menu == MENU_MATERIAIS and field == "familia":
            value = value or "PLACAS"
        coerced = _coerce_field(menu, field, value)
        if menu == MENU_MATERIAIS and field == "preco_liq" and coerced is None:
            coerced = calcular_preco_liq(row.get("preco_tab"), row.get("margem"), row.get("desconto"))
        sanitized[field] = _json_ready(coerced)
    return sanitized


def _deserialize_model_line(menu: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
    row: Dict[str, Any] = {"ordem": int(payload.get("ordem", 0))}
    for field in MENU_FIELDS[menu]:
        value = payload.get(field)
        coerced = _coerce_field(menu, field, value)
        if menu == MENU_MATERIAIS and field == "preco_liq" and coerced is None:
            coerced = calcular_preco_liq(payload.get("preco_tab"), payload.get("margem"), payload.get("desconto"))
        row[field] = coerced
    if menu == MENU_MATERIAIS:
        row["grupo_material"] = _normalize_grupo_material(row.get("grupo_material"))
        row["familia"] = row.get("familia") or "PLACAS"
    return row


def guardar_modelo(
    db: Session,
    *,
    user_id: int,
    tipo_menu: str,
    nome_modelo: str,
    linhas: Sequence[Mapping[str, Any]],
    replace_id: Optional[int] = None,
) -> DadosGeraisModelo:
    if tipo_menu not in MODEL_MAP:
        raise ValueError("Tipo de menu inválido")
    nome_limpo = nome_modelo.strip()
    if not nome_limpo:
        raise ValueError("Nome do modelo obrigatório")
    if replace_id:
        modelo = db.execute(
            select(DadosGeraisModelo).where(
                DadosGeraisModelo.id == replace_id,
                DadosGeraisModelo.user_id == user_id,
            )
        ).scalar_one_or_none()
        if not modelo:
            raise ValueError("Modelo não encontrado para substituir")
        modelo.nome_modelo = nome_limpo
        modelo.tipo_menu = tipo_menu
        db.execute(delete(DadosGeraisModeloItem).where(DadosGeraisModeloItem.modelo_id == modelo.id))
    else:
        modelo = DadosGeraisModelo(
            user_id=user_id,
            nome_modelo=nome_limpo,
            tipo_menu=tipo_menu,
        )
        db.add(modelo)
        db.flush()
    for ordem, linha in enumerate(linhas):
        payload = _prepare_model_line(tipo_menu, linha, ordem)
        db.add(
            DadosGeraisModeloItem(
                modelo_id=modelo.id,
                tipo_menu=tipo_menu,
                ordem=ordem,
                dados=json.dumps(payload),
            )
        )
    db.flush()
    return modelo


def listar_modelos(db: Session, *, user_id: int, tipo_menu: Optional[str] = None) -> List[DadosGeraisModelo]:
    stmt = select(DadosGeraisModelo).where(DadosGeraisModelo.user_id == user_id)
    if tipo_menu:
        stmt = stmt.where(DadosGeraisModelo.tipo_menu == tipo_menu)
    stmt = stmt.order_by(DadosGeraisModelo.created_at.desc(), DadosGeraisModelo.id.desc())
    return db.execute(stmt).scalars().all()


def carregar_modelo(db: Session, modelo_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
    stmt = select(DadosGeraisModelo).where(DadosGeraisModelo.id == modelo_id)
    if user_id is not None:
        stmt = stmt.where(DadosGeraisModelo.user_id == user_id)
    modelo = db.execute(stmt).scalar_one_or_none()
    if not modelo:
        raise ValueError("Modelo não encontrado")
    itens_stmt = (
        select(DadosGeraisModeloItem)
        .where(DadosGeraisModeloItem.modelo_id == modelo.id)
        .order_by(DadosGeraisModeloItem.ordem, DadosGeraisModeloItem.id)
    )
    itens = db.execute(itens_stmt).scalars().all()
    linhas: List[Dict[str, Any]] = []
    for item in itens:
        try:
            dados = json.loads(item.dados)
        except json.JSONDecodeError:
            dados = {}
        linhas.append(_deserialize_model_line(modelo.tipo_menu, dados))
    return {"modelo": modelo, "linhas": linhas}


def eliminar_modelo(db: Session, *, modelo_id: int, user_id: int) -> None:
    stmt = select(DadosGeraisModelo).where(
        DadosGeraisModelo.id == modelo_id,
        DadosGeraisModelo.user_id == user_id,
    )
    modelo = db.execute(stmt).scalar_one_or_none()
    if not modelo:
        raise ValueError("Modelo não encontrado")
    db.delete(modelo)
    db.flush()


def renomear_modelo(db: Session, *, modelo_id: int, user_id: int, novo_nome: str) -> DadosGeraisModelo:
    nome_limpo = novo_nome.strip()
    if not nome_limpo:
        raise ValueError("Nome do modelo obrigatório")
    stmt = select(DadosGeraisModelo).where(
        DadosGeraisModelo.id == modelo_id,
        DadosGeraisModelo.user_id == user_id,
    )
    modelo = db.execute(stmt).scalar_one_or_none()
    if not modelo:
        raise ValueError("Modelo não encontrado")
    modelo.nome_modelo = nome_limpo
    db.flush()
    return modelo
