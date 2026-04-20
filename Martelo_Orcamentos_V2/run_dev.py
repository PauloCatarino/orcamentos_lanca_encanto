# run_dev.py

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import threading
from urllib.parse import urlsplit, urlunsplit
import sys

from PySide6 import QtWidgets, QtGui, QtCore

from Martelo_Orcamentos_V2.app.config import settings
from Martelo_Orcamentos_V2.app.db import SessionLocal, init_db
from Martelo_Orcamentos_V2.app.services.modulos import DEFAULT_BASE_DADOS_ORC, KEY_ORC_DB_BASE

from Martelo_Orcamentos_V2.app.services.settings import get_setting
from Martelo_Orcamentos_V2.app.services import modulos_referencia as svc_modulos_referencia
from Martelo_Orcamentos_V2.ui.login import LoginDialog
import getpass
import os
from Martelo_Orcamentos_V2.ui.main_window import MainWindow

# Para correr a aplicação em modo desenvolvimento (com recarregamento automático):

# este codigo serve para compitar os ficheiro que estão na pasta '\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Compras\Tabela e Catalogos_Fornecedores\Tabelas Preços\Pesquisa_Profunda_IA' para serem usados por pesquisa IA
#     python scripts/ingest_profundo.py --embeddings data/ia_embeddings

# 1º Ativar o ambiente virtual powershell  ->    .\.venv_Martelo\Scripts\Activate.ps1         -> RESULTADO NO TERMINAL   (.venv_Martelo) PS C:\Users\Utilizador\Documents\Martelo_Orcamentos_V2>
# 2º para testar Orçamentos ->                 python -m Martelo_Orcamentos_V2.run_dev            -> RESULTADO NO TERMINAL (.venv_Martelo) PS C:\Users\Utilizador\Documents\Martelo_Orcamentos_V2> python -m Martelo_Orcamentos_V2.run_dev                                    

# 3º Para criar o ficheiro executavel 'Setup_Martelo_Orcamentos_V2.exe' com indicação automatica da proxima versao existe um ficheiro release.bat que tem o seguinte conteudo (atualizar o numero da versao antes de correr):
# este ficheiro "release.bat" tem o seguinte conteudo (atualizar o numero da versao antes de correr):
# esta na pasta C:\Users\Utilizador\Documents\Martelo_Orcamentos_V2\release.bat 
# o ficheiro *executavel 'Setup_Martelo_Orcamentos_V2.exe' fica na pasta C:\Users\Utilizador\Documents\Martelo_Orcamentos_V2\dist\Setup_Martelo_Orcamentos_V2.exe e fica tambem 
# na pasta do servidor para ser partilhado com os utilizadores na pasta \\SERVER_LE\_Lanca_Encanto\LancaEncanto\Dep._Orcamentos\Instalador_Setup_Martelo_Orcamentos_V2 
'''
git pull origin main  # Atualizar o repositório local
# Fazer as alterações necessárias no código

git add .
git commit -m "399"
git push origin main

'''

## Credenciais iniciais para o admin (se não existir, criar com script seed_admin.py): ->     python -m Martelo_Orcamentos_V2.scripts.seed_admin --username admin --password admin123 --role admin
# python -m Martelo_Orcamentos_V2.scripts.seed_admin --username Paulo --password 123456 --role user -> cria user normal permite criar novos utilizadores

# user : admin                  user: paulo
# pass : admin123               pass: 123456

def _mask_db_uri(uri: str) -> str:
    """Esconde a palavra-passe na URI para logging."""
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

_LOG_USER_LABEL = "-"
_APP_QUITTING = False
_STARTUP_VIDEO_DIALOG = None

class _UserContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.user = _LOG_USER_LABEL
        return True

def _set_log_user(user) -> None:
    global _LOG_USER_LABEL
    if user is None:
        _LOG_USER_LABEL = "-"
        return
    username = getattr(user, "username", None) or getattr(user, "email", None) or None
    if not username:
        username = str(getattr(user, "id", "") or "-")
    _LOG_USER_LABEL = str(username)

def _mark_app_quitting() -> None:
    global _APP_QUITTING
    _APP_QUITTING = True

