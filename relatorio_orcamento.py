# relatorio_orcamento.py

# =============================================================================
# Geração de relatórios de orçamento (PDF e Excel)
# - Preenche os dados do orçamento na interface (cliente, totais, tabela de itens).
# - Gera ficheiros PDF (com ReportLab) e Excel (com xlsxwriter) prontos a enviar ao cliente.
# - Integra-se com as funções de dashboard/resumos de custos.
# - Permite gerir pasta de cada orçamento e garantir organização dos ficheiros.

# Este módulo recolhe os dados preenchidos na interface gráfica, calcula os
# totais do orçamento e exporta duas versões do relatório:
# - PDF criado com ReportLab, incluindo uma tabela de itens e um rodapé com
#   data, número orçamento e versão e paginação 1/2 ; 2/2.
# - Ficheiro Excel produzido com xlsxwriter contendo os mesmos dados.
#
# A função :func:`gerar_relatorio_orcamento` coordena o processo de preenchimento
# e geração dos ficheiros.


# Preenchimento automático dos dados do orçamento (cliente, totais, artigos) a partir da interface gráfica.

# Geração de relatórios em PDF (com ReportLab) e Excel (com xlsxwriter), prontos para partilhar com o cliente.

# Exportação de ficheiro Excel em formato especial para importação no PHC.

# Gestão automática das pastas de cada orçamento/versão (incluindo criação se necessário).

# Envio de orçamento por email (com corpo HTML editável e vários anexos).

# Funcionalidade de envio rápido pelo WhatsApp Web (abre o browser com número e mensagem, pronto a anexar).

# Integração com dashboard de resumos de consumos para controlo de custos e análises.

# Totalmente integrado com a interface PyQt (QtDesigner), facilitando uso mesmo para quem não é programador.



# =============================================================================

import os
import shutil
import webbrowser
import urllib.parse
import subprocess
import sys
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QHeaderView, QMessageBox, QVBoxLayout, QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QListWidget, QDialogButtonBox, QFileDialog, QLabel, QWidget, QHBoxLayout
from PyQt5.QtWidgets import QApplication
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import ( SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
import xlsxwriter
from db_connection import obter_cursor
from utils import obter_diretorio_base # importa se estiver noutro ficheiro

from orcamentos import _gerar_nome_pasta_orcamento # importa se estiver noutro ficheiro
from resumo_consumos import gerar_resumos_excel # o que faz este gerador de resumos?    
from orcamento_items import carregar_itens_orcamento, atualizar_custos_e_precos_itens 


def abrir_pasta_com_ficheiro(path: str) -> None:
    """Abre o explorador de ficheiros na pasta do ficheiro indicado."""
    # Faz com que, ao enviar por WhatsApp, a pasta do PDF fique logo aberta,
    # tornando fácil o 'drag & drop' para o browser ou o upload manual.
    if not path or not os.path.exists(path):
        return
    pasta = os.path.dirname(os.path.abspath(path))
    try:
        if sys.platform.startswith("win"):
            subprocess.Popen(["explorer", os.path.normpath(pasta)])
        elif sys.platform.startswith("darwin"):
            subprocess.Popen(["open", pasta])
        else:
            subprocess.Popen(["xdg-open", pasta])
    except Exception as e:
        print(f"Erro ao abrir pasta: {e}")


# =============================================================================
# Diálogo para edição do corpo do email e anexos Menu onde utilizador pode editar o corpo do email e adicionar/remover anexos.
# =============================================================================
class EmailDialog(QDialog):
    """
    Diálogo PyQt para editar o corpo do email (com HTML), gerir anexos (adicionar/remover)
    e aceder à função de envio rápido por WhatsApp Web (abre o browser com o número do cliente).
    """
    def __init__(self, html_default, anexos_iniciais=None, pasta_default=None, telemovel=None, pdf_path=None, parent=None):
        # Construtor do diálogo. Recebe:
        # - html_default: corpo do email já formatado (HTML)
        # - anexos_iniciais: lista de anexos já incluídos (ex: PDF gerado)
        # - pasta_default: diretório onde vai buscar anexos (normalmente a pasta do orçamento)
        # - telemovel: número de telefone do cliente (usado no WhatsApp)
        # - pdf_path: caminho do PDF gerado para facilitar anexar no WhatsApp
        # - parent: widget pai (normalmente None)

        # Layout superior (vertical) do diálogo
        # 1. Campo de edição do corpo do email (com HTML, área grande)
        # 2. Lista de anexos (área mais pequena, raramente muitos anexos)
        # 3. Botões para adicionar/remover anexos
        # 4. Botão "Enviar por WhatsApp" (abre browser)
        # 5. Botões OK / Cancel (aceitar ou cancelar envio)
        super().__init__(parent)
        self.setWindowTitle("Editar corpo do email e anexos")
        self.setMinimumSize(850, 600)
        self.pasta_default = pasta_default or os.getcwd()
        self.telemovel = telemovel or ""
        self.pdf_path = pdf_path

        layout = QVBoxLayout(self)

        # Corpo do email (HTML)
        corpo_lbl = QLabel("<b>Corpo do Email:</b>")
        layout.addWidget(corpo_lbl)
        self.text_edit = QTextEdit(self)
        self.text_edit.setHtml(html_default)
        self.text_edit.setMinimumHeight(350)  # Maior altura
        layout.addWidget(self.text_edit, stretch=3)  # Mais espaço para o texto

        # Lista de anexos (pequena)
        anexos_lbl = QLabel("<b>Anexos:</b>")
        layout.addWidget(anexos_lbl)
        self.anexos_list = QListWidget(self)
        self.anexos_list.setMaximumHeight(100)  # Pequena altura para anexos
        if anexos_iniciais:
            for anexo in anexos_iniciais:
                self.anexos_list.addItem(anexo)
        layout.addWidget(self.anexos_list, stretch=1)

        # Botões anexos
        botoes_h = QHBoxLayout()
        self.btn_add_anexo = QPushButton("Adicionar anexo(s)")
        self.btn_remover = QPushButton("Remover selecionado")
        botoes_h.addWidget(self.btn_add_anexo)
        botoes_h.addWidget(self.btn_remover)
        layout.addLayout(botoes_h)

        # Botão para enviar o PDF via WhatsApp
        self.btn_whatsapp = QPushButton("Enviar por WhatsApp")
        layout.addWidget(self.btn_whatsapp)

        self.btn_whatsapp.clicked.connect(self.enviar_whatsapp)

        self.btn_add_anexo.clicked.connect(self.adicionar_anexos)
        self.btn_remover.clicked.connect(self.remover_anexo)

        # OK / Cancel
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def adicionar_anexos(self):
        # Permite escolher ficheiros para anexar ao email.
        # Abre já na pasta do orçamento, facilita adicionar ficheiros adicionais.
        ficheiros, _ = QFileDialog.getOpenFileNames(
            self, 
            "Escolher ficheiros para anexar", 
            directory=self.pasta_default
        )
        for f in ficheiros:
            if f and not self.anexo_ja_adicionado(f):
                self.anexos_list.addItem(f)

    def remover_anexo(self):
        # Remove anexos selecionados da lista de anexos.
        for item in self.anexos_list.selectedItems():
            self.anexos_list.takeItem(self.anexos_list.row(item))

    def anexo_ja_adicionado(self, path):
        # Verifica se um ficheiro já está na lista de anexos para evitar duplicados.
        for i in range(self.anexos_list.count()):
            if self.anexos_list.item(i).text() == path:
                return True
        return False

    def get_corpo_e_anexos(self):
        # Devolve o corpo do email (HTML) e a lista de caminhos dos anexos selecionados.
        corpo_html = self.text_edit.toHtml()
        anexos = [self.anexos_list.item(i).text() for i in range(self.anexos_list.count())]
        return corpo_html, anexos
    
    def enviar_whatsapp(self):
        # Abre o browser na conversa WhatsApp Web do cliente, com mensagem pré-preenchida.
        # Depois abre a pasta do PDF, para anexar facilmente o orçamento.
        # Mostra mensagem a avisar que a janela foi aberta.
        numero = ''.join(filter(str.isdigit, str(self.telemovel)))
        if not numero:
            QMessageBox.warning(self, "Sem número", "Cliente sem número de telemóvel.")
            return
        mensagem = "Olá! Segue em anexo o orçamento em PDF."
        url = f"https://wa.me/{numero}?text={urllib.parse.quote(mensagem)}"
        webbrowser.open(url)
        if self.pdf_path and os.path.exists(self.pdf_path):
            abrir_pasta_com_ficheiro(self.pdf_path)
        QMessageBox.information(self, "WhatsApp Web", "Janela do WhatsApp aberta! Anexe o PDF manualmente.")


# =============================================================================
# Função: permite pedir ao utilizador o corpo do email modificar o modelo 
# =============================================================================
def pedir_corpo_email(parent, html_default):
    """
    Abre um diálogo PyQt simples apenas para editar o corpo do email (HTML).
    Pode ser usada se não quiseres gerir anexos (versão mais minimalista).
    """
    dlg = QDialog(parent)
    dlg.setWindowTitle("Editar corpo do email")
    layout = QVBoxLayout(dlg)
    text_edit = QTextEdit(dlg)
    text_edit.setHtml(html_default)  # Usa HTML!
    text_edit.setMinimumSize(850, 500)  # Torna a janela maior e confortável
    layout.addWidget(text_edit)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dlg)
    layout.addWidget(buttons)
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    dlg.setLayout(layout)
    if dlg.exec_() == QDialog.Accepted:
        return text_edit.toHtml()   # Mantém HTML!
    return None

