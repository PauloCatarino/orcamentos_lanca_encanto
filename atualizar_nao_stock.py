from db_connection import obter_cursorfrom db_connection import obter_cursor



def atualizar_nao_stock():def atualizar_nao_stock():

    print("Iniciando atualização de campos nao_stock...")    cursor = obter_cursor()

        

    tabelas = [    tabelas = [

        "materias_primas",        "materias_primas",

        "dados_gerais_materiais",         "dados_gerais_materiais", 

        "dados_gerais_ferragens",        "dados_gerais_ferragens",

        "dados_gerais_sistemas_correr",         "dados_gerais_sistemas_correr", 

        "dados_gerais_acabamentos",        "dados_gerais_acabamentos",

        "dados_items_materiais",        "dados_items_materiais",

        "dados_items_ferragens",        "dados_items_ferragens",

        "dados_items_sistemas_correr",        "dados_items_sistemas_correr",

        "dados_items_acabamentos"        "dados_items_acabamentos"

    ]    ]

        

    with obter_cursor() as cursor:    for tabela in tabelas:

        for tabela in tabelas:        print(f"\nProcessando tabela: {tabela}")

            print(f"\nProcessando tabela: {tabela}")        try:

            try:            cursor.execute(f"SHOW COLUMNS FROM `{tabela}` LIKE 'nao_stock'")

                cursor.execute(f"SHOW COLUMNS FROM `{tabela}` LIKE 'nao_stock'")            if not cursor.fetchone():

                if not cursor.fetchone():                print(f"  Tabela {tabela} não tem coluna nao_stock")

                    print(f"  Tabela {tabela} não tem coluna nao_stock")                continue

                    continue            

                            print("  Atualizando valores...")

                print("  Atualizando valores...")            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE nao_stock = TRUE")

                cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE nao_stock = TRUE")            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 0 WHERE nao_stock = FALSE")

                cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 0 WHERE nao_stock = FALSE")            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE nao_stock = '✓'")

                cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE nao_stock = '✓'")            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 0 WHERE nao_stock IS NULL")

                cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 0 WHERE nao_stock IS NULL")            cursor.execute(f"ALTER TABLE `{tabela}` MODIFY COLUMN nao_stock INTEGER NOT NULL DEFAULT 0")

                cursor.execute(f"ALTER TABLE `{tabela}` MODIFY COLUMN nao_stock INTEGER NOT NULL DEFAULT 0")            

                            print(f"  Valores atualizados, realizando commit...")

                print(f"  Valores atualizados, realizando commit...")            cursor.execute("COMMIT")

                cursor.execute("COMMIT")            print(f"  Tabela {tabela} atualizada com sucesso")

                print(f"  Tabela {tabela} atualizada com sucesso")            

                        except Exception as e:

            except Exception as e:            print(f"  Erro ao processar {tabela}: {str(e)}")

                print(f"  Erro ao processar {tabela}: {str(e)}")            cursor.execute("ROLLBACK")

                cursor.execute("ROLLBACK")            

                cursor.close()

    print("\nProcesso concluído!")    print("\nProcesso concluído!")



if __name__ == "__main__":if __name__ == "__main__":

    atualizar_nao_stock()    atualizar_nao_stock()