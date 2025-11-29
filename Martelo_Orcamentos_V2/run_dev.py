# run_dev.py

import logging
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
import sys

from PySide6 import QtWidgets

from Martelo_Orcamentos_V2.app.config import settings
from Martelo_Orcamentos_V2.app.db import SessionLocal, init_db
from Martelo_Orcamentos_V2.ui.login import LoginDialog
from Martelo_Orcamentos_V2.ui.main_window import MainWindow


# Para correr a aplicação em modo desenvolvimento (com recarregamento automático):





# para testar ->                   python -m Martelo_Orcamentos_V2.run_dev                                       


#(.venv_Martelo) PS C:\Users\Utilizador\Documents\Martelo_Orcamentos_V2> python -m Martelo_Orcamentos_V2.run_dev



# Ativar o ambiente virtual powershell  ->          .\.venv_Martelo\Scripts\Activate.ps1
#  .\build_exe.bat    -> para criar o executável (na pasta dist) Martelo_Orcamentos_V2.exe

'''
git pull origin main  # Atualizar o repositório local
# Fazer as alterações necessárias no código

git add .
git commit -m "398"
git push origin main

'''

## Credenciais iniciais para o admin (se não existir, criar com script seed_admin.py): ->     python -m Martelo_Orcamentos_V2.scripts.seed_admin --username admin --password admin123 --role admin
# python -m Martelo_Orcamentos_V2.scripts.seed_admin --username Paulo --password 123456 --role user -> cria user normal permite criar novos utilizadores


# user : admin
# pass : admin123






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


def _setup_logging() -> Path:
    """Cria logging para consola + ficheiro (junto ao exe ou ao script)."""
    log_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    log_path = log_dir / "martelo_debug.log"

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handlers = [logging.StreamHandler(sys.stdout)]
    try:
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(formatter)
        fh.setLevel(logging.INFO)
        handlers.append(fh)
    except Exception as exc:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
        logging.getLogger(__name__).warning("Nao foi possivel criar ficheiro de log (%s)", exc)
        return log_path

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", handlers=handlers)
    logging.getLogger("Martelo_Orcamentos_V2.app.services.dados_items").setLevel(logging.WARNING)
    logging.getLogger("Martelo_Orcamentos_V2.app.services.dados_gerais").setLevel(logging.INFO)
    logging.getLogger("Martelo_Orcamentos_V2.ui.models.qt_table").setLevel(logging.INFO)
    logging.getLogger("Martelo_Orcamentos_V2.ui.pages.dados_gerais").setLevel(logging.INFO)
    logging.getLogger("passlib.handlers.bcrypt").setLevel(logging.ERROR)

    masked_uri = _mask_db_uri(settings.DB_URI)
    logging.getLogger(__name__).info("Logging em: %s", log_path)
    logging.getLogger(__name__).info("DB_URI usado: %s", masked_uri)
    return log_path


def main():
    log_path = _setup_logging()
    logging.getLogger(__name__).info("Arranque da aplicacao (logs em %s)", log_path)
    app = QtWidgets.QApplication(sys.argv)
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
    # Requer login normal
    login = LoginDialog()
    if login.exec() == QtWidgets.QDialog.Accepted:
        mw = MainWindow(current_user=login.current_user)
        mw.showMaximized()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()