# =============================================================================
# Função: gerar_corpo_email_html
# =============================================================================     

def gerar_corpo_email_html(valor_orcamento):
    """
    Lê um template HTML e, opcionalmente, uma assinatura personalizada.
    Substitui as variáveis {{valor}} e {{assinatura}} no template HTML pelo valor real e assinatura.
    Devolve o HTML pronto a usar como corpo do email.
    """
    with open("templates/email_template.html", "r", encoding="utf-8") as f:
        corpo_html = f.read()
    # Lê a assinatura HTML
    assinatura_html = ""
    assinatura_path = os.getenv("ASSINATURA_HTML")
    if assinatura_path and os.path.exists(assinatura_path):
        with open(assinatura_path, "r", encoding="utf-8") as f:
            assinatura_html = f.read()
    # Substitui as variáveis no HTML
    valor_formatado = f"{valor_orcamento:.2f}".replace('.', ',')
    corpo_html = corpo_html.replace("{{valor}}", valor_formatado)
    corpo_html = corpo_html.replace("{{assinatura}}", assinatura_html)
    return corpo_html

# =============================================================================
# Função: _parse_float
# =============================================================================
# Converte um texto (com símbolo € ou separadores de milhares) para float,
# garantindo compatibilidade entre formatos (pt/EN).
# =============================================================================
def _parse_float(value: str) -> float:
    """Converts a string to float, handling thousands separators and currency symbols."""
    if not value:
        return 0.0
    
    txt = str(value).strip()
    print(f"DEBUG _parse_float: valor original='{txt}'")
    
    # Remove símbolos de moeda e espaços
    txt = txt.replace('€', '').replace('$', '').replace('\xa0', '').replace(' ', '')
    print(f"DEBUG _parse_float: após remover símbolos='{txt}'")
    
    # Se contém vírgula, assumimos formato português/europeu (1.234,56)
    if ',' in txt:
        # Separa a parte decimal
        partes = txt.split(',')
        if len(partes) == 2:
            # Remove pontos da parte inteira (separadores de milhares)
            parte_inteira = partes[0].replace('.', '')
            parte_decimal = partes[1]
            txt = f"{parte_inteira}.{parte_decimal}"
            print(f"DEBUG _parse_float: formato europeu convertido='{txt}'")
    else:
        # Se não tem vírgula, pode ser formato americano ou número simples
        # Apenas remove pontos se houver mais de um (separadores de milhares)
        pontos = txt.count('.')
        if pontos > 1:
            # Remove todos os pontos exceto o último
            partes = txt.split('.')
            txt = ''.join(partes[:-1]) + '.' + partes[-1]
            print(f"DEBUG _parse_float: múltiplos pontos corrigidos='{txt}'")
    
    try:
        resultado = float(txt)
        print(f"DEBUG _parse_float: resultado final={resultado}")
        return resultado
    except ValueError as e:
        print(f"Erro ao converter '{value}' para float: {e}")
        return 0.0
        
        
# =============================================================================
# Função: _format_int
# =============================================================================
# Formata um texto numérico para inteiro, removendo casas decimais. Se o valor
# for vazio ou não numérico, retorna uma string vazia.
# =============================================================================
def _format_int(value: str) -> str:
    """Return integer string without decimals or empty string if not numeric."""
    if not value or not str(value).strip():
        return ""
    num = _parse_float(value)
    return f"{int(num)}"

# =============================================================================
# Função: _first_text
# =============================================================================
# Retorna o primeiro texto preenchido de uma lista de widgets.
# Usado para buscar dados de cliente da interface (procurando por vários campos).
# =============================================================================
def _first_text(*widgets) -> str:
    """Return the first non-empty text from given widgets."""
    for w in widgets:
        if w is not None:
            txt = w.text()
            if txt:
                return txt
    return ""

# =============================================================================
# Função: _enviar_email
# =============================================================================
# Envia um email com anexo utilizando as configurações do ficheiro ``.env``.
# =============================================================================
from utils_email import send_email
import sys
print("Python exe:", sys.executable)

def _enviar_email(destino: str, assunto: str, corpo: str, anexos=None) -> None:
    """
    Envia email com múltiplos anexos, usando configurações e autenticação definidas em utils_email.
    """
    if anexos is None:
        anexos = []
    send_email(destino, assunto, corpo, anexos)


# =============================================================================
# Função: _obter_dados_cliente
# =============================================================================
# Consulta a base de dados pelo ID do cliente e devolve os dados para o relatório.
# =============================================================================
def _obter_dados_cliente(cliente_id: str):
    """
    Consulta a base de dados e devolve os dados do cliente para preencher os relatórios e emails.
    """
    if not cliente_id:
        return None
    try:
        with obter_cursor() as cur:
            cur.execute(
                "SELECT nome, morada, email, numero_cliente_phc, telefone, telemovel FROM clientes WHERE id=%s",
                (cliente_id,),
            )
            return cur.fetchone()
    except Exception as e:
        print(f"Erro ao obter dados do cliente {cliente_id}: {e}")
        return None

