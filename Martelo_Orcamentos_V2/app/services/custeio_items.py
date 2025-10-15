from __future__ import annotations

from decimal import Decimal
import unicodedata
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from Martelo_Orcamentos_V2.app.models.client import Client
from Martelo_Orcamentos_V2.app.models.custeio import CusteioItem
from Martelo_Orcamentos_V2.app.models.dados_gerais import DadosItemsMaterial
from Martelo_Orcamentos_V2.app.models.materia_prima import MateriaPrima
from Martelo_Orcamentos_V2.app.models.orcamento import Orcamento, OrcamentoItem
from Martelo_Orcamentos_V2.app.models.user import User
from Martelo_Orcamentos_V2.app.services import dados_items as svc_dados_items


TreeNode = Dict[str, Any]


TREE_DEFINITION: List[TreeNode] = [
    {
        "label": "COSTAS",
        "children": [
            {"label": "COSTA CHAPAR [0000]"},
            {"label": "COSTA CHAPAR [0022]"},
            {"label": "COSTA CHAPAR [2222]"},
            {"label": "COSTA CHAPAR [1111]"},
            {"label": "COSTA REBAIXADA [0000]"},
            {"label": "COSTA PARA REBAIXO [0000]"},
        ],
    },
    {
        "label": "LATERAIS",
        "children": [
            {"label": "LATERAL [0000]"},
            {"label": "LATERAL [2000]"},
            {"label": "LATERAL [2022]"},
            {"label": "LATERAL [2222]"},
            {"label": "LATERAL [2100]"},
            {"label": "DIVISORIA [2000]"},
            {"label": "TRAVESSA [2200]"},
            {"label": "PRUMO [2200]"},
        ],
    },
    {
        "label": "TETOS",
        "children": [
            {"label": "TETO [0000]"},
            {"label": "TETO [2000]"},
            {"label": "TETO [2200]"},
            {"label": "TETO [2100]"},
            {"label": "TETO [2222]"},
            {"label": "TETO [2111]"},
        ],
    },
    {
        "label": "FUNDOS",
        "children": [
            {"label": "FUNDO [0000]"},
            {"label": "FUNDO [2000]"},
            {"label": "FUNDO [2111]"},
            {"label": "FUNDO [2222]"},
            {"label": "FUNDO [2000] + PES"},
            {"label": "FUNDO [2200] + PES"},
            {"label": "FUNDO [2222] + PES"},
            {"label": "FUNDO [2111] + PES"},
        ],
    },
    {
        "label": "PRATELEIRAS AMOVIVEIS",
        "children": [
            {"label": "PRATELEIRA AMOVIVEL [2000]"},
            {"label": "PRATELEIRA AMOVIVEL [2111]"},
            {"label": "PRATELEIRA AMOVIVEL [2222]"},
            {"label": "PRAT. AMOV. [2111] + SUPORTE PRATELEIRA"},
            {
                "label": "PRAT. AMOV. [2111] + SUPORTE PRATELEIRA + VARAO + SUPORTE VARAO",
            },
        ],
    },
    {
        "label": "PRATELEIRAS FIXAS",
        "children": [
            {"label": "PRATELEIRA FIXA [0000]"},
            {"label": "PRATELEIRA FIXA [2000]"},
            {"label": "PRATELEIRA FIXA [2111]"},
            {"label": "PRATELEIRA FIXA [2222]"},
            {"label": "PRAT. FIXA [2000] + VARAO + SUPORTE VARAO"},
        ],
    },
    {
        "label": "GAVETA FRENTE",
        "children": [
            {"label": "FRENTE GAVETA [2222]"},
            {"label": "FRENTE GAVETA [2222] + PUXADOR"},
        ],
    },
    {
        "label": "GAVETA CAIXA",
        "children": [
            {"label": "LATERAL GAVETA [2202]"},
            {"label": "TRASEIRA GAVETA [2000]"},
        ],
    },
    {
        "label": "GAVETA FUNDO",
        "children": [
            {"label": "FUNDO GAVETA [0022]"},
            {"label": "FUNDO GAVETA [0000]"},
        ],
    },
    {
        "label": "PORTAS ABRIR 1",
        "children": [
            {"label": "PORTA ABRIR [2222]"},
            {"label": "PORTA ABRIR [2222] + DOBRADICA"},
            {"label": "PORTA ABRIR [2222] + DOBRADICA + PUXADOR"},
        ],
    },
    {
        "label": "PAINEIS",
        "children": [
            {"label": "PAINEL CORRER [0000]"},
            {"label": "PAINEL CORRER [2222]"},
            {"label": "PAINEL ESPELHO [2222]"},
        ],
    },
    {
        "label": "FERRAGENS",
        "children": [
            {
                "label": "DOBRADICAS",
                "children": [
                    {"label": "DOBRADICA RETA"},
                    {"label": "DOBRADICA CANTO SEGO"},
                    {"label": "DOBRADICA ABERTURA TOTAL"},
                    {"label": "DOBRADICA 1"},
                    {"label": "DOBRADICA 2"},
                ],
            },
            {
                "label": "SUPORTES PRATELEIRA",
                "children": [
                    {"label": "SUPORTE PRATELEIRA 1"},
                    {"label": "SUPORTE PRATELEIRA 2"},
                    {"label": "SUPORTE PAREDE"},
                ],
            },
            {
                "label": "SPP (ACESSORIOS AJUSTAVEIS)",
                "children": [
                    {"label": "VARAO {SPP}"},
                    {"label": "PERFIL LAVA LOUCA {SPP}"},
                    {"label": "RODAPE PVC {SPP}"},
                    {"label": "PUXADOR GOLA C {SPP}"},
                    {"label": "PUXADOR GOLA J {SPP}"},
                    {"label": "PUXADOR PERFIL {SPP} 1"},
                    {"label": "PUXADOR PERFIL {SPP} 2"},
                    {"label": "PUXADOR PERFIL {SPP} 3"},
                    {"label": "CALHA LED {SPP} 1"},
                    {"label": "CALHA LED {SPP} 2"},
                    {"label": "FITA LED {SPP} 1"},
                    {"label": "FITA LED {SPP} 2"},
                    {"label": "FERRAGENS DIVERSAS {SPP} 6"},
                    {"label": "FERRAGENS DIVERSAS {SPP} 7"},
                    {"label": "CALHA SUPERIOR {SPP} 1 CORRER"},
                    {"label": "CALHA SUPERIOR {SPP} 2 CORRER"},
                    {"label": "CALHA INFERIOR {SPP} 1 CORRER"},
                    {"label": "CALHA INFERIOR {SPP} 2 CORRER"},
                    {"label": "PERFIL HORIZONTAL H {SPP}"},
            {"label": "PERFIL HORIZONTAL U {SPP}"},
            {"label": "PERFIL HORIZONTAL L {SPP}"},
            {"label": "ACESSORIO {SPP} 7 CORRER"},
            {"label": "ACESSORIO {SPP} 8 CORRER"},
        ],
            },
            {
                "label": "PUXADORES",
                "children": [
                    {"label": "PUXADOR TIC-TAC"},
                    {"label": "PUXADOR FRESADO J"},
                    {"label": "PUXADOR STD 1"},
                    {"label": "PUXADOR STD 2"},
                ],
            },
            {
                "label": "CORREDICAS GAVETAS",
                "children": [
                    {"label": "CORREDICA INVISIVEL"},
                    {"label": "CORREDICA LATERAL METALICA"},
                    {"label": "CORREDICA 1"},
                    {"label": "CORREDICA 2"},
                ],
            },
            {
                "label": "PES",
                "children": [
                    {"label": "PES 1"},
                    {"label": "PES 2"},
                    {"label": "PES 3"},
                ],
            },
            {
                "label": "SISTEMAS ELEVATORIOS",
                "children": [
                    {"label": "AVENTOS 1"},
                    {"label": "AVENTOS 2"},
                    {"label": "AMORTECEDOR"},
                    {"label": "SISTEMA BASCULANTE 1"},
                    {"label": "SISTEMA BASCULANTE 2"},
                ],
            },
            {
                "label": "ILUMINACAO",
                "children": [
                    {"label": "TRANSFORMADOR 1"},
                    {"label": "TRANSFORMADOR 2"},
                    {"label": "SENSOR LED 1"},
                    {"label": "SENSOR LED 2"},
                    {"label": "SENSOR LED 3"},
                    {"label": "ILUMINACAO 1"},
                    {"label": "ILUMINACAO 2"},
                    {"label": "ILUMINACAO 3"},
                    {"label": "CABOS LED 1"},
                    {"label": "CABOS LED 2"},
                    {"label": "CABOS LED 3"},
                ],
            },
            {
                "label": "COZINHAS",
                "children": [
                    {"label": "BALDE LIXO"},
                    {"label": "CESTO CANTO FEIJAO"},
                    {"label": "CESTO CANTO 1"},
                    {"label": "CESTO CANTO 2"},
                    {"label": "PORTA TALHERES"},
                    {"label": "PORTA GARRAFAS"},
                    {"label": "TULHA 1"},
                    {"label": "TULHA 2"},
                    {"label": "FUNDO ALUMINIO 1"},
                    {"label": "FUNDO ALUMINIO 2"},
                    {"label": "FUNDO PLASTICO FIGORIFICO"},
                    {"label": "SALVA SIFAO"},
                    {"label": "ACESSORIO COZINHA 1"},
                    {"label": "ACESSORIO COZINHA 2"},
                    {"label": "ACESSORIO COZINHA 3"},
                ],
            },
            {
                "label": "ROUPEIROS",
                "children": [
                    {"label": "PORTA CALCAS"},
                    {"label": "VARAO TROMBONE"},
                    {"label": "VARAO EXTENSIVEL"},
                    {"label": "GRELHA VELUDO"},
                    {"label": "SAPATEIRA"},
                ],
            },
            {
                "label": "FERRAGENS DIVERSAS {FERRAGENS}",
                "children": [
                    {"label": "FERRAGENS DIVERSAS 1"},
                    {"label": "FERRAGENS DIVERSAS 2"},
                    {"label": "FERRAGENS DIVERSAS 3"},
                    {"label": "FERRAGENS DIVERSAS 4"},
                    {"label": "FERRAGENS DIVERSAS 5"},
                ],
            },
            {
                "label": "UNIOES CANTO SPP",
                "children": [
                    {"label": "SUPORTE TERMINAL VARAO"},
                    {"label": "SUPORTE CENTRAL VARAO"},
                    {"label": "TERMINAL PERFIL LAVA LOUCA"},
                    {"label": "CANTO RODAPE PVC"},
                    {"label": "GRAMPAS RODAPE PVC"},
                ],
            },
            {
                "label": "SISTEMAS CORRER",
                "children": [
                    {"label": "PUXADOR VERTICAL 1"},
                    {"label": "PUXADOR VERTICAL 2"},
                    {"label": "RODIZIO SUPERIOR 1"},
                    {"label": "RODIZIO SUPERIOR 2"},
                    {"label": "RODIZIO INFERIOR 1"},
                    {"label": "RODIZIO INFERIOR 2"},
                ],
            },
            {
                "label": "FERRAGENS DIVERSAS {SISTEMAS CORRER}",
                "children": [
                    {"label": "ACESSORIO 1 CORRER"},
                    {"label": "ACESSORIO 2 CORRER"},
                    {"label": "ACESSORIO 3 CORRER"},
                    {"label": "ACESSORIO 4 CORRER"},
                    {"label": "ACESSORIO 5 CORRER"},
                    {"label": "ACESSORIO 6 CORRER"},
                ],
            },
        ],
    },
]


