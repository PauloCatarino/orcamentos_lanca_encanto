# aplicar_formatacao_visual_blk.py
# -*- coding: utf-8 -*-

from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtCore import Qt

# Índices das colunas relevantes (para consistência)
IDX_BLK = 12
IDX_PLIQ = 21 # Coluna Preço Líquido, onde o tooltip de origem será armazenado
COLUNAS_FORMATADAS_RANGE = range(18, 33) # Colunas 18 (ref_le) a 32 (esp_mp)

def aplicar_ou_limpar_formatacao_blk(table, row, aplicar=True, origem_pliq_tooltip=""):
    """
    Aplica (se aplicar=True) ou remove (se aplicar=False) a formatação visual
    (fundo verde, tooltips) às colunas 18-32 da linha especificada.
    Define também o tooltip de origem na coluna PLIQ.

    Parâmetros:
    ----------
    table: QTableWidget
        Referência à tabela 'tab_def_pecas'.
    row: int
        Índice da linha a formatar.
    aplicar: bool
        True para aplicar a formatação verde, False para limpar (branco).
    origem_pliq_tooltip: str
        Texto a ser definido como tooltip da coluna PLIQ (geralmente "manual" ou "escolher").
        Será "" se a formatação for limpa.
    """
    #print(f"[DEBUG Format BLK Apply/Clear] Linha {row+1}, Aplicar: {aplicar}, Origem PLIQ: '{origem_pliq_tooltip}'")

    cor_fundo_padrao = QColor(255, 255, 255)  # Branco
    cor_fundo_edicao = QColor(200, 255, 200)  # Verde claro

    tooltip_geral_edicao = "Valor editado"    # Tooltip para colunas 18-32 (exceto PLIQ)

    cor_a_aplicar = cor_fundo_edicao if aplicar else cor_fundo_padrao
    tooltip_geral_a_aplicar = tooltip_geral_edicao if aplicar else ""
    tooltip_pliq_a_aplicar = origem_pliq_tooltip if aplicar else "" # Tooltip do PLIQ só é relevante se aplicando
    fonte_italico = False # Nunca itálico

    # Guardar estado atual dos sinais para restaurar depois
    old_signals_blocked_state = table.signalsBlocked()
    table.blockSignals(True) # Bloquear sinais durante as modificações

    try:
        # Aplicar/Limpar formatação nas colunas 18-32
        for col in COLUNAS_FORMATADAS_RANGE:
            item = table.item(row, col)
            if item is None:
                # Se está a limpar e o item não existe, não faz nada
                if not aplicar:
                    continue
                # Se está a aplicar, cria o item
                item = QTableWidgetItem()
                table.setItem(row, col, item)

            # Aplica a cor de fundo
            item.setBackground(QBrush(cor_a_aplicar))

            # Define o tooltip geral (exceto para PLIQ)
            if col != IDX_PLIQ:
                item.setToolTip(tooltip_geral_a_aplicar)

            # Aplicar estilo da fonte (sem itálico)
            fonte = item.font()
            fonte.setItalic(fonte_italico)
            item.setFont(fonte)

        # Aplicar tooltip específico na coluna PLIQ (21)
        item_pliq = table.item(row, IDX_PLIQ)
        if item_pliq is None:
             # Se está a limpar e o item não existe, não faz nada
             if not aplicar:
                 pass # Continua para o próximo passo (não há item para limpar)
             else:
                 # Se está a aplicar, cria o item
                 item_pliq = QTableWidgetItem()
                 table.setItem(row, IDX_PLIQ, item_pliq)

        # Só define o tooltip se o item existir (foi encontrado ou criado)
        if item_pliq:
            item_pliq.setToolTip(tooltip_pliq_a_aplicar)

    finally:
        table.blockSignals(old_signals_blocked_state) # Restaurar estado anterior dos sinais
print("Módulo aplicar_formatacao_visual_blk.py definido (tentativa 3).")