# =============================================================================
# Classe FooterCanvas
# =============================================================================
# Canvas customizado para desenhar o rodapé do PDF (data, nº orçamento/versão, página).
# =============================================================================
class FooterCanvas(canvas.Canvas):
    """
    Classe que customiza o rodapé de cada página no PDF (data, nº orçamento, paginação).
    """
    def __init__(self, data_str: str, num_ver: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_str = data_str
        self.num_ver = num_ver
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_footer(page_count)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def _draw_footer(self, page_count: int):
        width, _ = A4
        self.setFont("Helvetica", 9)
        page_num = self.getPageNumber()
        # Data (esquerda)
        self.drawString(20, 20, self.data_str)
        # Nº orçamento e versão (centro)
        self.drawCentredString(width / 2, 20, self.num_ver)
        # Paginação (direita)
        self.drawRightString(width - 20, 20, f"{page_num}/{page_count}")

# =============================================================================
# Função: preencher_campos_relatorio
# =============================================================================
# Preenche na interface (UI) todos os campos do relatório, incluindo:
# - Dados de cliente (nome, morada, contacto, etc.)
# - Dados do orçamento (nº, versão, data)
# - Tabela de itens do orçamento
# - Cálculo de totais, subtotal, total geral, etc.
# =============================================================================
def preencher_campos_relatorio(ui: QtWidgets.QWidget) -> None:
    """Preenche a aba de relatório com os dados atuais do orçamento."""
    # 2. Preencher dados do orçamento
    cliente_id = _first_text(
        getattr(ui, "lineEdit_id_cliente", None),
        getattr(ui, "lineEdit_idCliente_noOrc", None),
    )
    dados_cli = _obter_dados_cliente(cliente_id)

    if dados_cli:
        nome, morada, email, num_phc, tel, telm = dados_cli
        ui.lineEdit_nome_cliente_3.setText(nome or "")
        ui.lineEdit_morada_cliente_3.setText(morada or "")
        ui.lineEdit_email_cliente_3.setText(email or "")
        ui.lineEdit_num_cliente_phc_3.setText(num_phc or "")
        ui.lineEdit_telefone_3.setText(tel or "")
        ui.lineEdit_telemovel_3.setText(telm or "")
    else:
        ui.lineEdit_nome_cliente_3.setText(
            _first_text(getattr(ui, "lineEdit_nome_cliente", None))
        )
        ui.lineEdit_morada_cliente_3.setText(
            _first_text(getattr(ui, "lineEdit_morada_cliente", None))
        )
        ui.lineEdit_email_cliente_3.setText(
            _first_text(getattr(ui, "lineEdit_email_cliente", None))
        )
        ui.lineEdit_num_cliente_phc_3.setText(
            _first_text(getattr(ui, "lineEdit_num_cliente_phc", None))
        )
        ui.lineEdit_telefone_3.setText(
            _first_text(getattr(ui, "lineEdit_telefone", None))
        )
        ui.lineEdit_telemovel_3.setText(
            _first_text(getattr(ui, "lineEdit_telemovel", None))
        )

     # Copiar a referência do cliente do separador 'Consulta Orcamentos'
    if hasattr(ui, "lineEdit_ref_cliente_2"):
        ui.lineEdit_ref_cliente_3.setText(ui.lineEdit_ref_cliente_2.text())


    # 2. Preencher dados do orçamento
    data_orc = ui.lineEdit_data.text()
    num_orc = ui.lineEdit_num_orcamento.text()
    ver_orc = ui.lineEdit_versao_orcamento.text()

    ui.label_data_orcamento_2.setText(data_orc)
    ui.label_data_2.setText(data_orc)
    ui.label_num_orcamento_2.setText(num_orc)
    ui.label_num_orcamento_3.setText(num_orc)
    ui.label_ver_orcamento_2.setText(ver_orc)
    ui.label_ver_orcamento_3.setText(ver_orc)

    # 3. Copiar tabela de artigos para tabela de relatório
    src = ui.tableWidget_artigos
    dst = ui.tableWidget_Items_Linha_Relatorio
    n = src.rowCount()
    dst.setRowCount(n)
    # Copia colunas 1-10 da tabela de artigos (ignora a coluna 0 "id_item")
    for i in range(n):
        for c in range(10):
            item = src.item(i, c + 1)
            txt = item.text() if item else ""
            dst.setItem(i, c, QtWidgets.QTableWidgetItem(txt))

    # 4. Ajustar colunas e linhas para visualização
    # Configurações de apresentação da tabela de itens
    # Ajusta larguras das colunas na tabelo do separadro Relatorio_orcamento
    # Nota: as larguras colunas são fixas, mas podem ser ajustadas conforme necessário
    larguras = [60, 100, 1600, 80, 80, 80, 60, 80, 150, 151]
    header = dst.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.Interactive)
    for idx, largura in enumerate(larguras):
        if idx < dst.columnCount():
            dst.setColumnWidth(idx, largura)
    dst.setWordWrap(True)
    dst.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    dst.resizeRowsToContents()

    # 5. Calcular totais (quantidade, subtotal, total geral)
    total_qt = 0.0
    subtotal = 0.0

    for i in range(n):
        qt_item = dst.item(i, 7)
        pt_item = dst.item(i, 9)  # Nota: mudei de coluna 10 para 9 - verificar se está correto
        
        qt_text = qt_item.text() if qt_item else ""
        pt_text = pt_item.text() if pt_item else ""
        
        
        qt = _parse_float(qt_text)
        pt = _parse_float(pt_text)
        
        
        total_qt += qt
        subtotal += pt
        


    ui.label_total_qt_2.setText(f"Total QT: {total_qt:g}")
    ui.label_subtotal_2.setText(f"Subtotal: {subtotal:,.2f}")
    ui.label_iva_2.setText("IVA: 23%")
    total_geral = subtotal * 1.23
    ui.label_total_geral_2.setText(f"Total Geral: {total_geral:,.2f}")
    ui.label_paginacao_2.setText("1/1")

