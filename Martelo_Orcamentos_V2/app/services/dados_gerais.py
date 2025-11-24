from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence
import logging
from datetime import datetime

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
    "Divisorias",
    "Tetos",
    "Fundos",
    "Prateleiras Fixas",
    "Prateleiras Amoviveis",
    "Prateleiras Parede",
    "Prateleiras",
    "Portas Abrir 1",
    "Portas Abrir 2",
    "Paineis",
    "Laterais Acabamento",
    "Tetos Acabamento",
    "Fundos Acabamento",
    "Costas Acabamento",
    "Prateleiras Acabamento",
    "Paineis Acabamento",
    "Remates Verticais",
    "Remates Horizontais",
    "Guarnicoes Produzidas",
    "Enchimentos Guarnicoes",
    "Rodape AGL",
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

FERRAGENS_GRUPOS: Sequence[str] = (
    "Dobradica Reta",
    "Dobradica Canto Sego",
    "Dobradica Abertura Total",
    "Dobradica 1",
    "Dobradica 2",
    "Suporte Prateleira 1",
    "Suporte Prateleira 2",
    "Suporte Parede",
    "Suporte Terminal Varao",
    "Suporte Central Varao",
    "Varao SPP",
    "Varao Trombone",
    "Varao Extensivel",
    "Terminal Perfil Lava Louca",
    "Perfil Lava Louca SPP",
    "Rodape PVC SPP",
    "Canto Rodape PVC",
    "Grampas Rodape PVC",
    "Pes 1",
    "Pes 2",
    "Pes 3",
    "Corredica Invisivel",
    "Corredica Lateral Metalica",
    "Corredica 1",
    "Corredica 2",
    "Puxador Tic Tac",
    "Puxador Fresado J",
    "Puxador STD 1",
    "Puxador STD 2",
    "Puxador Gola C SPP",
    "Puxador Gola J SPP",
    "Puxador Perfil SPP 1",
    "Puxador Perfil SPP 2",
    "Puxador Perfil SPP 3",
    "Sistema Basculante 1",
    "Sistema Basculante 2",
    "Aventos 1",
    "Aventos 2",
    "Amortecedor",
    "Balde Lixo",
    "Cesto Canto Feijao",
    "Cesto Canto 1",
    "Cesto Canto 2",
    "Porta Talheres",
    "Porta Calcas",
    "Porta Garrafas",
    "Tulha 1",
    "Tulha 2",
    "Fundo Aluminio 1",
    "Fundo Aluminio 2",
    "Fundo Plastico Frigorifico",
    "Grelha Veludo",
    "Salva Sifao",
    "Sapateira",
    "Acessorio Cozinha 1",
    "Acessorio Cozinha 2",
    "Acessorio Cozinha 3",
    "Calha Led 1 SPP",
    "Calha Led 2 SPP",
    "Fita Led 1 SPP",
    "Fita Led 2 SPP",
    "Transformador 1",
    "Transformador 2",
    "Cabos Led 1",
    "Cabos Led 2",
    "Cabos Led 3",
    "Sensor Led 1",
    "Sensor Led 2",
    "Sensor Led 3",
    "Iluminacao 1",
    "Iluminacao 2",
    "Iluminacao 3",
    "Ferragens Diversas 1",
    "Ferragens Diversas 2",
    "Ferragens Diversas 3",
    "Ferragens Diversas 4",
    "Ferragens Diversas 5",
    "Ferragens Diversas 6 SPP",
    "Ferragens Diversas 7 SPP",
)