CUSTEIO_COLUMN_SPECS: List[Dict[str, Any]] = [
    {"key": "id", "label": "id", "type": "int", "editable": False},
    {"key": "descricao_livre", "label": "Descricao_Livre", "type": "text", "editable": True},
    {"key": "def_peca", "label": "Def_Peca", "type": "text", "editable": False},
    {"key": "descricao", "label": "Descricao", "type": "text", "editable": False},
    {"key": "qt_mod", "label": "QT_mod", "type": "numeric", "editable": True},
    {"key": "qt_und", "label": "QT_und", "type": "numeric", "editable": True},
    {"key": "comp", "label": "Comp", "type": "numeric", "editable": True, "format": "int"},
    {"key": "larg", "label": "Larg", "type": "numeric", "editable": True, "format": "int"},
    {"key": "esp", "label": "Esp", "type": "numeric", "editable": True, "format": "int"},
    {"key": "mps", "label": "MPs", "type": "bool", "editable": True},
    {"key": "mo", "label": "MO", "type": "bool", "editable": True},
    {"key": "orla", "label": "Orla", "type": "bool", "editable": True},
    {"key": "blk", "label": "BLK", "type": "bool", "editable": True},
    {"key": "nst", "label": "NST", "type": "bool", "editable": True},
    {"key": "mat_default", "label": "Mat_Default", "type": "text", "editable": True},
    {"key": "qt_total", "label": "Qt_Total", "type": "numeric", "editable": False, "format": "two"},
    {"key": "comp_res", "label": "comp_res", "type": "numeric", "editable": False, "format": "int"},
    {"key": "larg_res", "label": "larg_res", "type": "numeric", "editable": False, "format": "int"},
    {"key": "esp_res", "label": "esp_res", "type": "numeric", "editable": False, "format": "int"},
    {"key": "ref_le", "label": "ref_le", "type": "text", "editable": True},
    {"key": "descricao_no_orcamento", "label": "descricao_no_orcamento", "type": "text", "editable": True},
    {"key": "pliq", "label": "pliq", "type": "numeric", "editable": True, "format": "money"},
    {"key": "und", "label": "und", "type": "text", "editable": True},
    {"key": "desp", "label": "desp", "type": "numeric", "editable": True, "format": "percent"},
    {"key": "orl_0_4", "label": "ORL 0.4", "type": "text", "editable": True},
    {"key": "orl_1_0", "label": "ORL 1.0", "type": "text", "editable": True},
    {"key": "tipo", "label": "tipo", "type": "text", "editable": True},
    {"key": "familia", "label": "familia", "type": "text", "editable": True},
    {"key": "comp_mp", "label": "comp_mp", "type": "numeric", "editable": True, "format": "int"},
    {"key": "larg_mp", "label": "larg_mp", "type": "numeric", "editable": True, "format": "int"},
    {"key": "esp_mp", "label": "esp_mp", "type": "numeric", "editable": True, "format": "int"},
    {"key": "orl_c1", "label": "ORL_C1", "type": "numeric", "editable": True, "format": "two"},
    {"key": "orl_c2", "label": "ORL_C2", "type": "numeric", "editable": True, "format": "two"},
    {"key": "orl_l1", "label": "ORL_L1", "type": "numeric", "editable": True, "format": "two"},
    {"key": "orl_l2", "label": "ORL_L2", "type": "numeric", "editable": True, "format": "two"},
    {"key": "ml_orl_c1", "label": "ML_ORL_C1", "type": "numeric", "editable": False, "format": "two"},
    {"key": "ml_orl_c2", "label": "ML_ORL_C2", "type": "numeric", "editable": False, "format": "two"},
    {"key": "ml_orl_l1", "label": "ML_ORL_L1", "type": "numeric", "editable": False, "format": "two"},
    {"key": "ml_orl_l2", "label": "ML_ORL_L2", "type": "numeric", "editable": False, "format": "two"},
    {"key": "custo_orl_c1", "label": "CUSTO_ORL_C1", "type": "numeric", "editable": False, "format": "two"},
    {"key": "custo_orl_c2", "label": "CUSTO_ORL_C2", "type": "numeric", "editable": False, "format": "two"},
    {"key": "custo_orl_l1", "label": "CUSTO_ORL_L1", "type": "numeric", "editable": False, "format": "two"},
    {"key": "custo_orl_l2", "label": "CUSTO_ORL_L2", "type": "numeric", "editable": False, "format": "two"},
    {"key": "gravar_modulo", "label": "GRAVAR_MODULO", "type": "bool", "editable": True},
    {"key": "custo_total_orla", "label": "CUSTO_TOTAL_ORLA", "type": "numeric", "editable": False, "format": "two"},
    {"key": "soma_total_ml_orla", "label": "SOMA_TOTAL_ML_ORLA", "type": "numeric", "editable": False, "format": "two"},
    {"key": "area_m2_und", "label": "AREA_M2_und", "type": "numeric", "editable": False, "format": "two"},
    {"key": "spp_ml_und", "label": "SPP_ML_und", "type": "numeric", "editable": False, "format": "two"},
    {"key": "cp01_sec", "label": "CP01_SEC", "type": "numeric", "editable": True, "format": "two"},
    {"key": "cp01_sec_und", "label": "CP01_SEC_und", "type": "numeric", "editable": True, "format": "two"},
    {"key": "cp02_orl", "label": "CP02_ORL", "type": "numeric", "editable": True, "format": "two"},
    {"key": "cp02_orl_und", "label": "CP02_ORL_und", "type": "numeric", "editable": True, "format": "two"},
    {"key": "cp03_cnc", "label": "CP03_CNC", "type": "numeric", "editable": True, "format": "two"},
    {"key": "cp03_cnc_und", "label": "CP03_CNC_und", "type": "numeric", "editable": True, "format": "two"},
    {"key": "cp04_abd", "label": "CP04_ABD", "type": "numeric", "editable": True, "format": "two"},
    {"key": "cp04_abd_und", "label": "CP04_ABD_und", "type": "numeric", "editable": True, "format": "two"},
    {"key": "cp05_prensa", "label": "CP05_PRENSA", "type": "numeric", "editable": True, "format": "two"},
    {"key": "cp05_prensa_und", "label": "CP05_PRENSA_und", "type": "numeric", "editable": True, "format": "two"},
    {"key": "cp06_esquad", "label": "CP06_ESQUAD", "type": "numeric", "editable": True, "format": "two"},
    {"key": "cp06_esquad_und", "label": "CP06_ESQUAD_und", "type": "numeric", "editable": True, "format": "two"},
    {"key": "cp07_embalagem", "label": "CP07_EMBALAGEM", "type": "numeric", "editable": True, "format": "two"},
    {"key": "cp07_embalagem_und", "label": "CP07_EMBALAGEM_und", "type": "numeric", "editable": True, "format": "two"},
    {"key": "cp08_mao_de_obra", "label": "CP08_MAO_DE_OBRA", "type": "numeric", "editable": True, "format": "two"},
    {"key": "cp08_mao_de_obra_und", "label": "CP08_MAO_DE_OBRA_und", "type": "numeric", "editable": True, "format": "two"},
    {"key": "custo_mp_und", "label": "CUSTO_MP_und", "type": "numeric", "editable": False, "format": "two"},
    {"key": "custo_mp_total", "label": "CUSTO_MP_Total", "type": "numeric", "editable": False, "format": "two"},
    {"key": "soma_custo_orla_total", "label": "Soma_Custo_Orla_Total", "type": "numeric", "editable": False, "format": "two"},
    {"key": "soma_custo_und", "label": "Soma_Custo_und", "type": "numeric", "editable": False, "format": "two"},
    {"key": "soma_custo_total", "label": "Soma_Custo_Total", "type": "numeric", "editable": False, "format": "two"},
    {"key": "soma_custo_acb", "label": "Soma_Custo_ACB", "type": "numeric", "editable": False, "format": "two"},
]


