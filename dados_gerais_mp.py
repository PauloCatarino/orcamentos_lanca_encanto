"""
dados_gerais_mp.py
==================
Módulo para manipulação das tabelas de Dados Gerais.
Este módulo contém funções para:
  - Criar a tabela no banco de dados para cada tipo de dado geral (ex.: materiais, ferragens, etc.);
  - Configurar o QTableWidget para exibição dos dados, utilizando delegates para formatação (moeda e percentual);
  - Obter valores distintos de uma coluna (para preenchimento de QComboBox);
  - Conectar os botões individuais de cada aba para ações como guardar, importar e limpar dados;
  - Funções auxiliares para limpar linhas de tabelas.

Observação:
  Todas as operações de banco de dados utilizam MySQL, via a função get_connection() importada do módulo db_connection.py.
"""
import mysql.connector # Para capturar erros específicos
from PyQt5.QtWidgets import (QTableWidgetItem, QComboBox, QPushButton, QMessageBox, QHeaderView, QAbstractItemView, QInputDialog, QStyledItemDelegate, QLineEdit)
from PyQt5.QtCore import Qt

from dados_gerais_manager import obter_nome_para_salvar, guardar_dados_gerais, importar_dados_gerais_com_opcao
#from configurar_guardar_dados_gerais_orcamento import guardar_dados_gerais_orcamento
from utils import adicionar_menu_limpar

def executar_guardar_dados_orcamento(main_window):
    """Carrega dinamicamente a função de gravação e executa-a.

    A importação tardia evita um ciclo entre este módulo e
    configurar_guardar_dados_gerais_orcamento.
    """
    from configurar_guardar_dados_gerais_orcamento import (
        guardar_dados_gerais_orcamento,
    )
    guardar_dados_gerais_orcamento(main_window)

# --- Delegates para formatação de moeda e percentual ---

class CurrencyDelegate(QStyledItemDelegate):
    def displayText(self, value, locale):
        """
        Formata um valor numérico para exibição como moeda.
        Exibe com 2 casas decimais e o símbolo '€'.
        """
        try:
            num = float(value)
            return f"{num:.2f}€"
        except (ValueError, TypeError):
            return str(value)

class PercentageDelegate(QStyledItemDelegate):
    def displayText(self, value, locale):
        """
        Formata um valor numérico para exibição como percentual.
        Exibe sem casas decimais e o símbolo '%'.
        """
        try:
            num = float(value)
            return f"{num*100:.0f}%"
        except (ValueError, TypeError):
            return str(value)

def configurar_delegate_table(table_widget):
    """
    Configura os delegates para colunas específicas do QTableWidget, para formatação de moeda e percentual.
    """
    table_widget.setItemDelegateForColumn(7, CurrencyDelegate())
    table_widget.setItemDelegateForColumn(8, PercentageDelegate())
    table_widget.setItemDelegateForColumn(9, PercentageDelegate())
    table_widget.setItemDelegateForColumn(11, PercentageDelegate())

# --- Funções para configurar botões e ações nas abas de Dados Gerais ---

def on_mp_button_clicked(ui, row, nome_tabela):
    """
    Exemplo de função para manipulação de clique em botão.
    Exibe uma mensagem informando qual linha e tabela foram clicadas.
    """
    QMessageBox.information(ui, "Botão clicado", f"Botão da linha {row} da tabela {nome_tabela} foi clicado.")

