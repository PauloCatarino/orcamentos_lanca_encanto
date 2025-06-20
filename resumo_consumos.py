# resumo_consumos.py
# Gera todos os resumos (Placas, Orlas, Ferragens, Maquinas/MO, Margens) para um orçamento selecionado.

"""
    MySQL
  |
  |__ db.py (carregar_tabela)
         |
         |__ pandas DataFrames: pecas, orcamentos, orcamento_items, etc
                   |
                   |__ resumo_consumos.py (gera todos os resumos)
                              |
                              |__ Excel com TODOS os dados + resumos

"""

import re
import sys
import os
import pandas as pd
import numpy as np

# Importa função para ler tabelas do MySQL
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from src.db import carregar_tabela


######################################################################
# 1. Constantes e utilitários
######################################################################

# Lista de todas as colunas da tabela dados_def_pecas (para garantir estrutura)
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

######################################################################
# 1A. Resumo Geral (filtra só o orçamento/versão)
######################################################################
def resumo_geral_pecas(df_pecas: pd.DataFrame, num_orc, versao) -> pd.DataFrame:
    """Garante que todas as 82 colunas estão presentes e ordenadas."""
    df = df_pecas.copy()
    # Filtrar só pelas peças do orçamento/versão correto!
    df = df[
        (df['num_orc'].astype(str) == str(num_orc)) &
        (df['ver_orc'].astype(str) == str(versao))
    ].copy()
    for col in COLUNAS_DADOS_DEF_PECAS:
        if col not in df.columns:
            df[col] = None
    df = df[COLUNAS_DADOS_DEF_PECAS]
    return df

######################################################################
# 2. Função para Resumo de Placas
######################################################################
def resumo_placas(pecas: pd.DataFrame, num_orc, versao) -> pd.DataFrame:
    """
    Cria o resumo de placas para o orçamento indicado, agrupando por descricao_no_orcamento.
    Calcula:
    - m2_consumidos = soma (area_m2_und * qt_total * (1 + desp/100))
    - qt_placas_utilizadas = ceil(m2_consumidos / area_placa)
    - custo_placas_utilizadas = qt_placas_utilizadas * area_placa * pliq
    Resumo das placas usadas no orçamento:
    - Agrupa por descricao_no_orcamento
    - Calcula área de placa, M2 consumidos, número de placas, custos totais
    """
    df = pecas[(pecas['num_orc'].astype(str) == str(num_orc)) & (pecas['ver_orc'].astype(str) == str(versao))].copy()
    df = df[df['und'] == 'M2']
    df['comp_mp'] = df['comp_mp'].astype(float)
    df['larg_mp'] = df['larg_mp'].astype(float)
    df['area_placa'] = (df['comp_mp'] / 1000) * (df['larg_mp'] / 1000)
    # ATENÇÃO: Desperdício (%)  o valor de desperdicio nao é dado em percentagem, mas sim em decimal (ex: 0.05 para 5%) ->desp = 0.05
    df['m2_consumidos'] = (df['area_m2_und'].astype(float) * df['qt_total'].astype(float) * (1 + df['desp'].astype(float)))
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
    grouped['qt_placas_utilizadas'] = np.ceil(grouped['m2_consumidos'] / grouped['area_placa'])
    grouped['custo_placas_utilizadas'] = grouped['qt_placas_utilizadas'] * grouped['area_placa'] * grouped['pliq']
    grouped = grouped[
        [
            'ref_le', 'descricao_no_orcamento', 'pliq', 'und', 'desp',
            'comp_mp', 'larg_mp', 'esp_mp', 'qt_placas_utilizadas',
            'area_placa', 'm2_consumidos', 'custo_mp_total', 'custo_placas_utilizadas'
        ]
    ]
    grouped['area_placa'] = grouped['area_placa'].round(3)
    grouped['m2_consumidos'] = grouped['m2_consumidos'].round(3)
    grouped['custo_mp_total'] = grouped['custo_mp_total'].round(2)
    grouped['custo_placas_utilizadas'] = grouped['custo_placas_utilizadas'].round(2)
    return grouped

######################################################################
# 3. Função para Resumo de Orlas 
######################################################################
def get_largura_fator(esp_peca):
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

