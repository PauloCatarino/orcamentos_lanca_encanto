from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ProcessoDeleteUiPlan:
    folder_confirmation_text: Optional[str]
    db_confirmation_text: str


def normalize_tipo_pasta_text(value: str) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def build_lista_material_imos_values(
    *,
    responsavel: str,
    ref_cliente: str,
    obra: str,
    nome_enc_imos_ix: str,
    num_cliente_phc: str,
    nome_cliente: str,
    nome_cliente_simplex: str,
    localizacao: str,
    descricao_producao: str,
    descricao_artigos: str,
    materias: str,
    qtd: str,
    plano_corte: str,
    data_conclusao: str,
    data_inicio: str,
    enc_phc: str,
) -> dict[str, str]:
    return {
        "RESPONSAVEL": str(responsavel or "").strip(),
        "REF_CLIENTE": str(ref_cliente or "").strip(),
        "OBRA": str(obra or "").strip(),
        "NOME_ENC_IMOS_IX": str(nome_enc_imos_ix or "").strip(),
        "NUM_CLIENTE_PHC": str(num_cliente_phc or "").strip(),
        "NOME_CLIENTE": str(nome_cliente or "").strip(),
        "NOME_CLIENTE_SIMPLEX": str(nome_cliente_simplex or "").strip(),
        "LOCALIZACAO": str(localizacao or "").strip(),
        "DESCRICAO_PRODUCAO": str(descricao_producao or "").strip(),
        "DESCRICAO_ARTIGOS": str(descricao_artigos or "").strip(),
        "MATERIAIS": str(materias or "").strip(),
        "QTD": str(qtd or "").strip(),
        "PLANO_CORTE": str(plano_corte or "").strip(),
        "DATA_CONCLUSAO": str(data_conclusao or "").strip(),
        "DATA_INICIO": str(data_inicio or "").strip(),
        "ENC_PHC": str(enc_phc or "").strip(),
    }


def build_processo_delete_ui_plan(
    *,
    info_text: str,
    folder: Optional[Path],
    delete_folder: bool,
    folder_preview_text: str,
) -> ProcessoDeleteUiPlan:
    folder_confirmation_text = None
    if delete_folder and folder:
        folder_confirmation_text = (
            f"Apagar pasta e registo de {info_text}?\n"
            f"Pasta: {folder}\n"
            f"Conteudo:\n{folder_preview_text}"
        )

    db_confirmation_text = (
        "Esta acao elimina DEFINITIVAMENTE o processo da base de dados e nao pode ser recuperada.\n\n"
    )
    if delete_folder and folder:
        db_confirmation_text += f"A pasta tambem sera apagada:\n{folder}\n\n"
    db_confirmation_text += "Pretende continuar?"

    return ProcessoDeleteUiPlan(
        folder_confirmation_text=folder_confirmation_text,
        db_confirmation_text=db_confirmation_text,
    )
