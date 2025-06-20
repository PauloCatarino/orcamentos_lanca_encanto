# modulo_dados_definicoes.py
# Módulo para criação, salvamento e carregamento das tabelas
# dados_modulo_medidas e dados_def_pecas em MySQL.

# 1. Criação das tabelas na base dados 'dados_modulo_medidas' & 'dados_def_pecas' , que estão no separdor orçamento items
# 2. Gravar em base dados os dados da tabela 'tab_modulo_medidas' , que estão no separdor orçamento items
# 3. Gravar em base dados os dados da tabela 'tab_def_pecas' , que estão no separador orçamento items
# 4. Carregamento de dados do DB para a UI preencher os dados nas colunas da tabela tab_modulo_medidas
# 5. Carregamento de dados do DB para a UI preencher os dados nas colunas da tabela tab_def_pecas



import mysql.connector
import decimal
from db_connection import obter_cursor
from PyQt5.QtWidgets import QTableWidgetItem, QMessageBox, QPushButton
from PyQt5.QtCore import Qt
from decimal import Decimal, InvalidOperation # Importar Decimal
from tabela_def_pecas_items import on_mp_button_clicked # importa o handler do botão “Escolher” a partir do módulo correto

from utils import converter_texto_para_valor, formatar_valor_moeda, formatar_valor_percentual, set_item, safe_item_text
from modulo_componentes_associados import (IDX_COMP_ASS_1, IDX_COMP_ASS_2, IDX_COMP_ASS_3,COLOR_ASSOCIATED_BG, COLOR_PRIMARY_WITH_ASS_BG) 
from aplicar_formatacao_visual_blk import aplicar_ou_limpar_formatacao_blk # Importar


IDX_BLK = 12                 # Checkbox BLK - Bloqueia atualização automática
IDX_PLIQ = 21                # Preço liquido

# 1. Criação das tabelas na base dados 'dados_modulo_medidas' & 'dados_def_pecas' , se não existirem
def criar_tabelas_definicoes():
    """
    Cria as tabelas 'dados_modulo_medidas' e 'dados_def_pecas' no banco MySQL,
    garantindo que a estrutura de 'dados_def_pecas' corresponde à UI e permite
    armazenar fórmulas como texto.
    """
    #print("A tentar criar/verificar tabelas de definições...")
    try:
        with obter_cursor() as cursor:
            # Tabela para medidas do módulo (sem alterações)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS dados_modulo_medidas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ids VARCHAR(50) NULL,
                num_orc VARCHAR(20) NULL,
                ver_orc VARCHAR(10) NULL,
                H DECIMAL(10,2) NULL, L DECIMAL(10,2) NULL, P DECIMAL(10,2) NULL,
                H1 DECIMAL(10,2) NULL, L1 DECIMAL(10,2) NULL, P1 DECIMAL(10,2) NULL,
                H2 DECIMAL(10,2) NULL, L2 DECIMAL(10,2) NULL, P2 DECIMAL(10,2) NULL,
                H3 DECIMAL(10,2) NULL, L3 DECIMAL(10,2) NULL, P3 DECIMAL(10,2) NULL,
                H4 DECIMAL(10,2) NULL, L4 DECIMAL(10,2) NULL, P4 DECIMAL(10,2) NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""") # Boa prática definir engine e charset
            #print("Tabela 'dados_modulo_medidas' verificada/criada.")

            # Tabela para definição de peças - ESTRUTURA CORRIGIDA
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS dados_def_pecas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ids VARCHAR(50) NULL,
                num_orc VARCHAR(20) NULL,
                ver_orc VARCHAR(10) NULL,
                descricao_livre TEXT NULL,
                def_peca VARCHAR(255) NULL,
                descricao TEXT NULL,
                qt_mod VARCHAR(255) NULL,  
                qt_und DECIMAL(10,2) NULL,
                comp VARCHAR(255) NULL,            
                larg VARCHAR(255) NULL,            
                esp VARCHAR(255) NULL, 
                mps BOOLEAN NULL,
                mo BOOLEAN NULL,
                orla BOOLEAN NULL,
                blk BOOLEAN NULL,
                mat_default VARCHAR(100) NULL,
                tab_default VARCHAR(100) NULL,
                ref_le VARCHAR(100) NULL,
                descricao_no_orcamento TEXT NULL,
                ptab DECIMAL(10,2) NULL,
                pliq DECIMAL(10,2) NULL,
                des1plus DECIMAL(5,2) NULL,
                des1minus DECIMAL(5,2) NULL,
                und VARCHAR(20) NULL,
                desp DECIMAL(5,2) NULL,
                corres_orla_0_4 VARCHAR(50) NULL,
                corres_orla_1_0 VARCHAR(50) NULL,
                tipo VARCHAR(50) NULL,
                familia VARCHAR(50) NULL,
                comp_mp DECIMAL(10,2) NULL,
                larg_mp DECIMAL(10,2) NULL,
                esp_mp DECIMAL(10,2) NULL,
                mp BOOLEAN NULL, -- Coluna 33 na BD (BOOLEAN)
                comp_ass_1 VARCHAR(255) NULL, -- Coluna 34 na BD (VARCHAR)
                comp_ass_2 VARCHAR(255) NULL, -- Coluna 35 na BD (VARCHAR)
                comp_ass_3 VARCHAR(255) NULL, -- Coluna 36 na BD (VARCHAR)
                orla_c1 DECIMAL(10,2) NULL,
                orla_c2 DECIMAL(10,2) NULL,
                orla_l1 DECIMAL(10,2) NULL,
                orla_l2 DECIMAL(10,2) NULL,
                ml_c1 DECIMAL(10,2) NULL,
                ml_c2 DECIMAL(10,2) NULL,
                ml_l1 DECIMAL(10,2) NULL,
                ml_l2 DECIMAL(10,2) NULL,
                custo_ml_c1 DECIMAL(12,2) NULL,
                custo_ml_c2 DECIMAL(12,2) NULL,
                custo_ml_l1 DECIMAL(12,2) NULL,
                custo_ml_l2 DECIMAL(12,2) NULL,
                qt_total DECIMAL(12,2) NULL,
                comp_res DECIMAL(10,2) NULL,
                larg_res DECIMAL(10,2) NULL,
                esp_res DECIMAL(10,2) NULL,
                gravar_modulo BOOLEAN NULL,
                area_m2_und DECIMAL(10,4) NULL,
                spp_ml_und DECIMAL(10,4) NULL,
                cp09_custo_mp DECIMAL(12,2) NULL,
                custo_mp_und DECIMAL(12,2) NULL,
                custo_mp_total DECIMAL(12,2) NULL,
                acb_sup BOOLEAN NULL,
                acb_inf BOOLEAN NULL,
                acb_sup_und DECIMAL(12,2) NULL,
                acb_inf_und DECIMAL(12,2) NULL,
                cp01_sec DECIMAL(12,2) NULL,
                cp01_sec_und DECIMAL(12,2) NULL,
                cp02_orl DECIMAL(12,2) NULL,
                cp02_orl_und DECIMAL(12,2) NULL,
                cp03_cnc DECIMAL(12,2) NULL,
                cp03_cnc_und DECIMAL(12,2) NULL,
                cp04_abd DECIMAL(12,2) NULL,
                cp04_abd_und DECIMAL(12,2) NULL,
                cp05_prensa DECIMAL(12,2) NULL,
                cp05_prensa_und DECIMAL(12,2) NULL,
                cp06_esquad DECIMAL(12,2) NULL,
                cp06_esquad_und DECIMAL(12,2) NULL,
                cp07_embalagem DECIMAL(12,2) NULL,
                cp07_embalagem_und DECIMAL(12,2) NULL,
                cp08_mao_de_obra DECIMAL(12,2) NULL,
                cp08_mao_de_obra_und DECIMAL(12,2) NULL,
                soma_custo_und DECIMAL(12,2) NULL,
                soma_custo_total DECIMAL(12,2) NULL,
                soma_custo_acb DECIMAL(12,2) NULL,
                INDEX idx_pecas_chave (ids, num_orc, ver_orc) -- Adicionar índice para otimizar buscas/deletes
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""")
            #print("Tabela 'dados_def_pecas' verificada/criada com estrutura atualizada.")
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao criar/verificar tabelas: {err}")
        QMessageBox.critical(None, "Erro Crítico de Base de Dados", f"Não foi possível criar/verificar as tabelas necessárias: {err}")
    except Exception as e:
        print(f"Erro inesperado ao criar/verificar tabelas: {e}")
        QMessageBox.critical(None, "Erro Crítico", f"Erro inesperado durante a inicialização da base de dados: {e}")

