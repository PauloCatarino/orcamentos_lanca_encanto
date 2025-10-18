# run_dev.py


import logging
logging.getLogger("passlib.handlers.bcrypt").setLevel(logging.ERROR)

import sys
from PySide6 import QtWidgets
from Martelo_Orcamentos_V2.app.db import SessionLocal, init_db
from Martelo_Orcamentos_V2.ui.login import LoginDialog
from Martelo_Orcamentos_V2.ui.main_window import MainWindow



# Para correr a aplicação em modo desenvolvimento (com recarregamento automático):



# para testar ->                                        python -m Martelo_Orcamentos_V2.run_dev                  


#(.venv_Martelo) PS C:\Users\Utilizador\Documents\Martelo_Orcamentos_V2> python -m Martelo_Orcamentos_V2.run_dev



# Ativar o ambiente virtual powershell  ->          .\.venv_Martelo\Scripts\Activate.ps1

'''
git pull origin main  # Atualizar o repositório local
# Fazer as alterações necessárias no código

git add .
git commit -m "354"
git push origin main

'''

## Credenciais iniciais para o admin (se não existir, criar com script seed_admin.py): ->     python -m Martelo_Orcamentos_V2.scripts.seed_admin --username admin --password admin123 --role admin

# user : admin
# pass : admin123


def main():
    app = QtWidgets.QApplication(sys.argv)
    init_db()
    login = LoginDialog()
    if login.exec() == QtWidgets.QDialog.Accepted:
        mw = MainWindow(current_user=login.current_user)
        mw.showMaximized()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()

