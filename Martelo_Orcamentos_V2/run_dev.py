import sys
from PySide6 import QtWidgets
from app.db import init_db
from ui.login import LoginDialog
from ui.main_window import MainWindow


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