SISTEMAS_CORRER_GRUPOS: Sequence[str] = (
    "Puxador Vertical 1",
    "Puxador Vertical 2",
    "Calha Superior 1 SPP",
    "Calha Superior 2 SPP",
    "Calha Inferior 1 SPP",
    "Calha Inferior 2 SPP",
    "Perfil Horizontal H SPP",
    "Perfil Horizontal U SPP",
    "Perfil Horizontal L SPP",
    "Painel Porta Correr 1",
    "Painel Porta Correr 2",
    "Painel Porta Correr 3",
    "Painel Porta Correr 4",
    "Painel Porta Correr 5",
    "Painel Espelho Correr 1",
    "Painel Espelho Correr 2",
    "Painel Espelho Correr 3",
    "Vidro",
    "Rodizio Sup 1",
    "Rodizio Sup 2",
    "Rodizio Inf 1",
    "Rodizio Inf 2",
    "Acessorio 1",
    "Acessorio 2",
    "Acessorio 3",
    "Acessorio 4",
    "Acessorio 5",
    "Acessorio 6",
    "Acessorio 7 SPP",
    "Acessorio 8 SPP",
)

SISTEMAS_CORRER_PLACAS: Sequence[str] = (
    "Painel Porta Correr 1",
    "Painel Porta Correr 2",
    "Painel Porta Correr 3",
    "Painel Porta Correr 4",
    "Painel Porta Correr 5",
    "Painel Espelho Correr 1",
    "Painel Espelho Correr 2",
    "Painel Espelho Correr 3",
    "Vidro",
)

SISTEMAS_CORRER_PLACAS_KEYS = {name.strip().casefold() for name in SISTEMAS_CORRER_PLACAS}

ACABAMENTOS_GRUPOS: Sequence[str] = (
    "Lacar Face Sup",
    "Lacar Face Inf",
    "Lacar 2 Faces",
    "Verniz Face Sup",
    "Verniz Face Inf",
    "Verniz 2 Faces",
    "Acabamento Face Sup 1",
    "Acabamento Face Sup 2",
    "Acabamento Face Inf 1",
    "Acabamento Face Inf 2",
)

FERRAGENS_GRUPOS: Sequence[str] = (
    "Dobradica Reta",
    "Dobradica Canto Sego",
    "Dobradica Abertura Total",
    "Dobradica 1",
    "Dobradica 2",
    "Suporte Prateleira 1",
    "Suporte Prateleira 2",
    "Suporte Parede",
    "Suporte Terminal Varao",
    "Suporte Central Varao",
    "Varao SPP",
    "Terminal Perfil Lava Louca",
    "Perfil Lava Louca SPP",
    "Rodape PVC SPP",
    "Canto Rodape PVC",
    "Grampas Rodape PVC",
    "Pes 1",
    "Pes 2",
    "Pes 3",
    "Corredica Invisivel",
    "Corredica Lateral Metalica",
    "Corredica 1",
    "Corredica 2",
    "Puxador Tic Tac",
    "Puxador Fresado J",
    "Puxador STD 1",
    "Puxador STD 2",
    "Puxador Perfil SPP 1",
    "Puxador Perfil SPP 2",
    "Puxador Perfil SPP 3",
    "Sistema Basculante 1",
    "Sistema Basculante 2",
    "Aventos 1",
    "Aventos 2",
    "Balde Lixo",
    "Canto Cozinha 1",
    "Canto Cozinha 2",
    "Porta Talheres",
    "Porta Calcas",
    "Tulha",
    "Fundo Aluminio",
    "Grelha Veludo",
    "Acessorio Cozinha 1",
    "Acessorio Cozinha 2",
    "Acessorio Cozinha 3",
    "Calha Led 1 SPP",
    "Calha Led 2 SPP",
    "Fita Led 1 SPP",
    "Fita Led 2 SPP",
    "Transformador 1",
    "Transformador 2",
    "Cabos Led 1",
    "Cabos Led 2",
    "Cabos Led 3",
    "Sensor Led 1",
    "Sensor Led 2",
    "Sensor Led 3",
    "Iluminacao 1",
    "Iluminacao 2",
    "Iluminacao 3",
    "Ferragens Diversas 1",
    "Ferragens Diversas 2",
    "Ferragens Diversas 3",
    "Ferragens Diversas 4",
    "Ferragens Diversas 5",
    "Ferragens Diversas 6 SPP",
    "Ferragens Diversas 7 SPP",
)

