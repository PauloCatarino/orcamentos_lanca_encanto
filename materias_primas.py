# materias_primas.py
# ---------------------------------------------------------
# Ajustes principais nesta versão:
#  - DESC1_PLUS e DESC2_MINUS só aceitam valores inteiros de 0% a 100%.
#  - PRECO_TABELA e PLIQ são sempre arredondados a 2 casas decimais.
#  - DESP continua podendo ser decimal (ex.: 2.5%).
#  - Ref_LE é UNIQUE e não editável.
#  - Pesquisa multi-termo, importação Excel e cálculo de PLIQ mantidos.

"""
materias_primas.py
==================
Este módulo é responsável por gerenciar a tabela de matérias-primas no banco de dados MySQL.
Principais funcionalidades:
  - Criação da tabela "materias_primas" (se não existir) com a definição adequada para MySQL.
  - Conexão e configuração do TableWidget da interface gráfica para exibição e edição dos dados.
  - Operações de inserção, atualização, exclusão e consulta de registros.
  - Implementação de funcionalidades como copiar/colar/apagar linhas e importação de dados a partir de um arquivo Excel.
  
Observação:
  Certifique-se de que o módulo "db_connection.py" esteja devidamente configurado para retornar uma conexão MySQL.
"""

import os
import pandas as pd
import mysql.connector  # Para tratamento de erros (por exemplo, IntegrityError)
import re # Importado para uso em parse_texto_digitado (embora não usado lá atualmente, pode ser útil)

from PyQt5.QtWidgets import (QTableWidgetItem, QMessageBox, QAbstractItemView, QMenu, QPushButton, QDialog)
from PyQt5.QtCore import Qt
import sys
import subprocess

# Importa a função de conexão MySQL (configurada no módulo db_connection.py)
from db_connection import obter_cursor
from utils import obter_diretorio_base

# Importa a janela de pesquisa (coloca este import a apontar para o teu ficheiro real)
from consulta_ref_fornecedores import JanelaPesquisa      # <--- nome do ficheiro do protótipo acima


# Variável global para copiar/colar linhas
_copied_row_data = None


def abrir_janela_pesquisa_multitexto():
    """
    Abre a janela de pesquisa multitexto (referências de placas Excel).
    É aberta como modal, o utilizador só consulta (não importa resultados automaticamente).
    """
    dlg = JanelaPesquisa()
    dlg.setWindowModality(Qt.ApplicationModal)
    dlg.exec_()  # Se JanelaPesquisa for QDialog; se for QWidget, usa dlg.show()



