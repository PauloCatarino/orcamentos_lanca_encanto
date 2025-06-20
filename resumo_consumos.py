# resumo_consumos.py
# Gera todos os resumos (Placas, Orlas, Ferragens, Maquinas/MO, Margens) para um orçamento selecionado.
# =============================================================================
# Este módulo:
#   - Gera todos os resumos de custos (Placas, Orlas, Ferragens, Máquinas/MO, Margens)
#     para um orçamento específico.
#   - Lê dados das tabelas do MySQL (ou simula se não existir).
#   - Cria DataFrames formatados prontos para exportação para Excel.
#   - Pode ser usado como backend de relatórios e dashboards.
# =============================================================================

import re
import sys
import os
import pandas as pd
import numpy as np

# =============================================================================
# Bloco: Importação dinâmica da função de carregar tabelas do MySQL
# =============================================================================
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
    from src.db import carregar_tabela
except ImportError:
    print("AVISO: Módulo 'src.db' não encontrado. As funções podem falhar.")
    def carregar_tabela(nome_tabela):
        print(f"Simulando carga da tabela: {nome_tabela}")
        return pd.DataFrame()

# =============================================================================
# 1. Constantes e utilitários
# =============================================================================
# Lista com todos os campos esperados para garantir exportação e compatibilidade.
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

# =============================================================================
# 1A. Função: resumo_geral_pecas
# =============================================================================
# Descrição:
# Filtra todas as peças de um orçamento/versão e devolve todas as colunas essenciais.
# =============================================================================
def resumo_geral_pecas(df_pecas: pd.DataFrame, num_orc, versao) -> pd.DataFrame:
    if df_pecas.empty:
        return pd.DataFrame(columns=COLUNAS_DADOS_DEF_PECAS)
    df = df_pecas.copy()
    df = df[
        (df['num_orc'].astype(str) == str(num_orc)) &
        (df['ver_orc'].astype(str) == str(versao))
    ].copy()
    # Garante que todas as colunas estão presentes, mesmo que vazias
    for col in COLUNAS_DADOS_DEF_PECAS:
        if col not in df.columns:
            df[col] = None
    return df[COLUNAS_DADOS_DEF_PECAS]

# =============================================================================
# 2. Função: resumo_placas
# =============================================================================
# Descrição:
# Resume o consumo e custos das placas usadas, calculando área, quantidade,
# desperdício, custo total teórico e real.
# =============================================================================
def resumo_placas(pecas: pd.DataFrame, num_orc, versao) -> pd.DataFrame:
    cols_esperadas = [
        'ref_le', 'descricao_no_orcamento', 'pliq', 'und', 'desp', 'comp_mp', 'larg_mp', 'esp_mp',
        'qt_placas_utilizadas', 'area_placa', 'm2_consumidos', 'custo_mp_total', 'custo_placas_utilizadas'
    ]
    if pecas.empty:
        return pd.DataFrame(columns=cols_esperadas)
    df = pecas[
        (pecas['num_orc'].astype(str) == str(num_orc)) & (pecas['ver_orc'].astype(str) == str(versao))
    ].copy()
    df = df[df['und'] == 'M2']
    if df.empty:
        return pd.DataFrame(columns=cols_esperadas)
    # Garantir que todas as colunas numéricas estão no formato correto
    for col in ['comp_mp', 'larg_mp', 'area_m2_und', 'qt_total', 'desp', 'pliq', 'custo_mp_total']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    # Calcula área da placa e área consumida com desperdício
    df['area_placa'] = (df['comp_mp'] / 1000) * (df['larg_mp'] / 1000)
    df['m2_consumidos'] = (df['area_m2_und'] * df['qt_total'] * (1 + df['desp']))
    grouped = df.groupby('descricao_no_orcamento').agg(
        ref_le=('ref_le', 'first'),
        pliq=('pliq', 'first'),
        und=('und', 'first'),
        desp=('desp', 'first'),
        comp_mp=('comp_mp', 'first'),
        larg_mp=('larg_mp', 'first'),
        esp_mp=('esp_mp', 'first'),
        area_placa=('area_placa', 'first'),
        m2_consumidos=('m2_consumidos', 'sum'),
        custo_mp_total=('custo_mp_total', 'sum')
    ).reset_index()
    grouped['qt_placas_utilizadas'] = np.ceil(grouped['m2_consumidos'] / grouped['area_placa'].replace(0, np.nan))
    grouped['custo_placas_utilizadas'] = grouped['qt_placas_utilizadas'] * grouped['area_placa'] * grouped['pliq']
    # Arredonda valores para melhor leitura
    for col in ['area_placa', 'm2_consumidos']:
        grouped[col] = grouped[col].round(3)
    for col in ['custo_mp_total', 'custo_placas_utilizadas']:
        grouped[col] = grouped[col].round(2)
    return grouped[cols_esperadas]