SISTEMAS_CORRER_GRUPOS: Sequence[str] = (
    "Puxador Vertical 1",
    "Puxador Vertical 2",
    "Calha Superior 1 SPP",
    "Calha Superior 2 SPP",
    "Calha Inferior 1 SPP",
    "Calha Inferior 2 SPP",
    "Perfil Horizontal H SPP",
    "Perfil Horizontal U SPP",
    "Perfil Horizontal L SPP",
    "Painel Porta Correr 1",
    "Painel Porta Correr 2",
    "Painel Porta Correr 3",
    "Painel Porta Correr 4",
    "Painel Porta Correr 5",
    "Painel Espelho Correr 1",
    "Painel Espelho Correr 2",
    "Painel Espelho Correr 3",
    "Vidro",
    "Rodizio Sup 1",
    "Rodizio Sup 2",
    "Rodizio Inf 1",
    "Rodizio Inf 2",
    "Acessorio 1",
    "Acessorio 2",
    "Acessorio 3",
    "Acessorio 4",
    "Acessorio 5",
    "Acessorio 6",
    "Acessorio 7 SPP",
    "Acessorio 8 SPP",
)

ACABAMENTOS_GRUPOS: Sequence[str] = (
    "Lacar Face Sup",
    "Lacar Face Inf",
    "Lacar 2 Faces",
    "Verniz Face Sup",
    "Verniz Face Inf",
    "Verniz 2 Faces",
    "Acabamento Face Sup 1",
    "Acabamento Face Sup 2",
    "Acabamento Face Inf 1",
    "Acabamento Face Inf 2",
)

# --- CONSTANTES DE MENU (IDs estáveis) ---------------------------------------
# IMPORTANTE: estas constantes têm de vir ANTES de QUALQUER mapeamento que as use.

MENU_MATERIAIS = "materiais"
MENU_FERRAGENS = "ferragens"
MENU_SIS_CORRER = "sistemas_correr"
MENU_ACABAMENTOS = "acabamentos"

# --- MAPAS BÁSICOS (usam os IDs acima) ---------------------------------------

MENU_FIXED_GROUPS = {
    # garante a lista base (linhas "fixas") por cada menu
    MENU_MATERIAIS: MATERIAIS_GRUPOS,
    MENU_FERRAGENS: FERRAGENS_GRUPOS,
    MENU_SIS_CORRER: SISTEMAS_CORRER_GRUPOS,
    MENU_ACABAMENTOS: ACABAMENTOS_GRUPOS,
}

MENU_PRIMARY_FIELD = {
    # identifica a "chave" primária de cada tabela do menu
    MENU_MATERIAIS: "grupo_material",
    MENU_FERRAGENS: "grupo_ferragem",
    MENU_SIS_CORRER: "grupo_sistema",
    MENU_ACABAMENTOS: "grupo_acabamento",
}

MENU_DEFAULT_FAMILIA = {
    MENU_MATERIAIS: "PLACAS",
    MENU_FERRAGENS: "FERRAGENS",
    MENU_SIS_CORRER: "FERRAGENS",
    MENU_ACABAMENTOS: "ACABAMENTOS",
}

MODEL_COMMON_FIELDS = ("ref_le", "descricao_material", "preco_tab", "preco_liq", "margem", "desconto", "und")
GLOBAL_PREFIX = "__GLOBAL__|"

LAYOUT_NAMESPACE = "dados_gerais"

def _familia_for_grupo(menu: str, grupo: Optional[str], default: Optional[str] = None) -> str:
    """
    Decide a familia padrão para um grupo. Mantém compatibilidade com a lógica
    anterior: se for sistemas_correr e o grupo estiver em SISTEMAS_CORRER_PLACAS,
    devolve 'PLACAS', senão 'FERRAGENS' ou o default fornecido.
    """
    base = default or MENU_DEFAULT_FAMILIA.get(menu, "PLACAS")
    if not grupo:
        return base
    if menu == MENU_SIS_CORRER:
        key = str(grupo).strip().casefold()
        if key in SISTEMAS_CORRER_PLACAS_KEYS:
            return "PLACAS"
        return "FERRAGENS"
    return base

