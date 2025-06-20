r"""
main.py
=======
Módulo principal do software de orçamentos.
...
Módulo principal do software de orçamentos.
Este módulo integra e 
gura os diversos componentes da interface (...)
e conecta os módulos responsáveis por gerenciar:
  - Clientes
  - Orçamentos e itens de orçamento
  - Materiais-primas
  - Dados gerais (materiais, ferragens, etc.)
  - Configurações
  - Gestão de Módulos Pré-definidos:
    - Permite aos utilizadores gravar conjuntos de peças da 'tab_def_pecas' como módulos reutilizáveis.
    - Oferece uma interface para importar módulos guardados para o orçamento atual.
    - Disponibiliza um diálogo para visualizar, editar e eliminar módulos existentes.
    - Coordena a interação entre a UI, os diálogos de gestão de módulos e o módulo de acesso à base de dados de módulos.
Utiliza MySQL como banco de dados, por meio do módulo "db_connection.py", para todas as operações.

pyuic5 -x orcamentos_le_layout.ui -o orcamentos_le_layout.py

 Para enviar atualizações para o github
git status                # (opcional) ver o que mudou
git add .                 # adiciona todos os ficheiros alterados
git commit -m "73º Commit"
git push                  # envia para o GitHub
 ______________________________//________________________
git pull origin main
# (resolver conflitos, se houver)
git add .
git commit -m "102 Commit"
git push origin main


git push 
______________________________//________________________

crtl + swift + p    escolher  o interpretador -> Python 3.12.8(venv)

Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
 .\venv\Scripts\Activate.ps1

r
...
 r(venv) PS C:\Users\Utilizador\Documents\ORCAMENTOS_LE_V2\ORCAMENTO_V2\orcamentos_lanca_encanto> 
...

______________________________//________________________


"""

import modulo_dados_definicoes
# Configuração visual e eventos para a tabela 'tab_modulo_medidas'
from tab_modulo_medidas_formatacao import setup_tab_modulo_medidas
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QFileDialog, QHBoxLayout, QPushButton, QComboBox, QDialog, QTableWidgetItem, QVBoxLayout
# Importa o módulo de conexão com a base de dados
from PyQt5.QtCore import Qt, QTimer, QEvent, QObject
# Interface gerada pelo Qt Designer
from orcamentos_le_layout import Ui_MainWindow
from importar_dados_gerais_por_modelo import ImportarDadosGeralDialog


# Módulos de funcionalidades
from clientes import set_db_path, criar_tabela_clientes, conectar_clientes_ui
from orcamentos import configurar_orcamentos_ui
# Função para navegar com setas up/down entre os itens do orçamento dentro do separador 'Orcamento de Items'
from orcamento_items import configurar_orcamento_ui, navegar_item_orcamento, atualizar_custos_e_precos_itens, calcular_preco_final_orcamento
from configuracoes import configurar_configuracoes_ui
from materias_primas import conectar_materias_primas_ui

from dados_gerais_mp import configurar_botoes_dados_gerais
from dados_gerais_materiais import configurar_materiais_ui, on_item_changed_materiais
from dados_gerais_ferragens import configurar_ferragens_ui, on_item_changed_ferragens
from dados_gerais_sistemas_correr import configurar_sistemas_correr_ui, on_item_changed_sistemas_correr
from dados_gerais_acabamentos import configurar_acabamentos_ui, on_item_changed_acabamentos
from dados_gerais_manager import guardar_dados_gerais, importar_dados_gerais_com_opcao

from dados_items_materiais import configurar_tabela_material, inicializar_dados_items_material
from dados_items_ferragens import configurar_tabela_ferragens, inicializar_dados_items_ferragens
from dados_items_sistemas_correr import configurar_tabela_sistemas_correr, inicializar_dados_items_sistemas_correr
from dados_items_acabamentos import configurar_tabela_acabamentos, inicializar_dados_items_acabamentos

from relatorio_orcamento import gerar_relatorio_orcamento # Gerar relatórios do orçamento em PDF e Excel este é o módulo que gera os relatórios do orçamento em PDF e Excel,  e será enviado por mail
from dashboard_resumos_custos import mostrar_dashboard_resumos # Mostrar o dashboard de resumos de custos no separador 'Relatórios -> Resumo de Custos Orcamento'

# Atualiza os 6 QListWidget com os nomes das peças lidos do ficheiro Excel 'TAB_DEF_PECAS.XLSX'.
from menu_grupos_def_pecas import atualizar_grupos_pecas
# Configura os QListWidget para permitir a seleção de múltiplos itens e alternar o estado de check ao clicar na linha.
from tabela_def_pecas_items import configurar_selecao_qt_lists
# Adiciona linhas na tabela "tab_def_pecas" a partir de peças selecionadas nos 6 GRUPOS QListWidget
from tabela_def_pecas_items import (conectar_inserir_def_pecas_tab_items, inserir_pecas_selecionadas,setup_context_menu, on_item_changed_def_pecas,definir_larguras_iniciais)
# Importe a função calcular_orlas do módulo calculo_orlas e atualizar os preços e materias primas tab_def_pecas.
from modulo_orquestrador import atualizar_tudo