# =============================================================================
# Função: gera_pdf
# =============================================================================
# Gera um ficheiro PDF com todos os dados do orçamento, incluindo:
# - Cabeçalho, dados do cliente, tabela de itens, totais e rodapé paginado.
# =============================================================================
def gera_pdf(ui: QtWidgets.QWidget, caminho: str) -> None:
    """
    Gera o PDF do relatório de orçamento com layout ajustado:
    - Nome cliente (esq.) e Nº Orçamento (dir.) na mesma linha
    - Data por baixo do Nº Orçamento, alinhada à direita
    - Morada, email, telefones, PHC logo abaixo do nome cliente (à esquerda)
    - Restante layout igual ao exemplo anterior
    Gera o PDF do orçamento. O layout é todo programático: cabeçalho, cliente, artigos, totais, rodapé.
    Usa estilos personalizados para formatação profissional.
    """
    from reportlab.platypus import Paragraph, Table, TableStyle, Spacer, SimpleDocTemplate, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    import os

    # 1. Definir estilos
    styles = getSampleStyleSheet()
    style_titulo = ParagraphStyle(
        "Titulo", fontSize=16, fontName="Helvetica-Bold", alignment=2,
        spaceAfter=0, textColor=colors.HexColor("#1A2A50")
    )
    style_numorc = ParagraphStyle(
        "NumOrc", fontSize=12, fontName="Helvetica-Bold", alignment=2,
        spaceAfter=0, textColor=colors.HexColor("#1A2A50")
    )
    style_data = ParagraphStyle(
        "Data", fontSize=9, fontName="Helvetica", alignment=2,
        spaceAfter=0, textColor=colors.grey
    )
    style_nome_cliente = ParagraphStyle(
        "NomeCliente", parent=styles["Normal"], fontSize=11, fontName="Helvetica-Bold",
        alignment=0, spaceAfter=1
    )
    style_small_italic = ParagraphStyle(
        "SmallItalic", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Oblique",
        textColor=colors.black, alignment=0, spaceAfter=1
    )
    style_ref = ParagraphStyle(
        "Ref", fontSize=10, fontName="Helvetica-Bold", textColor=colors.HexColor("#184ca7"),
        alignment=0, spaceAfter=0
    )
    style_obra = ParagraphStyle(
        "Obra", fontSize=10, fontName="Helvetica-Bold", textColor=colors.red,
        alignment=0, spaceAfter=0
    )

    # 2. Preparar dados da UI
    from utils import obter_diretorio_base
    caminho_base_dados = obter_diretorio_base(ui.lineEdit_base_dados.text())
    caminho_logotipo = os.path.join(caminho_base_dados, "LE_Logotipo.png")

    data_orc = ui.label_data_orcamento_2.text().strip()
    num_orc = ui.label_num_orcamento_2.text().strip()
    ver_orc = ui.label_ver_orcamento_2.text().strip()
    ref_cliente = ui.lineEdit_ref_cliente_3.text().strip()
    obra_val = getattr(ui, "lineEdit_obra_2", None)
    obra_val = obra_val.text().strip() if obra_val else ""
    nome_cliente = ui.lineEdit_nome_cliente_3.text().strip().upper()
    morada = ui.lineEdit_morada_cliente_3.text().strip()
    email = ui.lineEdit_email_cliente_3.text().strip()
    telefone = ui.lineEdit_telefone_3.text().strip()
    telemovel = ui.lineEdit_telemovel_3.text().strip()
    num_phc = ui.lineEdit_num_cliente_phc_3.text().strip()

    # Certifica-te que isto vem primeiro!
    logo_img = ""
    if os.path.exists(caminho_logotipo):
        try:
            logo_img = Image(caminho_logotipo, width=85, height=35)
        except Exception as e:
            print(f"Erro ao carregar logotipo: {e}")

    # 3. Preparar documento e elementos PDF
    doc = SimpleDocTemplate(
        caminho,
        pagesize=A4,
        leftMargin=10,
        rightMargin=10,
        topMargin=10,
        bottomMargin=50,
    )
    elems = []

    # 4. Linha topo: logotipo à esquerda, título à direita
    linha_topo = [
        [logo_img, Paragraph("Relatório de Orçamento", style_titulo)]
    ]
    table_topo = Table(linha_topo, colWidths=[120, 410])
    table_topo.setStyle(TableStyle([
        ("VALIGN", (0, 0), (0, 0), "TOP"),
        ("VALIGN", (1, 0), (1, 0), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (0, 0), 2),
        ("BOTTOMPADDING", (0, 0), (1, 0), 0),
    ]))
    elems.append(table_topo)
    elems.append(Spacer(0, 8))

    # --5.- Bloco: Nome Cliente / Nº Orçamento na mesma linha, Data mesmo por baixo à direita ---
    linha_cabecalho = [
        [
            Paragraph(nome_cliente, style_nome_cliente),
            Paragraph(f"Nº Orçamento: {num_orc}_{ver_orc}", style_numorc)
        ],
        [
            "",  # Nada debaixo do nome cliente
            Paragraph(f"Data: {data_orc}", style_data)
        ]
    ]
    table_cabecalho = Table(linha_cabecalho, colWidths=[340, 220])
    table_cabecalho.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, 0), "LEFT"),    # Nome cliente à esquerda
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),   # Nº orçamento à direita
        ("ALIGN", (1, 1), (1, 1), "RIGHT"),   # Data alinhada à direita, por baixo do orçamento
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (1, 1), (1, 1), 0),
        ("LEFTPADDING", (0, 0), (0, -1), 0),
        ("RIGHTPADDING", (1, 0), (1, -1), 0),
    ]))
    elems.append(table_cabecalho)
    elems.append(Spacer(0, 4))

    # 6. Dados do cliente (morada, email, telefones, PHC): todos à esquerda, logo abaixo
    if morada:
        elems.append(Paragraph(morada, style_small_italic))
    if email:
        elems.append(Paragraph(email, style_small_italic))
    linha_final = []
    if telefone:
        linha_final.append(f"Telefone: <i>{telefone}</i>")
    if telemovel:
        linha_final.append(f"Telemóvel: <i>{telemovel}</i>")
    if num_phc:
        linha_final.append(f"N.º cliente PHC: <i>{num_phc}</i>")
    if linha_final:
        texto_linha = "  |  ".join(linha_final)
        elems.append(Paragraph(texto_linha, style_small_italic))
    elems.append(Spacer(0, 6))

    # 7. Ref. e Obra (mantém)
    linha_ref_obra = [
        [
            Paragraph(f"Ref.: {ref_cliente}", style_ref) if ref_cliente else "",
            Paragraph(f"Obra: {obra_val}", style_obra) if obra_val else ""
        ]
    ]
    table_ref_obra = Table(linha_ref_obra, colWidths=[290, 280])
    table_ref_obra.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "LEFT"),
        ("VALIGN", (0, 0), (1, 0), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 0),
        ("LEFTPADDING", (1, 0), (1, 0), 40),
        ("TOPPADDING", (0, 0), (1, 0), 2),
        ("BOTTOMPADDING", (0, 0), (1, 0), 6),
    ]))
    elems.append(table_ref_obra)
    elems.append(Spacer(0, 2))

    # 8. Tabela de artigos
    headers = [
        "Item", "Codigo", "Descrição", "Alt", "Larg", "Prof", "Und", "Qt", "Preco Unit", "Preco Total"
    ]
    data = [headers]
    tw = ui.tableWidget_Items_Linha_Relatorio
    for r in range(tw.rowCount()):
        row = []
        for c in range(tw.columnCount()):
            itm = tw.item(r, c)
            txt = itm.text() if itm else ""
            if c == 2:
                lines = txt.splitlines()
                if lines:
                    first, *rest = lines
                    formatted = f"<b>{first}</b>"
                    if rest:
                        tab = "&nbsp;&nbsp;&nbsp;"
                        parts = []
                        for l in rest:
                            line = l.lstrip("\t")
                            highlight = False
                            if line.startswith("-"):
                                line = line[1:]
                            elif line.startswith("*"):
                                line = line[1:]
                                highlight = True
                            line = line.lstrip()
                            if highlight:
                                parts.append(f"{tab}<font backColor='#ccffcc'>{line}</font>")
                            else:
                                parts.append(tab + line)
                        italic_text = "<br/>".join(parts)
                        formatted += f"<br/><i><font size='8'>{italic_text}</font></i>"
                    row.append(Paragraph(formatted, styles["Normal"]))
                else:
                    row.append("")
            elif c == 9:
                row.append(Paragraph(f"<b>{txt}</b>", styles["Normal"]))
            else:
                if c in (3, 4, 5, 7):
                    row.append(_format_int(txt))
                else:
                    row.append(txt)
        data.append(row)

    col_widths = [25, 60, 260, 25, 25, 25, 25, 25, 50, 55]
    table = Table(data, repeatRows=1, colWidths=col_widths)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elems.append(table)
    elems.append(Spacer(1, 2))

    # 9. Quadro dos totais (igual)
    def add_euro(valor):
        valor = valor.strip()
        return valor if "€" in valor else valor + "€"

    subtotal_val = add_euro(ui.label_subtotal_2.text().split(":")[-1].strip())
    iva_val = ui.label_iva_2.text().split(":")[-1].strip()
    total_geral_val = add_euro(ui.label_total_geral_2.text().split(":")[-1].strip())
    total_qt_val = ui.label_total_qt_2.text().split(":")[-1].strip()

    bold_total_style = ParagraphStyle(
        "BoldTotal",
        parent=styles["Normal"],
        alignment=2,  # Direita
        fontSize=11,
        textColor=colors.darkblue,
        fontName="Helvetica-Bold"
    )
    totais_data = [
        ["", ""],
        ["Total QT:", total_qt_val],
        ["Subtotal:", subtotal_val],
        ["IVA (23%):", iva_val],
        [Paragraph("Total Geral:", bold_total_style), Paragraph(total_geral_val, bold_total_style)]
    ]
    totais_table = Table(totais_data, colWidths=[90, 80], hAlign="RIGHT")
    totais_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 11),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.darkblue),
        ("TOPPADDING", (0, -1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
        ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
        ("BOX", (0, -1), (-1, -1), 1.0, colors.HexColor("#002060")),
    ]))
    elems.append(totais_table)

    # 10. Gerar o PDF (mantém rodapé já implementado)
    doc.build(
        elems,
        canvasmaker=lambda *a, **kw: FooterCanvas(
            data_orc,
            f"{num_orc}_{ver_orc}",
            *a, **kw,
        ),
    )


