# -*- coding: utf-8 -*-
# calculadora_consumos.py

"""Funções de cálculo para o Resumo de Consumos de um orçamento.

Este módulo contém rotinas que agregam e calculam os consumos de
materiais e custos de produção a partir das tabelas ``orcamento_items``
e ``tab_def_pecas``.
"""
from __future__ import annotations

import pandas as pd


# ---------------------------------------------------------------------------
#  Utilidades
# ---------------------------------------------------------------------------

def get_largura_fator(esp_peca: float) -> tuple[float, float]:
    """Determina largura da orla e fator de conversão em €/ml.

    Parameters
    ----------
    esp_peca : float
        Espessura da peça em milímetros.

    Returns
    -------
    tuple[float, float]
        ``(largura_mm, fator)`` onde ``fator`` é usado para converter o preço
        de €/m² para €/ml.
    """
    if esp_peca <= 0:
        return 0.0, 0.0
    if esp_peca < 20:
        return 23.0, 1000 / 23
    elif esp_peca < 31:
        return 35.0, 1000 / 35
    elif esp_peca < 40:
        return 45.0, 1000 / 45
    return 60.0, 1000 / 60


# ---------------------------------------------------------------------------
#  Cálculos principais
# ---------------------------------------------------------------------------

def calc_consumo_orlas(df_items: pd.DataFrame, df_pecas: pd.DataFrame) -> pd.DataFrame:
    """Calcula o consumo total de orlas para as peças do orçamento.

    É esperado que ``df_items`` contenha a coluna ``cod_peca`` e
    ``df_pecas`` tenha ``cod_peca`` e ``espessura``. Este é apenas um
    esqueleto simplificado; ajuste conforme os campos reais.
    """
    df = df_items.merge(df_pecas[["cod_peca", "espessura"]], on="cod_peca")
    resultados = []

    for _, row in df.iterrows():
        larg, fator = get_largura_fator(row["espessura"])
        perimetro = row.get("perimetro", 0.0)
        desperdicio = row.get("desperdicio", 0.0)
        preco_m2 = row.get("preco_m2", 0.0)

        ml = perimetro
        ml_ajust = ml * (1 + desperdicio / 100)
        custo_ml = preco_m2 / fator if fator else 0.0

        resultados.append({
            "cod_peca": row["cod_peca"],
            "larg_orla_mm": larg,
            "consumo_ml": ml_ajust,
            "consumo_m2": ml_ajust * larg / 1000,
            "custo_total": custo_ml * ml_ajust,
        })

    return pd.DataFrame(resultados)


# Placeholder para outras funções (placas, ferragens, etc.)

def calc_consumo_placas(df_items: pd.DataFrame, df_pecas: pd.DataFrame) -> pd.DataFrame:
    """Calcula o consumo de placas de madeira. (A implementar)."""
    return pd.DataFrame()


def calc_consumo_ferragens(df_items: pd.DataFrame) -> pd.DataFrame:
    """Calcula o consumo de ferragens. (A implementar)."""
    return pd.DataFrame()


def calc_custos_maquinas(df_items: pd.DataFrame) -> pd.DataFrame:
    """Agrupa os custos de operações de máquinas. (A implementar)."""
    return pd.DataFrame()


def calc_margens(df_items: pd.DataFrame) -> pd.DataFrame:
    """Resumo das margens aplicadas no orçamento. (A implementar)."""
    return pd.DataFrame()