MATERIAL_GROUP_LOOKUP = {
    name.upper(): name
    for name in svc_dados_items.MENU_FIXED_GROUPS.get(svc_dados_items.MENU_MATERIAIS, ())
}


def _normalize_token(value: Optional[str]) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value).strip())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.casefold()


_FAMILIA_MENU_ALIASES_RAW = {
    "PLACAS": svc_dados_items.MENU_MATERIAIS,
    "PLACA": svc_dados_items.MENU_MATERIAIS,
    "FERRAGENS": svc_dados_items.MENU_FERRAGENS,
    "FERRAGEM": svc_dados_items.MENU_FERRAGENS,
    "SISTEMAS CORRER": svc_dados_items.MENU_SIS_CORRER,
    "SISTEMA CORRER": svc_dados_items.MENU_SIS_CORRER,
    "SIST CORRER": svc_dados_items.MENU_SIS_CORRER,
    "ACABAMENTOS": svc_dados_items.MENU_ACABAMENTOS,
    "ACABAMENTO": svc_dados_items.MENU_ACABAMENTOS,
}

FAMILIA_MENU_ALIASES = {_normalize_token(key): value for key, value in _FAMILIA_MENU_ALIASES_RAW.items()}


def _menu_for_familia(familia: Optional[str]) -> Optional[str]:
    token = _normalize_token(familia)
    if not token:
        return None
    return FAMILIA_MENU_ALIASES.get(token)