# =============================================================================
# Função: gera_excel
# =============================================================================
# Gera um ficheiro Excel com a tabela de itens e totais do orçamento.
# =============================================================================
def gera_excel(ui: QtWidgets.QWidget, caminho: str) -> None:
    """
    Gera um ficheiro Excel formatado com logotipo, cabeçalho, morada, itens, totais (estilo PDF).
    Esta versão corrige os alinhamentos do cabeçalho e melhora o ajuste automático da altura das linhas.
    """

    # --- 1. Obter dados do cliente e do orçamento diretamente da interface ---
    nome_cliente = ui.lineEdit_nome_cliente_3.text().strip().upper()
    morada = ui.lineEdit_morada_cliente_3.text().strip()
    email = ui.lineEdit_email_cliente_3.text().strip()
    num_orc = ui.label_num_orcamento_2.text().strip()
    ver_orc = ui.label_ver_orcamento_2.text().strip()
    data_orc = ui.label_data_orcamento_2.text().strip()
    ref_cliente = ui.lineEdit_ref_cliente_3.text().strip()
    # Para obter a obra, verifica se o widget existe
    obra_val_widget = getattr(ui, "lineEdit_obra_2", None)
    obra_val = obra_val_widget.text().strip() if obra_val_widget else ""
    telefone = ui.lineEdit_telefone_3.text().strip()
    telemovel = ui.lineEdit_telemovel_3.text().strip()
    num_phc = ui.lineEdit_num_cliente_phc_3.text().strip()

    # --- 2. Linha de contactos, tudo na mesma linha ---
    linha_final = []
    if telefone: linha_final.append(f"Telefone: {telefone}")
    if telemovel: linha_final.append(f"Telemóvel: {telemovel}")
    if num_phc: linha_final.append(f"N.º cliente PHC: {num_phc}")
    txt_contactos = "  |  ".join(linha_final)

    # --- 3. Caminho para o logotipo ---
    caminho_base_dados = obter_diretorio_base(ui.lineEdit_base_dados.text())
    caminho_logotipo = os.path.join(caminho_base_dados, "LE_Logotipo.png")

    # --- 4. Criar workbook e worksheet ---
    wb = xlsxwriter.Workbook(caminho)
    ws = wb.add_worksheet("Relatório")

    # --- 5. Definir formatações personalizadas ---
    azul_escuro = '#184ca7'

    # Título principal (Relatório de Orçamento)
    cell_title = wb.add_format({'bold': True, 'font_size': 15, 'align': 'center', 'valign': 'vcenter'})
    # Nome cliente à esquerda
    cell_cab_left = wb.add_format({'bold': True, 'font_size': 12, 'align': 'left', 'valign': 'vcenter'})
    # Nº orçamento e Data (usado para ambos)
    cell_cab_info = wb.add_format({'bold': True, 'font_size': 12, 'align': 'left', 'valign': 'vcenter'})
    # Morada, email, contactos
    cell_morada = wb.add_format({'font_size': 10, 'align': 'left', 'valign': 'vcenter'})
    cell_mail = wb.add_format({'font_size': 10, 'align': 'left', 'valign': 'vcenter'})
    cell_contactos = wb.add_format({'font_size': 10, 'align': 'left', 'valign': 'vcenter'})
    # Cabeçalho da tabela
    cell_header = wb.add_format({'bold': True, 'bg_color': '#D9D9D9', 'align': 'center', 'border': 1, 'valign': 'vcenter'})
    # Células normais da tabela de itens
    cell_item = wb.add_format({'align': 'center', 'font_size': 10, 'border': 1, 'valign': 'vcenter'})
    # Totais (labels e valores)
    cell_total_label = wb.add_format({'align': 'right', 'bold': True, 'font_size': 10, 'valign': 'vcenter'})
    cell_total_val = wb.add_format({'align': 'center', 'bold': True, 'font_size': 11, 'color': '#002060', 'valign': 'vcenter'})
    # Ref. e Obra (com cores e tamanhos específicos)
    cell_ref = wb.add_format({'align': 'left', 'font_size': 16, 'bold': True, 'color': azul_escuro, 'valign': 'vcenter'})
    cell_obra = wb.add_format({'align': 'left', 'font_size': 16, 'bold': True, 'color': 'red', 'valign': 'vcenter'})
    # Descrição: título do artigo
    cell_descr_titulo = wb.add_format({'bold': True, 'font_size': 11, 'align': 'left'})
    # Descrição: sublinhas em itálico
    cell_descr_sub = wb.add_format({'italic': True, 'font_size': 10, 'align': 'left'})
    # Descrição: para a célula, wrap e borda
    cell_descr_container = wb.add_format({'border': 1, 'text_wrap': True, 'valign': 'top'})

    # --- 6. Margens e ajuste para imprimir tudo numa só página ---
    ws.set_margins(left=0.2, right=0.2, top=0.2, bottom=0.2)
    ws.fit_to_pages(1, 1)

    # --- 7. Largura das colunas ---
    ws.set_column('A:A', 7)
    ws.set_column('B:B', 18)
    ws.set_column('C:C', 44)
    ws.set_column('D:F', 8)
    ws.set_column('G:H', 8)
    ws.set_column('I:J', 16)

    row = 0

    # --- 8. Cabeçalho: logotipo, título e info do cliente/orçamento ---
    # Linha do logotipo
    if os.path.exists(caminho_logotipo):
        ws.set_row(row, 70)  # altura extra para logo
        ws.merge_range(row, 0, row, 1, '')
        ws.insert_image(row, 0, caminho_logotipo, {'x_scale': 0.15, 'y_scale': 0.15, 'x_offset': 15, 'y_offset': 10, 'positioning': 1})
    # Título principal à direita
    ws.merge_range(row, 3, row, 9, "Relatório de Orçamento", cell_title)
    row += 1

    # Linha do nome do cliente (A-C), nº orçamento (I-J)
    ws.merge_range(row, 0, row, 2, nome_cliente, cell_cab_left)
    ws.merge_range(row, 8, row, 9, f"Nº Orçamento: {num_orc}_{ver_orc}", cell_cab_info)
    row += 1

    # Linha da morada (A-C), data (I-J)
    ws.merge_range(row, 0, row, 2, morada, cell_morada)
    ws.merge_range(row, 8, row, 9, f"Data: {data_orc}", cell_cab_info)
    row += 1

    # Linha do email (A-C)
    ws.merge_range(row, 0, row, 2, email, cell_mail)
    row += 1

    # Linha dos contactos (A-C)
    ws.merge_range(row, 0, row, 2, txt_contactos, cell_contactos)
    row += 1

    # Linha da referência (A-C) e da obra (D-J)
    ws.merge_range(row, 0, row, 2, f"Ref.: {ref_cliente}", cell_ref)
    ws.merge_range(row, 3, row, 9, f"Obra: {obra_val}", cell_obra)
    row += 1

    row += 1  # Linha em branco

    # --- 9. Cabeçalho da tabela de itens ---
    headers = ["Item", "Codigo", "Descrição", "Alt", "Larg", "Prof", "Und", "Qt", "Preco Unit", "Preco Total"]
    for c, h in enumerate(headers):
        ws.write(row, c, h, cell_header)
    row += 1

    # --- 10. Tabela de artigos (itens) ---
    tw = ui.tableWidget_Items_Linha_Relatorio
    for r in range(tw.rowCount()):
        # Obter descrição (coluna 2) para contar o número de linhas de texto
        desc_item = tw.item(r, 2)
        desc_text = desc_item.text() if desc_item else ""
        num_linhas = len(desc_text.split('\n')) if desc_text else 1

        # Ajusta a altura da linha conforme quantidade de linhas na descrição
        ws.set_row(row, max(20, 15 * num_linhas))

        for c in range(tw.columnCount()):
            itm = tw.item(r, c)
            txt = itm.text() if itm else ""

            if c == 2:  # Coluna "Descrição"
                linhas = txt.split('\n')
                rich_parts = []
                if linhas:
                    # Cabeçalho em negrito (primeira linha)
                    rich_parts.append(cell_descr_titulo)
                    rich_parts.append(linhas[0].strip())
                # Cada sublinha (começando da segunda) vai para nova linha e em itálico
                for linha_subitem in linhas[1:]:
                    if linha_subitem.strip():
                        rich_parts.append('\n')  # quebra de linha
                        rich_parts.append(cell_descr_sub)
                        rich_parts.append(linha_subitem.strip())
                # Escreve a célula Descrição como rich text (negrito + italico), tudo dentro da célula, com wrap e borda
                ws.write_rich_string(row, c, *rich_parts, cell_descr_container)
            else:
                # Outras colunas: valor normal com formato centralizado e borda
                ws.write(row, c, txt, cell_item)
        row += 1

    # --- 11. Totais (QT, Subtotal, IVA, Total Geral) ---
    def euro(val):
        v = str(val).strip()
        return v if '€' in v else f"{v} €"

    subtotal_val = euro(ui.label_subtotal_2.text().split(":")[-1].strip())
    iva_val = ui.label_iva_2.text().split(":")[-1].strip()
    total_geral_val = euro(ui.label_total_geral_2.text().split(":")[-1].strip())
    total_qt_val = ui.label_total_qt_2.text().split(":")[-1].strip()

    ws.write(row, 8, "Total QT:", cell_total_label)
    ws.write(row, 9, total_qt_val, cell_total_val)
    row += 1
    ws.write(row, 8, "Subtotal:", cell_total_label)
    ws.write(row, 9, subtotal_val, cell_total_val)
    row += 1
    ws.write(row, 8, "IVA (23%):", cell_total_label)
    ws.write(row, 9, iva_val, cell_total_val)
    row += 1
    ws.write(row, 8, "Total Geral:", cell_total_label)
    ws.write(row, 9, total_geral_val, cell_total_val)

    # --- 12. Rodapé da folha física (data | orçamento | paginação) ---
    footer_text = f"{data_orc}       {num_orc}_{ver_orc}       Página &P de &N"
    ws.set_footer(footer_text, {'margin': 0.5, 'align_with_margins': True})

    # --- 13. Fechar o workbook (guardar ficheiro Excel) ---
    wb.close()



