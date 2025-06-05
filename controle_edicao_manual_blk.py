from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTableWidgetItem
# A função de formatação visual BLK
from aplicar_formatacao_visual_blk import aplicar_ou_limpar_formatacao_blk


# Índices das colunas relevantes
IDX_BLK = 12
IDX_PLIQ = 21
IDX_PTAB = 20
IDX_DES1PLUS = 22
IDX_DES1MINUS = 23
IDX_DESP = 25
COLUNAS_FORMATADAS_BLK_RANGE = range(18, 33) # Colunas 18 a 32 para formatação BLK
COLUNAS_FORMATACAO_NUMERICA = { # Colunas para formatação numérica imediata
    IDX_PTAB: "moeda",
    IDX_PLIQ: "moeda",
    IDX_DES1PLUS: "percentual",
    IDX_DES1MINUS: "percentual",
    IDX_DESP: "percentual"
}

# Flag global para evitar recursão
_processing_on_cell_changed_for_blk = False

def on_cell_changed_for_blk_logic(ui, row, col):
    """
    Handler principal para o sinal cellChanged da tab_def_pecas.
    - NÃO faz formatação numérica aqui (€, %).
    - Se uma célula nas colunas 18-32 é editada, ativa BLK e aplica formatação visual "manual".
    - Se a checkbox BLK (coluna 12) é desmarcada, limpa a formatação visual das colunas 18-32.
    """
    global _processing_on_cell_changed_for_blk
    if _processing_on_cell_changed_for_blk:
        #print(f"[DEBUG CTRL_BLK] Recursion guard active for L{row+1} C{col+1}")
        return

    table = ui.tab_def_pecas
    if not table: return # Segurança adicional

    # Proteção se a atualização geral estiver em andamento
    if table.property("atualizando_tudo") or table.property("importando_dados"):
        #print(f"[DEBUG CTRL_BLK] Exiting due to table property flags for L{row+1} C{col+1}")
        return

    _processing_on_cell_changed_for_blk = True
    #print(f"[DEBUG CTRL_BLK] --- ENTRADA Handler - L{row+1} C{col+1} ---")

    try:
        item_alterado = table.item(row, col)
        # Caso 1: Edição manual nas colunas 18-32
        if col in COLUNAS_FORMATADAS_BLK_RANGE:
            # Só aplicar se o item realmente existir (evitar erros ao limpar)
            if item_alterado:
                #print(f"[CTRL_BLK] Edição manual detectada: L{row+1}, C{col+1}. Ativando BLK e formatando.")

                # a) Ativar o BLK (coluna 12)
                blk_item = table.item(row, IDX_BLK)
                if blk_item is None:
                    blk_item = QTableWidgetItem()
                    blk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    table.setItem(row, IDX_BLK, blk_item)

                if blk_item.checkState() != Qt.Checked:
                    #print(f"[DEBUG CTRL_BLK] Marcando BLK para L{row+1}")
                    # Não bloquear sinais aqui, pois setCheckState deve disparar este mesmo handler novamente
                    # A flag _processing_on_cell_changed_for_blk protege contra recursão.
                    blk_item.setCheckState(Qt.Checked)

                # b) Aplicar a formatação visual verde ("manual" para PLIQ tooltip)
                aplicar_ou_limpar_formatacao_blk(table, row, aplicar=True, origem_pliq_tooltip="manual")

        # Caso 2: Checkbox BLK (coluna 12) foi alterado
        elif col == IDX_BLK:
            blk_item = table.item(row, IDX_BLK) # Re-obter item caso tenha sido criado acima
            if blk_item:
                #print(f"[DEBUG CTRL_BLK] Coluna BLK alterada: L{row+1}, Estado: {blk_item.checkState()}")
                if blk_item.checkState() == Qt.Unchecked:
                    # BLK foi DESMARCADO pelo utilizador
                    #print(f"[DEBUG CTRL_BLK] BLK desmarcado, limpando formatação para L{row+1}")
                    aplicar_ou_limpar_formatacao_blk(table, row, aplicar=False, origem_pliq_tooltip="")
                # else: BLK Marcado - não faz nada na formatação aqui

    finally:
        _processing_on_cell_changed_for_blk = False # Libera flag
        #print(f"[DEBUG CTRL_BLK] --- SAÍDA Handler - L{row+1} C{col+1} ---")

# A função conectar_eventos_edicao_manual permanece a mesma,
# mas a sua chamada será movida para main.py
def conectar_eventos_edicao_manual(ui):
    """
    Liga o evento 'cellChanged' da tabela 'tab_def_pecas' à função
    on_cell_changed_for_blk_logic.
    Esta função deve ser chamada UMA VEZ durante a inicialização da UI (em main.py).
    """
    table = ui.tab_def_pecas
    
    # Tenta desconectar primeiro para garantir conexão única
    try:
        table.cellChanged.disconnect(on_cell_changed_for_blk_logic)
    except TypeError:
        pass 

    # Conecta a função
    table.cellChanged.connect(lambda r, c: on_cell_changed_for_blk_logic(ui, r, c))
    print("[DEBUG CONEXÃO] Sinal cellChanged conectado a on_cell_changed_for_blk_logic.")