# menu_grupos_def_pecas.py

import os
import pandas as pd
from PyQt5.QtWidgets import QMessageBox, QListWidgetItem, QAbstractItemView
from PyQt5.QtCore import Qt, QCoreApplication

#imagem-> menu_grupos_pecas.png

def atualizar_grupos_pecas(ui):
    """
    Atualiza os 6 QListWidget com os nomes das peças lidos do ficheiro Excel 'TAB_DEF_PECAS.XLSX'.

    O ficheiro Excel é procurado na pasta definida em ui.lineEdit_base_dados (após remover espaços).

    Como a tabela do Excel possui cabeçalho na linha 5 (header=4) e os dados começam na linha 6,
    a leitura é feita com header=4. Cada linha do ficheiro deve conter pelo menos as colunas:
      - A coluna 'GRUPO' define qual lista deve receber a peça (ex.: "caixote", "ferragens" etc.).
      - A coluna 'DEF_PECA' define o texto que aparecerá no QListWidget (ex.: "COSTA CHAPAR [0000]").
      - A coluna  'MAT_DEFAULT': valor que será armazenado para a coluna Mat_Default.
      - A coluna  'TAB_DEFAULT': valor que será armazenado para a coluna Tab_Default (ex.: "Tab_Material_11").
    
    Os grupos são mapeados para os QListWidget correspondentes:
      "caixote"            -> ui.listWidget_caixote_4
      "ferragens"          -> ui.listWidget_ferragens_4
      "mao_de_obra"           -> ui.listWidget_mao_obra_4
      "paineis"            -> ui.listWidget_paineis_4
      "remates_guarnicoes" -> ui.listWidget_remates_guarnicoes_4
      "sistemas_correr"    -> ui.listWidget_sistemas_correr_4
      "acabamentos"    -> ui.listWidget_acabamentos_4
    """
   # 1) Extrair a pasta do caminho do .db
    caminho_base = ui.lineEdit_base_dados.text().strip()
    folder_base = os.path.dirname(caminho_base)
    
    # 2) Montar caminho do Excel
    excel_file = os.path.join(folder_base, "TAB_DEF_PECAS.XLSX")

    # 3) Verificar existência
    if not os.path.exists(excel_file):
        QMessageBox.critical(ui.centralwidget, "Erro", f"Ficheiro {excel_file} não encontrado.")
        return

    # 4) Ler Excel (header na linha 5 – header=4)
    try:
        # Se sua planilha tem cabeçalho na linha 5, use header=4. Ajuste se necessário.
        df = pd.read_excel(excel_file, header=4)
    except Exception as e:
        QMessageBox.critical(ui.centralwidget, "Erro", f"Erro ao ler o ficheiro Excel:\n{str(e)}")
        return

    # 5) Mapeamento do nome do grupo -> QListWidget
    grupos_map = {
        "caixote": ui.listWidget_caixote_4,
        "ferragens": ui.listWidget_ferragens_4,
        "mao_de_obra": ui.listWidget_mao_obra_4,
        "paineis": ui.listWidget_paineis_4,
        "remates_guarnicoes": ui.listWidget_remates_guarnicoes_4,
        "sistemas_correr": ui.listWidget_sistemas_correr_4,
        "acabamentos": ui.listWidget_acabamentos_4
    }

    # 6) Limpar cada QListWidget
    for widget in grupos_map.values():
        widget.clear()

    # 7) Verificar se as colunas obrigatórias existem
    for coluna in ["GRUPO", "DEF_PECA", "MAT_DEFAULT", "TAB_DEFAULT"]:
        if coluna not in df.columns:
            QMessageBox.critical(ui.centralwidget, "Erro",
                f"O ficheiro Excel deve conter a coluna '{coluna}'.")
            return

    # 8) Preencher as listas
    for index, row in df.iterrows():
        # Grupo (caixote, ferragens, etc.)
        grupo_lower = str(row["GRUPO"]).strip().lower().replace(" ", "_")
        # Texto a exibir (ex.: "COSTA CHAPAR [0000]")
        texto_peca = str(row["DEF_PECA"]).strip()
        mat_default = str(row["MAT_DEFAULT"]).strip()
        tab_default = str(row["TAB_DEFAULT"]).strip()

        # Se o grupo estiver no dicionário, cria item checkable
        if grupo_lower in grupos_map:
            list_widget = grupos_map[grupo_lower]

            # Exemplo 1: criar item com checkbox real (checkable)
            item = QListWidgetItem(texto_peca)
            # Permitir check:
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable) # item.setFlags(item.flags() | Qt.ItemIsUserCheckable)   
            item.setCheckState(Qt.Unchecked)
            # Armazenar os dados extras:
            item.setData(Qt.UserRole + 1, mat_default)
            item.setData(Qt.UserRole + 2, tab_default)
            list_widget.addItem(item)

            # Exemplo 2 (alternativo): se quiser apenas prefixar "☐ ", sem checkbox real
            # item = "☐ " + texto_peca
            # list_widget.addItem(item)

    # 9) Mensagem de sucesso
    QMessageBox.information(ui.centralwidget, "Sucesso", "Grupos de peças atualizados com sucesso.")

    # 10)Reconstroi o dicionário de opções a partir dos QListWidget atualizados
    opcoes_por_grupo = {
        "caixote": [ui.listWidget_caixote_4.item(i).text() for i in range(ui.listWidget_caixote_4.count())],
        "ferragens": [ui.listWidget_ferragens_4.item(i).text() for i in range(ui.listWidget_ferragens_4.count())],
        "mao_obra": [ui.listWidget_mao_obra_4.item(i).text() for i in range(ui.listWidget_mao_obra_4.count())],
        "paineis": [ui.listWidget_paineis_4.item(i).text() for i in range(ui.listWidget_paineis_4.count())],
        "remates_guarnicoes": [ui.listWidget_remates_guarnicoes_4.item(i).text() for i in range(ui.listWidget_remates_guarnicoes_4.count())],
        "sistemas_correr": [ui.listWidget_sistemas_correr_4.item(i).text() for i in range(ui.listWidget_sistemas_correr_4.count())],
        "acabamentos": [ui.listWidget_acabamentos_4.item(i).text() for i in range(ui.listWidget_acabamentos_4.count())]
    }
    # Atualiza o delegate da tabela (para que os combobox sejam preenchidos com as opções atuais)
    from tabela_def_pecas_items import install_def_peca_delegate
    # Corrigido: passar a tabela como parent e o dicionário de opções separadamente
    install_def_peca_delegate(ui, ui.tab_def_pecas, opcoes_por_grupo)

