from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, ROUND_HALF_UP
import json
import re
import unicodedata
import uuid
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from sqlalchemy import delete, select, func
from sqlalchemy.orm import Session

from Martelo_Orcamentos_V2.app.models.client import Client
from Martelo_Orcamentos_V2.app.models.custeio import CusteioItem, CusteioItemDimensoes
from Martelo_Orcamentos_V2.app.models.dados_gerais import DadosItemsMaterial, DadosItemsFerragem
from Martelo_Orcamentos_V2.app.models.materia_prima import MateriaPrima
from Martelo_Orcamentos_V2.app.models.orcamento import Orcamento, OrcamentoItem
from Martelo_Orcamentos_V2.app.models.user import User
from Martelo_Orcamentos_V2.app.services import dados_items as svc_dados_items
from Martelo_Orcamentos_V2.app.services.settings import get_setting, set_setting


TreeNode = Dict[str, Any]


ACABAMENTO_DEFAULTS = [
    "Lacar Face Sup",
    "Lacar Face Inf",
    "Lacar 2 Faces",
    "Verniz Face Sup",
    "Verniz Face Inf",
    "Verniz 2 faces",
    "Acabamento Face Sup 1",
    "Acabamento Face Sup 2",
    "Acabamento Face Inf 1",
    "Acabamento Face Inf 2",
]

DIMENSION_KEY_ORDER: Sequence[str] = (
    "H",
    "L",
    "P",
    "H1",
    "L1",
    "P1",
    "H2",
    "L2",
    "P2",
    "H3",
    "L3",
    "P3",
    "H4",
    "L4",
    "P4",
)
DIMENSION_ALLOWED_VARIABLES: Set[str] = set(DIMENSION_KEY_ORDER) | {"HM", "LM", "PM"}

_AUTO_DIMENSION_SETTING_TEMPLATE = "custeio:auto_dims:user:{user_id}"
_AUTO_DIMENSION_TRUE_VALUES = {"1", "true", "yes", "on", "sim"}
_AUTO_DIMENSION_RULES: Tuple[Tuple[str, str, str], ...] = (
    ("COSTA", "HM", "LM"),
    ("PORTA ABRIR", "HM", "LM"),
    ("LATERAL", "HM", "PM"),
    ("DIVISORIA", "HM", "PM"),
    ("TETO", "LM", "PM"),
    ("FUNDO", "LM", "PM"),
    ("PRATELEIRA AMOVIVEL", "LM", "PM"),
    ("PRAT AMOV", "LM", "PM"),
    ("PRATELEIRA FIXA", "LM", "PM"),
    ("PRAT FIXA", "LM", "PM"),
)

_DIVISAO_LABEL_TOKEN = "DIVISAO INDEPENDENTE"


def _uppercase_no_accents(value: Optional[str]) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.upper()


def _normalize_token(value: Optional[str]) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value).strip())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.casefold()


GROUP_LOOKUP: Dict[str, Dict[str, str]] = {}
for _menu, _groups in svc_dados_items.MENU_FIXED_GROUPS.items():
    for _name in _groups:
        GROUP_LOOKUP[_normalize_token(_name)] = {"menu": _menu, "name": _name}

_FERRAGEM_CHILD_TYPE_MAP: Dict[str, Dict[str, str]] = {
    _normalize_token("SUPORTE PRATELEIRA"): {"tipo": "SUPORTE PRATELEIRA", "familia": "FERRAGENS"},
    _normalize_token("VARAO"): {"tipo": "SPP", "familia": "FERRAGENS"},
    _normalize_token("VARÃO"): {"tipo": "SPP", "familia": "FERRAGENS"},
    _normalize_token("SUPORTE VARAO"): {"tipo": "SUPORTE VARAO", "familia": "FERRAGENS"},
    _normalize_token("SUPORTE VARÃO"): {"tipo": "SUPORTE VARAO", "familia": "FERRAGENS"},
    _normalize_token("PUXADOR"): {"tipo": "PUXADOR", "familia": "FERRAGENS"},
    _normalize_token("PES"): {"tipo": "PES", "familia": "FERRAGENS"},
    _normalize_token("PÉS"): {"tipo": "PES", "familia": "FERRAGENS"},
    _normalize_token("DOBRADICA"): {"tipo": "DOBRADICAS", "familia": "FERRAGENS"},
    _normalize_token("DOBRADIÇA"): {"tipo": "DOBRADICAS", "familia": "FERRAGENS"},
}

_FERRAGEM_TIPO_KEYWORDS: Dict[str, Sequence[str]] = {
    _normalize_token("SUPORTE PRATELEIRA"): ("suporte", "prateleira"),
    _normalize_token("SUPORTE VARAO"): ("suporte", "varao"),
    _normalize_token("SUPORTE VARÃO"): ("suporte", "varao"),
    _normalize_token("SPP"): ("varao", "spp"),
    _normalize_token("PUXADOR"): ("puxador",),
    _normalize_token("PES"): ("pes",),
    _normalize_token("DOBRADICAS"): ("dobradica",),
}

DEFAULT_QT_RULES: Dict[str, Dict[str, Any]] = {
    "PES": {
        "matches": ["PES"],
        "expression": "4 if COMP < 650 and LARG < 800 else 6 if COMP >= 650 and LARG < 800 else 8",
        "tooltip": "4 se COMP<650 & LARG<800 | 6 se COMP>=650 & LARG<800 | 8 caso contrário",
    },
    "SUPORTE PRATELEIRA": {
        "matches": ["SUPORTE PRATELEIRA"],
        "expression": "8 if COMP >= 1100 and LARG >= 800 else 6 if COMP >= 1100 else 4",
        "tooltip": "4 por defeito | 6 se COMP>=1100 | 8 se COMP>=1100 & LARG>=800",
    },
    "VARAO SPP": {
        "matches": ["VARAO SPP", "VARAO"],
        "expression": "1",
        "tooltip": "1 varão por peça principal (COMP herdado para cálculo de ML).",
    },
    "SUPORTE VARAO": {
        "matches": ["SUPORTE VARAO"],
        "expression": "2",
        "tooltip": "2 suportes por varão.",
    },
    "SUPORTE TERMINAL VARAO": {
        "matches": ["SUPORTE TERMINAL VARAO"],
        "expression": "2",
        "tooltip": "2 suportes por varão.",
    },
    "SUPORTE VARAO": {
        "matches": ["SUPORTE VARAO"],
        "expression": "2",
        "tooltip": "2 suportes por varão.",
    },
    "DOBRADICA": {
        "matches": ["DOBRADICA"],
        "expression": "("
                        "2 if COMP <= 850 "
                        "else 3 if COMP <= 1600 "
                        "else 4 if COMP <= 2000 "
                        "else 5 if COMP <= 2600 "
                        "else 6 + ((COMP - 2600) // 600)"
                    ") + (1 if LARG >= 605 else 0)",
        "tooltip": "Até 850: 2 | 851-1600: 3 | 1601-2000: 4 | 2001-2600: 5 | depois: +1/600mm. Soma +1 se LARG>=605.",
    },
    "PUXADOR": {
        "matches": ["PUXADOR"],
        "expression": "1",
        "tooltip": "1 puxador por porta (total acompanha o QT_und da peça principal).",
    },
}

RULES_SETTING_TEMPLATE = "custeio_rules_{orcamento}_{versao}"
RULES_SETTING_DEFAULT = "custeio_rules_default"


