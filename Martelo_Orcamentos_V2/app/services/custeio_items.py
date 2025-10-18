from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import json
import re
import unicodedata
import uuid
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

DEFAULT_QT_RULES: Dict[str, Dict[str, Any]] = {
    "PES": {
        "matches": ["PES"],
        "expression": "4 if COMP < 650 and LARG < 800 else 6 if COMP >= 650 and LARG < 800 else 8",
        "tooltip": "4 se COMP<650 & LARG<800 | 6 se COMP≥650 & LARG<800 | 8 caso contrário",
    },
    "SUPORTE PRATELEIRA": {
        "matches": ["SUPORTE PRATELEIRA"],
        "expression": "8 if COMP >= 1100 and LARG >= 800 else 6 if COMP >= 1100 else 4",
        "tooltip": "4 por defeito | 6 se COMP≥1100 | 8 se COMP≥1100 & LARG≥800",
    },
    "VARAO SPP": {
        "matches": ["VARAO SPP", "VARAO"],
        "expression": "1",
        "tooltip": "1 varão por peça principal (COMP herdado para cálculo de ML).",
    },
    "SUPORTE TERMINAL VARAO": {
        "matches": ["SUPORTE TERMINAL VARAO"],
        "expression": "2",
        "tooltip": "2 suportes por varão.",
    },
    "DOBRADICA": {
        "matches": ["DOBRADICA"],
        "expression": "(2 if COMP < 850 else 3 if COMP < 1600 else 2 + int((COMP - 2 * 120) / 750)) + (1 if LARG >= 605 else 0)",
        "tooltip": "2 se COMP<850mm, 3 se COMP<1600mm, ≥1600mm: 2+(úteis/750mm) +1 se LARG≥605mm",
    },
    "PUXADOR": {
        "matches": ["PUXADOR"],
        "expression": "QT_PAI",
        "tooltip": "1 puxador por porta (quantidade = QT_und da peça principal).",
    },
}

RULES_SETTING_TEMPLATE = "custeio_rules_{orcamento}_{versao}"


def _clone_rules(rules: Mapping[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    cloned: Dict[str, Dict[str, Any]] = {}
    for key, value in rules.items():
        cloned[key] = deepcopy(value)
    return cloned


def load_qt_rules(session: Session, ctx: svc_dados_items.DadosItemsContext) -> Dict[str, Dict[str, Any]]:
    base = _clone_rules(DEFAULT_QT_RULES)
    if not ctx:
        return base
    setting_key = RULES_SETTING_TEMPLATE.format(orcamento=ctx.orcamento_id, versao=ctx.versao)
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


def save_qt_rules(session: Session, ctx: svc_dados_items.DadosItemsContext, rules: Mapping[str, Any]) -> None:
    if not ctx:
        return
    setting_key = RULES_SETTING_TEMPLATE.format(orcamento=ctx.orcamento_id, versao=ctx.versao)
    set_setting(session, setting_key, json.dumps(rules, ensure_ascii=False))
    session.flush()


def reset_qt_rules(session: Session, ctx: svc_dados_items.DadosItemsContext) -> None:
    if not ctx:
        return
    setting_key = RULES_SETTING_TEMPLATE.format(orcamento=ctx.orcamento_id, versao=ctx.versao)
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
    qt_pai = float(parent_row.get("qt_und") or 1.0)
    env = {
        "COMP": float(parent_row.get("comp") or 0),
        "LARG": float(parent_row.get("larg") or 0),
        "ESP": float(parent_row.get("esp") or 0),
        "COMP_MP": float(parent_row.get("comp_mp") or 0),
        "LARG_MP": float(parent_row.get("larg_mp") or 0),
        "ESP_MP": float(parent_row.get("esp_mp") or 0),
        "QT_PAI": qt_pai,
        "QT_DIV": divisor,
        "QT_MOD": parent_qt,
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
    if regra_nome == "PUXADOR":
        result = qt_pai * result
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
        "label": "GAVETA FRENTE",
        "group": "Gaveta Frente",
        "children": [
            {"label": "FRENTE GAVETA [2222]"},
            {"label": "FRENTE GAVETA [2222] + PUXADOR"},
        ],
    },
    {
        "label": "GAVETA CAIXA",
        "group": "Gaveta Caixa",
        "children": [
            {"label": "LATERAL GAVETA [2202]"},
            {"label": "TRASEIRA GAVETA [2000]"},
        ],
    },
    {
        "label": "GAVETA FUNDO",
        "group": "Gaveta Fundo",
        "children": [
            {"label": "FUNDO GAVETA [0022]"},
            {"label": "FUNDO GAVETA [0000]"},
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
    {"key": "acabamento", "label": "Acabamento", "type": "text", "editable": True},
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
    orla_lookup = _build_orla_lookup(session)
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
        _aplicar_orla_espessuras(linha, orla_lookup)
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
    orla_lookup = _build_orla_lookup(session)
    for selecao in selecoes:
        parts = [p.strip() for p in selecao.split(">") if p.strip()]
        if not parts:
            continue

        linha = _empty_row()
        linha["descricao_livre"] = ""
        linha["def_peca"] = parts[-1]

        grupo = grupo_por_def_peca(linha["def_peca"])
        material = obter_material_por_grupo(session, ctx, grupo)

        if material:
            _preencher_linha_com_material(linha, material, grupo)
        else:
            linha["descricao"] = linha["def_peca"]
        if linha.get("qt_mod") in (None, 0):
            linha["qt_mod"] = 1
        if linha.get("qt_und") in (None, 0):
            linha["qt_und"] = 1
        _aplicar_orla_espessuras(linha, orla_lookup)
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