def configurar_botoes_dados_gerais(main_window):
    """
    Configura os botões de cada aba de Dados Gerais (Materiais, Ferragens, Sistemas Correr, Acabamentos).
    Cada botão é conectado a funções específicas de guardar, importar e limpar dados.
    """
    # Aba Materiais
    try:
        btn_guardar_mat = main_window.ui.guardar_dados_gerais_material
        btn_importar_mat = main_window.ui.importar_dados_gerais_material
        btn_limpar_mat = main_window.ui.limpar_linha_material
        # Obter o botão específico para guardar os dados do orçamento
        btn_guardar_orcamento = main_window.ui.guardar_dados_gerais_orcamento

        btn_guardar_mat.clicked.connect(lambda: acao_guardar_dados(main_window, "materiais"))
        btn_importar_mat.clicked.connect(lambda: acao_importar_dados(main_window, "materiais"))
        btn_limpar_mat.clicked.connect(lambda: limpar_linha_por_tab(main_window, "materiais"))
        adicionar_menu_limpar(main_window.ui.Tab_Material, lambda: limpar_linha_por_tab(main_window, "materiais"))
        # Corrigindo a ligação: passando main_window.ui para a função e utilizando o botão definido
        btn_guardar_orcamento.clicked.connect(lambda: executar_guardar_dados_orcamento(main_window))
    except Exception as e:
        QMessageBox.warning(main_window, "Configuração Materiais", f"Erro: {e}")

    # Aba Ferragens
    try:
        btn_guardar_fer = main_window.ui.guardar_dados_gerais_ferragens
        btn_importar_fer = main_window.ui.importar_dados_gerais_ferragens
        btn_limpar_fer = main_window.ui.limpar_linha_ferragens

        btn_guardar_fer.clicked.connect(lambda: acao_guardar_dados(main_window, "ferragens"))
        btn_importar_fer.clicked.connect(lambda: acao_importar_dados(main_window, "ferragens"))
        btn_limpar_fer.clicked.connect(lambda: limpar_linha_por_tab(main_window, "ferragens"))
        adicionar_menu_limpar(main_window.ui.Tab_Ferragens, lambda: limpar_linha_por_tab(main_window, "ferragens"))
    except Exception as e:
        QMessageBox.warning(main_window, "Configuração Ferragens", f"Erro: {e}")

    # Aba Sistemas Correr
    try:
        btn_guardar_sc = main_window.ui.guardar_dados_gerais_sistemas_correr
        btn_importar_sc = main_window.ui.importar_dados_gerais_sistemas_correr
        btn_limpar_sc = main_window.ui.limpar_linha_sistemas_correr

        btn_guardar_sc.clicked.connect(lambda: acao_guardar_dados(main_window, "sistemas_correr"))
        btn_importar_sc.clicked.connect(lambda: acao_importar_dados(main_window, "sistemas_correr"))
        btn_limpar_sc.clicked.connect(lambda: limpar_linha_por_tab(main_window, "sistemas_correr"))
        adicionar_menu_limpar(main_window.ui.Tab_Sistemas_Correr,lambda: limpar_linha_por_tab(main_window, "sistemas_correr"))
    except Exception as e:
        QMessageBox.warning(main_window, "Configuração Sistemas Correr", f"Erro: {e}")

    # Aba Acabamentos
    try:
        btn_guardar_acab = main_window.ui.guardar_dados_gerais_acabamentos
        btn_importar_acab = main_window.ui.importar_dados_gerais_acabamentos
        btn_limpar_acab = main_window.ui.limpar_linha_acabamentos

        btn_guardar_acab.clicked.connect(lambda: acao_guardar_dados(main_window, "acabamentos"))
        btn_importar_acab.clicked.connect(lambda: acao_importar_dados(main_window, "acabamentos"))
        btn_limpar_acab.clicked.connect(lambda: limpar_linha_por_tab(main_window, "acabamentos"))
        adicionar_menu_limpar(main_window.ui.Tab_Acabamentos, lambda: limpar_linha_por_tab(main_window, "acabamentos"))
    except Exception as e:
        QMessageBox.warning(main_window, "Configuração Acabamentos", f"Erro: {e}")