# 2. Gravar em base dados os dados da tabela 'tab_modulo_medidas' , que estão no separador orçamento items
def salvar_dados_modulo_medidas(ui):
    tbl = ui.tab_modulo_medidas
    if tbl.rowCount() == 0:
        print("Tabela de medidas do módulo vazia, nada a guardar.")
        return

    # 1) Lê os nomes das colunas diretamente dos headers (em minúsculas, para casar com os nomes no banco)
    cols = []
    for i in range(tbl.columnCount()):
        header_item = tbl.horizontalHeaderItem(i)
        if header_item:
             cols.append(header_item.text().lower())
        else:
             # Se um cabeçalho não existir, interrompe ou trata como erro
             print(f"[Erro] salvar_dados_modulo_medidas: Cabeçalho da coluna {i} não encontrado.")
             QMessageBox.warning(None,"Erro Interface", f"Cabeçalho da coluna {i} não encontrado na tabela de medidas.")
             return # Aborta o salvamento

    # 2) Coleta os valores da primeira linha, convertendo '' → None e números para Decimal
    vals_map = {} # Usar um dicionário para facilitar
    if tbl.rowCount() > 0:
        for i in range(tbl.columnCount()):
            col_name = cols[i]
            item = tbl.item(0, i)
            texto = item.text().strip() if item and item.text() is not None else ""  # Pega texto, trata None
            if texto == "":
                vals_map[col_name] = None
            else:
                if col_name in ["ids", "num_orc", "ver_orc"]:
                    # Estes campos devem ser tratados como texto simples para
                    # preservar eventuais zeros à esquerda (ex: versao "01").
                    vals_map[col_name] = texto
                else:
                    try:
                        # Substituir vírgula por ponto antes de converter
                        valor_decimal = Decimal(texto.replace(',', '.'))
                        vals_map[col_name] = valor_decimal
                    except InvalidOperation:
                        print(
                            f"[Aviso] salvar_dados_modulo_medidas: Valor '{texto}' na coluna '{col_name}' não é um número válido. Guardando como NULL."
                        )
                        vals_map[col_name] = None
    else:
        print("[Info] salvar_dados_modulo_medidas: Tabela de medidas vazia.")
        return

    # 3) Extrai as chaves
    key_ids = vals_map.get('ids')
    key_num = vals_map.get('num_orc')
    key_ver = vals_map.get('ver_orc')

     # === INÍCIO MODIFICAÇÃO: Formatar ver_orc para guardar/consultar na BD ===
    key_ver_final = str(key_ver).strip() if key_ver is not None else "00"
    # === FIM MODIFICAÇÃO ===

    # Validar se as chaves existem (já são string ou None)
    if key_ids is None or key_num is None or key_ver is None:
        QMessageBox.warning(None, "Erro Dados", "Faltam identificadores (Item, Orçamento, Versão) na tabela de medidas.")
        return

    # Validar comprimento de key_ver (VARCHAR(10) na BD)
    if len(str(key_ver)) > 10: # Usar str(key_ver) para lidar com None
        QMessageBox.warning(None, "Erro de Validação", f"O valor para 'Versão Orçamento' ('{key_ver}') excede 10 caracteres.")
        return # Parar o processo de guardar

    # Validar comprimento de ids (VARCHAR(50) na BD)
    if len(str(key_ids)) > 50:
         QMessageBox.warning(None, "Erro de Validação", f"O valor para 'Item Orçamento' ('{key_ids}') excede o limite de 50 caracteres.")
         return

    # Validar comprimento de num_orc (VARCHAR(20) na BD)
    if len(str(key_num)) > 20:
         QMessageBox.warning(None, "Erro de Validação", f"O valor para 'Número Orçamento' ('{key_num}') excede o limite de 20 caracteres.")
         return


    # --- Diálogo de Confirmação (Opcional, se quisermos perguntar antes de substituir medidas) ---
    # Para medidas, geralmente há apenas uma linha por Item/Orc/Ver, então a substituição é esperada.
    # Podemos omitir o diálogo de confirmação e apenas apagar/inserir.
    print(f"A guardar dados de medidas para {key_ids}/{key_num}/{key_ver}.")


    try:
        with obter_cursor() as cursor:
            # Delete existing records for this key combination
            cursor.execute(
                "DELETE FROM dados_modulo_medidas WHERE ids=%s AND num_orc=%s AND ver_orc=%s",
                (str(key_ids), str(key_num), str(key_ver)) # Usar str() por segurança
            )
            #print(f"Registos antigos de medidas para {key_ids}/{key_num}/{key_ver} eliminados ({cursor.rowcount} linhas).") # Debug

            # Prepare the list of values for insertion IN THE SAME ORDER AS COLS
            # O dicionário vals_map já foi criado na ordem correta dos cabeçalhos (cols)
            vals_list = [vals_map.get(col) for col in cols]

            # Ensure the keys in vals_list are strings as expected by the DB schema VARCHAR fields
            # Ensure Decimal values remain Decimal objects
            # Ensure None remains None
            final_vals_list = []
            for i, col_name in enumerate(cols):
                 val = vals_list[i]
                 if val is None:
                      final_vals_list.append(None)
                 elif isinstance(val, Decimal):
                      final_vals_list.append(val) # Keep Decimal
                 else:
                      # Convert other types (like int, float, bool) to string for VARCHAR columns
                      # Assuming all non-Decimal columns in this table are VARCHAR/TEXT (ids, num_orc, ver_orc)
                      final_vals_list.append(str(val))


            placeholders = ', '.join(['%s'] * len(cols))
            sql = f"INSERT INTO dados_modulo_medidas ({', '.join(f'`{c}`' for c in cols)}) VALUES ({placeholders})" # Usar backticks para os nomes das colunas
            cursor.execute(sql, tuple(final_vals_list))
            print("Dados de medidas do módulo guardados com sucesso.")
            # QMessageBox.information(None, "Guardar Dados", "Dados de medidas do módulo guardados com sucesso.") # Não mostrar msg para não incomodar

    except mysql.connector.Error as err:
        QMessageBox.critical(None, "Erro Base de Dados", f"Erro MySQL ao guardar medidas do módulo: {err}")
        print(f"Erro MySQL (medidas): {err}")
    except Exception as e:
        QMessageBox.critical(None, "Erro Inesperado", f"Erro inesperado ao guardar medidas do módulo: {e}")
        import traceback
        traceback.print_exc()

