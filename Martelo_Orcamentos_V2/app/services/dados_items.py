from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Optional, Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from Martelo_Orcamentos_V2.app.utils.bool_converter import bool_to_int, int_to_bool

from Martelo_Orcamentos_V2.app.services.bool_converter import bool_to_int, int_to_bool

from Martelo_Orcamentos_V2.app.models import (
    Client,
    Orcamento,
    OrcamentoItem,
    User,
    DadosItemsMaterial,
    DadosItemsFerragem,
    DadosItemsSistemaCorrer,
    DadosItemsAcabamento,
    DadosItemsModelo,
    DadosItemsModeloItem,
)
from Martelo_Orcamentos_V2.app.services import dados_gerais as svc_dg

MENU_MATERIAIS = svc_dg.MENU_MATERIAIS
MENU_FERRAGENS = svc_dg.MENU_FERRAGENS
MENU_SIS_CORRER = svc_dg.MENU_SIS_CORRER
MENU_ACABAMENTOS = svc_dg.MENU_ACABAMENTOS

MENU_FIXED_GROUPS = svc_dg.MENU_FIXED_GROUPS
MENU_PRIMARY_FIELD = svc_dg.MENU_PRIMARY_FIELD
MENU_DEFAULT_FAMILIA = svc_dg.MENU_DEFAULT_FAMILIA

MENU_FIELDS_BASE = svc_dg.MENU_FIELDS
MENU_FIELD_TYPES_BASE = svc_dg.MENU_FIELD_TYPES

MENU_FIELDS: Dict[str, Sequence[str]] = {
    MENU_MATERIAIS: MENU_FIELDS_BASE[MENU_MATERIAIS] + ("linha", "custo_mp_und", "custo_mp_total"),
    MENU_FERRAGENS: MENU_FIELDS_BASE[MENU_FERRAGENS] + ("linha", "spp_ml_und", "custo_mp_und", "custo_mp_total"),
    MENU_SIS_CORRER: MENU_FIELDS_BASE[MENU_SIS_CORRER] + ("linha", "custo_mp_und", "custo_mp_total"),
    MENU_ACABAMENTOS: MENU_FIELDS_BASE[MENU_ACABAMENTOS] + ("linha", "custo_acb_und", "custo_acb_total"),
}

MENU_FIELD_TYPES: Dict[str, Dict[str, Sequence[str]]] = {
    MENU_MATERIAIS: {
        **MENU_FIELD_TYPES_BASE[MENU_MATERIAIS],
        "integer": MENU_FIELD_TYPES_BASE[MENU_MATERIAIS]["integer"] + ("linha",),
        "decimal": MENU_FIELD_TYPES_BASE[MENU_MATERIAIS]["decimal"] + ("custo_mp_und", "custo_mp_total"),
    },
    MENU_FERRAGENS: {
        **MENU_FIELD_TYPES_BASE[MENU_FERRAGENS],
        "integer": MENU_FIELD_TYPES_BASE[MENU_FERRAGENS]["integer"] + ("linha",),
        "decimal": MENU_FIELD_TYPES_BASE[MENU_FERRAGENS]["decimal"] + ("spp_ml_und", "custo_mp_und", "custo_mp_total"),
    },
    MENU_SIS_CORRER: {
        **MENU_FIELD_TYPES_BASE[MENU_SIS_CORRER],
        "integer": MENU_FIELD_TYPES_BASE[MENU_SIS_CORRER]["integer"] + ("linha",),
        "decimal": MENU_FIELD_TYPES_BASE[MENU_SIS_CORRER]["decimal"] + ("custo_mp_und", "custo_mp_total"),
    },
    MENU_ACABAMENTOS: {
        **MENU_FIELD_TYPES_BASE[MENU_ACABAMENTOS],
        "integer": MENU_FIELD_TYPES_BASE[MENU_ACABAMENTOS]["integer"] + ("linha",),
        "decimal": MENU_FIELD_TYPES_BASE[MENU_ACABAMENTOS]["decimal"] + ("custo_acb_und", "custo_acb_total"),
    },
}

MODEL_MAP = {
    MENU_MATERIAIS: DadosItemsMaterial,
    MENU_FERRAGENS: DadosItemsFerragem,
    MENU_SIS_CORRER: DadosItemsSistemaCorrer,
    MENU_ACABAMENTOS: DadosItemsAcabamento,
}

