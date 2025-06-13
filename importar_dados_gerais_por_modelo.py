"""
importar_dados_gerais_por_modelo.py
====================================

Módulo responsável por apresentar um diálogo para importar modelos de Dados Gerais
para os 4 separadores (Material, Ferragens, Sistemas Correr, Acabamentos).

Contém a classe `ImportarDadosGeralDialog` que permite ao utilizador selecionar
modelos guardados para cada tipo de Dados Gerais e importá-los para as respetivas
tabelas na interface da aplicação.

Funcionalidades principais:
  - Apresenta um diálogo modal com listas de modelos guardados para cada separador
    de Dados Gerais.
  - Permite a seleção de um ou mais modelos para importação.
  - Ao confirmar, importa os dados do primeiro modelo selecionado para cada
    separador, utilizando a função `importar_dados_gerais_por_modelo` do módulo
    `dados_gerais_manager.py`.
  - Exibe mensagens informativas de sucesso ou aviso ao utilizador.

Classes:
  - `ImportarDadosGeralDialog`: Diálogo para importação de Dados Gerais.
"""
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGroupBox, QListWidget, QListWidgetItem, QHBoxLayout, QPushButton, QMessageBox, QLabel
from PyQt5.QtCore import Qt
from dados_gerais_manager import listar_nomes_descricoes_dados_gerais

class ImportarDadosGeralDialog(QDialog):
    def __init__(self, main_window, parent=None): # Modified: Accept main_window instead of ui
        super().__init__(parent)
        self.main_window = main_window # Modified: Store main_window
        self.ui = main_window.ui # Keep ui for accessing UI elements, but use main_window for parent purposes
        self.setWindowTitle("Importar Dados Gerais dos 4 Separadores")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)

        # Dicionário para armazenar as listas para cada tabela
        self.listas = {}
        self.descricoes = {}
        self.labels_desc = {}
        # Para cada tabela, cria um QGroupBox com um QListWidget
        tabelas = [
            ("materiais", "Material"),
            ("ferragens", "Ferragens"),
            ("sistemas_correr", "Sistemas Correr"),
            ("acabamentos", "Acabamentos")
        ]
        for tabela, titulo in tabelas:
            group = QGroupBox(titulo)
            group_layout = QVBoxLayout(group)
            lista = QListWidget()
            lista.setSelectionMode(QListWidget.SingleSelection)
            nomes_desc = listar_nomes_descricoes_dados_gerais(tabela, somente_completos=True)
            self.descricoes[tabela] = nomes_desc
            for nome, desc in nomes_desc.items():
                item = QListWidgetItem(nome)
                item.setData(Qt.UserRole, nome)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                lista.addItem(item)
            lista.itemChanged.connect(lambda it, t=tabela: self._apenas_um_checked(it, t))
            lista.currentItemChanged.connect(lambda cur, prev, t=tabela: self._atualizar_descricao(t, cur))
            group_layout.addWidget(lista)
            label = QLabel("")
            label.setWordWrap(True)
            group_layout.addWidget(label)
            layout.addWidget(group)
            self.listas[tabela] = lista
            self.labels_desc[tabela] = label

        # Botões na parte inferior
        btn_layout = QHBoxLayout()
        self.btn_importar = QPushButton("Importar Selecionados")
        self.btn_cancelar = QPushButton("Cancelar")
        btn_layout.addWidget(self.btn_importar)
        btn_layout.addWidget(self.btn_cancelar)
        layout.addLayout(btn_layout)

        self.btn_importar.clicked.connect(self.importar)
        self.btn_cancelar.clicked.connect(self.reject)

    def _apenas_um_checked(self, item, tabela):
        if item.checkState() == Qt.Checked:
            lista = self.listas.get(tabela)
            if not lista:
                return
            for i in range(lista.count()):
                it = lista.item(i)
                if it is not item:
                    it.setCheckState(Qt.Unchecked)

    def _atualizar_descricao(self, tabela, item):
        label = self.labels_desc.get(tabela)
        if label is None:
            return
        if not item:
            label.setText("")
            return
        nome = item.data(Qt.UserRole)
        desc = self.descricoes.get(tabela, {}).get(nome, "")
        label.setText(desc)

    def importar(self):
        # Para cada tabela, percorre a lista e coleta os itens marcados
        selecionados = {}
        for tabela, lista in self.listas.items():
            nomes_selecionados = []
            for i in range(lista.count()):
                item = lista.item(i)
                if item.checkState() == Qt.Checked:
                    nomes_selecionados.append(item.data(Qt.UserRole))
            selecionados[tabela] = nomes_selecionados

        if not any(selecionados.values()):
            QMessageBox.warning(self, "Atenção", "Nenhum modelo foi selecionado para importação.")
            return

        # Aqui você pode definir como importar: por exemplo, para cada tabela importar o primeiro modelo selecionado
        # ou combinar dados de vários modelos.
        # Neste exemplo, vamos importar o primeiro modelo selecionado para cada tabela.
        for tabela, modelos in selecionados.items():
            if modelos:
                modelo = modelos[0]
                self.importar_por_nome(tabela, modelo)

        QMessageBox.information(self, "Sucesso", "Dados importados com sucesso.")
        self.accept()

    def importar_por_nome(self, tabela, nome):
        """
        Função auxiliar para importar os dados de uma tabela específica a partir do nome do modelo.
        Aqui você poderá chamar uma função de importação (por exemplo, uma nova função que não
        solicite interatividade) para atualizar o QTableWidget correspondente.
        """
        # Defina os mapeamentos para cada tabela (os mesmos usados nas funções de importação já existentes)
        mapeamentos = {
            "materiais": {
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
            },
            "ferragens": {
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
            },
            "sistemas_correr": {
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
            },
            "acabamentos": {
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
        }
        mapeamento = mapeamentos.get(tabela)
        if mapeamento is None:
            return
        # Aqui você pode chamar uma função (por exemplo, importar_dados_gerais_por_modelo) que você criará
        # no módulo dados_gerais_manager.py para importar o modelo já definido sem interatividade.
        # Como exemplo:
        try:
            
            from dados_gerais_manager import importar_dados_gerais_com_opcao
            # Aqui passamos o modelo escolhido para que a função não solicite novamente o nome
            importar_dados_gerais_com_opcao(self.main_window, tabela, mapeamento, nome)
           
        except ImportError:
            # Se não existir, você pode implementar a lógica similar à função importar_dados_gerais_com_opcao,
            # mas sem a necessidade de solicitar o modelo via QInputDialog.
            QMessageBox.warning(self, "Erro", f"Função de importação para {tabela} não implementada.")