# 3. Gravar em base dados os dados da tabela 'tab_def_pecas' , que estão no separador orçamento items
def salvar_dados_def_pecas(ui):
    tbl = ui.tab_def_pecas
    rows = tbl.rowCount()
    if rows == 0:
        print("Nenhuma linha na tabela de peças para guardar.")
        #QMessageBox.information(None, "Guardar Dados", "A tabela de tab_def_peças está vazia. Não há dados para guardar.")
        return

    # --- Obter Valores Chave e Validar Comprimentos ---
    key_ids = ui.lineEdit_item_orcamento.text().strip()
    key_num = ui.lineEdit_num_orcamento.text().strip()
    key_ver = ui.lineEdit_versao_orcamento.text().strip()# Obter valor original do line edit

    # === INÍCIO MODIFICAÇÃO: Formatar ver_orc para guardar/consultar na BD ===
    key_ver_final = str(key_ver).strip() if key_ver is not None else "00"
    # === FIM MODIFICAÇÃO ===

    # --- DEBUG ---
    print(f"[DEBUG salvar_dados_def_pecas] Tentando guardar com chaves:")
    print(f"  key_ids: '{key_ids}' (Tipo: {type(key_ids)}, Vazio: {not key_ids})")
    print(f"  key_num: '{key_num}' (Tipo: {type(key_num)}, Vazio: {not key_num})")
    print(f"  key_ver: '{key_ver}' (Tipo: {type(key_ver)}, Vazio: {not key_ver})")
    print(f"  key_ver_final (formatado): '{key_ver_final}'")
    # --- FIM DEBUG ---

    # Adicionar validação para chaves vazias
    if not key_ids or not key_num or not key_ver_final: # Usar key_ver_final para validar se a versão formatada não é vazia
         QMessageBox.critical(None, "Erro de Dados", "Os campos Item, Nº Orçamento e Versão não podem estar vazios para guardar.")
         return


    # Validar comprimento de ver_orc (VARCHAR(10) na BD)
    if len(key_ver_final) > 10:
        QMessageBox.warning(None, "Erro de Validação", f"O valor para 'Versão Orçamento' ('{key_ver_final}') excede 10 caracteres.")
        return # Parar o processo de guardar

    # Validar comprimento de ids (VARCHAR(50) na BD)
    if len(key_ids) > 50:
         QMessageBox.warning(None, "Erro de Validação", f"O valor para 'Item Orçamento' ('{key_ids}') excede o limite de 50 caracteres.")
         return

    # Validar comprimento de num_orc (VARCHAR(20) na BD)
    if len(key_num) > 20:
         QMessageBox.warning(None, "Erro de Validação", f"O valor para 'Número Orçamento' ('{key_num}') excede o limite de 20 caracteres.")
         return

    # --- Diálogo de Confirmação ---
    contagem_registos = 0
    try:
        with obter_cursor() as cursor:
            # Verificar se já existem registos para esta combinação de chaves
            check_sql = "SELECT COUNT(*) FROM dados_def_pecas WHERE ids=%s AND num_orc=%s AND ver_orc=%s"
            cursor.execute(check_sql, (key_ids, key_num, key_ver_final)) # Usar key_ver_final
            resultado_contagem = cursor.fetchone()
            if resultado_contagem:
                contagem_registos = resultado_contagem[0]

    except Exception as e:
        QMessageBox.critical(None, "Erro de Base de Dados", f"Erro ao verificar dados existentes: {e}")
        print(f"Erro ao verificar dados: {e}")
        return # Parar se não conseguirmos verificar

    if contagem_registos > 0:
        resposta = QMessageBox.question(
            None, # Widget pai
            "Confirmar Substituição",
            f"Já existem {contagem_registos} registos para:\n"
            f"  Item: {key_ids}\n"
            f"  Orçamento: {key_num}\n"
            f"  Versão: {key_ver_final}\n\n" # Mostrar key_ver_final no diálogo
            "Deseja substituir os dados existentes pelos dados atuais da tabela?",
            QMessageBox.Yes | QMessageBox.No, # Botões
            QMessageBox.Yes # Botão padrão forçado a ficar ativo o botão 'Yes'
        )

        if resposta == QMessageBox.No:
            print("Operação de guardar cancelada pelo utilizador.")
            QMessageBox.information(None, "Guardar Dados", "Operação cancelada.")
            return # Parar se o utilizador selecionar Não

    # --- Prosseguir com Eliminação e Inserção ---
    print(f"A guardar {rows} linhas para {key_ids}/{key_num}/{key_ver_final}. Registos existentes: {contagem_registos} (serão substituídos se existirem).")

    # Lista colunas na tabela em Base Dados 82 colunas da BD (deve corresponder a CREATE TABLE)
    cols_bd = [
        'ids','num_orc','ver_orc','descricao_livre','def_peca','descricao',
        'qt_mod','qt_und','comp','larg','esp','mps','mo','orla','blk',
        'mat_default','tab_default','ref_le','descricao_no_orcamento','ptab','pliq',
        'des1plus','des1minus','und','desp','corres_orla_0_4','corres_orla_1_0',
        'tipo','familia','comp_mp','larg_mp','esp_mp','mp','comp_ass_1',
        'comp_ass_2','comp_ass_3','orla_c1','orla_c2','orla_l1','orla_l2',
        'ml_c1','ml_c2','ml_l1','ml_l2','custo_ml_c1','custo_ml_c2','custo_ml_l1',
        'custo_ml_l2','qt_total','comp_res','larg_res','esp_res','gravar_modulo',
        'area_m2_und','spp_ml_und','cp09_custo_mp','custo_mp_und','custo_mp_total',
        'acb_sup','acb_inf', 'acb_sup_und', 'acb_inf_und',
        'cp01_sec','cp01_sec_und','cp02_orl','cp02_orl_und',
        'cp03_cnc','cp03_cnc_und','cp04_abd','cp04_abd_und','cp05_prensa',
        'cp05_prensa_und','cp06_esquad','cp06_esquad_und','cp07_embalagem',
        'cp07_embalagem_und','cp08_mao_de_obra','cp08_mao_de_obra_und',
        'soma_custo_und','soma_custo_total','soma_custo_acb'
    ]
    #print(f" [DEBUG] Número de colunas na BD: {len(cols_bd)}") # Debug

    # Colunas que são DECIMAL, FLOAT, etc. (numéricas)
    # IMPORTANTE: Certifique-se que esta lista está completa e correta, de acordo com o schema da BD.
    decimal_cols = {
        'qt_mod','qt_und','comp','larg','esp','ptab','pliq','des1plus','des1minus','desp',
        'comp_mp','larg_mp','esp_mp','comp_ass_1','comp_ass_2','comp_ass_3',
        'orla_c1','orla_c2','orla_l1','orla_l2','ml_c1','ml_c2','ml_l1','ml_l2',
        'custo_ml_c1','custo_ml_c2','custo_ml_l1','custo_ml_l2','qt_total',
        'comp_res','larg_res','esp_res','area_m2_und','spp_ml_und','cp09_custo_mp',
        'custo_mp_und','custo_mp_total', 'acb_sup_und', 'acb_inf_und', # <- Adicionadas
        'cp01_sec','cp01_sec_und','cp02_orl','cp02_orl_und',
        'cp03_cnc','cp03_cnc_und','cp04_abd','cp04_abd_und',
        'cp05_prensa','cp05_prensa_und','cp06_esquad','cp06_esquad_und',
        'cp07_embalagem','cp07_embalagem_und','cp08_mao_de_obra','cp08_mao_de_obra_und',
        'soma_custo_und','soma_custo_total','soma_custo_acb'
    }

    # Colunas BOOLEAN (ou TINYINT(1) na BD)
    bool_cols = {'mps','mo','orla','blk','mp','gravar_modulo','acb_sup','acb_inf'}
    
    # Mapeamento NOME_COLUNA_BD -> ÍNDICE_COLUNA_UI (Conforme lista 0-81 fornecida)
    # IMPORTANTE: Verificar cuidadosamente se estes índices correspondem à sua UI
    map_bd_para_ui = {
        'ids': 15, 'num_orc': 16, 'ver_orc': 17, 'descricao_livre': 1, 'def_peca': 2,
        'descricao': 3, 'qt_mod': 4, 'qt_und': 5, 'comp': 6, 'larg': 7, 'esp': 8,
        'mps': 9, 'mo': 10, 'orla': 11, 'blk': 12, 'mat_default': 13, 'tab_default': 14,
        'ref_le': 18, 'descricao_no_orcamento': 19, 'ptab': 20, 'pliq': 21,
        'des1plus': 22, 'des1minus': 23, 'und': 24, 'desp': 25, 'corres_orla_0_4': 26,
        'corres_orla_1_0': 27, 'tipo': 28, 'familia': 29, 'comp_mp': 30, 'larg_mp': 31,
        'esp_mp': 32, 'mp': 33, 'comp_ass_1': 34, 'comp_ass_2': 35, 'comp_ass_3': 36,
        'orla_c1': 37, 'orla_c2': 38, 'orla_l1': 39, 'orla_l2': 40, 'ml_c1': 41,
        'ml_c2': 42, 'ml_l1': 43, 'ml_l2': 44, 'custo_ml_c1': 45, 'custo_ml_c2': 46,
        'custo_ml_l1': 47, 'custo_ml_l2': 48, 'qt_total': 49, 'comp_res': 50,
        'larg_res': 51, 'esp_res': 52, 'gravar_modulo': 53, 'area_m2_und': 54,
        'spp_ml_und': 55, 'cp09_custo_mp': 56, 'custo_mp_und': 57, 'custo_mp_total': 58,
        'acb_sup': 59, 'acb_inf': 60, 'acb_sup_und': 61, 'acb_inf_und': 62,
        'cp01_sec': 63, 'cp01_sec_und': 64, 'cp02_orl': 65, 'cp02_orl_und': 66,
        'cp03_cnc': 67, 'cp03_cnc_und': 68, 'cp04_abd': 69, 'cp04_abd_und': 70,
        'cp05_prensa': 71, 'cp05_prensa_und': 72, 'cp06_esquad': 73, 'cp06_esquad_und': 74,
        'cp07_embalagem': 75, 'cp07_embalagem_und': 76, 'cp08_mao_de_obra': 77,
        'cp08_mao_de_obra_und': 78, 'soma_custo_und': 79, 'soma_custo_total': 80,
        'soma_custo_acb': 81
    }

    # Colunas que AGORA são texto (fórmulas) - ANTES eram tratadas como DECIMAL
    formula_cols_bd = {'qt_mod', 'qt_und', 'comp', 'larg', 'esp'}
     # Índices UI das colunas booleanas (checkboxes)
    bool_indices_ui = {9, 10, 11, 12, 33, 53, 59, 60} # mps, mo, orla, blk, mp, gravar_modulo, acb_sup, acb_inf
    
    # Verifica se todos os nomes de colunas da BD estão no mapeamento
    if len(map_bd_para_ui) != len(cols_bd) - 3: # (-3 para ids, num_orc, ver_orc que são preenchidos à parte)
         print(f"[AVISO] Mapeamento BD->UI incompleto? BD:{len(cols_bd)}, <=> Map:{len(map_bd_para_ui)}")
         # Poderia levantar um erro aqui se for crítico

    moeda_indices_ui = {20, 21, 45, 46, 47, 48, 57, 58, 61, 62, 64, 66, 68, 70, 72, 74, 76, 78, 79, 80, 81} # ptab, pliq, custo_ml_c1, custo_ml_c2, custo_ml_l1, custo_ml_l2, custo_mp_und, custo_mp_total, acb_sup_und, acb_inf_und, cp01_sec_und, cp02_orl_und, cp03_cnc_und, cp04_abd_und, cp05_prensa_und, cp06_esquad_und, cp07_embalagem_und, cp08_mao_de_obra_und
    percent_indices_ui = {22, 23, 25} # des1plus, des1minus, desp
    colunas_texto = {'descricao_livre','def_peca','descricao','mat_default','tab_default','ref_le','descricao_no_orcamento','und','corres_orla_0_4','corres_orla_1_0','tipo','familia','comp_ass_1','comp_ass_2','comp_ass_3','qt_mod','comp','larg','esp'}

    try:
        with obter_cursor() as cursor:
            cursor.execute("DELETE FROM dados_def_pecas WHERE ids=%s AND num_orc=%s AND ver_orc=%s", (key_ids, key_num, key_ver_final))

            insert_sql = f"INSERT INTO dados_def_pecas ({', '.join(cols_bd)}) VALUES ({', '.join(['%s'] * len(cols_bd))})"
            dados_para_inserir = []

            for r in range(rows):
                valores_linha_bd = []
                for nome_coluna_bd in cols_bd:
                    idx_ui = map_bd_para_ui.get(nome_coluna_bd, -1)
                    if idx_ui == -1:
                        valores_linha_bd.append(None)
                        continue

                    item = tbl.item(r, idx_ui)
                    texto = item.text().strip() if item and item.text() is not None else None

                    if nome_coluna_bd in ['ids', 'num_orc', 'ver_orc']:
                        valores_linha_bd.append({'ids': key_ids, 'num_orc': key_num, 'ver_orc': key_ver_final}[nome_coluna_bd])
                    elif idx_ui in bool_indices_ui:
                        if idx_ui == 33:
                            estado_bool = item.data(Qt.UserRole) if item else False
                            valores_linha_bd.append(1 if estado_bool else 0)
                        else:
                            estado = item.checkState() if item else Qt.Unchecked
                            valores_linha_bd.append(1 if estado == Qt.Checked else 0)
                    elif nome_coluna_bd in colunas_texto:
                        valores_linha_bd.append(texto if texto else None)
                    else:
                        if texto is None or texto == "":
                            valores_linha_bd.append(None)
                        else:
                            try:
                                if idx_ui in percent_indices_ui:
                                    valor_float = converter_texto_para_valor(texto, 'percentual')
                                elif idx_ui in moeda_indices_ui:
                                    valor_float = converter_texto_para_valor(texto, 'moeda')
                                else:
                                    valor_float = float(texto.replace(",", "."))
                                valores_linha_bd.append(Decimal(str(valor_float)))
                            except (InvalidOperation, ValueError, TypeError):
                                print(f"[Aviso] L{r+1} C'{nome_coluna_bd}': Valor '{texto}' inválido. Guardando NULL.")
                                valores_linha_bd.append(None)

                if len(valores_linha_bd) == len(cols_bd):
                    dados_para_inserir.append(tuple(valores_linha_bd))

            if dados_para_inserir:
                cursor.executemany(insert_sql, dados_para_inserir)
                print(f"{len(dados_para_inserir)} linha(s) guardada(s) com sucesso.")
                QMessageBox.information(None, "Guardar Dados", f"{len(dados_para_inserir)} linha(s) guardada(s) com sucesso.")
            else:
                print("Nenhum dado válido para inserir.")

    except mysql.connector.Error as err:
        QMessageBox.critical(None, "Erro Base de Dados", f"Erro MySQL ao guardar dados: {err}")
        print(f"Erro MySQL ao guardar dados: {err}")
    except Exception as e:
        QMessageBox.critical(None, "Erro Inesperado", f"Erro inesperado ao guardar dados: {e}")
        import traceback
        traceback.print_exc()

