# teste_calc.py
import sys
sys.path.append(".")

from src.db import carregar_tabela

df_pecas = carregar_tabela("dados_def_pecas")
print("Colunas em dados_def_pecas:\n", df_pecas.columns.tolist())

from src.db import carregar_orcamento
from src.calculadora_consumos import calc_consumo_placas, calc_consumo_orlas

def main():
    # ---------------------------------------------------------------
    # 1) Defina aqui os valores reais do seu orçamento:
    # ---------------------------------------------------------------
    num_orc, versao = "250001", "00"

    # ---------------------------------------------------------------
    # 2) Carregamento de dados:
    # ---------------------------------------------------------------
    df_items = carregar_orcamento(num_orc, versao)
    df_pecas  = carregar_tabela("dados_def_pecas")

    # ---------------------------------------------------------------
    # 3) Cálculos de consumo:
    # ---------------------------------------------------------------
    df_placas = calc_consumo_placas(df_items, df_pecas)
    df_orlas  = calc_consumo_orlas(df_items, df_pecas)

    # ---------------------------------------------------------------
    # 4) Impressão de resultados:
    # ---------------------------------------------------------------
    print("=== Consumo de Placas ===")
    print(df_placas.head(), "\n")
    print(df_placas.describe(), "\n")

    print("=== Consumo de Orlas ===")
    print(df_orlas.head(), "\n")
    print(df_orlas.describe())

if __name__ == "__main__":
    main()