def _build_leaf_lookup() -> Dict[str, str]:
    mapping: Dict[str, str] = {}

    def _walk(node: Dict[str, Any], parent: Optional[str] = None) -> None:
        label = str(node.get("label", "")).strip()
        if not label:
            return
        children = node.get("children") or []
        if not parent:
            parent_label = label
        else:
            parent_label = parent
        if children:
            for child in children:
                _walk(child, parent_label)
        else:
            mapping[label.upper()] = parent_label

    for entry in TREE_DEFINITION:
        _walk(entry, None)
    return mapping


LEAF_TO_GROUP = _build_leaf_lookup()


def _grupo_label_from_material(material: Any) -> Optional[str]:
    if material is None:
        return None
    for attr in ("grupo_material", "grupo_ferragem", "grupo_sistema", "grupo_acabamento", "familia"):
        value = getattr(material, attr, None)
        if value:
            return str(value)
    return None


def _collect_mat_default_options(session: Session, ctx: svc_dados_items.DadosItemsContext, menu: str) -> List[str]:
    model = svc_dados_items.MODEL_MAP.get(menu)
    if not model:
        return []
    primary_field = svc_dados_items.MENU_PRIMARY_FIELD.get(menu)
    if not primary_field:
        return []

    column = getattr(model, primary_field)
    stmt = select(column).where(
        model.orcamento_id == ctx.orcamento_id,
        model.item_id == ctx.item_id,
    )

    ordem_column = getattr(model, "ordem", None)
    if ordem_column is not None:
        stmt = stmt.order_by(ordem_column, column)
    else:
        stmt = stmt.order_by(column)

    values = session.execute(stmt).scalars().all()
    seen: Set[str] = set()
    resultado: List[str] = []
    for value in values:
        if not value:
            continue
        text = str(value).strip()
        if not text:
            continue
        token = _normalize_token(text)
        if token in seen:
            continue
        seen.add(token)
        resultado.append(text)

    if not resultado:
        defaults = svc_dados_items.MENU_FIXED_GROUPS.get(menu, ())
        for value in defaults:
            text = str(value).strip()
            if not text:
                continue
            token = _normalize_token(text)
            if token in seen:
                continue
            seen.add(token)
            resultado.append(text)

    return resultado


