from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Mapping, Sequence

from sqlalchemy.orm import Session

from Martelo_Orcamentos_V2.app.services import modulos as svc_modulos
from Martelo_Orcamentos_V2.app.services.settings import get_setting, set_setting

KEY_MODULOS_REFERENCIA_SEED_VERSION = "modulos_referencia_seed_version"
MODULOS_REFERENCIA_SEED_VERSION = "2026-04-v1"


def _row(
    def_peca: str,
    *,
    descricao: str = "",
    qt_mod: float = 1,
    qt_und: float = 1,
    comp: str | None = None,
    larg: str | None = None,
    esp: float | None = 19,
    mat_default: str | None = None,
    tipo: str | None = None,
    familia: str | None = None,
    und: str | None = None,
) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "descricao_livre": "",
        "def_peca": def_peca,
        "descricao": descricao or def_peca,
        "qt_mod": qt_mod,
        "qt_und": qt_und,
        "gravar_modulo": False,
    }
    if comp is not None:
        row["comp"] = comp
    if larg is not None:
        row["larg"] = larg
    if esp is not None:
        row["esp"] = esp
    if mat_default is not None:
        row["mat_default"] = mat_default
    if tipo is not None:
        row["tipo"] = tipo
    if familia is not None:
        row["familia"] = familia
    if und is not None:
        row["und"] = und
    return row


REFERENCE_MODULES: Sequence[Mapping[str, Any]] = (
    {
        "nome": "REF | 1 Porta + 5 Prateleiras",
        "descricao": (
            "Modulo global de referencia para arranque rapido. "
            "Caso base com corpo simples, 1 porta de abrir e 5 prateleiras."
        ),
        "linhas": [
            _row("LATERAL", descricao="Lateral", qt_und=2, comp="HM", larg="PM", familia="PLACAS"),
            _row("TETO", descricao="Teto", comp="LM", larg="PM", familia="PLACAS"),
            _row("FUNDO", descricao="Fundo", comp="LM", larg="PM", familia="PLACAS"),
            _row("COSTA", descricao="Costa", comp="HM", larg="LM", familia="PLACAS"),
            _row(
                "PRATELEIRA AMOVIVEL [2111]",
                descricao="Prateleira Amovivel",
                qt_und=5,
                comp="LM",
                larg="PM",
                familia="PLACAS",
            ),
            _row(
                "PORTA ABRIR [2222] + DOBRADICA + PUXADOR",
                descricao="Porta Abrir",
                comp="HM",
                larg="LM",
                mat_default="Portas Abrir 1",
                familia="PLACAS",
            ),
            _row("DOBRADICA", descricao="Dobradica", qt_und=4, tipo="DOBRADICAS", familia="FERRAGENS"),
            _row("PUXADOR", descricao="Puxador", tipo="PUXADOR", familia="FERRAGENS"),
        ],
    },
    {
        "nome": "REF | 2 Portas + 5 Prateleiras",
        "descricao": (
            "Modulo global de referencia para arranque rapido. "
            "Caso base com corpo simples, 2 portas de abrir e 5 prateleiras."
        ),
        "linhas": [
            _row("LATERAL", descricao="Lateral", qt_und=2, comp="HM", larg="PM", familia="PLACAS"),
            _row("TETO", descricao="Teto", comp="LM", larg="PM", familia="PLACAS"),
            _row("FUNDO", descricao="Fundo", comp="LM", larg="PM", familia="PLACAS"),
            _row("COSTA", descricao="Costa", comp="HM", larg="LM", familia="PLACAS"),
            _row(
                "PRATELEIRA AMOVIVEL [2111]",
                descricao="Prateleira Amovivel",
                qt_und=5,
                comp="LM",
                larg="PM",
                familia="PLACAS",
            ),
            _row(
                "PORTA ABRIR [2222] + DOBRADICA + PUXADOR",
                descricao="Porta Esquerda",
                comp="HM",
                larg="LM/2",
                mat_default="Portas Abrir 1",
                familia="PLACAS",
            ),
            _row("DOBRADICA", descricao="Dobradica Esq.", qt_und=4, tipo="DOBRADICAS", familia="FERRAGENS"),
            _row("PUXADOR", descricao="Puxador Esq.", tipo="PUXADOR", familia="FERRAGENS"),
            _row(
                "PORTA ABRIR [2222] + DOBRADICA + PUXADOR",
                descricao="Porta Direita",
                comp="HM",
                larg="LM/2",
                mat_default="Portas Abrir 1",
                familia="PLACAS",
            ),
            _row("DOBRADICA", descricao="Dobradica Dir.", qt_und=4, tipo="DOBRADICAS", familia="FERRAGENS"),
            _row("PUXADOR", descricao="Puxador Dir.", tipo="PUXADOR", familia="FERRAGENS"),
        ],
    },
    {
        "nome": "REF | Sistema de Correr",
        "descricao": (
            "Modulo global de referencia para arranque rapido. "
            "Caso base com 2 paineis de correr e componentes principais do sistema."
        ),
        "linhas": [
            _row("LATERAL", descricao="Lateral", qt_und=2, comp="HM", larg="PM", familia="PLACAS"),
            _row("TETO", descricao="Teto", comp="LM", larg="PM", familia="PLACAS"),
            _row("FUNDO", descricao="Fundo", comp="LM", larg="PM", familia="PLACAS"),
            _row(
                "PAINEL CORRER [2222]",
                descricao="Painel Correr",
                qt_und=2,
                comp="HM",
                larg="LM/2",
                mat_default="Painel Porta Correr 1",
                tipo="Painel Porta Correr 1",
                familia="SISTEMAS CORRER",
            ),
            _row(
                "CALHA SUPERIOR {SPP} 2 CORRER",
                descricao="Calha Superior",
                comp="LM",
                tipo="Calha Superior 2 SPP",
                familia="SISTEMAS CORRER",
                und="ML",
            ),
            _row(
                "CALHA INFERIOR {SPP} 2 CORRER",
                descricao="Calha Inferior",
                comp="LM",
                tipo="Calha Inferior 2 SPP",
                familia="SISTEMAS CORRER",
                und="ML",
            ),
            _row(
                "ACESSORIO {SPP} 7 CORRER",
                descricao="Acessorio 7",
                tipo="Acessorio 7 SPP",
                familia="SISTEMAS CORRER",
            ),
            _row(
                "ACESSORIO {SPP} 8 CORRER",
                descricao="Acessorio 8",
                tipo="Acessorio 8 SPP",
                familia="SISTEMAS CORRER",
            ),
        ],
    },
)


