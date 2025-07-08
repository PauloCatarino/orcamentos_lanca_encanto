# maquinas_orcamento.py
# -*- coding: utf-8 -*-

"""
Módulo: maquinas_orcamento.py

Objetivo:
---------
Gerir os valores de produção específicos de cada orçamento.
Este módulo cria a tabela ``orcamento_maquinas`` no banco de dados e
fornece funções para registrar, carregar e salvar esses valores,
permitindo que sejam utilizados nos cálculos de custos.

Funcionalidades:
----------------
1. ``criar_tabela_maquinas_orcamento`` garante que a estrutura da tabela exista.
2. ``registrar_valores_maquinas_orcamento`` grava valores provenientes da UI ou
   dos valores padrão das máquinas.
3. ``carregar_ou_inicializar_maquinas_orcamento`` obtém os valores de um
   orçamento, populando a interface e criando registros padrão caso não
   existam.
4. ``salvar_tabela_orcamento_maquinas`` persiste as edições feitas na UI na
   tabela de banco de dados.

Estas funções mantêm os valores de produção em sincronia com cada orçamento,
permitindo sua aplicação nos cálculos de custos.
"""


from PyQt5.QtWidgets import QTableWidgetItem, QHeaderView
from PyQt5.QtCore import QSettings
from db_connection import obter_cursor

# Resumo padrao das descrições por nome de variável. Utilizado para preencher
# a coluna "Resumo da descrição" sempre que a base de dados não possuir um
# valor definido (ou estiver em branco).
RESUMO_DESCRICOES = {
    "VALOR_SECCIONADORA": "€/ML para a máquina Seccionadora",
    "VALOR_ORLADORA": "€/ML para a máquina Orladora",
    "CNC_PRECO_PECA_BAIXO": "€/peça se AREA_M2_und ≤ 0.7",
    "CNC_PRECO_PECA_MEDIO": "€/peça se 0.7 < AREA_M2_und < 1",
    "CNC_PRECO_PECA_ALTO": "€/peça se AREA_M2_und ≥ 1",
    "VALOR_ABD": "€/peça para a máquina ABD",
    "EUROS_HORA_CNC": "€/hora para a máquina CNC",
    "EUROS_HORA_PRENSA": "€/hora para a máquina Prensa",
    "EUROS_HORA_ESQUAD": "€/hora para a máquina Esquadrejadora",
    "EUROS_EMBALAGEM_M3": "€/M³ para Embalagem",
    "EUROS_HORA_MO": "€/hora para Mão de Obra",
}

ORDER_DESCRICAO = [
    "VALOR_SECCIONADORA",
    "VALOR_ORLADORA",
    "CNC_PRECO_PECA_BAIXO",
    "CNC_PRECO_PECA_MEDIO",
    "CNC_PRECO_PECA_ALTO",
    "VALOR_ABD",
    "EUROS_HORA_CNC",
    "EUROS_HORA_PRENSA",
    "EUROS_HORA_ESQUAD",
    "EUROS_EMBALAGEM_M3",
    "EUROS_HORA_MO",
]

# ---- Persistência da ordem das colunas da tabela -----
SETTINGS_KEY_ORDEM_COLUNAS = "orcamento_maquinas/ordem_colunas"


def _salvar_ordem_colunas(tabela):
    """Guarda a ordem atual das colunas usando ``QSettings``."""
    header = tabela.horizontalHeader()
    ordem = [header.logicalIndex(i) for i in range(header.count())]
    QSettings().setValue(SETTINGS_KEY_ORDEM_COLUNAS, ordem)


def _restaurar_ordem_colunas(tabela):
    """Restaura a ordem de colunas anteriormente guardada, se existir."""
    settings = QSettings()
    ordem = settings.value(SETTINGS_KEY_ORDEM_COLUNAS)
    if ordem:
        try:
            ordem = [int(i) for i in ordem]
        except Exception:
            return
        header = tabela.horizontalHeader()
        if header.count() == len(ordem):
            for visual, logical in enumerate(ordem):
                atual = header.visualIndex(logical)
                if atual != visual:
                    header.moveSection(atual, visual)

