from db_connection import obter_cursor


def criar_tabela_maquinas_orcamento():
    """Cria a tabela `orcamento_maquinas` se ainda não existir."""
    try:
        with obter_cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS orcamento_maquinas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    id_item VARCHAR(50) NULL,
                    num_orc VARCHAR(20) NULL,
                    ver_orc VARCHAR(10) NULL,
                    descricao_equipamento VARCHAR(50) NULL,
                    valor_producao_std DECIMAL(10,2) NULL,
                    valor_producao_serie DECIMAL(10,2) NULL,
                    UNIQUE KEY idx_orcamento_maq (id_item, num_orc, ver_orc, descricao_equipamento)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
    except Exception as e:
        print(f"Erro ao criar tabela orcamento_maquinas: {e}")


def registrar_valores_maquinas_orcamento(num_orc, ver_orc, id_item):
    """Regista os valores atuais das máquinas para o item do orçamento."""
    try:
        with obter_cursor() as cursor:
            cursor.execute("SELECT nome_variavel, valor_std, valor_serie FROM maquinas_producao")
            linhas = cursor.fetchall()
            for nome, val_std, val_ser in linhas:
                cursor.execute(
                    """
                    INSERT INTO orcamento_maquinas
                        (id_item, num_orc, ver_orc, descricao_equipamento, valor_producao_std, valor_producao_serie)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        valor_producao_std = VALUES(valor_producao_std),
                        valor_producao_serie = VALUES(valor_producao_serie)
                    """,
                    (id_item, num_orc, ver_orc, nome, val_std, val_ser)
                )
    except Exception as e:
        print(f"Erro ao registrar valores de máquinas: {e}")