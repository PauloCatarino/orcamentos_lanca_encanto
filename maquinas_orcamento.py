from db_connection import obter_cursor


def criar_tabela_maquinas_orcamento():
    """Cria a tabela `orcamento_maquinas` se ainda não existir."""
    try:
        with obter_cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS orcamento_maquinas (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    numero_orcamento VARCHAR(20) NULL,
                    versao_orcamento VARCHAR(10) NULL,
                    descricao_equipamento VARCHAR(50) NULL,
                    valor_producao_std DECIMAL(10,2) NULL,
                    valor_producao_serie DECIMAL(10,2) NULL,
                    UNIQUE KEY idx_orcamento_maq (numero_orcamento, versao_orcamento, descricao_equipamento)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
    except Exception as e:
        print(f"Erro ao criar tabela orcamento_maquinas: {e}")


def registrar_valores_maquinas_orcamento(num_orc, ver_orc):
    """Regista os valores atuais das máquinas para o orçamento."""
    try:
        with obter_cursor() as cursor:
            cursor.execute(
                "SELECT nome_variavel, valor_std, valor_serie FROM maquinas_producao"
            )
            linhas = cursor.fetchall()
            for nome, val_std, val_ser in linhas:
                cursor.execute(
                    """
                    INSERT INTO orcamento_maquinas
                        (numero_orcamento, versao_orcamento, descricao_equipamento, valor_producao_std, valor_producao_serie)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        valor_producao_std = VALUES(valor_producao_std),
                        valor_producao_serie = VALUES(valor_producao_serie)
                    """,
                    (num_orc, ver_orc, nome, val_std, val_ser),
                )
    except Exception as e:
        print(f"Erro ao registrar valores de máquinas: {e}")


def carregar_ou_inicializar_maquinas_orcamento(num_orc, ver_orc):
    """Carrega valores já registados ou inicializa com os padrões."""
    try:
        with obter_cursor() as cursor:
            cursor.execute(
                """
                SELECT descricao_equipamento, valor_producao_std, valor_producao_serie
                FROM orcamento_maquinas
                WHERE numero_orcamento=%s AND versao_orcamento=%s
                """,
                (num_orc, ver_orc),
            )
            linhas = cursor.fetchall()
            if linhas:
                for nome, val_std, val_ser in linhas:
                    cursor.execute(
                        """
                        INSERT INTO maquinas_producao (nome_variavel, valor_std, valor_serie)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            valor_std=VALUES(valor_std),
                            valor_serie=VALUES(valor_serie)
                        """,
                        (nome, val_std, val_ser),
                    )
            else:
                registrar_valores_maquinas_orcamento(num_orc, ver_orc)
    except Exception as e:
        print(f"Erro ao carregar valores de máquinas do orçamento: {e}")