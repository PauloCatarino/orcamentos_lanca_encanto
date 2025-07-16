# -*- coding: utf-8 -*-
"""Modulo para gerir percentagens de margens e ajustes associadas a cada orcamento.

Esta tabela guarda os valores de margem de lucro, custos administrativos e
outros ajustes para cada par (num_orc, ver_orc). Quando um orcamento é aberto,
os valores são carregados para a interface. Qualquer alteração é guardada
ao atualizar os custos do orçamento.
"""

from db_connection import obter_cursor
from utils import converter_texto_para_valor, formatar_valor_percentual


def criar_tabela_margens_ajustes():
    """Cria a tabela ``margens_ajustes_percentagens`` se ainda não existir."""
    try:
        with obter_cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS margens_ajustes_percentagens (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    num_orc VARCHAR(20) NOT NULL,
                    ver_orc VARCHAR(10) NOT NULL,
                    margem_lucro_perc DOUBLE DEFAULT 0.0,
                    custos_admin_perc DOUBLE DEFAULT 0.0,
                    margem_acabamentos_perc DOUBLE DEFAULT 0.0,
                    margem_mp_orlas_perc DOUBLE DEFAULT 0.0,
                    margem_mao_obra_perc DOUBLE DEFAULT 0.0,
                    UNIQUE KEY idx_orc (num_orc, ver_orc)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """
            )
    except Exception as e:
        print(f"Erro ao criar tabela margens_ajustes_percentagens: {e}")


def carregar_ou_inicializar_margens(num_orc, ver_orc, ui=None):
    """Carrega as percentagens para ``num_orc`` e ``ver_orc``.

    Se nao existir registo, cria um com valores atuais da UI (se fornecida)
    ou zeros por defeito.
    Se ``ui`` for fornecida, preenche os lineEdits correspondentes.
    """
    try:
        with obter_cursor() as cursor:
            cursor.execute(
                """
                SELECT margem_lucro_perc, custos_admin_perc, margem_acabamentos_perc,
                       margem_mp_orlas_perc, margem_mao_obra_perc
                FROM margens_ajustes_percentagens
                WHERE num_orc=%s AND ver_orc=%s
                """,
                (num_orc, ver_orc),
            )
            row = cursor.fetchone()
            if not row:
                if ui is not None:
                    valores = (
                        converter_texto_para_valor(ui.lineEdit_margem_lucro.text(), "percentual"),
                        converter_texto_para_valor(ui.lineEdit_custos_administrativos.text(), "percentual"),
                        converter_texto_para_valor(ui.margem_acabamentos.text(), "percentual"),
                        converter_texto_para_valor(ui.margem_MP_orlas.text(), "percentual"),
                        converter_texto_para_valor(ui.margem_mao_obra.text(), "percentual"),
                    )
                else:
                    valores = (0.0, 0.0, 0.0, 0.0, 0.0)
                cursor.execute(
                    """
                    INSERT INTO margens_ajustes_percentagens
                        (num_orc, ver_orc, margem_lucro_perc, custos_admin_perc,
                         margem_acabamentos_perc, margem_mp_orlas_perc, margem_mao_obra_perc)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (num_orc, ver_orc, *valores),
                )
                row = valores
    except Exception as e:
        print(f"Erro ao carregar margens do orçamento: {e}")
        return

    if ui is not None and row:
        try:
            margem, admin, acab, mp_orlas, mao = row
            ui.lineEdit_margem_lucro.setText(formatar_valor_percentual(margem))
            ui.lineEdit_custos_administrativos.setText(formatar_valor_percentual(admin))
            ui.margem_acabamentos.setText(formatar_valor_percentual(acab))
            ui.margem_MP_orlas.setText(formatar_valor_percentual(mp_orlas))
            ui.margem_mao_obra.setText(formatar_valor_percentual(mao))
        except Exception as e:
            print(f"Erro ao aplicar margens na UI: {e}")


def salvar_margens(ui):
    """Guarda os valores atuais dos lineEdits na tabela."""
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    ver_orc = ui.lineEdit_versao_orcamento.text().strip()
    valores = (
        converter_texto_para_valor(ui.lineEdit_margem_lucro.text(), "percentual"),
        converter_texto_para_valor(ui.lineEdit_custos_administrativos.text(), "percentual"),
        converter_texto_para_valor(ui.margem_acabamentos.text(), "percentual"),
        converter_texto_para_valor(ui.margem_MP_orlas.text(), "percentual"),
        converter_texto_para_valor(ui.margem_mao_obra.text(), "percentual"),
    )
    try:
        with obter_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO margens_ajustes_percentagens
                    (num_orc, ver_orc, margem_lucro_perc, custos_admin_perc,
                     margem_acabamentos_perc, margem_mp_orlas_perc, margem_mao_obra_perc)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    margem_lucro_perc=VALUES(margem_lucro_perc),
                    custos_admin_perc=VALUES(custos_admin_perc),
                    margem_acabamentos_perc=VALUES(margem_acabamentos_perc),
                    margem_mp_orlas_perc=VALUES(margem_mp_orlas_perc),
                    margem_mao_obra_perc=VALUES(margem_mao_obra_perc)
                """,
                (num_orc, ver_orc, *valores),
            )
    except Exception as e:
        print(f"Erro ao salvar margens do orçamento: {e}")

    return True