def _setup_logging() -> Path:
    """Cria logging para consola + ficheiro (junto ao exe ou ao script)."""
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        # 1) Preferir pasta do utilizador (Program Files pode ser read-only ou virtualizado)
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            candidates.append(Path(base) / "Martelo_Orcamentos_V2")
        # 2) Ao lado do .exe (apenas se tiver permissoes)
        try:
            candidates.append(Path(sys.executable).resolve().parent)
        except Exception:
            pass
    else:
        candidates.append(Path(__file__).resolve().parent)

    formatter = logging.Formatter("%(asctime)s %(levelname)s [user=%(user)s] %(name)s: %(message)s")
    user_filter = _UserContextFilter()

    last_exc: Exception | None = None
    for log_dir in candidates:
        log_path = log_dir / "martelo_debug.log"
        try:
            log_dir.mkdir(parents=True, exist_ok=True)


            sh = logging.StreamHandler(sys.stdout)
            sh.setLevel(logging.INFO)
            sh.setFormatter(formatter)
            sh.addFilter(user_filter)

            # Nao limpar logs a cada arranque para manter historico de erros anteriores.
            fh = RotatingFileHandler(log_path, mode="a", maxBytes=5_000_000, backupCount=5, encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            fh.setFormatter(formatter)
            fh.addFilter(user_filter)

            # `force=True` é importante porque alguns módulos (ex.: app/db.py) chamam basicConfig ao importar.
            logging.basicConfig(level=logging.DEBUG, handlers=[sh, fh], force=True)
            logging.captureWarnings(True)
            logging.getLogger("Martelo_Orcamentos_V2.app.services.dados_items").setLevel(logging.WARNING)
            logging.getLogger("Martelo_Orcamentos_V2.app.services.dados_gerais").setLevel(logging.INFO)
            logging.getLogger("Martelo_Orcamentos_V2.ui.models.qt_table").setLevel(logging.INFO)
            logging.getLogger("Martelo_Orcamentos_V2.ui.pages.dados_gerais").setLevel(logging.INFO)
            logging.getLogger("matplotlib").setLevel(logging.WARNING)
            logging.getLogger("matplotlib.font_manager").setLevel(logging.WARNING)
            logging.getLogger("passlib.handlers.bcrypt").setLevel(logging.ERROR)

            masked_uri = _mask_db_uri(settings.DB_URI)
            logging.getLogger(__name__).info("Logging em: %s", log_path)
            logging.getLogger(__name__).info("DB_URI usado: %s", masked_uri)
            return log_path
        except Exception as exc:
            last_exc = exc
            continue

    # fallback: sem ficheiro (último recurso)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", force=True)
    logging.getLogger(__name__).warning("Nao foi possivel criar ficheiro de log (%s)", last_exc)
    return (candidates[0] / "martelo_debug.log") if candidates else Path("martelo_debug.log")

def _install_exception_hooks() -> None:
    def _handle_exception(exc_type, exc, tb):
        logging.getLogger("Martelo_Orcamentos_V2").critical("Excecao nao tratada", exc_info=(exc_type, exc, tb))
        try:
            sys.__excepthook__(exc_type, exc, tb)
        except Exception:
            pass

    sys.excepthook = _handle_exception

    if hasattr(threading, "excepthook"):
        def _handle_thread_exception(args):  # type: ignore[no-redef]
            logging.getLogger("Martelo_Orcamentos_V2").critical(
                "Excecao nao tratada em thread",
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            )

        threading.excepthook = _handle_thread_exception  # type: ignore[attr-defined]

class MarteloApplication(QtWidgets.QApplication):
    def notify(self, receiver: QtCore.QObject, event: QtCore.QEvent) -> bool:  # type: ignore[override]
        try:
            return super().notify(receiver, event)
        except Exception as exc:
            # Em shutdown é comum existirem eventos tardios para widgets já destruídos.
            # Não é um erro real para o utilizador, portanto evitamos spam no terminal.
            if isinstance(exc, RuntimeError) and "already deleted" in str(exc):
                try:
                    closing_down = bool(getattr(QtCore.QCoreApplication, "closingDown", lambda: False)())
                except Exception:
                    closing_down = False
                if closing_down or _APP_QUITTING:
                    return False
            try:
                event_type = int(event.type())
            except Exception:
                event_type = -1
            logging.getLogger("Martelo_Orcamentos_V2").exception(
                "Excecao no loop Qt (receiver=%s event_type=%s)",
                type(receiver).__name__ if receiver is not None else "None",
                event_type,
            )
            return False

def _apply_app_icon(app: QtWidgets.QApplication) -> None:
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "Martelo_Orcamentos_V2" / "martelo.ico")
        candidates.append(Path(meipass) / "martelo.ico")
    # dev / source tree
    candidates.append(Path(__file__).resolve().parent / "martelo.ico")
    candidates.append(Path(__file__).resolve().parent.parent / "martelo.ico")

    for path in candidates:
        try:
            if path and path.exists():
                icon = QtGui.QIcon(str(path))
                if not icon.isNull():
                    app.setWindowIcon(icon)
                    return
        except Exception:
            continue