def limpar_linha_por_tab(main_window, nome_tabela):
    """
    Limpa os dados da linha selecionada na tabela correspondente à aba especificada.
    Após limpar, a linha é deselecionada.
    """
    if nome_tabela == "materiais":
        table = main_window.ui.Tab_Material
        from dados_gerais_mp import COLUNAS_LIMPAR_MATERIAIS as cols
    elif nome_tabela == "ferragens":
        table = main_window.ui.Tab_Ferragens
        from dados_gerais_mp import COLUNAS_LIMPAR_FERRAGENS as cols
    elif nome_tabela == "sistemas_correr":
        table = main_window.ui.Tab_Sistemas_Correr
        from dados_gerais_mp import COLUNAS_LIMPAR_SISTEMAS_CORRER as cols
    elif nome_tabela == "acabamentos":
        table = main_window.ui.Tab_Acabamentos
        from dados_gerais_mp import COLUNAS_LIMPAR_ACABAMENTOS as cols
    else:
        QMessageBox.warning(main_window, "Limpar Linha", "Tabela não identificada.")
        return

    row = table.currentRow()
    if row >= 0:
        limpar_linha_dados_gerais(table, row, cols)
        # Mantém a linha ativa selecionada após a limpeza
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.selectRow(row)
        QMessageBox.information(main_window, "Limpar Linha", f"Linha {row+1} da aba '{nome_tabela}' limpa com sucesso.")
    else:
        QMessageBox.warning(main_window, "Limpar Linha", f"Nenhuma linha selecionada na aba '{nome_tabela}'.")

# --- Constantes de colunas a limpar para cada tipo de tabela ---
COLUNAS_LIMPAR_MATERIAIS = [1, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17, 18, 19]
COLUNAS_LIMPAR_FERRAGENS = [1, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17, 18, 19]
COLUNAS_LIMPAR_SISTEMAS_CORRER = [1, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17, 18, 19]
COLUNAS_LIMPAR_ACABAMENTOS = [1, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 17, 18, 19]

def limpar_linha_dados_gerais(table_widget, row_index, colunas_indices_limpar):
    """
    Limpa os valores de colunas específicas de uma linha do QTableWidget.
    Bloqueia sinais para evitar eventos desnecessários durante a limpeza.
    """
    from dados_gerais_materiais import original_pliq_values
    table_widget.blockSignals(True)
    for col_idx in colunas_indices_limpar:
        if table_widget.cellWidget(row_index, col_idx):
            widget = table_widget.cellWidget(row_index, col_idx)
            if isinstance(widget, QComboBox):
                widget.setCurrentIndex(-1)
            elif isinstance(widget, QLineEdit):
                widget.clear()
        else:
            item = table_widget.item(row_index, col_idx)
            if item:
                item.setText("")
    for col in [8, 9, 10]:
        if row_index in original_pliq_values:
            del original_pliq_values[row_index]
    table_widget.blockSignals(False)

