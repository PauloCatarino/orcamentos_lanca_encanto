#from app.db import init_db
from Martelo_Orcamentos_V2.app.db import init_db


def main():
    init_db()
    print("Tabelas criadas/atualizadas com sucesso (ORM).")


if __name__ == "__main__":
    main()

