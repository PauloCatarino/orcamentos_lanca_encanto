"""
utils.py
========
Este módulo contém funções genéricas de utilidade para o projeto, incluindo:
  - Geração automática do próximo ID para a tabela "orcamentos".
  - Sugestão do próximo número de orçamento com base no ano atual.
  - Limpeza e atualização dos campos da interface para novos orçamentos.
  - Limpeza dos campos do formulário de clientes.
  - Funções de formatação de valores (moeda e percentual) e conversão de texto formatado para valores numéricos.
  - Obtenção de valores distintos de uma coluna com filtro aplicado.

Observação:
  Este módulo utiliza a função get_connection() para obter conexões com o MySQL.
  Certifique-se de que o módulo "db_connection.py" esteja devidamente configurado para retornar uma conexão MySQL.
"""

import datetime
import math
import re
import mysql.connector
from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem, QAbstractItemView
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from db_connection import obter_cursor

# Cor de seleção para linhas das tabelas | # Cor de fundo para linhas selecionadas
ROW_SELECTION_COLOR = QColor(173, 216, 230)  # Azul claro  Esta variavel serve para alterar a cor de seleção das linhas nas tabelas


# Lista de variáveis válidas para expressões matemáticas
VARIAVEIS_VALIDAS = [
    "H", "L", "P",
    "H1", "L1", "P1",
    "H2", "L2", "P2",
    "H3", "L3", "P3",
    "H4", "L4", "P4",
    "HM", "LM", "PM"
]
original_pliq_values = {}


def gerar_id_orcamento():
    """
    Gera automaticamente o próximo ID para a tabela 'orcamentos'.
    Usa o gestor de contexto obter_cursor() para gerir a conexão e o cursor.

    Retorna:
      Uma string com o próximo ID (calculado como MAX(id) + 1), ou "1" em caso de erro.
    """
    ultimo_id = 0  # Valor padrão caso a tabela esteja vazia ou ocorra erro
    try:
        # Utiliza o gestor de contexto para obter e fechar cursor/conexão
        with obter_cursor() as cursor:
            cursor.execute("SELECT MAX(id) FROM orcamentos")
            resultado = cursor.fetchone()
            # Verifica se o resultado não é None e se o valor não é None
            if resultado and resultado[0] is not None:
                ultimo_id = resultado[0]
        # O 'with' garante que cursor e conexão são fechados aqui
        return str(ultimo_id + 1)
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao gerar ID de orçamento: {err}")
        # Retornar "1" como fallback seguro em caso de erro na BD
        return "1"
    except Exception as e:
        print(f"Erro inesperado ao gerar ID de orçamento: {e}")
        return "1"  # Fallback

# Função refatorada para usar obter_cursor()


def sugerir_numero_orcamento(ano):
    """
    Sugere automaticamente o próximo número de orçamento para o ano fornecido.
    Usa o gestor de contexto obter_cursor() para gerir a conexão e o cursor.

    Parâmetros:
      - ano: string representando o ano.

    Retorna:
      Uma string no formato "YYNNNN", ou um valor padrão em caso de erro.
    """
    ultimo_num_orc = None
    try:
        # Utiliza o gestor de contexto
        with obter_cursor() as cursor:
            cursor.execute(
                "SELECT MAX(num_orcamento) FROM orcamentos WHERE ano = %s", (ano,))
            resultado = cursor.fetchone()
            if resultado and resultado[0] is not None:
                ultimo_num_orc = resultado[0]

        # Lógica de cálculo do próximo número (fora do 'with')
        if ultimo_num_orc:
            try:
                # Considera que o formato é YYNNNN; extrai os dígitos da sequência.
                seq = int(ultimo_num_orc[2:])
                novo_seq = seq + 1
            except (ValueError, IndexError):
                # Se o formato não for o esperado, retorna um padrão
                print(
                    f"Aviso: Formato inesperado para último num_orcamento ('{ultimo_num_orc}'). Usando sequência 1.")
                novo_seq = 1
        else:
            novo_seq = 1
        # Formata o resultado final
        return f"{ano[-2:]}{novo_seq:04d}"

    except mysql.connector.Error as err:
        print(f"Erro MySQL ao sugerir número de orçamento: {err}")
        # Retorna um valor padrão em caso de erro na BD
        return f"{ano[-2:]}0001"
    except Exception as e:
        print(f"Erro inesperado ao sugerir número de orçamento: {e}")
        return f"{ano[-2:]}0001"  # Fallback


