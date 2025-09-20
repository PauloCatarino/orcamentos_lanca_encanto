# run_dev.py

import sys
from PySide6 import QtWidgets
from Martelo_Orcamentos_V2.app.db import SessionLocal, init_db
from Martelo_Orcamentos_V2.ui.login import LoginDialog
from Martelo_Orcamentos_V2.ui.main_window import MainWindow



# para testar ->                 python -m Martelo_Orcamentos_V2.run_dev

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

