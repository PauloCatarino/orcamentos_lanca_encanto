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
            mask = dados_pecas['descricao_no_orcamento'].str.strip().str.lower() == desc_filtrada
            dados_pecas.loc[mask, 'desp'] = round(novo_desp, 4)
            linhas_ids = dados_pecas.loc[mask, 'id']
            for id_peca in linhas_ids:
                atualizar_desp_na_bd(id_peca, novo_desp)
                linhas_ajustadas.append(id_peca)
    print(f"==> {len(linhas_ajustadas)} linhas ajustadas na base de dados para placas não stock.")
    return linhas_ajustadas  # Só retorna os IDs, não o DataFrame modificado

# Função para atualizar custos/preços dos items (exemplo, ajusta import conforme o teu projeto)
def atualizar_custos_precos_items(num_orc, versao):
    """Recalcula custos e preços de todos os itens do orçamento diretamente na BD."""
    try:
        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        cur.execute(
            "SELECT id FROM orcamentos WHERE num_orcamento=%s AND versao=%s",
            (str(num_orc), str(versao).zfill(2)),
        )
        row = cur.fetchone()
        if not row:
            print(f"[ERRO] Orçamento {num_orc} versão {versao} não encontrado.")
            conn.close()
            return
        id_orc = row["id"]

        cur.execute(
            "SELECT * FROM orcamento_items WHERE id_orcamento=%s",
            (id_orc,),
        )
        items = cur.fetchall()
        for item in items:
            item_num = item["item"].strip()

            # Carrega todas as peças deste item para calcular custos
            cur.execute(
                """
                SELECT mps, und, area_m2_und, spp_ml_und, pliq, desp,
                       cp09_custo_mp, qt_total,
                       custo_ml_c1, custo_ml_c2, custo_ml_l1, custo_ml_l2,
                       Soma_Custo_und, Soma_Custo_ACB
                FROM dados_def_pecas
                WHERE ids=%s AND num_orc=%s AND ver_orc=%s
                """,
                (item_num, str(num_orc), str(versao)),
            )
            pecas = cur.fetchall()

            orlas = mao = mp = acab = 0.0
            for p in pecas:
                (mps_flag, und, area_m2, spp_ml, pliq, desp_p, cp09, qt_total,
                 cml1, cml2, cml3, cml4, soma_und, soma_acb) = p

                orlas += float(cml1 or 0) + float(cml2 or 0) + float(cml3 or 0) + float(cml4 or 0)
                mao += float(soma_und or 0)
                acab += float(soma_acb or 0)

                if cp09 and not mps_flag:
                    desp_frac = float(desp_p or 0)
                    pliq_v = float(pliq or 0)
                    if str(und).upper() == "M2":
                        mp_und = float(area_m2 or 0) * (1 + desp_frac) * pliq_v
                    elif str(und).upper() == "ML":
                        mp_und = float(spp_ml or 0) * (1 + desp_frac) * pliq_v
                    elif str(und).upper() == "UND":
                        mp_und = pliq_v * (1 + desp_frac)
                    else:
                        mp_und = 0.0
                    mp += mp_und * float(qt_total or 0)

            custo_produzido = orlas + mao + mp + acab

            margem_perc = float(item.get("margem_lucro_perc") or 0)
            custos_admin_perc = float(item.get("custos_admin_perc") or 0)
            ajustes1_perc = float(item.get("ajustes1_perc") or 0)
            ajustes2_perc = float(item.get("ajustes2_perc") or 0)

            valor_margem = custo_produzido * margem_perc
            valor_custos_admin = custo_produzido * custos_admin_perc
            valor_ajustes1 = custo_produzido * ajustes1_perc
            valor_ajustes2 = custo_produzido * ajustes2_perc

            preco_unit = (
                custo_produzido
                + valor_margem
                + valor_custos_admin
                + valor_ajustes1
                + valor_ajustes2
            )
            qt = float(item.get("qt") or 1)
            preco_total = preco_unit * qt

            cur.execute(
                """
                UPDATE orcamento_items SET
                    preco_unitario=%s,
                    preco_total=%s,
                    custo_produzido=%s,
                    custo_total_orlas=%s,
                    custo_total_mao_obra=%s,
                    custo_total_materia_prima=%s,
                    custo_total_acabamentos=%s,
                    margem_lucro_perc=%s,
                    valor_margem=%s,
                    custos_admin_perc=%s,
                    valor_custos_admin=%s,
                    ajustes1_perc=%s,
                    valor_ajustes1=%s,
                    ajustes2_perc=%s,
                    valor_ajustes2=%s
                WHERE id_item=%s
                """,
                (
                    preco_unit,
                    preco_total,
                    custo_produzido,
                    orlas,
                    mao,
                    mp,
                    acab,
                    margem_perc,
                    valor_margem,
                    custos_admin_perc,
                    valor_custos_admin,
                    ajustes1_perc,
                    valor_ajustes1,
                    ajustes2_perc,
                    valor_ajustes2,
                    item["id_item"],
                ),
            )

        conn.commit()
        conn.close()
        print("[INFO] Custos e preços dos items recalculados e atualizados.")
    except Exception as e:
        print(f"[ERRO] Falha ao recalcular custos dos items: {e}")
        traceback.print_exc()

# Workflow total
def workflow_ajustar_placas_nao_stock(dados_pecas, resumo_placas, num_orc, versao):
    linhas_ajustadas = ajustar_placas_nao_stock(dados_pecas, resumo_placas)
    if not linhas_ajustadas:
        print("Nenhuma placa 'não stock' encontrada para ajuste.")
        return dados_pecas
    # Atualiza custos/preços dos items (chama função de recalculo para todos os items deste orçamento)
    atualizar_custos_precos_items(num_orc, versao)
    print("[Martelo] Ajuste de placas não stock concluído.")
    return dados_pecas