def gera_excel_importacao_phc(ui: QtWidgets.QWidget, caminho: str) -> None:
    """
    Gera um ficheiro Excel compatível com importação PHC.
    - Cabeçalho na linha 1: RefCliente | Referencia | Designacao | XAltura | YLargura | ZEspessura | Qtd | Venda
    - Linha 2 em branco.
    - Dados começam na linha 3.
    - Na coluna 'Designacao' nunca há mais de 57 caracteres por linha/célula.
    - Se necessário, continua o texto da descrição na linha seguinte, sem cortar palavras.
    - Coluna 'Venda' SEM símbolo €, apenas valor numérico.
    """

    import xlsxwriter

    # 1. Cria workbook e worksheet
    wb = xlsxwriter.Workbook(caminho)
    ws = wb.add_worksheet("Importacao")

    # 2. Ajusta as larguras das colunas para ficar igual ao modelo PHC
    ws.set_column('A:A', 12)  # RefCliente
    ws.set_column('B:B', 10)  # Referencia
    ws.set_column('C:C', 60)  # Designacao
    ws.set_column('D:D', 10)  # XAltura
    ws.set_column('E:E', 10)  # YLargura
    ws.set_column('F:F', 12)  # ZEspessura
    ws.set_column('G:G', 6)   # Qtd
    ws.set_column('H:H', 12)  # Venda

    # 3. Escreve o cabeçalho na linha 1 (índice 0)
    cabecalho = [
        "RefCliente", "Referencia", "Designacao",
        "XAltura", "YLargura", "ZEspessura", "Qtd", "Venda"
    ]
    ws.write_row(0, 0, cabecalho)

    # 4. Linha 2 fica em branco (index=1)
    # Não é preciso escrever nada, Excel já deixa em branco por padrão

    # 5. Começa a preencher dados na linha 3 (index=2)
    row = 2
    tw = ui.tableWidget_Items_Linha_Relatorio

    # 6. Função auxiliar para limpar/preparar o preço, SEM símbolo €,
    # aceita "," e "." como separador decimal, devolve float
    def limpar_preco(v):
        v = v.replace('€', '').replace(' ', '').replace(',', '.')
        try:
            return float(v)
        except Exception:
            return v

    # 7. Função para dividir o texto da descrição em linhas de no máximo 57 caracteres,
    # sem cortar palavras ao meio
    def dividir_em_linhas(texto, max_len=57):
        palavras = texto.split()
        linhas = []
        atual = ""
        for p in palavras:
            if len(atual) + len(p) + (1 if atual else 0) <= max_len:
                atual = atual + (" " if atual else "") + p
            else:
                linhas.append(atual)
                atual = p
        if atual:
            linhas.append(atual)
        return linhas

    # 8. Percorre todas as linhas da tabela de artigos do orçamento
    for r in range(tw.rowCount()):
        # Vai buscar cada campo da linha
        codigo = tw.item(r, 1).text() if tw.item(r, 1) else ""
        designacao_raw = tw.item(r, 2).text() if tw.item(r, 2) else ""
        xaltura = tw.item(r, 3).text() if tw.item(r, 3) else ""
        ylargo = tw.item(r, 4).text() if tw.item(r, 4) else ""
        zesp = tw.item(r, 5).text() if tw.item(r, 5) else ""
        qtd = tw.item(r, 7).text() if tw.item(r, 7) else ""
        venda = tw.item(r, 8).text() if tw.item(r, 8) else ""

        venda = limpar_preco(venda)  # <--- Limpa o símbolo €, devolve valor numérico

        # Separa a descrição completa em linhas (máx 57 caracteres, nunca corta palavras)
        partes = []
        for linha in designacao_raw.split('\n'):
            partes.extend(dividir_em_linhas(linha.strip()))

        # 9. Escreve cada linha da descrição:
        #    - Primeira linha do artigo: preenche todos os campos
        #    - Linhas seguintes: só coluna "Designacao", resto fica vazio
        for idx, linha_desc in enumerate(partes):
            if idx == 0:
                ws.write(row, 0, codigo)     # RefCliente
                ws.write(row, 1, 'MOB')     # Referencia (fixo)
                ws.write(row, 2, linha_desc) # Designacao (até 57 chars)
                ws.write(row, 3, xaltura)   # XAltura
                ws.write(row, 4, ylargo)    # YLargura
                ws.write(row, 5, zesp)      # ZEspessura
                ws.write(row, 6, qtd)       # Qtd
                ws.write(row, 7, venda)     # Venda (só número!)
            else:
                ws.write(row, 2, linha_desc) # Só coluna Designacao
            row += 1

    # 10. Guarda e fecha o ficheiro Excel
    wb.close()




