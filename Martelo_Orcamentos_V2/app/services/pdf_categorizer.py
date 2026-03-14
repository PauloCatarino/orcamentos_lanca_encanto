from __future__ import annotations

import re
from typing import Dict, Optional, Tuple


CATEGORY_CUT_RITE = "CUT_RITE_PLANO CORTE"
CATEGORY_FERRAGENS = "FERRAGENS"
CATEGORY_PROJETO = "PROJETO"
CATEGORY_RESUMO_GERAL = "RESUMO_GERAL"
CATEGORY_MATERIAIS = "LISTA_PEÇAS_MATERIAIS"
CATEGORY_ETIQUETA = "ETIQUETA PALETE"
CATEGORY_RESUMO_ML = "RESUMO_ML_ORLAS"
CATEGORY_AUTOCAD = "AUTOCAD_IMOS IX"
CATEGORY_OUTROS = "OUTROS"


PATTERNS = [
    (CATEGORY_FERRAGENS, re.compile(r"^1_list_ferr", re.IGNORECASE), 1),
    (CATEGORY_PROJETO, re.compile(r"^2_proj", re.IGNORECASE), 2),
    (CATEGORY_RESUMO_GERAL, re.compile(r"^3_resumo_geral", re.IGNORECASE), 3),
    (CATEGORY_ETIQUETA, re.compile(r"^5_etiqueta", re.IGNORECASE), 5),
    (CATEGORY_RESUMO_ML, re.compile(r"^6_resumo_ml", re.IGNORECASE), 6),
]


DEFAULTS: Dict[str, Dict[str, object]] = {
    CATEGORY_CUT_RITE: {"priority": 0, "paper_size": "A3", "orientation": "horizontal", "quantity": 1},
    CATEGORY_FERRAGENS: {"priority": 1, "paper_size": "A4", "orientation": "vertical", "quantity": 3},
    CATEGORY_PROJETO: {"priority": 2, "paper_size": "A4", "orientation": "horizontal", "quantity": 2},
    CATEGORY_RESUMO_GERAL: {"priority": 3, "paper_size": "A4", "orientation": "vertical", "quantity": 1},
    CATEGORY_MATERIAIS: {"priority": 4, "paper_size": "A3", "orientation": "horizontal", "quantity": 1},
    CATEGORY_ETIQUETA: {"priority": 5, "paper_size": "A4", "orientation": "vertical", "quantity": 3},
    CATEGORY_RESUMO_ML: {"priority": 6, "paper_size": "A4", "orientation": "horizontal", "quantity": 1},
    CATEGORY_AUTOCAD: {"priority": 7, "paper_size": "A3", "orientation": "horizontal", "quantity": 1},
    CATEGORY_OUTROS: {"priority": 8, "paper_size": "A4", "orientation": "vertical", "quantity": 1},
}


def categorize_file(
    file_name: str,
    *,
    nome_plano_cut_rite: Optional[str] = None,
    nome_enc_imos_ix: Optional[str] = None,
    origin: str = "unknown",
) -> Tuple[str, int]:
    base_name = (file_name or "").strip()
    lower_name = base_name.casefold()

    if nome_plano_cut_rite:
        if lower_name == f"{str(nome_plano_cut_rite).strip().casefold()}.pdf":
            return CATEGORY_CUT_RITE, DEFAULTS[CATEGORY_CUT_RITE]["priority"]  # type: ignore[return-value]

    if nome_enc_imos_ix:
        prefix = f"lista_material_{str(nome_enc_imos_ix).strip().casefold()}"
        if lower_name.startswith(prefix):
            return CATEGORY_MATERIAIS, DEFAULTS[CATEGORY_MATERIAIS]["priority"]  # type: ignore[return-value]

    if lower_name.startswith("lista_material"):
        return CATEGORY_MATERIAIS, DEFAULTS[CATEGORY_MATERIAIS]["priority"]  # type: ignore[return-value]

    for category, regex, priority in PATTERNS:
        if regex.match(base_name):
            return category, priority

    if origin == "autocad":
        return CATEGORY_AUTOCAD, DEFAULTS[CATEGORY_AUTOCAD]["priority"]  # type: ignore[return-value]

    return CATEGORY_OUTROS, DEFAULTS[CATEGORY_OUTROS]["priority"]  # type: ignore[return-value]


def default_config(category: str) -> Dict[str, object]:
    return dict(DEFAULTS.get(category, DEFAULTS[CATEGORY_OUTROS]))