def limpar_campos_orcamento(ui):
    """
    Limpa os campos específicos do orçamento na interface gráfica (Separador Consulta Orcamentos).
    """
    campos_a_limpar = [
        ui.lineEdit_preco, ui.lineEdit_ref_cliente_2, ui.lineEdit_nome_cliente_2, ui.lineEdit_enc_phc,
        ui.lineEdit_obra_2, ui.plainTextEdit_caracteristicas, ui.lineEdit_localizacao,
        ui.plainTextEdit_info_1, ui.plainTextEdit_info_2
    ]
    for campo in campos_a_limpar:
        campo.clear()


def atualizar_campos_para_novo_orcamento(ui):
    """
    Atualiza os campos da interface para um novo orçamento com base nos dados atuais.

    Parâmetros:
      - ui: objeto da interface que contém os campos do orçamento.
      - get_connection: função que retorna uma conexão com o MySQL.
    """
    # Gera o próximo ID para o orçamento.
    new_id = gerar_id_orcamento()
    ui.lineEdit_id.setText(new_id)

    # Define o ano atual.
    ano_atual = str(datetime.datetime.now().year)
    ui.lineEdit_ano.setText(ano_atual)

    # Sugere o próximo número de orçamento.
    proximo_num = sugerir_numero_orcamento(ano_atual)
    ui.lineEdit_num_orcamento_2.setText(proximo_num)

    # Define a versão padrão "00".
    ui.lineEdit_versao.setText("00")

    # Define a data atual.
    ui.lineEdit_data.setText(datetime.datetime.now().strftime("%d/%m/%Y"))


def limpar_dados_cliente(ui):
    """
    Limpa todos os campos do grupo de dados do cliente na interface (Separador Clientes).

    Parâmetros:
      - ui: objeto da interface que contém os campos do cliente.
    """
    ui.lineEdit_nome_cliente.clear()
    ui.lineEdit_nome_cliente_simplex.clear()
    ui.lineEdit_morada_cliente.clear()
    ui.lineEdit_email_cliente.clear()
    ui.lineEdit_pagina_web.clear()
    ui.lineEdit_num_cliente_phc.clear()
    ui.lineEdit_info_1.clear()
    ui.lineEdit_info_2.clear()
    ui.lineEdit_telefone.clear()
    ui.lineEdit_telemovel.clear()


def formatar_valor_moeda(valor):
    """
    Formata um valor numérico para exibição como moeda.
    Exibe sempre com 2 casas decimais e o símbolo '€'.

    Parâmetros:
      - valor: número a ser formatado.

    Retorna:
      Uma string formatada ou o valor original convertido para string em caso de erro.
    """
    # Adicionada verificação inicial para None
    if valor is None:
        return ""
    try:
        # Tenta converter para float antes de formatar
        return f"{float(valor):.2f}€"
    except (ValueError, TypeError):
        # Se não for possível converter (ex: texto não numérico), retorna como string
        return str(valor)


def formatar_valor_percentual(valor):
    """
    Formata um valor numérico para exibição como percentual.
    Exibe sem casas decimais e com o símbolo '%'.

    Parâmetros:
      - valor: número (fração) a ser formatado.

    Retorna:
      Uma string com o valor percentual ou o valor original convertido para string em caso de erro.
    """
    # Adicionada verificação inicial para None
    if valor is None:
        return ""
    try:
        # Tenta converter para float e multiplica por 100
        pct = float(valor) * 100
        # Formata como inteiro (sem casas decimais) e adiciona '%'
        return f"{pct:.2f}%"
    except (ValueError, TypeError):
        return str(valor)


