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


def atualizar_desp_na_bd(id_peca, novo_desp, custo_mp_und=None, custo_mp_total=None):
    """Atualiza ``desp`` e opcionalmente os custos de MP na BD."""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            if custo_mp_und is not None and custo_mp_total is not None:
                cur.execute(
                    "UPDATE dados_def_pecas SET desp=%s, blk=1, custo_mp_und=%s, custo_mp_total=%s WHERE id=%s",
                    (novo_desp, custo_mp_und, custo_mp_total, id_peca),
                )
            else:
                cur.execute(
                    "UPDATE dados_def_pecas SET desp=%s, blk=1 WHERE id=%s",
                    (novo_desp, id_peca),
                )
            conn.commit()
        conn.close()
        print(
            f"[BD] Peça id {id_peca} atualizada: desp={novo_desp:.4f}, "
            f"custo_mp_und={custo_mp_und}, custo_mp_total={custo_mp_total}"
        )
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
            area_pecas = float(row.get('m2_total_pecas', 0))
            area_placa = float(row['area_placa'])
            desc = row['descricao_no_orcamento']
            # Número de placas necessário baseado apenas na soma das peças (sem
            # desperdício). Isto garante que consideramos placas inteiras sempre
            # que o material for marcado como "não stock".
            if area_placa > 0:
                ratio = area_pecas / area_placa
                n_placas = math.ceil(ratio - 0.01)
                if n_placas < 1:
                    n_placas = 1
                area_total_placas = n_placas * area_placa
            else:
                n_placas = 0
                area_total_placas = 0

            if area_pecas > 0:
                novo_desp = (area_total_placas / area_pecas) - 1
            else:
                novo_desp = 0
            if debug:
                print(
                    f"[{desc}] Não Stock: {n_placas} placas inteiras, "
                    f"Área placas: {area_total_placas:.3f} m2, "
                    f"Área peças: {area_pecas:.3f} m2, "
                    f"Novo %desp: {novo_desp*100:.2f}%"
                )
            # Atualizar todas as linhas em dados_pecas que correspondam a este material
            desc_filtrada = str(desc).strip().lower()
            mask = dados_pecas['descricao_no_orcamento'].str.strip().str.lower() == desc_filtrada
            dados_pecas.loc[mask, 'desp'] = round(novo_desp, 4)
            for idx2, peca in dados_pecas.loc[mask].iterrows():
                id_peca = peca['id']
                cp09 = float(peca.get('cp09_custo_mp', 0) or 0)
                mps_flag = bool(peca.get('mps'))
                und = str(peca.get('und', '')).upper()
                area_m2 = float(peca.get('area_m2_und', 0) or 0)
                spp_ml = float(peca.get('spp_ml_und', 0) or 0)
                pliq = float(peca.get('pliq', 0) or 0)
                qt_total = float(peca.get('qt_total', 0) or 0)

                custo_mp_und = 0.0
                if cp09 >= 1 and not mps_flag:
                    if und == 'M2':
                        custo_mp_und = area_m2 * (1 + novo_desp) * pliq
                    elif und == 'ML':
                        custo_mp_und = spp_ml * (1 + novo_desp) * pliq
                    elif und == 'UND':
                        custo_mp_und = pliq * (1 + novo_desp)

                custo_mp_total = custo_mp_und * qt_total

                dados_pecas.at[idx2, 'custo_mp_und'] = round(custo_mp_und, 2)
                dados_pecas.at[idx2, 'custo_mp_total'] = round(custo_mp_total, 2)

                atualizar_desp_na_bd(
                    id_peca,
                    novo_desp,
                    round(custo_mp_und, 2),
                    round(custo_mp_total, 2),
                )
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
            item_num = str(item["item"]).strip()

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
                mps_flag = p["mps"]
                und = p["und"]
                area_m2 = p["area_m2_und"]
                spp_ml = p["spp_ml_und"]
                pliq = p["pliq"]
                desp_p = p["desp"]
                cp09 = p["cp09_custo_mp"]
                qt_total = p["qt_total"]
                cml1 = p["custo_ml_c1"]
                cml2 = p["custo_ml_c2"]
                cml3 = p["custo_ml_l1"]
                cml4 = p["custo_ml_l2"]
                soma_und = p["Soma_Custo_und"]
                soma_acb = p["Soma_Custo_ACB"]

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
            margem_acabamentos_perc = float(item.get("margem_acabamentos_perc") or 0)
            margem_mp_orlas_perc = float(item.get("margem_mp_orlas_perc") or 0)
            margem_mao_obra_perc = float(item.get("margem_mao_obra_perc") or 0)

            valor_margem = custo_produzido * margem_perc
            valor_custos_admin = custo_produzido * custos_admin_perc
            valor_acabamentos = acab * margem_acabamentos_perc
            valor_mp_orlas = (mp + orlas) * margem_mp_orlas_perc
            valor_mao_obra = mao * margem_mao_obra_perc

            preco_unit = (
                custo_produzido
                + valor_margem
                + valor_custos_admin
                + valor_acabamentos
                + valor_mp_orlas
                + valor_mao_obra
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
                    margem_acabamentos_perc=%s,
                    valor_acabamentos=%s,
                    margem_mp_orlas_perc=%s,
                    valor_mp_orlas=%s,
                    margem_mao_obra_perc=%s,
                    valor_mao_obra=%s
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
                    margem_acabamentos_perc,
                    valor_acabamentos,
                    margem_mp_orlas_perc,
                    valor_mp_orlas,
                    margem_mao_obra_perc,
                    valor_mao_obra,
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