def get_orla_codes(def_peca):
    """Extrai os 4 algarismos do padrão [xxxx] em qualquer parte do campo def_peca."""
    if def_peca is None:
        return [0, 0, 0, 0]
    m = re.search(r"\[(\d{4})\]", str(def_peca))
    if not m:
        return [0, 0, 0, 0]
    return [int(x) for x in m.group(1)]
   
def clean_ref(ref):
    """Remove espaços e converte nulos para string vazia."""
    if pd.isnull(ref):
        return ''
    return str(ref).strip()

def resumo_orlas(pecas: pd.DataFrame, num_orc, versao):
    """
    Cria o resumo de orlas, separando por referência, espessura e largura,
    analisando cada lado da peça, conforme o código [xxxx] em def_peca.
    Resumo das orlas usadas no orçamento:
    - Agrupa por referência de orla, espessura e largura
    - Soma ml e custo total para cada referência/espessura/largura
    """
    df = pecas[(pecas['num_orc'].astype(str) == str(num_orc)) & (pecas['ver_orc'].astype(str) == str(versao))].copy()
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
            if code == 0 or ml == 0:
                continue  # Sem orla neste lado
            if code == 1:
                espessura = '0.4mm'
                ref = clean_ref(row['corres_orla_0_4'])
            elif code == 2:
                espessura = '1.0mm'
                ref = clean_ref(row['corres_orla_1_0'])
            else:
                continue
            if not ref:
                continue
            resumo.append({
                'ref_orla': ref,
                'espessura_orla': espessura,
                'largura_orla': largura,
                'ml': ml,
                'custo': custo
            })
    df_resumo = pd.DataFrame(resumo)
    if df_resumo.empty:
        return pd.DataFrame(columns=['ref_orla', 'espessura_orla', 'largura_orla', 'ml_total', 'custo_total'])
    grupo = df_resumo.groupby(['ref_orla', 'espessura_orla', 'largura_orla'], as_index=False).agg(
        ml_total=('ml', 'sum'),
        custo_total=('custo', 'sum')
    )
    grupo['ml_total'] = grupo['ml_total'].round(2)
    grupo['custo_total'] = grupo['custo_total'].round(2)
    return grupo

######################################################################
# 4. Função para Resumo de Ferragens
######################################################################
def resumo_ferragens(pecas: pd.DataFrame, num_orc, versao):
    """
    Gera resumo de ferragens só para o orçamento/versão.
    - Agrupa por referência (ref_le) e descrição (descricao_no_orcamento)
    - Soma os totais das colunas já calculadas
    - Inclui apenas linhas em que ref_le começa por 'FER'
    - Para 'und' == 'ml', a coluna custo_mp_und fica 0.
    - spp_ml_total = spp_ml_und * qt_total
    """
    df = pecas[
        (pecas['num_orc'].astype(str) == str(num_orc)) &
        (pecas['ver_orc'].astype(str) == str(versao))
    ].copy()

    # Filtra apenas linhas de ferragens (ref_le começa com 'FER')
    df = df[df['ref_le'].astype(str).str.startswith("FER")]

    # Calcular spp_ml_total = spp_ml_und * qt_total
    df['spp_ml_und'] = df['spp_ml_und'].astype(float)
    df['qt_total'] = df['qt_total'].astype(float)
    df['spp_ml_total'] = df['spp_ml_und'] * df['qt_total']

    # Agrupa e agrega os campos
    grupo = df.groupby(['ref_le', 'descricao_no_orcamento', 'pliq', 'und', 'desp', 'comp_mp', 'larg_mp', 'esp_mp']).agg(
        qt_total=('qt_total', 'sum'),
        spp_ml_total=('spp_ml_total', 'sum'),
        custo_mp_und=('custo_mp_und', 'sum'),
        custo_mp_total=('custo_mp_total', 'sum')
    ).reset_index()

    # Corrigir custo_mp_und para ferragens em ml
    grupo['custo_mp_und'] = np.where(grupo['und'].str.lower() == 'ml', 0, grupo['custo_mp_und'])

    # Arredonda as somas
    grupo['qt_total'] = grupo['qt_total'].round(2)
    grupo['spp_ml_total'] = grupo['spp_ml_total'].round(2)
    grupo['custo_mp_und'] = grupo['custo_mp_und'].round(2)
    grupo['custo_mp_total'] = grupo['custo_mp_total'].round(2)

    return grupo[
        ['ref_le', 'descricao_no_orcamento', 'pliq', 'und', 'desp', 'comp_mp', 'larg_mp', 'esp_mp', 'qt_total', 'spp_ml_total', 'custo_mp_und', 'custo_mp_total']
    ]

