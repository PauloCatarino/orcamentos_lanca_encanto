from db_connection import obter_cursor#!/usr/bin/env python# Script para corrigir valores inconsistentes de nao_stock"""Script para corrigir valores inconsistentes de nao_stock.""""""""""""



def fix_nao_stock_values():

    cursor = obter_cursor()

    from db_connection import obter_cursor

    tabelas = [

        "materias_primas",

        "dados_gerais_materiais", 

        "dados_gerais_ferragens",def fix_nao_stock_values():from db_connection import obter_cursor

        "dados_gerais_sistemas_correr", 

        "dados_gerais_acabamentos",    cursor = obter_cursor()

        "dados_items_materiais",

        "dados_items_ferragens",    

        "dados_items_sistemas_correr",

        "dados_items_acabamentos"    tabelas = [

    ]

            "materias_primas",def fix_nao_stock_values():from db_connection import obter_cursorScript para corrigir valores inconsistentes de nao_stock.

    for tabela in tabelas:

        print(f"\nProcessando tabela: {tabela}")        "dados_gerais_materiais", 

        try:

            cursor.execute(f"SHOW COLUMNS FROM `{tabela}` LIKE 'nao_stock'")        "dados_gerais_ferragens",    cursor = obter_cursor()

            if not cursor.fetchone():

                print(f"  Tabela {tabela} não tem coluna nao_stock")        "dados_gerais_sistemas_correr", 

                continue

                    "dados_gerais_acabamentos",    

            print("  Atualizando valores...")

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE nao_stock = TRUE")        "dados_items_materiais",

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 0 WHERE nao_stock = FALSE")

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE nao_stock = '✓'")        "dados_items_ferragens",    tabelas = [

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 0 WHERE nao_stock IS NULL")

            cursor.execute(f"ALTER TABLE `{tabela}` MODIFY COLUMN nao_stock INTEGER NOT NULL DEFAULT 0")        "dados_items_sistemas_correr",

            

            print(f"  Valores atualizados, realizando commit...")        "dados_items_acabamentos"        "materias_primas",def fix_nao_stock_values():"""Script para corrigir valores inconsistentes de nao_stock.

            cursor.execute("COMMIT")

            print(f"  Tabela {tabela} atualizada com sucesso")    ]

            

        except Exception as e:            "dados_gerais_materiais", 

            print(f"  Erro ao processar {tabela}: {str(e)}")

            cursor.execute("ROLLBACK")    for tabela in tabelas:

            

    cursor.close()        print(f"\nProcessando tabela: {tabela}")        "dados_gerais_ferragens",    print("\nCorrigindo valores de nao_stock nas tabelas:")

    print("\nProcesso concluído!")

        try:

if __name__ == "__main__":

    fix_nao_stock_values()            cursor.execute(f"SHOW COLUMNS FROM `{tabela}` LIKE 'nao_stock'")        "dados_gerais_sistemas_correr", 

            if not cursor.fetchone():

                print(f"  Tabela {tabela} não tem coluna nao_stock")        "dados_gerais_acabamentos",    from db_connection import obter_cursor

                continue

                    "dados_items_materiais",

            print("  Atualizando valores...")

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE nao_stock = TRUE")        "dados_items_ferragens",    tabelas = [

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 0 WHERE nao_stock = FALSE")

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE nao_stock = '✓'")        "dados_items_sistemas_correr",

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 0 WHERE nao_stock IS NULL")

            cursor.execute(f"ALTER TABLE `{tabela}` MODIFY COLUMN nao_stock INTEGER NOT NULL DEFAULT 0")        "dados_items_acabamentos"        "materias_primas",""""""

            

            print(f"  Valores atualizados, realizando commit...")    ]

            cursor.execute("COMMIT")

            print(f"  Tabela {tabela} atualizada com sucesso")            "dados_gerais_materiais", 

            

        except Exception as e:    for tabela in tabelas:

            print(f"  Erro ao processar {tabela}: {str(e)}")

            cursor.execute("ROLLBACK")        print(f"\nProcessando tabela: {tabela}")        "dados_gerais_ferragens",def fix_nao_stock_values():

            

    cursor.close()        try:

    print("\nProcesso concluído!")

            # Verifica se a tabela tem a coluna        "dados_gerais_sistemas_correr", 

if __name__ == "__main__":

    fix_nao_stock_values()            cursor.execute(f"SHOW COLUMNS FROM `{tabela}` LIKE 'nao_stock'")

            if not cursor.fetchone():        "dados_gerais_acabamentos",    """Corrige valores inconsistentes de nao_stock em todas as tabelas."""from db_connection import obter_cursorfrom db_connection import get_connection

                print(f"  Tabela {tabela} não tem coluna nao_stock")

                continue        "dados_items_materiais",

            

            # Atualiza valores        "dados_items_ferragens",    print("\nCorrigindo valores de nao_stock nas tabelas:")

            print("  Atualizando valores...")

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE nao_stock = TRUE")        "dados_items_sistemas_correr",

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 0 WHERE nao_stock = FALSE")

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE nao_stock = '✓'")        "dados_items_acabamentos"    from Martelo_Orcamentos_V2.app.utils.bool_converter import bool_to_int

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 0 WHERE nao_stock IS NULL")

            cursor.execute(f"ALTER TABLE `{tabela}` MODIFY COLUMN nao_stock INTEGER NOT NULL DEFAULT 0")    ]

            

            cursor.execute("COMMIT")        tabelas = [

            print(f"  Tabela {tabela} atualizada com sucesso")

                cursor = obter_cursor()

        except Exception as e:

            print(f"  Erro ao processar {tabela}: {str(e)}")            "materias_primas",def fix_nao_stock_values():

            cursor.execute("ROLLBACK")

                for tabela in tabelas:

    cursor.close()

    print("\nProcesso concluído!")        print(f"\nTabela: {tabela}")        "dados_gerais_materiais", 



if __name__ == "__main__":        try:

    fix_nao_stock_values()
            cursor.execute(f"SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{tabela}' AND COLUMN_NAME = 'nao_stock'")        "dados_gerais_ferragens",    """Corrige valores inconsistentes de nao_stock em todas as tabelas."""def fix_nao_stock_values():

            tipo_atual = cursor.fetchone()

            if not tipo_atual:        "dados_gerais_sistemas_correr", 

                print(f"Tabela {tabela} não tem coluna nao_stock")

                continue        "dados_gerais_acabamentos",    print("\nCorrigindo valores de nao_stock nas tabelas:")    """Corrige valores inconsistentes de nao_stock em todas as tabelas."""

                

            print(f"Tipo atual da coluna: {tipo_atual[0]}")        "dados_items_materiais",

            

            # 1. Ajusta valores TRUE/FALSE booleanos        "dados_items_ferragens",        print("\nCorrigindo valores de nao_stock nas tabelas:")

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE nao_stock = TRUE")

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 0 WHERE nao_stock = FALSE")        "dados_items_sistemas_correr",

            

            # 2. Ajusta checkmark ('✓') para 1        "dados_items_acabamentos"    tabelas = [    

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE nao_stock = '✓'")

                ]

            # 3. Converte strings

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE CAST(nao_stock AS CHAR) IN ('true', 'sim', 'yes')")            "dados_gerais_materiais",     tabelas = [

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 0 WHERE CAST(nao_stock AS CHAR) IN ('false', 'nao', 'no')")

                cursor = obter_cursor()

            # 4. Valores NULL viram 0

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 0 WHERE nao_stock IS NULL")            "dados_gerais_ferragens",        "dados_gerais_materiais", 

            

            # 5. Força quaisquer outros valores para 0/1    for tabela in tabelas:

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = CASE WHEN nao_stock = 0 THEN 0 ELSE 1 END WHERE nao_stock != 0 AND nao_stock != 1")

                    print(f"\nTabela: {tabela}")        "dados_gerais_sistemas_correr",         "dados_gerais_ferragens",

            # 6. Altera o tipo da coluna para INTEGER

            cursor.execute(f"ALTER TABLE `{tabela}` MODIFY COLUMN nao_stock INTEGER NOT NULL DEFAULT 0")        try:

            

            cursor.execute("COMMIT")            cursor.execute(f"SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{tabela}' AND COLUMN_NAME = 'nao_stock'")        "dados_gerais_acabamentos",        "dados_gerais_sistemas_correr", 

            print(f"Tabela {tabela} corrigida e alterada para INTEGER")

                        tipo_atual = cursor.fetchone()

        except Exception as e:

            print(f"Erro ao corrigir {tabela}: {str(e)}")            if not tipo_atual:        "dados_items_materiais",        "dados_gerais_acabamentos",

            cursor.execute("ROLLBACK")

                            print(f"Tabela {tabela} não tem coluna nao_stock")

    print("\nCorreções concluídas!")

    cursor.close()                continue        "dados_items_ferragens",        "dados_items_materiais",



if __name__ == "__main__":                

    fix_nao_stock_values()
            print(f"Tipo atual da coluna: {tipo_atual[0]}")        "dados_items_sistemas_correr",        "dados_items_ferragens",

            

            # 1. Ajusta valores TRUE/FALSE booleanos        "dados_items_acabamentos"        "dados_items_sistemas_correr",

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE nao_stock = TRUE")

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 0 WHERE nao_stock = FALSE")    ]        "dados_items_acabamentos"

            

            # 2. Ajusta checkmark ('✓') para 1        ]

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE nao_stock = '✓'")

                cursor = obter_cursor()    

            # 3. Converte strings

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE LOWER(nao_stock) IN ('true', 'sim', 'yes')")        conn = get_connection()

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 0 WHERE LOWER(nao_stock) IN ('false', 'nao', 'no')")

                for tabela in tabelas:    cur = conn.cursor()

            # 4. Valores NULL viram 0

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 0 WHERE nao_stock IS NULL")        print(f"\nTabela: {tabela}")    

            

            # 5. Força quaisquer outros valores para 0/1        try:    for tabela in tabelas:

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = CASE WHEN nao_stock = 0 THEN 0 ELSE 1 END WHERE nao_stock != 0 AND nao_stock != 1")

                        # 1. Ajusta valores TRUE/FALSE booleanos        print(f"\nTabela: {tabela}")

            # 6. Altera o tipo da coluna para INTEGER

            cursor.execute(f"ALTER TABLE `{tabela}` MODIFY COLUMN nao_stock INTEGER NOT NULL DEFAULT 0")            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE nao_stock = TRUE")        try:

            

            cursor.execute("COMMIT")            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 0 WHERE nao_stock = FALSE")            # 1. Ajusta valores TRUE para 1

            print(f"Tabela {tabela} corrigida e alterada para INTEGER")

                                    cur.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE nao_stock = TRUE")

        except Exception as e:

            print(f"Erro ao corrigir {tabela}: {str(e)}")            # 2. Ajusta checkmark ('✓') para 1            

            cursor.execute("ROLLBACK")

                        cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE nao_stock = '✓'")            # 2. Ajusta valores FALSE para 0

    print("\nCorreções concluídas!")

    cursor.close()                        cur.execute(f"UPDATE `{tabela}` SET nao_stock = 0 WHERE nao_stock = FALSE")



if __name__ == "__main__":            # 3. Converte strings            

    fix_nao_stock_values()
            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE nao_stock IN ('true', 'sim', 'yes')")            # 3. Ajusta checkmark ('✓') para 1

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 0 WHERE nao_stock IN ('false', 'nao', 'no')")            cur.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE nao_stock = '✓'")

                        

            # 4. Valores NULL viram 0            # 4. Converte strings

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 0 WHERE nao_stock IS NULL")            cur.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE nao_stock IN ('true', 'sim', 'yes')")

                        cur.execute(f"UPDATE `{tabela}` SET nao_stock = 0 WHERE nao_stock IN ('false', 'nao', 'no')")

            # 5. Força quaisquer outros valores para 0/1            

            cursor.execute(f"UPDATE `{tabela}` SET nao_stock = 1 WHERE nao_stock != 0 AND nao_stock != 1")            # 5. Valores NULL viram 0

                        cur.execute(f"UPDATE `{tabela}` SET nao_stock = 0 WHERE nao_stock IS NULL")

            # 6. Altera o tipo da coluna para INTEGER            

            cursor.execute(f"ALTER TABLE `{tabela}` MODIFY COLUMN nao_stock INTEGER NOT NULL DEFAULT 0")            conn.commit()

                        print(f"Tabela {tabela} corrigida")

            cursor.execute("COMMIT")            

            print(f"Tabela {tabela} corrigida e alterada para INTEGER")        except Exception as e:

                        print(f"Erro ao corrigir {tabela}: {str(e)}")

        except Exception as e:            conn.rollback()

            print(f"Erro ao corrigir {tabela}: {str(e)}")            

            cursor.execute("ROLLBACK")    print("\nCorreções concluídas!")

                cur.close()

    print("\nCorreções concluídas!")    conn.close()

    cursor.close()

if __name__ == "__main__":

if __name__ == "__main__":    fix_nao_stock_values()
    fix_nao_stock_values()