def _buscar_material_por_menu(
    session: Session,
    ctx: svc_dados_items.DadosItemsContext,
    menu: str,
    grupo: Optional[str],
) -> Optional[Any]:
    if not grupo:
        return None

    model = svc_dados_items.MODEL_MAP.get(menu)
    if not model:
        return None

    primary_field = svc_dados_items.MENU_PRIMARY_FIELD.get(menu)
    if not primary_field:
        return None

    stmt = select(model).where(
        model.orcamento_id == ctx.orcamento_id,
        model.item_id == ctx.item_id,
    )

    ordem_column = getattr(model, "ordem", None)
    id_column = getattr(model, "id", None)
    order_columns = []
    if ordem_column is not None:
        order_columns.append(ordem_column)
    if id_column is not None:
        order_columns.append(id_column)
    if order_columns:
        stmt = stmt.order_by(*order_columns)

    rows = session.execute(stmt).scalars().all()
    alvo = _normalize_token(grupo)

    for row in rows:
        valor = getattr(row, primary_field, None)
        if _normalize_token(valor) == alvo:
            return row

    return None


def _empty_row() -> Dict[str, Any]:
    row: Dict[str, Any] = {}
    for spec in CUSTEIO_COLUMN_SPECS:
        key = spec["key"]
        if key == "id":
            row[key] = None
        elif spec["type"] == "bool":
            row[key] = False
        else:
            row[key] = None
    return row