# =============================================================================
# 3. Função: resumo_orlas
# =============================================================================
# Descrição:
# Cria resumo do consumo e custo de orlas, considerando cada lado
# das peças e os respetivos códigos, largura e espessura.
# =============================================================================
def get_largura_fator(esp_peca):
    # Calcula largura e fator de conversão com base na espessura da peça
    try:
        esp = float(esp_peca) if esp_peca is not None else 0.0
    except (TypeError, ValueError):
        esp = 0.0
    if esp <= 0: return 0.0, 0.0
    if esp < 20: return 23.0, 1000.0 / 23.0
    elif esp < 31: return 35.0, 1000.0 / 35.0
    elif esp < 40: return 45.0, 1000.0 / 45.0
    else: return 60.0, 1000.0 / 60.0

def get_orla_codes(def_peca):
    # Extrai os códigos dos lados de orla a partir do campo 'def_peca'
    if def_peca is None: return [0, 0, 0, 0]
    m = re.search(r"\[(\d{4})\]", str(def_peca))
    if not m: return [0, 0, 0, 0]
    return [int(x) for x in m.group(1)]

def clean_ref(ref):
    # Remove espaços e nulos nas referências
    if pd.isnull(ref): return ''
    return str(ref).strip()

def resumo_orlas(pecas: pd.DataFrame, num_orc, versao):
    df = pecas[(pecas['num_orc'].astype(str) == str(num_orc)) & (pecas['ver_orc'].astype(str) == str(versao))].copy()
    if df.empty:
        return pd.DataFrame(columns=['ref_orla', 'espessura_orla', 'largura_orla', 'ml_total', 'custo_total'])
    df['orla_codes'] = df['def_peca'].apply(get_orla_codes)
    df['largura_orla'], df['fator_conv'] = zip(*df['esp_mp'].apply(get_largura_fator))
    resumo = []
    for idx, row in df.iterrows():
        lados = ['c1', 'c2', 'l1', 'l2']
        ml_lados = [row['ml_c1'], row['ml_c2'], row['ml_l1'], row['ml_l2']]
        custo_lados = [row['custo_ml_c1'], row['custo_ml_c2'], row['custo_ml_l1'], row['custo_ml_l2']]
        orla_codes = row['orla_codes']
        largura = row['largura_orla']
        for i, lado in enumerate(lados):
            code = orla_codes[i]
            ml = float(ml_lados[i]) if not pd.isnull(ml_lados[i]) else 0.0
            custo = float(custo_lados[i]) if not pd.isnull(custo_lados[i]) else 0.0
            if code == 0 or ml == 0: continue
            if code == 1: espessura, ref = '0.4mm', clean_ref(row['corres_orla_0_4'])
            elif code == 2: espessura, ref = '1.0mm', clean_ref(row['corres_orla_1_0'])
            else: continue
            if not ref: continue
            resumo.append({'ref_orla': ref, 'espessura_orla': espessura, 'largura_orla': largura, 'ml': ml, 'custo': custo})
    df_resumo = pd.DataFrame(resumo)
    if df_resumo.empty:
        return pd.DataFrame(columns=['ref_orla', 'espessura_orla', 'largura_orla', 'ml_total', 'custo_total'])
    grupo = df_resumo.groupby(['ref_orla', 'espessura_orla', 'largura_orla'], as_index=False).agg(
        ml_total=('ml', 'sum'),
        custo_total=('custo', 'sum')
    )
    grupo['ml_total'], grupo['custo_total'] = grupo['ml_total'].round(2), grupo['custo_total'].round(2)
    return grupo