def _familia_for_grupo(menu: str, grupo: Optional[str], default: Optional[str] = None) -> str:
    base = default or MENU_DEFAULT_FAMILIA.get(menu, "PLACAS")
    if not grupo:
        return base
    if menu == MENU_SIS_CORRER:
        key = str(grupo).strip().casefold()
        if key in SISTEMAS_CORRER_PLACAS_KEYS:
            return "PLACAS"
        return "FERRAGENS"
    return base

LEGACY_TO_NEW: Dict[str, str] = {
    # normalização de nomes antigos -> novos
    "Mat_Costas": "Costas",
    "Mat_Laterais": "Laterais",
    "Mat_Divisorias": "Divisorias",
    "Mat_Tetos": "Tetos",
    "Mat_Fundos": "Fundos",
    "Mat_Prat_Fixas": "Prateleiras Fixas",
    "Mat_Prat_Amoviveis": "Prateleiras Amoviveis",
    "Mat_Prat_Parede": "Prateleiras Parede",
    "Mat_Prateleiras": "Prateleiras",
    "Mat_Portas_Abrir": "Portas Abrir 1",
    "Mat_Portas_Correr": "Portas Abrir 2",
    "Mat_Paineis": "Paineis",
    "Mat_Laterais_Acabamento": "Laterais Acabamento",
    "Mat_Tetos_Acabamento": "Tetos Acabamento",
    "Mat_Fundos_Acabamento": "Fundos Acabamento",
    "Mat_Costas_Acabamento": "Costas Acabamento",
    "Mat_Prat_Acabamento": "Prateleiras Acabamento",
    "Mat_Tampos_Acabamento": "Paineis Acabamento",
    "Mat_Remates_Verticais": "Remates Verticais",
    "Mat_Remates_Horizontais": "Remates Horizontais",
    "Mat_Guarnicoes_Verticais": "Guarnicoes Produzidas",
    "Mat_Guarnicoes_Horizontais": "Enchimentos Guarnicoes",
    "Mat_Enchimentos_Guarnicao": "Enchimentos Guarnicoes",
    "Mat_Rodape_AGL": "Rodape AGL",
    "Mat_Gavetas_Frentes": "Gaveta Frente",
    "Mat_Gavetas_Caixa": "Gaveta Caixa",
    "Mat_Gavetas_Fundo": "Gaveta Fundo",
    "Mat_Prumos": "Prumos",
    "Mat_Travessas": "Travessas",
    "Mat_Livre_1": "Material_Livre_1",
    "Mat_Livre_2": "Material_Livre_2",
    "Mat_Livre_3": "Material_Livre_3",
    "Mat_Livre_4": "Material_Livre_4",
    "Mat_Livre_5": "Material_Livre_5",
    "Mat_Livre_6": "Material_Livre_6",
    "Mat_Livre_7": "Material_Livre_7",
    "Mat_Livre_8": "Material_Livre_8",
    "Mat_Livre_9": "Material_Livre_9",
    "Mat_Livre_10": "Material_Livre_10",
    "Portas Abrir": "Portas Abrir 1",
    "Portas Correr": "Portas Abrir 2",
}


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
        "grupo_ferragem",
        "descricao",
        "ref_le",
        "descricao_material",
        "preco_tab",
        "preco_liq",
        "margem",
        "desconto",
        "und",
        "desp",
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
    MENU_SIS_CORRER: (
        "grupo_sistema",
        "descricao",
        "ref_le",
        "descricao_material",
        "preco_tab",
        "preco_liq",
        "margem",
        "desconto",
        "und",
        "desp",
        "tipo",
        "familia",
        "comp_mp",
        "larg_mp",
        "esp_mp",
        "orl_0_4",
        "orl_1_0",
        "id_mp",
        "nao_stock",
        "reserva_1",
        "reserva_2",
        "reserva_3",
    ),
    MENU_ACABAMENTOS: (
        "grupo_acabamento",
        "descricao",
        "ref_le",
        "descricao_material",
        "preco_tab",
        "preco_liq",
        "margem",
        "desconto",
        "und",
        "desp",
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
}