def converter_texto_para_valor(txt, tipo):
    """
    Converte um texto formatado para um valor numérico "limpo".

    Parâmetros:
      - txt: string a ser convertida.
      - tipo: tipo de conversão; pode ser 'moeda' ou 'percentual'.

    Retorna:
      Um float representando o valor numérico limpo. Retorna 0.0 em caso de falha.
    """
    if not txt:
        return 0.0
    txt_limpo = txt.strip()
    try:
        if tipo == "moeda":
            # Remove '€', substitui ',' por '.' e converte para float com 2 casas decimais
            return round(float(txt_limpo.replace("€", "").replace(",", ".")), 2)
        elif tipo == "percentual":
            # Remove '%', substitui ',' por '.' e converte para float, depois divide por 100
            return float(txt_limpo.replace("%", "").replace(",", ".")) / 100.0
        else:
            # Se o tipo não for reconhecido, tenta converter diretamente para float
            # (pode ser útil para números simples)
            return float(txt_limpo.replace(",", "."))
    except (ValueError, TypeError):
        # Retorna 0.0 se a conversão falhar
        return 0.0


def limpar_formatacao_preco(valor_formatado):
    """
    Remove símbolos de moeda (€) e separadores de milhares (espaços)
    e substitui a vírgula decimal por ponto, retornando uma string
    pronta para ser convertida em float.

    Parâmetros:
      - valor_formatado: string com o valor formatado (ex: "1 234,56 €").

    Retorna:
      String limpa (ex: "1234.56") ou string vazia se a entrada for None ou vazia.
    """
    if not valor_formatado:
        return ""
    # Remove o símbolo '€', remove espaços (separadores de milhares), substitui ',' por '.'
    valor_limpo = valor_formatado.replace(
        "€", "").replace(" ", "").replace(",", ".").strip()
    return valor_limpo


def get_distinct_values_with_filter(col_name, filter_col, filter_val):
    """
    Retorna os valores distintos da coluna `col_name` da tabela "materias_primas",
    considerando apenas os registros em que `filter_col` é igual a `filter_val`.
    Exclui valores nulos ou vazios.

    Parâmetros:
      - col_name: nome da coluna da qual se deseja obter valores distintos.
      - filter_col: coluna que será utilizada para filtrar os registros.
      - filter_val: valor que os registros devem ter na coluna de filtro.

    Retorna:
      Uma lista com os valores distintos encontrados.
    """
    # Importação local para evitar dependência circular.
    # from orcamentos import get_connection
    values = []
    # Validação básica dos nomes das colunas para prevenir injeção SQL simples
    # (Idealmente, usar uma lista mais completa de colunas permitidas)
    allowed_cols = {"tipo", "familia", "ref_le", "descricao",
                    "material"}  # Adicione outras colunas se necessário
    col_name_safe = col_name.strip('`').lower()
    filter_col_safe = filter_col.strip('`').lower()

    if col_name_safe not in allowed_cols or filter_col_safe not in allowed_cols:
        print(
            f"[ERRO] Tentativa de usar colunas não permitidas em get_distinct_values_with_filter: {col_name}, {filter_col}")
        return values  # Retorna lista vazia

    # Usar backticks ` em torno dos nomes das colunas na query
    query = f"""
        SELECT DISTINCT `{col_name_safe}`
        FROM materias_primas
        WHERE LOWER(TRIM(`{filter_col_safe}`)) = LOWER(TRIM(%s))
          AND `{col_name_safe}` IS NOT NULL
          AND `{col_name_safe}` <> ''
        ORDER BY `{col_name_safe}`
    """
    try:
        # Utiliza o gestor de contexto
        with obter_cursor() as cursor:
            cursor.execute(query, (filter_val,))
            # Extrai o primeiro elemento de cada tupla retornada
            values = [row[0] for row in cursor.fetchall()]
    except mysql.connector.Error as err:
        print(
            f"Erro MySQL ao obter valores distintos ({col_name} filtrado por {filter_col}): {err}")
    except Exception as e:
        print(f"Erro inesperado ao obter valores distintos: {e}")
    return values