def _get_auto_login_credentials(db) -> tuple[str | None, str | None, bool]:
    """Tenta obter credenciais de login automático baseado no usuário do sistema."""
    try:
        # Obtém o usuário do sistema operacional
        system_user = getpass.getuser().lower()
        
        # Primeiro tenta obter mapeamento personalizado via settings
        mapping_key = f"user_mapping_{system_user}"
        martelo_user = get_setting(db, mapping_key)
        
        # Se não encontrou mapeamento personalizado, usa mapeamento padrão
        if not martelo_user:
            # Mapeamento padrão (pode ser expandido)
            default_mapping = {
                'utilizador': 'Paulo',  # Exemplo: usuário Windows 'utilizador' mapeia para 'Paulo' no Martelo
                # Adicione mais mapeamentos padrão conforme necessário
                # 'usuario_windows': 'usuario_martelo',
            }
            martelo_user = default_mapping.get(system_user)
            
        if not martelo_user:
            return None, None, False
            
        # Verifica se o usuário existe no banco
        from Martelo_Orcamentos_V2.app.models import User
        user = db.query(User).filter(User.username == martelo_user, User.is_active == True).first()
        if not user:
            return None, None, False
            
        # Verifica se o pré-preenchimento está habilitado globalmente
        auto_fill_enabled = get_setting(db, "auto_fill_login", "true").lower() == "true"
        if not auto_fill_enabled:
            return None, None, False
            
        # Verifica se o login automático está habilitado para este usuário específico
        auto_login_enabled = get_setting(db, f"auto_login_{martelo_user}", "false").lower() == "true"
        
        if auto_login_enabled:
            # Para login automático seguro, seria necessário armazenar senha criptografada
            # Por enquanto, apenas pré-preenche o usuário
            return martelo_user, None, False
        else:
            # Apenas pré-preenche o usuário
            return martelo_user, None, False
            
    except Exception:
        return None, None, False
    
def main():
    log_path = _setup_logging()
    _install_exception_hooks()
    logging.getLogger(__name__).info("Arranque da aplicacao (logs em %s)", log_path)
    app = MarteloApplication(sys.argv)
    app.aboutToQuit.connect(_mark_app_quitting)
    _apply_app_icon(app)
    # Estilo global para seleções das tabelas (cinza escuro / texto branco)
    base_stylesheet = app.styleSheet() or ""
    selection_style = (
        "QTableView::item:selected{background-color:#555555;color:#ffffff;}"
        "QTableView::item:selected:active{background-color:#555555;color:#ffffff;}"
        "QTableView::item:selected:!active{background-color:#666666;color:#ffffff;}"
        "QTableView::item:hover{background-color:#6a6a6a;color:#ffffff;}"
    )
    app.setStyleSheet(f"{base_stylesheet}\n{selection_style}")
    init_db()

    bootstrap_db = SessionLocal()
    try:
        created_reference_modules = svc_modulos_referencia.ensure_reference_modules(bootstrap_db)
        bootstrap_db.commit()
        if created_reference_modules:
            logging.getLogger(__name__).info(
                "Modulos globais de referencia criados no arranque: %s",
                created_reference_modules,
            )
    except Exception as exc:
        try:
            bootstrap_db.rollback()
        except Exception:
            pass
        logging.getLogger(__name__).warning(
            "Falha ao garantir modulos globais de referencia: %s",
            exc,
        )
    finally:
        bootstrap_db.close()
    
    # Tenta obter credenciais de login automático
    db = SessionLocal()
    try:
        auto_user, auto_password, auto_submit = _get_auto_login_credentials(db)
    finally:
        db.close()
    
    # Login com possível pré-preenchimento automático
    login = LoginDialog(auto_user=auto_user, auto_password=auto_password, auto_submit=auto_submit)
    if login.exec() == QtWidgets.QDialog.Accepted:
        _set_log_user(login.current_user)
        logging.getLogger(__name__).info(
            "Login efetuado com sucesso (user=%s)",
            getattr(login.current_user, "username", "-"),
        )
        mw = MainWindow(current_user=login.current_user)
        mw.showMaximized()
        
        sys.exit(app.exec())

if __name__ == "__main__":
    main()