def listar_modulos_referencia() -> List[Dict[str, Any]]:
    return deepcopy(list(REFERENCE_MODULES))


def ensure_reference_modules(db: Session) -> int:
    current_version = str(get_setting(db, KEY_MODULOS_REFERENCIA_SEED_VERSION, "") or "").strip()
    if current_version == MODULOS_REFERENCIA_SEED_VERSION:
        return 0

    existing = svc_modulos.listar_modulos_por_scope(db, None, "global")
    existing_names = {
        str(item.get("nome") or "").strip().casefold()
        for item in existing
        if str(item.get("nome") or "").strip()
    }

    created = 0
    for modulo_data in listar_modulos_referencia():
        nome = str(modulo_data.get("nome") or "").strip()
        if not nome:
            continue
        if nome.casefold() in existing_names:
            continue

        modulo = svc_modulos.guardar_modulo(
            db,
            user_id=None,
            nome=nome,
            descricao=modulo_data.get("descricao"),
            linhas=modulo_data.get("linhas") or (),
            imagem_path=None,
            is_global=True,
        )
        modulo.extras = {
            "seed": "reference",
            "seed_version": MODULOS_REFERENCIA_SEED_VERSION,
        }
        created += 1
        existing_names.add(nome.casefold())

    set_setting(db, KEY_MODULOS_REFERENCIA_SEED_VERSION, MODULOS_REFERENCIA_SEED_VERSION)
    return created
