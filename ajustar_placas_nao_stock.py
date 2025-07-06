# ajustar_placas_nao_stock.py
"""
Lógica para ajustar o desperdício (%) de placas não stock,
garantindo que os custos finais consideram sempre placas inteiras.
Chama-se APÓS gerar os resumos de consumo, ANTES de recalcular preços finais.
"""

import math
from db_connection import get_connection  # Importa o método do pool (ajusta nome se for diferente)
import pandas as pd
import traceback


def atualizar_desp_na_bd(id_peca, novo_desp):
    """
    Atualiza o valor de desperdício (%) na base de dados para a peça indicada.
    """
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            sql = "UPDATE dados_def_pecas SET desp = %s WHERE id = %s"
            cur.execute(sql, (novo_desp, id_peca))
            conn.commit()
        conn.close()
        print(f"[BD] Peça id {id_peca} atualizada: desp = {novo_desp:.4f}")
    except Exception as e:
        print(f"[ERRO BD] Falha ao atualizar desp na peça id={id_peca}: {e}")
        traceback.print_exc()

def ajustar_placas_nao_stock(dados_pecas: pd.DataFrame, resumo_placas: pd.DataFrame, debug=True):
    """
    Percorre as placas de nao_stock, calcula o novo %desp para cada peça e atualiza na BD.
    """
    print("\nInício do workflow Martelo: Ajuste Placas Não Stock")
    linhas_ajustadas = []
    for idx, row in resumo_placas.iterrows():
        if str(row.get('nao_stock', '')) == '✓':
            # Quantidade de placas inteiras e área total de placas
            n_placas = int(row['qt_placas_utilizadas'])
            area_placa = float(row['area_placa'])
            area_total_placas = n_placas * area_placa
            m2_consumidos = float(row['m2_consumidos'])
            desc = row['descricao_no_orcamento']
            # Cálculo do novo %desp (para que a soma dos m2 de peças = area das placas inteiras)
            if m2_consumidos > 0:
                novo_desp = (area_total_placas / m2_consumidos) - 1
            else:
                novo_desp = 0
            if debug:
                print(f"[{desc}] Não Stock: {n_placas} placas inteiras, Área placas: {area_total_placas:.3f} m2, Consumo peças: {m2_consumidos:.3f} m2, Novo %desp: {novo_desp*100:.2f}%")
            # Atualizar todas as linhas em dados_pecas que correspondam a este material
            desc_filtrada = str(desc).strip().lower()
            linhas_pecas = dados_pecas[
                dados_pecas['descricao_no_orcamento'].str.strip().str.lower() == desc_filtrada
            ]
            for i, linha in linhas_pecas.iterrows():
                id_peca = linha['id']
                atualizar_desp_na_bd(id_peca, novo_desp)
                linhas_ajustadas.append(id_peca)
    print(f"==> {len(linhas_ajustadas)} linhas ajustadas na base de dados para placas não stock.")
    return linhas_ajustadas  # Só retorna os IDs, não o DataFrame modificado

# Função para atualizar custos/preços dos items (exemplo, ajusta import conforme o teu projeto)
def atualizar_custos_precos_items(num_orc, versao):
    from orcamento_items import atualizar_custos_e_precos_itens_por_num_versao
    # Esta função é um exemplo, podes adaptar se o teu projeto usar outra assinatura
    atualizar_custos_e_precos_itens_por_num_versao(num_orc, versao)
    print("[INFO] Custos e preços dos items recalculados e atualizados.")

# Workflow total
def workflow_ajustar_placas_nao_stock(dados_pecas, resumo_placas, num_orc, versao, path_excel_dashboard):
    linhas_ajustadas = ajustar_placas_nao_stock(dados_pecas, resumo_placas)
    if not linhas_ajustadas:
        print("Nenhuma placa 'não stock' encontrada para ajuste.")
        return
    # Atualiza custos/preços dos items (chama função de recalculo para todos os items deste orçamento)
    atualizar_custos_precos_items(num_orc, versao)
    # Gerar novamente o dashboard dos resumos (para refletir o novo custo!)
    from resumo_consumos import gerar_resumos_excel
    gerar_resumos_excel(path_excel_dashboard, num_orc, versao)
    print("[Martelo] Workflow completo de placas não stock finalizado.")