# 4. Carregamento de dados do DB para a UI preencher os dados nas colunas da tabela tab_modulo_medidas
def carregar_dados_modulo_medidas(ui):
    """
    Carrega os dados da tabela 'dados_modulo_medidas' do banco de dados
    para a QTableWidget 'tab_modulo_medidas' na interface do usuário.

    Busca os dados filtrando por 'ids', 'num_orc' e 'ver_orc' obtidos da UI.
    Especifica a ordem das colunas na consulta SELECT para corresponder
    à ordem esperada pela QTableWidget.
    Converte valores None (SQL NULL) para strings vazias ("") na tabela.
    """
    tbl = ui.tab_modulo_medidas
    key_ids = ui.lineEdit_item_orcamento.text().strip()
    key_num = ui.lineEdit_num_orcamento.text().strip()
    key_ver = ui.lineEdit_versao_orcamento.text().strip()

     # === INÍCIO MODIFICAÇÃO: Formatar ver_orc para consultar na BD ===
    # O valor de key_ver já deve vir formatado como "00", "01", etc. do lineEdit.
    key_ver_final = str(key_ver).strip() if key_ver is not None else "00"
    # === FIM MODIFICAÇÃO ===

    # --- Definição da Ordem Correta das Colunas ---
    # Ordem das colunas conforme a tab_modulo_medidas na interface gráfica
    # Garante que lê os cabeçalhos da tabela UI para saber a ordem e o número de colunas
    colunas_ui_headers = []
    for i in range(tbl.columnCount()):
        header_item = tbl.horizontalHeaderItem(i)
        if header_item:
             colunas_ui_headers.append(header_item.text().strip().lower())
        else:
             print(f"[ERRO] carregar_dados_modulo_medidas: Cabeçalho da coluna {i} não encontrado. Abortando carregamento.")
             QMessageBox.warning(None, "Erro Interface", f"Cabeçalho da coluna {i} não encontrado na tabela de medidas.")
             # Limpa a tabela e insere uma linha vazia para evitar crash
             tbl.setRowCount(1)
             for j in range(tbl.columnCount()):
                 item = QTableWidgetItem("")
                 tbl.setItem(0, j, item)
             return # Aborta o carregamento

    # Cria a string para o SELECT query, usando backticks para nomes de colunas/tabelas, na ordem dos headers da UI
    colunas_sql_select = ", ".join(f"`{c}`" for c in colunas_ui_headers) # Usar backticks
    sql = f"""
        SELECT {colunas_sql_select}
        FROM dados_modulo_medidas
        WHERE ids=%s AND num_orc=%s AND ver_orc=%s
        ORDER BY id
    """

    try:
        with obter_cursor() as cursor:
            # A query agora seleciona as colunas na ordem definida por colunas_ui_headers
            cursor.execute(sql, (key_ids, key_num, key_ver_final))
            row_bd = cursor.fetchone() # Lê apenas uma linha (a tabela de medidas só tem uma por orçamento/item)

        tbl.setRowCount(0) # Limpa a tabela na UI antes de carregar
        if row_bd:
            tbl.insertRow(0) # Insere uma nova linha para os dados carregados
            # print(f"[DEBUG] Dados encontrados na BD: {row_bd}") # Debug dados retornados pela query

            # Itera pelos valores retornados pela BD (que já estão na ordem de colunas_ui_headers)
            for col_index, val_bd in enumerate(row_bd):
                # Pega o nome da coluna atual (segundo a ordem do SELECT, que é a da UI)
                col_name_ui = colunas_ui_headers[col_index]
                # print(f"[DEBUG] Processando coluna UI {col_index} ('{col_name_ui}'): Valor BD={val_bd!r} (Tipo: {type(val_bd)})") # Debug valor individual

                texto_celula = ""
                # Verifica o tipo de dados para formatação
                if isinstance(val_bd, decimal.Decimal):
                    # Formata valores Decimais: sem casas decimais se for um inteiro, ou com 2 casas
                    if val_bd == val_bd.to_integral_value():
                         # Converte para int para remover .0, depois para string
                        texto_celula = str(int(val_bd))
                    else:
                        # Mantém 2 casas decimais se tiver parte fracionária, substitui '.' por ',' para exibição na UI
                        texto_celula = f"{val_bd:.2f}".replace('.', ',')
                elif val_bd is not None:
                    # Para outros tipos (strings, ints), apenas converte para string (se não for None)
                    texto_celula = str(val_bd)
                # else: texto_celula permanece "" (para val_bd is None)

                # print(f"[DEBUG] Formatado para UI: '{texto_celula}'") # Debug texto que vai para a célula

                # Usa set_item para garantir que o item existe e definir o texto formatado
                set_item(tbl, 0, col_index, texto_celula)
                # Obtém o item após set_item para definir flags
                item = tbl.item(0, col_index)

                # Define as flags de editabilidade:
                # As colunas 'ids', 'num_orc', 'ver_orc' devem ser não editáveis.
                if item: # Garante que o item existe
                     if col_name_ui in ['ids', 'num_orc', 'ver_orc']:
                          item.setFlags(item.flags() & ~Qt.ItemIsEditable) # Remove a flag de editável
                     else:
                          # As colunas das medidas (H, L, P, H1..P4) devem ser editáveis.
                          item.setFlags(item.flags() | Qt.ItemIsEditable) # Garante que a flag de editável está ativa


            #print(f"Dados de medidas carregados com sucesso para {key_ids}/{key_num}/{key_ver_final}.")
        else:
            # Se nenhum dado foi encontrado para as chaves, inicializa a tabela com uma linha vazia
            print(f"Nenhum dado encontrado para medidas: {key_ids}/{key_num}/{key_ver_final}. Inicializando tabela com linha vazia.")
            tbl.setRowCount(1) # Garante que existe uma linha

            # Preenche a linha vazia, definindo editabilidade correta
            for i in range(tbl.columnCount()):
                item = QTableWidgetItem("")
                # Identifica o nome da coluna pelo cabeçalho da UI para definir flags
                header_item = tbl.horizontalHeaderItem(i)
                header_name = header_item.text().strip().lower() if header_item else ""

                if header_name in ['ids', 'num_orc', 'ver_orc']:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                else:
                    item.setFlags(item.flags() | Qt.ItemIsEditable) # Garante que H,L,P etc são editáveis
                tbl.setItem(0, i, item)

    except mysql.connector.Error as err:
        # Captura erros específicos do MySQL
        print(f"Erro MySQL ao carregar medidas: {err}")
        QMessageBox.critical(None, "Erro Base de Dados", f"Erro MySQL ao carregar medidas:\n{err}")
        # Em caso de erro fatal, limpa a tabela e insere uma linha vazia para evitar crash
        tbl.setRowCount(1)
        for i in range(tbl.columnCount()):
             item = QTableWidgetItem("")
             header_item = tbl.horizontalHeaderItem(i)
             header_name = header_item.text().strip().lower() if header_item else ""
             if header_name in ['ids', 'num_orc', 'ver_orc']:
                 item.setFlags(item.flags() & ~Qt.ItemIsEditable)
             else:
                 item.setFlags(item.flags() | Qt.ItemIsEditable)
             tbl.setItem(0, i, item)

    except Exception as e:
        # Captura outros erros inesperados
        print(f"Erro inesperado ao carregar medidas: {e}")
        QMessageBox.critical(None, "Erro Inesperado", f"Erro inesperado ao carregar medidas:\n{e}")
        import traceback
        traceback.print_exc() # Imprime a stack trace para ajudar na depuração
         # Em caso de erro fatal, limpa a tabela e insere uma linha vazia
        tbl.setRowCount(1)
        for i in range(tbl.columnCount()):
             item = QTableWidgetItem("")
             header_item = tbl.horizontalHeaderItem(i)
             header_name = header_item.text().strip().lower() if header_item else ""
             if header_name in ['ids', 'num_orc', 'ver_orc']:
                 item.setFlags(item.flags() & ~Qt.ItemIsEditable)
             else:
                 item.setFlags(item.flags() | Qt.ItemIsEditable)
             tbl.setItem(0, i, item)

    finally:
        # O orcamentar_items.click() (ou a sequência de chamadas no orcamento_items.py)
        # deve garantir que a função `actualizar_ids_num_orc_ver_orc_tab_modulo_medidas`
        # é chamada após o carregamento, para reforçar a definição dos IDs/NumOrc/VerOrc
        # e a sua não-editabilidade.
        print("[DEBUG] Finalizada execução de carregar_dados_modulo_medidas.")    #pretendo eliminar esta linha