def avaliar_formula_segura(expr):
    """
    Avalia uma expressão matemática de forma segura, permitindo apenas funções do módulo math.
    Retorna o resultado ou None em caso de erro.
    """
    if not isinstance(expr, str):  # Verifica se a entrada é uma string
        return None

    expr = expr.strip()
    if expr == "":
        # Expressão vazia não é avaliada
        return None
    try:
        # Dicionário seguro, permite apenas funções matemáticas
        safe_dict = {"__builtins__": None}
        # Adiciona funções e constantes do módulo math
        safe_dict.update({k: getattr(math, k)
                         for k in dir(math) if not k.startswith("__")})
        # Avalia a expressão usando o dicionário seguro
        return eval(expr, safe_dict)
    except NameError as ne:
        # Erro comum se tentar usar variáveis não definidas (H, L, etc. não são passadas aqui)
        print(
            f"[Erro avaliar_formula_segura] Nome não definido: {ne} na expressão '{expr}'")
        return None
    except SyntaxError as se:
        print(
            f"[Erro avaliar_formula_segura] Sintaxe inválida: {se} na expressão '{expr}'")
        return None
    except Exception as e:
        # Captura outros erros potenciais (divisão por zero, etc.)
        print(f"[Erro avaliar_formula_segura] Erro ao avaliar '{expr}': {e}")
        return None


def validar_expressao_modulo(texto, row=None, nome_coluna=None):
    """
    Valida se o texto representa:
      - um número (ex.: "2500" ou "2500,00");
      - uma variável simples (ex.: "H");
      - ou uma expressão aritmética composta (ex.: "H/2", "L*3", "H+150", "(H/2)+90"),
    garantindo que as variáveis utilizadas estejam listadas em VARIAVEIS_VALIDAS.

    Parâmetros:
      texto       : string a ser validada.
      row         : (opcional) número da linha (usado para mensagem de erro).
      nome_coluna : (opcional) nome da coluna (usado para mensagem de erro).

    Retorna:
      True se a expressão for válida; False em caso contrário.
      Em caso de expressão inválida, exibe uma QMessageBox com a mensagem de erro.
    """
    if not isinstance(texto, str):
        return False  # Garante que é string
    texto = texto.strip().upper()
    if not texto:
        return True  # Vazio é válido

    # 1. Tenta converter para número
    try:
        float(texto.replace(",", "."))
        return True
    except ValueError:
        pass  # Não é número simples, continua a validação

    # 2. Verifica se é uma variável válida isolada
    if texto in VARIAVEIS_VALIDAS:
        return True

    # 3. Valida expressão composta
    # Extrai todas as "palavras" (potenciais variáveis)
    # Modificado para incluir HM, LM, PM
    tokens = re.findall(r'[A-Z][A-Z0-9]*', texto)
    for token in tokens:
        # Se não for um número (já tratado) e não for variável válida
        if not token.isdigit() and token not in VARIAVEIS_VALIDAS:
            msg = f"O valor '{texto}'"
            if row is not None and nome_coluna is not None:
                msg += f" na linha {row+1}, coluna '{nome_coluna}'"
            msg += f" contém a variável inválida '{token}'.\nPermitidas: {', '.join(VARIAVEIS_VALIDAS)}"
            QMessageBox.warning(None, "Valor Inválido", msg)
            return False

    # 4. Tenta avaliar a expressão com variáveis dummy para testar a sintaxe
    dummy_env = {var: 1 for var in VARIAVEIS_VALIDAS}
    # Adiciona funções matemáticas seguras ao ambiente dummy
    math_funcs = {k: getattr(math, k)
                  for k in dir(math) if not k.startswith("__")}
    dummy_env.update(math_funcs)

    try:
        # Usa eval com o ambiente dummy e restrições
        eval(texto, {"__builtins__": None}, dummy_env)
        return True  # Se avaliou sem erro, a sintaxe é válida
    except Exception as e:
        msg = f"A expressão '{texto}'"
        if row is not None and nome_coluna is not None:
            msg += f" na linha {row+1}, coluna '{nome_coluna}'"
        msg += f" não é válida.\nErro: {e}"
        QMessageBox.warning(None, "Expressão Inválida", msg)
        return False