"""
def ajustar_placas_nao_stock(df_pecas, df_resumo_placas, debug=False):
    
    Ajusta o campo 'desp' em df_pecas para materiais da família PLACAS com nao_stock=1,
    de modo a que o custo reflicta placas inteiras.
    df_pecas: DataFrame com todas as peças de orçamento (tab_def_pecas)
    df_resumo_placas: DataFrame do resumo de placas (gerado após consumos)
    Return: df_pecas atualizado
    
    # Campos obrigatórios
    COL_DESC = "descricao_no_orcamento"
    COL_FAMILIA = "familia"
    COL_NAO_STOCK = "nao_stock"
    COL_COMP = "comp_mp"
    COL_LARG = "larg_mp"
    COL_AREA_M2_UND = "area_m2_und"
    COL_QT_TOTAL = "qt_total"
    COL_DESP = "desp"
    # Opcional: marcar linhas alteradas para debug
    COL_AJUSTADO = "desp_ajustado"

    if debug:
        print("Início do ajuste para placas não stock.")

    # Garantir que colunas existem (ajustar nomes conforme o teu projeto)
    for col in [COL_DESC, COL_FAMILIA, COL_COMP, COL_LARG, COL_AREA_M2_UND, COL_QT_TOTAL]:
        if col not in df_pecas.columns:
            raise ValueError(f"Coluna obrigatória não encontrada: {col}")

    if COL_NAO_STOCK not in df_resumo_placas.columns:
        raise ValueError(f"Coluna 'nao_stock' não encontrada no resumo de placas!")

    # Limpar eventual marcação anterior
    if COL_AJUSTADO in df_pecas.columns:
        df_pecas[COL_AJUSTADO] = False
    else:
        df_pecas[COL_AJUSTADO] = False

    # Ciclo por cada placa do resumo com nao_stock=1
    for idx, placa in df_resumo_placas.iterrows():
        nao_stock = str(placa.get(COL_NAO_STOCK, "")).strip()
        desc = placa[COL_DESC]
        comp = float(placa[COL_COMP])
        larg = float(placa[COL_LARG])
        area_placa = (comp / 1000.0) * (larg / 1000.0)
        m2_consumidos = float(placa.get("m2_consumidos", 0))
        if nao_stock in ("1", "True", "Sim", "✓", "X") and area_placa > 0 and m2_consumidos > 0:
            # Só linhas da família PLACAS e descrição igual
            mask_pecas = (df_pecas[COL_DESC] == desc) & (df_pecas[COL_FAMILIA].str.upper() == "PLACAS")
            area_pecas = (df_pecas.loc[mask_pecas, COL_AREA_M2_UND] * df_pecas.loc[mask_pecas, COL_QT_TOTAL]).sum()
            if area_pecas == 0:
                continue
            n_placas = math.ceil(m2_consumidos / area_placa)
            total_area_placa = n_placas * area_placa
            novo_desp = (total_area_placa / area_pecas) - 1
            df_pecas.loc[mask_pecas, COL_DESP] = round(novo_desp, 4)
            df_pecas.loc[mask_pecas, COL_AJUSTADO] = True
            if debug:
                print(f"[{desc}] Não Stock: {n_placas} placas inteiras, Area placas: {total_area_placa:.3f} m2, Consumo peças: {area_pecas:.3f} m2, Novo %desp: {novo_desp:.4%}")

    return df_pecas

# Exemplo de chamada no teu fluxo principal:
# from ajustar_placas_nao_stock import ajustar_placas_nao_stock
# df_pecas = ajustar_placas_nao_stock(df_pecas, df_resumo_placas, debug=True)
"""