######################################################################
# 5. Função para Resumo de Maquinas/Mão de Obra (MO)
######################################################################
def resumo_maquinas_mo(pecas: pd.DataFrame, num_orc, versao):
    """
    Resumo dos custos das máquinas e mão de obra não-maquinas.
    Soma os totais por operação:
    - Seccionadora, Orladora, CNC, ABD, Prensa, Esquadrejadora, Embalamento, Mão de Obra
    - Resumo dos custos das máquinas e mão de obra, enriquecido com info de ml e nº de peças para Corte, Orlagem, CNC, ABD.
    - Resumo dos custos das máquinas e mão de obra, incluindo apenas peças que passam por cada operação (cpXX >= 1).
    """
    df = pecas[
        (pecas['num_orc'].astype(str) == str(num_orc)) &
        (pecas['ver_orc'].astype(str) == str(versao))
    ].copy()

    # Seccionadora (Corte)
    df_corte = df[df['cp01_sec'].astype(float) >= 1].copy()
    pecas_cortadas = df_corte['qt_total'].astype(float).sum().round(0)
    custo_corte = (df_corte['qt_total'].astype(float) * df_corte['cp01_sec_und'].astype(float)).sum().round(2)
    ml_corte = ((df_corte['comp_res'].astype(float)*2 + df_corte['larg_res'].astype(float)*2) * df_corte['qt_total'].astype(float) / 1000).sum().round(2)

    # Orladora (Orlagem)
    df_orla = df[df['cp02_orl'].astype(float) >= 1].copy()
    # Calcula quantas vezes cada peça passa na orladora
    df_orla['orl_passagens'] = (
        (df_orla['orla_c1'].astype(float) > 0).astype(int) +
        (df_orla['orla_c2'].astype(float) > 0).astype(int) +
        (df_orla['orla_l1'].astype(float) > 0).astype(int) +
        (df_orla['orla_l2'].astype(float) > 0).astype(int)
    )
    pecas_orladas = (df_orla['orl_passagens'] * df_orla['qt_total'].astype(float)).sum().round(0)
    custo_orladora = (df_orla['cp02_orl_und'].astype(float) * df_orla['qt_total'].astype(float)).sum().round(2)
    ml_orla = (df_orla['ml_c1'].astype(float) + df_orla['ml_c2'].astype(float) + df_orla['ml_l1'].astype(float) + df_orla['ml_l2'].astype(float)).sum().round(2)

    # CNC (Mecanizações)
    df_cnc = df[df['cp03_cnc'].astype(float) >= 1].copy()
    pecas_cnc = df_cnc['qt_total'].astype(float).sum().round(0)
    custo_cnc = (df_cnc['cp03_cnc_und'].astype(float) * df_cnc['qt_total'].astype(float)).sum().round(2)

    # ABD (Mecanizações)
    df_abd = df[df['cp04_abd'].astype(float) >= 1].copy()
    pecas_abd = df_abd['qt_total'].astype(float).sum().round(0)
    custo_abd = (df_abd['cp04_abd_und'].astype(float) * df_abd['qt_total'].astype(float)).sum().round(2)

    # Esquadrejadora (Cortes Manuais)
    df_esquad = df[df['cp06_esquad'].astype(float) >= 1].copy()
    custo_esquad = (df_esquad['cp06_esquad_und'].astype(float) * df_esquad['qt_total'].astype(float)).sum().round(2)

    # Embalamento (Paletização)
    df_embal = df[df['cp07_embalagem'].astype(float) >= 1].copy()
    custo_embal = (df_embal['cp07_embalagem_und'].astype(float) * df_embal['qt_total'].astype(float)).sum().round(2)

    # Mão de Obra (MO geral)
    df_mo = df[df['cp08_mao_de_obra'].astype(float) >= 1].copy()
    custo_mo = (df_mo['cp08_mao_de_obra_und'].astype(float) * df_mo['qt_total'].astype(float)).sum().round(2)

    # Prensa (Montagem)
    df_prensa = df[df['cp05_prensa'].astype(float) >= 1].copy()
    # Soma o custo da prensa, mas não considera nº de peças (já está agregado)
    custo_prensa = (df_prensa['cp05_prensa_und'].astype(float) * df_prensa['qt_total'].astype(float)).sum().round(2)

    # Seccionadora (Corte) - Verifica se há peças cortadas
    # Montar DataFrame para exportar
    rows = [
        {
            "Operação": "Seccionadora (Corte)",
            "Custo Total (€)": custo_corte,
            "ML Corte": ml_corte,
            "Nº Peças": int(pecas_cortadas)
        },
        {
            "Operação": "Orladora (Orlagem)",
            "Custo Total (€)": custo_orladora,
            "ML Orlado": ml_orla,
            "Nº Peças": int(pecas_orladas)
        },
        {
            "Operação": "CNC (Mecanizações)",
            "Custo Total (€)": custo_cnc,
            "Nº Peças": int(pecas_cnc)
        },
        {
            "Operação": "ABD (Mecanizações)",
            "Custo Total (€)": custo_abd,
            "Nº Peças": int(pecas_abd)
        },
        {
            "Operação": "Prensa (Montagem)",
            "Custo Total (€)": custo_prensa
        },
        {
            "Operação": "Esquadrejadora (Cortes Manuais)",
            "Custo Total (€)": custo_esquad
        },
        {
            "Operação": "Embalamento (Paletização)",
            "Custo Total (€)": custo_embal
        },
        {
            "Operação": "Mão de Obra (MO geral)",
            "Custo Total (€)": custo_mo
        }
    ]

    # Ajustar DataFrame para campos diferentes por linha
    df_final = pd.DataFrame(rows)
    for col in ["Operação", "Custo Total (€)", "ML Corte", "ML Orlado", "Nº Peças"]:
        if col not in df_final.columns:
            df_final[col] = ""
    df_final = df_final[["Operação", "Custo Total (€)", "ML Corte", "ML Orlado", "Nº Peças"]]

    return df_final