# =============================================================================
# 4. Função: resumo_ferragens
# =============================================================================
# Descrição:
# Cria resumo dos consumos e custos das ferragens (itens cujo código ref_le
# começa por 'FER'), agrupando quantidade, metros lineares e custos.
# =============================================================================
def resumo_ferragens(pecas: pd.DataFrame, num_orc, versao):
    cols_esperadas = [
        'ref_le', 'descricao_no_orcamento', 'pliq', 'und', 'desp', 'comp_mp', 'larg_mp', 'esp_mp',
        'qt_total', 'spp_ml_total', 'custo_mp_und', 'custo_mp_total'
    ]
    if pecas.empty:
        return pd.DataFrame(columns=cols_esperadas)
    df = pecas[
        (pecas['num_orc'].astype(str) == str(num_orc)) & (pecas['ver_orc'].astype(str) == str(versao))
    ].copy()
    df = df[df['ref_le'].astype(str).str.startswith("FER")]
    if df.empty:
        return pd.DataFrame(columns=cols_esperadas)
    for col in ['spp_ml_und', 'qt_total', 'custo_mp_und', 'custo_mp_total']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df['spp_ml_total'] = df['spp_ml_und'] * df['qt_total']
    grupo = df.groupby([
        'ref_le', 'descricao_no_orcamento', 'pliq', 'und', 'desp', 'comp_mp', 'larg_mp', 'esp_mp'
    ]).agg(
        qt_total=('qt_total', 'sum'),
        spp_ml_total=('spp_ml_total', 'sum'),
        custo_mp_und=('custo_mp_und', 'sum'),
        custo_mp_total=('custo_mp_total', 'sum')
    ).reset_index()
    # Se unidade é 'ml', custo unitário deve ser zero
    grupo['custo_mp_und'] = np.where(grupo['und'].str.lower() == 'ml', 0, grupo['custo_mp_und'])
    for col in ['qt_total', 'spp_ml_total', 'custo_mp_und', 'custo_mp_total']:
        grupo[col] = grupo[col].round(2)
    return grupo[cols_esperadas]

