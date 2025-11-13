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
import unicodedata
from db_connection import obter_cursor
from utils import formatar_valor_moeda, formatar_valor_percentual

TAB_SIS_CORRER_DB = "dados_items_sistemas_correr"
TAB_SIS_CORRER_DEFAULT = "Tab_Sistemas_Correr_11"
IDX_DEF_PECA_COL = 2  # Coluna fixa Def_Peca na tab_def_pecas


def _normalize_key(value):
    """Remove acentos, espaços extras e coloca em maiúsculas para comparação."""
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.strip().upper()


def _build_special_configs():
    """
    Cria o mapeamento Def_Peca -> configuração especial.

    Cada configuração indica que aquele Def_Peca deve usar os dados da
    tabela de Sistemas Correr, filtrando pela linha correta (sistemas_correr),
    família desejada e, opcionalmente, um material preferido a selecionar.
    """
    entries = [
        # Grupo: SPP Ajustáveis (família ferragens - mostrar todos dessa linha)
        ("CALHA SUPERIOR {SPP} 1 CORRER", "Calha Superior 1 SPP", "FERRAGENS", False),
        ("CALHA SUPERIOR {SPP} 2 CORRER", "Calha Superior 2 SPP", "FERRAGENS", False),
        ("CALHA INFERIOR {SPP} 1 CORRER", "Calha Inferior 1 SPP", "FERRAGENS", False),
        ("CALHA INFERIOR {SPP} 2 CORRER", "Calha Inferior 2 SPP", "FERRAGENS", False),
        ("PERFIL HORIZONTAL H {SPP}", "Perfil Horizontal H SPP", "FERRAGENS", False),
        ("PERFIL HORIZONTAL U {SPP}", "Perfil Horizontal U SPP", "FERRAGENS", False),
        ("PERFIL HORIZONTAL L {SPP}", "Perfil Horizontal L SPP", "FERRAGENS", False),
        ("ACESSORIO {SPP} 7 CORRER", "Acessorio 7 SPP", "FERRAGENS", False),
        ("ACESSORIO {SPP} 8 CORRER", "Acessorio 8 SPP", "FERRAGENS", False),
        # Grupo: Sistemas correr principais (nomes coincidentes)
        ("PUXADOR VERTICAL 1", "Puxador Vertical 1", "FERRAGENS", False),
        ("PUXADOR VERTICAL 2", "Puxador Vertical 2", "FERRAGENS", False),
        ("RODIZIO SUP 1", "Rodizio Sup 1", "FERRAGENS", False),
        ("RODIZIO SUP 2", "Rodizio Sup 2", "FERRAGENS", False),
        ("RODIZIO INF 1", "Rodizio Inf 1", "FERRAGENS", False),
        ("RODIZIO INF 2", "Rodizio Inf 2", "FERRAGENS", False),
        ("ACESSORIO 1 CORRER", "Acessorio 1", "FERRAGENS", False),
        ("ACESSORIO 2 CORRER", "Acessorio 2", "FERRAGENS", False),
        ("ACESSORIO 3 CORRER", "Acessorio 3", "FERRAGENS", False),
        ("ACESSORIO 4 CORRER", "Acessorio 4", "FERRAGENS", False),
        ("ACESSORIO 5 CORRER", "Acessorio 5", "FERRAGENS", False),
        ("ACESSORIO 6 CORRER", "Acessorio 6", "FERRAGENS", False),
        # Grupo: Painéis (família placas e seleção automática se vazio)
        ("PAINEL CORRER [0000]", "Painel Porta Correr 1", "PLACAS", True),
        ("PAINEL CORRER [2222]", "Painel Porta Correr 1", "PLACAS", True),
        ("PAINEL ESPELHO [2222]", "Painel Espelho Correr 1", "PLACAS", True),
    ]
    config = {}
    for def_peca, linha_sc, familia, auto_select in entries:
        base = {
            "db_table": TAB_SIS_CORRER_DB,
            "id_column": "id_sc",
            "use_id_filter": False,
            "sistemas_correr": linha_sc,
            "familia": familia,
            "preferred_material": linha_sc,
            "auto_select": auto_select,
            "tab_default_override": TAB_SIS_CORRER_DEFAULT,
        }
        # Para os painéis, a lista deve mostrar toda a família PLACAS,
        # mas a leitura de dados deve mapear especificamente para a linha indicada.
        if familia == "PLACAS":
            base["combo_filters"] = {"sistemas_correr": None, "familia": "PLACAS"}
            base["data_filters"] = {"sistemas_correr": linha_sc, "familia": "PLACAS"}
        config[_normalize_key(def_peca)] = base
    return config


SPECIAL_DEF_PECA_CONFIG = _build_special_configs()


def _get_special_config(def_peca_text):
    """Obtém (cópia) da configuração especial para o Def_Peca informado."""
    key = _normalize_key(def_peca_text)
    cfg = SPECIAL_DEF_PECA_CONFIG.get(key)
    return dict(cfg) if cfg else None


