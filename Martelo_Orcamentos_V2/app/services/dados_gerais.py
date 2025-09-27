from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence

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
)

LEGACY_TO_NEW = {old: new for old, new in zip(LEGACY_MATERIAIS_GRUPOS, MATERIAIS_GRUPOS)}


def _normalize_grupo_material(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    return LEGACY_TO_NEW.get(value, value)



MENU_MATERIAIS = "materiais"
MENU_FERRAGENS = "ferragens"
MENU_SIS_CORRER = "sistemas_correr"
MENU_ACABAMENTOS = "acabamentos"

MODEL_MAP = {
    MENU_MATERIAIS: DadosGeraisMaterial,
    MENU_FERRAGENS: DadosGeraisFerragem,
    MENU_SIS_CORRER: DadosGeraisSistemaCorrer,
    MENU_ACABAMENTOS: DadosGeraisAcabamento,
}

DECIMAL_ZERO = Decimal("0")


def _json_ready(value: Any):
    if isinstance(value, Decimal):
        return float(value)
    return value


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_decimal(value: Any, *, scale: int = 4) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    if isinstance(value, Decimal):
        return value.quantize(Decimal(10) ** -scale)
    try:
        text = str(value).strip().replace("%", "").replace("€", "").replace(",", ".")
        if not text:
            return None
        dec = Decimal(text)
        return dec.quantize(Decimal(10) ** -scale)
    except Exception:
        return None


def _ensure_percent(value: Any) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    if isinstance(value, Decimal):
        return value
    text = str(value).strip().replace("%", "")
    if not text:
        return None
    text = text.replace(",", ".")
    try:
        dec = Decimal(text)
    except Exception:
        return None
    if dec > 1:
        dec = dec / Decimal("100")
    return dec.quantize(Decimal("0.0001"))


def calcular_preco_liq(preco_tab: Any, margem: Any, desconto: Any) -> Optional[Decimal]:
    p = _ensure_decimal(preco_tab)
    m = _ensure_percent(margem) or DECIMAL_ZERO
    d = _ensure_percent(desconto) or DECIMAL_ZERO
    if p is None:
        return None
    try:
        total = (p * (Decimal("1") - d)) * (Decimal("1") + m)
        return total.quantize(Decimal("0.0001"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------

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
    return DadosGeraisContext(
        orcamento_id=orcamento_id,
        cliente_id=cliente.id,
        ano=str(orc.ano or ""),
        num_orcamento=str(orc.num_orcamento or ""),
        versao=f"{int(orc.versao):02d}" if str(orc.versao or "").isdigit() else str(orc.versao or ""),
        user_id=getattr(user, "id", None),
    )


# ---------------------------------------------------------------------------
# Load / Save
# ---------------------------------------------------------------------------

def _rows_to_dict(rows: Iterable[Any], *, menu: str) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for row in rows:
        payload: Dict[str, Any] = {
            "id": getattr(row, "id", None),
            "ordem": getattr(row, "ordem", 0) or 0,
        }
        if menu == MENU_MATERIAIS:
            preco_tab = _ensure_decimal(row.get("preco_tab"))
            margem = _ensure_percent(row.get("margem"))
            desconto = _ensure_percent(row.get("desconto"))
            preco_liq = _ensure_decimal(row.get("preco_liq"))
            if preco_liq is None:
                preco_liq = calcular_preco_liq(preco_tab, margem, desconto)
            payload.update(
                {
                    "grupo_material": _normalize_grupo_material(row.get("grupo_material")),
                    "descricao": row.get("descricao"),
                    "ref_le": row.get("ref_le"),
                    "descricao_material": row.get("descricao_material"),
                    "preco_tab": preco_tab,
                    "preco_liq": preco_liq,
                    "margem": margem,
                    "desconto": desconto,
                    "und": row.get("und"),
                    "desp": _ensure_percent(row.get("desp")),
                    "orl_0_4": row.get("orl_0_4"),
                    "orl_1_0": row.get("orl_1_0"),
                    "tipo": row.get("tipo"),
                    "familia": row.get("familia") or "PLACAS",
                    "comp_mp": row.get("comp_mp") or None,
                    "larg_mp": row.get("larg_mp") or None,
                    "esp_mp": row.get("esp_mp") or None,
                    "id_mp": row.get("id_mp"),
                    "nao_stock": bool(row.get("nao_stock")),
                    "reserva_1": row.get("reserva_1"),
                    "reserva_2": row.get("reserva_2"),
                    "reserva_3": row.get("reserva_3"),
                }
            )
        else:
            payload.update(
                {
                    "categoria": getattr(row, "categoria", None),
                    "descricao": getattr(row, "descricao", None),
                    "referencia": getattr(row, "referencia", None),
                    "fornecedor": getattr(row, "fornecedor", None),
                    "preco_tab": getattr(row, "preco_tab", None),
                    "preco_liq": getattr(row, "preco_liq", None),
                    "margem": getattr(row, "margem", None),
                    "desconto": getattr(row, "desconto", None),
                    "und": getattr(row, "und", None),
                    "qt": getattr(row, "qt", None),
                    "nao_stock": bool(getattr(row, "nao_stock", False)),
                    "reserva_1": getattr(row, "reserva_1", None),
                    "reserva_2": getattr(row, "reserva_2", None),
                    "reserva_3": getattr(row, "reserva_3", None),
                }
            )
        result.append(payload)
    result.sort(key=lambda item: item.get("ordem", 0))
    return result


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
        data[menu] = _rows_to_dict(rows, menu=menu)
    if not data[MENU_MATERIAIS]:
        data[MENU_MATERIAIS] = [
            {
                "id": None,
                "ordem": idx,
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
            for idx, nome in enumerate(MATERIAIS_GRUPOS)
        ]
    return data


def _normalize_row(menu: str, ctx: DadosGeraisContext, row: Mapping[str, Any], order: int) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "cliente_id": ctx.cliente_id,
        "user_id": ctx.user_id,
        "ano": ctx.ano,
        "num_orcamento": ctx.num_orcamento,
        "versao": ctx.versao,
        "ordem": order,
    }
    if menu == MENU_MATERIAIS:
        preco_tab = _ensure_decimal(row.get("preco_tab"))
        margem = _ensure_percent(row.get("margem"))
        desconto = _ensure_percent(row.get("desconto"))
        preco_liq = _ensure_decimal(row.get("preco_liq"))
        if preco_liq is None:
            preco_liq = calcular_preco_liq(preco_tab, margem, desconto)
        payload.update(
            {
                "grupo_material": row.get("grupo_material"),
                "descricao": row.get("descricao"),
                "ref_le": row.get("ref_le"),
                "descricao_material": row.get("descricao_material"),
                "preco_tab": preco_tab,
                "preco_liq": preco_liq,
                "margem": margem,
                "desconto": desconto,
                "und": row.get("und"),
                "desp": _ensure_percent(row.get("desp")),
                "orl_0_4": row.get("orl_0_4"),
                "orl_1_0": row.get("orl_1_0"),
                "tipo": row.get("tipo"),
                "familia": row.get("familia"),
                "comp_mp": row.get("comp_mp") or None,
                "larg_mp": row.get("larg_mp") or None,
                "esp_mp": row.get("esp_mp") or None,
                "id_mp": row.get("id_mp"),
                "nao_stock": bool(row.get("nao_stock")),
                "reserva_1": row.get("reserva_1"),
                "reserva_2": row.get("reserva_2"),
                "reserva_3": row.get("reserva_3"),
            }
        )
    else:
        preco_tab = _ensure_decimal(row.get("preco_tab"))
        margem = _ensure_percent(row.get("margem"))
        desconto = _ensure_percent(row.get("desconto"))
        preco_liq = _ensure_decimal(row.get("preco_liq"))
        if preco_liq is None:
            preco_liq = calcular_preco_liq(preco_tab, margem, desconto)
        payload.update(
            {
                "categoria": row.get("categoria"),
                "descricao": row.get("descricao"),
                "referencia": row.get("referencia"),
                "fornecedor": row.get("fornecedor"),
                "preco_tab": preco_tab,
                "preco_liq": preco_liq,
                "margem": margem,
                "desconto": desconto,
                "und": row.get("und"),
                "qt": _ensure_decimal(row.get("qt")),
                "nao_stock": bool(row.get("nao_stock")),
                "reserva_1": row.get("reserva_1"),
                "reserva_2": row.get("reserva_2"),
                "reserva_3": row.get("reserva_3"),
            }
        )
    return payload


def guardar_dados_gerais(db: Session, ctx: DadosGeraisContext, data: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
    for menu, rows in data.items():
        model = MODEL_MAP.get(menu)
        if not model:
            continue
        # limpa registos existentes
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
        for order, row in enumerate(rows):
            payload = _normalize_row(menu, ctx, row, order)
            record = model(**payload)
            db.add(record)
    db.flush()


# ---------------------------------------------------------------------------
# Modelos por utilizador
# ---------------------------------------------------------------------------

def guardar_modelo(
    db: Session,
    *,
    user_id: int,
    tipo_menu: str,
    nome_modelo: str,
    linhas: Sequence[Mapping[str, Any]],
) -> DadosGeraisModelo:
    if tipo_menu not in MODEL_MAP:
        raise ValueError("Tipo de menu inválido")
    if not nome_modelo.strip():
        raise ValueError("Nome do modelo obrigatório")
    modelo = DadosGeraisModelo(
        user_id=user_id,
        nome_modelo=nome_modelo.strip(),
        tipo_menu=tipo_menu,
    )
    db.add(modelo)
    db.flush()
    for ordem, linha in enumerate(linhas):
        serializado = {chave: _json_ready(valor) for chave, valor in dict(linha).items()}
        db.add(
            DadosGeraisModeloItem(
                modelo_id=modelo.id,
                tipo_menu=tipo_menu,
                ordem=ordem,
                dados=json.dumps(serializado),
            )
        )
    db.flush()
    return modelo


def listar_modelos(db: Session, *, user_id: int, tipo_menu: Optional[str] = None) -> List[DadosGeraisModelo]:
    stmt = select(DadosGeraisModelo).where(DadosGeraisModelo.user_id == user_id)
    if tipo_menu:
        stmt = stmt.where(DadosGeraisModelo.tipo_menu == tipo_menu)
    stmt = stmt.order_by(DadosGeraisModelo.created_at.desc())
    return db.execute(stmt).scalars().all()


def carregar_modelo(db: Session, modelo_id: int) -> Dict[str, Any]:
    modelo = db.get(DadosGeraisModelo, modelo_id)
    if not modelo:
        raise ValueError("Modelo não encontrado")
    itens_stmt = (
        select(DadosGeraisModeloItem)
        .where(DadosGeraisModeloItem.modelo_id == modelo_id)
        .order_by(DadosGeraisModeloItem.ordem, DadosGeraisModeloItem.id)
    )
    itens = db.execute(itens_stmt).scalars().all()
    linhas: List[Dict[str, Any]] = []
    for item in itens:
        try:
            data = json.loads(item.dados)
        except json.JSONDecodeError:
            data = {}
        linhas.append(data)
    return {
        "modelo": modelo,
        "linhas": linhas,
    }