def validar_variaveis_usadas(formula, row, nome_coluna):
    # Esta função parece redundante se validar_expressao_modulo for usada corretamente
    # import re
    # tokens = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', formula.upper()) # Expressão mais genérica
    # for token in tokens:
    #     if not token.isdigit() and token not in VARIAVEIS_VALIDAS: # Ignora números
    #         QMessageBox.warning(None, "Variável Inválida",
    #             f"A variável '{token}' usada na linha {row+1}, coluna '{nome_coluna}' não é reconhecida.\nPermitidas: {', '.join(VARIAVEIS_VALIDAS)}")
    #         return False
    return True  # Se usada, deve retornar True se tudo ok


##############################################
# Parte 6.1: botão "Escolher" na coluna MP
##############################################
def on_mp_button_clicked(ui, row, nome_tabela):
    # Importação local para evitar o ciclo de importação
    from tabela_def_pecas_items import escolher_material_item
    from PyQt5.QtWidgets import QMessageBox
    """
    Chamado quando o usuário clica no botão "Escolher" na coluna MP.
    Abre o diálogo de seleção de material (adaptado para tab_def_pecas) e,
    se confirmado, mapeia os dados do material para a linha 'row' da tabela 'tab_def_pecas'.
    Exibe uma mensagem informando se a seleção foi bem-sucedida.
    """

    if escolher_material_item(ui, row):
        QMessageBox.information(
            None, "Material", f"Material selecionado para a linha {row+1}.")


# --- Função auxiliar para obter texto de célula de forma segura ---
def safe_item_text(table, row, col, default=""):
    """
    Retorna o texto do item na célula (row, col) ou o valor default caso o item não exista ou seja None.
    """
    item = table.item(row, col)
    if item is None or item.text() is None:
        return default
    return item.text()


def set_item(table, row, col, text):
    """
    Garante que exista um QTableWidgetItem na célula (row, col).
    Se não existir, cria um novo item.
    Define o texto do item existente ou novo.
    Evita criar e setar o mesmo item repetidamente na mesma célula.
    """
    item = table.item(row, col)
    if item is None:
        # Se o item não existe, cria um novo e define-o na célula.
        item = QTableWidgetItem(str(text))  # Garante que o texto é string
        table.setItem(row, col, item)
    else:
        # Se o item já existe, apenas atualiza o texto.
        # Não precisa de chamar setItem novamente, pois o item já está na tabela.
        item.setText(str(text))  # Garante que o texto é string

    # Opcional: Pode querer retornar o item para permitir configurações adicionais (flags, tooltips, etc.)
    return item


def adicionar_menu_limpar(tabela, callback):
    """Associa um menu de contexto com opção de limpar linhas selecionadas."""
    from PyQt5.QtWidgets import QMenu

    def abrir_menu(pos):
        menu = QMenu(tabela)
        acao = menu.addAction("Limpar linha(s) selecionada(s)")
        acao_ret = menu.exec_(tabela.mapToGlobal(pos))
        if acao_ret == acao:
            callback()

    tabela.setContextMenuPolicy(Qt.CustomContextMenu)
    tabela.customContextMenuRequested.connect(abrir_menu)