# Tipagem por campo (para coercao/conversão de tipos)
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
        "percent": ("margem", "desconto", "desp"),
        "integer": ("comp_mp", "larg_mp", "esp_mp"),
        "decimal": (),
        "bool": ("nao_stock",),
    },
    MENU_SIS_CORRER: {
        "money": ("preco_tab", "preco_liq"),
        "percent": ("margem", "desconto", "desp"),
        "integer": ("comp_mp", "larg_mp", "esp_mp"),
        "decimal": (),
        "bool": ("nao_stock",),
    },
    MENU_ACABAMENTOS: {
        "money": ("preco_tab", "preco_liq"),
        "percent": ("margem", "desconto", "desp"),
        "integer": ("comp_mp", "larg_mp", "esp_mp"),
        "decimal": (),
        "bool": ("nao_stock",),
    },
}

# Mapa menu -> modelo ORM
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


def _strip_accents(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def _normalize_number_text(value: Any, *, allow_percent: bool = False) -> str:
    text = _strip_accents(str(value))
    text = text.replace("\u20ac", "").replace("EUR", "").replace(" ", "")
    if allow_percent:
        text = text.replace("%", "")
    text = text.replace(",", ".")
    return text


def _ensure_decimal(value: Any) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    text_value = _normalize_number_text(value)
    if not text_value:
        return None
    try:
        dec = Decimal(text_value)
        return dec.quantize(Decimal("0.0001"))
    except Exception:
        return None


def _ensure_percent(value: Any) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    text_value = _normalize_number_text(value, allow_percent=True)
    if not text_value:
        return None
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
        if field == "nao_stock":  # Tratamento especial para nao_stock
            if isinstance(value, str):
                normalized = _strip_accents(value).strip().lower()
                if normalized in ("true", "sim", "yes", "1"):
                    return 1
                if normalized in ("false", "nao", "no", "0"):
                    return 0
            if isinstance(value, (int, float, Decimal)):
                try:
                    return 1 if bool(Decimal(str(value))) else 0
                except Exception:
                    return 0
            return 1 if bool(value) else 0
        else:
            if isinstance(value, str):
                normalized = _strip_accents(value).strip().lower()
                if normalized in ("true", "sim", "yes", "1"):
                    return True
                if normalized in ("false", "nao", "no", "0"):
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
        raise ValueError("Orcamento nao encontrado")
    if not orc.client_id:
        raise ValueError("Orcamento sem cliente associado")
    cliente = db.get(Client, orc.client_id)
    if not cliente:
        raise ValueError("Cliente associado nao encontrado")
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
        primary = MENU_PRIMARY_FIELD.get(menu)
        if field == primary:
            if menu == MENU_MATERIAIS:
                coerced = _normalize_grupo_material(coerced)
            else:
                coerced = _strip_accents(str(coerced)) if coerced else coerced
        if field == "familia":
            coerced = coerced or MENU_DEFAULT_FAMILIA.get(menu, "PLACAS")
        result[field] = coerced
    return result


def _default_rows_for_menu(menu: str) -> List[Dict[str, Any]]:
    defaults: List[Dict[str, Any]] = []
    primary = MENU_PRIMARY_FIELD[menu]
    fixed = MENU_FIXED_GROUPS[menu]
    default_familia = MENU_DEFAULT_FAMILIA.get(menu, "PLACAS")
    for ordem, name in enumerate(fixed):
        familia_padrao = _familia_for_grupo(menu, name, default_familia)
        row: Dict[str, Any] = {
            "id": None,
            "ordem": ordem,
            primary: name,
        }
        for field in MENU_FIELDS[menu]:
            if field not in row:
                if field == "familia":
                    row[field] = familia_padrao
                elif field == "nao_stock":
                    row[field] = False
                else:
                    row[field] = None
        defaults.append(row)
    return defaults


DEFAULT_ROWS_BY_MENU: Dict[str, List[Dict[str, Any]]] = {
    menu: _default_rows_for_menu(menu) for menu in MENU_FIXED_GROUPS
}


def _ensure_menu_rows(menu: str, rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    fixed = MENU_FIXED_GROUPS.get(menu)
    if not fixed:
        return [dict(row) for row in rows or []]
    primary = MENU_PRIMARY_FIELD[menu]
    default_familia = MENU_DEFAULT_FAMILIA.get(menu, "PLACAS")
    existing: Dict[str, Dict[str, Any]] = {}
    extras: List[Dict[str, Any]] = []
    for row in rows or []:
        row_dict = dict(row)
        value = row_dict.get(primary)
        name: Optional[str]
        if menu == MENU_MATERIAIS:
            name = _normalize_grupo_material(value)
        else:
            name = _strip_accents(str(value)).strip() if value else None
        if not name:
            continue
        row_dict[primary] = name
        if name not in fixed and name not in existing:
            extras.append(row_dict)
        existing[name] = row_dict
    defaults = {row[primary]: dict(row) for row in DEFAULT_ROWS_BY_MENU[menu]}
    ensured: List[Dict[str, Any]] = []
    for ordem, name in enumerate(fixed):
        base = defaults.get(name, {primary: name, "ordem": ordem})
        merged = dict(base)
        familia_padrao = _familia_for_grupo(menu, name, default_familia)
        row = existing.get(name)
        if row:
            merged.update(row)
        merged["ordem"] = ordem
        merged.setdefault("id", row.get("id") if row else None)
        if "familia" in merged and not merged.get("familia"):
            merged["familia"] = familia_padrao
        if "nao_stock" in merged:
            merged["nao_stock"] = bool(merged.get("nao_stock", False))
        for field in MENU_FIELDS[menu]:
            merged.setdefault(field, None)
        ensured.append(merged)
    for extra in extras:
        extra_row = dict(extra)
        extra_row.setdefault("id", extra_row.get("id"))
        extra_row.setdefault("ordem", len(ensured))
        if "familia" in extra_row and not extra_row.get("familia"):
            extra_row["familia"] = _familia_for_grupo(menu, extra_row.get(primary), default_familia)
        if "nao_stock" in extra_row:
            extra_row["nao_stock"] = bool(extra_row.get("nao_stock", False))
        for field in MENU_FIELDS[menu]:
            extra_row.setdefault(field, None)
        ensured.append(extra_row)
    return ensured

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
        data[menu] = _ensure_menu_rows(menu, [_row_to_dict(menu, row) for row in rows])
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
    primary = MENU_PRIMARY_FIELD.get(menu)
    default_familia = MENU_DEFAULT_FAMILIA.get(menu, "PLACAS")
    grupo_valor = row.get(primary) if primary else None
    for field in MENU_FIELDS[menu]:
        value = row.get(field)
        if field == primary:
            if menu == MENU_MATERIAIS:
                value = _normalize_grupo_material(value)
            else:
                value = _strip_accents(str(value)) if value else value
            grupo_valor = value
        if field == "familia":
            value = value or _familia_for_grupo(menu, grupo_valor, default_familia)
        coerced = _coerce_field(menu, field, value)
        if field == "preco_liq" and coerced is None:
            coerced = calcular_preco_liq(row.get("preco_tab"), row.get("margem"), row.get("desconto"))
        payload[field] = coerced
    if menu != MENU_MATERIAIS:
        if payload.get("preco_liq") is None:
            payload["preco_liq"] = calcular_preco_liq(row.get("preco_tab"), row.get("margem"), row.get("desconto"))
    return payload


def _coerce(menu: str, field: str, value: Any) -> Any:
    """
    Wrapper seguro para _coerce_field. Garante que o campo 'nao_stock'
    fica sempre guardado como 0/1, aceita True/False, '1'/'0', 'on'/'off'.
    Se _coerce_field existir mais abaixo, chamamos; senão fazemos fallback.
    """
    # fallback simples para nao_stock (garante 0/1)
    if field == "nao_stock":
        # Normalizar vários tipos possíveis
        if isinstance(value, bool):
            return int(value)
        if value is None:
            return 0
        # aceitar strings '1','0','true','false','on','off'
        s = str(value).strip().lower()
        if s in ("1", "true", "yes", "on"):
            return 1
        return 0

    # se existir a função _coerce_field definida mais abaixo, usa-a
    try:
        return _coerce_field(menu, field, value)  # type: ignore[name-defined]
    except NameError:
        # fallback genérico (devolve o valor tal como está)
        return value

def guardar_dados_gerais(
    db: Session,
    ctx: "DadosGeraisContext",  # o tipo context definido neste ficheiro
    payload: Mapping[str, Sequence[Mapping[str, Any]]],
) -> None:
    """
    Guarda os 'dados gerais' (materiais, ferragens, sistemas_correr, acabamentos, ...)
    - Para cada menu (p.ex. 'materiais', 'ferragens'...) substitui as linhas existentes
      para o mesmo contexto (cliente_id / ano / num_orcamento / versao).
    - 'nao_stock' é tratado pelo _coerce(...) (igual ao que já faz para os items).
    """
    # Percorre os menus (materiais, ferragens, sistemas_correr, acabamentos, ...)
    for menu, rows in payload.items():
        # Se for um menu desconhecido, ignora
        if menu not in MODEL_MAP:
            continue

        model = MODEL_MAP[menu]

        # Remove as linhas existentes para o mesmo contexto (cliente / ano / nº orcamento / versão)
        # (dados gerais não têm item_id nem orcamento_id — usamos o conjunto cliente/ano/num_orcamento/versao)
        db.execute(
            delete(model).where(
                model.cliente_id == ctx.cliente_id,
                model.ano == ctx.ano,
                model.num_orcamento == ctx.num_orcamento,
                model.versao == ctx.versao,
            )
        )

        # Se não houver linhas, continua para o próximo menu
        if not rows:
            continue

        # Insere cada linha (mantendo 'ordem' se existir, ou atribuindo o enumerado)
        for ordem, row in enumerate(rows):
            body = dict(row)
            body.setdefault("ordem", ordem)

            # Campos comuns ao contexto de "dados gerais"
            instance_kwargs: Dict[str, Any] = {
                "cliente_id": ctx.cliente_id,
                "user_id": ctx.user_id,
                "ano": ctx.ano,
                "num_orcamento": ctx.num_orcamento,
                "versao": ctx.versao,
                "ordem": body.get("ordem", ordem) or ordem,
            }

            # Para cada campo do menu (MENU_FIELDS define a lista de campos permitidos),
            # coerciamos o valor com _coerce(menu, field, value) (já existente no ficheiro)
            for field in MENU_FIELDS[menu]:
                value = body.get(field)
                coerced = _coerce(menu, field, value)
                instance_kwargs[field] = coerced

            # Adiciona a nova instância ao sessão
            db.add(model(**instance_kwargs))

    # Faz commit ao final de tudo
    db.commit()


def _prepare_model_line(menu: str, row: Mapping[str, Any], ordem: int) -> Dict[str, Any]:
    sanitized: Dict[str, Any] = {"ordem": ordem}
    primary = MENU_PRIMARY_FIELD.get(menu)
    default_familia = MENU_DEFAULT_FAMILIA.get(menu, "PLACAS")
    grupo_valor = row.get(primary) if primary else None
    # apenas os campos relevantes para o modelo (colunas visíveis comuns)
    fields_to_keep = [primary] if primary else []
    fields_to_keep += list(MODEL_COMMON_FIELDS)
    for field in fields_to_keep:
        value = row.get(field)
        if field == primary:
            if menu == MENU_MATERIAIS:
                value = _normalize_grupo_material(value)
            else:
                value = _strip_accents(str(value)) if value else value
            grupo_valor = value
        if field == "familia":
            value = value or _familia_for_grupo(menu, grupo_valor, default_familia)
        coerced = _coerce_field(menu, field, value)
        if field == "preco_liq" and coerced is None:
            coerced = calcular_preco_liq(row.get("preco_tab"), row.get("margem"), row.get("desconto"))
        sanitized[field] = _json_ready(coerced)
    return sanitized


def _deserialize_model_line(menu: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
    row: Dict[str, Any] = {"ordem": int(payload.get("ordem", 0))}
    primary = MENU_PRIMARY_FIELD.get(menu)
    default_familia = MENU_DEFAULT_FAMILIA.get(menu, "PLACAS")
    fields_to_keep = [primary] if primary else []
    fields_to_keep += list(MODEL_COMMON_FIELDS)
    for field in fields_to_keep:
        value = payload.get(field)
        coerced = _coerce_field(menu, field, value)
        if menu == MENU_MATERIAIS and field == "preco_liq" and coerced is None:
            coerced = calcular_preco_liq(payload.get("preco_tab"), payload.get("margem"), payload.get("desconto"))
        row[field] = coerced
    if menu == MENU_MATERIAIS:
        row["grupo_material"] = _normalize_grupo_material(row.get("grupo_material"))
    if "familia" in row:
        row["familia"] = row.get("familia") or _familia_for_grupo(menu, row.get(primary), default_familia)
    return row


def guardar_modelo(
    db: Session,
    *,
    user_id: int,
    tipo_menu: str,
    nome_modelo: str,
    linhas: Sequence[Mapping[str, Any]],
    is_global: bool = False,
    add_timestamp: bool = False,
    replace_id: Optional[int] = None,
) -> DadosGeraisModelo:
    if tipo_menu not in MODEL_MAP:
        raise ValueError("Tipo de menu invalido")
    nome_limpo = nome_modelo.strip()
    if add_timestamp:
        nome_limpo = f"{nome_limpo} ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
    if is_global:
        nome_limpo = f"{GLOBAL_PREFIX}{nome_limpo}"
    if not nome_limpo:
        raise ValueError("Nome do modelo obrigatorio")
    if replace_id:
        modelo = db.execute(
            select(DadosGeraisModelo).where(
                DadosGeraisModelo.id == replace_id,
                DadosGeraisModelo.user_id == user_id,
            )
        ).scalar_one_or_none()
        if not modelo:
            raise ValueError("Modelo nao encontrado para substituir")
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
    stmt = select(DadosGeraisModelo).where(
        (DadosGeraisModelo.user_id == user_id) | (DadosGeraisModelo.nome_modelo.startswith(GLOBAL_PREFIX))
    )
    if tipo_menu:
        stmt = stmt.where(DadosGeraisModelo.tipo_menu == tipo_menu)
    stmt = stmt.order_by(DadosGeraisModelo.created_at.desc(), DadosGeraisModelo.id.desc())
    return db.execute(stmt).scalars().all()


def carregar_modelo(db: Session, modelo_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
    stmt = select(DadosGeraisModelo).where(DadosGeraisModelo.id == modelo_id)
    if user_id is not None:
        stmt = stmt.where(
            (DadosGeraisModelo.user_id == user_id)
            | (DadosGeraisModelo.user_id.is_(None))
            | (DadosGeraisModelo.nome_modelo.startswith(GLOBAL_PREFIX))
        )
    modelo = db.execute(stmt).scalar_one_or_none()
    if not modelo:
        raise ValueError("Modelo nao encontrado")
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
        raise ValueError("Modelo nao encontrado")
    db.delete(modelo)
    db.flush()


def renomear_modelo(db: Session, *, modelo_id: int, user_id: int, novo_nome: str) -> DadosGeraisModelo:
    nome_limpo = novo_nome.strip()
    if not nome_limpo:
        raise ValueError("Nome do modelo obrigatorio")
    stmt = select(DadosGeraisModelo).where(
        DadosGeraisModelo.id == modelo_id,
        DadosGeraisModelo.user_id == user_id,
    )
    modelo = db.execute(stmt).scalar_one_or_none()
    if not modelo:
        raise ValueError("Modelo nao encontrado")
    modelo.nome_modelo = nome_limpo
    db.flush()
    return modelo
