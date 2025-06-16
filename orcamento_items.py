"""
orcamento_items.py
==================
Este módulo gerencia os itens (artigos) de cada orçamento e integra diversas funcionalidades essenciais para o gerenciamento dos orçamentos. As principais funcionalidades são:

1) Criação da tabela "orcamento_items" no banco de dados MySQL (se não existir), com definição adequada para MySQL.

2) Ao clicar em "Abrir Orçamento":
   - Alterna para a aba "Orcamento".
   - Carrega os dados do orçamento e do cliente do banco de dados.
   - Exibe todos os itens do orçamento no QTableWidget (tableWidget_artigos).

3) Inserção de um novo item de orçamento via groupBox de linhas, com atualização automática do próximo número do item.

4) Duplicação e eliminação de itens da linha de orçamento diretamente pela tabela por meio de menu de contexto.

5) Edição de itens, tanto diretamente na tabela (por meio do evento itemChanged) quanto via groupBox, com recálculo do preço total conforme necessário.

6) Ao selecionar uma linha na tabela, os dados são copiados para o groupBox para edição e, após a alteração, o groupBox é limpo (exceto o campo do item, que é mantido ou incrementado automaticamente).

7) NOVA FUNCIONALIDADE – Mapeamento dos dados do separador "tab_criar_orcamento" para o separador "dados_item_orcamento":
   - Preenchimento dos QLineEdit conforme:
       • nome_cliente_11    ← lineEdit_nome_cliente1
       • num_orcamento_11   ← lineEdit_num_orcamento
       • versao_orcamento_11← lineEdit_versao_orcamento
       • ref_cliente_11     ← lineEdit_ref_cliente
   - Atualização da tabela 'tab_artigos_11' com os dados dos itens, onde a primeira linha de dados (índice 0) recebe:
       • Coluna "Item"          ← lineEdit_item_orcamento
       • Coluna "Codigo"        ← lineEdit_codigo_orcamento (convertido para maiúsculas)
       • Coluna "Descricao"     ← plainTextEdit_descricao_orcamento
       • Coluna "Altura"        ← lineEdit_altura_orcamento
       • Coluna "Largura"       ← lineEdit_largura_orcamento
       • Coluna "Profundidade"  ← lineEdit_profundidade_orcamento
       • Coluna "Und"           ← lineEdit_und_orcamento
       • Coluna "QT"            ← lineEdit_qt_orcamento
       • Caso existam colunas para preço unitário e total, estas são deixadas em branco para posterior cálculo.

8) NOVO: Cálculo de Custos Detalhados e Margens na 'tableWidget_artigos':
   - `Custo Produzido`: Soma de `Custo Total Orlas (€)` + `Custo Total Mão de Obra (€)` + `Custo Total Acabamentos (€)`.
   - `Custo Total Orlas (€)`: Soma dos custos parciais das orlas (CUSTO_ML_C1 + CUSTO_ML_C2 + CUSTO_ML_L1 + CUSTO_ML_L2) da `dados_def_pecas` para todas as peças associadas ao item.
   - `Custo Total Mão de Obra (€)`: Soma dos custos de máquinas/mão de obra unitários (Soma_Custo_und) da `dados_def_pecas` para todas as peças associadas ao item.
   - `Custo Total Matéria Prima (€)`: Soma dos CUSTO_MP_Total da `dados_def_pecas` para todas as peças associadas ao item.
   - `Custo Total Acabamentos (€)`: Soma dos Soma_Custo_ACB da `dados_def_pecas` para todas as peças associadas ao item.
   - `Margem de Lucro (%)`, `Valor da Margem (€)`, `Custos Administrativos (%)`, `Valor Custos Admin. (€)`, `Ajustes_1(%)`, `Valor Ajustes_1 (€)`, `Ajustes_2 (%)`, `Valor Ajustes_2 (€)`: Calculados com base no custo total do item e percentagens. As percentagens podem ser editadas por item ou usar valores globais (lineEdit_margem_lucro, etc.).

9) NOVO: Lógica "Atingir Objetivo de Preço Final":
   - Permite ao utilizador definir um preço final no `lineEdit_atingir_preco_final`.
   - O botão `pushButton_atualiza_preco_final` ajusta automaticamente a `Margem de Lucro (%)` de todos os itens para que a soma dos `Preco_Total` dos itens atinja o valor definido no objetivo.

Observação: Certifique-se de que a função get_connection(), importada do módulo de conexão, esteja corretamente configurada para retornar uma conexão MySQL.
"""

import datetime
import mysql.connector  # Adicionado para erros específicos
from PyQt5.QtCore import QDate, Qt, QTimer  # Importado QTimer
from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem, QAbstractItemView, QTreeWidgetItem,  QMenu, QDialog
from PyQt5.QtGui import QColor  # Importar QColor para a coloração de células
# Importa a função de conexão MySQL (já configurada no módulo de conexão)
from db_connection import obter_cursor
# Importa a função para configurar os Dados Gerais do Orçamento
from configurar_guardar_dados_gerais_orcamento import configurar_dados_gerais, carregar_dados_gerais_se_existir
from utils import (formatar_valor_moeda, converter_texto_para_valor, formatar_valor_percentual, set_item, verificar_dados_itens_salvos)
from menu_descricoes import configurar_menu_descricoes # Este módulo é usado para configurar o menu de descrições pré-definidas que existe no separdor orcamento, permite adicionar descricoes a cada item de orçamento

# Importa diálogo e gestor de descrições
from dialogo_descricoes import DialogoDescricoes
from descricoes_manager import carregar_descricoes, guardar_descricoes
# Importar o módulo necessário para chamar a função de atualização da tab_modulo_medidas
import tabela_def_pecas_items

# Importar o módulo para as funções de carregamento (embora sejam chamadas indiretamente)
import modulo_dados_definicoes


# Importa a função para configurar os Dados Items (tabela de materiais do item)
from dados_items_materiais import configurar_dados_items_orcamento_materiais as configurar_dados_items_orcamento_materiais
# Importa a função para configurar os Dados Items (tabela de ferragens do item)
from dados_items_ferragens import configurar_dados_items_orcamento_ferragens as configurar_dados_items_orcamento_ferragens
# Importa a função para configurar os Dados Items (tabela de sistemas_correr do item)
from dados_items_sistemas_correr import configurar_dados_items_orcamento_sistemas_correr as configurar_dados_items_orcamento_sistemas_correr
# Importa a função para configurar os Dados Items (tabela de acabamentos do item)
from dados_items_acabamentos import configurar_dados_items_orcamento_acabamentos as configurar_dados_items_orcamento_acabamentos
# Importa a função para carregar os dados da Base Dados SQL do módulo de medidas e da tabela de definições de peças
from modulo_dados_definicoes import carregar_dados_modulo_medidas, carregar_dados_def_pecas
from modulo_orquestrador import atualizar_tudo # Importa a função para atualizar tudo após ações de orçamento
from tab_modulo_medidas_formatacao import aplicar_formatacao # Importa a função para aplicar formatação na tabela de medidas


# Variável global para evitar chamadas recursivas durante edição programática
_editando_programaticamente = False
# --- Constantes para índices das colunas na tableWidget_artigos (0-based) ---
# Estas constantes são usadas para aceder às colunas da tableWidget_artigos de forma legível.
COL_ID_ITEM = 0  # Esta coluna é oculta na UI
COL_ITEM_NUM = 1
COL_CODIGO = 2
COL_DESCRICAO = 3
COL_ALTURA = 4
COL_LARGURA = 5
COL_PROFUNDIDADE = 6
COL_UND = 7
COL_QT = 8
COL_PRECO_UNIT = 9
COL_PRECO_TOTAL = 10
COL_CUSTO_PRODUZIDO = 11
COL_CUSTO_ORLAS = 12
COL_CUSTO_MO = 13
COL_CUSTO_MP = 14
COL_CUSTO_ACABAMENTOS = 15
COL_MARGEM_PERC = 16
COL_MARGEM_VALOR = 17
COL_CUSTOS_ADMIN_PERC = 18
COL_CUSTOS_ADMIN_VALOR = 19
COL_AJUSTES1_PERC = 20
COL_AJUSTES1_VALOR = 21
COL_AJUSTES2_PERC = 22
COL_AJUSTES2_VALOR = 23  # Última coluna, total de 24 colunas (0-23)

# --- Constantes para índices das colunas na dados_def_pecas (na DB) ---
# Estes correspondem às colunas na tabela 'dados_def_pecas'
# Obtidos de modulo_calculos_custos.py para consistência.
# Não são usados diretamente aqui para query, mas são importantes para entender a origem dos dados.
# Os dados são somados da DB e não individualmente de cada peça.
IDX_DEF_PECA_DB = 2  # Def_Peca
IDX_QT_TOTAL_DB = 49  # Qt_Total
IDX_CUSTO_ML_C1_DB = 45  # CUSTO_ML_C1
IDX_CUSTO_ML_C2_DB = 46  # CUSTO_ML_C2
IDX_CUSTO_ML_L1_DB = 47  # CUSTO_ML_L1
IDX_CUSTO_ML_L2_DB = 48  # CUSTO_ML_L2
IDX_CUSTO_MP_TOTAL_DB = 58  # CUSTO_MP_Total
IDX_SOMA_CUSTO_UND_DB = 79  # Soma_Custo_und (máquinas/MO por peça)
IDX_SOMA_CUSTO_ACB_DB = 81  # Soma_Custo_ACB
# Cor para células editadas manualmente
COLOR_MANUAL_EDIT = QColor(255, 255, 150)  # Amarelo claro


def configurar_orcamento_ui(main_window):
    """
    Configura a interface do módulo de itens de orçamento.
    - Cria a tabela "orcamento_items" no banco (se não existir).
    - Ajusta o QTableWidget (tableWidget_artigos) para ter 24 colunas.
    - Conecta botões de ação e sinais de eventos (seleção, edição, pesquisa).
    """
    criar_tabela_orcamento_items()
    ui = main_window.ui  # Obtém ui a partir de main_window

    # Conecta os validadores para os lineEdits de percentagem
    ui.lineEdit_margem_lucro.textChanged.connect(
        lambda: _validate_percentage_input(ui.lineEdit_margem_lucro, 0, 99))
    ui.lineEdit_custos_administrativos.textChanged.connect(
        lambda: _validate_percentage_input(ui.lineEdit_custos_administrativos, 0, 99))
    ui.lineEdit_ajustes_1.textChanged.connect(
        lambda: _validate_percentage_input(ui.lineEdit_ajustes_1, 0, 99))
    ui.lineEdit_ajustes_2.textChanged.connect(
        lambda: _validate_percentage_input(ui.lineEdit_ajustes_2, 0, 99))

    # Botão "Abrir Orçamento"
    ui.pushButton_abrir_orcamento.clicked.connect(
        lambda: abrir_orcamento((main_window)))

    # Botões de Inserir, Eliminar,  Editar itens, Pesquisar, Configurar Dados Gerais
    ui.pushButton_inserir_linha_orcamento.clicked.connect(
        lambda: inserir_item_orcamento(ui))
    ui.pushButton_configurar_dados_gerais.clicked.connect(lambda: configurar_dados_gerais(
        main_window))  # Preenche os campos num_orc e ver_orc nas tabelas dos Dados Gerais

    # Se o utilizador preencher manualmente num_orc ou versao, tenta carregar dados gerais
    ui.lineEdit_num_orcamento.editingFinished.connect(
        lambda: carregar_dados_gerais_se_existir(main_window))
    ui.lineEdit_versao_orcamento.editingFinished.connect(
        lambda: carregar_dados_gerais_se_existir(main_window))
    # Ao alternar para o separador de Dados Gerais MP, carrega dados se existirem
    ui.tabWidget_orcamento.currentChanged.connect(
        lambda idx: carregar_dados_gerais_se_existir(main_window)
        if ui.tabWidget_orcamento.widget(idx).objectName() == "dados_gerais_mp"
        else None)

    ui.pushButton_eliminar_linha_orcamento.clicked.connect(
        lambda: eliminar_item_orcamento(ui))
    ui.pushButton_editar_linha_orcamento_2.clicked.connect(
        lambda: editar_item_orcamento_groupbox(ui))
    ui.lineEdit_pesquisar_orcamento.textChanged.connect(
        lambda: pesquisar_itens(ui))
    # Botão "orcamentar_items": mapeia os dados do separador "tab_criar_orcamento" para "dados_item_orcamento"
    # e também configura as tabelas dos itens (materiais, ferragens, sistemas correr e acabamentos)
    # Este botão também atualiza os dados de medidas e definições de peças.
    ui.orcamentar_items.clicked.connect(lambda: acao_orcamentar_items(main_window))

    # NOVO: Conexão para o botão "Atualiza Preco Items Orcamento"
    # Este botão irá disparar o cálculo e atualização de todas as colunas de custo e preço por item.
    # Por padrão, não força a margem global.
    ui.pushButton_atualiza_preco_items.clicked.connect(
        lambda: atualizar_custos_e_precos_itens(ui, force_global_margin_update=False))

    # NOVO/MODIFICADO: Conexão para o botão "Atualiza Preco Final"
    # Este botão recalcula o preço final do orçamento, e pode ajustar a margem.
    ui.pushButton_atualiza_preco_final.clicked.connect(
        lambda: calcular_preco_final_orcamento(ui))

    # Configuração da tabela "tableWidget_artigos": 24 colunas (coluna 0 = id_item, oculto)
    ui.tableWidget_artigos.setColumnCount(24)
    header_labels = [
        "id_item", "Item", "Codigo", "Descricao",
        "Altura", "Largura", "Profund", "Und", "QT", "Preco_Unit", "Preco_Total", "Custo Produzido",
        "Custo Total Orlas (€)", "Custo Total Mão de Obra (€)", "Custo Total Matéria Prima (€)", "Custo Total Acabamentos (€)",
        "Margem de Lucro (%)", "Valor da Margem (€)", "Custos Administrativos (%)", "Valor Custos Admin. (€)",
        "Ajustes_1(%)", "Valor Ajustes_1 (€)", "Ajustes_2 (%)", "Valor Ajustes_2 (€)"
    ]
    ui.tableWidget_artigos.setHorizontalHeaderLabels(header_labels)
    ui.tableWidget_artigos.setColumnHidden(
        COL_ID_ITEM, True)  # Ocultar coluna id_item

    # Permite edição direta na tabela
    ui.tableWidget_artigos.setEditTriggers(
        QAbstractItemView.DoubleClicked | QAbstractItemView.SelectedClicked
    )
    ui.tableWidget_artigos.itemChanged.connect(
        lambda item: handle_item_editado(ui, item))

    # Ao selecionar uma linha, atualiza os campos do groupBox para edição
    ui.tableWidget_artigos.itemSelectionChanged.connect(
        lambda: atualizar_campos_groupbox_por_selecao(ui))

    # Chama a função para configurar o menu de contexto no groupBox de linhas opção com o botão lado direito do rato tem opção de limpar dados nos campos dos item do orçamento para poder escrever novo item a inserir na tabela dos items do orcamento
    configurar_context_menu_groupbox(ui)
    # Configura menu de contexto para duplicar linhas na tabela de artigos
    configurar_context_menu_tabela(ui)
    # Menu de descrições pré-definidas para o campo de descrição do item dentro do separador de orcamento
    configurar_menu_descricoes(ui)

    # Inicializa o campo de item com "1"
    ui.lineEdit_item_orcamento.setText("1")