# ... (as funções carregar_dados_def_pecas e actualizar_ids_num_orc_ver_orc_tab_modulo_medidas) ...

# Mantenha as funções salvar_dados_modulo_medidas e salvar_dados_def_pecas
# como estavam, elas já parecem estar a gravar corretamente, incluindo o tratamento de Decimal.


# 5. Carregamento de dados do DB para a UI preencher os dados nas colunas da tabela tab_def_pecas
def carregar_dados_def_pecas(ui):
    """
    Carrega dados da tabela 'dados_def_pecas' do MySQL para a QTableWidget 'tab_def_pecas',
    aplicando formatação, configurando checkboxes, botões e cores de fundo para
    componentes principais e associados.
    """
    print("\n--- Iniciando carregamento de dados para tab_def_pecas ---")
    tbl = ui.tab_def_pecas
    key_ids = ui.lineEdit_item_orcamento.text().strip()
    key_num = ui.lineEdit_num_orcamento.text().strip()
    key_ver = ui.lineEdit_versao_orcamento.text().strip()

    # === INÍCIO MODIFICAÇÃO: Formatar ver_orc para consultar na BD ===
    # O valor de key_ver já deve vir formatado como "00", "01", etc. do lineEdit.
    key_ver_final = str(key_ver).strip() if key_ver is not None else "00"
    # === FIM MODIFICAÇÃO ===

    # 1) Defina a lista de colunas do banco NA MESMA ORDEM da QTableWidget UI.
    # Esta lista DEVE ser a ordem exata das colunas na sua tabela UI (0-based).
    # Se a ordem na BD for diferente, o SELECT deve reordenar.
    # Assumimos que a ordem na BD `dados_def_pecas` está igual à ordem da UI 0-81.
    # A coluna 'id' (PK auto_increment) está na BD mas geralmente não é mostrada na UI
    # ou é a coluna 0. A descrição original do mapeamento BD->UI começa no índice 0 da UI
    # com 'id', o que sugere que a primeira coluna da UI É o 'id' da BD.
    # A lista `colunas_ui_ordenadas` deve refletir as colunas da BD na ORDEM da UI.
    # Baseado na lista de 82 colunas fornecida na descrição de `salvar_dados_def_pecas`,

        # 1) Defina a lista de colunas do banco NA MESMA ORDEM de tab_def_pecas.
    colunas_ui_ordenadas = [
        'id',                      # 0 → id (PK do registro)
        'descricao_livre',         # 1 → Descricao_Livre
        'def_peca',                # 2 → Def_Peca
        'descricao',               # 3 → Descricao
        'qt_mod',                  # 4 → QT_mod
        'qt_und',                  # 5 → QT_und
        'comp',                    # 6 → Comp
        'larg',                    # 7 → Larg
        'esp',                     # 8 → Esp
        'mps',                     # 9 → MPs (checkbox)
        'mo',                      # 10 → MO (checkbox)
        'orla',                    # 11 → Orla (checkbox)
        'blk',                     # 12 → BLK (checkbox)
        'mat_default',             # 13 → Mat_Default
        'tab_default',             # 14 → Tab_Default
        'ids',                     # 15 → ids
        'num_orc',                 # 16 → num_orc
        'ver_orc',                 # 17 → ver_orc
        'ref_le',                  # 18 → ref_le
        'descricao_no_orcamento',  # 19 → descricao_no_orcamento
        'ptab',                    # 20 → ptab
        'pliq',                    # 21 → pliq
        'des1plus',                # 22 → des1plus
        'des1minus',               # 23 → des1minus
        'und',                     # 24 → und
        'desp',                    # 25 → desp
        'corres_orla_0_4',         # 26 → corres_orla_0_4
        'corres_orla_1_0',         # 27 → corres_orla_1_0
        'tipo',                    # 28 → tipo
        'familia',                 # 29 → familia
        'comp_mp',                 # 30 → comp_mp
        'larg_mp',                 # 31 → larg_mp
        'esp_mp',                  # 32 → esp_mp
        'mp',                      # 33 → MP (checkbox)
        'comp_ass_1',              # 34 → COMP_ASS_1
        'comp_ass_2',              # 35 → COMP_ASS_2
        'comp_ass_3',              # 36 → COMP_ASS_3
        'orla_c1',                 # 37 → ORLA_C1
        'orla_c2',                 # 38 → ORLA_C2
        'orla_l1',                 # 39 → ORLA_L1
        'orla_l2',                 # 40 → ORLA_L2
        'ml_c1',                   # 41 → ML_C1
        'ml_c2',                   # 42 → ML_C2
        'ml_l1',                   # 43 → ML_L1
        'ml_l2',                   # 44 → ML_L2
        'custo_ml_c1',             # 45 → CUSTO_ML_C1
        'custo_ml_c2',             # 46 → CUSTO_ML_C2
        'custo_ml_l1',             # 47 → CUSTO_ML_L1
        'custo_ml_l2',             # 48 → CUSTO_ML_L2
        'qt_total',                # 49 → Qt_Total
        'comp_res',                # 50 → comp_res
        'larg_res',                # 51 → larg_res
        'esp_res',                 # 52 → esp_res
        'gravar_modulo',           # 53 → GRAVAR_MODULO (checkbox)
        'area_m2_und',             # 54 → AREA_M2_und
        'spp_ml_und',              # 55 → SPP_ML_und
        'cp09_custo_mp',           # 56 → CP09_CUSTO_MP
        'custo_mp_und',            # 57 → CUSTO_MP_und
        'custo_mp_total',          # 58 → CUSTO_MP_Total
        'acb_sup',                 # 59 → ACB_SUP (checkbox)
        'acb_inf',                 # 60 → ACB_INF (checkbox)
        'acb_sup_und',             # 61 -> ACB_SUP_und
        'acb_inf_und',             # 62 -> ACB_INF_und
        'cp01_sec',                # 63 → CP01_SEC
        'cp01_sec_und',            # 64 → CP01_SEC_und
        'cp02_orl',                # 65 → CP02_ORL
        'cp02_orl_und',            # 66 → CP02_ORL_und
        'cp03_cnc',                # 67 → CP03_CNC
        'cp03_cnc_und',            # 68 → CP03_CNC_und
        'cp04_abd',                # 69 → CP04_ABD
        'cp04_abd_und',            # 70 → CP04_ABD_und
        'cp05_prensa',             # 71 → CP05_PRENSA
        'cp05_prensa_und',         # 72 → CP05_PRENSA_und
        'cp06_esquad',             # 73 → CP06_ESQUAD
        'cp06_esquad_und',         # 74 → CP06_ESQUAD_und
        'cp07_embalagem',          # 75 → CP07_EMBALAGEM
        'cp07_embalagem_und',      # 76 → CP07_EMBALAGEM_und
        'cp08_mao_de_obra',        # 77 → CP08_MAO_DE_OBRA
        'cp08_mao_de_obra_und',    # 78 → CP08_MAO_DE_OBRA_und
        'soma_custo_und',          # 79 → Soma_Custo_und
        'soma_custo_total',        # 80 → Soma_Custo_Total
        'soma_custo_acb'           # 81 → Soma_Custo_ACB
    ]
    num_cols_esperadas = len(colunas_ui_ordenadas)# Número total de colunas esperadas na tabela UI
    print(f" [DEBUG] Número de colunas esperadas na UI para carregar: {len(colunas_ui_ordenadas)}") # Debug
    # 2) Monta e executa o SELECT com colunas na ordem da UI para leitura da BD
    #    A ordem no SELECT deve coincidir com 'colunas_ordenadas'
    colunas_sql_select = ", ".join(f"`{c}`" for c in colunas_ui_ordenadas)
    sql = f"""
        SELECT {colunas_sql_select}
          FROM dados_def_pecas
         WHERE ids=%s AND num_orc=%s AND ver_orc=%s
         ORDER BY id
    """

    rows_bd = []
    try:
        with obter_cursor() as cursor:
            cursor.execute(sql, (key_ids, key_num, key_ver_final))
            rows_bd = cursor.fetchall()
            print(f"Consulta SQL executada. {len(rows_bd)} registos encontrados na BD.")

    except mysql.connector.Error as err:
        QMessageBox.critical(None, "Erro Base de Dados", f"Erro MySQL ao carregar peças: {err}")
        print(f"[ERRO] MySQL ao carregar peças: {err}")
        tbl.setRowCount(0) # Limpa a tabela em caso de erro de BD
        return
    except Exception as e:
        QMessageBox.critical(None, "Erro Inesperado", f"Erro inesperado ao consultar peças: {e}")
        print(f"[ERRO] Inesperado ao consultar peças: {e}")
        import traceback
        traceback.print_exc()
        tbl.setRowCount(0) # Limpa a tabela
        return

    # --- Início do Preenchimento da Tabela ---
    try:
        tbl.blockSignals(True) # Bloqueia sinais para evitar processamento durante o preenchimento
        tbl.setProperty("importando_dados", True) # Flag para outros handlers

        tbl.setRowCount(0) # Limpa a tabela antes de preencher
        tbl.setRowCount(len(rows_bd)) # Ajusta o número de linhas
        print(f"Ajustado número de linhas da tabela UI para: {len(rows_bd)}")

        # Índices UI importantes (baseados em colunas_ui_ordenadas)
        formula_indices_ui = {4, 5, 6, 7, 8} # qt_mod, qt_und, comp, larg, esp
        bool_indices_ui = {9, 10, 11, 12, 33, 53, 59, 60} # mps, mo, orla, blk, mp, gravar_modulo, acb_sup, acb_inf
        moeda_indices_ui = {20, 21, 45, 46, 47, 48, 57, 58, 61, 62, 64, 66, 68, 70, 72, 74, 76, 78, 79, 80, 81}# ptab, pliq, custo_ml_c1, custo_ml_c2, custo_ml_l1, custo_ml_l2, custo_mp_und, custo_mp_total, acb_sup_und, acb_inf_und, cp01_sec_und, cp02_orl_und, cp03_cnc_und, cp04_abd_und, cp05_prensa_und, cp06_esquad_und, cp07_embalagem_und, cp08_mao_de_obra_und
        percent_indices_ui = {22, 23, 25}# des1plus, des1minus, desp # Colunas que são moeda (formato moeda) e percentuais (formato percentual)
        col_idx_mp_button = 33 # Coluna onde o botão "Escolher" para MP deve aparecer
        cols_nao_editaveis = {0, 15, 16, 17, col_idx_mp_button} # id, ids, num_orc, ver_orc, célula do botão


        # Preenche célula a célula
        for r, row_data_bd in enumerate(rows_bd):
            # Verifica se o número de colunas da BD corresponde ao esperado
            if len(row_data_bd) != num_cols_esperadas:
                print(f"[ERRO] Linha BD {r}: Número de colunas recebido ({len(row_data_bd)}) != esperado ({num_cols_esperadas}). Saltando linha.")
                # Poderia setar uma linha vazia ou com erro
                for c_err in range(tbl.columnCount()):
                     item_err = QTableWidgetItem("ERRO DADOS")
                     item_err.setFlags(Qt.ItemIsEnabled)
                     tbl.setItem(r, c_err, item_err)
                continue # Pula para a próxima linha da BD

            # Processa cada coluna para a linha 'r'
            for col_index_ui, val_bd in enumerate(row_data_bd):

                # --- CASO ESPECIAL: Coluna do Botão MP (Índice 33) ---
                if col_index_ui == col_idx_mp_button:
                    # Adiciona o botão na célula
                    btn = QPushButton("Escolher")
                    # Conecta o botão (usando lambda para capturar a linha 'r' correta)
                    btn.clicked.connect(lambda checked, linha=r: on_mp_button_clicked(ui, linha, "tab_def_pecas"))
                    tbl.setCellWidget(r, col_index_ui, btn)

                    # Cria um item associado para armazenar dados se necessário (ex: estado bool da BD)
                    item_ui = QTableWidgetItem() # Item não terá texto visível aqui
                    # Armazena o valor booleano (0 ou 1) da BD no UserRole do item
                    item_ui.setData(Qt.UserRole, bool(val_bd))
                    # Define flags: Habilitado, Selecionável, mas NÃO Editável pelo teclado
                    item_ui.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    tbl.setItem(r, col_index_ui, item_ui) # Define o item (mesmo com o widget)
                    # print(f"  Debug [L{r} C{col_index_ui}]: Botão MP adicionado. Estado BD bool={bool(val_bd)}")
                    continue # Vai para a próxima coluna

                # --- Tratamento das outras colunas ---
                texto_final_ui = "" # Valor padrão

                # 1. Formatação do valor da BD para texto da UI
                if val_bd is None:
                    texto_final_ui = "" # Nulo na BD -> String vazia na UI
                elif col_index_ui in formula_indices_ui:
                    # Para colunas de fórmula, usar o texto diretamente da BD (são VARCHAR/TEXT)
                    texto_final_ui = str(val_bd)
                elif isinstance(val_bd, Decimal):
                    # Formatar Decimal
                    if val_bd == val_bd.to_integral_value():
                        texto_final_ui = str(int(val_bd))
                    else:
                        if col_index_ui in moeda_indices_ui:
                            texto_final_ui = formatar_valor_moeda(val_bd)
                        elif col_index_ui in percent_indices_ui:
                            texto_final_ui = formatar_valor_percentual(val_bd)
                        elif col_index_ui == 5:  # Qt_und (arredondar para inteiro)
                            texto_final_ui = str(int(round(val_bd)))
                        else:
                            texto_final_ui = f"{val_bd:.2f}".replace('.', ',')
                elif col_index_ui in bool_indices_ui:
                    # Colunas booleanas (checkboxes) - não definimos texto aqui, só o estado
                    pass
                else:
                    # Outros tipos (INT, FLOAT, VARCHAR, etc.)
                    if col_index_ui in moeda_indices_ui:
                        try:
                            texto_final_ui = formatar_valor_moeda(float(val_bd))
                        except Exception:
                            texto_final_ui = str(val_bd)
                    elif col_index_ui in percent_indices_ui:
                        try:
                            texto_final_ui = formatar_valor_percentual(float(val_bd))
                        except Exception:
                            texto_final_ui = str(val_bd)
                    elif col_index_ui == 5:
                        try:
                            texto_final_ui = str(int(round(float(val_bd))))
                        except Exception:
                            texto_final_ui = str(val_bd)
                    else:
                        texto_final_ui = str(val_bd)

                # 2. Criação do QTableWidgetItem
                item_ui = QTableWidgetItem()

                # 3. Configuração do Item (Checkbox, Texto, Flags)
                if col_index_ui in bool_indices_ui: # É uma coluna de checkbox (exceto a 33, já tratada)?
                    # Configura como checkbox
                    item_ui.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    estado = Qt.Checked if val_bd else Qt.Unchecked # val_bd é 0 ou 1
                    item_ui.setCheckState(estado)
                    # Checkboxes geralmente não precisam de texto, mas pode ser útil para debug:
                    # item_ui.setText(str(int(val_bd))) # Descomente para ver 0/1
                else:
                    # Configura como item de texto normal
                    item_ui.setText(texto_final_ui)
                    # Define flags de editabilidade
                    if col_index_ui in cols_nao_editaveis:
                        item_ui.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable) # Não editável
                    else:
                        item_ui.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable) # Editável

                # 4. Define o item na tabela
                tbl.setItem(r, col_index_ui, item_ui)

                # --- DEBUG: Verifica o texto logo após setar (Descomente se necessário) ---
                # test_item = tbl.item(r, col_index_ui)
                # if test_item:
                #     print(f"  Debug [L{r} C{col_index_ui}]: Item setado. Texto='{test_item.text()}', CheckState={test_item.checkState() if col_index_ui in bool_indices_ui else 'N/A'}")
                # else:
                #     print(f"  Debug [L{r} C{col_index_ui}]: FALHA AO SETAR ITEM?")
            # --- Fim do loop de colunas ---
            # Se a célula BLK (coluna 12) estiver marcada, aplicar formatação visual BLK
            # --- INÍCIO DA NOVA LÓGICA: Aplicar formatação BLK ao carregar ---
            blk_item_carregado = tbl.item(r, IDX_BLK) # IDX_BLK = 12
            if blk_item_carregado and blk_item_carregado.checkState() == Qt.Checked:
                origem_tooltip_pliq_carregado = ""
                item_pliq_carregado = tbl.item(r, IDX_PLIQ) # IDX_PLIQ = 21
                if item_pliq_carregado and item_pliq_carregado.toolTip():
                    origem_tooltip_pliq_carregado = item_pliq_carregado.toolTip().strip().lower()
                
                # Determina a origem para a formatação. Se o tooltip do PLIQ indicar "escolher",
                # usa essa origem, senão assume "manual" (pois BLK está ativo).
                origem_formatacao_ao_carregar = "manual" # Default se não encontrar "escolher"
                if "escolher" in origem_tooltip_pliq_carregado:
                    origem_formatacao_ao_carregar = "escolher"
                
                #print(f"[CARREGAR_BD] L{r+1} BLK=True. Formatando com origem='{origem_formatacao_ao_carregar}'.")
                 # Chamada corrigida para usar 'aplicar=True' e 'origem_pliq_tooltip'
                aplicar_ou_limpar_formatacao_blk(
                    table=tbl,
                    row=r,
                    aplicar=True, # Sempre aplicar a formatação verde se BLK está ativo ao carregar
                    origem_pliq_tooltip=origem_formatacao_ao_carregar # Passa a origem para o tooltip do PLIQ
                )

        # ------------------------------------------------------------------
        # Aplicar Cores de Fundo (Após Preenchimento Completo)
        # ------------------------------------------------------------------
        print("\n--- Iniciando aplicação de cores de fundo ---")
        ultima_principal_row = None # Índice da linha da última peça principal encontrada
        comps_da_ultima_principal = set() # Conjunto de componentes associados (em MAIÚSCULAS)

        # Resetar cores da coluna def_peca (índice 2) para o padrão
        col_def_peca_idx = 2
        cor_fundo_padrao = tbl.palette().base() # Cor de fundo padrão da tabela
        for row_idx in range(tbl.rowCount()):
            cell_item = tbl.item(row_idx, col_def_peca_idx)
            if cell_item:
                cell_item.setBackground(cor_fundo_padrao)

        # Itera pelas linhas para aplicar a lógica de coloração
        for row in range(tbl.rowCount()):
            def_peca_item = tbl.item(row, col_def_peca_idx)
            if not def_peca_item: continue # Pula linha se não houver item na coluna def_peca

            def_peca_texto = def_peca_item.text().strip().upper()

            # Se não houver texto em def_peca, não pode ser principal nem associada direta
            if not def_peca_texto:
                #print(f"  [L{row:03}] Sem Def_Peca, ignorada para coloração.")
                continue

            # 1. Verifica se é ASSOCIADA à ÚLTIMA principal encontrada
            is_associated = False
            if ultima_principal_row is not None and def_peca_texto in comps_da_ultima_principal:
                def_peca_item.setBackground(COLOR_ASSOCIATED_BG) # Azul claro
                #print(f"  [L{row:03}] '{def_peca_texto}' marcada como ASSOCIADA à L{ultima_principal_row} (Azul Claro)")
                is_associated = True
                # Uma peça associada NÃO PODE ser uma nova principal ao mesmo tempo

            # 2. Se NÃO for associada, verifica se PODE ser uma NOVA principal
            if not is_associated:
                # Esta linha é agora a candidata a ser a "última principal"
                ultima_principal_row = row
                # Lê os componentes associados desta linha (colunas 34, 35, 36)
                comp1 = safe_item_text(tbl, row, IDX_COMP_ASS_1).strip().upper()
                comp2 = safe_item_text(tbl, row, IDX_COMP_ASS_2).strip().upper()
                comp3 = safe_item_text(tbl, row, IDX_COMP_ASS_3).strip().upper()
                # Atualiza o conjunto de componentes da *nova* última principal
                comps_da_ultima_principal = {c for c in [comp1, comp2, comp3] if c} # Guarda apenas os não vazios

                # Se esta nova principal TEM componentes associados, pinta-a de azul-escuro
                if comps_da_ultima_principal:
                    def_peca_item.setBackground(COLOR_PRIMARY_WITH_ASS_BG) # Azul escuro
                    print(f"  [L{row:03}] '{def_peca_texto}' marcada como PRINCIPAL com associados: {comps_da_ultima_principal} (Azul Escuro)") # pretendo eliminar esta linha
                else:
                    # É uma linha principal, mas sem associados definidos nela
                    # Mantém a cor de fundo padrão (já resetada)
                    print(f"  [L{row:03}] '{def_peca_texto}' é linha PRINCIPAL sem associados.")  # pretendo eliminar esta linha
                    # Não precisa limpar comps_da_ultima_principal aqui, pois foi resetado acima

        print("--- Aplicação de cores concluída ---")
        # ------------------------------------------------------------------
        # Fim da Aplicação de Cores
        # ------------------------------------------------------------------

    except Exception as e:
        # Captura erros inesperados DURANTE o preenchimento ou coloração
        QMessageBox.critical(None, "Erro Inesperado", f"Erro inesperado durante o preenchimento/coloração da tabela de peças: {e}")
        print(f"[ERRO] Inesperado durante preenchimento/coloração: {e}")
        import traceback
        traceback.print_exc()
        # Considerar limpar a tabela aqui também se ocorrer um erro grave no meio do processo
        # tbl.setRowCount(0) # Limpa a tabela em caso de erro grave
        # tbl.setRowCount(1) # Ou apenas uma linha vazia para evitar crash
    finally:
        # Desbloqueia sinais SEMPRE
        tbl.blockSignals(False)
        tbl.setProperty("importando_dados", False)   # já não estamos a importar
        # Após carregar os dados base das peças, este bloco orquestra a atualização completa.
        # Importa e chama 'atualizar_tudo' para processar as linhas carregadas,
        # realizar cálculos, atualizar a UI e tratar componentes associados.
        # Erros durante este processo são capturados e registados.
        try:
            from modulo_orquestrador import atualizar_tudo # Importa a função central de orquestração.
            print("[INFO] Carregar dados de peças: processando linhas carregadas.")
            atualizar_tudo(ui)
        except Exception as e:
            print(f"[ERRO] Erro ao atualizar dados apos carregar pecas: {e}")