def acao_guardar_dados(main_window, nome_tabela):
    """
    Para a tabela especificada (ex.: 'materiais' ou 'ferragens'), obtém interativamente
    o nome do modelo e chama a função de guardar os dados gerais.
    """
    if nome_tabela == "materiais":
        # Mapeamento já existente para a Tab_Materiais
        col_info = {
            1:  {"nome": "descricao", "type": "text"},
            5:  {"nome": "ref_le", "type": "text"},
            6:  {"nome": "descricao_no_orcamento", "type": "text"},
            7:  {"nome": "ptab", "type": "float", "percent": False},
            8:  {"nome": "pliq", "type": "float", "percent": False},
            9:  {"nome": "desc1_plus", "type": "float", "percent": True},
            10: {"nome": "desc2_minus", "type": "float", "percent": True},
            11: {"nome": "und", "type": "text"},
            12: {"nome": "desp", "type": "float", "percent": True},
            13: {"nome": "corres_orla_0_4", "type": "text"},
            14: {"nome": "corres_orla_1_0", "type": "text"},
            15: {"nome": "tipo", "type": "text"},
            16: {"nome": "familia", "type": "text"},
            17: {"nome": "comp_mp", "type": "float", "percent": False},
            18: {"nome": "larg_mp", "type": "float", "percent": False},
            19: {"nome": "esp_mp", "type": "float", "percent": False},
        }
        nome_escolhido, desc = obter_nome_para_salvar(main_window, "materiais")
        if not nome_escolhido:
            return
        guardar_dados_gerais(main_window, "materiais", col_info, nome_registro=nome_escolhido, descricao_registro=desc)

    elif nome_tabela == "ferragens":
        # Novo mapeamento para a Tab_Ferragens
        # Observação: a coluna 0 contém o nome da linha (definido por FERRAGENS_LINHAS) e
        # não é editável, por isso iniciamos com a coluna 1.
        col_info = {
            1:  {"nome": "descricao", "type": "text"},
            5:  {"nome": "ref_le", "type": "text"},
            6:  {"nome": "descricao_no_orcamento", "type": "text"},
            7:  {"nome": "ptab", "type": "float", "percent": False},
            8:  {"nome": "pliq", "type": "float", "percent": False},
            9:  {"nome": "desc1_plus", "type": "float", "percent": True},
            10: {"nome": "desc2_minus", "type": "float", "percent": True},
            11: {"nome": "und", "type": "text"},
            12: {"nome": "desp", "type": "float", "percent": True},
            13: {"nome": "corres_orla_0_4", "type": "text"},
            14: {"nome": "corres_orla_1_0", "type": "text"},
            15: {"nome": "tipo", "type": "text"},
            16: {"nome": "familia", "type": "text"},
            17: {"nome": "comp_mp", "type": "float", "percent": False},
            18: {"nome": "larg_mp", "type": "float", "percent": False},
            19: {"nome": "esp_mp", "type": "float", "percent": False},
        }
        # Solicita ao usuário um nome para salvar os dados de ferragens
        nome_escolhido, desc = obter_nome_para_salvar(main_window, "ferragens")
        if not nome_escolhido:
            return
        guardar_dados_gerais(main_window, "ferragens", col_info, nome_registro=nome_escolhido, descricao_registro=desc)

    elif nome_tabela == "sistemas_correr":
        # Para a aba Sistemas Correr, a estrutura é similar,
        # mas a primeira coluna (índice 0) é o nome da linha e não faz parte dos dados a serem salvos.
        col_info = {
            1:  {"nome": "descricao", "type": "text"},
            5:  {"nome": "ref_le", "type": "text"},
            6:  {"nome": "descricao_no_orcamento", "type": "text"},
            7:  {"nome": "ptab", "type": "float", "percent": False},
            8:  {"nome": "pliq", "type": "float", "percent": False},
            9:  {"nome": "desc1_plus", "type": "float", "percent": True},
            10: {"nome": "desc2_minus", "type": "float", "percent": True},
            11: {"nome": "und", "type": "text"},
            12: {"nome": "desp", "type": "float", "percent": True},
            13: {"nome": "corres_orla_0_4", "type": "text"},
            14: {"nome": "corres_orla_1_0", "type": "text"},
            15: {"nome": "tipo", "type": "text"},
            16: {"nome": "familia", "type": "text"},
            17: {"nome": "comp_mp", "type": "float", "percent": False},
            18: {"nome": "larg_mp", "type": "float", "percent": False},
            19: {"nome": "esp_mp", "type": "float", "percent": False},
        }
        nome_escolhido, desc = obter_nome_para_salvar(main_window, "sistemas_correr")
        if not nome_escolhido:
            return
        guardar_dados_gerais(main_window, "sistemas_correr", col_info, nome_registro=nome_escolhido, descricao_registro=desc)

    elif nome_tabela == "acabamentos":
            # Para a aba Acabaemntos, a estrutura é similar,
            # mas a primeira coluna (índice 0) é o nome da linha e não faz parte dos dados a serem salvos.
            col_info = {
                1:  {"nome": "descricao", "type": "text"},
                5:  {"nome": "ref_le", "type": "text"},
                6:  {"nome": "descricao_no_orcamento", "type": "text"},
                7:  {"nome": "ptab", "type": "float", "percent": False},
                8:  {"nome": "pliq", "type": "float", "percent": False},
                9:  {"nome": "desc1_plus", "type": "float", "percent": True},
                10: {"nome": "desc2_minus", "type": "float", "percent": True},
                11: {"nome": "und", "type": "text"},
                12: {"nome": "desp", "type": "float", "percent": True},
                13: {"nome": "corres_orla_0_4", "type": "text"},
                14: {"nome": "corres_orla_1_0", "type": "text"},
                15: {"nome": "tipo", "type": "text"},
                16: {"nome": "familia", "type": "text"},
                17: {"nome": "comp_mp", "type": "float", "percent": False},
                18: {"nome": "larg_mp", "type": "float", "percent": False},
                19: {"nome": "esp_mp", "type": "float", "percent": False},
            }
            nome_escolhido, desc = obter_nome_para_salvar(main_window, "acabamentos")
            if not nome_escolhido:
                return
            guardar_dados_gerais(main_window, "acabamentos", col_info, nome_registro=nome_escolhido, descricao_registro=desc)


    else:
        QMessageBox.information(main_window, "Info", f"Guardando para '{nome_tabela}' ainda não implementado.")