######################################################################
# 6. Função para Resumo de Margens (lendo já do Excel)
######################################################################
def resumo_margens_excel(excel_path, num_orcamento, versao):
    """
    - Lê os separadores 'Orcamentos' e 'Orcamento_Items' do Excel e gera um resumo das margens, custos admin, ajustes.
    - Gera um resumo das margens, custos administrativos e ajustes de um orçamento,
        a partir dos separadores 'Orcamentos' e 'Orcamento_Items' de um ficheiro Excel.

    Parâmetros:
        excel_path (str): Caminho para o ficheiro Excel.
        num_orcamento (str/int): Número do orçamento a analisar (ex: "250001").
        versao (str/int): Versão do orçamento a analisar (ex: "01").

    Retorna:
        df_resumo (DataFrame): DataFrame formatado para exportação para o Excel.
    """

    # 1. Ler os separadores relevantes do Excel
    orcamentos = pd.read_excel(excel_path, sheet_name="Orcamentos", dtype=str)
    orcamento_items = pd.read_excel(excel_path, sheet_name="Orcamento_Items", dtype=str)

    # 2. Normalizar todas as versões para str, sem zeros à esquerda
    num_orcamento_formatado = str(num_orcamento)
    versao_formatada = str(versao).zfill(2)

    print("Depois eliminar -> num_orcamento_formatado:", num_orcamento_formatado)
    print("Depois eliminar -> versao_formatada:", versao_formatada)
    print(orcamentos[['id','num_orcamento','versao']])  # debug para conferir valores

    # Filtrar a linha correta no Excel
    id_orcamento = orcamentos.loc[
        (orcamentos['num_orcamento'].str.strip() == num_orcamento_formatado) &
        (orcamentos['versao'].str.strip().str.zfill(2) == versao_formatada), 'id'
    ]
    if id_orcamento.empty:
        print("Orçamento não encontrado!")
        return pd.DataFrame()
    id_orcamento = id_orcamento.iloc[0]

    # Filtrar itens associados
    itens = orcamento_items[orcamento_items['id_orcamento'].astype(str) == str(id_orcamento)].copy()

    # Funções auxiliares
    def safe_mean(col):
        try:
            return pd.to_numeric(itens[col], errors="coerce").mean()
        except Exception:
            return 0

    def safe_sum(col):
        try:
            return pd.to_numeric(itens[col], errors="coerce").sum()
        except Exception:
            return 0

    resumo = {
        "Margem (%)": round(safe_mean('margem_lucro_perc')*100, 2),
        "Valor Margem (€)": round(safe_sum('valor_margem'), 2),
        "Custos Admin (%)": round(safe_mean('custos_admin_perc')*100, 2),
        "Valor Custos Admin (€)": round(safe_sum('valor_custos_admin'), 2),
        "Ajustes 1 (%)": round(safe_mean('ajustes1_perc')*100, 2),
        "Valor Ajustes 1 (€)": round(safe_sum('valor_ajustes1'), 2),
        "Ajustes 2 (%)": round(safe_mean('ajustes2_perc')*100, 2),
        "Valor Ajustes 2 (€)": round(safe_sum('valor_ajustes2'), 2),
    }

    # Criar DataFrame para Excel
    df_resumo = pd.DataFrame([
        {"Tipo": "Margem", "Percentagem (%)": resumo["Margem (%)"], "Valor (€)": resumo["Valor Margem (€)"]},
        {"Tipo": "Custos Admin", "Percentagem (%)": resumo["Custos Admin (%)"], "Valor (€)": resumo["Valor Custos Admin (€)"]},
        {"Tipo": "Ajustes 1", "Percentagem (%)": resumo["Ajustes 1 (%)"], "Valor (€)": resumo["Valor Ajustes 1 (€)"]},
        {"Tipo": "Ajustes 2", "Percentagem (%)": resumo["Ajustes 2 (%)"], "Valor (€)": resumo["Valor Ajustes 2 (€)"]},
    ])
    return df_resumo



