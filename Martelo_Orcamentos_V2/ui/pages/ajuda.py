from __future__ import annotations

from datetime import date
import html
import subprocess
from typing import Any, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.models.user import User
from Martelo_Orcamentos_V2.utils_email import send_email
from Martelo_Orcamentos_V2.utils_version import (
    UpdateInfo,
    check_for_updates,
    get_current_version,
    get_setup_share_path,
    launch_installer,
    stage_installer_to_temp,
)


def _help_html(*, current_user: Optional[Any] = None) -> str:
    username = getattr(current_user, "username", None) or ""
    user_line = f"<p><b>Utilizador:</b> {html.escape(username)}</p>" if username else ""

    # Nota: manter HTML simples para compatibilidade com QTextBrowser.
    return f"""
    <html>
    <head>
      <meta charset="utf-8" />
      <style>
        body {{ font-family: Segoe UI, Arial, sans-serif; font-size: 12px; color: #222; }}
        h1 {{ font-size: 20px; margin: 6px 0 10px 0; }}
        h2 {{ font-size: 15px; margin: 18px 0 6px 0; }}
        h3 {{ font-size: 13px; margin: 12px 0 6px 0; }}
        p {{ margin: 6px 0; }}
        li {{ margin: 4px 0; }}
        code {{ background: #f3f3f3; padding: 1px 4px; border-radius: 3px; }}
        .muted {{ color: #666; }}
        .box {{
          border: 1px solid #e5e5e5;
          background: #fbfbfb;
          padding: 10px 12px;
          border-radius: 6px;
          margin: 10px 0;
        }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #e5e5e5; padding: 6px 8px; vertical-align: top; }}
        th {{ background: #f6f6f6; text-align: left; }}
      </style>
    </head>
    <body>
      <h1>Ajuda - Martelo Orçamentos V2</h1>
      <p class="muted">Guia prático de utilização (atualizado em {date.today().isoformat()}).</p>
      {user_line}

      <div class="box">
        <b>Como usar esta página</b>
        <ul>
          <li>Use a caixa de pesquisa acima (ou <code>Ctrl+F</code>) para encontrar termos.</li>
          <li>Clique nos links do índice para saltar para a secção desejada.</li>
        </ul>
      </div>
      <div class="box">
        <b>Atalhos de teclado</b>
        <ul>
          <li><code>Ctrl+G</code>: gravar/guardar no menu atual (quando existe botão de guardar).</li>
          <li><code>Ctrl+C</code> / <code>Ctrl+V</code>: copiar/colar linhas em <b>Dados Gerais</b>, <b>Dados Items</b> e <b>Custeio dos Items</b>.</li>
        </ul>
      </div>

      <div class="box">
        <b>Novidades desta versão</b>
        <ul>
          <li><b>Orçamentos</b>: resumo diário personalizado e janela de tarefas por orçamento.</li>
          <li><b>Custeio dos Items</b>: componentes filhos aceitam override local em <code>QT_und</code>, sem alterar a regra base.</li>
          <li><b>Produção</b>: criação automática da lista de peças no CUT-RITE a partir do Excel <code>Lista_Material_*.xlsm</code>.</li>
          <li><b>Produção</b>: novo botão <code>Imprimir PDFs</code> para emitir os documentos do processo.</li>
        </ul>
      </div>

      <h2>Índice</h2>
      <ul>
        <li><a href="#workflow">Fluxo de trabalho (resumo)</a></li>
        <li><a href="#novidades">Novidades desta versão</a></li>
        <li><a href="#orcamentos">Orçamentos</a></li>
        <li><a href="#items">Items</a></li>
        <li><a href="#dados">Dados Gerais e Dados Items</a></li>
        <li><a href="#custeio">Custeio dos Items</a></li>
        <li><a href="#materias">Matérias Primas + Pesquisa IA</a></li>
        <li><a href="#relatorios">Relatórios</a></li>
        <li><a href="#consumos">Resumo de Consumos</a></li>
        <li><a href="#config">Configurações</a></li>
        <li><a href="#producao">Produção</a></li>
        <li><a href="#dicas">Dicas rápidas / Perguntas frequentes</a></li>
      </ul>

      <a name="workflow"></a>
      <h2>Fluxo de trabalho (resumo)</h2>
      <div class="box">
        <ol>
          <li><b>Orçamentos</b>: criar/selecionar um orçamento e preencher cliente/obra/estado.</li>
          <li><b>Items</b>: inserir itens (cada orçamento tem vários itens).</li>
          <li><b>Dados Gerais</b>: configurar tabelas base (Materiais, Ferragens, Sistemas Correr, Acabamentos).</li>
          <li><b>Dados Items</b>: ajustar dados específicos do item (pode mapear a partir dos Dados Gerais).</li>
          <li><b>Custeio dos Items</b>: inserir peças, matérias-primas, acabamentos e validar custos.</li>
          <li><b>Atualizar Custos</b>: confirmar o preço final do item/orçamento e margens.</li>
          <li><b>Relatórios</b>: pré-visualizar e exportar (PDF/Excel) ou enviar por email.</li>
          <li><b>Resumo de Consumos</b>: dashboard, plano de corte e exportações.</li>
          <li><b>Produção</b>: converter orçamento para processo ou criar processo novo.</li>
        </ol>
      </div>

      <h3>Mapa rápido (métricas / onde fazer)</h3>
      <table>
        <tr>
          <th>Área</th>
          <th>Objetivo</th>
          <th>O que confirmar</th>
        </tr>
        <tr>
          <td><b>Orçamentos</b></td>
          <td>Criar e gerir versões/estado do orçamento</td>
          <td>Cliente, obra, versão, utilizador, datas e descrição</td>
        </tr>
        <tr>
          <td><b>Items</b></td>
          <td>Detalhar o orçamento por itens</td>
          <td>Dimensões, descrição, tipo de produção (STD/SÉRIE), margens e preços</td>
        </tr>
        <tr>
          <td><b>Custeio</b></td>
          <td>Construir a lista de peças e calcular custos</td>
          <td>Matérias-primas, acabamentos, orlas, mão de obra, linhas bloqueadas (BLK)</td>
        </tr>
        <tr>
          <td><b>Relatórios</b></td>
          <td>Gerar PDF/Excel e enviar ao cliente</td>
          <td>Pré-visualização correta, anexos e texto do email</td>
        </tr>
      </table>

      <a name="novidades"></a>
      <h2>Novidades desta versão</h2>
      <table>
        <tr>
          <th>Área</th>
          <th>Novidade</th>
          <th>Como usar</th>
        </tr>
        <tr>
          <td><b>Orçamentos</b></td>
          <td>Resumo Diário com lembretes e tarefas por orçamento.</td>
          <td>Abra <code>Resumo Diário</code> para rever pendentes por utilizador e use <code>Tarefas</code> quando precisar de follow-up formal.</td>
        </tr>
        <tr>
          <td><b>Custeio dos Items</b></td>
          <td>Override local para componentes filhos em <code>QT_und</code>.</td>
          <td>Edite apenas a linha do filho. A regra base mantém-se; o destaque visual mostra linhas alteradas manualmente.</td>
        </tr>
        <tr>
          <td><b>Produção</b></td>
          <td>Integração CUT-RITE a partir do Excel de lista de material.</td>
          <td>Use <code>Enviar CUT-RITE</code> no processo; o Martelo abre o CUT-RITE, cria a lista de peças e grava o plano.</td>
        </tr>
        <tr>
          <td><b>Produção</b></td>
          <td>Emissão rápida de documentação do processo.</td>
          <td>Use <code>Imprimir PDFs</code> para imprimir os PDFs ligados ao processo selecionado.</td>
        </tr>
      </table>

      <a name="orcamentos"></a>
      <h2>Orçamentos</h2>
      <ul>
        <li><b>Criar novo orçamento</b>: use o botão <code>Novo Orçamento</code>, selecione cliente e preencha dados principais.</li>
        <li><b>Clientes temporarios</b>: no menu <b>Clientes</b> existem 2 separadores (PHC e Clientes Temporarios). Registe o cliente temporario; ele fica associado ao cliente <code>CONSUMIDOR FINAL</code>.</li>
        <li><b>Selecionar cliente temporario</b>: no campo Cliente escolha <code>CONSUMIDOR FINAL</code>; abre uma lista de clientes temporarios para selecionar e fica o <b>nome simplex</b> gravado no orcamento.</li>
        <li><b>Guardar</b>: use <code>Salvar</code> para gravar alterações (atalho <code>Ctrl+G</code>).</li>
        <li><b>Nova versão</b>: use <code>Duplicar / Versão</code> (recomendado quando muda o desenho/condições comerciais).</li>
        <li><b>Abrir items</b>: use <code>Abrir Items</code> para entrar no detalhe do orçamento.</li>
        <li><b>Pasta do orçamento</b>: pode criar/abrir a pasta no servidor ligada ao orçamento.</li>
        <li><b>Pasta com temporarios</b>: ao criar a pasta no servidor, o nome segue <code>numero_orcamento + nome_simplex</code> do cliente temporario.</li>
        <li><b>Lista de orcamentos</b>: a coluna <b>Cliente</b> mostra o <b>nome simplex</b> para clientes temporarios.</li>
        <li><b>Info do cliente</b>: duplo clique numa linha do orcamento abre um menu que indica se o cliente e de PHC ou Temporario.</li>
        <li><b>Resumo Diário</b>: abre os lembretes do utilizador e também pode ser reaberto manualmente pelo botão próprio.</li>
        <li><b>Tarefas</b>: permite criar apontamentos formais por orçamento; use apenas quando precisar de acompanhamento estruturado.</li>
      </ul>

      <a name="items"></a>
      <h2>Items</h2>
      <ul>
        <li>Cada item é uma unidade de trabalho com dimensões e custo próprio.</li>
        <li><b>Descrição</b>: clique com o botão direito para inserir descrições predefinidas.</li>
        <li><b>Atualizar custos</b>: após alterar peças/matérias-primas/margens, pressione <code>Atualizar Custos</code>.</li>
        <li><b>Margens</b>: pode editar margens para refletir o preço final; também pode definir um preço final e o sistema ajusta margens automaticamente.</li>
        <li><b>STD / SÉRIE</b>: selecione o tipo de produção do item.</li>
        <li><b>Duplicar / mover</b>: é possível duplicar linhas de items, expandir para ver conteúdo e mover para cima/baixo.</li>
      </ul>

      <a name="dados"></a>
      <h2>Dados Gerais e Dados Items</h2>
      <p>Estas áreas configuram as tabelas que alimentam o custeio:</p>
      <ul>
        <li><b>Dados Gerais</b>: base do orçamento (Materiais, Ferragens, Sistemas Correr, Acabamentos, etc.).</li>
        <li><b>Dados Items</b>: especificações do item (pode ser mapeado dos Dados Gerais).</li>
        <li><b>Modelos</b>: pode <code>Gravar Modelo</code> e <code>Importar</code> modelos guardados.</li>
        <li><b>Utilizador vs Global</b>: modelos <b>Global</b> ficam disponíveis para todos os utilizadores.</li>
        <li><b>Atalhos</b>: <code>Ctrl+G</code> para guardar; <code>Ctrl+C</code>/<code>Ctrl+V</code> para copiar/colar linhas.</li>
      </ul>

      <a name="custeio"></a>
      <h2>Custeio dos Items</h2>
      <ul>
        <li><b>Inserção por tipos</b>: existe um menu para selecionar um ou vários tipos e inserir na tabela.</li>
        <li><b>Colunas</b>: pode mostrar/ocultar colunas conforme a necessidade.</li>
        <li><b>Navegação</b>: setas <code>up/down</code> para navegar entre items.</li>
        <li><b>Preencher Dados Items</b>: mapeia automaticamente Dados Gerais para as tabelas do item.</li>
        <li><b>Peças pai/filho</b>: peças compostas já incluem componentes associados (ex.: porta + dobradiça + puxador).</li>
        <li><b>Override local em filhos</b>: quando um componente filho precisa de ajuste pontual, edite a coluna <code>QT_und</code> apenas nessa linha.</li>
        <li><b>Regra base preservada</b>: a edição local não altera a fórmula global da peça; afeta apenas o item/linha atual do orçamento.</li>
        <li><b>Destaque visual</b>: quando existe override manual, <code>QT_mod</code> e <code>QT_und</code> ficam em itálico e sublinhado para identificar a exceção local.</li>
        <li><b>Reposição automática</b>: ao limpar o valor manual em <code>QT_und</code>, a linha volta a usar a fórmula padrão.</li>
        <li><b>Variáveis</b>: o custeio usa variáveis como <code>H/L/P/HM/LM/PM</code> em cálculos.</li>
        <li><b>Botão direito</b>: opções para copiar/colar linhas, inserir, selecionar matéria-prima e inserir divisões independentes.</li>
        <li><b>Divisão independente</b>: serve para separar artigos (organização e controlo de consumos).</li>
        <li><b>Módulos</b>: pode gravar módulos com descrição e imagem; importar; e gerir (editar/apagar/copiar Utilizador↔Global).</li>
        <li><b>Flags</b>: colunas para não considerar <code>MP</code>, <code>MO</code>, <code>Orla</code> e linhas bloqueadas <code>BLK</code>.</li>
        <li><b>Acabamentos</b>: colunas para face superior/inferior (listas suspensas).</li>
        <li><b>Atalhos</b>: <code>Ctrl+G</code> para guardar; <code>Ctrl+C</code>/<code>Ctrl+V</code> para copiar/colar linhas.</li>
      </ul>

      <a name="materias"></a>
      <h2>Matérias Primas + Pesquisa IA</h2>
      <ul>
        <li><b>Pesquisar</b>: use <code>%</code> para separar multi-termos (ex.: <code>placa%branco</code>).</li>
        <li><b>Abrir Excel</b> / <b>Atualizar Importação</b>: consultar e atualizar a base de matérias-primas.</li>
        <li><b>Colunas</b> / <b>Gravar Layout</b>: personalizar as colunas visíveis e guardar o layout.</li>
        <li><b>Pesquisa IA</b>: pesquisa semântica em documentos curados (requer ingestão).</li>
        <li><b>Atualizar IA</b>: executa a ingestão e atualiza o índice (pode demorar alguns minutos).</li>
      </ul>
      <div class="box">
        <b>Nota</b>: se a pesquisa IA não devolver resultados, confirme se o índice foi gerado e se as pastas de IA estão configuradas em <b>Configurações</b>.
      </div>

      <a name="relatorios"></a>
      <h2>Relatórios</h2>
      <ul>
        <li>Em <b>Relatórios → Relatório de Orçamento</b> existe uma pré-visualização do orçamento.</li>
        <li><b>Exportar</b>: PDF / Excel.</li>
        <li><b>Email</b>: enviar orçamento por email com texto predefinido (editável) e anexos.</li>
        <li>Por defeito, o orçamento gerado é anexado ao email (pode adicionar anexos extra).</li>
      </ul>

      <a name="consumos"></a>
      <h2>Resumo de Consumos</h2>
      <ul>
        <li><b>Dashboard</b>: exportar para PDF.</li>
        <li><b>Plano de corte</b>: exportar em PDF.</li>
        <li>Selecione quais matérias-primas devem ser consideradas como placas inteiras.</li>
        <li>Pode reverter o processo inicial caso precise refazer o cálculo.</li>
      </ul>

      <a name="config"></a>
      <h2>Configurações</h2>
      <ul>
        <li><b>Pastas base</b>: defina os caminhos de trabalho (orçamentos, matérias-primas, base de dados e produção).</li>
        <li><b>IA</b>: configure <code>Pasta Pesquisa Profunda IA</code>, <code>Pasta Embeddings IA</code> e <code>Pasta Modelo IA (texto)</code>.</li>
        <li><b>Provedor resposta IA</b>: <code>local</code> usa modelo offline; <code>openai</code> usa API (requer chave).</li>
        <li><b>CUT-RITE</b>: configure <code>Executavel CUT-RITE</code>, <code>Pasta Trabalho CUT-RITE</code> e <code>Pasta Dados CUT-RITE</code> antes de usar a automação.</li>
      </ul>
      <div class="box">
        <b>Recomendação</b>: em ambientes com vários PCs, use caminhos de servidor (UNC) para garantir que todos acedem ao mesmo índice/recursos.
      </div>

      <a name="producao"></a>
      <h2>Produção</h2>
      <div class="box">
        <b>Objetivo</b>: gerir processos de produção associados a encomendas (PHC) ou a um orçamento, com versões,
        pastas de trabalho e documentação (descrições/notas).
      </div>

      <h3>Lista, pesquisa e filtros</h3>
      <ul>
        <li><b>Pesquisa</b>: procura em todos os campos da tabela (processo, enc. PHC, cliente, ref. cliente, obra, localização, descrições, etc.).</li>
        <li><b>Multi-termos</b>: pode separar por <code>%</code> ou por espaços (ex.: <code>jf_viva%260006</code> ou <code>jf_viva 260006</code>).</li>
        <li><b>Filtros</b>: <b>Estado</b>, <b>Cliente</b> e <b>Responsável</b>. Use <code>Todos</code> para limpar.</li>
        <li><b>Sem resultados</b>: se existir pesquisa mas os filtros estiverem a bloquear resultados, o Martelo pergunta se pretende pesquisar em <code>Todos</code> (limpa filtros automaticamente).</li>
        <li><b>Dica</b>: os filtros são editáveis — pode escrever para encontrar rapidamente o cliente/responsável.</li>
      </ul>

      <h3>Criar e editar processos</h3>
      <ul>
        <li><b>Novo Processo</b>: cria um processo a partir de uma encomenda PHC (origens adicionais podem estar em desenvolvimento).</li>
        <li><b>Campos obrigatórios</b>: <code>Ano</code> e <code>Num Enc PHC</code>.</li>
        <li><b>Salvar</b>: grava as alterações do processo selecionado.</li>
        <li><b>Nova Versão Processo</b>: cria uma nova versão do processo (útil para revisões e para separar versões de obra/plano).</li>
        <li><b>Eliminar</b>: remove o processo selecionado (pode perguntar também pela pasta associada).</li>
        <li><b>Atualizar</b>: recarrega a lista de processos.</li>
        <li><b>Imprimir PDFs</b>: envia para impressão os PDFs associados ao processo selecionado.</li>
      </ul>

      <h3>Converter orçamento</h3>
      <ul>
        <li><b>Converter Orçamento</b>: seleciona um orçamento e cria automaticamente o processo de produção.</li>
        <li><b>Pré-requisito</b>: o orçamento deve ter o <code>Num Enc PHC (enc_phc)</code> preenchido.</li>
        <li><b>Versão CutRite (PP)</b>: ao converter é pedida a versão (por defeito <code>01</code>).</li>
      </ul>

      <h3>Pastas, IMOS e documentos</h3>
      <ul>
        <li><b>Criar Pasta</b>: cria/atualiza a <code>Pasta Servidor</code> do processo (base definida em <b>Configurações</b>).</li>
        <li><b>Abrir Pasta</b>: abre a pasta no Explorador.</li>
        <li><b>Lista Material_IMOS</b>: cria o Excel <code>Lista_Material_&lt;Nome Enc IMOS IX&gt;.xlsm</code> na Pasta Servidor (a partir do modelo) e preenche os dados.</li>
        <li><b>Nome Plano CUT-RITE</b> / <b>Nome Enc IMOS IX</b>: gerados automaticamente a partir dos campos (mantém padrão e facilita localizar ficheiros).</li>
        <li><b>Enviar CUT-RITE</b>: abre o CUT-RITE, cria a lista de peças com base no Excel de material e grava o plano com o <b>Nome Plano CUT-RITE</b>.</li>
        <li><b>Pré-requisitos CUT-RITE</b>: confirme em <b>Configurações</b> os caminhos <code>Executavel CUT-RITE</code>, <code>Pasta Trabalho CUT-RITE</code> e <code>Pasta Dados CUT-RITE</code>.</li>
        <li><b>Imagem/preview</b>: o painel de imagem tenta mostrar a imagem encontrada na estrutura do IMOS IX (se existir na pasta do IMOS).</li>
      </ul>

      <a name="dicas"></a>
      <h2>Dicas rápidas / Perguntas frequentes</h2>
      <ul>
        <li><b>O preço não mudou</b>: confirme que carregou em <code>Atualizar Custos</code> após alterações.</li>
        <li><b>Preciso repetir um item</b>: use <code>Duplicar</code> e ajuste apenas o necessário.</li>
        <li><b>Quero reaproveitar configurações</b>: grave um <b>Modelo</b> ou um <b>Módulo</b> (Utilizador ou Global).</li>
        <li><b>Separar consumos</b>: use <b>Divisão independente</b> para separar artigos/zonas.</li>
        <li><b>Bloquear linhas</b>: marque <code>BLK</code> para evitar alterações acidentais.</li>
      </ul>

      <p class="muted">Sugestões de melhoria: anote o cenário (ecrã/ações) e envie ao admin para ajustarmos o fluxo.</p>
    </body>
    </html>
    """


