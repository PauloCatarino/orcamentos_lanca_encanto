Martelo Orçamentos V2
=====================

Nova base do software de orçamentos, pensada para multiutilizador, robustez (FKs reais) e UI moderna.

Estrutura
- `app/` código de domínio/infra/serviços (SQLAlchemy + Pydantic Settings)
- `ui/` aplicação PySide6 (login + janela principal)
- `scripts/` SQL inicial e utilitários (seed admin)

Requisitos
- Python 3.12+
- MySQL 8.x (ou compatível)

Setup rápido (ambiente de dev)
1) Criar e ativar venv
   - Windows: `python -m venv .venv && .venv\\Scripts\\activate`
2) Instalar deps: `pip install -r requirements.txt`
3) Configurar `.env` (copiar de `.env.example` e ajustar `DB_URI`)
4) Criar BD (opção A: Workbench) ou executar o SQL:
   - `mysql -u <user> -p <host> < scripts/001_init_schema.sql`
5) Semear utilizador admin:
   - `python scripts/seed_admin.py --username admin --password admin123 --role admin`
6) Executar: `python run_dev.py`

Notas de arquitetura
- ORM SQLAlchemy 2.0; FKs diretas `id_item_fk` nas tabelas filhas (ON DELETE CASCADE)
- Settings via Pydantic (`app/config.py`), `.env` na raiz
- UI PySide6 com login (QDialog) e janela principal (placeholders)
- Relatórios/integrações serão adicionados em módulos dedicados

Segurança
- Palavras‑passe com `bcrypt` (passlib)
- `.env` não deve ir para VCS (use `.env.example` como base)

Próximos passos
- Preencher casos de uso (services) e listas de orçamentos/itens
- Adicionar migrações Alembic (posterior)

