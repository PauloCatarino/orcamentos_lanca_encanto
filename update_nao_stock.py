import mysql.connector
from mysql.connector import Error

# Configuração da conexão com o banco de dados
db_config = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "orcamentos_le",
    "password": "admin",
    "database": "orcamentos",
    "charset": "utf8mb4"
}

def atualizar_nao_stock():
    print("Iniciando atualização de campos nao_stock...")
    
    try:
        # Conecta ao banco
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        tabelas = [
            "dados_gerais_materiais", 
            "dados_gerais_ferragens",
            "dados_gerais_sistemas_correr", 
            "dados_gerais_acabamentos"
        ]
        
        for tabela in tabelas:
            print(f"\nProcessando tabela: {tabela}")
            try:
                # Verifica se a coluna existe
                cursor.execute(f"SHOW COLUMNS FROM `{tabela}` LIKE 'nao_stock'")
                if not cursor.fetchone():
                    print(f"  Tabela {tabela} não tem coluna nao_stock")
                    continue
                
                print("  Atualizando valores...")
                
                # Primeiro, atualiza valores NULL para 0
                update_null = f"UPDATE `{tabela}` SET nao_stock = 0 WHERE nao_stock IS NULL"
                cursor.execute(update_null)
                print(f"  - Atualizados {cursor.rowcount} valores NULL para 0")
                
                # Depois, normaliza todos os valores para 0/1
                # Primeiro converte strings para 0/1
                update_strings = f"""
                    UPDATE `{tabela}` 
                    SET nao_stock = CASE 
                        WHEN LOWER(CAST(nao_stock AS CHAR)) IN ('0', 'false', 'f', 'n', 'no', '') THEN 0 
                        WHEN LOWER(CAST(nao_stock AS CHAR)) IN ('1', 'true', 't', 'y', 'yes', '✓') THEN 1
                        ELSE nao_stock
                    END
                    WHERE nao_stock IS NOT NULL
                """
                cursor.execute(update_strings)
                print(f"  - Convertidos {cursor.rowcount} valores string para 0/1")
                
                # Depois normaliza quaisquer outros valores numéricos
                update_numbers = f"""
                    UPDATE `{tabela}` 
                    SET nao_stock = CASE 
                        WHEN nao_stock = 0 THEN 0
                        ELSE 1
                    END
                    WHERE nao_stock IS NOT NULL
                """
                cursor.execute(update_strings)
                print(f"  - Convertidos {cursor.rowcount} valores string para 0/1")
                
                cursor.execute(update_numbers)
                print(f"  - Normalizados {cursor.rowcount} valores numéricos para 0/1")
                
                # Altera o tipo da coluna para INTEGER
                alter_column = f"ALTER TABLE `{tabela}` MODIFY COLUMN nao_stock INTEGER NOT NULL DEFAULT 0"
                cursor.execute(alter_column)
                print("  - Tipo da coluna alterado para INTEGER")
                
                # Mostra distribuição atual dos valores
                count_sql = f"SELECT nao_stock, COUNT(*) FROM {tabela} GROUP BY nao_stock"
                cursor.execute(count_sql)
                print("\n  Distribuição atual dos valores:")
                for value, count in cursor.fetchall():
                    print(f"  - Valor {value}: {count} registros")
                
                conn.commit()
                print(f"\n  Tabela {tabela} atualizada com sucesso!")
                
            except Error as e:
                print(f"  Erro ao processar {tabela}: {str(e)}")
                conn.rollback()
                
        print("\nProcesso concluído!")
                
    except Error as e:
        print(f"\nErro de conexão: {str(e)}")
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()
            print("\nConexão com o banco fechada.")

if __name__ == "__main__":
    atualizar_nao_stock()