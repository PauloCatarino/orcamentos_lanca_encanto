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
#  Lista completa de colunas da tabela dados_def_pecas (ordem exata)
# ---------------------------------------------------------------------------

COLUNAS_DADOS_DEF_PECAS = [
    'id', 'descricao_livre', 'def_peca', 'descricao', 'qt_mod', 'qt_und', 'comp', 'larg', 'esp', 'mps', 'mo', 'orla', 'blk',
    'mat_default', 'tab_default', 'ids', 'num_orc', 'ver_orc', 'ref_le', 'descricao_no_orcamento', 'ptab', 'pliq', 'des1plus',
    'des1minus', 'und', 'desp', 'corres_orla_0_4', 'corres_orla_1_0', 'tipo', 'familia', 'comp_mp', 'larg_mp', 'esp_mp', 'mp',
    'comp_ass_1', 'comp_ass_2', 'comp_ass_3', 'orla_c1', 'orla_c2', 'orla_l1', 'orla_l2', 'ml_c1', 'ml_c2', 'ml_l1', 'ml_l2',
    'custo_ml_c1', 'custo_ml_c2', 'custo_ml_l1', 'custo_ml_l2', 'qt_total', 'comp_res', 'larg_res', 'esp_res', 'gravar_modulo',
    'area_m2_und', 'spp_ml_und', 'cp09_custo_mp', 'custo_mp_und', 'custo_mp_total', 'acb_sup', 'acb_inf', 'acb_sup_und',
    'acb_inf_und', 'cp01_sec', 'cp01_sec_und', 'cp02_orl', 'cp02_orl_und', 'cp03_cnc', 'cp03_cnc_und', 'cp04_abd',
    'cp04_abd_und', 'cp05_prensa', 'cp05_prensa_und', 'cp06_esquad', 'cp06_esquad_und', 'cp07_embalagem',
    'cp07_embalagem_und', 'cp08_mao_de_obra', 'cp08_mao_de_obra_und', 'soma_custo_und', 'soma_custo_total', 'soma_custo_acb'
]


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
     # Garantir número válido
    try:
        esp = float(esp_peca) if esp_peca is not None else 0.0
    except (TypeError, ValueError):
        esp = 0.0

    if esp <= 0:
        return 0.0, 0.0
    if esp < 20:
        return 23.0, 1000.0 / 23.0
    elif esp < 31:
        return 35.0, 1000.0 / 35.0
    elif esp < 40:
        return 45.0, 1000.0 / 45.0
    else:
        return 60.0, 1000.0 / 60.0


# ---------------------------------------------------------------------------
#  Cálculo principal — Exporta TODAS as colunas para o Resumo Geral
# ---------------------------------------------------------------------------

def resumo_geral_pecas(df_pecas: pd.DataFrame) -> pd.DataFrame:
    """
    Garante que todas as 82 colunas de dados_def_pecas vão para o resumo (na ordem certa).
    Se faltar alguma coluna, ela é criada com valor vazio.
    """
    df = df_pecas.copy()

    # Adiciona colunas em falta (caso existam campos novos)
    for col in COLUNAS_DADOS_DEF_PECAS:
        if col not in df.columns:
            df[col] = None  # ou pd.NA para manter compatibilidade

    # Garante a ordem
    df = df[COLUNAS_DADOS_DEF_PECAS]
    return df

# ---------------------------------------------------------------------------
#  Cálculos existentes (placas, orlas, etc.)
# ---------------------------------------------------------------------------

def calc_consumo_placas(df_items: pd.DataFrame, df_pecas: pd.DataFrame) -> pd.DataFrame:
    # ... (mantém a função igual, para não alterar tua lógica existente)
    pecas = df_pecas.rename(columns={'ids': 'peca_ids'})
    df = df_items.merge(
        pecas,
        how='left',
        left_on='codigo',
        right_on='def_peca'
    )
    df['cod_peca'] = df['codigo']
    df['consumo_bruto'] = df['area_m2_und'].fillna(0) * df['qt_und'].fillna(0)
    df['consumo_m2'] = df['consumo_bruto'] * (1 + df['desp'].fillna(0) / 100)
    df['qtd_placas'] = df.apply(
        lambda r: r['consumo_m2'] / r['area_m2_und'] if r['area_m2_und'] > 0 else 0,
        axis=1
    )
    df['custo_unit_placa'] = df['pliq'].fillna(0)
    df['custo_total'] = df['qtd_placas'] * df['custo_unit_placa']
    return df

def calc_consumo_orlas(df_items: pd.DataFrame, df_pecas: pd.DataFrame) -> pd.DataFrame:
    # ... (mantém a função igual, para não alterar tua lógica existente)
    pecas = df_pecas.rename(columns={'ids': 'peca_ids'})
    df = df_items.merge(
        pecas,
        how='left',
        left_on='codigo',
        right_on='def_peca'
    )
    df['cod_peca'] = df['codigo']
    df['ml_total'] = df[['ml_c1', 'ml_c2', 'ml_l1', 'ml_l2']].fillna(0).sum(axis=1)
    df['ml_ajust'] = df['ml_total'] * (1 + df['desp'].fillna(0) / 100)
    df['custo_ml'] = df[
        ['custo_ml_c1', 'custo_ml_c2', 'custo_ml_l1', 'custo_ml_l2']
    ].replace(0, pd.NA).mean(axis=1).fillna(0)
    df['custo_total'] = df['custo_ml'] * df['ml_ajust']
    larg_fat = df['esp'].apply(get_largura_fator)
    df[['larg_orla_mm', 'fator_conv']] = pd.DataFrame(
        larg_fat.tolist(), index=df.index
    )
    df['consumo_m2'] = df['ml_ajust'] * df['larg_orla_mm'] / 1000
    return df

# ... (mantém os placeholders para ferragens, máquinas, margens, etc.)

# Placeholders para ferragens, máquinas e margens


def calc_consumo_ferragens(df_items: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula o consumo de ferragens agrupando por item.
    Implementar conforme colunas de ferragens em df_items.
    """
    # TODO: agregar por 'cod_ferragem', 'qt_total', 'preco_und', etc.
    return pd.DataFrame()


def calc_custos_maquinas(df_items: pd.DataFrame) -> pd.DataFrame:
    """
    Agrupa os custos de operações de máquinas.
    Implementar conforme colunas de custo de máquina em df_items.
    """
    # TODO: agrupar por operação (ex: 'cp03_cnc', 'cp05_prensa')
    return pd.DataFrame()


def calc_margens(df_items: pd.DataFrame) -> pd.DataFrame:
    """
    Resume as margens aplicadas no orçamento.
    Usa colunas de percentuais e valores de margem em df_items.
    """
    # TODO: extrair colunas 'margem_perc', 'valor_margem'
    return pd.DataFrame()