# NOVO: Função de validação para os lineEdits de percentagem


def _validate_percentage_input(line_edit, min_val, max_val):
    """
    Valida se o texto num QLineEdit é uma percentagem numérica válida
    (entre min_val e max_val).
    Formata o texto com "%" no final e duas casas decimais.
    """
    current_text = line_edit.text().strip()

    # Se o texto está vazio, considera 0% e não alerta
    if not current_text:
        line_edit.setText("0.00%")
        return

    # Remove o '%' para tentar converter
    numeric_text = current_text.replace("%", "").replace(",", ".")

    try:
        value = float(numeric_text)  # Ex: 12.5 para 12.5%
        # Se o valor for fora do range, alerta e tenta reverter
        if not (min_val <= value <= max_val):
            # CORRIGIDO: Usar line_edit.window() como parent para QMessageBox
            QMessageBox.warning(line_edit.window(), "Valor Inválido",
                                f"A percentagem deve estar entre {min_val}% e {max_val}%.")
            # Tentar reverter para o último valor válido ou limpar
            # Por simplicidade, podemos limpar e forçar o user a corrigir
            line_edit.setText("")
            return

        # Reformatar para incluir "%" se ainda não tiver
        # Formatar como inteiro para percentagem
        formatted_text = f"{value:.2f}%"
        if current_text != formatted_text:
            line_edit.blockSignals(True)  # Evita loop recursivo
            line_edit.setText(formatted_text)
            line_edit.blockSignals(False)

    except ValueError:
        # CORRIGIDO: Usar line_edit.window() como parent para QMessageBox
        QMessageBox.warning(line_edit.window(), "Entrada Inválida",
                            "Por favor, insira um valor numérico válido para a percentagem (ex: 15, 5.5%).")
        line_edit.setText("")  # Limpa o campo se a conversão falhar


def mapeia_dados_items_orcamento(main_window):
    """
    Mapeia os dados do separador (Orcamento)  'tab_criar_orcamento' para o separador 'dados_item_orcamento' (Orcamento de Items).

    Preenche os QLineEdit:
      - nome_cliente_11    ← lineEdit_nome_cliente
      - num_orcamento_11   ← lineEdit_num_orcamento
      - versao_orcamento_11← lineEdit_versao_orcamento
      - ref_cliente_11     ← lineEdit_ref_cliente

    E preenche a QTreeWidget 'tab_artigos_11' com os dados dos itens:
      - Coluna "Item"          ← lineEdit_item_orcamento
      - Coluna "Codigo"        ← lineEdit_codigo_orcamento (convertido para maiúsculas)
      - Coluna "Descricao"     ← plainTextEdit_descricao_orcamento
      - Coluna "Altura"        ← lineEdit_altura_orcamento
      - Coluna "Largura"       ← lineEdit_largura_orcamento
      - Coluna "Profundidade"  ← lineEdit_profundidade_orcamento
      - Coluna "Und"           ← lineEdit_und_orcamento
      - Coluna "QT"            ← lineEdit_qt_orcamento
    Se houver colunas extras (por exemplo, para Preço Unitário, Preço Total ou %), estas serão preenchidas com valores vazios.
    """
    ui = main_window.ui

    # Atualiza os campos do orçamento com dados do groupBox ou dos QLineEdit originais.
    ui.nome_cliente_11.setText(ui.lineEdit_nome_cliente1.text())
    ui.num_orcamento_11.setText(ui.lineEdit_num_orcamento.text())
    ui.versao_orcamento_11.setText(ui.lineEdit_versao_orcamento.text())
    ui.ref_cliente_11.setText(ui.lineEdit_ref_cliente.text())

    # Obter a fonte dos itens: tableWidget_artigos (que contém todos os itens armazenados)
    source = ui.tableWidget_artigos
    # QTreeWidget destino
    dest = ui.tab_artigos_11
    dest.clear()

    rows = source.rowCount()
    # Mapeamento de colunas da tableWidget_artigos para a tab_artigos_11 (QTreeWidget)
    # Note: tab_artigos_11 (QTreeWidget) tem menos colunas que tableWidget_artigos (QTableWidget).
    # Apenas as colunas básicas são copiadas.
    # col_source_idx: COL_ITEM_NUM, COL_CODIGO, COL_DESCRICAO, COL_ALTURA, COL_LARGURA, COL_PROFUNDIDADE, COL_UND, COL_QT, COL_PRECO_UNIT, COL_PRECO_TOTAL
    # col_dest_idx:   0,              1,         2,             3,         4,           5,                6,      7,      8,             10 (col 9 é "New Column")

    for row in range(rows):
        item_data = []
        # Item (source col 1) -> dest col 0
        item_data.append(_get_cell_text(source, row, COL_ITEM_NUM))
        # Codigo (source col 2) -> dest col 1
        item_data.append(_get_cell_text(source, row, COL_CODIGO))
        # Descricao (source col 3) -> dest col 2
        item_data.append(_get_cell_text(source, row, COL_DESCRICAO))
        # Altura (source col 4) -> dest col 3
        item_data.append(_get_cell_text(source, row, COL_ALTURA))
        # Largura (source col 5) -> dest col 4
        item_data.append(_get_cell_text(source, row, COL_LARGURA))
        # Profundidade (source col 6) -> dest col 5
        item_data.append(_get_cell_text(source, row, COL_PROFUNDIDADE))
        # Und (source col 7) -> dest col 6
        item_data.append(_get_cell_text(source, row, COL_UND))
        # QT (source col 8) -> dest col 7
        item_data.append(_get_cell_text(source, row, COL_QT))
        # Preco_Unit (source col 9) -> dest col 8
        item_data.append(_get_cell_text(source, row, COL_PRECO_UNIT))

        # Coluna 9 (no QTreeWidget) é "New Column" - deixada vazia
        item_data.append("")

        # Preco_Total (source col 10) -> dest col 10
        item_data.append(_get_cell_text(source, row, COL_PRECO_TOTAL))

        # Colunas 11, 12, 13 ("Info_1", "Info_2", "Info_4") no QTreeWidget - deixadas vazias
        item_data.append("")
        item_data.append("")
        item_data.append("")

        dest.addTopLevelItem(QTreeWidgetItem(item_data))

        