def _clone_rules(rules: Mapping[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    cloned: Dict[str, Dict[str, Any]] = {}
    for key, value in rules.items():
        cloned[key] = deepcopy(value)
    return cloned


def load_qt_rules(
    session: Session,
    ctx: Optional[svc_dados_items.DadosItemsContext] = None,
    *,
    orcamento_id: Optional[int] = None,
    versao: Optional[str] = None,
) -> Dict[str, Dict[str, Any]]:
    if ctx is not None:
        orcamento_id = getattr(ctx, "orcamento_id", None)
        versao = getattr(ctx, "versao", None)

    base = _clone_rules(DEFAULT_QT_RULES)

    if orcamento_id is None:
        raw = get_setting(session, RULES_SETTING_DEFAULT, None)
        if not raw:
            return base
        try:
            data = json.loads(raw)
        except Exception:
            return base
        if isinstance(data, dict):
            for key, override in data.items():
                if key in base and isinstance(override, dict):
                    base[key].update({k: v for k, v in override.items() if v is not None})
        return base

    setting_key = RULES_SETTING_TEMPLATE.format(orcamento=orcamento_id, versao=versao or "01")
    raw = get_setting(session, setting_key, None)
    if not raw:
        return base
    try:
        data = json.loads(raw)
    except Exception:
        return base
    if isinstance(data, dict):
        for key, override in data.items():
            if key in base and isinstance(override, dict):
                base[key].update({k: v for k, v in override.items() if v is not None})
    return base


def save_qt_rules(
    session: Session,
    ctx: Optional[svc_dados_items.DadosItemsContext],
    rules: Mapping[str, Any],
    *,
    orcamento_id: Optional[int] = None,
    versao: Optional[str] = None,
) -> None:
    if ctx is not None:
        orcamento_id = getattr(ctx, "orcamento_id", None)
        versao = getattr(ctx, "versao", None)

    if orcamento_id is None:
        set_setting(session, RULES_SETTING_DEFAULT, json.dumps(rules, ensure_ascii=False))
        session.flush()
        return

    setting_key = RULES_SETTING_TEMPLATE.format(orcamento=orcamento_id, versao=versao or "01")
    set_setting(session, setting_key, json.dumps(rules, ensure_ascii=False))
    session.flush()


def reset_qt_rules(
    session: Session,
    ctx: Optional[svc_dados_items.DadosItemsContext],
    *,
    orcamento_id: Optional[int] = None,
    versao: Optional[str] = None,
    reset_default: bool = False,
) -> None:
    if ctx is not None:
        orcamento_id = getattr(ctx, "orcamento_id", None)
        versao = getattr(ctx, "versao", None)

    if reset_default or orcamento_id is None:
        set_setting(session, RULES_SETTING_DEFAULT, None)
        session.flush()
        return

    setting_key = RULES_SETTING_TEMPLATE.format(orcamento=orcamento_id, versao=versao or "01")
    set_setting(session, setting_key, None)
    session.flush()


def _identify_regra(def_peca: str, rules: Mapping[str, Dict[str, Any]]) -> Optional[str]:
    token = _normalize_token(def_peca)
    if not token:
        return None
    for name, data in rules.items():
        for match in data.get("matches", []):
            if _normalize_token(match) in token:
                return name
    return None


def calcular_qt_filhos(
    regra_nome: Optional[str],
    parent_row: Mapping[str, Any],
    child_row: Mapping[str, Any],
    divisor: float,
    parent_qt: float,
    rules: Mapping[str, Dict[str, Any]],
) -> float:
    if not regra_nome or regra_nome not in rules:
        return float(child_row.get("qt_und") or 1.0)
    regra = rules[regra_nome]
    expression = regra.get("expression")
    default = regra.get("default")

    def _numeric(value: Any) -> float:
        coerced = _coerce_dimensao_valor(value)
        if coerced is None:
            try:
                return float(value or 0)
            except Exception:
                return 0.0
        return coerced

    qt_pai = _numeric(parent_row.get("qt_und")) or 1.0
    comp_val = parent_row.get("comp_res")
    larg_val = parent_row.get("larg_res")
    esp_val = parent_row.get("esp_res")
    env = {
        "COMP": _numeric(comp_val if comp_val not in (None, "") else parent_row.get("comp")),
        "LARG": _numeric(larg_val if larg_val not in (None, "") else parent_row.get("larg")),
        "ESP": _numeric(esp_val if esp_val not in (None, "") else parent_row.get("esp")),
        "COMP_MP": _numeric(parent_row.get("comp_mp")),
        "LARG_MP": _numeric(parent_row.get("larg_mp")),
        "ESP_MP": _numeric(parent_row.get("esp_mp")),
        "QT_PAI": qt_pai,
        "QT_DIV": _numeric(divisor),
        "QT_MOD": _numeric(parent_qt),
    }
    if expression:
        try:
            value = eval(expression, {"__builtins__": {}}, env)  # noqa: S307
        except Exception:
            value = default if default is not None else 1
    else:
        value = default if default is not None else 1
    try:
        result = float(value)
    except Exception:
        result = 1.0
    return max(result, 0.0)


def identificar_regra(def_peca: str, rules: Optional[Mapping[str, Dict[str, Any]]] = None) -> Optional[str]:
    source = rules or DEFAULT_QT_RULES
    return _identify_regra(def_peca, source)


TREE_DEFINITION: List[TreeNode] = [
    {
        "label": "COSTAS",
        "group": "Costas",
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
        "group": "Laterais",
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
        "group": "Tetos",
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
        "group": "Fundos",
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
        "group": "Prateleiras Amoviveis",
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
        "group": "Prateleiras Fixas",
        "children": [
            {"label": "PRATELEIRA FIXA [0000]"},
            {"label": "PRATELEIRA FIXA [2000]"},
            {"label": "PRATELEIRA FIXA [2111]"},
            {"label": "PRATELEIRA FIXA [2222]"},
            {"label": "PRAT. FIXA [2000] + VARAO + SUPORTE VARAO"},
        ],
    },
    {
        "label": "GAVETAS",
        "group": "Gavetas",
        "children": [
            {"label": "FRENTE GAVETA [2222]"},
            {"label": "FRENTE GAVETA [2222] + PUXADOR"},
            {"label": "LATERAL GAVETA [2202]"},
            {"label": "TRASEIRA GAVETA [2000]"},
            {"label": "FUNDO GAVETA [0022]"},
        ],
    },
    {
        "label": "REMATES/GUARNICOES",
        "children": [
            {"label": "REMATE VERTICAL [2200]", "group": "Remates Verticais"},
            {"label": "RODATETO [0000]", "group": "Remates Horizontais"},
            {"label": "RODATETO [2200]", "group": "Remates Horizontais"},
            {"label": "RODATETO [2222]", "group": "Remates Horizontais"},
            {"label": "RODAPE AGL [0000]", "group": "Rodape AGL"},
            {"label": "RODAPE AGL [2200]", "group": "Rodape AGL"},
            {"label": "RODAPE AGL [2222]", "group": "Rodape AGL"},
            {"label": "RODAPE PVC/ALUMINIO", "group": "Rodape PVC/Aluminio"},
            {"label": "ENCHIMENTO GUARNICAO [2000]", "group": "Enchimentos Guarnicoes"},
            {"label": "GUARNICAO PRODUZIDA [2222]", "group": "Guarnicoes Produzidas"},
            {"label": "GUARNICAO COMPRA L", "group": "Guarnicoes Compra"},
        ],
    },
    {
        "label": "PORTAS ABRIR",
        "children": [
            {"label": "PORTA ABRIR [2222]", "group": "Portas Abrir 1"},
            {"label": "PORTA ABRIR [2222] + DOBRADICA", "group": "Portas Abrir 1"},
            {"label": "PORTA ABRIR [2222] + DOBRADICA + PUXADOR", "group": "Portas Abrir 2"},
        ],
    },
    {
        "label": "PORTAS CORRER",
        "children": [
            {"label": "PAINEL CORRER [0000]", "group": "Paineis"},
            {"label": "PAINEL CORRER [2222]", "group": "Paineis"},
            {"label": "PAINEL ESPELHO [2222]", "group": "Paineis"},
        ],
    },
    {
        "label": "SERVICOS",
        "children": [
            {"label": "MAO OBRA (Min)"},
            {"label": "CNC (Min)"},
            {"label": "CNC (5 Min)"},
            {"label": "CNC (15 Min)"},
            {"label": "COLAGEM SANDWICH (M2)"},
        ],
    },
    {
        "label": "FERRAGENS",
        "children": [
            {
                "label": "DOBRADICAS",
                "children": [
                    {"label": "DOBRADICA RETA", "group": "Dobradica Reta"},
                    {"label": "DOBRADICA CANTO SEGO", "group": "Dobradica Canto Sego"},
                    {"label": "DOBRADICA ABERTURA TOTAL", "group": "Dobradica Abertura Total"},
                    {"label": "DOBRADICA 1", "group": "Dobradica 1"},
                    {"label": "DOBRADICA 2", "group": "Dobradica 2"},
                ],
            },
            {
                "label": "SUPORTES PRATELEIRA",
                "children": [
                    {"label": "SUPORTE PRATELEIRA 1", "group": "Suporte Prateleira 1"},
                    {"label": "SUPORTE PRATELEIRA 2", "group": "Suporte Prateleira 2"},
                    {"label": "SUPORTE PAREDE", "group": "Suporte Parede"},
                ],
            },
            {
                "label": "SPP (ACESSORIOS AJUSTAVEIS)",
                "children": [
                    {"label": "VARAO {SPP}", "group": "Varao SPP"},
                    {"label": "PERFIL LAVA LOUCA {SPP}", "group": "Perfil Lava Louca SPP"},
                    {"label": "RODAPE PVC {SPP}", "group": "Rodape PVC SPP"},
                    {"label": "PUXADOR GOLA C {SPP}", "group": "Puxador Gola C SPP"},
                    {"label": "PUXADOR GOLA J {SPP}", "group": "Puxador Gola J SPP"},
                    {"label": "PUXADOR PERFIL {SPP} 1", "group": "Puxador Perfil SPP 1"},
                    {"label": "PUXADOR PERFIL {SPP} 2", "group": "Puxador Perfil SPP 2"},
                    {"label": "PUXADOR PERFIL {SPP} 3", "group": "Puxador Perfil SPP 3"},
                    {"label": "CALHA LED {SPP} 1", "group": "Calha Led 1 SPP"},
                    {"label": "CALHA LED {SPP} 2", "group": "Calha Led 2 SPP"},
                    {"label": "FITA LED {SPP} 1", "group": "Fita Led 1 SPP"},
                    {"label": "FITA LED {SPP} 2", "group": "Fita Led 2 SPP"},
                    {"label": "FERRAGENS DIVERSAS {SPP} 6", "group": "Ferragens Diversas 6 SPP"},
                    {"label": "FERRAGENS DIVERSAS {SPP} 7", "group": "Ferragens Diversas 7 SPP"},
                    {"label": "CALHA SUPERIOR {SPP} 1 CORRER", "group": "Calha Superior 1 SPP"},
                    {"label": "CALHA SUPERIOR {SPP} 2 CORRER", "group": "Calha Superior 2 SPP"},
                    {"label": "CALHA INFERIOR {SPP} 1 CORRER", "group": "Calha Inferior 1 SPP"},
                    {"label": "CALHA INFERIOR {SPP} 2 CORRER", "group": "Calha Inferior 2 SPP"},
                    {"label": "PERFIL HORIZONTAL H {SPP}", "group": "Perfil Horizontal H SPP"},
                    {"label": "PERFIL HORIZONTAL U {SPP}", "group": "Perfil Horizontal U SPP"},
                    {"label": "PERFIL HORIZONTAL L {SPP}", "group": "Perfil Horizontal L SPP"},
                    {"label": "ACESSORIO {SPP} 7 CORRER", "group": "Acessorio 7 SPP"},
                    {"label": "ACESSORIO {SPP} 8 CORRER", "group": "Acessorio 8 SPP"},
                ],
            },
            {
                "label": "PUXADORES",
                "children": [
                    {"label": "PUXADOR TIC-TAC", "group": "Puxador Tic Tac"},
                    {"label": "PUXADOR FRESADO J", "group": "Puxador Fresado J"},
                    {"label": "PUXADOR STD 1", "group": "Puxador STD 1"},
                    {"label": "PUXADOR STD 2", "group": "Puxador STD 2"},
                ],
            },
            {
                "label": "CORREDICAS GAVETAS",
                "children": [
                    {"label": "CORREDICA INVISIVEL", "group": "Corredica Invisivel"},
                    {"label": "CORREDICA LATERAL METALICA", "group": "Corredica Lateral Metalica"},
                    {"label": "CORREDICA 1", "group": "Corredica 1"},
                    {"label": "CORREDICA 2", "group": "Corredica 2"},
                ],
            },
            {
                "label": "PES",
                "children": [
                    {"label": "PES 1", "group": "Pes 1"},
                    {"label": "PES 2", "group": "Pes 2"},
                    {"label": "PES 3", "group": "Pes 3"},
                ],
            },
            {
                "label": "SISTEMAS ELEVATORIOS",
                "children": [
                    {"label": "AVENTOS 1", "group": "Aventos 1"},
                    {"label": "AVENTOS 2", "group": "Aventos 2"},
                    {"label": "AMORTECEDOR", "group": "Amortecedor"},
                    {"label": "SISTEMA BASCULANTE 1", "group": "Sistema Basculante 1"},
                    {"label": "SISTEMA BASCULANTE 2", "group": "Sistema Basculante 2"},
                ],
            },
            {
                "label": "ILUMINACAO",
                "children": [
                    {"label": "TRANSFORMADOR 1", "group": "Transformador 1"},
                    {"label": "TRANSFORMADOR 2", "group": "Transformador 2"},
                    {"label": "SENSOR LED 1", "group": "Sensor LED 1"},
                    {"label": "SENSOR LED 2", "group": "Sensor LED 2"},
                    {"label": "SENSOR LED 3", "group": "Sensor LED 3"},
                    {"label": "ILUMINACAO 1", "group": "Iluminacao 1"},
                    {"label": "ILUMINACAO 2", "group": "Iluminacao 2"},
                    {"label": "ILUMINACAO 3", "group": "Iluminacao 3"},
                    {"label": "CABOS LED 1", "group": "Cabos Led 1"},
                    {"label": "CABOS LED 2", "group": "Cabos Led 2"},
                    {"label": "CABOS LED 3", "group": "Cabos Led 3"},
                ],
            },
            {
                "label": "COZINHAS",
                "children": [
                    {"label": "BALDE LIXO", "group": "Balde Lixo"},
                    {"label": "CESTO CANTO FEIJAO 1", "group": "Cesto Canto Feijao"},
                    {"label": "CANTO COZINHA 1", "group": "Canto Cozinha 1"},
                    {"label": "CANTO COZINHA 2", "group": "Canto Cozinha 2"},
                    {"label": "PORTA TALHERES", "group": "Porta Talheres"},
                    {"label": "TULHA 1", "group": "Tulha 1"},
                    {"label": "TULHA 2", "group": "Tulha 2"},
                    {"label": "FUNDO ALUMINIO 1", "group": "Fundo Aluminio 1"},
                    {"label": "FUNDO ALUMINIO 2", "group": "Fundo Aluminio 2"},
                    {"label": "FUNDO PLASTICO FRIGORIFICO", "group": "Fundo Plastico Frigorifico"},
                    {"label": "SALVA SIFAO", "group": "Salva Sifao"},
                ],
            },
            {
                "label": "ROUPEIROS",
                "children": [
                    {"label": "PORTA CALCAS", "group": "Porta Calcas"},
                    {"label": "VARAO TROMBONE", "group": "Varao Trombone"},
                    {"label": "VARAO EXTENSIVEL", "group": "Varao Extensivel"},
                    {"label": "GRELHA VELUDO", "group": "Grelha Veludo"},
                ],
            },
            {
                "label": "FERRAGENS DIVERSAS {FERRAGENS}",
                "children": [
                    {"label": "FERRAGENS DIVERSAS 1", "group": "Ferragens Diversas 1"},
                    {"label": "FERRAGENS DIVERSAS 2", "group": "Ferragens Diversas 2"},
                    {"label": "FERRAGENS DIVERSAS 3", "group": "Ferragens Diversas 3"},
                    {"label": "FERRAGENS DIVERSAS 4", "group": "Ferragens Diversas 4"},
                    {"label": "FERRAGENS DIVERSAS 5", "group": "Ferragens Diversas 5"},
                ],
            },
            {
                "label": "UNIOES CANTO SPP",
                "children": [
                    {"label": "SUPORTE TERMINAL VARAO", "group": "Suporte Terminal Varao"},
                    {"label": "SUPORTE CENTRAL VARAO", "group": "Suporte Central Varao"},
                    {"label": "TERMINAL PERFIL LAVA LOUCA", "group": "Terminal Perfil Lava Louca"},
                    {"label": "CANTO RODAPE PVC", "group": "Canto Rodape PVC"},
                    {"label": "GRAMPAS RODAPE PVC", "group": "Grampas Rodape PVC"},
                ],
            },
            {
                "label": "SISTEMAS CORRER",
                "children": [
                    {"label": "PUXADOR VERTICAL 1", "group": "Puxador Vertical 1"},
                    {"label": "PUXADOR VERTICAL 2", "group": "Puxador Vertical 2"},
                    {"label": "RODIZIO SUP 1", "group": "Rodizio Sup 1"},
                    {"label": "RODIZIO SUP 2", "group": "Rodizio Sup 2"},
                    {"label": "RODIZIO INF 1", "group": "Rodizio Inf 1"},
                    {"label": "RODIZIO INF 2", "group": "Rodizio Inf 2"},
                    {"label": "ACESSORIO 1 CORRER", "group": "Acessorio 1"},
                    {"label": "ACESSORIO 2 CORRER", "group": "Acessorio 2"},
                    {"label": "ACESSORIO 3 CORRER", "group": "Acessorio 3"},
                    {"label": "ACESSORIO 4 CORRER", "group": "Acessorio 4"},
                    {"label": "ACESSORIO 5 CORRER", "group": "Acessorio 5"},
                    {"label": "ACESSORIO 6 CORRER", "group": "Acessorio 6"},
                ],
            },
            {
                "label": "FERRAGENS DIVERSAS {SISTEMAS CORRER}",
                "children": [
                    {"label": "ACESSORIO 7 SPP", "group": "Acessorio 7 SPP"},
                    {"label": "ACESSORIO 8 SPP", "group": "Acessorio 8 SPP"},
                ],
            },
        ],
    },
]

CUSTEIO_COLUMN_SPECS: List[Dict[str, Any]] = [
    {"key": "id", "label": "id", "type": "int", "editable": False},
    {"key": "descricao_livre", "label": "Descricao_Livre", "type": "text", "editable": True},
    {"key": "icon_hint", "label": "", "type": "icon", "editable": False},
    {"key": "def_peca", "label": "Def_Peca", "type": "text", "editable": False},
    {"key": "descricao", "label": "Descricao", "type": "text", "editable": False},
    {"key": "qt_mod", "label": "QT_mod", "type": "numeric", "editable": True},
    {"key": "qt_und", "label": "QT_und", "type": "numeric", "editable": True},
    {"key": "comp", "label": "Comp", "type": "text", "editable": True},
    {"key": "larg", "label": "Larg", "type": "text", "editable": True},
    {"key": "esp", "label": "Esp", "type": "text", "editable": True},
    {"key": "mps", "label": "MPs", "type": "bool", "editable": True},
    {"key": "mo", "label": "MO", "type": "bool", "editable": True},
    {"key": "orla", "label": "Orla", "type": "bool", "editable": True},
    {"key": "blk", "label": "BLK", "type": "bool", "editable": True},
    {"key": "nst", "label": "NST", "type": "bool", "editable": True},
    {"key": "mat_default", "label": "Mat_Default", "type": "text", "editable": True},
    {"key": "acabamento_sup", "label": "Acabamento_SUP", "type": "text", "editable": True},
    {"key": "acabamento_inf", "label": "Acabamento_INF", "type": "text", "editable": True},
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
    {"key": "orl_c1", "label": "ORL_C1", "type": "numeric", "editable": True, "format": "one"},
    {"key": "orl_c2", "label": "ORL_C2", "type": "numeric", "editable": True, "format": "one"},
    {"key": "orl_l1", "label": "ORL_L1", "type": "numeric", "editable": True, "format": "one"},
    {"key": "orl_l2", "label": "ORL_L2", "type": "numeric", "editable": True, "format": "one"},
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
    {"key": "perimetro_und", "label": "PERIMETRO_und", "type": "numeric", "editable": False, "format": "two"},
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

    def _walk(node: Dict[str, Any], inherited_group: Optional[str]) -> None:
        label = str(node.get("label", "")).strip()
        if not label:
            return
        group = node.get("group") or inherited_group
        children = node.get("children") or []
        if children:
            for child in children:
                _walk(child, group)
        else:
            if group:
                mapping[label.upper()] = group
            else:
                mapping[label.upper()] = label

    for entry in TREE_DEFINITION:
        initial_group = entry.get("group") or entry.get("label")
        _walk(entry, initial_group)
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


def _clean_ferragem_token(token: str) -> str:
    cleaned = token.strip()
    while cleaned and cleaned[-1].isdigit():
        cleaned = cleaned[:-1]
    cleaned = cleaned.rstrip("_ ").strip()
    return cleaned or token


def _lookup_ferragem_info(label: Optional[str]) -> Optional[Dict[str, str]]:
    if label is None:
        return None
    text = str(label).strip()
    if not text:
        return None
    token = _normalize_token(text)
    if not token:
        return None
    info = _FERRAGEM_CHILD_TYPE_MAP.get(token)
    if info:
        return info
    simplified = _clean_ferragem_token(token)
    if simplified and simplified != token:
        info = _FERRAGEM_CHILD_TYPE_MAP.get(simplified)
        if info:
            return info
    if "_" in token:
        base = token.split("_", 1)[0].strip()
        info = _FERRAGEM_CHILD_TYPE_MAP.get(base)
        if info:
            return info
    return None


def _group_keywords_for_tipo(tipo: Optional[str]) -> Sequence[str]:
    if not tipo:
        return ()
    key = _normalize_token(tipo)
    keywords = _FERRAGEM_TIPO_KEYWORDS.get(key)
    if keywords:
        return keywords
    return tuple(word for word in key.split() if word)


def _buscar_ferragem_por_tipo(
    session: Session,
    ctx: svc_dados_items.DadosItemsContext,
    tipo: Optional[str],
    familia: Optional[str] = None,
):
    if not tipo:
        return None
    tipo_text = str(tipo).strip()
    if not tipo_text:
        return None

    stmt = (
        select(DadosItemsFerragem)
        .where(
            DadosItemsFerragem.orcamento_id == ctx.orcamento_id,
            DadosItemsFerragem.item_id == ctx.item_id,
        )
    )
    stmt = stmt.where(func.lower(DadosItemsFerragem.tipo) == tipo_text.lower())

    if familia:
        familia_text = str(familia).strip()
        if familia_text:
            stmt = stmt.where(func.lower(DadosItemsFerragem.familia) == familia_text.lower())

    stmt = stmt.order_by(DadosItemsFerragem.linha, DadosItemsFerragem.grupo_ferragem).limit(1)
    return session.execute(stmt).scalar_one_or_none()


def obter_ferragem_por_tipo(
    session: Session,
    ctx: svc_dados_items.DadosItemsContext,
    tipo: Optional[str],
    familia: Optional[str] = None,
):
    if not tipo:
        return None
    familia_base = familia or "FERRAGENS"
    material = _buscar_ferragem_por_tipo(session, ctx, tipo, familia_base)
    if material:
        return material
    return _buscar_ferragem_por_tipo(session, ctx, tipo, None)


def inferir_ferragem_info(data: Any) -> Optional[Dict[str, str]]:
    if isinstance(data, Mapping):
        mapping = data
        tipo_val = mapping.get("tipo")
        familia_val = mapping.get("familia")
        if tipo_val:
            familia_text = str(familia_val or "FERRAGENS").strip()
            if _normalize_token(familia_text) == _normalize_token("FERRAGENS"):
                return {"tipo": str(tipo_val).strip(), "familia": familia_text}
        for key in ("_child_source", "def_peca", "descricao", "descricao_livre", "_parent_label", "mat_default"):
            value = mapping.get(key)
            info = inferir_ferragem_info(value)
            if info:
                return info
        return None
    if isinstance(data, str):
        text = data.strip()
        if not text:
            return None
        info = _lookup_ferragem_info(text)
        if info:
            return info
        parts = [part.strip() for part in text.split("+") if part.strip()]
        for part in parts:
            info = _lookup_ferragem_info(part)
            if info:
                return info
        return None
    return None


def lista_mat_default_ferragens(
    session: Session,
    ctx: svc_dados_items.DadosItemsContext,
    tipo: Optional[str],
) -> List[str]:
    if not tipo:
        return []
    tipo_text = str(tipo).strip()
    if not tipo_text:
        return []

    stmt = (
        select(DadosItemsFerragem.grupo_ferragem)
        .where(
            DadosItemsFerragem.orcamento_id == ctx.orcamento_id,
            DadosItemsFerragem.item_id == ctx.item_id,
            func.lower(DadosItemsFerragem.tipo) == tipo_text.lower(),
        )
        .order_by(DadosItemsFerragem.linha, DadosItemsFerragem.grupo_ferragem)
    )

    valores = session.execute(stmt).scalars().all()
    vistos: Set[str] = set()
    resultado: List[str] = []
    for valor in valores:
        if not valor:
            continue
        texto = str(valor).strip()
        if not texto:
            continue
        token = _normalize_token(texto)
        if token in vistos:
            continue
        vistos.add(token)
        resultado.append(texto)

    if resultado:
        return resultado

    defaults = svc_dados_items.MENU_FIXED_GROUPS.get(svc_dados_items.MENU_FERRAGENS, ())
    keywords = _group_keywords_for_tipo(tipo_text)
    for grupo in defaults:
        texto = str(grupo).strip()
        if not texto:
            continue
        token = _normalize_token(texto)
        if token in vistos:
            continue
        if not keywords or all(keyword in token for keyword in keywords):
            vistos.add(token)
            resultado.append(texto)

    return resultado


def _collect_group_options(session: Session, ctx: svc_dados_items.DadosItemsContext, menu: str) -> List[str]:
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


def _coerce_checkbox_to_bool(value: Any) -> bool:
    """
    Converte valores provenientes da UI (ints, strings, Qt.CheckState, etc.) para booleano.
    Aceita:
      - None -> False
      - bool -> mantem
      - int/float/Decimal -> 0->False, outros->True (aceita 0,1,2)
      - str -> '1','0','true','false','sim','nao','checked','unchecked','on','off' etc.
    """
    if value is None:
        return False
    if isinstance(value, bool):
        return value

    # Qt.CheckState: Qt.Unchecked=0, Qt.PartiallyChecked=1, Qt.Checked=2
    # Aceitamos 2 como True, 1 como True (parcial) e 0 como False.
    if isinstance(value, (int, float, Decimal)):
        try:
            ival = int(value)
            return ival != 0
        except Exception:
            return bool(value)

    if isinstance(value, str):
        normalized = unicodedata.normalize("NFKD", value).encode("ASCII", "ignore").decode("ASCII")
        token = normalized.strip().lower()
        if token in {"1", "true", "t", "sim", "yes", "y", "on", "checked", "checked=true", "true"}:
            return True
        if token in {"0", "false", "f", "nao", "não", "no", "n", "off", "unchecked", ""}:
            return False
        # Qualquer string não-vazia assume True (compatibilidade com checkbox)
        return True

    # Fallback: truthiness
    return bool(value)


def _auto_dimensions_setting_key(user_id: int) -> str:
    return _AUTO_DIMENSION_SETTING_TEMPLATE.format(user_id=user_id)


def is_auto_dimension_enabled(session: Session, user_id: Optional[int]) -> bool:
    if not user_id:
        return False
    raw = get_setting(session, _auto_dimensions_setting_key(user_id), None)
    if raw is None:
        return False
    token = str(raw).strip().lower()
    return token in _AUTO_DIMENSION_TRUE_VALUES


def set_auto_dimension_enabled(session: Session, user_id: Optional[int], enabled: bool) -> None:
    if not user_id:
        return
    value = "1" if enabled else "0"
    set_setting(session, _auto_dimensions_setting_key(user_id), value)


def _normalize_def_peca_for_auto(def_peca: Optional[str]) -> str:
    if not def_peca:
        return ""
    text = unicodedata.normalize("NFKD", str(def_peca))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.upper().replace("_", " ")
    text = re.sub(r"[^A-Z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def sugerir_dimensoes_automaticas(def_peca: Optional[str]) -> Optional[Tuple[str, str]]:
    normalized = _normalize_def_peca_for_auto(def_peca)
    if not normalized:
        return None
    for prefix, comp_expr, larg_expr in _AUTO_DIMENSION_RULES:
        if normalized.startswith(prefix):
            return comp_expr, larg_expr
    return None


def aplicar_dimensoes_automaticas(linhas: Sequence[Dict[str, Any]]) -> None:
    for linha in linhas:
        sugestao = sugerir_dimensoes_automaticas(linha.get("def_peca"))
        if not sugestao:
            continue
        comp_expr, larg_expr = sugestao
        if linha.get("comp") in (None, ""):
            linha["comp"] = comp_expr
        if linha.get("larg") in (None, ""):
            linha["larg"] = larg_expr


def _is_divisao_def(def_peca: Optional[str]) -> bool:
    return _uppercase_no_accents(def_peca).strip() == _DIVISAO_LABEL_TOKEN


def _is_spp_context(und: Optional[str], def_peca: Optional[str]) -> bool:
    if (und or "").strip().upper() == "ML":
        return True
    raw = (def_peca or "").upper()
    if "{SPP}" in raw:
        return True
    texto = _uppercase_no_accents(def_peca)
    return texto.startswith("SPP")


def _format_formula_value(value: Any) -> Optional[str]:
    coerced = _coerce_dimensao_valor(value)
    if coerced is None:
        return None
    if abs(coerced - round(coerced)) < 1e-6:
        return str(int(round(coerced)))
    formatted = f"{coerced:.4f}".rstrip("0").rstrip(".")
    return formatted or str(coerced)


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


_ORLA_PATTERN = re.compile(r"\[(\d{4})]")


def _format_orla_value(valor: Any) -> Optional[str]:
    if valor in (None, "", False):
        return None
    try:
        if isinstance(valor, Decimal):
            dec = valor
        else:
            dec = Decimal(str(valor).replace(",", "."))
        dec = dec.quantize(Decimal("0.1"))
    except Exception:
        return None
    return f"{dec:.1f}"


def _build_orla_lookup(session: Session) -> Dict[str, str]:
    stmt = select(
        MateriaPrima.descricao_orcamento,
        MateriaPrima.esp_mp,
        MateriaPrima.familia,
    )
    mapping: Dict[str, str] = {}
    for descricao, espessura, familia in session.execute(stmt):
        familia_norm = (str(familia).strip().casefold() if familia else "")
        if familia_norm != "orlas":
            continue
        chave = (descricao or "").strip().casefold()
        if not chave:
            continue
        formato = _format_orla_value(espessura)
        if formato:
            mapping[chave] = formato
    return mapping


def obter_mapa_orlas(session: Session) -> Dict[str, str]:
    return _build_orla_lookup(session)


def _resolver_espessura_orla(
    codigo: str,
    linha: Mapping[str, Any],
    lookup: Mapping[str, str],
) -> Optional[float]:
    codigo = (codigo or "0").strip()
    if not codigo or codigo == "0":
        return None
    if codigo == "1":
        descricao = linha.get("orl_0_4")
        fallback = "0.4"
    elif codigo == "2":
        descricao = linha.get("orl_1_0")
        fallback = "1.0"
    else:
        return None
    chave = (descricao or "").strip().casefold()
    valor = lookup.get(chave)
    if not valor:
        valor = fallback
    try:
        return float(str(valor).replace(",", "."))
    except Exception:
        try:
            return float(fallback)
        except Exception:
            return None


def _aplicar_orla_espessuras(
    linha: Dict[str, Any],
    lookup: Mapping[str, str],
) -> Dict[str, Optional[float]]:
    resultado: Dict[str, Optional[float]] = {
        "orl_c1": None,
        "orl_c2": None,
        "orl_l1": None,
        "orl_l2": None,
    }
    def_peca = (linha.get("def_peca") or "")
    match = _ORLA_PATTERN.search(def_peca)
    if not match:
        linha.update(resultado)
        return resultado
    codigo = match.group(1)
    posicoes = [
        ("orl_c1", 0),
        ("orl_c2", 1),
        ("orl_l1", 2),
        ("orl_l2", 3),
    ]
    for chave, idx in posicoes:
        digito = codigo[idx] if idx < len(codigo) else "0"
        resultado[chave] = _resolver_espessura_orla(digito, linha, lookup)
    linha.update(resultado)
    return resultado


def calcular_espessuras_orla(session: Session, linha: Dict[str, Any]) -> Dict[str, Optional[float]]:
    lookup = _build_orla_lookup(session)
    return _aplicar_orla_espessuras(linha, lookup)


def aplicar_espessuras_orla(linha: Dict[str, Any], lookup: Mapping[str, str]) -> Dict[str, Optional[float]]:
    return _aplicar_orla_espessuras(linha, lookup)


def _parse_float_value(valor: Any) -> Optional[float]:
    """Converte diferentes representações numéricas (incluindo strings com vírgula) para float."""
    if valor in (None, "", False):
        return None
    if isinstance(valor, Decimal):
        try:
            return float(valor)
        except (TypeError, ValueError):
            return None
    if isinstance(valor, (int, float)):
        try:
            return float(valor)
        except (TypeError, ValueError):
            return None
    try:
        texto = str(valor).strip().replace(",", ".")
        if not texto:
            return None
        return float(texto)
    except (TypeError, ValueError):
        return None


def preencher_info_orlas_linha(
    session: Session,
    linha: Dict[str, Any],
    ref_cache: Optional[Dict[str, Tuple[float, float, Optional[str]]]] = None,
) -> None:
    """Preenche campos orl_ref_*, orl_pliq_* e orl_desp_* com base nas referências das colunas ORL 0.4/1.0."""
    if ref_cache is None:
        ref_cache = {}

    for side in ("c1", "c2", "l1", "l2"):
        esp_orla = _parse_float_value(linha.get(f"orl_{side}"))
        chosen_ref: Optional[str] = None
        pliq = 0.0
        desp = 0.0

        if esp_orla is not None:
            if abs(esp_orla - 0.4) < 0.01:
                chosen_ref = linha.get("orl_0_4")
            elif abs(esp_orla - 1.0) < 0.01:
                chosen_ref = linha.get("orl_1_0")
            else:
                chosen_ref = linha.get("orl_1_0") or linha.get("orl_0_4")

        if chosen_ref:
            chosen_ref = str(chosen_ref).strip() or None

        if chosen_ref:
            cache_key = chosen_ref
            if cache_key in ref_cache:
                preco_m2, desp_percent, matched = ref_cache[cache_key]
            else:
                preco_m2, desp_percent, matched = _obter_info_orla_por_ref(
                    session,
                    chosen_ref,
                    esp_esperada=esp_orla,
                )
                ref_cache[cache_key] = (preco_m2, desp_percent, matched)
            pliq = preco_m2 or 0.0
            desp = desp_percent or 0.0
            if matched:
                chosen_ref = matched

        linha[f"orl_ref_{side}"] = chosen_ref
        linha[f"orl_pliq_{side}"] = pliq
        linha[f"orl_desp_{side}"] = desp


def _get_orla_width_factor(esp_peca: Any) -> Tuple[float, float]:
    """Retorna (largura_mm, fator) com base na espessura da peça.

    Mantém compatibilidade com calculo_orlas.get_orla_width_factor.
    """
    try:
        if esp_peca is None:
            return 0, 0
        esp = float(esp_peca)
    except Exception:
        return 0, 0

    if esp <= 0:
        return 0, 0
    if esp < 20:
        return 23, 43
    if esp < 31:
        return 35, 28
    if esp < 40:
        return 45, 22
    return 60, 16


def _obter_info_orla_por_ref(
    session: Session,
    ref_candidate: Optional[str],
    esp_esperada: Optional[float] = None,
) -> Tuple[float, float, Optional[str]]:
    """Retorna (preco_m2, desp_percent, matched_ref_le) para a orla escolhida."""
    if not ref_candidate:
        return 0.0, 0.0, None

    chave = str(ref_candidate).strip()
    if not chave:
        return 0.0, 0.0, None

    stmt = (
        select(MateriaPrima)
        .where(func.coalesce(MateriaPrima.ref_le, "") == chave)
        .limit(1)
    )
    mat = session.execute(stmt).scalar_one_or_none()
    if mat:
        try:
            return float(mat.pliq or 0.0), float(getattr(mat, "desp", 0) or 0.0), (mat.ref_le or chave)
        except Exception:
            return 0.0, 0.0, None

    stmt2 = (
        select(MateriaPrima)
        .where(func.lower(func.coalesce(MateriaPrima.descricao_orcamento, "")) == chave.lower())
        .limit(1)
    )
    mat = session.execute(stmt2).scalar_one_or_none()
    if mat:
        try:
            return float(mat.pliq or 0.0), float(getattr(mat, "desp", 0) or 0.0), (mat.ref_le or chave)
        except Exception:
            return 0.0, 0.0, None

    if esp_esperada is not None:
        try:
            esp_val = float(esp_esperada)
        except Exception:
            esp_val = None
        if esp_val is not None:
            stmt3 = (
                select(MateriaPrima)
                .where(func.coalesce(MateriaPrima.familia, "").ilike("orlas"))
                .where(func.cast(MateriaPrima.esp_mp, func.FLOAT) == esp_val)
                .limit(1)
            )
            mat = session.execute(stmt3).scalar_one_or_none()
            if mat:
                try:
                    return float(mat.pliq or 0.0), float(getattr(mat, "desp", 0) or 0.0), (mat.ref_le or None)
                except Exception:
                    return 0.0, 0.0, None

    return 0.0, 0.0, None


def atualizar_orlas_custeio(session: Session, orcamento_id: int, item_id: int) -> None:
    """Recalcula ml/custo de orlas para as linhas do item informado."""
    if orcamento_id is None or item_id is None:
        return

    stmt = (
        select(CusteioItem)
        .where(
            CusteioItem.orcamento_id == orcamento_id,
            CusteioItem.item_id == item_id,
        )
        .order_by(CusteioItem.ordem, CusteioItem.id)
    )
    registros = session.execute(stmt).scalars().all()

    ref_cache: Dict[str, Tuple[float, float, Optional[str]]] = {}

    for reg in registros:
        comp_res_val = _parse_float_value(reg.comp_res)
        larg_res_val = _parse_float_value(reg.larg_res)
        esp_res_val = _parse_float_value(reg.esp_res)

        comp_res_mm = Decimal(str(comp_res_val)) if comp_res_val is not None else Decimal("0")
        larg_res_mm = Decimal(str(larg_res_val)) if larg_res_val is not None else Decimal("0")
        esp_res = esp_res_val or 0.0
        comp_m = (comp_res_mm / Decimal("1000")).quantize(Decimal("0.0001"))
        larg_m = (larg_res_mm / Decimal("1000")).quantize(Decimal("0.0001"))

        if _is_divisao_def(reg.def_peca):
            reg.area_m2_und = None
            reg.perimetro_und = None
        else:
            area_decimal = (comp_res_mm * larg_res_mm) / Decimal("1000000") if comp_res_mm and larg_res_mm else Decimal("0")
            perimetro_decimal = ((comp_res_mm + larg_res_mm) * Decimal("2")) / Decimal("1000") if comp_res_mm or larg_res_mm else Decimal("0")
            reg.area_m2_und = area_decimal.quantize(Decimal("0.0001"))
            reg.perimetro_und = perimetro_decimal.quantize(Decimal("0.0001"))

        if _is_divisao_def(reg.def_peca):
            reg.spp_ml_und = None
        elif _is_spp_context(getattr(reg, "und", None), getattr(reg, "def_peca", None)):
            if comp_res_val is not None:
                spp_decimal = (Decimal(str(comp_res_val)) / Decimal("1000")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                reg.spp_ml_und = spp_decimal
            else:
                reg.spp_ml_und = None
        else:
            reg.spp_ml_und = None

        soma_ml = Decimal("0")
        soma_custos = Decimal("0")

        for chave, dim_m in (("c1", comp_m), ("c2", comp_m), ("l1", larg_m), ("l2", larg_m)):
            esp_orla = _parse_float_value(getattr(reg, f"orl_{chave}"))
            ml_val = Decimal("0")
            custo_val = Decimal("0")

            if esp_orla not in (None, 0):
                ref_cand: Optional[str] = None
                if abs(esp_orla - 0.4) < 0.01:
                    ref_cand = reg.orl_0_4
                elif abs(esp_orla - 1.0) < 0.01:
                    ref_cand = reg.orl_1_0
                else:
                    ref_cand = reg.orl_1_0 or reg.orl_0_4

                if ref_cand:
                    ref_cand = str(ref_cand).strip() or None

                preco_m2 = 0.0
                desp_percent = 0.0
                matched_ref: Optional[str] = None
                if ref_cand:
                    cache_key = ref_cand
                    if cache_key in ref_cache:
                        preco_m2, desp_percent, matched_ref = ref_cache[cache_key]
                    else:
                        preco_m2, desp_percent, matched_ref = _obter_info_orla_por_ref(session, ref_cand, esp_esperada=esp_orla)
                        ref_cache[cache_key] = (preco_m2, desp_percent, matched_ref)

                ml_base = dim_m.quantize(Decimal("0.01"))

                try:
                    desp_pct = float(desp_percent or 0.0)
                    if desp_pct <= 1:
                        desp_pct *= 100.0
                except Exception:
                    desp_pct = 0.0

                if not desp_pct:
                    desp_pct = 8.0

                try:
                    desp_decimal = Decimal(str(desp_pct)) / Decimal("100")
                except Exception:
                    desp_decimal = Decimal("0.08")

                ml_unit_with_waste = (ml_base * (Decimal("1") + desp_decimal)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                qt_total_val = _parse_float_value(reg.qt_total) or 1.0
                qt_total = Decimal(str(qt_total_val))

                ml_val = (ml_unit_with_waste * qt_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                try:
                    _, fator = _get_orla_width_factor(esp_res)
                    if fator and preco_m2:
                        euro_por_ml = (Decimal(str(preco_m2)) / Decimal(str(fator))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    else:
                        euro_por_ml = Decimal("0.00")
                except Exception:
                    euro_por_ml = Decimal("0.00")

                custo_val = (ml_val * euro_por_ml).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            if chave == "c1":
                reg.ml_orl_c1 = ml_val
                reg.custo_orl_c1 = custo_val
            elif chave == "c2":
                reg.ml_orl_c2 = ml_val
                reg.custo_orl_c2 = custo_val
            elif chave == "l1":
                reg.ml_orl_l1 = ml_val
                reg.custo_orl_l1 = custo_val
            elif chave == "l2":
                reg.ml_orl_l2 = ml_val
                reg.custo_orl_l2 = custo_val

            soma_ml += ml_val
            soma_custos += custo_val

        reg.soma_total_ml_orla = soma_ml.quantize(Decimal("0.0001"))
        reg.custo_total_orla = soma_custos.quantize(Decimal("0.0001"))

    session.flush()


def _registro_precisa_recalculo(reg: CusteioItem) -> bool:
    campos_orla = (
        (reg.orl_c1, reg.ml_orl_c1, reg.custo_orl_c1),
        (reg.orl_c2, reg.ml_orl_c2, reg.custo_orl_c2),
        (reg.orl_l1, reg.ml_orl_l1, reg.custo_orl_l1),
        (reg.orl_l2, reg.ml_orl_l2, reg.custo_orl_l2),
    )
    for esp_val, ml_val, custo_val in campos_orla:
        if esp_val not in (None, 0, "") and (ml_val in (None, "") or custo_val in (None, "")):
            return True
    if any(
        reg_field in (None, "", 0)
        for reg_field in (reg.custo_total_orla, reg.soma_total_ml_orla)
    ):
        return True
    return False


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

    if any(_registro_precisa_recalculo(reg) for reg in registros):
        atualizar_orlas_custeio(session, orcamento_id, item_id)
        registros = session.execute(stmt).scalars().all()

    linhas: List[Dict[str, Any]] = []
    orla_lookup = _build_orla_lookup(session)
    ref_cache: Dict[str, Tuple[float, float, Optional[str]]] = {}
    for registro in registros:
        linha = _empty_row()
        linha["id"] = registro.id
        for spec in CUSTEIO_COLUMN_SPECS:
            key = spec["key"]
            if key == "id" or spec["type"] == "icon":
                continue

            if key in {"comp", "larg", "esp"}:
                expr_attr = f"{key}_expr"
                expr_val = getattr(registro, expr_attr, None)
                if expr_val not in (None, ""):
                    linha[key] = expr_val
                else:
                    linha[key] = _format_formula_value(getattr(registro, key, None))
                continue

            valor = getattr(registro, key, None)
            if spec["type"] == "numeric":
                linha[key] = _decimal_to_float(valor)
            elif spec["type"] == "bool":
                linha[key] = _coerce_checkbox_to_bool(valor)
            else:
                linha[key] = valor
        _aplicar_orla_espessuras(linha, orla_lookup)

        preencher_info_orlas_linha(session, linha, ref_cache)

        is_divisao = _is_divisao_def(linha.get("def_peca"))
        need_area = linha.get("area_m2_und") in (None, "", 0)
        need_perimetro = linha.get("perimetro_und") in (None, "", 0)
        if is_divisao:
            linha["area_m2_und"] = None
            linha["perimetro_und"] = None
        elif need_area or need_perimetro:
            comp_val = _parse_float_value(linha.get("comp_res"))
            larg_val = _parse_float_value(linha.get("larg_res"))
            if comp_val is not None and larg_val is not None:
                comp_m = comp_val / 1000.0
                larg_m = larg_val / 1000.0
                if need_area:
                    linha["area_m2_und"] = round(comp_m * larg_m, 4)
                if need_perimetro:
                    linha["perimetro_und"] = round(2 * (comp_m + larg_m), 4)
        if not is_divisao and _is_spp_context(linha.get("und"), linha.get("def_peca")):
            comp_val = _parse_float_value(linha.get("comp_res"))
            if comp_val is not None:
                linha["spp_ml_und"] = round(comp_val / 1000.0, 2)
            else:
                linha["spp_ml_und"] = None
        else:
            linha["spp_ml_und"] = None
        linhas.append(linha)

    return linhas


def salvar_custeio_items(
    session: Session,
    ctx: svc_dados_items.DadosItemsContext,
    linhas: Sequence[Mapping[str, Any]],
    dimensoes: Optional[Mapping[str, Any]] = None,
) -> None:
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
        comp_res_val = _parse_float_value(linha.get("comp_res"))
        larg_res_val = _parse_float_value(linha.get("larg_res"))
        is_divisao = _is_divisao_def(linha.get("def_peca"))
        if comp_res_val is not None and larg_res_val is not None and not is_divisao:
            comp_m = comp_res_val / 1000.0
            larg_m = larg_res_val / 1000.0
            area_val = round(comp_m * larg_m, 4)
            perimetro_val = round(2 * (comp_m + larg_m), 4)
            linha["area_m2_und"] = area_val
            linha["perimetro_und"] = perimetro_val
        elif is_divisao:
            linha["area_m2_und"] = None
            linha["perimetro_und"] = None
        if not is_divisao and _is_spp_context(linha.get("und"), linha.get("def_peca")):
            if comp_res_val is not None:
                linha["spp_ml_und"] = round(comp_res_val / 1000.0, 2)
            else:
                linha["spp_ml_und"] = None
        else:
            linha["spp_ml_und"] = None
        for spec in CUSTEIO_COLUMN_SPECS:
            key = spec["key"]
            if key == "id" or spec["type"] == "icon":
                continue

            if key in {"comp", "larg", "esp"}:
                expr_attr = f"{key}_expr"
                expr_val = linha.get(key)
                setattr(registro, expr_attr, _normalise_string(expr_val))
                resultado = linha.get(f"{key}_res")
                setattr(registro, key, _to_decimal(resultado))
                continue

            valor = linha.get(key)
            if spec["type"] == "numeric":
                setattr(registro, key, _to_decimal(valor))
            elif spec["type"] == "bool":
                coerced_bool = _coerce_checkbox_to_bool(valor)
                setattr(registro, key, coerced_bool)
            else:
                setattr(registro, key, _normalise_string(valor))
        session.add(registro)

    if dimensoes is not None:
        try:
            guardar_dimensoes(session, ctx, dimensoes)
        except Exception:
            # Se falhar, mantem estados anteriores mas nao interrompe a gravacao principal
            pass

    try:
        atualizar_orlas_custeio(session, ctx.orcamento_id, ctx.item_id)
    except Exception:
        # Não bloqueia o fluxo principal caso o cálculo das orlas falhe
        pass

    session.commit()


def gerar_linhas_para_selecoes(
    session: Session,
    ctx: svc_dados_items.DadosItemsContext,
    selecoes: Sequence[str],
) -> List[Dict[str, Any]]:
    linhas: List[Dict[str, Any]] = []
    orla_lookup = _build_orla_lookup(session)
    for selecao in selecoes:
        parts = [p.strip() for p in selecao.split(">") if p.strip()]
        if not parts:
            continue

        raw_def: str = parts[-1]

        tokens = [tok.strip() for tok in raw_def.split("+") if tok.strip()]
        parent_label = tokens[0] if tokens else raw_def
        child_tokens = tokens[1:] if len(tokens) > 1 else []

        linha = _empty_row()
        linha["descricao_livre"] = ""
        linha["def_peca"] = raw_def

        grupo_parent = grupo_por_def_peca(parent_label)
        material_parent = obter_material_por_grupo(session, ctx, grupo_parent)

        if material_parent:
            _preencher_linha_com_material(linha, material_parent, grupo_parent)
        else:
            linha["descricao"] = parent_label

        if linha.get("qt_mod") in (None, 0):
            linha["qt_mod"] = 1
        if linha.get("qt_und") in (None, 0):
            linha["qt_und"] = 1

        linha["_child_tokens"] = child_tokens
        linha["_parent_label"] = parent_label

        _aplicar_orla_espessuras(linha, orla_lookup)
        linhas.append(linha)

        if child_tokens:
            seen_counts: Dict[str, int] = {}
            for child_label in child_tokens:
                base = child_label.strip()
                if not base:
                    continue
                seen_counts[base] = seen_counts.get(base, 0) + 1
                suffix = seen_counts[base]
                def_child = f"{base}_{suffix}" if suffix > 1 else base

                child_row = _empty_row()
                child_row["descricao_livre"] = ""
                child_row["def_peca"] = def_child

                grupo_child = grupo_por_def_peca(base) or base
                material_child = obter_material_por_grupo(session, ctx, grupo_child)
                if not material_child:
                    material_child = obter_material_por_grupo(session, ctx, base)

                ferragem_info: Optional[Dict[str, str]] = None
                if not material_child:
                    ferragem_info = _lookup_ferragem_info(base)
                    if ferragem_info:
                        material_child = obter_ferragem_por_tipo(
                            session,
                            ctx,
                            ferragem_info.get("tipo"),
                            ferragem_info.get("familia"),
                        )

                if material_child:
                    grupo_hint = grupo_child or (ferragem_info.get("tipo") if ferragem_info else None)
                    _preencher_linha_com_material(child_row, material_child, grupo_hint)
                else:
                    child_row["descricao"] = base
                    if ferragem_info:
                        if ferragem_info.get("familia"):
                            child_row.setdefault("familia", ferragem_info["familia"])
                        if ferragem_info.get("tipo"):
                            child_row.setdefault("tipo", ferragem_info["tipo"])
                        if not child_row.get("mat_default"):
                            lista = lista_mat_default_ferragens(session, ctx, ferragem_info.get("tipo"))
                            if lista:
                                child_row["mat_default"] = lista[0]

                child_row["qt_mod"] = 1
                child_row["qt_und"] = None
                child_row["_parent_label"] = parent_label
                child_row["_child_source"] = base
                child_row["_regra_nome"] = base
                if (child_row.get("und") or "").strip().upper() == "ML":
                    inherited_comp = linha.get("comp")
                    if inherited_comp:
                        child_row["comp"] = inherited_comp

                _aplicar_orla_espessuras(child_row, orla_lookup)
                linhas.append(child_row)

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
    linha["acabamento_sup"] = getattr(material, "acabamento_sup", None) or getattr(material, "acabamento", None)
    linha["acabamento_inf"] = getattr(material, "acabamento_inf", None)

    comp_val = _format_formula_value(getattr(material, "comp", None))
    if comp_val is not None:
        linha["comp"] = comp_val
    larg_val = _format_formula_value(getattr(material, "larg", None))
    if larg_val is not None:
        linha["larg"] = larg_val
    esp_val = _format_formula_value(getattr(material, "esp", None))
    if esp_val is not None:
        linha["esp"] = esp_val

    linha["comp_mp"] = _decimal_to_float(getattr(material, "comp_mp", None))
    linha["larg_mp"] = _decimal_to_float(getattr(material, "larg_mp", None))
    linha["esp_mp"] = _decimal_to_float(getattr(material, "esp_mp", None))
    linha["nst"] = _coerce_checkbox_to_bool(getattr(material, "nao_stock", False))
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
            valores = _collect_group_options(session, ctx, menu)
            if valores:
                return valores

    menu = _menu_for_familia(familia)
    if menu:
        return list(svc_dados_items.MENU_FIXED_GROUPS.get(menu, ()))

    return list(svc_dados_items.MENU_FIXED_GROUPS.get(svc_dados_items.MENU_MATERIAIS, ()))


def lista_acabamento(
    session: Optional[Session] = None,
    ctx: Optional[svc_dados_items.DadosItemsContext] = None,
) -> List[str]:
    if session and ctx:
        valores = _collect_group_options(session, ctx, svc_dados_items.MENU_ACABAMENTOS)
        if valores:
            return valores
    return list(ACABAMENTO_DEFAULTS)


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


def _empty_dimensoes_dict() -> Dict[str, Optional[float]]:
    return {key: None for key in DIMENSION_KEY_ORDER}


def _coerce_dimensao_valor(valor: Any) -> Optional[float]:
    if valor in (None, "", False):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        try:
            text = str(valor).replace(",", ".")
            return float(text) if text else None
        except (TypeError, ValueError):
            return None


def carregar_dimensoes(
    session: Session,
    ctx: svc_dados_items.DadosItemsContext,
) -> Tuple[Dict[str, Optional[float]], bool]:
    if ctx is None:
        return _empty_dimensoes_dict(), False

    stmt = (
        select(CusteioItemDimensoes)
        .where(
            CusteioItemDimensoes.orcamento_id == ctx.orcamento_id,
            CusteioItemDimensoes.item_id == ctx.item_id,
            CusteioItemDimensoes.versao == ctx.versao,
            CusteioItemDimensoes.user_id == ctx.user_id,
        )
        .order_by(CusteioItemDimensoes.id.desc())
        .limit(1)
    )
    registro = session.execute(stmt).scalar_one_or_none()
    valores = _empty_dimensoes_dict()
    if registro:
        for chave in DIMENSION_KEY_ORDER:
            valores[chave] = _decimal_to_float(getattr(registro, chave.lower(), None))
    return valores, registro is not None


def guardar_dimensoes(
    session: Session,
    ctx: svc_dados_items.DadosItemsContext,
    valores: Mapping[str, Any],
) -> None:
    if ctx is None:
        return

    stmt = (
        select(CusteioItemDimensoes)
        .where(
            CusteioItemDimensoes.orcamento_id == ctx.orcamento_id,
            CusteioItemDimensoes.item_id == ctx.item_id,
            CusteioItemDimensoes.versao == ctx.versao,
            CusteioItemDimensoes.user_id == ctx.user_id,
        )
        .limit(1)
    )
    registro = session.execute(stmt).scalar_one_or_none()
    if registro is None:
        registro = CusteioItemDimensoes(
            orcamento_id=ctx.orcamento_id,
            item_id=ctx.item_id,
            cliente_id=ctx.cliente_id,
            user_id=ctx.user_id,
            ano=ctx.ano,
            num_orcamento=ctx.num_orcamento,
            versao=ctx.versao,
            ordem=0,
        )

    for chave in DIMENSION_KEY_ORDER:
        setattr(registro, chave.lower(), _to_decimal(valores.get(chave)))

    session.add(registro)
    session.flush()


def dimensoes_default_por_item(item: Optional[OrcamentoItem]) -> Dict[str, Optional[float]]:
    valores = _empty_dimensoes_dict()
    if not item:
        return valores
    valores["H"] = _decimal_to_float(getattr(item, "altura", None))
    valores["L"] = _decimal_to_float(getattr(item, "largura", None))
    valores["P"] = _decimal_to_float(getattr(item, "profundidade", None))
    return valores


def _group_info(grupo: Optional[str]) -> Optional[Dict[str, str]]:
    if not grupo:
        return None
    return GROUP_LOOKUP.get(_normalize_token(grupo))



def grupo_por_def_peca(def_peca: str) -> Optional[str]:
    if not def_peca:
        return None
    chave = LEAF_TO_GROUP.get(def_peca.strip().upper())
    if not chave:
        return None
    info = _group_info(chave)
    if info:
        return info["name"]
    return chave




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