def _decimal_to_float(value: Optional[Decimal]) -> Optional[float]:
    if value is None:
        return None
    return float(value)


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value in (None, "", False):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _normalise_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


def listar_custeio_items(session: Session, orcamento_id: int, item_id: Optional[int]) -> List[Dict[str, Any]]:
    if not item_id:
        return []

    stmt = (
        select(CusteioItem)
        .where(
            CusteioItem.orcamento_id == orcamento_id,
            CusteioItem.item_id == item_id,
        )
        .order_by(CusteioItem.ordem, CusteioItem.id)
    )
    registros = session.execute(stmt).scalars().all()

    linhas: List[Dict[str, Any]] = []
    for registro in registros:
        linha = _empty_row()
        linha["id"] = registro.id
        for spec in CUSTEIO_COLUMN_SPECS:
            key = spec["key"]
            if key == "id":
                continue
            valor = getattr(registro, key, None)
            if spec["type"] == "numeric":
                linha[key] = _decimal_to_float(valor)
            elif spec["type"] == "bool":
                linha[key] = bool(valor)
            else:
                linha[key] = valor
        linhas.append(linha)

    return linhas


def salvar_custeio_items(session: Session, ctx: svc_dados_items.DadosItemsContext, linhas: Sequence[Mapping[str, Any]]) -> None:
    # Remove registros antigos
    session.execute(
        delete(CusteioItem).where(
            CusteioItem.orcamento_id == ctx.orcamento_id,
            CusteioItem.item_id == ctx.item_id,
        )
    )
    session.flush()

    for ordem, linha in enumerate(linhas):
        registro = CusteioItem(
            orcamento_id=ctx.orcamento_id,
            item_id=ctx.item_id,
            cliente_id=ctx.cliente_id,
            user_id=ctx.user_id,
            ano=ctx.ano,
            num_orcamento=ctx.num_orcamento,
            versao=ctx.versao,
            ordem=ordem,
        )
        for spec in CUSTEIO_COLUMN_SPECS:
            key = spec["key"]
            if key == "id":
                continue
            valor = linha.get(key)
            if spec["type"] == "numeric":
                setattr(registro, key, _to_decimal(valor))
            elif spec["type"] == "bool":
                setattr(registro, key, bool(valor))
            else:
                setattr(registro, key, _normalise_string(valor))
        session.add(registro)

    session.commit()