def _ordenar_linhas(linhas):
    """Ordena as linhas segundo ``ORDER_DESCRICAO``."""
    mapa = {
        nome: (
            nome,
            std,
            serie,
            resumo if resumo else RESUMO_DESCRICOES.get(nome, ""),
        )
        for nome, std, serie, resumo in linhas
    }
    ordenadas = [
        mapa[nome]
        for nome in ORDER_DESCRICAO
        if nome in mapa
    ]
    for item in linhas:
        if item[0] not in ORDER_DESCRICAO:
            ordenadas.append(item)
    return ordenadas


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
                    resumo_descricao TEXT NULL,
                    UNIQUE KEY idx_orcamento_maq (numero_orcamento, versao_orcamento, descricao_equipamento)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
            try:
                cursor.execute("ALTER TABLE orcamento_maquinas ADD COLUMN resumo_descricao TEXT")
            except Exception:
                pass
    except Exception as e:
        print(f"Erro ao criar tabela orcamento_maquinas: {e}")


def registrar_valores_maquinas_orcamento(num_orc, ver_orc, ui=None):
    """Regista na tabela os valores das máquinas para o orçamento.

    Se ``ui`` for fornecida, lê os dados de ``ui.tableWidget_orcamento_maquinas``;
    caso contrário, utiliza os valores atuais de ``maquinas_producao``.
    """
    try:
        with obter_cursor() as cursor:
            linhas = []
            if ui and hasattr(ui, "tableWidget_orcamento_maquinas"):
                tbl = ui.tableWidget_orcamento_maquinas
                # Usa a descrição da BD caso a célula de resumo esteja vazia
                cursor.execute(
                    "SELECT nome_variavel, descricao FROM maquinas_producao"
                )
                desc_map = {**RESUMO_DESCRICOES, **dict(cursor.fetchall())}
                for row in range(tbl.rowCount()):
                    nome = tbl.item(row, 0).text() if tbl.item(row, 0) else ""
                    std = tbl.item(row, 1).text() if tbl.item(row, 1) else "0"
                    serie = tbl.item(row, 2).text() if tbl.item(row, 2) else "0"
                    resumo = tbl.item(row, 3).text() if tbl.item(row, 3) else ""
                    if not resumo:
                        resumo = desc_map.get(nome, "")
                    linhas.append((nome, float(std), float(serie), resumo))
            else:
                cursor.execute(
                    "SELECT nome_variavel, valor_std, valor_serie, descricao FROM maquinas_producao"
                )
                linhas = [
                    (
                        n,
                        float(vs),
                        float(vr),
                        desc if desc else RESUMO_DESCRICOES.get(n, ""),
                    )
                    for n, vs, vr, desc in cursor.fetchall()
                ]

            linhas = _ordenar_linhas(linhas)

            for nome, val_std, val_ser, resumo in linhas:
                cursor.execute(
                    """
                    INSERT INTO orcamento_maquinas
                        (numero_orcamento, versao_orcamento, descricao_equipamento, valor_producao_std, valor_producao_serie, resumo_descricao)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        valor_producao_std = VALUES(valor_producao_std),
                        valor_producao_serie = VALUES(valor_producao_serie),
                        resumo_descricao = VALUES(resumo_descricao)
                    """,
                    (num_orc, ver_orc, nome, val_std, val_ser, resumo),
                )
    except Exception as e:
        print(f"Erro ao registrar valores de máquinas: {e}")


