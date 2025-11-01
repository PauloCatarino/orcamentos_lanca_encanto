"""
Script para testar se os campos nao_stock estão funcionando corretamente.
"""
from db_connection import get_connection
from utils import formatar_valor_moeda
from Martelo_Orcamentos_V2.app.utils.bool_converter import bool_to_int, int_to_bool

def test_nao_stock_values():
    """Verifica os valores de nao_stock em todas as tabelas relevantes."""
    print("\nTestando valores de nao_stock nas tabelas:")
    
    tabelas = [
        "dados_gerais_materiais", 
        "dados_gerais_ferragens",
        "dados_gerais_sistemas_correr", 
        "dados_gerais_acabamentos",
        "dados_items_materiais",
        "dados_items_ferragens",
        "dados_items_sistemas_correr",
        "dados_items_acabamentos"
    ]
    
    conn = get_connection()
    cur = conn.cursor()
    
    for tabela in tabelas:
        print(f"\nTabela: {tabela}")
        try:
            cur.execute(f"SELECT nao_stock FROM `{tabela}` LIMIT 5")
            valores = cur.fetchall()
            print(f"Primeiros 5 valores:")
            for val in valores:
                val_int = val[0]
                val_bool = int_to_bool(val_int)
                print(f"  - Valor banco: {val_int} -> bool: {val_bool}")
                
        except Exception as e:
            print(f"Erro ao consultar {tabela}: {str(e)}")
            
    print("\nTeste concluído!")
    cur.close()
    conn.close()

if __name__ == "__main__":
    test_nao_stock_values()