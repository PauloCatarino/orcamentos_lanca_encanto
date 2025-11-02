# run_dev.py


import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("Martelo_Orcamentos_V2.app.services.dados_items").setLevel(logging.WARNING)
logging.getLogger("Martelo_Orcamentos_V2.app.services.dados_gerais").setLevel(logging.INFO)
logging.getLogger("passlib.handlers.bcrypt").setLevel(logging.ERROR)
logging.basicConfig(level=logging.DEBUG)

import sys
from PySide6 import QtWidgets
from Martelo_Orcamentos_V2.app.db import SessionLocal, init_db
from Martelo_Orcamentos_V2.ui.login import LoginDialog
from Martelo_Orcamentos_V2.ui.main_window import MainWindow



# Para correr a aplicação em modo desenvolvimento (com recarregamento automático):





# para testar ->                                                        


#(.venv_Martelo) PS C:\Users\Utilizador\Documents\Martelo_Orcamentos_V2> python -m Martelo_Orcamentos_V2.run_dev



# Ativar o ambiente virtual powershell  ->          .\.venv_Martelo\Scripts\Activate.ps1

'''
git pull origin main  # Atualizar o repositório local
# Fazer as alterações necessárias no código

git add .
git commit -m "385"
git push origin main

'''

## Credenciais iniciais para o admin (se não existir, criar com script seed_admin.py): ->     python -m Martelo_Orcamentos_V2.scripts.seed_admin --username admin --password admin123 --role admin

# user : admin
# pass : admin123


def main():
    app = QtWidgets.QApplication(sys.argv)
    init_db()
    # Auto-login para agilizar os testes; remover quando deixar de ser necessário.
    login = LoginDialog(auto_user="admin", auto_password="admin123", auto_submit=True)
    if login.exec() == QtWidgets.QDialog.Accepted:
        mw = MainWindow(current_user=login.current_user)
        mw.showMaximized()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()