# =============================================================================
# Função: _obter_caminho_pasta_orcamento
# =============================================================================
# Devolve o caminho onde guardar relatórios para este orçamento/versão.
# Garante que as pastas existem (versão '00' e a versão atual).
# =============================================================================
def _obter_caminho_pasta_orcamento(ui: QtWidgets.QWidget) -> str:
    """Retorna o caminho da pasta onde guardar os relatórios do orçamento.

    A estrutura passou a conter sempre subpastas de versão, começando por
    ``00``. Este helper cria a pasta da versão solicitada (e a ``00`` caso
    ainda não exista) antes de devolvê-la.
    """
    caminho_base = ui.lineEdit_orcamentos.text().strip()
    ano = ui.lineEdit_ano.text().strip()
    num = ui.lineEdit_num_orcamento_2.text().strip()
    nome_cliente = ui.lineEdit_nome_cliente_2.text().strip()
    versao = ui.lineEdit_versao.text().strip()
    nome_pasta = _gerar_nome_pasta_orcamento(num, nome_cliente)
    pasta_mae = os.path.join(caminho_base, ano, nome_pasta)
    pasta_versao = os.path.join(pasta_mae, versao)

    # Garante que a versão '00' existe, mesmo que estivermos noutra versão
    # Cria pastas se necessário
    if versao != "00":
        os.makedirs(os.path.join(pasta_mae, "00"), exist_ok=True)

    os.makedirs(pasta_versao, exist_ok=True)
    return pasta_versao


# =============================================================================
# Função: exportar_relatorio
# =============================================================================
# Gera os ficheiros PDF e Excel do orçamento na pasta correta.
# Mostra mensagem ao utilizador no final.
# =============================================================================
def exportar_relatorio(ui: QtWidgets.QWidget) -> None:
    """Gera os ficheiros PDF, Excel normal e Excel PHC na pasta do orçamento.
    Gera os três ficheiros do orçamento (PDF, Excel normal, Excel PHC) na pasta correta.
    Informa o utilizador do sucesso."""
    pasta = _obter_caminho_pasta_orcamento(ui)
    num = ui.label_num_orcamento_2.text()
    ver = ui.label_ver_orcamento_2.text()

    pdf_path = os.path.join(pasta, f"{num}_{ver}.pdf")
    xls_path = os.path.join(pasta, f"{num}_{ver}.xlsx")
    xls_phc_path = os.path.join(pasta, f"{num}_{ver}_PHC.xlsx")

    gera_pdf(ui, pdf_path)
    gera_excel(ui, xls_path)
    gera_excel_importacao_phc(ui, xls_phc_path)  # <--- NOVO: Gera Excel PHC

    print(f"Relatórios guardados em:\nPDF: {pdf_path}\nXLSX: {xls_path}\nXLSX PHC: {xls_phc_path}")
    QtWidgets.QMessageBox.information(
        getattr(ui, "tabWidget_orcamento", None),
        "Gerado",
        f"Arquivos gerados:\n• {pdf_path}\n• {xls_path}\n• {xls_phc_path}",
    )

# =============================================================================
# Função: gerar_relatorio_orcamento
# =============================================================================
# Processo completo: preenche os campos, pergunta ao utilizador e gera os ficheiros.
# =============================================================================
def gerar_relatorio_orcamento(ui: QtWidgets.QWidget) -> None:
    """Fluxo completo de geração do relatório."""
    preencher_campos_relatorio(ui)
    resp = QtWidgets.QMessageBox.question(
        getattr(ui, "tabWidget_orcamento", None),
        "Confirmar geração",
        "Campos preenchidos.\nDeseja gerar o Relatorio do Orçamento em PDF e em  Excel inclui tambem o Excel de Importação para PHC agora?",
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        QtWidgets.QMessageBox.Yes,
    )
    if resp == QtWidgets.QMessageBox.Yes:
        exportar_relatorio(ui)

# =============================================================================
# Função: enviar_orcamento_por_email    
# =============================================================================
# Gera o PDF (se necessário) e envia por email ao cliente.
def enviar_orcamento_por_email(ui: QtWidgets.QWidget) -> None:
    """
    Gera o PDF se não existir, pede ao utilizador para editar o corpo do email e anexar ficheiros,
    e envia o email ao cliente.
    Atualiza o estado do orçamento para "Enviado" na base de dados.
    """
    preencher_campos_relatorio(ui)

    pasta = _obter_caminho_pasta_orcamento(ui)
    num = ui.label_num_orcamento_2.text()
    ver = ui.label_ver_orcamento_2.text()
    pdf_path = os.path.join(pasta, f"{num}_{ver}.pdf")

    if not os.path.exists(pdf_path):
        try:
            gera_pdf(ui, pdf_path)
        except Exception as e:
            QMessageBox.critical(None, "Erro", f"Não foi possível gerar o PDF:\n{e}")
            return

    destino = ui.lineEdit_email_cliente_3.text().strip()
    if not destino:
        destino, ok = QtWidgets.QInputDialog.getText(
            getattr(ui, "tabWidget_orcamento", None),
            "Email do Cliente",
            "O cliente não tem email registado. Introduza um email para envio:",
        )
        if not ok or not destino.strip():
            QMessageBox.warning(None, "Email inválido", "Operação cancelada por falta de email.")
            return
        destino = destino.strip()

    num_orc = ui.lineEdit_num_orcamento_2.text().strip()
    versao = ui.lineEdit_versao.text().strip()
    ref_cliente = ui.lineEdit_ref_cliente_2.text().strip()
    obra = ui.lineEdit_obra_2.text().strip() if hasattr(ui, "lineEdit_obra_2") else ""

    assunto = f"Orcamento LE-> {num_orc}_{versao}"
    if ref_cliente:
        assunto += f" | Ref. cliente: {ref_cliente}"
    if obra:
        assunto += f" | Ref. Obra {obra}"

    subtotal_txt = ui.label_subtotal_2.text().split(":")[-1].strip()
    valor_orcamento = _parse_float(subtotal_txt)

     # -- GERA O CORPO HTML JÁ FORMATADO --
    corpo_default = gerar_corpo_email_html(valor_orcamento)

    # -- GERA O CORPO HTML JÁ FORMATADO   E ABRE PARA ADICIONAR ANEXOS NA PASTA DO ORÇAMENTO--
    telemovel = ui.lineEdit_telemovel_3.text().strip()
    dlg = EmailDialog(corpo_default, anexos_iniciais=[pdf_path], pasta_default=pasta, telemovel=telemovel, pdf_path=pdf_path)
    if dlg.exec_() == QDialog.Accepted:
        corpo_final, anexos = dlg.get_corpo_e_anexos()
    else:
        QMessageBox.information(None, "Cancelado", "Envio cancelado pelo utilizador.")
        return

    # -- ENVIA O EMAIL (mantém HTML) --
    try:
        _enviar_email(destino, assunto, corpo_final, anexos)
    except Exception as e:
        QMessageBox.critical(None, "Erro no envio", f"Não foi possível enviar o email:\n{e}")
        return

    try:
        id_orc = ui.lineEdit_id.text().strip()
        if id_orc:
            with obter_cursor() as cur:
                cur.execute("UPDATE orcamentos SET status=%s WHERE id=%s", ("Enviado", id_orc))
    except Exception as e:
        print(f"Erro ao atualizar status para 'Enviado': {e}")

    QMessageBox.information(None, "Sucesso", f"Email enviado para {destino}")


