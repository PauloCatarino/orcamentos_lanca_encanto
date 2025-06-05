#tabela_def_pecas_combobox_mat_default.py
# -*- coding: utf-8 -*-

"""
Resumo:
-------
Esta função percorre todas as linhas da tabela 'tab_def_pecas' e transforma o valor da coluna 
'Mat_Default' (índice 13) em um QComboBox dinâmico. Para cada linha, a função:
  1. Recupera o valor da coluna 'Tab_Default' (índice 14) para determinar qual tabela de dados consultar.
  2. Utiliza os parâmetros 'num_orc', 'ver_orc' e o identificador específico (id_mat, id_fer, id_acb ou id_sc)
     obtidos dos respectivos lineEdits para filtrar a consulta na tabela de dados 
     (dados_items_materiais, dados_items_ferragens, dados_items_acabamentos ou dados_items_sistemas_correr).
  3. Executa uma query que retorna os materiais distintos (coluna "material") disponíveis para aquele item.
  4. Preenche o QComboBox com a lista de materiais obtida. Se o valor atualmente exibido na célula não estiver
     na lista, ele é adicionado ao início.
  5. Conecta o sinal 'currentTextChanged' do QComboBox a uma função (on_mat_default_changed) que, quando o valor 
     for alterado, atualizará os demais dados da linha.
     
Funcionalidade:
---------------
- Atualiza dinamicamente a coluna 'Mat_Default' com um QComboBox cujas opções refletem os materiais disponíveis 
  na base de dados, conforme os parâmetros do orçamento (num_orc, ver_orc) e o identificador específico (id_mat, 
  id_fer, id_acb, id_sc).
"""

from PyQt5.QtWidgets import QComboBox, QTableWidgetItem, QMessageBox
from PyQt5.QtCore import Qt
import mysql.connector
from db_connection import obter_cursor
from utils import formatar_valor_moeda, formatar_valor_percentual