class _UpdateCheckWorker(QtCore.QObject):
    finished = QtCore.Signal(object)  # UpdateInfo

    def __init__(self, *, share_path: str) -> None:
        super().__init__()
        self._share_path = share_path

    @QtCore.Slot()
    def run(self) -> None:
        info = check_for_updates(share_path=self._share_path)
        self.finished.emit(info)


class AjudaPage(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, *, current_user: Optional[Any] = None) -> None:
        super().__init__(parent)
        self._current_user = current_user
        self._update_info: Optional[UpdateInfo] = None
        self._update_thread: Optional[QtCore.QThread] = None
        self._update_worker: Optional[_UpdateCheckWorker] = None
        self._version_loaded: bool = False

        self.setObjectName("AjudaPage")
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QtWidgets.QLabel("Ajuda")
        header_font = header.font()
        header_font.setPointSize(max(header_font.pointSize(), 12) + 2)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)

        self.tabs = QtWidgets.QTabWidget(self)
        layout.addWidget(self.tabs, 1)

        # --------------------
        # TAB: Ajuda
        # --------------------
        self.tab_help = QtWidgets.QWidget(self)
        help_layout = QtWidgets.QVBoxLayout(self.tab_help)
        help_layout.setContentsMargins(0, 0, 0, 0)
        help_layout.setSpacing(8)

        search_row = QtWidgets.QHBoxLayout()
        self.ed_search = QtWidgets.QLineEdit(self.tab_help)
        self.ed_search.setPlaceholderText("Pesquisar na ajuda... (Ctrl+F)")
        self.btn_prev = QtWidgets.QPushButton("Anterior", self.tab_help)
        self.btn_next = QtWidgets.QPushButton("Próximo", self.tab_help)
        self.btn_top = QtWidgets.QPushButton("Topo", self.tab_help)
        self.btn_clear = QtWidgets.QToolButton(self.tab_help)
        self.btn_clear.setText("X")
        self.btn_clear.setToolTip("Limpar pesquisa")
        self.btn_clear.setAutoRaise(True)

        self.btn_prev.clicked.connect(lambda: self._find(backward=True))
        self.btn_next.clicked.connect(lambda: self._find(backward=False))
        self.btn_top.clicked.connect(self._scroll_top)
        self.btn_clear.clicked.connect(self._clear_search)
        self.ed_search.returnPressed.connect(lambda: self._find(backward=False))
        self.ed_search.textChanged.connect(self._on_search_text_changed)

        search_row.addWidget(self.ed_search, 1)
        search_row.addWidget(self.btn_prev)
        search_row.addWidget(self.btn_next)
        search_row.addWidget(self.btn_top)
        search_row.addWidget(self.btn_clear)
        help_layout.addLayout(search_row)

        self.browser = QtWidgets.QTextBrowser(self.tab_help)
        self.browser.setOpenExternalLinks(True)
        self.browser.setHtml(_help_html(current_user=self._current_user))
        help_layout.addWidget(self.browser, 1)

        self.btn_prev.setEnabled(False)
        self.btn_next.setEnabled(False)

        self.tabs.addTab(self.tab_help, "Ajuda")

        # --------------------
        # TAB: Versão
        # --------------------
        self.tab_version = QtWidgets.QWidget(self)
        self._build_version_tab(self.tab_version)
        self.tabs.addTab(self.tab_version, "Versão")
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:  # type: ignore[override]
        if event.matches(QtGui.QKeySequence.Find):
            try:
                self.tabs.setCurrentWidget(self.tab_help)
            except Exception:
                pass
            self.ed_search.setFocus()
            self.ed_search.selectAll()
            return
        super().keyPressEvent(event)

    def _scroll_top(self) -> None:
        try:
            self.browser.verticalScrollBar().setValue(0)
        except Exception:
            self.browser.moveCursor(QtGui.QTextCursor.Start)

    def _clear_search(self) -> None:
        self.ed_search.setText("")
        self.browser.moveCursor(QtGui.QTextCursor.Start)

    def _on_search_text_changed(self, text: str) -> None:
        if not text.strip():
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)
            return
        self.btn_prev.setEnabled(True)
        self.btn_next.setEnabled(True)

    def _find(self, *, backward: bool) -> None:
        term = (self.ed_search.text() or "").strip()
        if not term:
            return

        flags = QtGui.QTextDocument.FindFlags()
        if backward:
            flags |= QtGui.QTextDocument.FindBackward

        found = self.browser.find(term, flags)
        if found:
            return

        cursor = self.browser.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End if backward else QtGui.QTextCursor.Start)
        self.browser.setTextCursor(cursor)
        self.browser.find(term, flags)

    def _build_version_tab(self, tab: QtWidgets.QWidget) -> None:
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        intro = QtWidgets.QLabel(
            "Aqui pode ver a versão instalada e verificar se existe uma atualização no servidor.\n"
            "A atualização é distribuída como um Setup (instalador) colocado na pasta partilhada."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        row_share = QtWidgets.QHBoxLayout()
        lbl_share = QtWidgets.QLabel("Pasta do instalador:")
        self.ed_share_path = QtWidgets.QLineEdit(tab)
        self.ed_share_path.setReadOnly(True)
        self.ed_share_path.setText(get_setup_share_path())
        btn_open_share = QtWidgets.QPushButton("Abrir", tab)
        btn_open_share.setToolTip("Abrir a pasta no Explorador do Windows.")
        btn_open_share.clicked.connect(self._open_share_folder)
        row_share.addWidget(lbl_share)
        row_share.addWidget(self.ed_share_path, 1)
        row_share.addWidget(btn_open_share)
        layout.addLayout(row_share)

        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)

        grid.addWidget(QtWidgets.QLabel("Versão instalada:"), 0, 0)
        self.lbl_installed = QtWidgets.QLabel("-", tab)
        grid.addWidget(self.lbl_installed, 0, 1)

        grid.addWidget(QtWidgets.QLabel("Última versão no servidor:"), 1, 0)
        self.lbl_latest = QtWidgets.QLabel("-", tab)
        grid.addWidget(self.lbl_latest, 1, 1)

        grid.addWidget(QtWidgets.QLabel("Instalador:"), 2, 0)
        self.ed_latest_installer = QtWidgets.QLineEdit(tab)
        self.ed_latest_installer.setReadOnly(True)
        grid.addWidget(self.ed_latest_installer, 2, 1)

        grid.addWidget(QtWidgets.QLabel("Estado:"), 3, 0)
        self.lbl_status = QtWidgets.QLabel("-", tab)
        self.lbl_status.setWordWrap(True)
        grid.addWidget(self.lbl_status, 3, 1)

        layout.addLayout(grid)

        # Mostrar a versão atual por defeito (sem depender do botão "Verificar agora")
        current_version = (get_current_version() or "").strip()
        if current_version:
            self.lbl_installed.setText(current_version)

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_check_updates = QtWidgets.QPushButton("Verificar agora", tab)
        self.btn_check_updates.clicked.connect(self._start_update_check)
        self.btn_install_update = QtWidgets.QPushButton("Instalar atualização", tab)
        self.btn_install_update.setEnabled(False)
        self.btn_install_update.clicked.connect(self._install_update)
        btn_row.addWidget(self.btn_check_updates)
        btn_row.addWidget(self.btn_install_update)
        btn_row.addStretch(1)

        self.btn_email_updates = QtWidgets.QPushButton("Enviar email de atualização (admin)", tab)
        self.btn_email_updates.setToolTip(
            "Envia um email a cada utilizador a informar que existe uma nova versão.\n"
            "Disponível apenas para o utilizador admin."
        )
        self.btn_email_updates.clicked.connect(self._email_updates_to_users)
        if not self._is_admin_user():
            self.btn_email_updates.setVisible(False)
        btn_row.addWidget(self.btn_email_updates)

        layout.addLayout(btn_row)
        layout.addStretch(1)

    def _on_tab_changed(self, _idx: int) -> None:
        if self.tabs.currentWidget() is not self.tab_version:
            return
        if self._version_loaded:
            return
        self._version_loaded = True
        QtCore.QTimer.singleShot(0, self._start_update_check)

    def _is_admin_user(self) -> bool:
        u = self._current_user
        if u is None:
            return False
        username = str(getattr(u, "username", "") or "").strip().lower()
        role = str(getattr(u, "role", "") or "").strip().lower()
        return username == "admin" or role == "admin"

    def _open_share_folder(self) -> None:
        path = (self.ed_share_path.text() or "").strip()
        if not path:
            return
        try:
            subprocess.Popen(["explorer.exe", path], close_fds=True)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Versão", f"Não foi possível abrir a pasta:\n{exc}")

    def _start_update_check(self) -> None:
        if self._update_thread and self._update_thread.isRunning():
            return

        share_path = (self.ed_share_path.text() or "").strip() or get_setup_share_path()
        self.ed_share_path.setText(share_path)

        self.btn_check_updates.setEnabled(False)
        self.lbl_status.setText("A verificar...")
        self.btn_install_update.setEnabled(False)
        self.ed_latest_installer.setText("")
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        worker = _UpdateCheckWorker(share_path=share_path)
        thread = QtCore.QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_update_check_finished)

        self._update_worker = worker
        self._update_thread = thread
        thread.start()

    @QtCore.Slot(object)
    def _on_update_check_finished(self, info: UpdateInfo) -> None:
        worker = self._update_worker
        thread = self._update_thread
        self._update_worker = None
        self._update_thread = None

        try:
            QtWidgets.QApplication.restoreOverrideCursor()
        except Exception:
            pass

        if worker is not None:
            worker.deleteLater()
        if thread is not None:
            thread.quit()
            thread.wait()
            thread.deleteLater()

        self._update_info = info
        self.btn_check_updates.setEnabled(True)

        installed = (info.installed_version or "").strip()
        self.lbl_installed.setText(installed or "(não detetada)")

        if info.error:
            self.lbl_latest.setText("(erro)")
            self.lbl_status.setText(f"Falha ao verificar atualizações: {info.error}")
            self.btn_install_update.setEnabled(False)
            return

        latest = info.latest_version or ""
        if not latest or not info.latest_installer:
            self.lbl_latest.setText("(não encontrado)")
            self.lbl_status.setText("Não foi encontrado nenhum instalador válido na pasta do servidor.")
            self.btn_install_update.setEnabled(False)
            return

        self.lbl_latest.setText(latest)
        self.ed_latest_installer.setText(str(info.latest_installer.path))

        if info.has_update:
            self.lbl_status.setText("Existe uma atualização disponível.")
            self.btn_install_update.setEnabled(True)
        else:
            self.lbl_status.setText("Está atualizado.")
            self.btn_install_update.setEnabled(False)

    def _install_update(self) -> None:
        info = self._update_info
        if not info or not info.latest_installer:
            QtWidgets.QMessageBox.information(self, "Versão", "Nenhum instalador encontrado.")
            return

        setup_path = info.latest_installer.path
        latest_version = info.latest_version or setup_path.name
        resp = QtWidgets.QMessageBox.question(
            self,
            "Atualizar",
            "O programa vai fechar e iniciar o instalador para atualizar.\n\n"
            f"Versão disponível: {latest_version}\n\n"
            "Pretende continuar?",
        )
        if resp != QtWidgets.QMessageBox.Yes:
            return

        staged = setup_path
        try:
            staged = stage_installer_to_temp(setup_path)
        except Exception:
            staged = setup_path

        try:
            launch_installer(staged)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Atualizar", f"Falha ao iniciar o instalador:\n{exc}")
            return

        app = QtWidgets.QApplication.instance()
        if app is not None:
            QtCore.QTimer.singleShot(200, app.quit)

    def _email_updates_to_users(self) -> None:
        if not self._is_admin_user():
            return

        info = self._update_info
        if not info or not info.latest_installer or not info.latest_version:
            QtWidgets.QMessageBox.information(
                self,
                "Versão",
                "Primeiro verifique as atualizações para obter a versão mais recente.",
            )
            return

        latest_version = info.latest_version
        installer_path = str(info.latest_installer.path)
        share_path = info.share_path

        default_text = (
            f"Existe uma nova versão do Martelo Orcamentos V2 disponível: {latest_version}.\n"
            "Para atualizar, feche o programa e execute o instalador:\n"
            f"{installer_path}\n\n"
            f"Pasta: {share_path}\n"
        )
        notes, ok = QtWidgets.QInputDialog.getMultiLineText(
            self,
            "Enviar email de atualização",
            "Mensagem a enviar aos utilizadores:",
            default_text,
        )
        if not ok:
            return
        notes = (notes or "").strip()
        if not notes:
            return

        db = SessionLocal()
        try:
            users = db.query(User).filter(User.is_active == True).all()  # noqa: E712
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Versão", f"Falha ao carregar utilizadores:\n{exc}")
            return
        finally:
            db.close()

        recipients: list[User] = []
        for u in users:
            email_addr = str(getattr(u, "email", "") or "").strip()
            if not email_addr:
                continue
            recipients.append(u)

        if not recipients:
            QtWidgets.QMessageBox.information(self, "Versão", "Nenhum utilizador com email definido.")
            return

        subject = f"[Martelo Orcamentos V2] Atualização disponível (v{latest_version})"

        sender_email = str(getattr(self._current_user, "email", "") or "").strip() or None
        sender_name = str(getattr(self._current_user, "username", "") or "").strip() or None

        progress = QtWidgets.QProgressDialog("A enviar emails...", "Cancelar", 0, len(recipients), self)
        progress.setWindowTitle("Enviar emails")
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()

        ok_count = 0
        errors: list[str] = []
        for idx, u in enumerate(recipients, start=1):
            progress.setValue(idx - 1)
            QtWidgets.QApplication.processEvents()
            if progress.wasCanceled():
                break

            to_addr = str(getattr(u, "email", "") or "").strip()
            user_name = str(getattr(u, "username", "") or "").strip()

            safe_notes = "<br>".join(html.escape(line) for line in notes.splitlines())
            body = (
                "<p>Olá,</p>"
                f"<p>{safe_notes}</p>"
                "<p>Com os melhores cumprimentos,<br>{{assinatura}}</p>"
            )
            try:
                send_email(
                    to_addr,
                    subject,
                    body,
                    anexos=None,
                    remetente_email=sender_email,
                    remetente_nome=sender_name,
                    cc=None,
                )
                ok_count += 1
            except Exception as exc:
                errors.append(f"{user_name or to_addr}: {exc}")

        progress.setValue(len(recipients))

        if errors:
            QtWidgets.QMessageBox.warning(
                self,
                "Enviar emails",
                f"Enviados: {ok_count}/{len(recipients)}\n\nErros:\n" + "\n".join(errors),
            )
        else:
            QtWidgets.QMessageBox.information(self, "Enviar emails", f"Enviados: {ok_count}/{len(recipients)}")