# =============================================================================
# 5. Função: resumo_maquinas_mo
# =============================================================================
# Descrição:
# Gera resumo de custos de operações de máquinas e mão de obra.
# Agrupa por operação: seccionadora, orladora, CNC, ABD, prensa, etc.
# Calcula metros, nº peças, custo total de cada operação.
# =============================================================================
def resumo_maquinas_mo(pecas: pd.DataFrame, num_orc, versao):
    cols_esperadas = ["Operação", "Custo Total (€)", "ML Corte", "ML Orlado", "Nº Peças"]
    if pecas.empty:
        return pd.DataFrame(columns=cols_esperadas)
    df = pecas[
        (pecas['num_orc'].astype(str) == str(num_orc)) & (pecas['ver_orc'].astype(str) == str(versao))
    ].copy()
    if df.empty:
        return pd.DataFrame(columns=cols_esperadas)
    numeric_cols = [
        'cp01_sec', 'cp01_sec_und', 'cp02_orl', 'cp02_orl_und', 'cp03_cnc', 'cp03_cnc_und', 'cp04_abd', 'cp04_abd_und',
        'cp05_prensa', 'cp05_prensa_und', 'cp06_esquad', 'cp06_esquad_und', 'cp07_embalagem', 'cp07_embalagem_und',
        'cp08_mao_de_obra', 'cp08_mao_de_obra_und', 'qt_total', 'comp_res', 'larg_res', 'orla_c1', 'orla_c2',
        'orla_l1', 'orla_l2', 'ml_c1', 'ml_c2', 'ml_l1', 'ml_l2'
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    def get_cost(df_filtered, cost_col, qty_col='qt_total'):
        return (df_filtered[cost_col] * df_filtered[qty_col]).sum().round(2)
    custo_corte = get_cost(df.loc[df['cp01_sec'] >= 1], 'cp01_sec_und')
    custo_orladora = get_cost(df.loc[df['cp02_orl'] >= 1], 'cp02_orl_und')
    custo_cnc = get_cost(df.loc[df['cp03_cnc'] >= 1], 'cp03_cnc_und')
    custo_abd = get_cost(df.loc[df['cp04_abd'] >= 1], 'cp04_abd_und')
    custo_prensa = get_cost(df.loc[df['cp05_prensa'] >= 1], 'cp05_prensa_und')
    custo_esquad = get_cost(df.loc[df['cp06_esquad'] >= 1], 'cp06_esquad_und')
    custo_embal = get_cost(df.loc[df['cp07_embalagem'] >= 1], 'cp07_embalagem_und')
    custo_mo = get_cost(df.loc[df['cp08_mao_de_obra'] >= 1], 'cp08_mao_de_obra_und')
    # Cálculo dos metros lineares e nº peças (Corte e Orlagem)
    df_corte = df.loc[df['cp01_sec'] >= 1]
    ml_corte = ((df_corte['comp_res'] * 2 + df_corte['larg_res'] * 2) * df_corte['qt_total'] / 1000).sum().round(2)
    pecas_cortadas = df_corte['qt_total'].sum()
    df_orla = df.loc[df['cp02_orl'] >= 1].copy()
    df_orla['passagens'] = (
        (df_orla['orla_c1'] > 0).astype(int) +
        (df_orla['orla_c2'] > 0).astype(int) +
        (df_orla['orla_l1'] > 0).astype(int) +
        (df_orla['orla_l2'] > 0).astype(int)
    )
    ml_orla = (df_orla['ml_c1'] + df_orla['ml_c2'] + df_orla['ml_l1'] + df_orla['ml_l2']).sum().round(2)
    pecas_orladas = (df_orla['passagens'] * df_orla['qt_total']).sum()
    pecas_cnc = df.loc[df['cp03_cnc'] >= 1, 'qt_total'].sum()
    pecas_abd = df.loc[df['cp04_abd'] >= 1, 'qt_total'].sum()
    rows = [
        {"Operação": "Seccionadora (Corte)", "Custo Total (€)": custo_corte, "ML Corte": ml_corte, "Nº Peças": int(pecas_cortadas)},
        {"Operação": "Orladora (Orlagem)", "Custo Total (€)": custo_orladora, "ML Orlado": ml_orla, "Nº Peças": int(pecas_orladas)},
        {"Operação": "CNC (Mecanizações)", "Custo Total (€)": custo_cnc, "Nº Peças": int(pecas_cnc)},
        {"Operação": "ABD (Mecanizações)", "Custo Total (€)": custo_abd, "Nº Peças": int(pecas_abd)},
        {"Operação": "Prensa (Montagem)", "Custo Total (€)": custo_prensa},
        {"Operação": "Esquadrejadora (Cortes Manuais)", "Custo Total (€)": custo_esquad},
        {"Operação": "Embalamento (Paletização)", "Custo Total (€)": custo_embal},
        {"Operação": "Mão de Obra (MO geral)", "Custo Total (€)": custo_mo}
    ]
    return pd.DataFrame(rows, columns=cols_esperadas).fillna('')

# =============================================================================
# 6. Função: resumo_margens_excel
# =============================================================================
# Descrição:
# Lê diretamente do ficheiro Excel os dados das margens e custos admin,
# devolve DataFrame com percentagens e valores.
# =============================================================================
def resumo_margens_excel(excel_path, num_orcamento, versao):
    cols_esperadas = ["Tipo", "Percentagem (%)", "Valor (€)"]
    try:
        orcamentos = pd.read_excel(excel_path, sheet_name="Orcamentos", dtype=str)
        orcamento_items = pd.read_excel(excel_path, sheet_name="Orcamento_Items", dtype=str)
    except (FileNotFoundError, ValueError) as e:
        print(f"AVISO: Não foi possível ler 'Orcamentos' ou 'Orcamento_Items' de {excel_path}: {e}")
        return pd.DataFrame(columns=cols_esperadas)

    num_orcamento_formatado = str(num_orcamento).strip()
    versao_formatada = str(versao).strip().zfill(2)
    id_orc_series = orcamentos.loc[
        (orcamentos['num_orcamento'].astype(str).str.strip() == num_orcamento_formatado) &
        (orcamentos['versao'].astype(str).str.strip().apply(lambda x: x.zfill(2)) == versao_formatada), 'id'
    ]
    if id_orc_series.empty:
        return pd.DataFrame(columns=cols_esperadas)
    id_orcamento = id_orc_series.iloc[0]
    itens = orcamento_items[orcamento_items['id_orcamento'].astype(str) == str(id_orcamento)].copy()
    if itens.empty:
        return pd.DataFrame(columns=cols_esperadas)
    def safe_mean(col): return pd.to_numeric(itens[col], errors="coerce").mean()
    def safe_sum(col): return pd.to_numeric(itens[col], errors="coerce").sum()
    resumo_dict = {
        "Margem": (safe_mean('margem_lucro_perc') * 100, safe_sum('valor_margem')),
        "Custos Admin": (safe_mean('custos_admin_perc') * 100, safe_sum('valor_custos_admin')),
        "Ajustes 1": (safe_mean('ajustes1_perc') * 100, safe_sum('valor_ajustes1')),
        "Ajustes 2": (safe_mean('ajustes2_perc') * 100, safe_sum('valor_ajustes2'))
    }
    data = [
        {"Tipo": k, "Percentagem (%)": f"{v[0]:.2f}%" if pd.notna(v[0]) else "0.00%", "Valor (€)": v[1] if pd.notna(v[1]) else 0}
        for k, v in resumo_dict.items()
    ]
    return pd.DataFrame(data, columns=cols_esperadas)

# =============================================================================
# 7. Função principal: gerar_resumos_excel
# =============================================================================
# Descrição:
# Executa todos os resumos, lê dados do MySQL (ou simulado), grava
# cada resumo numa folha do ficheiro Excel indicado. Pode ser usado em batch.
# =============================================================================
def gerar_resumos_excel(path_excel, num_orc, versao):
    print(f"===> A GERAR RESUMOS EXCEL PARA: {path_excel}")
    print(f"===> ORÇAMENTO: {num_orc} | VERSÃO: {versao}")
    if not os.path.exists(path_excel):
        pd.DataFrame().to_excel(path_excel, index=False)
        print(f"--- Ficheiro Excel criado em: {path_excel}")

    # Carrega tabelas (de bd MySQL ou simulação)
    pecas = carregar_tabela("dados_def_pecas")
    orcamentos = carregar_tabela("orcamentos")
    orcamento_items = carregar_tabela("orcamento_items")
    print(f"--- Linhas carregadas | Peças: {len(pecas)}, Orçamentos: {len(orcamentos)}, Itens: {len(orcamento_items)}")

    num_orc_f = str(num_orc).strip()
    ver_f = str(versao).strip().zfill(2)

    orcamentos_filtrados = orcamentos[
        (orcamentos['num_orcamento'].astype(str).str.strip() == num_orc_f) &
        (orcamentos['versao'].astype(str).str.strip().apply(lambda x: x.zfill(2)) == ver_f)
    ].copy()
    id_orcamento = None
    if not orcamentos_filtrados.empty and 'id' in orcamentos_filtrados.columns:
        id_orcamento = int(orcamentos_filtrados.iloc[0]['id'])
        orcamento_items_filtrados = orcamento_items[orcamento_items['id_orcamento'].astype(int) == id_orcamento].copy()
    else:
        orcamento_items_filtrados = pd.DataFrame(columns=orcamento_items.columns)

    # Executa cada resumo
    df_resumogeral = resumo_geral_pecas(pecas, num_orc, versao)
    df_resumo_placas = resumo_placas(pecas, num_orc, versao)
    df_resumo_orlas = resumo_orlas(pecas, num_orc, versao)
    df_resumo_ferragens = resumo_ferragens(pecas, num_orc, versao)
    df_resumo_maquinas_mo = resumo_maquinas_mo(pecas, num_orc, versao)

    # Gravação principal dos resumos no Excel
    try:
        with pd.ExcelWriter(path_excel, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            df_resumogeral.to_excel(writer, sheet_name="Resumo Geral", index=False)
            df_resumo_placas.to_excel(writer, sheet_name="Resumo Placas", index=False)
            df_resumo_orlas.to_excel(writer, sheet_name="Resumo Orlas", index=False)
            df_resumo_ferragens.to_excel(writer, sheet_name="Resumo Ferragens", index=False)
            df_resumo_maquinas_mo.to_excel(writer, sheet_name="Resumo Maquinas_MO", index=False)
            orcamentos_filtrados.to_excel(writer, sheet_name="Orcamentos", index=False)
            orcamento_items_filtrados.to_excel(writer, sheet_name="Orcamento_Items", index=False)
        print("--- Gravação dos resumos principais concluída.")
    except Exception as exc:
        print(f"ERRO CRÍTICO ao gravar resumos principais no Excel: {exc}")
        return
    
    # Gravação do resumo de margens (folha separada)
    df_resumo_margens = resumo_margens_excel(path_excel, num_orc, versao)
    try:
        with pd.ExcelWriter(path_excel, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            df_resumo_margens.to_excel(writer, sheet_name="Resumo Margens", index=False)
        print("--- Gravação do resumo de margens concluída.")
    except Exception as exc:
        print(f"ERRO CRÍTICO ao gravar resumo de margens no Excel: {exc}")

    print(f"===> RESUMOS GERADOS/ATUALIZADOS COM SUCESSO EM: {path_excel}")