##########################################################################
# Função 1: aplicar_combobox_mat_default
##########################################################################
def aplicar_combobox_mat_default(ui):
    """
    Transforma a coluna 'Mat_Default' da tabela 'tab_def_pecas' em QComboBox dinâmicos.
    
    Para cada linha:
      - Recupera o valor da coluna "Tab_Default" (índice 14) e, com base nesse valor, determina
        qual tabela de dados consultar e qual o campo identificador correspondente.
      - Obtém os parâmetros do orçamento (num_orc, ver_orc, identificador) dos respectivos lineEdits.
      - Executa uma query na base de dados para obter os materiais distintos disponíveis.
      - Cria um QComboBox e preenche-o com a lista de materiais obtida.
      - Se o valor atualmente na célula "Mat_Default" (índice 13) não estiver na lista, insere-o no início.
      - Conecta o sinal "currentTextChanged" do QComboBox para chamar a função on_mat_default_changed
        (através de um handler que identifica a linha correspondente).
      - Define o QComboBox como widget da célula na coluna "Mat_Default".
    """
    table = ui.tab_def_pecas
    print("[INFO] Iniciando aplicação de ComboBox na coluna Mat_Default...") # Info

    valor_num_orc = ui.lineEdit_num_orcamento.text().strip()
    valor_ver_orc = ui.lineEdit_versao_orcamento.text().strip()
    valor_ids = ui.lineEdit_item_orcamento.text().strip()

    # Mapeamento Tab_Default -> Tabela BD e Coluna ID (mantido)
    db_mapping = {
        "Tab_Material_11": "dados_items_materiais",
        "Tab_Ferragens_11": "dados_items_ferragens",
        "Tab_Acabamentos_12": "dados_items_acabamentos",
        "Tab_Sistemas_Correr_11": "dados_items_sistemas_correr"
    }
    id_mapping = {
        "Tab_Material_11": "id_mat",
        "Tab_Ferragens_11": "id_fer",
        "Tab_Acabamentos_12": "id_acb",
        "Tab_Sistemas_Correr_11": "id_sc"
    }

    for row in range(table.rowCount()):
        item_tab = table.item(row, 14) # Coluna Tab_Default
        if not item_tab: continue
        tab_default = item_tab.text().strip()

        if tab_default not in db_mapping: continue

        db_table = db_mapping[tab_default]
        id_column = id_mapping[tab_default]

        # Consulta à BD para obter materiais (usando obter_cursor)
        materials = []
        try:
            # Utiliza o gestor de contexto
            with obter_cursor() as cursor:
                # Query para obter materiais distintos
                # Usar backticks para nomes de colunas/tabelas se contiverem caracteres especiais ou forem palavras reservadas
                # Assumindo que 'material' é o nome correto da coluna
                query = f"""
                    SELECT DISTINCT `material`
                    FROM `{db_table}`
                    WHERE `num_orc`=%s AND `ver_orc`=%s AND `{id_column}`=%s
                    AND `material` IS NOT NULL AND `material` <> ''
                    ORDER BY `material`
                """
                cursor.execute(query, (valor_num_orc, valor_ver_orc, valor_ids))
                # Extrai os resultados
                materials = [r[0] for r in cursor.fetchall()]
            # A conexão e o cursor são fechados automaticamente ao sair do bloco 'with'

        except mysql.connector.Error as db_err:
            # Logar erro de BD sem interromper o loop para outras linhas
            print(f"[ERRO DB] Linha {row}: Erro ao consultar materiais para '{db_table}': {db_err}")
            # Pode definir 'materials' como lista vazia ou manter o valor anterior?
            # Por segurança, continuamos com a lista vazia neste caso.
            materials = []
        except Exception as e:
            print(f"[ERRO INESPERADO] Linha {row}: Erro ao consultar materiais: {e}")
            import traceback
            traceback.print_exc()
            materials = []

        # Cria e configura o QComboBox
        combo = QComboBox()
        # Adiciona um item vazio no início para representar "Nenhum" ou "Não Definido"
        combo.addItem("")
        combo.addItems(materials)

        item_mat = table.item(row, 13) # Coluna Mat_Default
        current_text = item_mat.text().strip() if item_mat else ""

        # Tenta definir o valor atual no ComboBox
        idx = combo.findText(current_text, Qt.MatchFixedString) # Busca exata
        if idx >= 0:
            combo.setCurrentIndex(idx)
        elif current_text:  # Se o texto atual não está na lista, adiciona manualmente e define como selecionado
             # Opção 1: Adicionar o item antigo (pode indicar dados inconsistentes)
             # combo.insertItem(1, current_text) # Insere após o item vazio
             # combo.setCurrentIndex(1)
             # Opção 2: Definir como vazio (força o usuário a escolher um válido)
             print(f"[INFO] Linha {row}: Material '{current_text}' não está na lista, mas será preservado pelo utilizador.")
             combo.insertItem(1, current_text)  # Insere logo após o item vazio
             combo.setCurrentIndex(1) # Define o item atual como o segundo (o primeiro é vazio)
             # Se o texto atual não estiver na lista e for vazio, define como o primeiro item (vazio)
        else:
            combo.setCurrentIndex(0) # Define para o item vazio se não houver texto atual

        # Conecta o sinal usando um handler que captura a linha correta
        def criar_handler_combobox(captured_row, combobox_widget):
            def handler(new_text):
                # Chama a função de atualização passando a linha capturada
                on_mat_default_changed(ui, captured_row, new_text)
            return handler

        # Desconecta qualquer handler anterior para evitar múltiplas conexões
        try:
            combo.currentTextChanged.disconnect()
        except TypeError: # Sinal não estava conectado
            pass
        # Conecta o novo handler
        combo.currentTextChanged.connect(criar_handler_combobox(row, combo))

        table.setCellWidget(row, 13, combo) # Define o ComboBox na célula

    print("[INFO] Aplicação de ComboBox na coluna Mat_Default concluída.")