def tornar_listwidget_clickavel(list_widget):
    """
    Configura o QListWidget para:
      - Destacar a linha selecionada.
      - Permitir que o clique em qualquer parte do item checkável alterne o estado de check.
    """
    # Modo de seleção: pode ser SingleSelection ou ExtendedSelection, conforme desejar
    list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
    list_widget.setSelectionBehavior(QAbstractItemView.SelectItems)

    # Função interna que alterna check ao clicar na linha
    def on_item_clicked(item):
        if item.flags() & Qt.ItemIsUserCheckable:
            if item.checkState() == Qt.Checked:
                item.setCheckState(Qt.Unchecked)
            else:
                item.setCheckState(Qt.Checked)

    # Conecta o sinal de clique
    list_widget.itemClicked.connect(on_item_clicked)

def conectar_botoes_configuracao(ui):
    """
    Conecta o botão 'Atualizar_Grupos_Pecas' ao método de atualização e
    ativa a funcionalidade de clique em cada QListWidget.
    """
    
    # Configurar cada QListWidget para alternar o check ao clicar na linha
    tornar_listwidget_clickavel(ui.listWidget_caixote_4)
    tornar_listwidget_clickavel(ui.listWidget_ferragens_4)
    tornar_listwidget_clickavel(ui.listWidget_mao_obra_4)
    tornar_listwidget_clickavel(ui.listWidget_paineis_4)
    tornar_listwidget_clickavel(ui.listWidget_remates_guarnicoes_4)
    tornar_listwidget_clickavel(ui.listWidget_sistemas_correr_4)
    tornar_listwidget_clickavel(ui.listWidget_acabamentos_4)

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow
    from orcamentos_le_layout import Ui_MainWindow
    
    app = QApplication(sys.argv)
    MainWindow = QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    
    conectar_botoes_configuracao(ui)
     
    sys.exit(app.exec_())