# Importar a função de conexão da lógica BLK
from controle_edicao_manual_blk import conectar_eventos_edicao_manual, on_cell_changed_for_blk_logic
# Função para obter o texto de um item de tabela, retornando uma string vazia se o item for None
from utils import safe_item_text, set_item, apply_row_selection_style
from relatorio_orcamento import on_gerar_relatorio_consumos_clicked # Gerar relatório de consumos no separador Relatorios -> Resumo de Consumos no Orcamento


# Modulo que trada Este módulo é responsável por todas as interações com a base de dados referentes à gravação, carregamento, e gestão de "Módulos Guardados".
import modulo_gestao_modulos_db
# Cria as tabelas 'dados_modulo_medidas' e 'dados_def_pecas' se não existirem.
# Esta chamada acontece uma vez quando o módulo main.py é carregado.
# Cria as tabelas 'modulos_guardados' e 'modulo_pecas_guardadas' se não existirem.
# Cria as tabelas 'modulos_guardados' e 'modulo_pecas_guardadas' se não existirem.
modulo_gestao_modulos_db.criar_tabelas_modulos()

# Cria as tabelas 'dados_modulo_medidas' e 'dados_def_pecas' se não existirem.
# Esta chamada acontece uma vez quando o módulo main.py é carregado.
modulo_dados_definicoes.criar_tabelas_definicoes()


