import argparse
from passlib.hash import bcrypt
from Martelo_Orcamentos_V2.app.db import SessionLocal, init_db
from Martelo_Orcamentos_V2.app.models.user import User


def seed_admin(username: str, password: str, role: str):
    """Cria o utilizador admin inicial, se não existir."""
    init_db()  # garante que as tabelas estão criadas
    db = SessionLocal()
    try:
        # Verifica se já existe um utilizador com este username
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"⚠️ Utilizador '{username}' já existe.")
            return

        # Gera hash seguro da password
        password_hash = bcrypt.hash(password)

        # Cria novo utilizador
        admin_user = User(
            username=username,
            pass_hash=password_hash,  # campo corresponde ao ORM
            role=role,
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        print(f"✅ Utilizador '{username}' criado com sucesso!")
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Seed inicial para criar o utilizador admin")
    parser.add_argument("--username", required=True, help="Nome de utilizador")
    parser.add_argument("--password", required=True, help="Password")
    parser.add_argument("--role", default="admin", help="Role do utilizador (default=admin)")

    args = parser.parse_args()
    seed_admin(args.username, args.password, args.role)


if __name__ == "__main__":
    main()