def gerar_linhas_para_selecoes(
    session: Session,
    ctx: svc_dados_items.DadosItemsContext,
    selecoes: Sequence[str],
) -> List[Dict[str, Any]]:
    linhas: List[Dict[str, Any]] = []
    for selecao in selecoes:
        parts = [p.strip() for p in selecao.split(">") if p.strip()]
        if not parts:
            continue

        linha = _empty_row()
        linha["descricao_livre"] = ""
        linha["def_peca"] = parts[-1]

        topo = parts[0].upper()
        grupo = MATERIAL_GROUP_LOOKUP.get(topo)
        if grupo:
            material = _obter_material(session, ctx, grupo)
        else:
            material = None

        if material:
            _preencher_linha_com_material(linha, material, grupo)
        else:
            linha["descricao"] = linha["def_peca"]
        linhas.append(linha)

    return linhas


def _obter_material(session: Session, ctx: svc_dados_items.DadosItemsContext, grupo: str) -> Optional[DadosItemsMaterial]:
    stmt = (
        select(DadosItemsMaterial)
        .where(
            DadosItemsMaterial.orcamento_id == ctx.orcamento_id,
            DadosItemsMaterial.item_id == ctx.item_id,
            DadosItemsMaterial.grupo_material.ilike(grupo),
        )
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()


def _preencher_linha_com_material(
    linha: Dict[str, Any],
    material: Any,
    grupo_hint: Optional[str] = None,
) -> None:
    descricao = getattr(material, "descricao", None) or getattr(material, "descricao_phc", None) or getattr(material, "descricao_orcamento", None)
    linha["descricao"] = descricao
    linha["ref_le"] = getattr(material, "ref_le", None) or getattr(material, "ref_fornecedor", None)
    linha["descricao_no_orcamento"] = getattr(material, "descricao_material", None) or getattr(material, "descricao_orcamento", None)
    linha["pliq"] = _decimal_to_float(getattr(material, "preco_liq", None) or getattr(material, "pliq", None))
    linha["und"] = getattr(material, "und", None)
    linha["desp"] = _decimal_to_float(getattr(material, "desp", None))
    linha["orl_0_4"] = getattr(material, "orl_0_4", None)
    linha["orl_1_0"] = getattr(material, "orl_1_0", None)
    linha["tipo"] = getattr(material, "tipo", None)
    linha["familia"] = getattr(material, "familia", None)
    linha["comp_mp"] = _decimal_to_float(getattr(material, "comp_mp", None))
    linha["larg_mp"] = _decimal_to_float(getattr(material, "larg_mp", None))
    linha["esp_mp"] = _decimal_to_float(getattr(material, "esp_mp", None))
    linha["nst"] = bool(getattr(material, "nao_stock", False))
    grupo = _grupo_label_from_material(material) or grupo_hint
    if grupo:
        linha["mat_default"] = grupo
    linha["spp_ml_und"] = _decimal_to_float(getattr(material, "spp_ml_und", None))
    linha["custo_mp_und"] = _decimal_to_float(getattr(material, "custo_mp_und", None))
    linha["custo_mp_total"] = _decimal_to_float(getattr(material, "custo_mp_total", None))

def carregar_contexto(
    session: Session,
    orcamento_id: int,
    *,
    item_id: Optional[int] = None,
) -> svc_dados_items.DadosItemsContext:
    """Delegates to dados_items context loader; requires item_id."""

    if item_id is None:
        raise ValueError("item_id e obrigatorio para carregar contexto de Dados Items")

    return svc_dados_items.carregar_contexto(session, orcamento_id, item_id=item_id)




def linha_vazia() -> Dict[str, Any]:
    return _empty_row()


def lista_mat_default(
    session: Optional[Session] = None,
    ctx: Optional[svc_dados_items.DadosItemsContext] = None,
    familia: Optional[str] = None,
) -> List[str]:
    if session and ctx:
        menu = _menu_for_familia(familia)
        if menu:
            return _collect_mat_default_options(session, ctx, menu)

        agregado: List[str] = []
        vistos: Set[str] = set()
        for menu_key in set(FAMILIA_MENU_ALIASES.values()):
            opcoes = _collect_mat_default_options(session, ctx, menu_key)
            for opcao in opcoes:
                token = _normalize_token(opcao)
                if token in vistos:
                    continue
                vistos.add(token)
                agregado.append(opcao)
        if agregado:
            return agregado

    return sorted(set(MATERIAL_GROUP_LOOKUP.values()))


def obter_material_por_grupo(
    session: Session,
    ctx: svc_dados_items.DadosItemsContext,
    grupo: Optional[str],
    familia: Optional[str] = None,
):
    if not grupo:
        return None

    if familia:
        material = obter_material_por_familia(session, ctx, familia, grupo)
        if material:
            return material

    material = _obter_material(session, ctx, grupo)
    if material:
        return material

    for menu_key in set(FAMILIA_MENU_ALIASES.values()):
        material = _buscar_material_por_menu(session, ctx, menu_key, grupo)
        if material:
            return material

    return None


def obter_material_por_familia(
    session: Session,
    ctx: svc_dados_items.DadosItemsContext,
    familia: Optional[str],
    grupo: Optional[str],
):
    menu = _menu_for_familia(familia)
    if not menu:
        return _obter_material(session, ctx, grupo) if grupo else None
    return _buscar_material_por_menu(session, ctx, menu, grupo)


def dados_material(material: Any) -> Dict[str, Any]:
    linha: Dict[str, Any] = {}
    _preencher_linha_com_material(linha, material)
    return linha


def grupo_por_def_peca(def_peca: str) -> Optional[str]:
    if not def_peca:
        return None
    chave = LEAF_TO_GROUP.get(def_peca.strip().upper())
    if not chave:
        return None
    return MATERIAL_GROUP_LOOKUP.get(chave.upper(), chave)




def obter_arvore() -> Sequence[TreeNode]:
    return TREE_DEFINITION


def carregar_orcamento(session: Session, orcamento_id: int) -> Optional[Orcamento]:
    return session.get(Orcamento, orcamento_id)


def carregar_item(session: Session, item_id: int) -> Optional[OrcamentoItem]:
    return session.get(OrcamentoItem, item_id)


def obter_cliente_nome(session: Session, client_id: Optional[int]) -> str:
    if not client_id:
        return "-"
    client = session.get(Client, client_id)
    return (client.nome if client else "-") or "-"


def obter_user_nome(session: Session, user_id: Optional[int]) -> str:
    if not user_id:
        return "-"
    user = session.get(User, user_id)
    return (user.username if user else "-") or "-"