##########################################################################
# Função 2: on_mat_default_changed
##########################################################################
def on_mat_default_changed(ui, row, new_value):
    """
    Esta função é chamada quando o usuário altera a seleção no QComboBox da coluna "Mat_Default".
    Ela realiza o seguinte:
      - Atualiza a célula "Mat_Default" com o novo valor.
      - Verifica o valor de "Tab_Default" (índice 14) para determinar se há dados adicionais a serem importados.
      - Se o valor de "Tab_Default" corresponder a uma tabela de dados (ex.: Tab_Material_11),
        executa uma query para buscar os dados correspondentes (descrição, ref_le, ptab, etc.).
      - Atualiza as colunas correspondentes na linha com os valores retornados pela query,
        inclusive a coluna "Esp" (índice 8).
    """
    table = ui.tab_def_pecas
    print(f"[INFO] Mat_Default alterado na linha {row} para: '{new_value}'") # Info

    # Atualiza visualmente e internamente a célula Mat_Default com o novo valor
    item_mat = QTableWidgetItem(new_value)
    table.setItem(row, 13, item_mat)
    
    # Passo 1: Atualizar o item QTableWidgetItem subjacente (opcional, mas bom para consistência)
    # O setCellWidget substitui o item, então precisamos recriá-lo ou obtê-lo se existir.
    # É mais seguro não depender do item subjacente aqui, pois o widget é o principal.

    item_tab = table.item(row, 14) # Coluna Tab_Default
    if item_tab is None: return
    tab_default = item_tab.text().strip()

    if tab_default not in {"Tab_Material_11", "Tab_Ferragens_11", "Tab_Acabamentos_12", "Tab_Sistemas_Correr_11"}:
        print(f"[AVISO] Linha {row}: Tab_Default '{tab_default}' inválido para atualização via Mat_Default.")
        return

    # Mapeamento (mantido)
    db_mapping = {
        "Tab_Material_11": "dados_items_materiais", "Tab_Ferragens_11": "dados_items_ferragens",
        "Tab_Acabamentos_12": "dados_items_acabamentos", "Tab_Sistemas_Correr_11": "dados_items_sistemas_correr"
    }
    id_mapping = {
        "Tab_Material_11": "id_mat", "Tab_Ferragens_11": "id_fer",
        "Tab_Acabamentos_12": "id_acb", "Tab_Sistemas_Correr_11": "id_sc"
    }
    db_table = db_mapping.get(tab_default)
    id_column = id_mapping.get(tab_default)

    if not db_table or not id_column: return # Segurança adicional

    valor_num_orc = ui.lineEdit_num_orcamento.text().strip()
    valor_ver_orc = ui.lineEdit_versao_orcamento.text().strip()
    valor_ids = ui.lineEdit_item_orcamento.text().strip()

    resultado = None
    try:
        # Usa obter_cursor para a consulta
        with obter_cursor() as cursor:
            query = (
                "SELECT descricao, ref_le, descricao_no_orcamento, ptab, pliq, desc1_plus, desc2_minus, und, desp, "
                "corres_orla_0_4, corres_orla_1_0, tipo, familia, comp_mp, larg_mp, esp_mp "
                f"FROM `{db_table}` WHERE `num_orc`=%s AND `ver_orc`=%s AND `{id_column}`=%s AND `material`=%s"
            )
            cursor.execute(query, (valor_num_orc, valor_ver_orc, valor_ids, new_value))
            resultado = cursor.fetchone()

        # Processa o resultado fora do 'with'
        if resultado:
            # Mapeamento BD -> UI (mantido)
            mapping = {
                 0: 3,  1: 18,  2: 19,  3: 20,  4: 21,  5: 22,  6: 23,  7: 24,  8: 25,
                 9: 26, 10: 27, 11: 28, 12: 29, 13: 30, 14: 31, 15: 32
            }
            table.blockSignals(True) # Bloqueia sinais para evitar loops
            try:
                for idx_res, col_target_ui in mapping.items():
                    valor_bd = resultado[idx_res]
                    texto_formatado = ""
                    if valor_bd is not None:
                        # Formatação (mantida)
                        if col_target_ui in {20, 21}: # ptab, pliq
                            try: texto_formatado = formatar_valor_moeda(float(valor_bd))
                            except (ValueError, TypeError): texto_formatado = str(valor_bd)
                        elif col_target_ui in {22, 23, 25}: # des1plus, des1minus, desp
                            try: texto_formatado = formatar_valor_percentual(float(valor_bd))
                            except (ValueError, TypeError): texto_formatado = str(valor_bd)
                        else: texto_formatado = str(valor_bd)
                    else: texto_formatado = ""

                    # Garante que o item existe
                    item_destino = table.item(row, col_target_ui)
                    if item_destino is None:
                        item_destino = QTableWidgetItem()
                        table.setItem(row, col_target_ui, item_destino)
                    item_destino.setText(texto_formatado)

                # Atualiza coluna Esp (índice 8)
                esp_valor_bd = resultado[15]
                esp_str = str(esp_valor_bd) if esp_valor_bd is not None else ""
                item_esp = table.item(row, 8)
                if item_esp is None:
                    item_esp = QTableWidgetItem()
                    table.setItem(row, 8, item_esp)
                item_esp.setText(esp_str)
                print(f"  [INFO] Linha {row}: Dados atualizados com base em Mat_Default '{new_value}'.")
            finally:
                table.blockSignals(False) # Desbloqueia sinais

        else:
            # Se não encontrou dados para o novo material, talvez limpar os campos?
            print(f"[AVISO] Linha {row}: Nenhum dado encontrado para Mat_Default '{new_value}' em '{db_table}'. Campos relacionados não atualizados.")
            # Poderia limpar as colunas aqui (opcional)

    except mysql.connector.Error as db_err:
        print(f"[ERRO DB] Linha {row}: Erro ao buscar dados para Mat_Default '{new_value}': {db_err}")
        QMessageBox.warning(None, "Erro Base de Dados", f"Erro ao buscar dados para a linha {row+1} (Mat: {new_value}): {db_err}")
    except Exception as e:
        print(f"[ERRO INESPERADO] Linha {row}: Erro em on_mat_default_changed: {e}")
        import traceback
        traceback.print_exc()
        QMessageBox.warning(None, "Erro Inesperado", f"Erro ao processar alteração na linha {row+1}: {e}")
