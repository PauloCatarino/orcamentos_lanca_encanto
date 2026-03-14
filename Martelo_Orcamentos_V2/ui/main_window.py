from typing import Optional
import random
import logging
from urllib.parse import urlsplit, urlunsplit

from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtCore import Qt

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from Martelo_Orcamentos_V2.app.config import settings
from Martelo_Orcamentos_V2.app.db import SessionLocal, engine, register_disconnect_handler
from .pages.orcamentos import OrcamentosPage
from .pages.itens import ItensPage
from .pages.materias_primas import MateriasPrimasPage
from .pages.clientes import ClientesPage
from .pages.dados_gerais import DadosGeraisPage
from .pages.dados_items import DadosItemsPage
from .pages.custeio_items import CusteioItemsPage
from .pages.relatorios import RelatoriosPage
from .pages.settings import SettingsPage
from .pages.producao import ProducaoPage
from .pages.ajuda import AjudaPage
from .pages.Encomendas_PHC import EncomendasPHCPage  # Encomendas PHC (consultas externas, read-only)


logger = logging.getLogger(__name__)


def _mask_db_uri(uri: str) -> str:
    try:
        parts = urlsplit(uri)
        if not parts.username:
            return uri
        host_port = parts.hostname or ""
        if parts.port:
            host_port = f"{host_port}:{parts.port}"
        user_part = f"{parts.username}:****@" if parts.username else ""
        netloc = f"{user_part}{host_port}"
        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    except Exception:
        return uri


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.setWindowIcon(QtWidgets.QApplication.windowIcon())
        self.setWindowTitle("Martelo Orçamentos V2")
        self.resize(1200, 800)

        self.current_orcamento_id: Optional[int] = None
        self.current_item_id: Optional[int] = None

        self.nav = QtWidgets.QTreeWidget()
        self.nav.setHeaderHidden(True)
        self.nav.setExpandsOnDoubleClick(False)
        self.nav.setRootIsDecorated(True)
        # Reduce navigation width to give more space to the main content
        self.nav.setFixedWidth(145)
        self._nav_items = {}
        self._nav_base_point_size = self.nav.font().pointSize()
        self._nav_active_delta = 1

        # Orcamentos group

        orc_node = QtWidgets.QTreeWidgetItem(["Orcamentos"])
        orc_node.setData(0, Qt.UserRole, 0)
        self.nav.addTopLevelItem(orc_node)
        self._nav_items["orcamentos"] = orc_node

        def _add_child(parent, text, stack_index, key):
            item = QtWidgets.QTreeWidgetItem([text])
            item.setData(0, Qt.UserRole, stack_index)
            parent.addChild(item)
            self._nav_items[key] = item
            return item

        _add_child(orc_node, "Items", 1, "items")
        _add_child(orc_node, "Dados Gerais", 4, "dados_gerais")
        _add_child(orc_node, "Dados Items", 5, "dados_items")
        _add_child(orc_node, "Custeio dos Items", 6, "custeio")
        _add_child(orc_node, "Relatorios", 7, "relatorios")
        orc_node.setExpanded(True)

        # Add standalone entries
        materias_node = QtWidgets.QTreeWidgetItem(["Materias Primas"])
        materias_node.setData(0, Qt.UserRole, 2)
        self.nav.addTopLevelItem(materias_node)
        self._nav_items["materias"] = materias_node

        clientes_node = QtWidgets.QTreeWidgetItem(["Clientes"])
        clientes_node.setData(0, Qt.UserRole, 3)
        self.nav.addTopLevelItem(clientes_node)
        self._nav_items["clientes"] = clientes_node

        configuracoes_node = QtWidgets.QTreeWidgetItem(["Configuracoes"])
        configuracoes_node.setData(0, Qt.UserRole, 8)
        self.nav.addTopLevelItem(configuracoes_node)
        self._nav_items["configuracoes"] = configuracoes_node

        producao_node = QtWidgets.QTreeWidgetItem(["Producao"])
        producao_node.setData(0, Qt.UserRole, 9)
        self.nav.addTopLevelItem(producao_node)
        self._nav_items["producao"] = producao_node

        # Encomendas PHC (apenas leitura / SELECT)
        encomendas_phc_node = QtWidgets.QTreeWidgetItem(["Encomendas PHC"])
        encomendas_phc_node.setData(0, Qt.UserRole, 12)
        self.nav.addTopLevelItem(encomendas_phc_node)
        self._nav_items["encomendas_phc"] = encomendas_phc_node

        ajuda_node = QtWidgets.QTreeWidgetItem(["Ajuda"])
        ajuda_node.setData(0, Qt.UserRole, 11)
        self.nav.addTopLevelItem(ajuda_node)
        self._nav_items["ajuda"] = ajuda_node

        sair_node = QtWidgets.QTreeWidgetItem(["Sair"])
        sair_node.setData(0, Qt.UserRole, 10)
        self.nav.addTopLevelItem(sair_node)
        self._nav_items["sair"] = sair_node

        self.nav.expandAll()
        self._reset_all_nav_item_styles()
        self.nav.expandAll()
        self._reset_all_nav_item_styles()
        self.stack = QtWidgets.QStackedWidget()

        self.pg_orc = OrcamentosPage(current_user=self.current_user)
        self.pg_itens = ItensPage(current_user=self.current_user)
        self.pg_itens.item_selected.connect(self.on_item_selected)
        self.pg_itens.production_mode_changed.connect(self.on_production_mode_changed)
        # NOVO: Conectar sinal de sincronização de preço
        self.pg_itens.price_changed.connect(self.on_price_changed)
        self.pg_materias = MateriasPrimasPage(current_user=self.current_user)
        self.pg_clientes = ClientesPage()
        self.pg_dados = DadosGeraisPage(current_user=self.current_user)
        self.pg_dados_items = DadosItemsPage(current_user=self.current_user)
        self.pg_custeio = CusteioItemsPage(current_user=self.current_user)
        self.pg_custeio.item_context_changed.connect(self.on_custeio_item_changed)
        self.pg_relatorios = RelatoriosPage(current_user=self.current_user)
        self.pg_producao = ProducaoPage(current_user=self.current_user)
        self.pg_ajuda = AjudaPage(current_user=self.current_user)
        self.pg_encomendas_phc = EncomendasPHCPage(current_user=self.current_user)
        self.pg_exit = QtWidgets.QWidget()
        exit_layout = QtWidgets.QVBoxLayout(self.pg_exit)
        exit_label = QtWidgets.QLabel("Para sair use o menu 'Sair' na navegação.\nGuardaremos o que estiver pendente antes de fechar.")
        exit_label.setWordWrap(True)
        exit_layout.addWidget(exit_label)
        exit_layout.addStretch(1)

        self.stack.addWidget(self.pg_orc)
        self.stack.addWidget(self.pg_itens)
        self.stack.addWidget(self.pg_materias)
        self.stack.addWidget(self.pg_clientes)
        self.stack.addWidget(self.pg_dados)
        self.stack.addWidget(self.pg_dados_items)
        self.stack.addWidget(self.pg_custeio)
        self.stack.addWidget(self.pg_relatorios)
        self.pg_settings = SettingsPage(current_user=self.current_user)
        self.pg_settings.margens_updated.connect(self.pg_itens.refresh_margem_defaults)
        self.stack.addWidget(self.pg_settings)
        self.stack.addWidget(self.pg_producao)
        self.stack.addWidget(self.pg_exit)
        self.stack.addWidget(self.pg_ajuda)
        # Encomendas PHC
        self.stack.addWidget(self.pg_encomendas_phc)

        self.nav.currentItemChanged.connect(self.on_nav_changed)
        self.pg_orc.orcamento_aberto.connect(self.on_abrir_orcamento)

        self.nav.setCurrentItem(self._nav_items["orcamentos"])
        self.stack.setCurrentIndex(0)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(central)
        layout.addWidget(self.nav)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        # Monitor de ligação DB (ex.: após hibernação/rede)
        self._db_online: bool = True
        self._db_watchdog = QtCore.QTimer(self)
        self._db_watchdog.setInterval(60_000)  # 60s
        self._db_watchdog.timeout.connect(self._on_db_watchdog_tick)
        self._db_watchdog.start()
        QtCore.QTimer.singleShot(2_000, self._on_db_watchdog_tick)
        register_disconnect_handler(self._on_db_disconnect_event)
        self._startup_daily_summary_done = False
        QtCore.QTimer.singleShot(1_500, self._show_startup_daily_summary)

    def _db_pages(self):
        return [
            getattr(self, "pg_orc", None),
            getattr(self, "pg_itens", None),
            getattr(self, "pg_materias", None),
            getattr(self, "pg_clientes", None),
            getattr(self, "pg_dados", None),
            getattr(self, "pg_dados_items", None),
            getattr(self, "pg_custeio", None),
            getattr(self, "pg_relatorios", None),
            getattr(self, "pg_settings", None),
            getattr(self, "pg_producao", None),
            getattr(self, "pg_encomendas_phc", None),
        ]

    def _reset_page_db(self, page) -> None:
        if page is None or not hasattr(page, "db"):
            return
        try:
            db = getattr(page, "db", None)
            if db is not None:
                try:
                    db.close()
                except Exception:
                    pass
        finally:
            try:
                page.db = SessionLocal()
            except Exception:
                pass

    def _cleanup_page_db(self, page) -> None:
        """
        Evita transações longas em sessões permanentes (muito comum em páginas GUI).
        Se houver apenas leitura/página inativa, fazemos rollback para libertar a ligação.
        """
        if page is None or not hasattr(page, "db"):
            return
        db = getattr(page, "db", None)
        if db is None:
            return
        try:
            has_pending = bool(getattr(db, "dirty", None) or getattr(db, "new", None) or getattr(db, "deleted", None))
        except Exception:
            has_pending = False
        if has_pending:
            return
        try:
            in_tx = bool(getattr(db, "in_transaction", lambda: False)())
        except Exception:
            in_tx = False
        if not in_tx:
            return
        try:
            db.rollback()
        except Exception:
            self._reset_page_db(page)

    def _ping_db(self) -> bool:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except (SQLAlchemyError, Exception) as exc:
            logger.warning("DB ping falhou: %s", exc)
            return False

    def _alert_db_offline(self) -> None:
        QtWidgets.QMessageBox.warning(
            self,
            "Base de Dados",
            "Perdeu ligacao a base de dados.\n\n"
            "Para evitar perda de dados, reinicie o Martelo.",
        )

    def _on_db_disconnect_event(self, _exc: BaseException) -> None:
        if not self._db_online:
            return
        self._db_online = False
        try:
            engine.dispose()
        except Exception:
            pass
        QtCore.QTimer.singleShot(0, self._alert_db_offline)

    def _on_db_watchdog_tick(self) -> None:
        # 1) libertar transações/ligações presas em sessões long-lived
        for page in self._db_pages():
            self._cleanup_page_db(page)

        # 2) ping leve para detetar queda de rede/hibernação
        ok = self._ping_db()
        if ok and not self._db_online:
            self._db_online = True
            for page in self._db_pages():
                self._reset_page_db(page)
            QtWidgets.QMessageBox.information(
                self,
                "Base de Dados",
                "Ligação à base de dados restabelecida. Pode continuar a trabalhar.",
            )
        elif (not ok) and self._db_online:
            self._db_online = False
            try:
                engine.dispose()
            except Exception:
                pass
            self._alert_db_offline()

    def _show_startup_daily_summary(self) -> None:
        if self._startup_daily_summary_done:
            return
        self._startup_daily_summary_done = True
        try:
            page = getattr(self, "pg_orc", None)
            if page is not None:
                page.show_daily_summary_dialog(force=False)
        except Exception:
            logger.exception("Falha ao mostrar resumo diario no arranque")

    def on_abrir_orcamento(self, orcamento_id: int):
        try:
            logger.info("Abrir orcamento id=%s (DB=%s)", orcamento_id, _mask_db_uri(settings.DB_URI))
        except Exception:
            logger.info("Abrir orcamento id=%s", orcamento_id)
        
        if self.current_orcamento_id:
            if not self.pg_custeio.auto_save_if_dirty():
                return
        self.current_orcamento_id = orcamento_id
        self.current_item_id = None
        self.pg_itens.load_orcamento(orcamento_id)
        self.pg_dados.load_orcamento(orcamento_id)
        self.pg_dados_items.load_item(orcamento_id, None)
        self.pg_custeio.load_item(orcamento_id, None)
        self.pg_settings.set_orcamento_context(orcamento_id)
        self.pg_relatorios.set_orcamento(orcamento_id)

        target_item = self._nav_items.get("items")
        if target_item:
            previous = self.nav.currentItem()
            if previous is not target_item:
                self.nav.blockSignals(True)
                self.nav.setCurrentItem(target_item)
                self.nav.blockSignals(False)
                if previous is not None:
                    self._set_nav_item_style(previous, active=False)
            self._set_nav_item_style(target_item, active=True)
        self.stack.setCurrentIndex(1)

    def on_nav_changed(self, current: Optional[QtWidgets.QTreeWidgetItem], previous: Optional[QtWidgets.QTreeWidgetItem]):
        if current is None:
            return
        index = current.data(0, Qt.UserRole)
        if index is None:
            # select first child if available
            if current.childCount():
                child = current.child(0)
                self.nav.blockSignals(True)
                self.nav.setCurrentItem(child)
                self.nav.blockSignals(False)
            return
        current_index = self.stack.currentIndex()
        if current_index == 6 and index != 6:
            if not self.pg_custeio.auto_save_if_dirty():
                self.nav.blockSignals(True)
                if previous:
                    self.nav.setCurrentItem(previous)
                self.nav.blockSignals(False)
                self.stack.setCurrentIndex(current_index)
                return
        if index == 10:
            self._prompt_exit(previous)
            return
        parent = current.parent()
        if parent:
            parent.setExpanded(True)
        self.stack.setCurrentIndex(index)
        if previous is not None:
            self._set_nav_item_style(previous, active=False)
        self._set_nav_item_style(current, active=True)

        if index == 0:
            self.pg_orc.reload_clients()
        elif index == 4 and self.current_orcamento_id:
            self.pg_dados.load_orcamento(self.current_orcamento_id)
        elif index == 5 and self.current_orcamento_id:
            self.pg_dados_items.load_item(self.current_orcamento_id, self.current_item_id)
        elif index == 6 and self.current_orcamento_id:
            self.pg_custeio.load_item(self.current_orcamento_id, self.current_item_id)
        elif index == 7 and self.current_orcamento_id:
            self.pg_relatorios.refresh_preview()
        elif index == 8 and self.current_orcamento_id:
            self.pg_settings.refresh_producao_mode()

    def on_item_selected(self, item_id: Optional[int]):
        if self.current_orcamento_id:
            if not self.pg_custeio.auto_save_if_dirty():
                return
        self.current_item_id = item_id
        if not self.current_orcamento_id:
            return
        self.pg_dados_items.load_item(self.current_orcamento_id, item_id)
        self.pg_custeio.load_item(self.current_orcamento_id, item_id)

    def on_production_mode_changed(self, modo: str):
        self.pg_settings.update_producao_mode_display(modo)
        if hasattr(self.pg_custeio, "on_production_mode_changed"):
            try:
                self.pg_custeio.on_production_mode_changed(modo)
            except Exception as exc:
                logger.exception("Falha ao atualizar modo de producao no custeio: %s", exc)

    def on_price_changed(self, orc_id: int, novo_preco: object):
        """NOVO: Sincroniza mudanças de preço entre menus Items e Orçamentos."""
        try:
            if self.pg_orc and hasattr(self.pg_orc, "on_price_changed_from_itens"):
                self.pg_orc.on_price_changed_from_itens(orc_id, novo_preco)
            # Refrescar tabela de orçamentos para mostrar novo preço
            if self.pg_orc and hasattr(self.pg_orc, "refresh_table"):
                self.pg_orc.refresh_table()
        except Exception as exc:
            logger.exception("Falha ao sincronizar preço: %s", exc)

    def on_custeio_item_changed(self, item_id: Optional[int]):
        if self.current_orcamento_id is None:
            return
        changed = item_id != self.current_item_id
        self.current_item_id = item_id
        if changed or self.stack.currentIndex() == 5:
            self.pg_dados_items.load_item(self.current_orcamento_id, item_id)
        if self.pg_itens and hasattr(self.pg_itens, "focus_item"):
            self.pg_itens.focus_item(item_id)

    def _reset_all_nav_item_styles(self) -> None:
        def reset_item(item: QtWidgets.QTreeWidgetItem) -> None:
            self._set_nav_item_style(item, active=False)
            for idx in range(item.childCount()):
                reset_item(item.child(idx))

        for idx in range(self.nav.topLevelItemCount()):
            reset_item(self.nav.topLevelItem(idx))

    def _set_nav_item_style(self, item: Optional[QtWidgets.QTreeWidgetItem], *, active: bool) -> None:
        if item is None:
            return
        font = item.font(0)
        font.setBold(active)
        font.setPointSize(self._nav_base_point_size + (self._nav_active_delta if active else 0))
        item.setFont(0, font)

    def _restore_nav(self, previous: Optional[QtWidgets.QTreeWidgetItem]) -> None:
        """Restaura a seleção anterior na navegação e mantém o stack atual."""
        if previous is None:
            return
        self.nav.blockSignals(True)
        self.nav.setCurrentItem(previous)
        self.nav.blockSignals(False)
        if previous.data(0, Qt.UserRole) is not None:
            try:
                self.stack.setCurrentIndex(previous.data(0, Qt.UserRole))
            except Exception:
                pass
        self._set_nav_item_style(previous, active=True)

    def _prompt_exit(self, previous: Optional[QtWidgets.QTreeWidgetItem]) -> None:
        """Pergunta ao utilizador se deseja sair, tenta gravar pendentes e mostra mensagem final."""
        try:
            if self.current_orcamento_id:
                if not self.pg_custeio.auto_save_if_dirty():
                    self._restore_nav(previous)
                    return
        except Exception as exc:
            logger.warning("Falha ao auto-gravar antes de sair: %s", exc)

        frases = [
            "Bom trabalho hoje! Cada corte conta para o próximo projeto.",
            "Respira fundo: amanhã há mais ideias para construir.",
            "Peças otimizadas, cabeça tranquila. Até já!",
            "O problema do Martelo são os Pregos. E tu já usaste muitos hoje!",
            "Guardar é garantir que nada se perde. Obrigado pelo empenho!",
            "Mais um dia bem cortado — até amanhã com mais ideias!",
            "Parabéns: hoje transformaste madeira em solução.",
            "Cada peça conta. Boa noite e mãos firmes amanhã.",
            "A oficina agradece o teu empenho — continua assim!",
            "Pequenos detalhes, grandes resultados. Obrigado pelo dia.",
            "Faz uma pausa: a melhor precisão vem com descanso.",
            "Metas cumpridas — o projeto avança.",
            "Excelente dia: desperdício minimizado, criatividade no máximo.",
            "Que os parafusos nunca faltem e as ideias não parem.",
            "Conta a história do dia pelas peças que saíram.",
            "Sair a ganhar: guardaste trabalho, poupaste tempo e aprendeste algo.",
            "Peças alinhadas, cabeça leve. Até amanhã!",
            "O segredo está no encaixe — bom descanso.",
            "A qualidade de hoje é o orgulho de amanhã.",
            "Obrigado pelo esforço — o martelo também reconhece.",
            "Respira, reorganiza, volta com vontade.",
            "Hoje fizeste bom trabalho — amanhã será ainda melhor.",
            "Um bom corte hoje evita retrabalho amanhã.",
            "Medei duas vezes, cortaste uma. Excelente disciplina.",
            "Boa noite — que a oficina fique calma e a mente criativa.",
            "A oficina fica mais forte com cada projeto finalizado.",
            "Pequenos progressos diários criam grandes móveis.",
            "O martelo descansa, mas as ideias ficam. Até já!",
            "Matéria-prima transformada por mãos competentes. Parabéns.",
            "O prazer está no acabamento — bom descanso!",
            "Obrigado por mais um dia de perfeição em pedaços.",
            "Deixa a poeira assentar — amanhã retomas com força.",
            "Os detalhes fazem a diferença — hoje fizeste muitos.",
            "Fechaste mais um orçamento — celebra essa conquista.",
            "Que estas peças te lembrem do quanto és capaz."
        ]
        inspiracao = random.choice(frases)
        resumo = []
        try:
            if self.current_orcamento_id:
                resumo.append(f"Orçamento ativo: {self.current_orcamento_id}")
            if self.current_item_id:
                resumo.append(f"Item ativo: {self.current_item_id}")
        except Exception:
            pass
        resumo_txt = "\n".join(resumo)

        box = QtWidgets.QMessageBox(self)
        box.setWindowTitle("Sair do Martelo")
        box.setIcon(QtWidgets.QMessageBox.Question)
        box.setText("Pretende sair do Martelo?")
        box.setInformativeText(f"{inspiracao}\n\n{resumo_txt}" if resumo_txt else inspiracao)
        box.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        box.setDefaultButton(QtWidgets.QMessageBox.No)
        ret = box.exec()
        if ret == QtWidgets.QMessageBox.Yes:
            QtWidgets.QApplication.quit()
        else:
            self._restore_nav(previous)