# =============================================================================
# Função: on_gerar_relatorio_consumos_clicked
# =============================================================================
# Handler para o botão 'Gerar Relatório de Consumos'.
# Gera o ficheiro Excel de resumo, mostra dashboard e seleciona o separador correto.
# =============================================================================

def on_gerar_relatorio_consumos_clicked(ui):
    """
    Handler para o botão 'Gerar Relatório de Consumos'.
    - Garante que existe um modelo Excel na pasta dos modelos.
    - Copia esse modelo para a pasta do orçamento com o nome correto.
    - Atualiza o ficheiro Excel com os resumos do orçamento selecionado.
    - Atualiza o dashboard na interface.
    """
    print("===> Handler para gerar relatório de consumos chamado!")

    # 1. Obter a pasta onde vão ser guardados os ficheiros do orçamento
    try:
        pasta_orcamento = _obter_caminho_pasta_orcamento(ui)
        if not pasta_orcamento or not os.path.exists(pasta_orcamento):
            QMessageBox.warning(None, "Caminho Inválido", f"A pasta do orçamento não foi encontrada ou não pôde ser criada:\n{pasta_orcamento}")
            return
    except Exception as e:
        QMessageBox.critical(None, "Erro Crítico", f"Falha ao obter o caminho da pasta do orçamento:\n{e}")
        return

    # 2. Obter dados essenciais da UI
    num_orcamento = ui.lineEdit_num_orcamento_2.text().strip()
    versao = ui.lineEdit_versao.text().strip()

    if not num_orcamento or not versao:
        QMessageBox.warning(None, "Dados Incompletos", "Por favor, preencha o número do orçamento e a versão antes de gerar o relatório.")
        return

    nome_ficheiro_excel = f"Resumo_Custos_{num_orcamento}_{versao}.xlsx"
    caminho_completo_excel = os.path.join(pasta_orcamento, nome_ficheiro_excel)

    # 3. Obter o caminho do modelo Excel a partir do campo de configuração
    pasta_modelos = obter_diretorio_base(ui.lineEdit_base_dados.text())
    nome_modelo = "MODELO_Resumo_Custos.xlsx"
    caminho_modelo = os.path.join(pasta_modelos, nome_modelo)

    if not os.path.exists(caminho_modelo):
        QMessageBox.critical(None, "Modelo não encontrado", f"O ficheiro modelo não existe:\n{caminho_modelo}")
        return

    # 4. Copiar o modelo apenas se o ficheiro novo não existir (evita sobrescrever alterações)
    if not os.path.exists(caminho_completo_excel):
        try:
            shutil.copyfile(caminho_modelo, caminho_completo_excel)
            print(f"[INFO] Modelo copiado para: {caminho_completo_excel}")
        except Exception as e:
            QMessageBox.critical(None, "Erro", f"Erro ao copiar modelo Excel:\n{e}")
            return

    # 5. Gerar resumos no ficheiro Excel (vai atualizar as folhas do modelo)
    try:
        from resumo_consumos import gerar_resumos_excel  # Importação localizada para evitar dependências circulares
        print(f"===> A gerar resumos para o ficheiro: {caminho_completo_excel}")
        gerar_resumos_excel(caminho_completo_excel, num_orcamento, versao)
        try:
            id_str = ui.lineEdit_id.text().strip()
            if id_str.isdigit():
                carregar_itens_orcamento(ui, int(id_str))
                atualizar_custos_e_precos_itens(ui, force_global_margin_update=False)
        except Exception as e_upd:
            print(f"[ERRO] Falha ao atualizar tabela de artigos: {e_upd}")
    except Exception as e:
        QMessageBox.critical(None, "Erro", f"Erro ao gerar o ficheiro Excel de resumos:\n{e}")
        import traceback
        traceback.print_exc()
        return

    # 6. Atualizar o dashboard na interface
    try:
        from dashboard_resumos_custos import mostrar_dashboard_resumos
        print(f"===> A gerar dashboard com dados de: {caminho_completo_excel}")

        if not os.path.exists(caminho_completo_excel):
            QMessageBox.warning(None, "Ficheiro não encontrado", f"O ficheiro de resumos não foi encontrado após a tentativa de criação:\n{caminho_completo_excel}")
            return

        mostrar_dashboard_resumos(ui.frame_resumos, caminho_completo_excel, ui)
        ui.tabWidget_orcamento.setCurrentWidget(ui.tab_relatorios)
        ui.Relatorio_Orcamento_2.setCurrentWidget(ui.Resumo_Consumos_Orcamento_2)

    except Exception as e:
        QMessageBox.critical(None, "Erro de Dashboard", f"Ocorreu um erro ao exibir o dashboard:\n{e}")
        import traceback
        traceback.print_exc()


# =============================================================================
# Main para testes: Executa o fluxo todo se correr diretamente este ficheiro
# =============================================================================
if __name__ == "__main__":
    from orcamentos_le_layout import Ui_MainWindow
    app = QtWidgets.QApplication([])
    main_win = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(main_win)
    
    # Adicionar layout ao frame_resumos para que os testes funcionem
    if ui.frame_resumos.layout() is None:
        layout_resumos = QVBoxLayout(ui.frame_resumos)
        ui.frame_resumos.setLayout(layout_resumos)
        
    ui.pushButton_Export_PDF_Relatorio.clicked.connect(lambda: gerar_relatorio_orcamento(ui)) 
    # A linha abaixo foi corrigida, estava a chamar a função diretamente em vez de um lambda
    ui.pushButton_Gerar_Relatorio_Consumos.clicked.connect(lambda: on_gerar_relatorio_consumos_clicked(ui)) 
    
    main_win.show()
    app.exec_()