def carregar_ou_inicializar_maquinas_orcamento(num_orc, ver_orc, ui=None):
    """Carrega valores do orçamento ou cria registros padrão.

    Se ``ui`` for fornecida e possuir ``tableWidget_orcamento_maquinas``,
    também preenche essa tabela com os valores carregados ou iniciais.
    """
    try:
        with obter_cursor() as cursor:
            cursor.execute(
                """
                SELECT descricao_equipamento, valor_producao_std, valor_producao_serie, resumo_descricao
                FROM orcamento_maquinas
                WHERE numero_orcamento=%s AND versao_orcamento=%s
                """,
                (num_orc, ver_orc),
            )
            linhas = cursor.fetchall()
            if not linhas:
                registrar_valores_maquinas_orcamento(num_orc, ver_orc)
                cursor.execute(
                    """
                    SELECT descricao_equipamento, valor_producao_std, valor_producao_serie, resumo_descricao
                    FROM orcamento_maquinas
                    WHERE numero_orcamento=%s AND versao_orcamento=%s
                    """,
                    (num_orc, ver_orc),
                )
                linhas = cursor.fetchall()

            desc_map = {**RESUMO_DESCRICOES}
            if any(not res for _, _, _, res in linhas):
                cursor.execute(
                    "SELECT nome_variavel, descricao FROM maquinas_producao"
                )
                desc_map.update(dict(cursor.fetchall()))

            linhas = _ordenar_linhas([
                (
                    n,
                    float(std),
                    float(serie),
                    res if res else desc_map.get(n, RESUMO_DESCRICOES.get(n, "")),
                )
                for n, std, serie, res in linhas
            ])

            for nome, val_std, val_ser, resumo in linhas:
                cursor.execute(
                    """
                    INSERT INTO maquinas_producao (nome_variavel, valor_std, valor_serie, descricao)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        valor_std=VALUES(valor_std),
                        valor_serie=VALUES(valor_serie),
                        descricao=VALUES(descricao)
                    """,
                    (nome, val_std, val_ser, resumo if resumo else RESUMO_DESCRICOES.get(nome, "")),
                )

        if ui and hasattr(ui, "tableWidget_orcamento_maquinas"):
            tbl = ui.tableWidget_orcamento_maquinas
            tbl.setRowCount(len(linhas))
            for r, (nome, val_std, val_ser, resumo) in enumerate(linhas):
                tbl.setItem(r, 0, QTableWidgetItem(str(nome)))
                tbl.setItem(r, 1, QTableWidgetItem(str(val_std)))
                tbl.setItem(r, 2, QTableWidgetItem(str(val_ser)))
                tbl.setItem(r, 3, QTableWidgetItem(resumo))
                tbl.setItem(r, 4, QTableWidgetItem(num_orc))
                tbl.setItem(r, 5, QTableWidgetItem(ver_orc))

            header = tbl.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.Interactive)
            tbl.resizeColumnsToContents()
            header.setSectionsMovable(True)
            if not hasattr(tbl, "_ordem_conectada"):
                header.sectionMoved.connect(lambda *_: _salvar_ordem_colunas(tbl))
                tbl._ordem_conectada = True
            _restaurar_ordem_colunas(tbl)
    except Exception as e:
        print(f"Erro ao carregar valores de máquinas do orçamento: {e}")


def salvar_tabela_orcamento_maquinas(ui):
    """Guarda no banco de dados os valores editados na tabela do orçamento."""
    try:
        tbl = ui.tableWidget_orcamento_maquinas
    except AttributeError:
        print("Tabela de máquinas do orçamento não encontrada na UI.")
        return False
    try:
        with obter_cursor() as cursor:
            cursor.execute(
                "SELECT nome_variavel, descricao FROM maquinas_producao"
            )
            desc_map = {**RESUMO_DESCRICOES, **dict(cursor.fetchall())}

            for row in range(tbl.rowCount()):
                nome = tbl.item(row, 0).text() if tbl.item(row, 0) else ""
                std = tbl.item(row, 1).text() if tbl.item(row, 1) else "0"
                serie = tbl.item(row, 2).text() if tbl.item(row, 2) else "0"
                resumo = tbl.item(row, 3).text() if tbl.item(row, 3) else ""
                if not resumo:
                    resumo = desc_map.get(nome, "")
                num_orc = tbl.item(row, 4).text() if tbl.item(row, 4) else ""
                ver_orc = tbl.item(row, 5).text() if tbl.item(row, 5) else ""
                cursor.execute(
                    """
                    INSERT INTO orcamento_maquinas
                        (numero_orcamento, versao_orcamento, descricao_equipamento, valor_producao_std, valor_producao_serie, resumo_descricao)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                        valor_producao_std=VALUES(valor_producao_std),
                        valor_producao_serie=VALUES(valor_producao_serie),
                        resumo_descricao=VALUES(resumo_descricao)
                    """,
                    (num_orc, ver_orc, nome, float(std), float(serie), resumo),
                )
        return True
    except Exception as e:
        print(f"Erro ao salvar dados de máquinas do orçamento: {e}")
        return False