import argparse
from app.db import SessionLocal, init_db
from app.models import User
from app.security import hash_password


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--role", default="admin")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == args.username).first()
        if u:
            print("Utilizador já existe; a atualizar palavra‑passe e role…")
            u.pass_hash = hash_password(args.password)
            u.role = args.role
        else:
            u = User(username=args.username, pass_hash=hash_password(args.password), role=args.role)
            db.add(u)
        db.commit()
        print("Utilizador admin semeado/atualizado com sucesso.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

