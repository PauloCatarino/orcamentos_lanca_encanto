from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from sqlalchemy.orm import Session

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
        "label": "PRATELEIRA AMOVIVEL",
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
        "label": "PRATELEIRA FIXA",
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
        "children": [
            {"label": "FRENTE GAVETA [2222]"},
            {"label": "FRENTE GAVETA [2222] + PUXADOR"},
            {"label": "LATERAL GAVETA [2202]"},
            {"label": "TRASEIRA GAVETA [2000]"},
            {"label": "FUNDO GAVETA [0022]"},
            {"label": "FUNDO GAVETA [0000]"},
        ],
    },
    {
        "label": "PORTAS ABRIR",
        "children": [
            {"label": "PORTA ABRIR [2222]"},
            {"label": "PORTA ABRIR [2222] + DOBRADICA"},
            {"label": "PORTA ABRIR [2222] + DOBRADICA + PUXADOR"},
        ],
    },
    {
        "label": "PORTAS CORRER",
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
                    {"label": "PUXADOR PERFIL {SPP} 1"},
                    {"label": "PUXADOR PERFIL {SPP} 2"},
                    {"label": "PUXADOR PERFIL {SPP} 3"},
                    {"label": "CALHA LED {SPP} 1"},
                    {"label": "CALHA LED {SPP} 2"},
                    {"label": "FITA LED {SPP} 1"},
                    {"label": "FITA LED {SPP} 2"},
                    {"label": "FERRAGENS DIVERSAS {SPP} 1"},
                    {"label": "FERRAGENS DIVERSAS {SPP} 2"},
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
                    {"label": "CANTO COZINHA 1"},
                    {"label": "CANTO COZINHA 2"},
                    {"label": "PORTA TALHERES"},
                    {"label": "TULHA"},
                    {"label": "FUNDO ALUMINIO 1"},
                    {"label": "FUNDO ALUMINIO 2"},
                    {"label": "FUNDO PLASTICO FIGORIFICO"},
                    {"label": "SALVA SIFAO"},
                ],
            },
            {
                "label": "ROUPEIROS",
                "children": [
                    {"label": "PORTA CALCAS"},
                    {"label": "VARAO EXTENSIVEL"},
                    {"label": "GRELHA VELUDO"},
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


def carregar_contexto(
    session: Session,
    orcamento_id: int,
    *,
    item_id: Optional[int] = None,
) -> svc_dados_items.DadosItemsContext:
    """Delegates to dados_items context loader to ensure consistent metadata."""

    return svc_dados_items.carregar_contexto(session, orcamento_id, item_id=item_id)


def obter_arvore() -> Sequence[TreeNode]:
    return TREE_DEFINITION

