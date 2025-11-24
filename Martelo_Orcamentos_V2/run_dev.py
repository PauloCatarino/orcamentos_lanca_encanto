# run_dev.py


import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("Martelo_Orcamentos_V2.app.services.dados_items").setLevel(logging.WARNING)
logging.getLogger("Martelo_Orcamentos_V2.app.services.dados_gerais").setLevel(logging.INFO)
logging.getLogger("Martelo_Orcamentos_V2.ui.models.qt_table").setLevel(logging.INFO)
logging.getLogger("Martelo_Orcamentos_V2.ui.pages.dados_gerais").setLevel(logging.INFO)
logging.getLogger("passlib.handlers.bcrypt").setLevel(logging.ERROR)

import sys
from PySide6 import QtWidgets
from Martelo_Orcamentos_V2.app.db import SessionLocal, init_db
from Martelo_Orcamentos_V2.ui.login import LoginDialog
from Martelo_Orcamentos_V2.ui.main_window import MainWindow



# Para correr a aplicação em modo desenvolvimento (com recarregamento automático):





# python -m Martelo_Orcamentos_V2.run_dev   -> para testar           
# .\build_exe.bat                           -> para criar o executável que fica na pasta dist\Martelo_Orcamentos_V2\Martelo_Orcamentos_V2.exe                          


#(.venv_Martelo) PS C:\Users\Utilizador\Documents\Martelo_Orcamentos_V2> python -m Martelo_Orcamentos_V2.run_dev



# Ativar o ambiente virtual powershell  ->          .\.venv_Martelo\Scripts\Activate.ps1

'''
git pull origin main  # Atualizar o repositório local
# Fazer as alterações necessárias no código

git add .
git commit -m "399"
git push origin main

'''

# python -m Martelo_Orcamentos_V2.scripts.seed_admin --username admin --password admin123 --role admin  -> Credenciais iniciais para o admin (se não existir, criar com script seed_admin.py): -    
# python -m Martelo_Orcamentos_V2.scripts.seed_admin --username Paulo --password 123456 --role user     -> Para criar outro user normal


# user : admin
# pass : admin123


def main():
    app = QtWidgets.QApplication(sys.argv)
    init_db()
    # Requer login normal
    login = LoginDialog()
    if login.exec() == QtWidgets.QDialog.Accepted:
        mw = MainWindow(current_user=login.current_user)
        mw.showMaximized()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()