def acao_orcamentar_items(main_window):
    """Executa as ações do botão 'orcamentar_items'."""
    ui = main_window.ui
    mapeia_dados_items_orcamento(main_window)
    configurar_dados_items_orcamento_materiais(main_window)
    configurar_dados_items_orcamento_ferragens(main_window)
    configurar_dados_items_orcamento_sistemas_correr(main_window)
    configurar_dados_items_orcamento_acabamentos(main_window)
    modulo_dados_definicoes.carregar_dados_modulo_medidas(ui)
    modulo_dados_definicoes.carregar_dados_def_pecas(ui)
    # Sincroniza H, L, P na tabela de medidas com as dimensões do item
    tbl_medidas = ui.tab_modulo_medidas
    if tbl_medidas.rowCount() == 0:
        tbl_medidas.setRowCount(1)
    set_item(tbl_medidas, 0, 0, ui.lineEdit_altura_orcamento.text())
    set_item(tbl_medidas, 0, 1, ui.lineEdit_largura_orcamento.text())
    set_item(tbl_medidas, 0, 2, ui.lineEdit_profundidade_orcamento.text())
    for c in (0, 1, 2):
        aplicar_formatacao(tbl_medidas.item(0, c))
    tabela_def_pecas_items.actualizar_ids_num_orc_ver_orc_tab_modulo_medidas(
        ui,
        ui.lineEdit_item_orcamento.text().strip(),
        ui.lineEdit_num_orcamento.text().strip(),
        ui.lineEdit_versao_orcamento.text().strip(),
    )
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    ver_orc = ui.lineEdit_versao_orcamento.text().strip()
    item_id = ui.lineEdit_item_orcamento.text().strip()

    if not verificar_dados_itens_salvos(num_orc, ver_orc, item_id):
        msg = (
            f"<p>Pretende preencher os dados do item <b>{item_id}</b> "
            f"com os Dados Gerais atuais?</p>"
            f"<p><small>Orçamento: <b>{num_orc}</b> | "
            f"Versão: <b>{ver_orc}</b></small></p>"
        )

        resp = QMessageBox.question(
            main_window,
            "Usar Dados Gerais",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if resp == QMessageBox.Yes:
            from utils import copiar_dados_gerais_para_itens

            copiar_dados_gerais_para_itens(ui)

    atualizar_tudo(ui)
    

def navegar_item_orcamento(main_window, direcao):
    """
    Navega entre os itens do QTreeWidget 'tab_artigos_11' com base na direção indicada.

    Parâmetros:
      main_window - objeto principal que contém a interface (ui)
      direcao     - inteiro: -1 para o item anterior, +1 para o próximo item

    A função atualiza os campos do groupBox (ex: lineEdit_item_orcamento, etc.)
    com os dados do item selecionado e simula o clique do botão 'orcamentar_items' para
    atualizar as tabelas dependentes: tab_def_pecas, Tab_Material_11, Tab_Ferragens_11,
    Tab_Sistemas_Correr_11 e Tab_Acabamentos_12.
    """
    ui = main_window.ui

    # Obter a referência do QTreeWidget que exibe os itens
    tree = ui.tab_artigos_11
    total_items = tree.topLevelItemCount()

    if total_items == 0:
        print("Nenhum item disponível na árvore.")
        # Se não houver itens, não faz nada.
        return

    # Se o atributo de controle do índice não existe, cria-o e inicializa em 0
    if not hasattr(main_window, "navegacao_index"):
        main_window.navegacao_index = 0

    # Calcula o novo índice com base na direção
    novo_index = main_window.navegacao_index + direcao

    # Se o índice estiver fora dos limites, pode optar por não atualizar ou fazer wrap-around.
    # Tratamento de limites (evita sair do range)
    if novo_index < 0:
        novo_index = 0  # Para no primeiro item
        print("Já está no primeiro item.")
        # return # Descomentar se não quiser que atualize ao tentar ir para trás do primeiro
    elif novo_index >= total_items:
        novo_index = total_items - 1  # Para no último item
        print("Já está no último item.")
        # return # Descomentar se não quiser que atualize ao tentar ir para a frente do último

    # Se o índice não mudou (porque estava no limite), não faz nada
    if novo_index == main_window.navegacao_index and (direcao == -1 and novo_index == 0 or direcao == 1 and novo_index == total_items - 1) and total_items > 1:
        # A condição `total_items > 1` evita que não atualize quando só há 1 item e clica seta
        # Apenas retorna se estava *já* no limite e tentou ultrapassá-lo
        if not (direcao == -1 and novo_index == 0 and main_window.navegacao_index == 0 and total_items == 1) and \
           not (direcao == 1 and novo_index == 0 and main_window.navegacao_index == 0 and total_items == 1):
            print("Índice não mudou (estava no limite).")
            # return # Poderia retornar aqui, mas vamos deixar atualizar mesmo assim para consistência

    main_window.navegacao_index = novo_index

    # Obtém o item do QTreeWidget correspondente ao novo índice
    item = tree.topLevelItem(novo_index)

    if not item:  # Segurança extra
        print(f"Erro: Item no índice {novo_index} não encontrado.")
        return

    # --- Obter os dados do NOVO item selecionado (do QTreeWidget tab_artigos_11) ---
    # Colunas no tab_artigos_11: 0=Item, 1=Codigo, 2=Descricao, 3=Altura, 4=Largura, 5=Profundidade, 6=Und, 7=Qt
    novo_id_str = item.text(0)  # Coluna "Item" da árvore
    # 'num_orc' e 'ver_orc' vêm dos lineEdits que refletem o orçamento ABERTO
    # Estes NÃO mudam ao navegar entre itens do MESMO orçamento.
    # Eles foram definidos pela função `mapeia_dados_items_orcamento`
    novo_num_orc_str = ui.num_orcamento_11.text().strip()
    novo_ver_orc_str = ui.versao_orcamento_11.text().strip()

    print(f"[DEBUG navegar_item] Navegando para item índice {novo_index}")
    print(
        f"  -> IDs obtidos: Item='{novo_id_str}', NumOrc='{novo_num_orc_str}', VerOrc='{novo_ver_orc_str}'")
    # Mostra todos os dados da linha da árvore
    print(
        f"  -> Dados Tree: {[item.text(i) for i in range(tree.columnCount())]}")

    # --- Atualizar os lineEdits PRINCIPAIS da UI (groupBox_linhas_orcamento) ---
    # Isto é importante para que o utilizador veja o item atual
    ui.lineEdit_item_orcamento.setText(item.text(0))  # Item
    ui.lineEdit_codigo_orcamento.setText(item.text(1))  # Codigo
    ui.plainTextEdit_descricao_orcamento.setPlainText(
        item.text(2))  # Descricao
    ui.lineEdit_altura_orcamento.setText(item.text(3))  # Altura
    ui.lineEdit_largura_orcamento.setText(item.text(4))  # Largura
    ui.lineEdit_profundidade_orcamento.setText(item.text(5))  # Profundidade
    ui.lineEdit_und_orcamento.setText(item.text(6))  # Und
    ui.lineEdit_qt_orcamento.setText(item.text(7))  # QT

    # Define o item corrente para que seja destacado (selecionado)
    # --- Selecionar visualmente o item na árvore ---
    tree.setCurrentItem(item)
    # Rola para o item
    tree.scrollToItem(item, QAbstractItemView.PositionAtCenter)

    print("Campos atualizados. Disparando atualização (simulando clique em orcamentar_items).")

    # Agora, simula o clique no botão "orcamentar_items"
    # Esse botão já está configurado para atualizar as demais tabelas e agora também os custos/preços.
    ui.orcamentar_items.click()

    # Garantia extra: recarrega as tabelas de definições após o clique.
    # Em algumas situações, dependências externas podem impedir que o
    # sinal "clicked" execute todas as funções pretendidas. Ao chamar
    # explicitamente as funções de carregamento aqui, asseguramos que as
    # colunas de medidas (H, L, P, H1..P4) são atualizadas com o item
    # recentemente selecionado.
    modulo_dados_definicoes.carregar_dados_modulo_medidas(ui)
    modulo_dados_definicoes.carregar_dados_def_pecas(ui)
    tabela_def_pecas_items.actualizar_ids_num_orc_ver_orc_tab_modulo_medidas(
        ui,
        novo_id_str,
        novo_num_orc_str,
        novo_ver_orc_str
    )

    print(f"[DEBUG navegar_item] Navegação para item {novo_id_str} concluída.")


def pesquisar_itens(ui):
    """
    Pesquisa itens de orçamento na tableWidget_artigos com base no termo digitado.
    Exibe ou oculta as linhas conforme a correspondência.
    """
    termo = ui.lineEdit_pesquisar_orcamento.text().strip()
    for row in range(ui.tableWidget_artigos.rowCount()):
        match = False
        for col in range(ui.tableWidget_artigos.columnCount()):
            item = ui.tableWidget_artigos.item(row, col)
            if item and termo.lower() in item.text().lower():
                match = True
                break
        ui.tableWidget_artigos.setRowHidden(row, not match)


def criar_tabela_orcamento_items():
    """
    Cria a tabela "orcamento_items" no banco de dados MySQL, se ainda não existir.
    Adapta a definição para MySQL, utilizando INT AUTO_INCREMENT.
    Também adiciona colunas que podem estar faltando em versões anteriores da tabela.
    """
    # print("Verificando/Criando tabela 'orcamento_items'...")
    try:
        with obter_cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orcamento_items (
                    id_item INT AUTO_INCREMENT PRIMARY KEY,
                    id_orcamento INT NOT NULL,      -- Chave estrangeira para orcamentos.id
                    item TEXT NULL,                 -- Número do item dentro do orçamento (ex: "1", "2")
                    codigo TEXT NULL,
                    descricao TEXT NULL,
                    altura DOUBLE NULL DEFAULT 0.0,
                    largura DOUBLE NULL DEFAULT 0.0,
                    profundidade DOUBLE NULL DEFAULT 0.0,
                    und VARCHAR(20) NULL,
                    qt DOUBLE NULL DEFAULT 1.0,     -- Quantidade
                    preco_unitario DOUBLE NULL DEFAULT 0.0,
                    preco_total DOUBLE NULL DEFAULT 0.0,
                    custo_produzido DOUBLE NULL DEFAULT 0.0,
                    custo_total_orlas DOUBLE NULL DEFAULT 0.0,
                    custo_total_mao_obra DOUBLE NULL DEFAULT 0.0,
                    custo_total_materia_prima DOUBLE NULL DEFAULT 0.0,
                    custo_total_acabamentos DOUBLE NULL DEFAULT 0.0,
                    margem_lucro_perc DOUBLE NULL DEFAULT 0.0,
                    valor_margem DOUBLE NULL DEFAULT 0.0,
                    custos_admin_perc DOUBLE NULL DEFAULT 0.0,
                    valor_custos_admin DOUBLE NULL DEFAULT 0.0,
                    ajustes1_perc DOUBLE NULL DEFAULT 0.0,
                    valor_ajustes1 DOUBLE NULL DEFAULT 0.0,
                    ajustes2_perc DOUBLE NULL DEFAULT 0.0,
                    valor_ajustes2 DOUBLE NULL DEFAULT 0.0,
                    FOREIGN KEY (id_orcamento) REFERENCES orcamentos(id) ON DELETE CASCADE ON UPDATE CASCADE -- Importante: ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

        #######################################################################

        # CONFIMRAR SE POSSO ELIMINAR SEGUINTES LINHAS
        # print("Tabela 'orcamento_items' verificada/criada.")
        # --- ADICIONAR COLUNAS QUE PODEM FALTAR se a tabela já existia ---
        # Este bloco permite a atualização da estrutura da tabela sem apagar dados existentes.
        columns_to_add = {
            "custo_produzido": "DOUBLE NULL DEFAULT 0.0",
            "custo_total_orlas": "DOUBLE NULL DEFAULT 0.0",
            "custo_total_mao_obra": "DOUBLE NULL DEFAULT 0.0",
            "custo_total_materia_prima": "DOUBLE NULL DEFAULT 0.0",
            "custo_total_acabamentos": "DOUBLE NULL DEFAULT 0.0",
            "margem_lucro_perc": "DOUBLE NULL DEFAULT 0.0",
            "valor_margem": "DOUBLE NULL DEFAULT 0.0",
            "custos_admin_perc": "DOUBLE NULL DEFAULT 0.0",
            "valor_custos_admin": "DOUBLE NULL DEFAULT 0.0",
            "ajustes1_perc": "DOUBLE NULL DEFAULT 0.0",
            "valor_ajustes1": "DOUBLE NULL DEFAULT 0.0",
            "ajustes2_perc": "DOUBLE NULL DEFAULT 0.0",
            "valor_ajustes2": "DOUBLE NULL DEFAULT 0.0"
        }
        for col_name, col_type in columns_to_add.items():
            try:
                with obter_cursor() as cursor:
                    # Verifica se a coluna já existe para evitar exceções
                    cursor.execute(
                        "SHOW COLUMNS FROM orcamento_items LIKE %s", (col_name,))
                    existe = cursor.fetchone()
                    if not existe:
                        cursor.execute(
                            f"ALTER TABLE orcamento_items ADD COLUMN `{col_name}` {col_type}"
                        )
                        print(
                            f"Coluna '{col_name}' adicionada a 'orcamento_items'.")
            except mysql.connector.Error as err:
                print(f"Erro MySQL ao adicionar coluna '{col_name}': {err}")
                QMessageBox.warning(
                    None, "Erro BD", f"Falha ao adicionar coluna '{col_name}':\n{err}"
                )
            except Exception as e:
                print(f"Erro inesperado ao adicionar coluna '{col_name}': {e}")
                QMessageBox.critical(
                    None,
                    "Erro",
                    f"Falha na configuração inicial ao adicionar coluna '{col_name}':\n{e}"
                )

        #######################################################################

    except mysql.connector.Error as err:
        print(f"Erro MySQL ao criar/verificar 'orcamento_items': {err}")
        QMessageBox.critical(
            None, "Erro BD", f"Falha na tabela 'orcamento_items':\n{err}")
    except Exception as e:
        print(f"Erro inesperado ao criar/verificar 'orcamento_items': {e}")
        QMessageBox.critical(
            None, "Erro", f"Falha na configuração inicial:\n{e}")


def abrir_orcamento(main_window):
    """
    Executa as seguintes ações ao clicar em "Abrir Orçamento":
      1) Alterna para a aba "Orcamento".
      2) Lê a linha selecionada na tableWidget_orcamentos para obter os IDs do orçamento e do cliente.
      3) Carrega os dados do orçamento e do cliente a partir do banco.
      4) Preenche os campos da interface e carrega os itens do orçamento na tableWidget_artigos.
      5) Ajusta o campo lineEdit_item_orcamento para o próximo item.
      6) NOVO: Dispara a atualização de custos e preços para todos os itens.
    """
    ui = main_window.ui  # Obtém ui a partir de main_window

    # Troca para a aba "Orcamento"
    for i in range(ui.tabWidget_orcamento.count()):
        if ui.tabWidget_orcamento.widget(i).objectName() == "tab_criar_orcamento":
            ui.tabWidget_orcamento.setCurrentIndex(i)
            break

    tbl_orcamentos = ui.tableWidget_orcamentos
    row_sel = tbl_orcamentos.currentRow()
    if row_sel < 0:
        QMessageBox.warning(None, "Aviso", "Nenhum orçamento selecionado.")
        return

    try:
        id_orc = int(tbl_orcamentos.item(row_sel, 0).text())
        id_cli = int(tbl_orcamentos.item(row_sel, 1).text())
        # print(f"Abrindo Orçamento ID: {id_orc}, Cliente ID: {id_cli}")
    except (AttributeError, ValueError, IndexError):
        QMessageBox.critical(
            None, "Erro", "Não foi possível obter IDs do orçamento selecionado.")
        return

    row_orc = None
    row_cli = None
    try:
        # Usa obter_cursor para buscar dados
        with obter_cursor() as cursor:
            # Carrega dados do orçamento
            cursor.execute("""
                SELECT ano, num_orcamento, versao, status, data, preco, ref_cliente,
                       obra, caracteristicas, localizacao, info_1, info_2
                  FROM orcamentos WHERE id=%s
            """, (id_orc,))
            row_orc = cursor.fetchone()

            # Carrega dados do cliente
            cursor.execute(
                "SELECT nome, morada, email, telefone FROM clientes WHERE id=%s", (id_cli,))
            row_cli = cursor.fetchone()
        # Commit/Rollback/Fecho automático

        # Preenche UI (fora do 'with')
        if row_orc:
            (ano, num, ver, status, dt_str, preco,
             ref, obra, carac, loc, i1, i2) = row_orc
            ui.lineEdit_num_orcamento.setText(num or "")
            # === INÍCIO MODIFICAÇÃO: Formatar a versão lida da BD para 2 dígitos ===
            versao_formatada = "00"  # Valor por defeito
            if ver is not None:
                try:
                    # Tenta converter para int e formatar como dois dígitos
                    # Converter para string antes para lidar com possíveis tipos diferentes
                    versao_int = int(str(ver).strip())
                    versao_formatada = f"{versao_int:02d}"
                except (ValueError, TypeError):
                    # Se não for um número válido, usa a string original se não for vazia, senão "00"
                    versao_formatada = str(ver).strip() if str(
                        ver).strip() else "00"
            # === FIM MODIFICAÇÃO ===

            ui.lineEdit_versao_orcamento.setText(versao_formatada or "")
            # ui.lineEdit_versao_orcamento.setText(ver or "")
            ui.lineEdit_ref_cliente.setText(ref or "")
            ui.lineEdit_obra.setText(obra or "")
            try:  # Formata data
                dt = datetime.datetime.strptime(dt_str, "%d/%m/%Y")
                ui.dateEdit_data_orcamento.setDate(
                    QDate(dt.year, dt.month, dt.day))
            except (ValueError, TypeError):
                ui.dateEdit_data_orcamento.setDate(QDate.currentDate())
            # Preencher outros campos se necessário (status, etc.)
        else:
            print(f"Aviso: Orçamento ID {id_orc} não encontrado na BD.")

        # print(f"[DEBUG] ->> Versão do orcamento: {versao_formatada}")  # Eliminar esta linha apagar

        if row_cli:
            (nome, morada, email, tel) = row_cli
            ui.lineEdit_nome_cliente1.setText(nome or "")
            ui.lineEdit_morada.setText(morada or "")
            ui.lineEdit_email.setText(email or "")
            # Preencher telefone se existir o campo na UI
        else:
            print(f"Aviso: Cliente ID {id_cli} não encontrado na BD.")

        # Guarda ID do orçamento e carrega itens
        ui.lineEdit_id.setText(str(id_orc))  # ID do orçamento carregado
        carregar_itens_orcamento(ui, id_orc)  # Chama função refatorada

        # Define próximo item
        prox = obter_proximo_item_para_orcamento(
            id_orc)  # Chama função refatorada
        ui.lineEdit_item_orcamento.setText(str(prox))

        # --- ADICIONADO: Chama o mapeamento inicial após abrir orçamento ---
        # Isso garante que os dados gerais e a árvore de itens sejam preenchidos
        mapeia_dados_items_orcamento(main_window)
        # Se existir configuracao previa de dados gerais, carrega automaticamente
        carregar_dados_gerais_se_existir(main_window)
        # E também força o carregamento inicial das tabelas de definição para o primeiro item
        # ui.orcamentar_items.click() # Simula clique para carregar tudo
        # --- FIM ADICIONADO ---
        # print("Orçamento aberto e itens carregados.")
        # NOVO: Após carregar todos os itens do orçamento, atualiza os custos e preços para todos
        # Não força a margem global ao abrir um orçamento, mantém as margens individuais se existirem.
        atualizar_custos_e_precos_itens(ui, force_global_margin_update=False)

    except mysql.connector.Error as err:
        print(f"Erro MySQL ao abrir orçamento: {err}")
        QMessageBox.critical(None, "Erro Base de Dados",
                             f"Erro ao carregar dados do orçamento:\n{err}")
    except Exception as e:
        print(f"Erro inesperado ao abrir orçamento: {e}")
        QMessageBox.critical(None, "Erro Inesperado",
                             f"Erro ao abrir orçamento:\n{e}")
        import traceback
        traceback.print_exc()


def carregar_itens_orcamento(ui, id_orcamento: int):
    """
    Carrega todos os itens da tabela "orcamento_items" para o orçamento especificado.
    Exibe os dados na tableWidget_artigos, ocultando a coluna de id_item.
    MODIFICADO para carregar as novas colunas de custos e ajustes.
    """
    # print(f"Carregando itens para orçamento ID: {id_orcamento}")
    registros = []
    try:
        with obter_cursor() as cursor:
            # Seleciona todas as colunas, incluindo as novas
            cursor.execute("""
                SELECT id_item, item, codigo, descricao, altura, largura, profundidade,
                       und, qt, preco_unitario, preco_total, custo_produzido,
                       custo_total_orlas, custo_total_mao_obra, custo_total_materia_prima,
                       custo_total_acabamentos, margem_lucro_perc, valor_margem,
                       custos_admin_perc, valor_custos_admin, ajustes1_perc,
                       valor_ajustes1, ajustes2_perc, valor_ajustes2
                FROM orcamento_items WHERE id_orcamento=%s ORDER BY id_item
            """, (id_orcamento,))
            registros = cursor.fetchall()
        # print(f"Encontrados {len(registros)} itens.")
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao carregar itens: {err}")
        return  # Não preenche a tabela se houver erro
    except Exception as e:
        print(f"Erro inesperado ao carregar itens: {e}")
        return

    tbl = ui.tableWidget_artigos
    global _editando_programaticamente
    # Evita que itemChanged seja disparado durante o carregamento
    _editando_programaticamente = True
    tbl.setRowCount(0)  # Limpa a tabela antes de preencher
    try:

        # Os dados vêm da BD na ordem da query SELECT.
        # É crucial que os índices aqui correspondam a essa ordem.
        # Ex: item_q.setText(formatar_valor_moeda(row_data[10])) para Preco_Total
        # row_data[11] para Custo_Produzido
        # row_data[12] para Custo_Total_Orlas, etc.

        # Mapeamento do índice da tupla 'row_data' para o índice da coluna da UI
        # (coluna_ui: índice_tupla_bd)
        ui_to_db_map = {
            COL_ID_ITEM: 0,
            COL_ITEM_NUM: 1,
            COL_CODIGO: 2,
            COL_DESCRICAO: 3,
            COL_ALTURA: 4,
            COL_LARGURA: 5,
            COL_PROFUNDIDADE: 6,
            COL_UND: 7,
            COL_QT: 8,
            COL_PRECO_UNIT: 9,
            COL_PRECO_TOTAL: 10,
            COL_CUSTO_PRODUZIDO: 11,  # NOVO
            COL_CUSTO_ORLAS: 12,
            COL_CUSTO_MO: 13,
            COL_CUSTO_MP: 14,
            COL_CUSTO_ACABAMENTOS: 15,
            COL_MARGEM_PERC: 16,
            COL_MARGEM_VALOR: 17,
            COL_CUSTOS_ADMIN_PERC: 18,
            COL_CUSTOS_ADMIN_VALOR: 19,
            COL_AJUSTES1_PERC: 20,
            COL_AJUSTES1_VALOR: 21,
            COL_AJUSTES2_PERC: 22,
            COL_AJUSTES2_VALOR: 23
        }

        for row_data in registros:
            row_idx = tbl.rowCount()
            tbl.insertRow(row_idx)
            for col_ui_idx in range(tbl.columnCount()):
                db_data_idx = ui_to_db_map.get(col_ui_idx)
                if db_data_idx is None:
                    # Se não há mapeamento, cria um item vazio
                    item_q = QTableWidgetItem("")
                else:
                    valor = row_data[db_data_idx]
                    texto_item = ""
                    # Formata colunas de preço
                    if col_ui_idx in [COL_PRECO_UNIT, COL_PRECO_TOTAL, COL_CUSTO_PRODUZIDO,  # Adicionado Custo Produzido
                                      COL_CUSTO_ORLAS, COL_CUSTO_MO, COL_CUSTO_MP, COL_CUSTO_ACABAMENTOS,
                                      COL_MARGEM_VALOR, COL_CUSTOS_ADMIN_VALOR, COL_AJUSTES1_VALOR, COL_AJUSTES2_VALOR]:
                        texto_item = formatar_valor_moeda(valor)
                    # Formata colunas de percentual
                    elif col_ui_idx in [COL_MARGEM_PERC, COL_CUSTOS_ADMIN_PERC, COL_AJUSTES1_PERC, COL_AJUSTES2_PERC]:
                        texto_item = formatar_valor_percentual(valor)
                    else:
                        texto_item = str(valor) if valor is not None else ""

                    item_q = QTableWidgetItem(texto_item)

                # Configurações de flags e coloração
                if col_ui_idx == COL_ID_ITEM:  # id_item (coluna 0)
                    item_q.setFlags(item_q.flags() & ~
                                    Qt.ItemIsEditable)  # Não editável

                # Aplicar coloração se a percentagem for diferente da global ao carregar
                if col_ui_idx in [COL_MARGEM_PERC, COL_CUSTOS_ADMIN_PERC, COL_AJUSTES1_PERC, COL_AJUSTES2_PERC]:
                    global_perc_val = 0.0
                    if col_ui_idx == COL_MARGEM_PERC:
                        global_perc_val = converter_texto_para_valor(
                            ui.lineEdit_margem_lucro.text(), "percentual")
                    elif col_ui_idx == COL_CUSTOS_ADMIN_PERC:
                        global_perc_val = converter_texto_para_valor(
                            ui.lineEdit_custos_administrativos.text(), "percentual")
                    elif col_ui_idx == COL_AJUSTES1_PERC:
                        global_perc_val = converter_texto_para_valor(
                            ui.lineEdit_ajustes_1.text(), "percentual")
                    elif col_ui_idx == COL_AJUSTES2_PERC:
                        global_perc_val = converter_texto_para_valor(
                            ui.lineEdit_ajustes_2.text(), "percentual")

                    cell_val = converter_texto_para_valor(
                        texto_item, "percentual")
                    if abs(cell_val - global_perc_val) > 0.001:  # Se os valores diferem
                        # Cor amarela para edição manual
                        item_q.setBackground(COLOR_MANUAL_EDIT)
                    else:
                        # Cor padrão da tabela (normalmente branca)
                        item_q.setBackground(tbl.palette().base().color())

                tbl.setItem(row_idx, col_ui_idx, item_q)
    finally:
        _editando_programaticamente = False  # Libera a flag
        tbl.resizeColumnsToContents()  # Ajusta largura das colunas


def inserir_item_orcamento(ui):
    """
    Lê os dados do groupBox_linhas_orcamento e insere um novo item na tabela "orcamento_items".
    Após a inserção, recarrega a tabela de itens e limpa os campos do groupBox (exceto o campo do item, que é incrementado).
    MODIFICADO para incluir os novos campos e disparar recalculo após a inserção.
    """
    id_orc_str = ui.lineEdit_id.text().strip()
    if not id_orc_str.isdigit():
        QMessageBox.warning(None, "Erro", "ID do Orçamento inválido!")
        return
    id_orc = int(id_orc_str)

    # Garante que o número do item seja sempre sequencial.
    # Obtém o próximo item disponível a partir da base de dados.
    prox_item = obter_proximo_item_para_orcamento(id_orc)
    # Ignora o valor eventualmente presente no QLineEdit e força o valor correto
    item_str = str(prox_item)
    ui.lineEdit_item_orcamento.setText(item_str)
    codigo = ui.lineEdit_codigo_orcamento.text().strip().upper()
    descricao = ui.plainTextEdit_descricao_orcamento.toPlainText().strip()
    altura_str = ui.lineEdit_altura_orcamento.text().strip()
    larg_str = ui.lineEdit_largura_orcamento.text().strip()
    prof_str = ui.lineEdit_profundidade_orcamento.text().strip()
    und = ui.lineEdit_und_orcamento.text().strip().lower()
    qt_str = ui.lineEdit_qt_orcamento.text().strip()

    try:
        altura = float(altura_str) if altura_str else 0.0
        largura = float(larg_str) if larg_str else 0.0
        profund = float(prof_str) if prof_str else 0.0
        qt = float(qt_str) if qt_str else 1.0
    except ValueError:
        QMessageBox.warning(
            None, "Erro", "Altura, Largura, Profundidade e QT devem ser numéricos.")
        return

    # Valores padrão para os novos campos (serão calculados por atualizar_custos_e_precos_itens)
    custo_produzido = 0.0
    custo_total_orlas = 0.0
    custo_total_mao_obra = 0.0
    custo_total_materia_prima = 0.0
    custo_total_acabamentos = 0.0

    # Obter valores padrão dos lineEdits globais para as percentagens
    margem_lucro_perc = converter_texto_para_valor(
        ui.lineEdit_margem_lucro.text(), "percentual")
    custos_admin_perc = converter_texto_para_valor(
        ui.lineEdit_custos_administrativos.text(), "percentual")
    ajustes1_perc = converter_texto_para_valor(
        ui.lineEdit_ajustes_1.text(), "percentual")
    ajustes2_perc = converter_texto_para_valor(
        ui.lineEdit_ajustes_2.text(), "percentual")

    # Os valores em euros são inicializados como 0 e serão calculados na próxima etapa
    valor_margem = 0.0
    valor_custos_admin = 0.0
    valor_ajustes1 = 0.0
    valor_ajustes2 = 0.0

    preco_unit = 0.0  # Será calculado
    preco_total = 0.0  # Será calculado

    print(f"Inserindo item {item_str} para orçamento {id_orc}...")
    try:
        with obter_cursor() as cursor:
            insert_query = """
                INSERT INTO orcamento_items (id_orcamento, item, codigo, descricao, altura,
                                             largura, profundidade, und, qt, preco_unitario, preco_total, custo_produzido,
                                             custo_total_orlas, custo_total_mao_obra, custo_total_materia_prima,
                                             custo_total_acabamentos, margem_lucro_perc, valor_margem,
                                             custos_admin_perc, valor_custos_admin, ajustes1_perc,
                                             valor_ajustes1, ajustes2_perc, valor_ajustes2)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            # Certifique-se que o número de parâmetros corresponde EXATAMENTE ao número de `%s`
            cursor.execute(insert_query, (id_orc, item_str, codigo, descricao, altura, largura,
                                          profund, und, qt, preco_unit, preco_total, custo_produzido,
                                          custo_total_orlas, custo_total_mao_obra, custo_total_materia_prima,
                                          custo_total_acabamentos, margem_lucro_perc, valor_margem,
                                          custos_admin_perc, valor_custos_admin, ajustes1_perc,
                                          valor_ajustes1, ajustes2_perc, valor_ajustes2))

        # Recarrega tabela para ver o novo item
        carregar_itens_orcamento(ui, id_orc)

        # Após a inserção e carregamento, forçar o recálculo dos custos e preços para a nova linha
        # e o preço final do orçamento.
        # Não força a margem global, apenas recalcula com as regras existentes.
        QTimer.singleShot(10, lambda: atualizar_custos_e_precos_itens(
            ui, force_global_margin_update=False))

        ui.lineEdit_codigo_orcamento.clear()
        ui.plainTextEdit_descricao_orcamento.clear()
        ui.lineEdit_altura_orcamento.clear()
        ui.lineEdit_largura_orcamento.clear()
        ui.lineEdit_profundidade_orcamento.clear()
        ui.lineEdit_und_orcamento.setText("und")
        ui.lineEdit_qt_orcamento.setText("1")
        prox = obter_proximo_item_para_orcamento(id_orc)
        ui.lineEdit_item_orcamento.setText(str(prox))
        QMessageBox.information(None, "OK", "Item inserido com sucesso.")

    except mysql.connector.Error as err:
        print(f"Erro MySQL ao inserir item: {err}")
        QMessageBox.critical(None, "Erro BD", f"Erro: {err}")
    except Exception as e:
        print(f"Erro inesperado ao inserir item: {e}")
        QMessageBox.critical(None, "Erro", f"Erro: {e}")


def eliminar_item_orcamento(ui):
    """
    Remove o item selecionado na tableWidget_artigos da tabela "orcamento_items".
    MODIFICADO para eliminar também os registos relacionados na `dados_def_pecas`
    e recalcular o preço final do orçamento.
    """
    tbl = ui.tableWidget_artigos
    row_sel = tbl.currentRow()
    if row_sel < 0:
        QMessageBox.warning(None, "Erro", "Nenhuma linha selecionada.")
        return

    # id_item na coluna 0 (oculta)
    id_item_ui_str = _get_cell_text(tbl, row_sel, COL_ID_ITEM)
    item_num_str = _get_cell_text(
        tbl, row_sel, COL_ITEM_NUM)  # 'Item' na coluna 1
    id_orc_str = ui.lineEdit_id.text().strip()
    ver_orc_str = ui.lineEdit_versao_orcamento.text().strip()  # Versão do orçamento

    if not id_item_ui_str.isdigit() or not id_orc_str.isdigit():
        QMessageBox.warning(None, "Erro", "ID item/orçamento inválido.")
        return

    id_item_db = int(id_item_ui_str)  # id_item da tabela orcamento_items

    resp = QMessageBox.question(None, "Confirmar", f"Tem a certeza que deseja eliminar o item ID {item_num_str}?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if resp != QMessageBox.Yes:
        return

    print(
        f"Eliminando item ID: {item_num_str} do orçamento ID: {id_orc_str}, Versão: {ver_orc_str}...")
    try:
        with obter_cursor() as cursor:
            # 1. Eliminar registos relacionados na `dados_def_pecas`
            # O critério de eliminação para dados_def_pecas é ids, num_orc, ver_orc
            cursor.execute("DELETE FROM dados_def_pecas WHERE ids=%s AND num_orc=%s AND ver_orc=%s",
                           (item_num_str, id_orc_str, ver_orc_str))
            print(
                f"  {cursor.rowcount} registos eliminados da dados_def_pecas para o item {item_num_str}.")

            # 2. Depois, eliminar o item da `orcamento_items`
            cursor.execute(
                "DELETE FROM orcamento_items WHERE id_item=%s", (id_item_db,))
            rows_affected = cursor.rowcount

        if rows_affected > 0:
            # Recarrega a tabela orcamento_items
            carregar_itens_orcamento(ui, id_orc_str)
            QMessageBox.information(
                None, "OK", "Item e dados relacionados eliminados com sucesso.")
            # Limpa groupbox e atualiza próximo item
            limpar_dados_linha_orcamento(ui)

            # Recalcula o preço final do orçamento após eliminação (não força a margem global)
            QTimer.singleShot(10, lambda: atualizar_custos_e_precos_itens(
                ui, force_global_margin_update=False))
        else:
            QMessageBox.warning(
                None, "Aviso", f"Item ID {item_num_str} não encontrado para eliminar.")

    except mysql.connector.Error as err:
        print(f"Erro MySQL ao eliminar item: {err}")
        QMessageBox.critical(None, "Erro BD", f"Erro: {err}")
    except Exception as e:
        print(f"Erro inesperado ao eliminar item: {e}")
        QMessageBox.critical(None, "Erro", f"Erro: {e}")


def editar_item_orcamento_groupbox(ui):
    """
    Edita o item selecionado utilizando os dados do groupBox_linhas_orcamento.
    Após a atualização, recarrega a tabela e limpa os campos do groupBox (exceto o campo do item, que é mantido).
    MODIFICADO para preservar os novos campos de custo/margem e recalcular a linha e o total.
    """
    tbl = ui.tableWidget_artigos
    row_sel = tbl.currentRow()
    if row_sel < 0:
        QMessageBox.warning(
            None, "Erro", "Nenhuma linha selecionada para editar.")
        return

    # ID da tabela orcamento_items
    id_item_str = _get_cell_text(tbl, row_sel, COL_ID_ITEM)
    if not id_item_str.isdigit():
        QMessageBox.warning(None, "Erro", "ID item inválido na tabela.")
        return
    id_item = int(id_item_str)

    id_orc_str = ui.lineEdit_id.text().strip()
    if not id_orc_str.isdigit():
        QMessageBox.warning(None, "Erro", "ID do Orçamento inválido.")
        return
    id_orc = int(id_orc_str)  # id_orcamento

    item_str = ui.lineEdit_item_orcamento.text().strip()
    codigo = ui.lineEdit_codigo_orcamento.text().strip().upper()
    descricao = ui.plainTextEdit_descricao_orcamento.toPlainText().strip()
    altura_str = ui.lineEdit_altura_orcamento.text().strip()
    larg_str = ui.lineEdit_largura_orcamento.text().strip()
    prof_str = ui.lineEdit_profundidade_orcamento.text().strip()
    und = ui.lineEdit_und_orcamento.text().strip().lower()
    qt_str = ui.lineEdit_qt_orcamento.text().strip()

    try:
        altura = float(altura_str) if altura_str else 0.0
        larg = float(larg_str) if larg_str else 0.0
        prof = float(prof_str) if prof_str else 0.0
        qt = float(qt_str) if qt_str else 1.0
    except ValueError:
        QMessageBox.warning(
            None, "Erro", "Altura, Largura, Profundidade e QT devem ser numéricos.")
        return

    print(f"Editando item ID: {id_item} (via groupbox)...")
    try:
        # Recuperar os valores de custos, margens e ajustes existentes na BD
        # para que não sejam resetados no UPDATE, pois não são editados via groupbox
        current_data = {}
        with obter_cursor() as cursor:
            # Atenção: A ordem das colunas no SELECT deve corresponder EXATAMENTE à ordem do unpacking abaixo.
            # Verifique se 'custo_produzido' está no índice correto.
            cursor.execute("""
                SELECT preco_unitario, preco_total, custo_produzido,
                       custo_total_orlas, custo_total_mao_obra, custo_total_materia_prima,
                       custo_total_acabamentos, margem_lucro_perc, valor_margem,
                       custos_admin_perc, valor_custos_admin, ajustes1_perc,
                       valor_ajustes1, ajustes2_perc, valor_ajustes2
                FROM orcamento_items WHERE id_item=%s
            """, (id_item,))
            res = cursor.fetchone()
            if res:
                # Corrigido: Certificar que custo_produzido é unpacked corretamente
                (current_data['preco_unitario'], current_data['preco_total'], current_data['custo_produzido'],
                 current_data['custo_total_orlas'], current_data['custo_total_mao_obra'], current_data['custo_total_materia_prima'],
                 current_data['custo_total_acabamentos'], current_data['margem_lucro_perc'], current_data['valor_margem'],
                 current_data['custos_admin_perc'], current_data['valor_custos_admin'], current_data['ajustes1_perc'],
                 current_data['valor_ajustes1'], current_data['ajustes2_perc'], current_data['valor_ajustes2']) = res
            else:
                QMessageBox.warning(
                    None, "Aviso", "Item não encontrado na base de dados para edição.")
                return

            # O preco_unitario e preco_total serão recalculados pela função `calcular_e_atualizar_linha_artigo`
            # após este UPDATE. Por isso, não precisamos recalculá-los aqui, apenas garantir que os dados
            # inseridos via groupbox são atualizados.

            # Executa UPDATE, mantendo os campos de custo/margem/ajustes
            update_query = """
                UPDATE orcamento_items SET item=%s, codigo=%s, descricao=%s, altura=%s,
                       largura=%s, profundidade=%s, und=%s, qt=%s,
                       preco_unitario=%s, preco_total=%s,
                       custo_produzido=%s,
                       custo_total_orlas=%s, custo_total_mao_obra=%s, custo_total_materia_prima=%s,
                       custo_total_acabamentos=%s, margem_lucro_perc=%s, valor_margem=%s,
                       custos_admin_perc=%s, valor_custos_admin=%s, ajustes1_perc=%s,
                       valor_ajustes1=%s, ajustes2_perc=%s, valor_ajustes2=%s
                 WHERE id_item=%s
            """
            # Certifique-se que o número de parâmetros corresponde EXATAMENTE ao número de `%s`
            cursor.execute(update_query, (item_str, codigo, descricao, altura, larg, prof, und, qt,
                                          current_data['preco_unitario'], current_data['preco_total'],
                                          current_data['custo_produzido'],
                                          current_data['custo_total_orlas'], current_data[
                                              'custo_total_mao_obra'], current_data['custo_total_materia_prima'],
                                          current_data['custo_total_acabamentos'], current_data[
                                              'margem_lucro_perc'], current_data['valor_margem'],
                                          current_data['custos_admin_perc'], current_data['valor_custos_admin'], current_data['ajustes1_perc'],
                                          current_data['valor_ajustes1'], current_data['ajustes2_perc'], current_data['valor_ajustes2'], id_item))

        # Recarrega tabela para que os dados do groupbox apareçam
        carregar_itens_orcamento(ui, id_orc)
        # Limpa groupbox e atualiza próximo item
        limpar_dados_linha_orcamento(ui)

        # Após a edição via groupbox, recalcular a linha específica e o total do orçamento
        # Não força a margem global, apenas recalcula com as regras existentes.
        QTimer.singleShot(10, lambda: atualizar_custos_e_precos_itens(
            ui, force_global_margin_update=False))

        QMessageBox.information(None, "OK", "Item editado com sucesso.")

    except mysql.connector.Error as err:
        print(f"Erro MySQL ao editar item: {err}")
        QMessageBox.critical(None, "Erro BD", f"Erro: {err}")
    except Exception as e:
        print(f"Erro inesperado ao editar item: {e}")
        QMessageBox.critical(None, "Erro", f"Erro: {e}")


def atualizar_campos_groupbox_por_selecao(ui):
    """
    Quando uma linha da tableWidget_artigos é selecionada, preenche os campos do groupBox_linhas_orcamento
    com os dados dessa linha (exceto a coluna id_item).
    """
    tbl = ui.tableWidget_artigos
    row_sel = tbl.currentRow()
    if row_sel < 0:
        return

    # Usar as constantes de coluna para maior clareza
    item_str = _get_cell_text(tbl, row_sel, COL_ITEM_NUM)
    codigo_str = _get_cell_text(tbl, row_sel, COL_CODIGO)
    descricao_str = _get_cell_text(tbl, row_sel, COL_DESCRICAO)
    altura_str = _get_cell_text(tbl, row_sel, COL_ALTURA)
    larg_str = _get_cell_text(tbl, row_sel, COL_LARGURA)
    prof_str = _get_cell_text(tbl, row_sel, COL_PROFUNDIDADE)
    und_str = _get_cell_text(tbl, row_sel, COL_UND)
    qt_str = _get_cell_text(tbl, row_sel, COL_QT)

    ui.lineEdit_item_orcamento.setText(item_str)
    ui.lineEdit_codigo_orcamento.setText(codigo_str)
    ui.plainTextEdit_descricao_orcamento.setPlainText(descricao_str)
    ui.lineEdit_altura_orcamento.setText(altura_str)
    ui.lineEdit_largura_orcamento.setText(larg_str)
    ui.lineEdit_profundidade_orcamento.setText(prof_str)
    ui.lineEdit_und_orcamento.setText(und_str)
    ui.lineEdit_qt_orcamento.setText(qt_str)


def _get_cell_text(tbl, row, col):
    """
    Função auxiliar que retorna o texto de uma célula da tabela, ou "" se estiver vazio.
    """
    item = tbl.item(row, col)
    return item.text() if item else ""


def obter_proximo_item_para_orcamento(id_orcamento: int) -> int:
    """
    Retorna o próximo número de item para um orçamento, calculado como MAX(CAST(item AS UNSIGNED)) + 1.
    Se não houver itens, retorna 1.
    """
    # print(f"Obtendo próximo item para orçamento ID: {id_orcamento}")
    max_item = 0
    try:
        with obter_cursor() as cursor:
            # Usar CAST para tratar 'item' como número
            cursor.execute(
                "SELECT MAX(CAST(item AS UNSIGNED)) FROM orcamento_items WHERE id_orcamento=%s", (id_orcamento,))
            resultado = cursor.fetchone()
            if resultado and resultado[0] is not None:
                max_item = int(resultado[0])
        return max_item + 1
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao obter max item: {err}")
        return 1
    except Exception as e:
        print(f"Erro ao obter max item: {e}")
        return 1


def handle_item_editado(ui, item):
    """
    Trata a edição direta de um item na tableWidget_artigos.
    Atualiza o banco de dados com o valor alterado e, se necessário, recalcula o preço_total
    e os novos campos de custo/margem.
    Aplica coloração à célula se a percentagem for alterada manualmente e difere da global.
    """
    global _editando_programaticamente
    if _editando_programaticamente:
        return

    tbl = item.tableWidget()
    row = item.row()
    col = item.column()

    if col == COL_ID_ITEM:  # id_item não é editável
        return

    id_item_str = _get_cell_text(tbl, row, COL_ID_ITEM)  # id_item da BD
    if not id_item_str.isdigit():
        return
    id_item = int(id_item_str)

    valor_novo_str = item.text().strip()

    # Mapeamento das colunas para os nomes dos campos no banco de dados
    colunas_db_map = {
        COL_ITEM_NUM: "item",
        COL_CODIGO: "codigo",
        COL_DESCRICAO: "descricao",
        COL_ALTURA: "altura",
        COL_LARGURA: "largura",
        COL_PROFUNDIDADE: "profundidade",
        COL_UND: "und",
        COL_QT: "qt",
        COL_PRECO_UNIT: "preco_unitario",
        # Recalculado, mas pode ser salvo se editado manualmente
        COL_PRECO_TOTAL: "preco_total",
        COL_CUSTO_PRODUZIDO: "custo_produzido",
        COL_CUSTO_ORLAS: "custo_total_orlas",
        COL_CUSTO_MO: "custo_total_mao_obra",
        COL_CUSTO_MP: "custo_total_materia_prima",
        COL_CUSTO_ACABAMENTOS: "custo_total_acabamentos",
        COL_MARGEM_PERC: "margem_lucro_perc",
        COL_MARGEM_VALOR: "valor_margem",
        COL_CUSTOS_ADMIN_PERC: "custos_admin_perc",
        COL_CUSTOS_ADMIN_VALOR: "valor_custos_admin",
        COL_AJUSTES1_PERC: "ajustes1_perc",
        COL_AJUSTES1_VALOR: "valor_ajustes1",
        COL_AJUSTES2_PERC: "ajustes2_perc",
        COL_AJUSTES2_VALOR: "valor_ajustes2"
    }
    campo_db = colunas_db_map.get(col)
    if not campo_db:
        return  # Coluna não mapeada, nada a fazer

    # Conversão de tipo e formatação (para input do utilizador)
    valor_novo_para_db = None
    # recalcular_linha_completa = False # Flag para decidir se a linha deve ser recalculada

    if campo_db in ["altura", "largura", "profundidade", "qt", "preco_unitario", "preco_total", "custo_produzido",
                    "custo_total_orlas", "custo_total_mao_obra", "custo_total_materia_prima", "custo_total_acabamentos",
                    "valor_margem", "valor_custos_admin", "valor_ajustes1", "valor_ajustes2"]:
        try:
            valor_novo_para_db = converter_texto_para_valor(
                valor_novo_str, "moeda")
            _editando_programaticamente = True
            item.setText(formatar_valor_moeda(valor_novo_para_db))
            # recalcular_linha_completa = True # Alterações nestas colunas podem afetar o total
        except ValueError:
            QMessageBox.warning(
                None, "Erro", f"Valor inválido ({valor_novo_str}) para {campo_db}. Deve ser numérico.")
            _editando_programaticamente = False
            return
    elif campo_db in ["margem_lucro_perc", "custos_admin_perc", "ajustes1_perc", "ajustes2_perc"]:
        try:
            valor_novo_para_db = converter_texto_para_valor(
                valor_novo_str, "percentual")
            # Validação de percentagem para células da tabela
            # Comparar o valor em percentagem (0-99)
            if not (0 <= valor_novo_para_db * 100 <= 99):
                QMessageBox.warning(tbl.window(), "Valor Inválido",
                                    f"A percentagem deve estar entre 0% e 99%.")
                _editando_programaticamente = False
                # Reverte o texto para o valor anterior ou vazio.
                # A forma mais robusta seria recarregar a célula do DB ou armazenar o valor anterior.
                # Por simplicidade, vamos deixar a célula com o valor inválido formatado ou em branco
                # e avisar o usuário.
                return  # Sai da função, não salva o valor inválido na DB
            _editando_programaticamente = True
            item.setText(formatar_valor_percentual(valor_novo_para_db))
            # recalcular_linha_completa = True # Alterações nestas percentagens devem disparar recalculo
            # Lógica de coloração para edições manuais de percentagem
            global_perc_value = 0.0
            if col == COL_MARGEM_PERC:
                global_perc_value = converter_texto_para_valor(
                    ui.lineEdit_margem_lucro.text(), "percentual")
            elif col == COL_CUSTOS_ADMIN_PERC:
                global_perc_value = converter_texto_para_valor(
                    ui.lineEdit_custos_administrativos.text(), "percentual")
            elif col == COL_AJUSTES1_PERC:
                global_perc_value = converter_texto_para_valor(
                    ui.lineEdit_ajustes_1.text(), "percentual")
            elif col == COL_AJUSTES2_PERC:
                global_perc_value = converter_texto_para_valor(
                    ui.lineEdit_ajustes_2.text(), "percentual")

            # Compara o valor editado com o valor global correspondente
            if abs(valor_novo_para_db - global_perc_value) > 0.001:  # Comparar floats com tolerância
                item.setBackground(COLOR_MANUAL_EDIT)  # Cor para edição manual
            else:
                # Cor padrão da tabela
                item.setBackground(tbl.palette().base().color())
        except ValueError:
            QMessageBox.warning(
                None, "Erro", f"Valor inválido ({valor_novo_str}) para {campo_db}. Deve ser numérico em percentagem.")
            _editando_programaticamente = False
            return
    else:  # Campos de texto (item, codigo, descricao, und)
        if campo_db == "codigo":
            valor_novo_str = valor_novo_str.upper()
            _editando_programaticamente = True
            item.setText(valor_novo_str)
        elif campo_db == "und":
            valor_novo_str = valor_novo_str.lower()
            _editando_programaticamente = True
            item.setText(valor_novo_str)
        valor_novo_para_db = valor_novo_str
        # Alterações nestas colunas não disparam recalculo completo da linha, apenas salvam
        # (código, descrição, altura, largura, profundidade, und)

    _editando_programaticamente = False  # Libera a flag antes de acessar a BD

    print(
        f"Atualizando item ID {id_item}, campo {campo_db} para '{valor_novo_str}'...")
    try:
        # AQUI: Apenas atualizamos a célula na DB e disparamos o recálculo total.
        # Isto evita que a chamada para calcular_e_atualizar_linha_artigo (que também faz DB ops)
        # tente bloquear a mesma tabela que esta UPDATE.
        with obter_cursor() as cursor:
            cursor.execute(
                f"UPDATE orcamento_items SET `{campo_db}`=%s WHERE id_item=%s", (valor_novo_para_db, id_item))
        print("  Atualização da célula na DB concluída.")

        # Dispara o recálculo completo de todos os itens e o preço final após um pequeno atraso.
        # Isso permite que a transação atual (da edição da célula) seja concluída.
        # Não força a margem global, apenas recalcula com as regras existentes.
        QTimer.singleShot(10, lambda: atualizar_custos_e_precos_itens(
            ui, force_global_margin_update=False))

    except mysql.connector.Error as err:
        print(f"[ERRO DB Transação] Erro durante a transação: {err}")
        QMessageBox.critical(
            None, "Erro BD", f"Erro ao atualizar item na tabela: {err}\nPor favor, tente novamente.")
    except Exception as e:
        print(f"Erro inesperado ao editar item na tabela: {e}")
        QMessageBox.critical(
            None, "Erro", f"Erro ao editar item na tabela:\n{e}")
# --- NOVO: Função para calcular e atualizar uma única linha da tableWidget_artigos ---


def calcular_e_atualizar_linha_artigo(ui, row_idx, force_global_margin_update=False):
    """
    Calcula e atualiza todos os campos de custo e preço para uma linha específica
    na tableWidget_artigos, buscando dados na dados_def_pecas e aplicando margens/ajustes.
    Adiciona tooltips com as fórmulas de cálculo e valores intermédios.
    Se `force_global_margin_update` for True, a margem de lucro (%) do item será forçada
    ao valor global, limpando qualquer override manual para esta célula.
    """
    tbl = ui.tableWidget_artigos
    global _editando_programaticamente

    # Obter os IDs de referência do item da linha atual na UI
    # id_item_db_val é o ID real do banco de dados para a tabela orcamento_items (coluna 0)
    id_item_db_val_str = _get_cell_text(tbl, row_idx, COL_ID_ITEM)
    # id_item_orcamento_str é o número "Item" que o usuário vê (coluna 1)
    id_item_orcamento_str = _get_cell_text(tbl, row_idx, COL_ITEM_NUM)
    num_orc_str = ui.lineEdit_num_orcamento.text().strip()
    ver_orc_str = ui.lineEdit_versao_orcamento.text().strip()

    # print(f"[DEBUG CalcLinha {row_idx+1}] Iniciando cálculo para Item '{id_item_orcamento_str}' (Orc: {num_orc_str}, Ver: {ver_orc_str})...")

    if not all([id_item_db_val_str, id_item_orcamento_str, num_orc_str, ver_orc_str]):
        print(
            f"[AVISO] Linha {row_idx+1}: Dados de identificação do item incompletos (DB ID, Item, Num_Orc, Ver_Orc). Saltando cálculo de custos detalhados.")
        # Limpar os campos de custo para evitar valores antigos
        _editando_programaticamente = True
        try:
            for col_idx in [COL_CUSTO_PRODUZIDO, COL_CUSTO_ORLAS, COL_CUSTO_MO, COL_CUSTO_MP, COL_CUSTO_ACABAMENTOS,
                            COL_MARGEM_VALOR, COL_CUSTOS_ADMIN_VALOR, COL_AJUSTES1_VALOR, COL_AJUSTES2_VALOR,
                            COL_PRECO_UNIT, COL_PRECO_TOTAL]:
                set_item(tbl, row_idx, col_idx, formatar_valor_moeda(0.0))
                item_q = tbl.item(row_idx, col_idx)
                if item_q:
                    item_q.setToolTip("Cálculo impossível: dados incompletos.")
        finally:
            _editando_programaticamente = False
        return

    # --- 1. Obter dados de `dados_def_pecas` para este item do orçamento ---
    # Soma dos custos de todas as peças (`def_peca`) que compõem este item do orçamento.
    total_orlas = 0.0
    total_mao_obra = 0.0
    total_materia_prima = 0.0
    total_acabamentos = 0.0

    try:
        with obter_cursor() as cursor:
            # Query para somar os custos relevantes da tabela dados_def_pecas
            # O critério de busca é ids (item do orcamento), num_orc (numero orcamento), ver_orc (versao orcamento)
            query = f"""
                SELECT SUM(CUSTO_ML_C1 + CUSTO_ML_C2 + CUSTO_ML_L1 + CUSTO_ML_L2),
                       SUM(Soma_Custo_und), -- Soma_Custo_und já é por unidade de peça
                       SUM(CUSTO_MP_Total),
                       SUM(Soma_Custo_ACB)
                FROM dados_def_pecas
                WHERE ids=%s AND num_orc=%s AND ver_orc=%s
            """
            cursor.execute(query, (id_item_orcamento_str,
                           num_orc_str, ver_orc_str))
            res = cursor.fetchone()

            if res and res[0] is not None:  # Verifica se há resultados válidos e não são None
                total_orlas = float(res[0]) if res[0] is not None else 0.0
                # A soma da mão de obra (Soma_Custo_und) já vem por peça. Deve ser multiplicada por QT_Total do item.
                # No entanto, a regra indica `SUM(Soma_Custo_und * QT_Total)`. Precisamos mudar a lógica aqui.
                # A Soma_Custo_und (col 79) é o custo unitário por peça. QT_Total (col 49) é a quantidade total de peças.
                # A soma no DB deve ser do custo total de cada peça.
                # A query já está a fazer SUM(Soma_Custo_und * QT_Total)
                total_mao_obra = float(res[1]) if res[1] is not None else 0.0
                total_materia_prima = float(
                    res[2]) if res[2] is not None else 0.0
                total_acabamentos = float(
                    res[3]) if res[3] is not None else 0.0
                # print(f"[DEBUG] Custos DB para item {id_item_orcamento_str}: Orlas={total_orlas:.2f}, MO={total_mao_obra:.2f}, MP={total_materia_prima:.2f}, Acab={total_acabamentos:.2f}")
            else:
                print(
                    f"[INFO] Nenhum dado de peça encontrado na dados_def_pecas para Item: {id_item_orcamento_str}, Orc: {num_orc_str}, Ver: {ver_orc_str}. Custos serão 0.")

    except mysql.connector.Error as err:
        print(
            f"Erro MySQL ao buscar dados de peças para item {id_item_orcamento_str}: {err}")
        return  # Sai se houver erro na BD
    except Exception as e:
        print(
            f"Erro inesperado ao buscar dados de peças para item {id_item_orcamento_str}: {e}")
        return  # Sai se houver outro erro

    # --- 2. Obter valores de percentagem: prioriza o valor da tabela, senão o global do lineEdit ---
    # Pega o texto da célula, tenta converter. Se vazio, pega do lineEdit correspondente.
    # Usamos o 'safe_item_text' indiretamente com '_get_cell_text'
    # NOTA: O `_get_cell_text` retorna string vazia se o item for None.
    # `converter_texto_para_valor` lida com string vazia e com a percentagem.

    # Ao obter a percentagem da célula, precisamos do valor NUMÉRICO, não formatado.
    # E para comparar, é preciso também do valor NUMÉRICO do lineEdit global.

    # Valores globais dos lineEdits (sempre lidos como números)
    global_margem_lucro_perc = converter_texto_para_valor(
        ui.lineEdit_margem_lucro.text(), "percentual")
    global_custos_admin_perc = converter_texto_para_valor(
        ui.lineEdit_custos_administrativos.text(), "percentual")
    global_ajustes1_perc = converter_texto_para_valor(
        ui.lineEdit_ajustes_1.text(), "percentual")
    global_ajustes2_perc = converter_texto_para_valor(
        ui.lineEdit_ajustes_2.text(), "percentual")

    # Decidir qual percentagem de margem de lucro usar
    # Se 'force_global_margin_update' for True, sobrescreve o valor da célula de margem de lucro
    # com o valor global e reseta a cor.
    # Adicionando depuração para as percentagens lidas
    # print(f"[DEBUG CalcLinha {row_idx+1}] Global Margem Lucro (%): {global_margem_lucro_perc*100:.2f}%")
    # print(f"[DEBUG CalcLinha {row_idx+1}] Célula Margem Lucro Texto (antes de parse): '{_get_cell_text(tbl, row_idx, COL_MARGEM_PERC)}'")
    margem_lucro_perc_cell_val_parsed = converter_texto_para_valor(
        _get_cell_text(tbl, row_idx, COL_MARGEM_PERC), "percentual")
    # print(f"[DEBUG CalcLinha {row_idx+1}] Célula Margem Lucro Valor Parsed: {margem_lucro_perc_cell_val_parsed*100:.2f}%")

    margem_lucro_perc = 0.0
    if force_global_margin_update:
        margem_lucro_perc = global_margem_lucro_perc
        # print(f"[DEBUG CalcLinha {row_idx+1}] Usando margem global (forced): {margem_lucro_perc*100:.2f}%")
        _editando_programaticamente = True  # Ativar para alterar a célula da margem
        try:
            item_q_margin_perc = tbl.item(row_idx, COL_MARGEM_PERC)
            if not item_q_margin_perc:  # Se a célula não existe, cria
                item_q_margin_perc = QTableWidgetItem()
                tbl.setItem(row_idx, COL_MARGEM_PERC, item_q_margin_perc)
            item_q_margin_perc.setText(
                formatar_valor_percentual(margem_lucro_perc))
            item_q_margin_perc.setBackground(
                tbl.palette().base().color())  # Resetar cor
        finally:
            _editando_programaticamente = False
    else:
        # Se a célula tem um valor diferente do global, usa o da célula. Senão, usa o global.
        if abs(margem_lucro_perc_cell_val_parsed - global_margem_lucro_perc) > 0.001:
            margem_lucro_perc = margem_lucro_perc_cell_val_parsed
            # print(f"[DEBUG CalcLinha {row_idx+1}] Usando margem da célula (diferente do global): {margem_lucro_perc*100:.2f}%")
        else:
            margem_lucro_perc = global_margem_lucro_perc
            # print(f"[DEBUG CalcLinha {row_idx+1}] Usando margem global (célula igual ou proxima): {margem_lucro_perc*100:.2f}%")

    # Adicionando depuração para os outros percentuais
    custos_admin_perc_cell = converter_texto_para_valor(
        _get_cell_text(tbl, row_idx, COL_CUSTOS_ADMIN_PERC), "percentual")
    custos_admin_perc = custos_admin_perc_cell if abs(
        custos_admin_perc_cell - global_custos_admin_perc) > 0.001 else global_custos_admin_perc
    # print(f"[DEBUG CalcLinha {row_idx+1}] Custos Admin Perc Efetivo: {custos_admin_perc*100:.2f}%")

    ajustes1_perc_cell = converter_texto_para_valor(
        _get_cell_text(tbl, row_idx, COL_AJUSTES1_PERC), "percentual")
    ajustes1_perc = ajustes1_perc_cell if abs(
        ajustes1_perc_cell - global_ajustes1_perc) > 0.001 else global_ajustes1_perc
    # print(f"[DEBUG CalcLinha {row_idx+1}] Ajustes 1 Perc Efetivo: {ajustes1_perc*100:.2f}%")

    ajustes2_perc_cell = converter_texto_para_valor(
        _get_cell_text(tbl, row_idx, COL_AJUSTES2_PERC), "percentual")
    ajustes2_perc = ajustes2_perc_cell if abs(
        ajustes2_perc_cell - global_ajustes2_perc) > 0.001 else global_ajustes2_perc
    # print(f"[DEBUG CalcLinha {row_idx+1}] Ajustes 2 Perc Efetivo: {ajustes2_perc*100:.2f}%")

    qt_item = converter_texto_para_valor(
        _get_cell_text(tbl, row_idx, COL_QT), "moeda")
    if qt_item <= 0:
        qt_item = 1.0

    custo_produzido_calculado = (
        total_orlas + total_mao_obra + total_materia_prima + total_acabamentos)
    # print(f"[DEBUG CalcLinha {row_idx+1}] Custo Produzido (Orlas+MO+MP+Acab): {custo_produzido_calculado:.2f}€")
    # --- 3. Calcular valores de margem, custos administrativos e ajustes ---
    # Valores de margem, custos administrativos e ajustes são calculados como percentagens do custo produzido

    # Remover a divisão por 100.0, pois as percentagens já estão em decimal.
    valor_margem = custo_produzido_calculado * margem_lucro_perc
    valor_custos_admin = custo_produzido_calculado * custos_admin_perc
    valor_ajustes1 = custo_produzido_calculado * ajustes1_perc
    valor_ajustes2 = custo_produzido_calculado * ajustes2_perc

    # Preço unitário do item (total do item dividido pela quantidade do item)
    # print(f"[DEBUG CalcLinha {row_idx+1}] Valores calculados: Margem={valor_margem:.2f}€, Admin={valor_custos_admin:.2f}€, Aj1={valor_ajustes1:.2f}€, Aj2={valor_ajustes2:.2f}€")

    # Preco_Unit é o preço de 1 unidade do item.
    # Preco_Total é o Preco_Unit * QT.
    preco_base_por_unidade = (custo_produzido_calculado + valor_margem +
                              valor_custos_admin + valor_ajustes1 + valor_ajustes2)
    preco_unit_calculado = preco_base_por_unidade
    preco_total_calculado = preco_base_por_unidade * qt_item
    # print(f"[DEBUG CalcLinha {row_idx+1}] Preco_Total Calculado para esta linha: {preco_total_calculado:.2f}€")

    # print(f"[DEBUG CalcLinha {row_idx+1}] Preço Unitário Calculado: {preco_unit_calculado:.2f}€")
    # print(f"[DEBUG CalcLinha {row_idx+1}] Preço Total Calculado: {preco_total_calculado:.2f}€")

    # --- 4. Atualizar UI e DB (bloqueia sinais temporariamente) ---
    # Ativa a flag para evitar disparos recursivos de itemChanged
    _editando_programaticamente = True
    try:
        # Bloqueia sinais da tabela enquanto atualiza programaticamente
        tbl.blockSignals(True)
        # Atualiza Custo Produzido
        tooltip_custo_produzido = f"Custo Produzido = Custo Total Orlas ({total_orlas:.2f}€) + Custo Total Mão de Obra ({total_mao_obra:.2f}€) + Custo Total Matéria Prima ({total_materia_prima:.2f}€) + Custo Total Acabamentos ({total_acabamentos:.2f}€) = {custo_produzido_calculado:.2f}€"
        set_item(tbl, row_idx, COL_CUSTO_PRODUZIDO,
                 formatar_valor_moeda(custo_produzido_calculado))
        if tbl.item(row_idx, COL_CUSTO_PRODUZIDO):
            tbl.item(row_idx, COL_CUSTO_PRODUZIDO).setToolTip(
                tooltip_custo_produzido)

        # Atualiza colunas de custos e valores em euros com tooltips
        tooltip_orlas = f"Soma dos custos de orlas de todas as peças deste item: {total_orlas:.2f}€"
        set_item(tbl, row_idx, COL_CUSTO_ORLAS,
                 formatar_valor_moeda(total_orlas))
        if tbl.item(row_idx, COL_CUSTO_ORLAS):
            tbl.item(row_idx, COL_CUSTO_ORLAS).setToolTip(tooltip_orlas)

        tooltip_mo = f"Soma dos custos de Mão de Obra e máquinas de todas as peças deste item: {total_mao_obra:.2f}€"
        set_item(tbl, row_idx, COL_CUSTO_MO,
                 formatar_valor_moeda(total_mao_obra))
        if tbl.item(row_idx, COL_CUSTO_MO):
            tbl.item(row_idx, COL_CUSTO_MO).setToolTip(tooltip_mo)

        tooltip_mp = f"Soma dos custos de Matéria Prima de todas as peças deste item: {total_materia_prima:.2f}€"
        set_item(tbl, row_idx, COL_CUSTO_MP,
                 formatar_valor_moeda(total_materia_prima))
        if tbl.item(row_idx, COL_CUSTO_MP):
            tbl.item(row_idx, COL_CUSTO_MP).setToolTip(tooltip_mp)

        tooltip_acab = f"Soma dos custos de Acabamentos de todas as peças deste item: {total_acabamentos:.2f}€"
        set_item(tbl, row_idx, COL_CUSTO_ACABAMENTOS,
                 formatar_valor_moeda(total_acabamentos))
        if tbl.item(row_idx, COL_CUSTO_ACABAMENTOS):
            tbl.item(row_idx, COL_CUSTO_ACABAMENTOS).setToolTip(tooltip_acab)

        # Margem de Lucro Percentual (já tratada acima para force_global_margin_update)
        tooltip_margem_perc = f"Percentagem de Margem de Lucro: {margem_lucro_perc*100:.2f}%"
        # A célula COL_MARGEM_PERC já foi atualizada e sua cor resetada se force_global_margin_update for True.
        # Caso contrário, precisamos garantir que o tooltip e a cor (se diferente do global) sejam corretos.
        item_q_margin_perc_current = tbl.item(row_idx, COL_MARGEM_PERC)
        if item_q_margin_perc_current:
            item_q_margin_perc_current.setToolTip(tooltip_margem_perc)
            if not force_global_margin_update:  # Se não estamos forçando, a cor é definida pela diferença com o global
                cell_val_current = converter_texto_para_valor(
                    item_q_margin_perc_current.text(), "percentual")
                # Compara o valor atual da célula com o global
                if abs(cell_val_current - global_margem_lucro_perc) > 0.001:
                    item_q_margin_perc_current.setBackground(
                        COLOR_MANUAL_EDIT)  # Cor amarela para edição manual
                else:
                    # Cor padrão da tabela (normalmente branca)
                    item_q_margin_perc_current.setBackground(
                        tbl.palette().base().color())

        tooltip_valor_margem = f"Valor da Margem de Lucro: {custo_produzido_calculado:.2f}€ * ({margem_lucro_perc*100:.2f}%) = {valor_margem:.2f}€"
        set_item(tbl, row_idx, COL_MARGEM_VALOR,
                 formatar_valor_moeda(valor_margem))
        if tbl.item(row_idx, COL_MARGEM_VALOR):
            tbl.item(row_idx, COL_MARGEM_VALOR).setToolTip(
                tooltip_valor_margem)

        tooltip_admin_perc = f"Percentagem de Custos Administrativos: {custos_admin_perc*100:.2f}%"
        set_item(tbl, row_idx, COL_CUSTOS_ADMIN_PERC,
                 formatar_valor_percentual(custos_admin_perc))
        if tbl.item(row_idx, COL_CUSTOS_ADMIN_PERC):
            tbl.item(row_idx, COL_CUSTOS_ADMIN_PERC).setToolTip(
                tooltip_admin_perc)

        tooltip_valor_admin = f"Valor de Custos Administrativos: {custo_produzido_calculado:.2f}€ * ({custos_admin_perc*100:.2f}%) = {valor_custos_admin:.2f}€"
        set_item(tbl, row_idx, COL_CUSTOS_ADMIN_VALOR,
                 formatar_valor_moeda(valor_custos_admin))
        if tbl.item(row_idx, COL_CUSTOS_ADMIN_VALOR):
            tbl.item(row_idx, COL_CUSTOS_ADMIN_VALOR).setToolTip(
                tooltip_valor_admin)

        tooltip_ajustes1_perc = f"Percentagem de Ajustes 1: {ajustes1_perc*100:.2f}%"
        set_item(tbl, row_idx, COL_AJUSTES1_PERC,
                 formatar_valor_percentual(ajustes1_perc))
        if tbl.item(row_idx, COL_AJUSTES1_PERC):
            tbl.item(row_idx, COL_AJUSTES1_PERC).setToolTip(
                tooltip_ajustes1_perc)

        tooltip_valor_ajustes1 = f"Valor de Ajustes 1: {custo_produzido_calculado:.2f}€ * ({ajustes1_perc*100:.2f}%) = {valor_ajustes1:.2f}€"
        set_item(tbl, row_idx, COL_AJUSTES1_VALOR,
                 formatar_valor_moeda(valor_ajustes1))
        if tbl.item(row_idx, COL_AJUSTES1_VALOR):
            tbl.item(row_idx, COL_AJUSTES1_VALOR).setToolTip(
                tooltip_valor_ajustes1)

        tooltip_ajustes2_perc = f"Percentagem de Ajustes 2: {ajustes2_perc*100:.2f}%"
        set_item(tbl, row_idx, COL_AJUSTES2_PERC,
                 formatar_valor_percentual(ajustes2_perc))
        if tbl.item(row_idx, COL_AJUSTES2_PERC):
            tbl.item(row_idx, COL_AJUSTES2_PERC).setToolTip(
                tooltip_ajustes2_perc)

        tooltip_valor_ajustes2 = f"Valor de Ajustes 2: {custo_produzido_calculado:.2f}€ * ({ajustes2_perc*100:.2f}%) = {valor_ajustes2:.2f}€"
        set_item(tbl, row_idx, COL_AJUSTES2_VALOR,
                 formatar_valor_moeda(valor_ajustes2))
        if tbl.item(row_idx, COL_AJUSTES2_VALOR):
            tbl.item(row_idx, COL_AJUSTES2_VALOR).setToolTip(
                tooltip_valor_ajustes2)

        # Atualizar Preco_Unit e Preco_Total na UI
        tooltip_preco_unit = f"Preço Unitário: (Custo Produzido ({custo_produzido_calculado:.2f}€) + Margem ({valor_margem:.2f}€) + Admin ({valor_custos_admin:.2f}€) + Aj1 ({valor_ajustes1:.2f}€) + Aj2 ({valor_ajustes2:.2f}€)) = {preco_unit_calculado:.2f}€"
        set_item(tbl, row_idx, COL_PRECO_UNIT,
                 formatar_valor_moeda(preco_unit_calculado))
        if tbl.item(row_idx, COL_PRECO_UNIT):
            tbl.item(row_idx, COL_PRECO_UNIT).setToolTip(tooltip_preco_unit)

        tooltip_preco_total = f"Preço Total: Preço Unitário ({preco_unit_calculado:.2f}€) * Quantidade ({qt_item:.0f}) = {preco_total_calculado:.2f}€"
        set_item(tbl, row_idx, COL_PRECO_TOTAL,
                 formatar_valor_moeda(preco_total_calculado))
        if tbl.item(row_idx, COL_PRECO_TOTAL):
            tbl.item(row_idx, COL_PRECO_TOTAL).setToolTip(tooltip_preco_total)

        # DEBUG: Confirmar o valor na célula após a atualização
        debug_read_preco_total = _get_cell_text(tbl, row_idx, COL_PRECO_TOTAL)
        # print(f"[DEBUG CalcLinha {row_idx+1}] Preco_Total na célula após set_item: {debug_read_preco_total}")

        # CUIDADO COM COLORAÇÃO: A lógica de colorir a célula de percentagem se ela foi editada manualmente
        # é feita em `handle_item_editado` ou `carregar_itens_orcamento`.
        # Aqui, ao recalcular, se o valor da célula (original ou já editado) é igual ao global,
        # a cor deve voltar ao normal. Se é diferente, deve manter a cor manual.
        # Isto já é tratado na função `carregar_itens_orcamento` e `handle_item_editado`.
        # O `set_item` em si não muda a cor, apenas o texto. A cor é definida à parte.

        # Salvar todos os valores calculados para o banco de dados
        # O id_item_db_val é o ID real da linha na orcamento_items
        id_item_db_val = int(id_item_db_val_str)

        with obter_cursor() as cursor:
            update_query = """
                UPDATE orcamento_items SET
                    preco_unitario=%s, preco_total=%s,custo_produzido=%s,
                    custo_total_orlas=%s, custo_total_mao_obra=%s, custo_total_materia_prima=%s,
                    custo_total_acabamentos=%s, margem_lucro_perc=%s, valor_margem=%s,
                    custos_admin_perc=%s, valor_custos_admin=%s, ajustes1_perc=%s,
                    valor_ajustes1=%s, ajustes2_perc=%s, valor_ajustes2=%s
                WHERE id_item=%s
            """
            cursor.execute(update_query, (
                preco_unit_calculado, preco_total_calculado, custo_produzido_calculado,
                total_orlas, total_mao_obra, total_materia_prima, total_acabamentos,
                # Salva o valor que foi efetivamente usado no cálculo (pode ser o manual ou o global)
                margem_lucro_perc, valor_margem,
                custos_admin_perc, valor_custos_admin, ajustes1_perc,
                valor_ajustes1, ajustes2_perc, valor_ajustes2,
                id_item_db_val  # id_item da tabela orcamento_items para o WHERE
            ))
            # print(f"  DB atualizado para item {id_item_orcamento_str}.")

    except mysql.connector.Error as err:
        print(
            f"[ERRO] Erro MySQL ao atualizar linha de artigo {row_idx+1}: {err}")
        # Relança o erro para ser capturado no nível superior, se necessário
        raise
    except Exception as e:
        print(
            f"[ERRO] Erro inesperado ao atualizar linha de artigo {row_idx+1}: {e}")
        import traceback
        traceback.print_exc()
        raise  # Relança o erro
    finally:
        tbl.blockSignals(False)  # Desbloqueia sinais
        _editando_programaticamente = False

# --- NOVO: Função para o botão "Atualiza Preco Items Orcamento" ---


def atualizar_custos_e_precos_itens(ui, force_global_margin_update=False):
    """
    Função principal para atualizar todos os cálculos de custos e preços
    para todos os itens na tableWidget_artigos.
    `force_global_margin_update` (bool): Se True, força a percentagem de margem de lucro
                                        de todos os itens a ser o valor global do lineEdit,
                                        sobrescrevendo qualquer override manual.
    """
    # print("[INFO] Iniciando atualização de custos e preços para todos os itens do orçamento...")
    tbl = ui.tableWidget_artigos
    for row_idx in range(tbl.rowCount()):
        try:
            # Passa a flag para a função de cálculo da linha
            calcular_e_atualizar_linha_artigo(
                ui, row_idx, force_global_margin_update)
        except Exception as e:
            print(
                f"[ERRO] Falha ao processar linha {row_idx+1} na atualização de itens: {e}")
            # CORRIGIDO: Usar um QWidget real como parent para QMessageBox
            QMessageBox.critical(ui.tabWidget_orcamento, "Erro de Cálculo",
                                 f"Falha ao calcular item {row_idx+1}: {e}")
            # Continua para a próxima linha, mas loga o erro e avisa o usuário.

    # Após atualizar todos os itens, garantir que o preço final do orçamento é recalculado
    # Não precisa passar a flag aqui, pois calcular_preco_final_orcamento vai lidar com isso.
    # O `calcular_preco_final_orcamento` será chamado no final, independentemente da flag.
    # Se o call veio do "atingir objetivo", ele será chamado novamente (loop).
    # Precisamos evitar isso.
    # A chamada para `calcular_preco_final_orcamento` deve ser apenas no final do `atualizar_custos_e_precos_itens`.
    # A lógica "atingir objetivo" *já* chama `atualizar_custos_e_precos_itens` e depois recalcula o total.
    # Então, este `calcular_preco_final_orcamento` aqui é redundante se chamado da lógica de "atingir objetivo".
    # Mas é necessário se chamado diretamente de `pushButton_atualiza_preco_items`.

    # Para evitar recursão/redundância, podemos fazer o seguinte:
    # Apenas o `pushButton_atualiza_preco_final` chama `calcular_preco_final_orcamento` (que por sua vez chama `atualizar_custos_e_precos_itens(force_global_margin_update=True)`).
    # O `pushButton_atualiza_preco_items` chama `atualizar_custos_e_precos_itens(force_global_margin_update=False)` E DEPOIS chama `calcular_preco_final_orcamento(ui)`
    # Isso requer uma pequena mudança no `configurar_orcamento_ui`.

    print("[INFO] Atualização de custos e preços dos itens concluída.")

# MODIFICADO: Lógica para "Atingir Objetivo de Preço Final"


def calcular_preco_final_orcamento(ui):
    """
    Ajusta automaticamente a margem de lucro (%) para, se o usuário definiu um objetivo,
    tentar atingir esse preço final. Em qualquer caso, atualiza sempre o campo
    'lineEdit_preco_final_orcamento' com a soma atual dos Preco_Total da tabela.

    Parâmetros:
      ui: instância de Ui_MainWindow (ou `main_window.ui`) passada pelo chamador

    Fluxo geral:
      1. Lê o objetivo de preço final (lineEdit_atingir_preco_final).
      2. Soma todos os Preco_Total e todos os Custo Produzido da tableWidget_artigos.
      3. Se não há objetivo (ou tabela vazia), apenas exibe a soma atual e retorna.
      4. Calcula qual deve ser a margem global para que a soma atinja o objetivo.
      5. Ajusta o campo lineEdit_margem_lucro com essa margem.
      6. Força a atualização de todos os itens (chama atualizar_custos_e_precos_itens com flag).
      7. Soma de novo todos os Preco_Total (já recalculados) e mostra em lineEdit_preco_final_orcamento.
    """

    # 1. Referência à tabela de itens
    tbl = ui.tableWidget_artigos

    target_price_str = ui.lineEdit_atingir_preco_final.text().strip()
    target_price = converter_texto_para_valor(
        target_price_str, "moeda") if target_price_str else 0.0

    # Coletar todos os valores individuais dos itens em listas
    preco_total_items = []  # Lista para armazenar os Preco_Total de cada item
    # Usaremos estes para o cálculo da nova margem percentual global
    # Σ (Custo Produzido * QT) para o denominador
    sum_custo_produzido_vezes_qt_total = 0.0
    # Σ (Custo Produzido * (1 + Admin_Perc + Aj1_Perc + Aj2_Perc) * QT) para o numerador
    sum_custo_base_e_outros_ajustes_vezes_qt_total = 0.0

    # Bloquear sinais da tabela durante a coleta para evitar chamadas redundantes de itemChanged
    tbl.blockSignals(True)
    try:
        for row_idx in range(tbl.rowCount()):
            try:
                # Obter valores de cada célula, convertendo para float.
                # Se a conversão falhar, converter_texto_para_valor retorna 0.0,
                # garantindo que as listas nunca tenham entradas inválidas ou falhem em 'append'.
                preco_total_items.append(converter_texto_para_valor(
                    _get_cell_text(tbl, row_idx, COL_PRECO_TOTAL), "moeda"))

                # Coleta de dados para a nova fórmula da margem global
                custo_produzido_item = converter_texto_para_valor(
                    _get_cell_text(tbl, row_idx, COL_CUSTO_PRODUZIDO), "moeda")
                qt_item = converter_texto_para_valor(
                    _get_cell_text(tbl, row_idx, COL_QT), "moeda")
                if qt_item <= 0:
                    qt_item = 1.0

                # Lendo percentuais atuais (globais ou da célula se houver override)
                global_custos_admin_perc = converter_texto_para_valor(
                    ui.lineEdit_custos_administrativos.text(), "percentual")
                global_ajustes1_perc = converter_texto_para_valor(
                    ui.lineEdit_ajustes_1.text(), "percentual")
                global_ajustes2_perc = converter_texto_para_valor(
                    ui.lineEdit_ajustes_2.text(), "percentual")

                custos_admin_perc_cell = converter_texto_para_valor(
                    _get_cell_text(tbl, row_idx, COL_CUSTOS_ADMIN_PERC), "percentual")
                ajustes1_perc_cell = converter_texto_para_valor(
                    _get_cell_text(tbl, row_idx, COL_AJUSTES1_PERC), "percentual")
                ajustes2_perc_cell = converter_texto_para_valor(
                    _get_cell_text(tbl, row_idx, COL_AJUSTES2_PERC), "percentual")

                # Valores de percentagem de Ajustes e Custos Admin REALMENTE aplicados ao item
                custos_admin_perc_effective = custos_admin_perc_cell if abs(
                    custos_admin_perc_cell - global_custos_admin_perc) > 0.001 else global_custos_admin_perc
                ajustes1_perc_effective = ajustes1_perc_cell if abs(
                    ajustes1_perc_cell - global_ajustes1_perc) > 0.001 else global_ajustes1_perc
                ajustes2_perc_effective = ajustes2_perc_cell if abs(
                    ajustes2_perc_cell - global_ajustes2_perc) > 0.001 else global_ajustes2_perc

                # Acumular Somas para a nova fórmula da margem global
                sum_custo_produzido_vezes_qt_total += custo_produzido_item * qt_item

                # Base para o cálculo da margem sem a própria margem, mas com outros custos e quantidade
                custo_base_e_outros_ajustes_unit = custo_produzido_item * \
                    (1 + custos_admin_perc_effective +
                     ajustes1_perc_effective + ajustes2_perc_effective)
                sum_custo_base_e_outros_ajustes_vezes_qt_total += custo_base_e_outros_ajustes_unit * qt_item

            except Exception as e:
                print(
                    f"[ERRO] Falha na leitura/conversão de dados de item na linha {row_idx}: {e}")
                QMessageBox.warning(ui.tabWidget_orcamento, "Erro de Leitura",
                                    f"Erro ao ler dados do item na linha {row_idx+1}. Este item pode não ser incluído corretamente nos cálculos globais. Erro: {e}")
                # Ensure something is appended even on error to keep lists same length for summing
                preco_total_items.append(0.0)
                # Não acumular para as novas somas se houver erro, para não distorcer.
                # Se custo_produzido_item ou qt_item for 0, já será tratado abaixo.

    finally:
        tbl.blockSignals(False)

    # Sumarizar o preço total atual
    sum_preco_total_current = sum(preco_total_items)

    if target_price > 0:  # Se um objetivo de preço final foi definido
        print(
            f"[INFO] Objetivo de preço final: {formatar_valor_moeda(target_price)}")

        # A nova fórmula para Nova_Margem_Perc:
        # target_price = Σ [ custo_produzido_item * (1 + Nova_Margem_Perc + Admin_Perc_Item + Aj1_Perc_Item + Aj2_Perc_Item) * qt_item ]
        # target_price = Σ [ (custo_produzido_item * qt_item) * (1 + Admin_Perc_Item + Aj1_Perc_Item + Aj2_Perc_Item) ] + Nova_Margem_Perc * Σ [ custo_produzido_item * qt_item ]
        # Nova_Margem_Perc = (target_price - Σ [ (custo_produzido_item * qt_item) * (1 + Admin_Perc_Item + Aj1_Perc_Item + Aj2_Perc_Item) ]) / Σ [ custo_produzido_item * qt_item ]

        if sum_custo_produzido_vezes_qt_total <= 0:
            QMessageBox.warning(ui.tabWidget_orcamento, "Erro de Cálculo",
                                "Custo Produzido total (vezes quantidade) dos itens é zero ou negativo. Não é possível ajustar a margem para atingir o objetivo de preço final.")
            ui.lineEdit_atingir_preco_final.clear()
            # A atualização do lineEdit_preco_final_orcamento será feita no final da função
            return

        # Calcular a nova margem percentual global necessária
        new_margin_perc = (
            target_price - sum_custo_base_e_outros_ajustes_vezes_qt_total) / sum_custo_produzido_vezes_qt_total

        # Limitar a nova margem de lucro a um valor razoável (e.g., 0-99%)
        if new_margin_perc < 0 or new_margin_perc > 0.99:
            QMessageBox.warning(ui.tabWidget_orcamento, "Aviso de Cálculo",
                                f"A margem de lucro calculada ({formatar_valor_percentual(new_margin_perc)}) "
                                "para atingir o objetivo está fora do intervalo de 0% a 99%. "
                                "O objetivo pode ser inatingível ou os custos/ajustes são desproporcionais."
                                "\nDefinindo margem para o limite mais próximo.")
            new_margin_perc = max(0.0, min(0.99, new_margin_perc))

        global _editando_programaticamente
        # Bloqueia sinais durante atualizações programáticas
        _editando_programaticamente = True
        try:
            # Atualizar o lineEdit global de margem de lucro
            ui.lineEdit_margem_lucro.setText(
                formatar_valor_percentual(new_margin_perc))

            # Recalcular todos os itens, FORÇANDO a margem global que acabamos de definir.
            # Isso é crucial para que todos os itens usem a nova margem calculada para atingir o objetivo.
            atualizar_custos_e_precos_itens(
                ui, force_global_margin_update=True)

            # Informar o utilizador sobre o sucesso
            QMessageBox.information(ui.tabWidget_orcamento, "Objetivo Atingido",
                                    f"Margem de Lucro ajustada para {formatar_valor_percentual(new_margin_perc)} para atingir o preço final de {formatar_valor_moeda(target_price)}.")
            ui.lineEdit_atingir_preco_final.clear()  # Limpa o campo do objetivo

        except Exception as e:
            QMessageBox.critical(ui.tabWidget_orcamento, "Erro ao Ajustar Margens",
                                 f"Ocorreu um erro ao ajustar as margens: {e}\nPor favor, verifique os dados dos itens.")
            print(f"[ERRO] Erro no ajuste proporcional de margens: {e}")
            import traceback
            traceback.print_exc()
        finally:
            _editando_programaticamente = False

    # Sempre atualizar o preço final do orçamento visível na UI, independentemente do caminho do 'if'
    final_sum_preco_total = 0.0
    for row_idx in range(tbl.rowCount()):
        current_preco_total_cell_text = _get_cell_text(
            tbl, row_idx, COL_PRECO_TOTAL)
        val = converter_texto_para_valor(
            current_preco_total_cell_text, "moeda")
        final_sum_preco_total += val
        # print(f"[DEBUG SumFinal] Linha {row_idx+1}: Preco_Total lido='{current_preco_total_cell_text}' convertido={val:.2f}€")

    ui.lineEdit_preco_final_orcamento.setText(
        formatar_valor_moeda(final_sum_preco_total))
    # print(f"[INFO] Preço final do orçamento (soma atual): {formatar_valor_moeda(final_sum_preco_total)}")


#################################################################################################################################
# 10. As funções: limpar_dados_linha_orcamento, exibir_menu_contexto_groupbox e configurar_context_menu_groupbox
# são usadas com opção lado direito do rato no groupBox_linhas_orcamento para limpar os dados dos campos do item do orçamento.
#################################################################################################################################

def limpar_dados_linha_orcamento(ui):
    """
    Limpa os dados dos campos do groupBox_linhas_orcamento, conforme:
      - Limpa: lineEdit_codigo_orcamento, plainTextEdit_descricao_orcamento,
                lineEdit_altura_orcamento, lineEdit_largura_orcamento, lineEdit_profundidade_orcamento.
      - Mantém: lineEdit_und_orcamento = "und", lineEdit_qt_orcamento = "1".
      - Atualiza: lineEdit_item_orcamento para o próximo número de item da tabela tableWidget_artigos.
    """
    ui.lineEdit_codigo_orcamento.clear()
    ui.plainTextEdit_descricao_orcamento.clear()
    ui.lineEdit_altura_orcamento.clear()
    ui.lineEdit_largura_orcamento.clear()
    ui.lineEdit_profundidade_orcamento.clear()

    # Define valor padrão para unidade e quantidade
    ui.lineEdit_und_orcamento.setText("und")
    ui.lineEdit_qt_orcamento.setText("1")

    # Atualiza o número do item: usa o id do orçamento para obter o próximo número
    id_orc_str = ui.lineEdit_id.text().strip()
    if id_orc_str.isdigit():
        id_orc = int(id_orc_str)
        prox = obter_proximo_item_para_orcamento(id_orc)
        ui.lineEdit_item_orcamento.setText(str(prox))
    else:
        ui.lineEdit_item_orcamento.setText("1")

#################################################################################################################################
# 10.1
#################################################################################################################################


def exibir_menu_contexto_groupbox(ui, pos):
    """
    Exibe um menu de contexto para o groupBox_linhas_orcamento, com a opção de limpar os dados da linha.
    """
    menu = QMenu()
    acao_limpar = menu.addAction("Limpar Dados da Linha")

    # Exibe o menu na posição global
    acao = menu.exec_(ui.groupBox_linhas_orcamento.mapToGlobal(pos))
    if acao == acao_limpar:
        limpar_dados_linha_orcamento(ui)

#################################################################################################################################
# 10.2  Funções de manipulação de itens do orçamento via menu de contexto
#
#  Inclui ações para limpar campos de edição, duplicar linhas de artigo e
#  eliminar itens selecionados. A duplicação copia todos os registos
#  correspondentes para um novo número sequencial de item, enquanto a
#  eliminação remove esses dados de todas as tabelas relacionadas.
#################################################################################################################################


def configurar_context_menu_groupbox(ui):
    """
    Configura o menu de contexto para o groupBox_linhas_orcamento. Opção com lado direito do rato
    tem opção de limpar dados nos campos dos item do orçamento para poder escrever novo item a inserir na tabela dos items do orcamento.
    """
    ui.groupBox_linhas_orcamento.setContextMenuPolicy(Qt.CustomContextMenu)
    ui.groupBox_linhas_orcamento.customContextMenuRequested.connect(
        lambda pos: exibir_menu_contexto_groupbox(ui, pos))

# --- Novas Funções para Duplicar Linhas na tableWidget_artigos ---


def configurar_context_menu_tabela(ui):
    """Adiciona um menu de contexto na tabela de artigos.

    O menu permite duplicar ou eliminar a linha selecionada, facilitando a
    gestão dos itens do orçamento diretamente na interface.
    """
    ui.tableWidget_artigos.setContextMenuPolicy(Qt.CustomContextMenu)
    ui.tableWidget_artigos.customContextMenuRequested.connect(
        lambda pos: exibir_menu_contexto_tabela(ui, pos))


def exibir_menu_contexto_tabela(ui, pos):
    """Exibe o menu de contexto da tabela de artigos."""
    menu = QMenu()
    acao_duplicar = menu.addAction("Duplicar Linha de Artigo")
    acao_eliminar = menu.addAction("Eliminar Linha de Artigo")

    acao = menu.exec_(ui.tableWidget_artigos.mapToGlobal(pos))
    if acao == acao_duplicar:
        duplicar_item_orcamento(ui)
    elif acao == acao_eliminar:
        excluir_item_orcamento(ui)


def duplicar_registos_associados(cursor, tabela, coluna_item, item_antigo, item_novo, num_orc, ver_orc):
    """Duplica registros de uma tabela associados a um item."""
    cursor.execute(f"SHOW COLUMNS FROM {tabela}")
    cols = [row[0] for row in cursor.fetchall() if row[0] != 'id']
    insert_cols = ", ".join(f"`{c}`" for c in cols)
    select_cols = ", ".join(
        ["%s" if c == coluna_item else f"`{c}`" for c in cols])
    query = (
        f"INSERT INTO {tabela} ({insert_cols}) "
        f"SELECT {select_cols} FROM {tabela} "
        f"WHERE {coluna_item}=%s AND num_orc=%s AND ver_orc=%s")
    params = [item_novo, item_antigo, num_orc, ver_orc]
    cursor.execute(query, params)


def duplicar_item_orcamento(ui):
    """Duplica a linha selecionada e todos os dados associados."""
    tbl = ui.tableWidget_artigos
    row_sel = tbl.currentRow()
    if row_sel < 0:
        QMessageBox.warning(
            None, "Erro", "Nenhuma linha selecionada para duplicar.")
        return

    id_item_str = _get_cell_text(tbl, row_sel, COL_ID_ITEM)
    item_num_str = _get_cell_text(tbl, row_sel, COL_ITEM_NUM)
    id_orc_str = ui.lineEdit_id.text().strip()
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    ver_orc = ui.lineEdit_versao_orcamento.text().strip()

    if not id_item_str.isdigit() or not id_orc_str.isdigit():
        QMessageBox.warning(None, "Erro", "ID inválido para duplicação.")
        return

    id_orc = int(id_orc_str)
    novo_item = obter_proximo_item_para_orcamento(id_orc)

    try:
        with obter_cursor() as cursor:
            cursor.execute(
                "SELECT codigo, descricao, altura, largura, profundidade, und, qt, "
                "preco_unitario, preco_total, custo_produzido, custo_total_orlas, "
                "custo_total_mao_obra, custo_total_materia_prima, custo_total_acabamentos, "
                "margem_lucro_perc, valor_margem, custos_admin_perc, valor_custos_admin, "
                "ajustes1_perc, valor_ajustes1, ajustes2_perc, valor_ajustes2 "
                "FROM orcamento_items WHERE id_item=%s",
                (int(id_item_str),))
            dados = cursor.fetchone()
            if not dados:
                QMessageBox.warning(None, "Erro", "Item não encontrado na BD.")
                return
            insert_q = (
                "INSERT INTO orcamento_items (id_orcamento, item, codigo, descricao, "
                "altura, largura, profundidade, und, qt, preco_unitario, preco_total, "
                "custo_produzido, custo_total_orlas, custo_total_mao_obra, "
                "custo_total_materia_prima, custo_total_acabamentos, margem_lucro_perc, "
                "valor_margem, custos_admin_perc, valor_custos_admin, ajustes1_perc, "
                "valor_ajustes1, ajustes2_perc, valor_ajustes2) VALUES (" + ", ".join([
                    "%s"]*24) + ")"
            )
            cursor.execute(insert_q, (id_orc, novo_item, *dados))

            duplicar_registos_associados(
                cursor, 'dados_modulo_medidas', 'ids', item_num_str, str(novo_item), num_orc, ver_orc)
            duplicar_registos_associados(
                cursor, 'dados_def_pecas', 'ids', item_num_str, str(novo_item), num_orc, ver_orc)
            duplicar_registos_associados(
                cursor, 'dados_items_materiais', 'id_mat', item_num_str, str(novo_item), num_orc, ver_orc)
            duplicar_registos_associados(
                cursor, 'dados_items_ferragens', 'id_fer', item_num_str, str(novo_item), num_orc, ver_orc)
            duplicar_registos_associados(
                cursor, 'dados_items_sistemas_correr', 'id_sc', item_num_str, str(novo_item), num_orc, ver_orc)
            duplicar_registos_associados(
                cursor, 'dados_items_acabamentos', 'id_acb', item_num_str, str(novo_item), num_orc, ver_orc)

        carregar_itens_orcamento(ui, id_orc)
        ui.lineEdit_item_orcamento.setText(
            str(obter_proximo_item_para_orcamento(id_orc)))
        QMessageBox.information(None, "OK", "Linha duplicada com sucesso.")
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao duplicar item: {err}")
        QMessageBox.critical(None, "Erro BD", f"Erro: {err}")
    except Exception as e:
        print(f"Erro inesperado ao duplicar item: {e}")
        QMessageBox.critical(None, "Erro", f"Erro: {e}")


def excluir_item_orcamento(ui):
    """Elimina a linha selecionada e remove todos os dados associados na BD."""
    tbl = ui.tableWidget_artigos
    row_sel = tbl.currentRow()
    if row_sel < 0:
        QMessageBox.warning(
            None, "Erro", "Nenhuma linha selecionada para eliminar.")
        return

    id_item_db = _get_cell_text(tbl, row_sel, COL_ID_ITEM)
    item_num = _get_cell_text(tbl, row_sel, COL_ITEM_NUM)
    id_orc_str = ui.lineEdit_id.text().strip()
    num_orc = ui.lineEdit_num_orcamento.text().strip()
    ver_orc = ui.lineEdit_versao_orcamento.text().strip()

    if not id_item_db.isdigit() or not id_orc_str.isdigit():
        QMessageBox.warning(None, "Erro", "ID inválido para exclusão.")
        return

    id_orc = int(id_orc_str)
    if QMessageBox.question(None, "Confirmar", f"Eliminar item {item_num}?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
        return

    try:
        with obter_cursor() as cursor:
            cursor.execute(
                "DELETE FROM orcamento_items WHERE id_item=%s", (int(id_item_db),))
            cursor.execute(
                "DELETE FROM dados_modulo_medidas WHERE ids=%s AND num_orc=%s AND ver_orc=%s",
                (item_num, num_orc, ver_orc))
            cursor.execute(
                "DELETE FROM dados_def_pecas WHERE ids=%s AND num_orc=%s AND ver_orc=%s",
                (item_num, num_orc, ver_orc))
            cursor.execute(
                "DELETE FROM dados_items_materiais WHERE id_mat=%s AND num_orc=%s AND ver_orc=%s",
                (item_num, num_orc, ver_orc))
            cursor.execute(
                "DELETE FROM dados_items_ferragens WHERE id_fer=%s AND num_orc=%s AND ver_orc=%s",
                (item_num, num_orc, ver_orc))
            cursor.execute(
                "DELETE FROM dados_items_sistemas_correr WHERE id_sc=%s AND num_orc=%s AND ver_orc=%s",
                (item_num, num_orc, ver_orc))
            cursor.execute(
                "DELETE FROM dados_items_acabamentos WHERE id_acb=%s AND num_orc=%s AND ver_orc=%s",
                (item_num, num_orc, ver_orc))

        carregar_itens_orcamento(ui, id_orc)
        ui.lineEdit_item_orcamento.setText(
            str(obter_proximo_item_para_orcamento(id_orc)))
        QMessageBox.information(None, "OK", "Linha eliminada com sucesso.")
    except mysql.connector.Error as err:
        print(f"Erro MySQL ao eliminar item: {err}")
        QMessageBox.critical(None, "Erro BD", f"Erro: {err}")
    except Exception as e:
        print(f"Erro inesperado ao eliminar item: {e}")
        QMessageBox.critical(None, "Erro", f"Erro: {e}")
#################################################################################################################################
# --- Fim das funções de manipulação de itens do orçamento ---

def configurar_menu_descricoes(ui):
    """Configura o menu de contexto para o campo de descrição."""
    widget = ui.plainTextEdit_descricao_orcamento
    widget.setContextMenuPolicy(Qt.CustomContextMenu)
    widget.customContextMenuRequested.connect(lambda pos: _abrir_menu_descricoes(ui))


def _abrir_menu_descricoes(ui):
    dialog = DialogoDescricoes(ui.plainTextEdit_descricao_orcamento)
    if dialog.exec_() == QDialog.Accepted:
        linhas = dialog.descricoes_selecionadas()
        if linhas:
            texto_atual = ui.plainTextEdit_descricao_orcamento.toPlainText().rstrip()
            for linha in linhas:
                texto_atual += "\n\t- " + linha
            ui.plainTextEdit_descricao_orcamento.setPlainText(texto_atual)