class MainApp(QMainWindow):
    def __init__(self):
        """
        Construtor da classe principal da aplicação.
        Inicializa a UI e conecta todas as funcionalidades dos diferentes módulos.
        """
        super().__init__()
        # Inicializa a interface gráfica a partir do ficheiro gerado pelo Qt Designer
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # Configura o título da janela principal
        # Aplicar estilo de seleção de linha às principais tabelas
        for tbl in [
            self.ui.tableWidget_tabela_clientes,
            self.ui.tableWidget_orcamentos,
            self.ui.tableWidget_artigos,
            self.ui.tableWidget_materias_primas,
            self.ui.Tab_Material,
            self.ui.Tab_Ferragens,
            self.ui.Tab_Sistemas_Correr,
            self.ui.Tab_Acabamentos,
            self.ui.Tab_Material_11,
            self.ui.Tab_Ferragens_11,
            self.ui.Tab_Sistemas_Correr_11,
            self.ui.Tab_Acabamentos_12,
        ]:
            apply_row_selection_style(tbl)
        # Configurações visuais e de comportamento da UI
        self.ui.tab_artigos_11.setSelectionMode(
            self.ui.tab_artigos_11.SingleSelection)
        self.ui.tab_artigos_11.setStyleSheet(
            "QTreeWidget::item:selected { background-color: #F7DC6F; }")

        # Configuração do parâmetro da base de dados.
        # Embora em MySQL a conexão não seja baseada num arquivo, este campo pode ser usado
        # para armazenar informações de configuração ou para referência.
        self.configurar_base_dados()
        self.navegacao_index = 0   # Índice que indica qual item do QTreeWidget separador 'Orcaemnto de Items' está sendo exibido # Variável para controlar a navegação entre itens do orçamento
        # Inicializa os lineEdits de percentagem com valores por defeito
        # Estes valores de percentagem por defeito estão no separador Orcamento de Items e existe uma grupobox com o nome "Margens e Custos"
        self.ui.lineEdit_margem_lucro.setText("15%")
        self.ui.lineEdit_custos_administrativos.setText("5%")
        self.ui.lineEdit_ajustes_1.setText("3%")
        self.ui.lineEdit_ajustes_2.setText("2%")

        # Conectar funcionalidades do separador Clientes
        # # Separador Clientes
        try:
            conectar_clientes_ui(self.ui)
            # print("[INFO] Módulo Clientes conectado.")
        except Exception as e:
            print(f"[ERRO] Falha ao conectar módulo Clientes: {e}")
            QMessageBox.critical(self, "Erro de Inicialização",
                                 f"Falha ao configurar o módulo de Clientes:\n{e}")

        # Separador Consulta Orçamentos
        try:
            configurar_orcamentos_ui(self.ui)
        except Exception as e:
            print("Erro em configurar_orcamentos_ui:", e)

        # Conectar o separador "Orcamento" (itens de orçamento)
        # Separador Orçamento Items
        try:
            configurar_orcamento_ui(self)  # Configura a UI base do separador
            # Conecta botões de navegação entre itens do orçamento
            self.ui.botao_up_item.clicked.connect(
                lambda: navegar_item_orcamento(self, -1))
            self.ui.botao_down_item.clicked.connect(
                lambda: navegar_item_orcamento(self, 1))
            # print("[INFO] Módulo Orçamento Items conectado.")
        except Exception as e:
            print(f"[ERRO] Falha ao conectar módulo Orçamento Items: {e}")
            QMessageBox.critical(self, "Erro de Inicialização",
                                 f"Falha ao configurar o separador de Itens de Orçamento:\n{e}")

        # Separador Configurações
        try:
            configurar_configuracoes_ui(self.ui)
            # print("[INFO] Módulo Configurações conectado.")
        except Exception as e:
            print(f"[ERRO] Falha ao conectar módulo Configurações: {e}")
            QMessageBox.critical(self, "Erro de Inicialização",
                                 f"Falha ao configurar o módulo de Configurações:\n{e}")

        # Separador Matérias-Primas
        try:
            conectar_materias_primas_ui(self.ui)
            # print("[INFO] Módulo Matérias-Primas conectado.")
        except Exception as e:
            print(f"[ERRO] Falha ao conectar módulo Matérias-Primas: {e}")
            QMessageBox.critical(self, "Erro de Inicialização",
                                 f"Falha ao configurar o módulo de Matérias-Primas:\n{e}")

        # Configurar módulos de Dados Gerais (materiais, ferragens,Sistemas Correr, Acabamentos etc.)
        # --- Configuração dos Módulos de Dados Gerais ---
        # Cada um configura sua respectiva aba no separador "Dados Gerais"
        try:
            configurar_materiais_ui(self.ui)
            # print("[INFO] Módulo Dados Gerais - Materiais configurado.")
        except Exception as e:
            print(f"[ERRO] Falha ao configurar Dados Gerais - Materiais: {e}")

        try:
            # Conecta botões comuns de guardar/importar/limpar
            configurar_botoes_dados_gerais(self)
            # print("[INFO] Botões comuns de Dados Gerais conectados.")
        except Exception as e:
            print(f"[ERRO] Falha ao conectar botões de Dados Gerais: {e}")

        try:
            configurar_ferragens_ui(self.ui)
            # print("[INFO] Módulo Dados Gerais - Ferragens configurado.")
        except Exception as e:
            print(f"[ERRO] Falha ao configurar Dados Gerais - Ferragens: {e}")

        try:
            configurar_sistemas_correr_ui(self.ui)
            # print("[INFO] Módulo Dados Gerais - Sistemas Correr configurado.")
        except Exception as e:
            print(
                f"[ERRO] Falha ao configurar Dados Gerais - Sistemas Correr: {e}")

        try:
            configurar_acabamentos_ui(self.ui)
            # print("[INFO] Módulo Dados Gerais - Acabamentos configurado.")
        except Exception as e:
            print(
                f"[ERRO] Falha ao configurar Dados Gerais - Acabamentos: {e}")

        # --- Configuração dos Módulos de Dados de ITENS de Orçamento ---
        # Cada um configura sua respectiva aba no separador "Orcamento de Items"
        # Configuração da tabela de materiais para items específicos Dados Items (materiais, ferragens,Sistemas Correr, Acabamentos))
        try:
            configurar_tabela_material(self)
            # Aqui você conecta o botão de guardar dados dos itens
            inicializar_dados_items_material(self)
            # print("DEBUG: Tabela materiais dos items configurada com sucesso.")
        except Exception as e:
            print("Erro ao configurar tabela materiais dos items:", e)

        try:
            configurar_tabela_ferragens(self)
            # Aqui você conecta o botão de guardar dados dos itens
            inicializar_dados_items_ferragens(self)
            # print("DEBUG: Tabela ferragens dos items configurada com sucesso.")
        except Exception as e:
            print("Erro ao configurar tabela ferragens dos items:", e)

        try:
            configurar_tabela_sistemas_correr(self)
            # Aqui você conecta o botão de guardar dados dos itens
            inicializar_dados_items_sistemas_correr(self)
            # print("DEBUG: Tabela Sistemas Correr dos items configurada com sucesso.")
        except Exception as e:
            print("Erro ao configurar tabela sistemas Correr dos items:", e)

        try:
            configurar_tabela_acabamentos(self)
            # Aqui você conecta o botão de guardar dados dos itens
            inicializar_dados_items_acabamentos(self)
            # print("DEBUG: Tabela Acabamentos dos items configurada com sucesso.")
        except Exception as e:
            print("Erro ao configurar tabela Acabamentos dos items:", e)

        # --- Configuração da Tabela de Definição de Peças (tab_def_pecas) ---
        try:
            table_def_pecas = self.ui.tab_def_pecas  # Atalho para a tabela
            # Configura a tabela de Definição de Peças (tab_def_pecas) com os dados do banco
            # Preenche os QListWidget com opções do Excel
            atualizar_grupos_pecas(self.ui)
            conectar_inserir_def_pecas_tab_items(self.ui)  # Conecta botão "Inserir Peças"
            # Configura menu de contexto e delegates
            setup_context_menu(self.ui, None)
            definir_larguras_iniciais(self.ui)
            # Configura clique simples nos QListWidget
            configurar_selecao_qt_lists(self.ui)

            # conectar_eventos_edicao_manual(self.ui) # CONECTAR O cellChanged PARA A LÓGICA BLK
            # ----> CONEXÕES DE SINAIS CENTRALIZADAS AQUI <----
            # 1. Conectar cellChanged para a lógica BLK
            try:
                table_def_pecas.cellChanged.disconnect()
            except TypeError:
                pass
            # Passar self.ui corretamente para o lambda
            table_def_pecas.cellChanged.connect(
                lambda r, c: on_cell_changed_for_blk_logic(self.ui, r, c))

            # 2. Conectar itemChanged para formatação numérica imediata
            try:
                table_def_pecas.itemChanged.disconnect()
            except TypeError:
                pass
            table_def_pecas.itemChanged.connect(on_item_changed_def_pecas)
            print(
                "[INFO Main] Sinal itemChanged conectado a on_item_changed_def_pecas.")
            # -------------------------------------------------
            print("[INFO] Tabela Definição de Peças configurada.")

            # Configura eventos e formatação da tabela de medidas
            setup_tab_modulo_medidas(self.ui)
            print("[INFO] Tabela de Medidas configurada.")
        except Exception as e:
            print(f"[ERRO] Falha ao configurar Definição de Peças: {e}")
            QMessageBox.critical(self, "Erro de Inicialização",
                                 f"Falha ao configurar a tabela de Definição de Peças:\n{e}")

        # --- Conexão de Botões Globais de Ação ---

        # Conexão do botão "Inserir Peças Selecionadas"
        try:
            self.ui.Inserir_Pecas_Selecionadas.clicked.connect(
                lambda: inserir_pecas_selecionadas(self.ui))
            # print("[INFO] Botão 'Inserir Peças Selecionadas' conectado.")
        except Exception as e:
            print(
                f"[ERRO] Falha ao conectar botão Inserir Peças Selecionadas: {e}")

        # Botão "Atualizar Preços" (recalcula todos os dados de tab_def_pecas)
        try:
            self.ui.Atualizar_Precos.clicked.connect(
                lambda: atualizar_tudo(self.ui))
        except Exception as e:
            print(f"[ERRO] Falha ao conectar botão Atualizar_Precos: {e}")

        # NOVO: Conexão para o botão "Atualiza Preco Items Orcamento"
        # Este botão irá disparar o cálculo e atualização de todas as colunas de custo e preço por item.
        # Por padrão, não força a margem global.
        # Após a atualização dos itens, recalcula o preço final do orçamento.
        self.ui.pushButton_atualiza_preco_items.clicked.connect(
            lambda: (
                # Atualiza os custos e preços de cada item. Não força a margem global.
                atualizar_custos_e_precos_itens(
                    self.ui, force_global_margin_update=False),
                # Após todos os itens estarem recalculados, atualiza o preço final global.
                # A função calcular_preco_final_orcamento, neste caso, apenas somará os totais.
                calcular_preco_final_orcamento(self.ui)
            )
        )

        # NOVO/MODIFICADO: Conexão para o botão "Atualiza Preco Final"
        # Este botão recalcula o preço final do orçamento, e pode ajustar a margem.
        # A função calcular_preco_final_orcamento agora lida com a lógica de ajuste
        # proporcional das margens e a atualização do preço final.
        self.ui.pushButton_atualiza_preco_final.clicked.connect(
            lambda: calcular_preco_final_orcamento(self.ui))

        # Botão "Guardar Dados Items" (salva tabelas tab_modulo_medidas e tab_def_pecas)
        try:
            # As funções chamadas já usam obter_cursor internamente
            self.ui.Guardar_Dados_Items.clicked.connect(
                lambda: (
                    print("[INFO] A guardar dados das medidas e peças..."),
                    modulo_dados_definicoes.salvar_dados_modulo_medidas(
                        self.ui),
                    modulo_dados_definicoes.salvar_dados_def_pecas(self.ui)
                    # A mensagem de sucesso é agora mostrada pela própria função salvar_dados_def_pecas
                    # QMessageBox.information(self, "Sucesso", "Dados guardados no banco.")
                )
            )
            # print("[INFO] Botão Guardar Dados Items conectado.")
        except Exception as e:
            print(f"[ERRO] Falha ao conectar botão Guardar Dados Items: {e}")

        # --- Conexão dos Novos Botões "Guardar Modulo" e "Importar Modulo" e "Gerir Modulos Guardados" dentro separador 'Orcamento de Items'---
        # --- Conexão dos Novos Botões "Guardar Modulo", "Importar Modulo" e "Gerir Modulo" ---
        try:
            # Botão para Guardar Módulos
            if hasattr(self.ui, 'Guardar_Modulo'):
                self.ui.Guardar_Modulo.clicked.connect(
                    self.on_guardar_modulo_clicked)
                print("[INFO Main] Botão 'Guardar_Modulo' conectado.")
            else:
                print("[AVISO Main] Botão 'Guardar_Modulo' não encontrado na UI.")

            # Botão para Importar Módulos
            if hasattr(self.ui, 'Importar_Modulo'):
                self.ui.Importar_Modulo.clicked.connect(
                    self.on_importar_modulo_clicked)
                print("[INFO Main] Botão 'Importar_Modulo' conectado.")
            else:
                print("[AVISO Main] Botão 'Importar_Modulo' não encontrado na UI.")

            # Botão para Gerir Módulos Guardados
            if hasattr(self.ui, 'Gerir_Modulo'):
                self.ui.Gerir_Modulo.clicked.connect(
                    self.on_gerir_modulos_clicked)
                print("[INFO Main] Botão 'Gerir_Modulo' conectado.")
            else:
                # Se o nome do botão for diferente, ajuste a string aqui também
                print(
                    "[AVISO Main] Botão 'Gerir_Modulo' (ou nome esperado) não encontrado na UI. Funcionalidade de gestão não conectada.")

            # print("[INFO Main] Botões de gestão de módulos parcialmente conectados.") # Pode remover ou ajustar esta linha

        except AttributeError as ae:
            print(
                f"[ERRO Main ATTRIBUTE] Falha ao conectar botões de gestão de módulos: {ae}. Verifique os nomes dos botões na UI.")
        except Exception as e:
            print(
                f"[ERRO Main] Falha geral ao conectar botões de gestão de módulos: {e}")

        # /////////////////////////////////////////////////

        # Conectar sinais de alteração das tabelas de Dados Gerais (opcional, se necessário reagir a mudanças)
        try:
            self.ui.Tab_Material.itemChanged.connect(on_item_changed_materiais)
            self.ui.Tab_Ferragens.itemChanged.connect(
                on_item_changed_ferragens)
            self.ui.Tab_Sistemas_Correr.itemChanged.connect(
                on_item_changed_sistemas_correr)
            self.ui.Tab_Acabamentos.itemChanged.connect(
                on_item_changed_acabamentos)
            # print("[INFO] Sinais itemChanged das tabelas de Dados Gerais conectados.")
        except Exception as e:
            print(
                f"[ERRO] Falha ao conectar sinais itemChanged de Dados Gerais: {e}")

        # Este botão permite importar dados gerais de todos os 4 separadores e preencher as 4 tabelas
        # (Materiais, Ferragens, Sistemas Correr e Acabamentos) de uma só vez.
        # O botão "Importar Dados Gerais" chama a função abrirImportarDialog, que abre o dialogo de importação
        try:
            self.ui.importar_dados_gerais_4_separadores.clicked.connect(
                self.abrirImportarDialog)
            # print("[INFO] Botão Importar Dados Gerais conectado.")
        except Exception as e:
            print(f"[ERRO] Falha ao conectar botão Importar Dados Gerais: {e}")

        # Botão para gerar relatório em PDF e Excel
        try:
            btn = getattr(self.ui, 'pushButton_Export_PDF_Relatorio', None)
            if btn is not None:
                btn.clicked.connect(lambda: gerar_relatorio_orcamento(self.ui))
                print("[INFO] Botão 'Exportar PDF e Excel Orçamento' conectado.")
            else:
                print("[AVISO] Botão 'Exportar PDF e Excel Orçamento' não encontrado na UI.")
        except Exception as e:
            print(f"[ERRO] Falha ao conectar botão Exportar PDF/Excel: {e}")

        # Botão para gerar relatório de consumos que está no separador "Relatórios -> Resumo de Consumos no Orcamento"
        btn_consumos = getattr(self.ui, "pushButton_Gerar_Relatorio_Consumos", None)
        if btn_consumos is not None:
            # A conexão agora aponta para a função correta
            btn_consumos.clicked.connect(lambda: on_gerar_relatorio_consumos_clicked(self.ui))
            print("[INFO] Botão 'Gerar Relatório de Consumos' conectado.")
        else:
            print("[AVISO] Botão 'Gerar Relatório de Consumos' não encontrado na UI.")

        # !! ALTERAÇÃO CRUCIAL !!
        # Adicionar um layout ao QWidget 'frame_resumos' para que possa receber o dashboard.
        if self.ui.frame_resumos.layout() is None:
            layout_resumos = QVBoxLayout(self.ui.frame_resumos)
            self.ui.frame_resumos.setLayout(layout_resumos)
            print("[INFO Main] Layout para o dashboard de resumos foi configurado.")

        print("--- Inicialização da UI Concluída ---")

    def abrirImportarDialog(self):
        """Abre o diálogo para importar dados gerais de um ficheiro modelo."""
        dialog = ImportarDadosGeralDialog(
            self, self)  # Passa a instância de MainApp como parent
        dialog.exec_()

    def on_item_changed(self, item):
        # Perceber se pode ser removida esta funcao: on_item_changed(self, item) - Função genérica movida para os módulos específicos se necessário
        """
        Função chamada quando um item na tabela de Materiais é alterado.
        Esta função pode ser utilizada para depuração ou processamento adicional.
        """
        print(f"Item alterado: {item.text()}")

    def configurar_base_dados(self):
        """
        Configura o parâmetro da base de dados utilizando o campo de configuração na interface.
        Em MySQL, a conexão é feita via parâmetros definidos no módulo db_connection.py.
        Aqui, o campo lineEdit_base_dados pode ser usado para armazenar informações adicionais ou
        para fins de referência.
        """
        # Inicializa o parâmetro a partir do campo da interface
        set_db_path(self.ui.lineEdit_base_dados)
        # Atualiza o caminho se o texto no lineEdit mudar
        self.ui.lineEdit_base_dados.textChanged.connect(
            lambda: set_db_path(self.ui.lineEdit_base_dados))

        # Cria a tabela de clientes (a função em clientes.py deve usar obter_cursor)
        try:
            criar_tabela_clientes()  # Assumindo que esta função foi refatorada em clientes.py
            # print("[INFO] Tabela Clientes verificada/criada.")
        except Exception as e:
            print(f"[ERRO] Falha ao criar/verificar tabela Clientes: {e}")
            QMessageBox.critical(self, "Erro Crítico de Base de Dados",
                                 f"Falha na inicialização da tabela de Clientes:\n{e}")

    # As 2 funções seguintes dizem respeito a funcionalidades . Para guardar ou importar módulos. para tab_def_peças
    # def on_importar_modulo_clicked_placeholder(self):
    # def on_guardar_modulo_clicked(self):

    # --- Funções Placeholder para os botões guardar_modulo & importar_modulo ---

    def on_guardar_modulo_clicked(self):

        # 1. Verificar linhas selecionadas com checkbox "Gravar_Modulo"
        # 2. Coletar dados das linhas
        # 3. Abrir o DialogoGravarModulo
        # 4. Chamar modulo_gestao_modulos_db.salvar_novo_modulo ou atualizar_modulo_existente
        """
        Chamado quando o botão "Guardar Modulo" é clicado.
        Coleta as linhas marcadas para gravação e abre o diálogo para nomear e salvar o módulo.
        """
        print("[INFO Main] Botão 'Guardar Módulo' clicado.")
        table = self.ui.tab_def_pecas
        pecas_para_gravar = []
        linhas_selecionadas_indices = []  # Para saber a ordem original

        # --- Identificar as colunas pelos seus nomes/índices ---
        IDX_GRAVAR_MODULO_CHK = 53  # Coluna do checkbox "Gravar_Modulo"
        IDX_DESCRICAO_LIVRE = 1
        IDX_DEF_PECA_MOD = 2      # Renomeado para evitar conflito com a constante global
        IDX_QT_UND_MOD = 5        # Renomeado
        IDX_COMP_MOD = 6          # Renomeado
        IDX_LARG_MOD = 7          # Renomeado
        IDX_ESP_MOD = 8           # Renomeado
        IDX_MAT_DEFAULT_MOD = 13  # Renomeado
        IDX_TAB_DEFAULT_MOD = 14  # Renomeado
        IDX_UND_MOD = 24          # Renomeado
        IDX_COMP_ASS_1 = 34  # Componente Associado na coluna 34 tab_def_pecas
        IDX_COMP_ASS_2 = 35
        IDX_COMP_ASS_3 = 36

        for row in range(table.rowCount()):
            item_chk = table.item(row, IDX_GRAVAR_MODULO_CHK)
            if item_chk and item_chk.checkState() == Qt.Checked:
                # Guardar o índice original da linha
                linhas_selecionadas_indices.append(row)

                peca_dados = {
                    # Ordem baseada na sequência de seleção
                    "ordem_peca": len(pecas_para_gravar),
                    "descricao_livre_peca": safe_item_text(table, row, IDX_DESCRICAO_LIVRE),
                    "def_peca_peca": safe_item_text(table, row, IDX_DEF_PECA_MOD),
                    # Guardar como texto
                    "qt_und_peca": safe_item_text(table, row, IDX_QT_UND_MOD),
                    # Guardar como texto
                    "comp_peca": safe_item_text(table, row, IDX_COMP_MOD),
                    # Guardar como texto
                    "larg_peca": safe_item_text(table, row, IDX_LARG_MOD),
                    # Guardar como texto
                    "esp_peca": safe_item_text(table, row, IDX_ESP_MOD),
                    "mat_default_peca": safe_item_text(table, row, IDX_MAT_DEFAULT_MOD),
                    "tab_default_peca": safe_item_text(table, row, IDX_TAB_DEFAULT_MOD),
                    "und_peca": safe_item_text(table, row, IDX_UND_MOD),
                    "comp_ass_1_peca": safe_item_text(table, row, IDX_COMP_ASS_1),
                    "comp_ass_2_peca": safe_item_text(table, row, IDX_COMP_ASS_2),
                    "comp_ass_3_peca": safe_item_text(table, row, IDX_COMP_ASS_3)
                }

                # Obter o 'grupo_peca' do UserRole da célula Def_Peca
                item_def_peca = table.item(row, IDX_DEF_PECA_MOD)
                if item_def_peca and item_def_peca.data(Qt.UserRole):
                    peca_dados["grupo_peca"] = item_def_peca.data(Qt.UserRole)
                else:
                    # Default se não houver grupo
                    peca_dados["grupo_peca"] = ""

                pecas_para_gravar.append(peca_dados)

        if not pecas_para_gravar:
            QMessageBox.information(self, "Nenhuma Peça Selecionada",
                                    "Por favor, marque as caixas de seleção na coluna 'Gravar_Modulo' "
                                    "das linhas que deseja incluir no módulo.")
            return

        print(
            f"[INFO Main] {len(pecas_para_gravar)} peças marcadas para gravação no módulo.")

        # Importar e mostrar o diálogo (será criado no próximo passo)
        try:
            from dialogo_gravar_modulo import DialogoGravarModulo
            dialog = DialogoGravarModulo(pecas_para_gravar, parent=self)
            if dialog.exec_() == QDialog.Accepted:
                print(
                    "[INFO Main] Módulo gravado com sucesso (ou operação concluída no diálogo).")
                # Opcional: Desmarcar os checkboxes após gravação bem-sucedida
                for row_idx in linhas_selecionadas_indices:
                    item_chk = table.item(row_idx, IDX_GRAVAR_MODULO_CHK)
                    if item_chk:
                        item_chk.setCheckState(Qt.Unchecked)
            else:
                print(
                    "[INFO Main] Operação de gravar módulo cancelada pelo utilizador.")
        except ImportError:
            QMessageBox.critical(
                self, "Erro", "O ficheiro 'dialogo_gravar_modulo.py' não foi encontrado.")
            print("[ERRO Main] Falha ao importar DialogoGravarModulo.")
        except Exception as e:
            QMessageBox.critical(
                self, "Erro", f"Erro ao abrir o diálogo de gravação de módulo: {e}")
            print(
                f"[ERRO Main] Erro ao instanciar/executar DialogoGravarModulo: {e}")
            import traceback
            traceback.print_exc()

    def on_importar_modulo_clicked(self):
        """
        Abre o diálogo para o utilizador selecionar um módulo guardado e,
        se selecionado, importa as suas peças para a tab_def_pecas.
        """

        # Aqui virá a lógica para:
        # 1. Abrir o DialogoImportarModulo
        # 2. Obter o módulo selecionado
        # 3. Chamar modulo_gestao_modulos_db.obter_pecas_de_modulo
        # 4. Inserir as peças na tab_def_pecas
        # 5. Chamar atualizar_tudo(self.ui)
        print("[INFO Main] Botão 'Importar Módulo' clicado.")

        # --- Identificar as colunas pelos seus nomes/índices ---
        IDX_DEF_PECA = 2      # Renomeado para evitar conflito com a constante global
        IDX_COMP_ASS_1 = 34  # Componente Associado na coluna 34 tab_def_pecas
        IDX_COMP_ASS_2 = 35
        IDX_COMP_ASS_3 = 36

        try:
            from dialogo_importar_modulo import DialogoImportarModulo
            # from tabela_def_pecas_items import inserir_linha_componente # Não usamos mais esta diretamente aqui
            from modulo_orquestrador import atualizar_tudo
            from modulo_componentes_associados import COLOR_ASSOCIATED_BG, COLOR_PRIMARY_WITH_ASS_BG, COLOR_MODULO_BG

            dialog = DialogoImportarModulo(parent=self)
            if dialog.exec_() == QDialog.Accepted:
                id_modulo_a_importar = dialog.get_selected_module_id()
                if id_modulo_a_importar is None:
                    QMessageBox.warning(
                        self, "Seleção Inválida", "Nenhum módulo foi selecionado para importação.")
                    return

                print(
                    f"[INFO Main] Importando peças do módulo ID: {id_modulo_a_importar}")
                pecas_do_modulo = modulo_gestao_modulos_db.obter_pecas_de_modulo(
                    id_modulo_a_importar)

                if not pecas_do_modulo:
                    QMessageBox.information(
                        self, "Módulo Vazio", f"O módulo selecionado (ID: {id_modulo_a_importar}) não contém peças.")
                    return

                table = self.ui.tab_def_pecas
                primeira_linha_importada = table.rowCount()  # Índice da primeira nova linha

                table.blockSignals(True)
                try:
                    for peca_data in pecas_do_modulo:
                        new_row = table.rowCount()
                        table.insertRow(new_row)

                        set_item(table, new_row, 1, peca_data.get(
                            "descricao_livre_peca", ""))

                        item_def_peca = QTableWidgetItem(
                            peca_data.get("def_peca_peca", ""))
                        item_def_peca.setData(
                            Qt.UserRole, peca_data.get("grupo_peca", ""))
                        table.setItem(new_row, IDX_DEF_PECA,
                                      item_def_peca)  # Usar constante

                        set_item(table, new_row, 5,
                                 peca_data.get("qt_und_peca", "1"))
                        set_item(table, new_row, 6,
                                 peca_data.get("comp_peca", ""))
                        set_item(table, new_row, 7,
                                 peca_data.get("larg_peca", ""))
                        set_item(table, new_row, 8,
                                 peca_data.get("esp_peca", ""))

                        for col_chk_idx in [9, 10, 11, 12, 53, 59, 60]:
                            chk = QTableWidgetItem()
                            chk.setFlags(Qt.ItemIsUserCheckable |
                                         Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                            # Por padrão, módulos importados não vêm com BLK ativo
                            chk.setCheckState(Qt.Unchecked)
                            table.setItem(new_row, col_chk_idx, chk)

                        set_item(table, new_row, 13, peca_data.get(
                            "mat_default_peca", ""))
                        set_item(table, new_row, 14, peca_data.get(
                            "tab_default_peca", ""))

                        set_item(table, new_row, 15,
                                 self.ui.lineEdit_item_orcamento.text().strip())
                        set_item(table, new_row, 16,
                                 self.ui.lineEdit_num_orcamento.text().strip())
                        set_item(table, new_row, 17,
                                 self.ui.lineEdit_versao_orcamento.text().strip())

                        set_item(table, new_row, 24,
                                 peca_data.get("und_peca", ""))

                        btn = QPushButton("Escolher")
                        # Correção na conexão do botão para usar self.on_mp_button_clicked
                        btn.clicked.connect(
                            lambda _, r=new_row: self.on_mp_button_clicked(r, "tab_def_pecas"))
                        table.setCellWidget(new_row, 33, btn)

                        # As colunas COMP_ASS_X (34,35,36) também devem ser preenchidas se existirem nos dados guardados.
                        # Assumindo que `peca_data` pode ter estas chaves (precisa ser adicionado ao salvar):
                        set_item(table, new_row, IDX_COMP_ASS_1,
                                 peca_data.get("comp_ass_1_peca", ""))
                        set_item(table, new_row, IDX_COMP_ASS_2,
                                 peca_data.get("comp_ass_2_peca", ""))
                        set_item(table, new_row, IDX_COMP_ASS_3,
                                 peca_data.get("comp_ass_3_peca", ""))

                        print(
                            f"  Peça '{peca_data.get('def_peca_peca')}' adicionada à tab_def_pecas na linha {new_row+1}")

                    # --- APLICAR CORES INICIAIS ÀS LINHAS IMPORTADAS ---
                    # Isto ajuda o orquestrador a identificar corretamente os associados no primeiro ciclo.
                    ultima_principal_importada = -1
                    comps_da_ultima_principal_importada = set()
                    cor_fundo_padrao_tabela = table.palette().base()

                    for r_imp in range(primeira_linha_importada, table.rowCount()):
                        item_def_peca_imp = table.item(r_imp, IDX_DEF_PECA)
                        if not item_def_peca_imp:
                            continue

                        texto_def_peca_imp = item_def_peca_imp.text().strip().upper()
                        cor_a_aplicar_linha_imp = cor_fundo_padrao_tabela  # Default

                        if texto_def_peca_imp == "MODULO":
                            cor_a_aplicar_linha_imp = COLOR_MODULO_BG
                            ultima_principal_importada = -1
                            comps_da_ultima_principal_importada.clear()
                        else:
                            e_associado_neste_bloco = False
                            if ultima_principal_importada != -1 and \
                               r_imp > ultima_principal_importada and \
                               texto_def_peca_imp in comps_da_ultima_principal_importada:
                                e_associado_neste_bloco = True

                            if e_associado_neste_bloco:
                                cor_a_aplicar_linha_imp = COLOR_ASSOCIATED_BG
                            else:  # Nova principal dentro do bloco importado
                                ultima_principal_importada = r_imp
                                comps_da_ultima_principal_importada.clear()
                                c1 = safe_item_text(
                                    table, r_imp, IDX_COMP_ASS_1).strip().upper()
                                c2 = safe_item_text(
                                    table, r_imp, IDX_COMP_ASS_2).strip().upper()
                                c3 = safe_item_text(
                                    table, r_imp, IDX_COMP_ASS_3).strip().upper()
                                if c1:
                                    comps_da_ultima_principal_importada.add(c1)
                                if c2:
                                    comps_da_ultima_principal_importada.add(c2)
                                if c3:
                                    comps_da_ultima_principal_importada.add(c3)

                                if comps_da_ultima_principal_importada:
                                    cor_a_aplicar_linha_imp = COLOR_PRIMARY_WITH_ASS_BG

                        for c_col in range(table.columnCount()):
                            item_celula = table.item(
                                r_imp, c_col) or QTableWidgetItem()
                            if table.item(r_imp, c_col) is None:
                                table.setItem(r_imp, c_col, item_celula)
                            item_celula.setBackground(cor_a_aplicar_linha_imp)
                    print(
                        "[INFO Main] Cores iniciais aplicadas às linhas do módulo importado.")
                    # --- FIM DA APLICAÇÃO DE CORES INICIAIS ---

                finally:
                    table.blockSignals(False)

                from tabela_def_pecas_items import update_ids
                update_ids(table)
                print(
                    "[INFO Main] Módulo importado. Chamando o orquestrador para processar...")
                # Pequeno delay para garantir que a UI atualiza antes do processamento pesado
                QTimer.singleShot(10, lambda: atualizar_tudo(self.ui))
                QMessageBox.information(self, "Importação Concluída",
                                        f"O módulo foi importado com {len(pecas_do_modulo)} peças.")
            else:
                print("[INFO Main] Importação de módulo cancelada.")

        except ImportError as ie:
            QMessageBox.critical(self, "Erro de Importação de Módulo",
                                 f"Erro ao carregar componentes do diálogo: {ie}\nVerifique se 'dialogo_importar_modulo.py' está no local correto.")
            print(
                f"[ERRO Main] Falha ao importar DialogoImportarModulo ou suas dependências: {ie}")
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Importar",
                                 f"Ocorreu um erro ao importar o módulo: {e}")
            print(f"[ERRO Main] Erro ao importar módulo: {e}")
            import traceback
            traceback.print_exc()

    # Certifique-se que o método on_mp_button_clicked existe em MainApp ou é importado corretamente
    # Se on_mp_button_clicked está em tabela_def_pecas_items.py, a chamada seria:
    from tabela_def_pecas_items import on_mp_button_clicked
    # btn.clicked.connect(lambda _, r=new_row: on_mp_button_clicked(self.ui, r, "tab_def_pecas"))

    def on_gerir_modulos_clicked(self):
        """
        Abre o diálogo para gerir os módulos guardados (listar, editar, eliminar).
        """
        print("[INFO Main] Botão 'Gerir Módulos Guardados' clicado.")
        try:
            from dialogo_gerir_modulos import DialogoGerirModulos
            dialog = DialogoGerirModulos(parent=self)
            dialog.exec_()  # Abre o diálogo modalmente
            # A lógica de recarregar/atualizar após edições/eliminações está dentro do próprio diálogo.
        except ImportError:
            QMessageBox.critical(
                self, "Erro", "O ficheiro 'dialogo_gerir_modulos.py' não foi encontrado.")
            print("[ERRO Main] Falha ao importar DialogoGerirModulos.")
        except Exception as e:
            QMessageBox.critical(
                self, "Erro", f"Erro ao abrir o diálogo de gestão de módulos: {e}")
            print(
                f"[ERRO Main] Erro ao instanciar/executar DialogoGerirModulos: {e}")
            import traceback
            traceback.print_exc()


# Bloco principal de execução
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication, QVBoxLayout
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec_())