def criar_tabela_materias_primas():
    """
    Cria (se não existir) a tabela "materias_primas" no MySQL.
    Define a coluna 'ID_MP' como chave primária auto-incrementada e 'Ref_LE' como UNIQUE.
    """
    #print("Verificando/Criando tabela 'materias_primas'...")
    try:
        with obter_cursor() as cursor:
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS materias_primas (
              ID_MP INT AUTO_INCREMENT PRIMARY KEY,
              REF_PHC TEXT NULL,
              REF_FORNECEDOR TEXT NULL,
              Ref_LE VARCHAR(10) NOT NULL UNIQUE, -- Chave única
              DESCRICAO_do_PHC TEXT NULL,
              DESCRICAO_no_ORCAMENTO TEXT NULL,
              PRECO_TABELA DOUBLE NULL DEFAULT 0.0,
              DESC1_PLUS DOUBLE NULL DEFAULT 0.0,   -- Armazena como fração (0 a 1)
              DESC2_MINUS DOUBLE NULL DEFAULT 0.0,  -- Armazena como fração (0 a 1)
              PLIQ DOUBLE NULL DEFAULT 0.0,
              UND VARCHAR(10) NULL,                 -- Aumentado ligeiramente o tamanho
              DESP DOUBLE NULL DEFAULT 0.0,         -- Armazena como fração (ex: 0.025 para 2.5%)
              ESP_MP DOUBLE NULL DEFAULT 0.0,
              TIPO VARCHAR(100) NULL,               -- Tamanhos aumentados
              FAMILIA VARCHAR(100) NULL,
              COR VARCHAR(100) NULL,
              CORESP_ORLA_0_4 VARCHAR(50) NULL,
              CORESP_ORLA_1_0 VARCHAR(50) NULL,
              COR_REF_MATERIAL VARCHAR(100) NULL,
              COMP_MP DOUBLE NULL DEFAULT 0.0,
              LARG_MP DOUBLE NULL DEFAULT 0.0,
              NOME_FORNECEDOR VARCHAR(255) NULL,
              NOME_FABRICANTE VARCHAR(255) NULL,
              DATA_ULTIMO_PRECO VARCHAR(10) NULL,   -- Manter como VARCHAR ou usar DATE?
              APLICACAO TEXT NULL,
              NOTAS_1 TEXT NULL,
              NOTAS_2 TEXT NULL,
              NOTAS_3 TEXT NULL,
              NOTAS_4 TEXT NULL,
              INDEX idx_ref_le (Ref_LE),             -- Índice para otimizar buscas por Ref_LE
              INDEX idx_tipo_familia (TIPO, FAMILIA) -- Índice para filtros comuns
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            #print("Tabela 'materias_primas' verificada/criada com sucesso.")
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao criar/verificar tabela 'materias_primas': {err}")
        QMessageBox.critical(None, "Erro Crítico de Base de Dados", f"Não foi possível criar/verificar a tabela 'materias_primas':\n{err}")
    except Exception as e:
        print(f"Erro inesperado ao criar/verificar tabela 'materias_primas': {e}")
        QMessageBox.critical(None, "Erro Crítico", f"Erro inesperado durante a inicialização da tabela 'materias_primas':\n{e}")





def carregar_materias_primas_para_tabela(ui, rows=None):
    """
    Carrega os registros da tabela "materias_primas" que estão na tabela da base dados para a tabela do QTableWidget -> 'tableWidget_materias_primas' .
    Se rows for None, carrega todos os registros; caso contrário, exibe somente os registros fornecidos.
    """
    tbl = ui.tableWidget_materias_primas
    tbl.blockSignals(True) # Bloqueia sinais durante o carregamento
    tbl.setRowCount(0) # Limpa a tabela antes de preencher

    if rows is None:
        #print("Carregando todas as matérias-primas da BD...")
        try:
            with obter_cursor() as cursor:
                # Ordenar por ID_MP por padrão
                cursor.execute("SELECT * FROM materias_primas ORDER BY ID_MP")
                rows = cursor.fetchall()
            #print(f"Carregados {len(rows)} registos.")
        except mysql.connector.Error as err:
            print(f"Erro MySQL ao carregar matérias-primas: {err}")
            QMessageBox.critical(None, "Erro Base de Dados", f"Não foi possível carregar as matérias-primas: {err}")
            rows = [] # Define como lista vazia para evitar erros no loop
        except Exception as e:
            print(f"Erro inesperado ao carregar matérias-primas: {e}")
            QMessageBox.critical(None, "Erro Inesperado", f"Erro ao carregar matérias-primas: {e}")
            rows = []

    # Preenche a tabela com os dados obtidos (BLOCO ÚNICO E CORRETO)
    for rdata in rows:
        row_idx = tbl.rowCount()
        tbl.insertRow(row_idx)
        for c, val in enumerate(rdata):
            disp = formatar_exibicao(c, val) # Formata para exibição
            item = QTableWidgetItem(disp)
            # Impede edição das colunas ID_MP (0) e Ref_LE (3)
            if c == 0 or c == 3:
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            tbl.setItem(row_idx, c, item)
    # Fim do loop 'for rdata in rows:'

    tbl.blockSignals(False) # Desbloqueia sinais após preencher tudo


def formatar_exibicao(col, val):
    """
    Formata o valor do banco para exibição:
      - Colunas 6 e 9 (PRECO_TABELA e PLIQ): exibe com 2 casas decimais e "€".
      - Colunas 7, 8 e 11 (DESC1_PLUS, DESC2_MINUS e DESP): exibe como percentual inteiro com "%".
    """
    if val is None:
        return ""
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return ""

    if col in [6, 9]:
        try:
            f = float(s)
            return f"{f:.2f}€"
        except:
            return s

    if col in [7, 8, 11]:
        try:
            f = float(s)
            pct = int(round(f * 100))
            return f"{pct}%"
        except:
            return s

    return s


def on_item_changed(ui, item):
    """
    Função chamada quando o usuário edita uma célula:
      - Converte o valor digitado (removendo sufixos) para o tipo adequado.
      - Atualiza o registro correspondente no banco de dados.
      - Recalcula o valor de PLIQ se as colunas de preço ou descontos forem alteradas.
    """
    if not item:
        return
    col = item.column()
    # Impede edição das colunas não editáveis
    if col == 0 or col == 3:
        return  # Não editar ID_MP e Ref_LE

    tbl = ui.tableWidget_materias_primas
    row = item.row()
    id_str = safe_text(tbl, row, 0) # Coluna ID_MP é a 0
    if not id_str or not id_str.isdigit():
        print(f"Erro: ID_MP inválido ou não encontrado na linha {row}.")
        return # Não pode atualizar sem ID

    id_mp = int(id_str)
    novo_txt = item.text().strip()

    # Mapeamento das colunas do banco
    colunas_db = [
        "ID_MP",         # 0
        "REF_PHC",       # 1
        "REF_FORNECEDOR",# 2
        "Ref_LE",        # 3
        "DESCRICAO_do_PHC",       # 4
        "DESCRICAO_no_ORCAMENTO", # 5
        "PRECO_TABELA",  # 6
        "DESC1_PLUS",    # 7
        "DESC2_MINUS",   # 8
        "PLIQ",          # 9
        "UND",           # 10
        "DESP",          # 11
        "ESP_MP",        # 12
        "TIPO",          # 13
        "FAMILIA",       # 14
        "COR",           # 15
        "CORESP_ORLA_0_4",    # 16
        "CORESP_ORLA_1_0",    # 17
        "COR_REF_MATERIAL",   # 18
        "COMP_MP",       # 19
        "LARG_MP",       # 20
        "NOME_FORNECEDOR",    # 21
        "NOME_FABRICANTE",    # 22
        "DATA_ULTIMO_PRECO",  # 23
        "APLICACAO",     # 24
        "NOTAS_1",       # 25
        "NOTAS_2",       # 26
        "NOTAS_3",       # 27
        "NOTAS_4"        # 28
    ]
    # Verifica se o índice da coluna é válido
    if col >= len(colunas_db):
        print(f"Erro: Índice de coluna {col} fora dos limites.")
        return

    db_col_name = colunas_db[col]

    # Converte o texto para o tipo de dado correto para o BD
    val_real = parse_texto_digitado(col, novo_txt)
    if val_real is None: # Se a validação/conversão falhou
        print(f"Valor inválido '{novo_txt}' digitado na coluna {db_col_name}. Recarregando valor original.")
        recarregar_celula(tbl, row, col, db_col_name, id_mp) # Recarrega valor da BD
        return

    try:
        # Atualiza o valor no banco de dados usando obter_cursor
        with obter_cursor() as cursor:
            # Usar backticks para nomes de coluna na query UPDATE
            update_query = f"UPDATE materias_primas SET `{db_col_name}`=%s WHERE ID_MP=%s"
            cursor.execute(update_query, (val_real, id_mp))
        # Commit é automático

        # Atualiza a exibição na célula com o valor formatado (após salvar)
        tbl.blockSignals(True)
        item.setText(formatar_exibicao(col, val_real))
        tbl.blockSignals(False)

        # Recalcula e atualiza PLIQ se necessário
        if col in [6, 7, 8]: # PRECO_TABELA, DESC1_PLUS, DESC2_MINUS
            preco = parse_texto_digitado(6, safe_text(tbl, row, 6)) or 0.0 # PRECO_TABELA            
            dplus = parse_texto_digitado(7, safe_text(tbl, row, 7)) or 0.0 # DESC1_PLUS  -> MARGEM
            dmins = parse_texto_digitado(8, safe_text(tbl, row, 8)) or 0.0 # DESC2_MINUS -> DESCONTO
            pliq = round((preco * (1 - dmins)) * (1 + dplus), 2) # Recalcula PLIQ = (PRECO_TABELA*(1-DESC2_MINUS))*(1+DESC1_PLUS)

            with obter_cursor() as cursor_pliq:
                cursor_pliq.execute("UPDATE materias_primas SET PLIQ=%s WHERE ID_MP=%s", (pliq, id_mp))
            # Commit automático

            # Atualiza a célula PLIQ na tabela
            tbl.blockSignals(True)
            tbl.setItem(row, 9, QTableWidgetItem(formatar_exibicao(9, pliq))) # Coluna 9 é PLIQ
            tbl.blockSignals(False)

    except mysql.connector.Error as err:
        print(f"Erro MySQL ao atualizar {db_col_name} para ID {id_mp}: {err}")
        QMessageBox.critical(None, "Erro Base de Dados", f"Erro ao atualizar dados: {err}")
        recarregar_celula(tbl, row, col, db_col_name, id_mp) # Recarrega em caso de erro
    except Exception as e:
        print(f"Erro inesperado ao atualizar {db_col_name}: {e}")
        QMessageBox.critical(None, "Erro Inesperado", f"Erro ao atualizar dados: {e}")
        recarregar_celula(tbl, row, col, db_col_name, id_mp)

def recarregar_celula(tbl, row, col, col_db, id_mp):
    """
    Se o valor digitado for inválido, recarrega o valor do banco e atualiza a célula na tabela.
    """
    print(f"Recarregando célula ({row}, {col}) para ID {id_mp}...")
    real_val = None
    try:
        with obter_cursor() as cursor:
            # Usar backticks para segurança
            cursor.execute(f"SELECT `{col_db}` FROM materias_primas WHERE ID_MP=%s", (id_mp,))
            r = cursor.fetchone()
            if r: real_val = r[0]
    except mysql.connector.Error as err:
        print(f"  Erro MySQL ao recarregar célula: {err}")
    except Exception as e:
        print(f"  Erro inesperado ao recarregar célula: {e}")

    texto_exib = formatar_exibicao(col, real_val) # Formata o valor obtido
    tbl.blockSignals(True)
    # Garante que o item existe antes de setar o texto
    item = tbl.item(row, col)
    if not item:
         item = QTableWidgetItem()
         tbl.setItem(row, col, item)
    item.setText(texto_exib)
    tbl.blockSignals(False)


def safe_text(tbl, row, col):
    """
    Retorna o texto contido na célula (row, col) ou "" se estiver vazio.
    """
    it = tbl.item(row, col)
    return it.text().strip() if it else ""


def parse_texto_digitado(col, txt):
    """
    Converte a string digitada para o tipo adequado:
      - Colunas 6 e 9 (PRECO_TABELA, PLIQ): converte para float (arredondado para 2 decimais).
      - Colunas 7,8 (DESC1_PLUS, DESC2_MINUS): converte para percentual inteiro (0 a 100) e retorna como fração.
      - Coluna 11 (DESP): converte para percentual (pode ter decimais).
      - Colunas 12,19,20: converte para float genérico.
      - Caso contrário, retorna o texto.
    Retorna None se houver erro de conversão ou valor fora dos limites.
    """
    if not txt:
        if col in [6, 7, 8, 9, 11, 12, 19, 20]:
            return 0.0
        else:
            return ""

    if col in [6, 9]:
        s = txt.replace("€", "").replace(",", ".").strip()
        try:
            val = float(s)
            return round(val, 2)
        except:
            QMessageBox.warning(None, "Erro", f"Valor inválido para Moeda: {txt}")
            return None

    if col in [7, 8]:
        s = txt.replace("%", "").replace(",", ".").strip()
        try:
            fVal = float(s)
        except:
            QMessageBox.warning(None, "Erro", f"Valor inválido (deve ser inteiro): {txt}")
            return None
        iVal = int(fVal)
        if abs(fVal - iVal) > 1e-9:
            QMessageBox.warning(None, "Erro", f"Percentual deve ser inteiro (ex.: 10%), não '{txt}'.")
            return None
        if iVal < 0 or iVal > 100:
            QMessageBox.warning(None, "Erro", f"Percentual fora do intervalo 0..100: {iVal}%")
            return None
        return iVal / 100.0

    if col == 11:
        s = txt.replace("%", "").replace(",", ".").strip()
        try:
            return float(s) / 100.0
        except:
            QMessageBox.warning(None, "Erro", f"Valor inválido para Percentagem: {txt}")
            return None

    if col in [12, 19, 20]:
        s = txt.replace(",", ".")
        try:
            return float(s)
        except:
            QMessageBox.warning(None, "Erro", f"Valor inválido (float): {txt}")
            return None

    return txt


# -------------------- Menu de Contexto: Copiar/Colar/Apagar Linha --------------------

def exibir_menu_contexto(ui, pos):
    tbl = ui.tableWidget_materias_primas
    menu = QMenu(tbl)
    ac_copy = menu.addAction("Copiar Linha")
    ac_paste = menu.addAction("Colar Linha")
    ac_del = menu.addAction("Apagar Linha")
    chosen = menu.exec_(tbl.mapToGlobal(pos))
    if chosen == ac_copy:
        copiar_linha(ui)
    elif chosen == ac_paste:
        colar_linha(ui)
    elif chosen == ac_del:
        apagar_linha(ui)


def copiar_linha(ui):
    """
    Copia os dados da linha selecionada (exceto o ID_MP) para uma variável global.
    """
    global _copied_row_data
    tbl = ui.tableWidget_materias_primas
    r = tbl.currentRow()
    if r < 0:
        QMessageBox.warning(None, "Erro", "Nenhuma linha selecionada para copiar.")
        return

    row_data = []
    for c in range(1, tbl.columnCount()):
        row_data.append(safe_text(tbl, r, c))
    _copied_row_data = row_data
    QMessageBox.information(None, "OK", "Linha copiada.")


def colar_linha(ui):
    """
    Cola os dados previamente copiados como uma nova linha no banco de dados.
    """
    global _copied_row_data
    if not _copied_row_data:
        QMessageBox.warning(None, "Erro", "Nenhuma linha foi copiada.")
        return
    if len(_copied_row_data) != 28:
        QMessageBox.warning(None, "Erro", "Dados copiados incorretos.")
        return

    db_cols = [
        "REF_PHC", "REF_FORNECEDOR", "Ref_LE",
        "DESCRICAO_do_PHC", "DESCRICAO_no_ORCAMENTO",
        "PRECO_TABELA", "DESC1_PLUS", "DESC2_MINUS", "PLIQ",
        "UND", "DESP", "ESP_MP",
        "TIPO", "FAMILIA", "COR",
        "CORESP_ORLA_0_4", "CORESP_ORLA_1_0", "COR_REF_MATERIAL",
        "COMP_MP", "LARG_MP",
        "NOME_FORNECEDOR", "NOME_FABRICANTE", "DATA_ULTIMO_PRECO",
        "APLICACAO", "NOTAS_1", "NOTAS_2", "NOTAS_3", "NOTAS_4"
    ]
    # Valida e converte os dados copiados
    parsed_vals = []
    ref_le_colado = "" # Para verificar duplicidade
    for i, txt in enumerate(_copied_row_data):
        col_real = i + 1 # Índice da coluna original na tabela (começa em 1)
        val = parse_texto_digitado(col_real, txt)
        if val is None: # Se a conversão falhou
            QMessageBox.warning(None, "Erro", f"Valor inválido na coluna '{db_cols[i]}' dos dados copiados: '{txt}'. Cola cancelada.")
            return
        parsed_vals.append(val)
        if db_cols[i] == "Ref_LE": # Armazena Ref_LE para verificar duplicidade
            ref_le_colado = val

    # Verificar se Ref_LE já existe ANTES de tentar inserir
    ref_le_existe = False
    try:
        with obter_cursor() as cursor_check:
            cursor_check.execute("SELECT 1 FROM materias_primas WHERE Ref_LE = %s LIMIT 1", (ref_le_colado,))
            if cursor_check.fetchone():
                ref_le_existe = True
    except mysql.connector.Error as err:
         QMessageBox.critical(None, "Erro BD", f"Erro ao verificar Ref_LE: {err}")
         return # Não prosseguir se não puder verificar

    if ref_le_existe:
        QMessageBox.warning(None, "Erro", f"Já existe um registo com Ref_LE '{ref_le_colado}'. Não é possível colar.")
        return

    # Monta a query INSERT
    placeholders = ", ".join(["%s"] * len(db_cols))
    sql = f"INSERT INTO materias_primas ({', '.join(db_cols)}) VALUES ({placeholders})"

    try:
        # Usa obter_cursor para inserir
        with obter_cursor() as cursor_insert:
            cursor_insert.execute(sql, parsed_vals)
        # Commit automático
        QMessageBox.information(None, "OK", "Linha colada com sucesso.")
        carregar_materias_primas_para_tabela(ui) # Recarrega a tabela
    except mysql.connector.Error as err: # Captura erro de integridade ou outro erro MySQL
        print(f"Erro MySQL ao colar linha: {err}")
        QMessageBox.critical(None, "Erro ao Colar", f"Falha ao inserir linha:\n{err}")
    except Exception as e:
        print(f"Erro inesperado ao colar linha: {e}")
        QMessageBox.critical(None, "Erro Inesperado", f"Erro ao colar linha:\n{e}")


def apagar_linha(ui):
    """
    Apaga a linha selecionada do QTableWidget e remove o registro correspondente do banco.
    """
    tbl = ui.tableWidget_materias_primas
    r = tbl.currentRow()
    if r < 0:
        QMessageBox.warning(None, "Erro", "Nenhuma linha selecionada.")
        return
    id_str = safe_text(tbl, r, 0) # Coluna ID_MP é a 0
    if not id_str.isdigit():
        QMessageBox.warning(None, "Erro", "ID_MP inválido.")
        return
    resp = QMessageBox.question(None, "Apagar?", f"Tem a certeza que deseja apagar a linha com ID {id_str}?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if resp != QMessageBox.Yes:
        return

    try:
        # Usa obter_cursor para apagar
        with obter_cursor() as cursor:
            cursor.execute("DELETE FROM materias_primas WHERE ID_MP=%s", (int(id_str),))
            rows_affected = cursor.rowcount # Verifica quantas linhas foram afetadas
        # Commit automático

        if rows_affected > 0:
            carregar_materias_primas_para_tabela(ui) # Recarrega a tabela
            QMessageBox.information(None, "OK", f"Linha ID {id_str} apagada com sucesso.")
        else:
             QMessageBox.warning(None, "Aviso", f"Nenhuma linha encontrada com ID {id_str} para apagar.")

    except mysql.connector.Error as err:
        print(f"Erro MySQL ao apagar linha ID {id_str}: {err}")
        QMessageBox.critical(None, "Erro Base de Dados", f"Erro ao apagar linha: {err}")
    except Exception as e:
        print(f"Erro inesperado ao apagar linha: {e}")
        QMessageBox.critical(None, "Erro Inesperado", f"Erro ao apagar linha: {e}")


# -------------------- Importação de Dados do Excel --------------------

def atualizar_dados_de_excel(ui):
    """
    Lê o arquivo 'TAB_MATERIAS_PRIMAS.xlsx', ignorando as 4 primeiras linhas,
    e faz INSERT ou UPDATE com base no campo Ref_LE (único).
    Converte datas para o formato dd/mm/yyyy e ajusta os valores:
      - PRECO_TABELA e PLIQ: arredondados a 2 casas.
      - DESC1_PLUS e DESC2_MINUS: obrigatoriamente inteiros entre 0 e 100.
      - DESP: pode ser decimal.
    """
        # Tenta obter o diretório a partir do lineEdit
    base_dir = obter_diretorio_base(ui.lineEdit_base_dados.text())
    if not base_dir or not os.path.isdir(base_dir):
        base_dir = os.getcwd()
        print(f"[AVISO] Caminho em lineEdit_base_dados não é válido, usando diretório atual: '{base_dir}'")

    excel_path = os.path.join(base_dir, "TAB_MATERIAS_PRIMAS.xlsx")
    if not os.path.exists(excel_path):
        QMessageBox.warning(None, "Erro", f"Ficheiro Excel não encontrado:\n{excel_path}")
        return

    try:
        # Ler Excel, tratando melhor os tipos de dados na leitura
        df = pd.read_excel(excel_path, skiprows=4, dtype=str) # Ler tudo como string inicialmente
        df = df.fillna('') # Substituir NaN por string vazia
    except Exception as e:
        QMessageBox.critical(None, "Erro", f"Falha ao ler Excel: {e}")
        return

    count_upd = 0
    count_ins = 0
    erros_integridade = 0

    try:
        # Usar obter_cursor para toda a operação de atualização/inserção
        with obter_cursor() as cursor:
            for _, row in df.iterrows():
                ref_le = str(row.get("Ref_LE", "")).strip()
                if not ref_le: continue # Ignora linhas sem Ref_LE

                # Obter e limpar/converter outros valores
                ref_phc   = str(row.get("REF_PHC", "")).strip()
                ref_forn  = str(row.get("REF_FORNECEDOR", "")).strip()
                desc_phc  = str(row.get("DESCRICAO_do_PHC", "")).strip()
                desc_orc  = str(row.get("DESCRICAO_no_ORCAMENTO", "")).strip()
                und       = str(row.get("UND", "")).strip()[:10] # Limita tamanho UND
                t_        = str(row.get("TIPO", "")).strip()[:100]
                fam       = str(row.get("FAMILIA", "")).strip()[:100]
                c_        = str(row.get("COR", "")).strip()[:100]
                co04      = str(row.get("CORESP_ORLA_0_4", "")).strip()[:50]
                co10      = str(row.get("CORESP_ORLA_1_0", "")).strip()[:50]
                corm      = str(row.get("COR_REF_MATERIAL", "")).strip()[:100]
                nfor      = str(row.get("NOME_FORNECEDOR", "")).strip()[:255]
                nfab      = str(row.get("NOME_FABRICANTE", "")).strip()[:255]
                dult      = tratar_data_str(row.get("DATA_ULTIMO_PRECO", ""))[:10] # Formata e limita
                aplc      = str(row.get("APLICACAO", "")).strip()
                n1        = str(row.get("NOTAS_1", "")).strip()
                n2        = str(row.get("NOTAS_2", "")).strip()
                n3        = str(row.get("NOTAS_3", "")).strip()
                n4        = str(row.get("NOTAS_4", "")).strip()

                # Parsing de valores numéricos
                preco = parse_excel_moeda(row.get("PRECO_TABELA", "0"))
                pliq_excel = parse_excel_moeda(row.get("PLIQ", "0")) # Lê PLIQ do Excel
                plus  = parse_excel_percent_inteiro(row.get("DESC1_(+)", "0"))
                minus = parse_excel_percent_inteiro(row.get("DESC2_(-)", "0"))
                dsp   = parse_excel_percent(row.get("DESP", "0"))
                esp   = parse_excel_float(row.get("ESP_MP", "0"))
                comp  = parse_excel_float(row.get("COMP_MP", "0"))
                larg  = parse_excel_float(row.get("LARG_MP", "0"))

                # Validação de percentuais inteiros
                if plus is None or minus is None:
                    print(f"Aviso: Linha com Ref_LE '{ref_le}' ignorada devido a percentual inválido.")
                    continue # Pula para a próxima linha do Excel

                # Recalcular PLIQ com base nos valores lidos do Excel, para garantir consistência
                pliq_calculado = round(preco * (1 + plus) * (1 - minus), 2)

                # Verifica se o registro existe
                cursor.execute("SELECT ID_MP FROM materias_primas WHERE Ref_LE=%s", (ref_le,))
                ex = cursor.fetchone()

                if ex: # UPDATE
                    id_mp_existente = ex[0]
                    update_query = '''
                    UPDATE materias_primas SET
                       REF_PHC=%s, REF_FORNECEDOR=%s, DESCRICAO_do_PHC=%s, DESCRICAO_no_ORCAMENTO=%s,
                       PRECO_TABELA=%s, DESC1_PLUS=%s, DESC2_MINUS=%s, PLIQ=%s, UND=%s, DESP=%s, ESP_MP=%s,
                       TIPO=%s, FAMILIA=%s, COR=%s, CORESP_ORLA_0_4=%s, CORESP_ORLA_1_0=%s, COR_REF_MATERIAL=%s,
                       COMP_MP=%s, LARG_MP=%s, NOME_FORNECEDOR=%s, NOME_FABRICANTE=%s, DATA_ULTIMO_PRECO=%s,
                       APLICACAO=%s, NOTAS_1=%s, NOTAS_2=%s, NOTAS_3=%s, NOTAS_4=%s
                    WHERE ID_MP=%s
                    '''
                    update_params = (
                        ref_phc, ref_forn, desc_phc, desc_orc, preco, plus, minus, pliq_calculado,
                        und, dsp, esp, t_, fam, c_, co04, co10, corm, comp, larg, nfor, nfab, dult,
                        aplc, n1, n2, n3, n4, id_mp_existente
                    )
                    cursor.execute(update_query, update_params)
                    count_upd += 1
                else: # INSERT
                    insert_query = '''
                    INSERT INTO materias_primas (
                        REF_PHC, REF_FORNECEDOR, Ref_LE, DESCRICAO_do_PHC, DESCRICAO_no_ORCAMENTO,
                        PRECO_TABELA, DESC1_PLUS, DESC2_MINUS, PLIQ, UND, DESP, ESP_MP, TIPO, FAMILIA,
                        COR, CORESP_ORLA_0_4, CORESP_ORLA_1_0, COR_REF_MATERIAL, COMP_MP, LARG_MP,
                        NOME_FORNECEDOR, NOME_FABRICANTE, DATA_ULTIMO_PRECO, APLICACAO,
                        NOTAS_1, NOTAS_2, NOTAS_3, NOTAS_4
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    '''
                    insert_params = (
                        ref_phc, ref_forn, ref_le, desc_phc, desc_orc, preco, plus, minus, pliq_calculado,
                        und, dsp, esp, t_, fam, c_, co04, co10, corm, comp, larg, nfor, nfab, dult,
                        aplc, n1, n2, n3, n4
                    )
                    try:
                        cursor.execute(insert_query, insert_params)
                        count_ins += 1
                    except mysql.connector.IntegrityError:
                        erros_integridade += 1
                        print(f"Aviso: Ref_LE '{ref_le}' já existe (concorrência ou erro anterior?), inserção ignorada.")
                    except mysql.connector.Error as insert_err:
                        print(f"Erro MySQL ao inserir Ref_LE '{ref_le}': {insert_err}")
                        # Poderia adicionar à lista de erros para mostrar no final

            # Commit é automático ao sair do 'with' sem erro
        print("Importação do Excel concluída.")

    except mysql.connector.Error as err:
        print(f"Erro MySQL durante atualização/inserção do Excel: {err}")
        QMessageBox.critical(None, "Erro Base de Dados", f"Erro durante o processamento do Excel:\n{err}")
        return # Interrompe em caso de erro grave de BD
    except Exception as e:
        print(f"Erro inesperado durante atualização/inserção do Excel: {e}")
        import traceback
        traceback.print_exc()
        QMessageBox.critical(None, "Erro Inesperado", f"Erro durante o processamento do Excel:\n{e}")
        return

    # Mensagem final após o loop
    msg_final = f"Excel processado!\nAtualizados: {count_upd}\nInseridos: {count_ins}"
    if erros_integridade > 0:
        msg_final += f"\nIgnorados por Ref_LE duplicado: {erros_integridade}"
    QMessageBox.information(None, "Importação Concluída", msg_final)

    # Recarrega a tabela na UI com os dados atualizados
    carregar_materias_primas_para_tabela(ui)


# -------------------- Funções Auxiliares para Parse do Excel --------------------

def parse_excel_moeda(val):
    """
    Converte strings como '12,63€' em float, arredondando para 2 decimais.
    Retorna 0.0 se o valor for vazio ou NaN.
    """
    if pd.isna(val):
        return 0.0
    s = str(val).replace("€", "").replace(",", ".").strip()
    if not s or s.lower() == "nan":
        return 0.0
    try:
        f = float(s)
        return round(f, 2)
    except:
        return 0.0


def parse_excel_percent_inteiro(val):
    """
    Converte valores do Excel para percentual (0 a 1) como inteiro.
    Aceita frações (ex.: 0.15 => 15%) ou valores acima de 1 (ex.: 15 => 15%).
    Retorna None se o valor arredondado não estiver entre 0 e 100.
    """
    if pd.isna(val):
        return 0.0
    if isinstance(val, (float, int)):
        fVal = float(val)
        if 0.0 <= fVal < 1.0:
            fVal = fVal * 100.0
        iVal = int(round(fVal))
        if iVal < 0 or iVal > 100:
            print(f"Percentual fora de 0..100: {iVal}")
            return None
        return iVal / 100.0
    s = str(val).replace("%", "").replace(",", ".").strip()
    if not s or s.lower() == "nan":
        return 0.0
    try:
        fVal = float(s)
        if 0.0 <= fVal < 1.0:
            fVal = fVal * 100.0
        iVal = int(round(fVal))
        if iVal < 0 or iVal > 100:
            print(f"Percentual fora de 0..100: {iVal}")
            return None
        return iVal / 100.0
    except:
        print(f"Valor inválido (deveria ser percentual inteiro): {val}")
        return None


def parse_excel_percent(val):
    """
    Converte valor de percentagem do Excel para decimal (ex.: 15% => 0.15).
    Aceita valores com decimais (ex.: 2.5 => 0.025). Se o valor for > 1 sem '%', assume 15 => 0.15.
    Retorna 0.0 em caso de falha.
    """
    if pd.isna(val):
        return 0.0
    if isinstance(val, (float, int)):
        if val > 1:
            return val / 100.0
        else:
            return float(val)
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return 0.0
    if s.endswith("%"):
        s = s.replace("%", "").replace(",", ".").strip()
        try:
            return float(s) / 100.0
        except:
            return 0.0
    else:
        s = s.replace(",", ".")
        try:
            num = float(s)
            if num > 1:
                return num / 100.0
            else:
                return num
        except:
            return 0.0


def parse_excel_float(val):
    """
    Converte uma string numérica (ex.: '19,2') para float (ex.: 19.2).
    Retorna 0.0 se o valor for vazio ou NaN.
    """
    if pd.isna(val):
        return 0.0
    s = str(val).replace(",", ".").strip()
    if not s or s.lower() == "nan":
        return 0.0
    try:
        return float(s)
    except:
        return 0.0


def tratar_data_str(val):
    """
    Converte a data do Excel para o formato dd/mm/yyyy.
    Retorna uma string vazia se a conversão falhar.
    """
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return ""
    try:
        dt = pd.to_datetime(s, format="%d/%m/%Y", errors="raise")
        return dt.strftime("%d/%m/%Y")
    except:
        try:
            dt2 = pd.to_datetime(s, format="%Y-%m-%d %H:%M:%S", errors="raise")
            return dt2.strftime("%d/%m/%Y")
        except:
            dt3 = pd.to_datetime(s, errors="coerce")
            if dt3 is pd.NaT:
                return ""
            return dt3.strftime("%d/%m/%Y")


# -------------------- Pesquisa Multi-termo --------------------

def pesquisar_materias_primas(ui):
    """
    Função chamada a cada caractere digitado.
    Utiliza split("%") para separar termos e realiza a pesquisa case-insensitive.
    """
    txt = ui.lineEdit_pesquisar_mp.text().strip()
    if not txt:
        carregar_materias_primas_para_tabela(ui) # Recarrega tudo se vazio
        return

    termos = [t for t in txt.split('%') if t.strip()] # Separa por % e remove vazios
    if termos:
        registros = buscar_materias_por_termos(termos) # Busca no BD
        carregar_materias_primas_para_tabela(ui, registros) # Atualiza tabela com resultados


def buscar_materias_por_termos(termos):
    """
    Monta a cláusula WHERE utilizando AND para os termos e OR para as colunas textuais.
    Utiliza LOWER para tornar a busca case-insensitive.
    Retorna os registros correspondentes.
    """
    registros = []
    try:
        with obter_cursor() as cursor:
            colunas_texto = [ # Colunas onde pesquisar
                "REF_PHC", "REF_FORNECEDOR", "Ref_LE", "DESCRICAO_do_PHC",
                "DESCRICAO_no_ORCAMENTO", "TIPO", "FAMILIA", "COR",
                "CORESP_ORLA_0_4", "CORESP_ORLA_1_0", "COR_REF_MATERIAL", "NOME_FORNECEDOR",
                "NOME_FABRICANTE", "DATA_ULTIMO_PRECO", "APLICACAO", "NOTAS_1",
                "NOTAS_2", "NOTAS_3", "NOTAS_4"
            ]
            where_clauses = []
            params = []
            for termo in termos:
                termo_like = f"%{termo}%" # Adiciona % em volta do termo
                clausulas_termo = [f"LOWER(`{col}`) LIKE LOWER(%s)" for col in colunas_texto]
                where_clauses.append(f"({' OR '.join(clausulas_termo)})")
                params.extend([termo_like] * len(colunas_texto))

            sql = "SELECT * FROM materias_primas"
            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)
            sql += " ORDER BY ID_MP" # Ordena por ID

            cursor.execute(sql, params)
            registros = cursor.fetchall()
    except mysql.connector.Error as err:
         print(f"Erro MySQL ao buscar matérias por termos: {err}")
         QMessageBox.warning(None, "Erro Pesquisa", f"Erro na busca: {err}")
    except Exception as e:
         print(f"Erro inesperado ao buscar matérias por termos: {e}")
         QMessageBox.warning(None, "Erro Pesquisa", f"Erro inesperado: {e}")
    return registros



def conectar_materias_primas_ui(main_ui):
    """
    Conecta a interface do módulo de matérias-primas:
      - Cria a tabela (se não existir).
      - Configura o QTableWidget (colunas, larguras e edição).
      - Carrega os dados do banco.
      - Conecta sinais para edição de células, menu de contexto, atualização via Excel e pesquisa.
    """
    ui = main_ui # Usa a variável local 'ui'
    criar_tabela_materias_primas()

    tbl = ui.tableWidget_materias_primas
    tbl.setColumnCount(29)

    # Definição dos cabeçalhos (ordem e nomes das colunas)
    headers = [
        "ID_MP",
        "REF_PHC",
        "REF_FORNECEDOR",
        "Ref_LE",
        "DESCRICAO_do_PHC",
        "DESCRICAO_no_ORCAMENTO",
        "PRECO_TABELA",
        "DESC1_(+)",
        "DESC2_(-)",
        "PLIQ",
        "UND",
        "DESP",
        "ESP_MP",
        "TIPO",
        "FAMILIA",
        "COR",
        "CORESP_ORLA_0.4",
        "CORESP_ORLA_1.0",
        "COR_REF_MATERIAL",
        "COMP_MP",
        "LARG_MP",
        "NOME_FORNECEDOR",
        "NOME_FABRICANTE",
        "DATA_ULTIMO_PRECO",
        "APLICACAO",
        "NOTAS_1",
        "NOTAS_2",
        "NOTAS_3",
        "NOTAS_4"
    ]
    tbl.setHorizontalHeaderLabels(headers)

    # Define as larguras de coluna (ajuste conforme necessário)
    col_widths = [
        50, 80, 100, 100, 450,
        450, 80, 60, 60, 60,
        50, 60, 60, 120, 110,
        90, 110, 110, 120, 60,
        60, 160, 120, 100, 100,
        50, 50, 50, 50
    ]
    for i, w in enumerate(col_widths):
        tbl.setColumnWidth(i, w)

    # Não permite editar a tabela das materias primas diretamente, tem de usar o ficheiro excel, ao tentar editar os dados aparece mensagem de aviso
    tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
    def informar_edicao():
        QMessageBox.information(None, "Editar Matérias-Primas",
                                "Edite o ficheiro Excel 'TAB_MATERIAS_PRIMAS.xlsx' para alterar dados.")
    tbl.cellDoubleClicked.connect(lambda r, c: informar_edicao())

    # Carrega os dados do banco na tabela
    carregar_materias_primas_para_tabela(ui)

    # Conecta o sinal de mudança de item para a função on_item_changed
    tbl = ui.tableWidget_materias_primas
    # Edição direta desativada; apenas informa que deve usar o Excel

    # Configura o menu de contexto (copiar/colar/apagar)
    tbl.setContextMenuPolicy(Qt.CustomContextMenu)
    tbl.customContextMenuRequested.connect(lambda pos: exibir_menu_contexto(ui, pos)) # Passa ui

    # Conecta o botão para atualizar os dados a partir do Excel
    ui.pushButton_atualizar_excel.clicked.connect(lambda: atualizar_dados_de_excel(ui)) # Passa ui

    # Conecta o campo de pesquisa (se existir) para filtrar os dados
    if hasattr(ui, 'lineEdit_pesquisar_mp'):
        ui.lineEdit_pesquisar_mp.textChanged.connect(lambda: pesquisar_materias_primas(ui)) # Passa ui

    # Botão para abrir diretamente o Excel para utilizador modificar no excel, so depois passa para tabela materias primas
    btn_abrir = QPushButton("Abrir Excel", ui.groupBox_materias_config)
    btn_abrir.setGeometry(830, 30, 180, 13)

    # Liga o botão de pesquisa de referência ao slot
    if hasattr(ui, 'pushButton_pesquisa_ref'):
        ui.pushButton_pesquisa_ref.clicked.connect(abrir_janela_pesquisa_multitexto)
        print("DEBUG: Ligado pushButton_pesquisa_ref ao slot de pesquisa de referência!")
    else:
        print("ERRO: O botão pushButton_pesquisa_ref não existe no ui.")


    # Função para abrir o Excel
    def abrir_excel():

        base_dir = obter_diretorio_base(ui.lineEdit_base_dados.text())
        if not base_dir or not os.path.isdir(base_dir):
            base_dir = os.getcwd()
        excel_path = os.path.join(base_dir, "TAB_MATERIAS_PRIMAS.xlsx")

        if not os.path.exists(excel_path):
            QMessageBox.warning(None, "Erro", f"Ficheiro Excel não encontrado:\n{excel_path}")
            return
        try:
            if sys.platform.startswith('win'):
                os.startfile(excel_path)
            elif sys.platform.startswith('darwin'):
                subprocess.Popen(['open', excel_path])
            else:
                subprocess.Popen(['xdg-open', excel_path])
        except Exception as e:
            QMessageBox.warning(None, "Erro", f"Não foi possível abrir o ficheiro:\n{e}")
    btn_abrir.clicked.connect(abrir_excel)
    ui.pushButton_abrir_excel = btn_abrir