######################################################################
# 7. Main: Executa todos os resumos e exporta para Excel
######################################################################
# resumo_consumos.py (no início do ficheiro, após imports)
def gerar_resumos_excel(path_excel, num_orc, versao):
    """
    Atualiza/gera todos os resumos no Excel indicado, para o orçamento e versão dados.
    """
  

    print(f"===> GERAR RESUMOS EXCEL PARA: {path_excel}")
    print(f"===> NUM_ORC: {num_orc} | VERSAO: {versao}")

    # 1. Carregar dados da BD
    pecas = carregar_tabela("dados_def_pecas")
    orcamentos = carregar_tabela("orcamentos")
    orcamento_items = carregar_tabela("orcamento_items")

    print(f"--- Linhas dados_def_pecas: {len(pecas)}")
    print(f"--- Linhas orcamentos: {len(orcamentos)}")
    print(f"--- Linhas orcamento_items: {len(orcamento_items)}")

    # Filtra orcamentos/orcamento_items para só mostrar os do orçamento/versão atual
    num_orc_f = str(num_orc).strip()
    ver_f = str(versao).zfill(2)

    orcamentos_filtrados = orcamentos[(orcamentos['num_orcamento'].astype(str).str.strip() == num_orc_f) & (orcamentos['versao'].astype(str).str.zfill(2) == ver_f)].copy()
    if 'id' in orcamentos_filtrados.columns and not orcamentos_filtrados.empty:
        id_orcamento = int(orcamentos_filtrados.iloc[0]['id'])
        orcamento_items_filtrados = orcamento_items[orcamento_items['id_orcamento'].astype(int) == id_orcamento].copy()
    else:
        orcamento_items_filtrados = pd.DataFrame(columns=orcamento_items.columns)
    # 2. Gerar os DataFrames de resumo
    df_resumogeral = resumo_geral_pecas(pecas, num_orc, versao)
    df_resumo_placas = resumo_placas(pecas, num_orc, versao)
    df_resumo_orlas = resumo_orlas(pecas, num_orc, versao)
    df_resumo_ferragens = resumo_ferragens(pecas, num_orc, versao)
    df_resumo_maquinas_mo = resumo_maquinas_mo(pecas, num_orc, versao)

    # 3. Exportar para o Excel (escreve/atualiza cada separador)
    try:
        with pd.ExcelWriter(path_excel, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            df_resumogeral.to_excel(writer, sheet_name="Resumo Geral", index=False)
            print(f"Resumo geral: {len(df_resumogeral)} linhas")
            df_resumo_placas.to_excel(writer, sheet_name="Resumo Placas", index=False)
            print(f"Resumo placas: {len(df_resumo_placas)} linhas")
            df_resumo_orlas.to_excel(writer, sheet_name="Resumo Orlas", index=False)
            print(f"Resumo orlas: {len(df_resumo_orlas)} linhas")
            df_resumo_ferragens.to_excel(writer, sheet_name="Resumo Ferragens", index=False)
            print(f"Resumo ferragens: {len(df_resumo_ferragens)} linhas")
            df_resumo_maquinas_mo.to_excel(writer, sheet_name="Resumo Maquinas_MO", index=False)
            print(f"Resumo máquinas/MO: {len(df_resumo_maquinas_mo)} linhas")
            orcamentos_filtrados.to_excel(writer, sheet_name="Orcamentos", index=False)
            orcamento_items_filtrados.to_excel(writer, sheet_name="Orcamento_Items", index=False)
        print("Gravação concluída")
    except Exception as exc:
        print(f"ERRO ao gravar no Excel: {exc}")

    print(f"Gravando no Excel: {path_excel}")
    # 4. Separador Margens (lendo do Excel)
    df_resumo_margens = resumo_margens_excel(path_excel, num_orc, versao)
    with pd.ExcelWriter(path_excel, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        df_resumo_margens.to_excel(writer, sheet_name="Resumo Margens", index=False)

    print(f"Resumos gerados/atualizados em: {path_excel}")








"""
def main():
    # 1) Parâmetros do orçamento de referência a analisar
    num_orc, versao = "250001", "01"
    file_name = f"Resumo_{num_orc}_{versao}.xlsx"

    # 2) Carregar dados do MySQL completos das peças da base de dados (tabela dados_def_pecas + orcaementos + orcamento_items)
    pecas = carregar_tabela("dados_def_pecas")
    orcamentos = carregar_tabela("orcamentos")
    orcamento_items = carregar_tabela("orcamento_items")

    # 2) Gerar todos os resumos exceto margens
    df_resumogeral = resumo_geral_pecas(pecas)
    df_resumo_placas = resumo_placas(pecas, num_orc, versao)
    df_resumo_orlas = resumo_orlas(pecas, num_orc, versao)
    df_resumo_ferragens = resumo_ferragens(pecas, num_orc, versao)
    df_resumo_maquinas_mo = resumo_maquinas_mo(pecas, num_orc, versao)
    
    # 3) Exportar para Excel (todos os dados, inclusive orcamentos)
    with pd.ExcelWriter(file_name, engine="xlsxwriter") as writer:
        df_resumogeral.to_excel(writer, sheet_name="Resumo Geral", index=False)
        df_resumo_placas.to_excel(writer, sheet_name="Resumo Placas", index=False)
        df_resumo_orlas.to_excel(writer, sheet_name="Resumo Orlas", index=False)
        df_resumo_ferragens.to_excel(writer, sheet_name="Resumo Ferragens", index=False)
        df_resumo_maquinas_mo.to_excel(writer, sheet_name="Resumo Maquinas_MO", index=False)
        orcamentos.to_excel(writer, sheet_name="Orcamentos", index=False)
        orcamento_items.to_excel(writer, sheet_name="Orcamento_Items", index=False)

    # 4) Agora gera o resumo de margens LENDO do Excel já criado
    df_resumo_margens = resumo_margens_excel(file_name, num_orc, versao)

    # 5) Adiciona o separador de margens ao Excel usando openpyxl (sem apagar os outros separadores)
    with pd.ExcelWriter(file_name, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        df_resumo_margens.to_excel(writer, sheet_name="Resumo Margens", index=False)

    print(f"Excel gerado: {file_name}")

if __name__ == "__main__":
    main()

"""