MENU_KEYS = (MENU_MATERIAIS, MENU_FERRAGENS, MENU_SIS_CORRER, MENU_ACABAMENTOS)

LAYOUT_NAMESPACE = "dados_items"


@dataclass
class DadosItemsContext:
    orcamento_id: int
    item_id: int
    cliente_id: int
    user_id: Optional[int]
    ano: str
    num_orcamento: str
    versao: str
    item_ordem: Optional[int]


_DEF_ROWS_CACHE: Dict[str, List[Dict[str, Any]]] = {
    key: svc_dg._default_rows_for_menu(key)  # type: ignore[attr-defined]
    for key in MENU_KEYS
}


def carregar_contexto(db: Session, orcamento_id: int, item_id: Optional[int] = None) -> DadosItemsContext:
    if not item_id:
        raise ValueError("item_id e obrigatorio para carregar Dados Items")

    orc = db.get(Orcamento, orcamento_id)
    if not orc:
        raise ValueError("Orcamento nao encontrado")

    if orc.client_id is None:
        raise ValueError("Orcamento sem cliente associado")
    item = db.get(OrcamentoItem, item_id)
    if not item or item.id_orcamento != orcamento_id:
        raise ValueError("Item do orcamento nao encontrado")

    return DadosItemsContext(
        orcamento_id=orcamento_id,
        item_id=item_id,
        cliente_id=orc.client_id,
        user_id=item.updated_by or orc.updated_by or orc.created_by,
        ano=str(orc.ano),
        num_orcamento=str(orc.num_orcamento),
        versao=str(item.versao or orc.versao or "00"),
        item_ordem=getattr(item, "item_ord", None),
    )


def _row_to_dict(menu: str, row: Any) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "id": getattr(row, "id", None),
        "ordem": getattr(row, "ordem", 0) or 0,
    }
    fields = MENU_FIELDS[menu]
    for field in fields:
        data[field] = getattr(row, field, None)
    if "familia" in data and not data.get("familia"):
        data["familia"] = MENU_DEFAULT_FAMILIA.get(menu, "PLACAS")
    if "nao_stock" in data:
        data["nao_stock"] = bool(data.get("nao_stock"))
    return data


