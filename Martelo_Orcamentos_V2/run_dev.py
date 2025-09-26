# run_dev.py

import sys
from PySide6 import QtWidgets
from Martelo_Orcamentos_V2.app.db import SessionLocal, init_db
from Martelo_Orcamentos_V2.ui.login import LoginDialog
from Martelo_Orcamentos_V2.ui.main_window import MainWindow



# para testar ->                                     python -m Martelo_Orcamentos_V2.run_dev

#(.venv) PS C:\Users\Utilizador\Documents\ORCAMENTOS_LE\ORCAMENTOS_LE\orcamentos_lanca_encanto>python -m Martelo_Orcamentos_V2.run_dev → Usar como módulo, mas tens de estar na pasta acima.



# Ativar o ambiente virtual powershell  ->          .\.venv\Scripts\Activate.ps1

'''
git add .
git commit -m "293 Commit"
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
        mw.show()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()