def acao_importar_dados(main_window, nome_tabela):
    """
    Importa os dados do banco para o QTableWidget de acordo com o mapeamento definido para a tabela.
    """

    if nome_tabela == "materiais":
        mapeamento = {
            'descricao': 1,
            'ref_le': 5,
            'descricao_no_orcamento': 6,
            'ptab': 7,
            'pliq': 8,
            'desc1_plus': 9,
            'desc2_minus': 10,
            'und': 11,
            'desp': 12,
            'corres_orla_0_4': 13,
            'corres_orla_1_0': 14,
            'tipo': 15,
            'familia': 16,
            'comp_mp': 17,
            'larg_mp': 18,
            'esp_mp': 19
        }
        importar_dados_gerais_com_opcao(main_window, "materiais", mapeamento)

    elif nome_tabela == "ferragens":
        mapeamento = {
            'descricao': 1,
            'ref_le': 5,
            'descricao_no_orcamento': 6,
            'ptab': 7,
            'pliq': 8,
            'desc1_plus': 9,
            'desc2_minus': 10,
            'und': 11,
            'desp': 12,
            'corres_orla_0_4': 13,
            'corres_orla_1_0': 14,
            'tipo': 15,
            'familia': 16,
            'comp_mp': 17,
            'larg_mp': 18,
            'esp_mp': 19
        }
        importar_dados_gerais_com_opcao(main_window, "ferragens", mapeamento)

    elif nome_tabela == "sistemas_correr":
        # Mapeamento específico para Sistemas de Correr.
        # Observe que a primeira coluna (índice 0) é o nome da linha e não deve ser incluída.
        mapeamento = {
            'descricao': 1,
            'ref_le': 5,
            'descricao_no_orcamento': 6,
            'ptab': 7,
            'pliq': 8,
            'desc1_plus': 9,
            'desc2_minus': 10,
            'und': 11,
            'desp': 12,
            'corres_orla_0_4': 13,
            'corres_orla_1_0': 14,
            'tipo': 15,
            'familia': 16,
            'comp_mp': 17,
            'larg_mp': 18,
            'esp_mp': 19
        }
        importar_dados_gerais_com_opcao(main_window, "sistemas_correr", mapeamento)

    elif nome_tabela == "acabamentos":
        mapeamento = {
            'descricao': 1,
            'ref_le': 5,
            'descricao_no_orcamento': 6,
            'ptab': 7,
            'pliq': 8,
            'desc1_plus': 9,
            'desc2_minus': 10,
            'und': 11,
            'desp': 12,
            'corres_orla_0_4': 13,
            'corres_orla_1_0': 14,
            'tipo': 15,
            'familia': 16,
            'comp_mp': 17,
            'larg_mp': 18,
            'esp_mp': 19
        }
        importar_dados_gerais_com_opcao(main_window, "acabamentos", mapeamento)
    else:
        QMessageBox.information(main_window, "Info", f"Importar para '{nome_tabela}' ainda não implementado.")        