def copiar_valores_tabela(origem, destino):
    """Copia valores de ``origem`` para ``destino`` célula a célula."""
    rows = min(origem.rowCount(), destino.rowCount())
    cols = min(origem.columnCount(), destino.columnCount())
    destino.blockSignals(True)
    destino.setProperty("importando", True)
    for r in range(rows):
        for c in range(cols):
            texto = ""
            w_src = origem.cellWidget(r, c)
            if w_src:
                if hasattr(w_src, "currentText"):
                    texto = w_src.currentText()
                elif hasattr(w_src, "text"):
                    texto = w_src.text()
            else:
                it = origem.item(r, c)
                if it:
                    texto = it.text()

            w_dst = destino.cellWidget(r, c)
            if w_dst:
                if hasattr(w_dst, "findText"):
                    idx = w_dst.findText(texto)
                    w_dst.setCurrentIndex(idx if idx >= 0 else -1)
                elif hasattr(w_dst, "setText"):
                    w_dst.setText(texto)
            else:
                set_item(destino, r, c, texto)
    destino.setProperty("importando", False)
    destino.blockSignals(False)


def copiar_dados_gerais_para_itens(ui):
    """Copia as quatro tabelas de Dados Gerais para as tabelas dos itens."""
    pares = [
        (ui.Tab_Material, ui.Tab_Material_11),
        (ui.Tab_Ferragens, ui.Tab_Ferragens_11),
        (ui.Tab_Sistemas_Correr, ui.Tab_Sistemas_Correr_11),
        (ui.Tab_Acabamentos, ui.Tab_Acabamentos_12),
    ]
    for origem, destino in pares:
        copiar_valores_tabela(origem, destino)


def apply_row_selection_style(table, color=ROW_SELECTION_COLOR):
    """Define que a tabela selecione linhas inteiras e aplica a cor de fundo da seleção."""
    if table is None:
        return
    try:
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setStyleSheet(
            f"QTableWidget::item:selected{{background-color: {color.name()};}}"
        )
    except Exception as e:
        print(f"[ERRO] apply_row_selection_style: {e}")

"""
def tabela_tem_dados(table):
    #Retorna True se a tabela possuir algum valor preenchido fora da primeira coluna.
    if table is None:
        return False
    try:
        for r in range(table.rowCount()):
            for c in range(1, table.columnCount()):
                widget = table.cellWidget(r, c)
                if widget:
                    if hasattr(widget, "currentText") and widget.currentText().strip():
                        return True
                    if hasattr(widget, "text") and widget.text().strip():
                        return True
                    if hasattr(widget, "value"):
                        try:
                            if widget.value():
                                return True
                        except Exception:
                            pass
                item = table.item(r, c)
                if item and item.text().strip():
                    return True
    except Exception as e:
        print(f"[ERRO] tabela_tem_dados: {e}")
    return False
"""
    
def verificar_dados_itens_salvos(num_orc, ver_orc, item_id):
    """Verifica se existem dados gravados para o item nas tabelas de dados dos itens.

    Retorna True se encontrar pelo menos um registo com alguma das colunas
    principais preenchidas (ref_le, descricao_no_orcamento, ptab, pliq,
    desc1_plus, desc2_minus, und ou desp). Caso contrário, retorna False.
    """
    tabelas = [
        ("dados_items_materiais", "id_mat"),
        ("dados_items_ferragens", "id_fer"),
        ("dados_items_sistemas_correr", "id_sc"),
        ("dados_items_acabamentos", "id_acb"),
    ]
    col_text = ["ref_le", "descricao_no_orcamento", "und"]
    col_num = ["ptab", "pliq", "desc1_plus", "desc2_minus", "desp"]
    condicoes = [f"COALESCE({c}, '') <> ''" for c in col_text]
    condicoes += [f"COALESCE({c}, 0) <> 0" for c in col_num]
    where_extra = " OR ".join(condicoes)
    for tabela, col_id in tabelas:
        try:
            with obter_cursor(commit_on_exit=False) as cursor:
                query = (
                    f"SELECT COUNT(*) FROM {tabela} "
                    f"WHERE num_orc=%s AND ver_orc=%s AND {col_id}=%s AND ({where_extra})"
                )
                cursor.execute(query, (num_orc, ver_orc, item_id))
                if cursor.fetchone()[0] > 0:
                    return True
        except mysql.connector.Error as err:
            print(f"[ERRO DB] Verificação de dados em {tabela}: {err}")
        except Exception as e:
            print(f"[ERRO] Verificação de dados em {tabela}: {e}")
    return False