def _montar_filtros_sql(db_table, id_column, cfg, num_orc, ver_orc, valor_ids, context="combo"):
    """
    Constrói as cláusulas WHERE e a lista de parâmetros a partir do contexto atual
    e de (eventual) configuração especial.
    """
    cfg = cfg or {}
    context_filters = cfg.get(f"{context}_filters", {})
    where_parts = ["`num_orc`=%s", "`ver_orc`=%s"]
    params = [num_orc, ver_orc]

    use_id_filter = context_filters.get("use_id_filter")
    if use_id_filter is None:
        use_id_filter = cfg.get("use_id_filter", True)

    if use_id_filter and id_column:
        where_parts.append(f"`{id_column}`=%s")
        params.append(valor_ids)

    if db_table == TAB_SIS_CORRER_DB:
        sistemas_correr = context_filters.get("sistemas_correr")
        if sistemas_correr is None:
            sistemas_correr = cfg.get("sistemas_correr")
        if sistemas_correr:
            where_parts.append("UPPER(`sistemas_correr`)=%s")
            params.append(sistemas_correr.upper())
        familia = context_filters.get("familia")
        if familia is None:
            familia = cfg.get("familia")
        if familia:
            where_parts.append("UPPER(`familia`)=%s")
            params.append(familia.upper())

    return where_parts, params


def _preparar_lista_material(materials, preferred=None):
    """Remove duplicados preservando ordem e prioriza o material preferido, se existir."""
    vistos = set()
    lista = []
    for material in materials:
        if material is None:
            continue
        if material in vistos:
            continue
        lista.append(material)
        vistos.add(material)

    if preferred and preferred in lista:
        lista.remove(preferred)
        lista.insert(0, preferred)
    return lista

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
        item_def = table.item(row, IDX_DEF_PECA_COL)
        tab_default = item_tab.text().strip() if item_tab else ""
        def_peca_text = item_def.text().strip() if item_def else ""

        special_cfg = _get_special_config(def_peca_text) if def_peca_text else None

        if special_cfg:
            tab_override = special_cfg.get("tab_default_override")
            if tab_override and tab_default != tab_override:
                tab_default = tab_override
                if item_tab is None:
                    item_tab = QTableWidgetItem(tab_default)
                    table.setItem(row, 14, item_tab)
                else:
                    item_tab.setText(tab_default)

        db_table = db_mapping.get(tab_default)
        id_column = id_mapping.get(tab_default)

        if special_cfg:
            db_table = special_cfg.get("db_table", db_table)
            id_column = special_cfg.get("id_column", id_column)

        if not db_table:
            continue

        # Consulta à BD para obter materiais (usando obter_cursor)
        materials = []
        try:
            where_parts, params = _montar_filtros_sql(
                db_table, id_column, special_cfg, valor_num_orc, valor_ver_orc, valor_ids, context="combo"
            )
            where_clause = " AND ".join(where_parts) if where_parts else "1=1"

            with obter_cursor() as cursor:
                query = f"""
                    SELECT DISTINCT `material`
                    FROM `{db_table}`
                    WHERE {where_clause}
                    AND `material` IS NOT NULL AND `material` <> ''
                    ORDER BY `material`
                """
                cursor.execute(query, params)
                materials = [r[0] for r in cursor.fetchall()]

            if special_cfg:
                materials = _preparar_lista_material(materials, special_cfg.get("preferred_material"))

        except mysql.connector.Error as db_err:
            print(f"[ERRO DB] Linha {row}: Erro ao consultar materiais para '{db_table}': {db_err}")
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
        should_auto_update = False
        if special_cfg and special_cfg.get("auto_select") and not current_text:
            preferred = special_cfg.get("preferred_material", "")
            if preferred:
                current_text = preferred
                should_auto_update = True

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

        if should_auto_update and current_text:
            on_mat_default_changed(ui, row, current_text)

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
    tab_default = item_tab.text().strip() if item_tab else ""
    item_def = table.item(row, IDX_DEF_PECA_COL)
    def_peca_text = item_def.text().strip() if item_def else ""
    special_cfg = _get_special_config(def_peca_text) if def_peca_text else None

    if special_cfg:
        tab_override = special_cfg.get("tab_default_override")
        if tab_override and tab_default != tab_override:
            tab_default = tab_override
            if item_tab is None:
                item_tab = QTableWidgetItem(tab_default)
                table.setItem(row, 14, item_tab)
            else:
                item_tab.setText(tab_default)

    tabs_validos = {"Tab_Material_11", "Tab_Ferragens_11", "Tab_Acabamentos_12", "Tab_Sistemas_Correr_11"}
    if tab_default not in tabs_validos and not special_cfg:
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

    if special_cfg:
        db_table = special_cfg.get("db_table", db_table)
        id_column = special_cfg.get("id_column", id_column)

    if not db_table:
        print(f"[AVISO] Linha {row}: Sem mapeamento de tabela para Tab_Default '{tab_default}'.")
        return # Segurança adicional

    valor_num_orc = ui.lineEdit_num_orcamento.text().strip()
    valor_ver_orc = ui.lineEdit_versao_orcamento.text().strip()
    valor_ids = ui.lineEdit_item_orcamento.text().strip()

    resultado = None
    try:
        # Usa obter_cursor para a consulta
        with obter_cursor() as cursor:
            where_parts, params = _montar_filtros_sql(
                db_table, id_column, special_cfg, valor_num_orc, valor_ver_orc, valor_ids, context="data"
            )
            where_parts.append("`material`=%s")
            params.append(new_value)
            where_clause = " AND ".join(where_parts) if where_parts else "1=1"

            query = f"""
                SELECT descricao, ref_le, descricao_no_orcamento, ptab, pliq, desc1_plus, desc2_minus, und, desp,
                       corres_orla_0_4, corres_orla_1_0, tipo, familia, comp_mp, larg_mp, esp_mp
                FROM `{db_table}`
                WHERE {where_clause}
            """
            cursor.execute(query, params)
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