def _json_ready_rows(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    prepared: List[Dict[str, Any]] = []
    for row in rows:
        clean = {}
        for key, value in dict(row).items():
            if isinstance(value, Decimal):
                clean[key] = float(value)
            else:
                clean[key] = value
        prepared.append(clean)
    return prepared


def carregar_dados_gerais(db: Session, ctx: DadosItemsContext) -> Dict[str, List[Dict[str, Any]]]:
    data: Dict[str, List[Dict[str, Any]]] = {}
    for menu, model in MODEL_MAP.items():
        stmt = (
            select(model)
            .where(model.item_id == ctx.item_id)
            .order_by(model.ordem, model.id)
        )
        rows = db.execute(stmt).scalars().all()
        dict_rows = [_row_to_dict(menu, row) for row in rows]
        ensured = svc_dg._ensure_menu_rows(menu, dict_rows)  # type: ignore[attr-defined]
        data[menu] = ensured
    return data


def _coerce(menu: str, field: str, value: Any) -> Any:
    return svc_dg._coerce_field(menu, field, value)  # type: ignore[attr-defined]


def guardar_dados_gerais(db: Session, ctx: DadosItemsContext, payload: Mapping[str, Sequence[Mapping[str, Any]]]) -> None:
    """
    Guarda os dados gerais (dados items) para um item.
    - payload: dicionário com chaves por menu ('materiais', 'ferragens', ...)
      e valor = lista de dicionários (linhas).
    Estratégia:
      - imprime payload para debug,
      - apaga linhas anteriores (com delete),
      - para cada row tenta coerzir os campos com _coerce(menu, field, value)
        e se falhar aplica um fallback seguro (ex.: nao_stock -> bool(value)).
    """
    import traceback

    # DEBUG: imprimir payload recebido (só para debug; pode remover depois)
    try:
        print("[DEBUG svc guardar_dados_gerais payload] >>>")
        print(json.dumps(payload, indent=2, default=str))
        print("<<<")
    except Exception as exc:
        print("[DEBUG] Falha ao imprimir payload:", exc)

    # Percorre menus e linhas
    for menu, rows in payload.items():
        try:
            print(f"[DEBUG] Processando menu={menu!r} linhas={len(rows) if rows is not None else 0}")
        except Exception:
            # Se rows não for iterável, não dê crash no print
            print(f"[DEBUG] Processando menu={menu!r}")

        # Validar menu conhecido
        if menu not in MODEL_MAP:
            print(f"[DEBUG] menu desconhecido: {menu!r} — a ignorar")
            continue

        model = MODEL_MAP[menu]

        # Apagar linhas antigas deste item
        db.execute(delete(model).where(model.item_id == ctx.item_id))

        if not rows:
            # nada a inserir
            continue

        # Inserir cada linha (recria do zero)
        for ordem, row in enumerate(rows):
            try:
                body = dict(row)  # cópia defensiva
                body.setdefault("ordem", ordem)

                # Campos base obrigatórios para construir a instância
                instance_kwargs: Dict[str, Any] = {
                    "orcamento_id": ctx.orcamento_id,
                    "item_id": ctx.item_id,
                    "cliente_id": ctx.cliente_id,
                    "user_id": ctx.user_id,
                    "ano": ctx.ano,
                    "num_orcamento": ctx.num_orcamento,
                    "versao": ctx.versao,
                    "ordem": body.get("ordem", ordem) or ordem,
                }

                # Coerir cada field de acordo com MENU_FIELDS[menu]
                for field in MENU_FIELDS[menu]:
                    value = body.get(field)

                    # Normalizar strings vazias para None (evita coerções estranhas)
                    if isinstance(value, str) and value.strip() == "":
                        value = None

                    try:
                        # tentativa normal de coerção (pode lançar)
                        coerced = _coerce(menu, field, value)
                    except Exception as exc:
                        # Regista o erro e aplica fallback seguro
                        print(f"[ERRO] ao coerzir campo: menu={menu!r}, field={field!r}, value={value!r}")
                        traceback.print_exc()

                        # Fallbacks por campo / tipo
                        if field == "nao_stock":
                            # checkbox: forçar booleano
                            coerced = bool(value)
                        else:
                            # Tentar converter por categorias definidas (MENU_FIELD_TYPES)
                            try:
                                ftypes = MENU_FIELD_TYPES.get(menu, {}) if "MENU_FIELD_TYPES" in globals() else {}
                                if field in ftypes.get("integer", ()):
                                    coerced = int(value) if value is not None else None
                                elif field in ftypes.get("decimal", ()):
                                    # Decimal importado no topo do ficheiro
                                    coerced = Decimal(str(value)) if value is not None else None
                                else:
                                    # fallback genérico: deixa o valor tal como vem
                                    coerced = value
                            except Exception:
                                # se tudo falhar, não bloqueia a gravação: usa valor original
                                coerced = value

                    # colocar valor final nos kwargs
                    # garantir que nao_stock fica como inteiro 0/1 — evita dependências subtis do SQLAlchemy
                    if field == "nao_stock":
                        # coerced pode ser bool, 0/1 ou "0"/"1" — normalizamos para int
                        try:
                            instance_kwargs[field] = 1 if bool(coerced) else 0
                        except Exception:
                            instance_kwargs[field] = 1 if coerced else 0
                    else:
                        instance_kwargs[field] = coerced

                # Adiciona a instância à sessão
                # print de amostra para confirmarmos o que vamos inserir (só primeiras 3 linhas por menu)
                if ordem < 3:
                    print(f"[DEBUG-INSERT] menu={menu!r} ordem={ordem} id_origem={body.get('id')!r} nao_stock={instance_kwargs.get('nao_stock')!r}")
                db.add(model(**instance_kwargs))

            except Exception:
                # Se uma linha falhar, regista e continua com as outras
                print(f"[ERRO] falha ao processar linha ordem={ordem} do menu {menu!r}")
                traceback.print_exc()
                continue

    # Commitar todas as alterações no fim
    db.commit()
        # --- verificação pós-commit: ler as linhas gravadas e imprimir nao_stock ---
    from sqlalchemy import select

    for menu_name, model_cls in MODEL_MAP.items():
        try:
            stmt = select(model_cls).where(model_cls.item_id == ctx.item_id).order_by(model_cls.ordem, model_cls.id)
            saved = db.execute(stmt).scalars().all()
            print(f"[AFTER COMMIT] menu={menu_name!r} rows_saved={len(saved)}")
            # imprime só os primeiros 10 para não encher o terminal
            for r in saved[:10]:
                print(f"  id={getattr(r,'id',None)} ordem={r.ordem} nao_stock={getattr(r,'nao_stock',None)}")
        except Exception as e:
            print(f"[AFTER COMMIT] falha ao ler menu {menu_name!r}: {e}")



@dataclass
class DadosItemsModeloData:
    modelo_id: int
    nome_modelo: str
    tipo_menu: str
    dados: List[Dict[str, Any]]
    replace: bool


def listar_modelos(db: Session, orcamento_id: int, *, item_id: Optional[int] = None) -> List[DadosItemsModelo]:
    stmt = select(DadosItemsModelo).where(DadosItemsModelo.orcamento_id == orcamento_id)
    if item_id is not None:
        stmt = stmt.where((DadosItemsModelo.item_id == item_id) | (DadosItemsModelo.item_id.is_(None)))
    stmt = stmt.order_by(DadosItemsModelo.nome_modelo, DadosItemsModelo.id)
    return db.execute(stmt).scalars().all()


def carregar_modelo(db: Session, modelo_id: int) -> Dict[str, List[Dict[str, Any]]]:
    stmt = (
        select(DadosItemsModeloItem)
        .where(DadosItemsModeloItem.modelo_id == modelo_id)
        .order_by(DadosItemsModeloItem.tipo_menu, DadosItemsModeloItem.ordem, DadosItemsModeloItem.id)
    )
    items = db.execute(stmt).scalars().all()
    result: Dict[str, List[Dict[str, Any]]] = {menu: [] for menu in MENU_KEYS}
    for item in items:
        try:
            dados = json.loads(item.dados)
        except Exception:
            continue
        if isinstance(dados, list):
            result[item.tipo_menu] = dados
    return result


def guardar_modelo(
    db: Session,
    ctx: DadosItemsContext,
    nome_modelo: str,
    linhas: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    replace_model_id: Optional[int] = None,
) -> DadosItemsModelo:
    if replace_model_id:
        modelo = db.get(DadosItemsModelo, replace_model_id)
        if not modelo:
            raise ValueError("Modelo nao encontrado")
        modelo.nome_modelo = nome_modelo
        modelo.item_id = ctx.item_id
        modelo.orcamento_id = ctx.orcamento_id
        modelo.user_id = ctx.user_id
        db.execute(delete(DadosItemsModeloItem).where(DadosItemsModeloItem.modelo_id == modelo.id))
    else:
        modelo = DadosItemsModelo(
            orcamento_id=ctx.orcamento_id,
            item_id=ctx.item_id,
            user_id=ctx.user_id,
            nome_modelo=nome_modelo,
            tipo_menu=MENU_MATERIAIS,
        )
        db.add(modelo)
        db.flush()

    for menu in MENU_KEYS:
        rows = linhas.get(menu, [])
        payload = json.dumps(_json_ready_rows(rows))
        db.add(
            DadosItemsModeloItem(
                modelo_id=modelo.id,
                tipo_menu=menu,
                ordem=0,
                dados=payload,
            )
        )
    db.commit()
    db.refresh(modelo)
    return modelo


def eliminar_modelo(db: Session, modelo_id: int, *, orcamento_id: int) -> None:
    stmt = select(DadosItemsModelo).where(
        DadosItemsModelo.id == modelo_id,
        DadosItemsModelo.orcamento_id == orcamento_id,
    )
    modelo = db.execute(stmt).scalar_one_or_none()
    if not modelo:
        raise ValueError("Modelo nao encontrado")
    db.delete(modelo)
    db.commit()


def renomear_modelo(db: Session, modelo_id: int, *, orcamento_id: int, novo_nome: str) -> DadosItemsModelo:
    stmt = select(DadosItemsModelo).where(
        DadosItemsModelo.id == modelo_id,
        DadosItemsModelo.orcamento_id == orcamento_id,
    )
    modelo = db.execute(stmt).scalar_one_or_none()
    if not modelo:
        raise ValueError("Modelo nao encontrado")
    modelo.nome_modelo = novo_nome
    db.add(modelo)
    db.commit()
    db.refresh(modelo)
    return modelo
calcular_preco_liq = svc_dg.calcular_preco_liq
