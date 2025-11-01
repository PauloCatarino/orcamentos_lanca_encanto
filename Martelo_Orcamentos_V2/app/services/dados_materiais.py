from typing import Any, Dict, List, Optional, cast
from sqlalchemy.orm import Session
from ..utils.bool_converter import bool_to_int, int_to_bool
from ..models.dados_gerais import (
    DadosGeraisMaterial, DadosGeraisFerragem,
    DadosGeraisSistemaCorrer, DadosGeraisAcabamento,
    DadosItemsMaterial, DadosItemsFerragem,
    DadosItemsSistemaCorrer, DadosItemsAcabamento
)

def save_dados_materiais(db: Session, dados: List[Dict[str, Any]], context: Dict[str, Any]) -> None:
    # Deleta registros existentes
    db.query(DadosGeraisMaterial).filter_by(
        orcamento_id=context["orcamento_id"]
    ).delete()

    # Insere novos registros
    for row in dados:
        material = DadosGeraisMaterial(
            orcamento_id=context["orcamento_id"],
            ordem=row.get("ordem", 0),
            ref_le=row.get("ref_le"),
            descricao=row.get("descricao"),
            ptab=row.get("ptab"),
            pliq=row.get("pliq"),
            nao_stock=bool_to_int(row.get("nao_stock")),  # Converte para inteiro (0/1)
            # ... outros campos
        )
        db.add(material)
    
    db.commit()

def load_dados_materiais(db: Session, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = []
    for mat in db.query(DadosGeraisMaterial).filter_by(
        orcamento_id=context["orcamento_id"]
    ).order_by(DadosGeraisMaterial.ordem):
        rows.append({
            "ordem": mat.ordem,
            "ref_le": mat.ref_le,
            "descricao": mat.descricao,
            "ptab": mat.ptab,
            "pliq": mat.pliq,
            "nao_stock": int_to_bool(mat.nao_stock),  # Converte para bool para a interface
            # ... outros campos
        })
    return rows