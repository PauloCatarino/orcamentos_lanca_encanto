"""
STREAMLIT (SQL Server) - acesso READ-ONLY via SELECT.

Nota:
 - Este modulo NUNCA deve escrever na BD (apenas SELECT).
 - A execucao e feita via PowerShell + System.Data.SqlClient (reutiliza phc_sql.run_select).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, TypedDict

from sqlalchemy.orm import Session

from Martelo_Orcamentos_V2.app.config import settings
from Martelo_Orcamentos_V2.app.services.settings import get_setting
from Martelo_Orcamentos_V2.app.services import phc_sql as _sql


# --- Settings keys (armazenados na tabela app_settings) ---
KEY_STREAMLIT_SERVER = "streamlit_sql_server"
KEY_STREAMLIT_DATABASE = "streamlit_sql_database"
KEY_STREAMLIT_USER = "streamlit_sql_user"
KEY_STREAMLIT_PASSWORD = "streamlit_sql_password"
KEY_STREAMLIT_TRUSTED = "streamlit_sql_trusted"
KEY_STREAMLIT_TRUST_CERT = "streamlit_sql_trust_server_certificate"


# --- Defaults (sem password hardcoded) ---
DEFAULT_STREAMLIT_SERVER = r"DESKTOP-PTJ4TE6,1433"
DEFAULT_STREAMLIT_DATABASE = "Lanca_Encanto2026"
DEFAULT_STREAMLIT_USER = "Lanca_Encanto_Stream"
DEFAULT_STREAMLIT_TRUSTED = False
DEFAULT_STREAMLIT_TRUST_CERT = True


class StreamlitConfig(TypedDict):
    server: str
    database: str
    trusted: bool
    trust_server_certificate: bool
    user: str
    password: str


def _parse_bool(raw: Any, *, default: bool = False) -> bool:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    s = str(raw).strip()
    if not s:
        return default
    return s.lower() in {"1", "true", "yes", "y", "sim", "on"}


def load_streamlit_config(db: Session) -> StreamlitConfig:
    server = (get_setting(db, KEY_STREAMLIT_SERVER, "") or "").strip()
    if not server:
        server = (settings.STREAMLIT_SQL_SERVER or "").strip() or DEFAULT_STREAMLIT_SERVER

    database = (get_setting(db, KEY_STREAMLIT_DATABASE, "") or "").strip()
    if not database:
        database = (settings.STREAMLIT_SQL_DATABASE or "").strip() or DEFAULT_STREAMLIT_DATABASE

    user = (get_setting(db, KEY_STREAMLIT_USER, "") or "").strip()
    if not user:
        user = (settings.STREAMLIT_SQL_USER or "").strip() or DEFAULT_STREAMLIT_USER

    trusted_raw = (get_setting(db, KEY_STREAMLIT_TRUSTED, "") or "").strip()
    if trusted_raw:
        trusted = _parse_bool(trusted_raw, default=DEFAULT_STREAMLIT_TRUSTED)
    else:
        trusted = (
            bool(settings.STREAMLIT_SQL_TRUSTED)
            if settings.STREAMLIT_SQL_TRUSTED is not None
            else DEFAULT_STREAMLIT_TRUSTED
        )

    trust_cert_raw = (get_setting(db, KEY_STREAMLIT_TRUST_CERT, "") or "").strip()
    if trust_cert_raw:
        trust_cert = _parse_bool(trust_cert_raw, default=DEFAULT_STREAMLIT_TRUST_CERT)
    else:
        trust_cert = (
            bool(settings.STREAMLIT_SQL_TRUST_SERVER_CERTIFICATE)
            if settings.STREAMLIT_SQL_TRUST_SERVER_CERTIFICATE is not None
            else DEFAULT_STREAMLIT_TRUST_CERT
        )

    password = get_setting(db, KEY_STREAMLIT_PASSWORD, "") or ""
    if not str(password).strip():
        password = (settings.STREAMLIT_SQL_PASSWORD or "").strip()

    return {
        "server": server,
        "database": database,
        "trusted": bool(trusted),
        "trust_server_certificate": bool(trust_cert),
        "user": user,
        "password": str(password),
    }


def build_connection_string(cfg: StreamlitConfig) -> str:
    server = (cfg.get("server") or "").strip()
    database = (cfg.get("database") or "").strip()
    user = (cfg.get("user") or "").strip()
    password = cfg.get("password") or ""
    trusted = bool(cfg.get("trusted"))
    trust_cert = bool(cfg.get("trust_server_certificate"))

    if not server or not database:
        raise ValueError("Configuracao Streamlit incompleta: Servidor e Base de Dados sao obrigatorios.")

    parts = [f"Server={server}", f"Database={database}", "Encrypt=False", "Connection Timeout=60"]
    if trusted:
        parts.append("Integrated Security=True")
    else:
        if not user:
            raise ValueError("Configuracao Streamlit incompleta: Utilizador em falta (ou ative Trusted_Connection).")
        if not str(password).strip():
            raise ValueError("Configuracao Streamlit incompleta: Password em falta.")
        parts.append(f"User ID={user}")
        parts.append(f"Password={password}")
    if trust_cert:
        parts.append("TrustServerCertificate=True")
    return ";".join(parts) + ";"


_CLIENTE_ABREVIADO_COL: Optional[str] = None


def _detect_cliente_abreviado_col(conn_str: str) -> Optional[str]:
    global _CLIENTE_ABREVIADO_COL
    if _CLIENTE_ABREVIADO_COL is not None:
        return _CLIENTE_ABREVIADO_COL or None

    candidates = ("Cliente_Abreviado", "ClienteAbreviado", "Abreviado", "Simplex", "ClienteSimplex")
    in_list = ", ".join([f"'{c}'" for c in candidates])
    query = f"""
SELECT COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'dbo'
  AND TABLE_NAME = 'Encomendas'
  AND COLUMN_NAME IN ({in_list})
""".strip()

    try:
        rows = _sql.run_select(conn_str, query)
    except Exception:
        _CLIENTE_ABREVIADO_COL = ""
        return None

    found = {str(r.get("COLUMN_NAME") or "") for r in (rows or [])}
    for c in candidates:
        if c in found:
            _CLIENTE_ABREVIADO_COL = c
            return c

    _CLIENTE_ABREVIADO_COL = ""
    return None


def query_streamlit_encomenda_itens(
    db: Session,
    *,
    num_enc_final: str | int,
    ano: str | int | None = None,
) -> List[Dict[str, Any]]:
    """
    Consulta (read-only) as tabelas dbo.Encomendas e dbo.ItensEncomenda (Streamlit),
    filtrando por Ano + Numero (Num_Enc_(F)).

    Devolve linhas (uma por item) com:
      Ano, Cliente, Cliente_Abreviado, Numero, RefCliente, Designacao, DataEntrega, DataRecepcao
    """
    raw = str(num_enc_final or "").strip()
    numero: str
    if re.fullmatch(r"_(\d{1,3})", raw):
        numero = "_" + raw[1:].zfill(3)
    else:
        digits = re.sub(r"\D", "", raw)
        if not digits:
            raise ValueError("Num_Enc_(F) invalido (indique digitos).")
        if len(digits) > 3:
            raise ValueError("Num_Enc_(F) invalido (deve ter 3 algarismos, ex.: 001).")
        numero = "_" + digits.zfill(3)

    ano_int: Optional[int] = None
    if ano is not None and str(ano).strip():
        try:
            ano_int = int(re.sub(r"\D", "", str(ano)))
        except Exception as exc:
            raise ValueError("Ano invalido.") from exc
        if ano_int < 1900 or ano_int > 2200:
            raise ValueError("Ano invalido.")

    cfg = load_streamlit_config(db)
    conn_str = build_connection_string(cfg)

    col_abrev = _detect_cliente_abreviado_col(conn_str)
    cliente_abreviado_expr = f"NULLIF(LTRIM(RTRIM(E.[{col_abrev}])), '')" if col_abrev else "''"

    year_filter = f" AND E.Ano = {int(ano_int)}" if ano_int is not None else ""

    query = f"""
SELECT
    E.Ano AS Ano,
    E.Cliente AS Cliente,
    {cliente_abreviado_expr} AS Cliente_Abreviado,
    E.Numero AS Numero,
    E.RefCliente AS RefCliente,
    I.Designacao AS Designacao,
    CONVERT(VARCHAR(10), E.DataEntrega, 104) AS DataEntrega,
    CONVERT(VARCHAR(10), E.DataRecepcao, 104) AS DataRecepcao
FROM dbo.Encomendas E WITH (NOLOCK)
LEFT JOIN dbo.ItensEncomenda I WITH (NOLOCK) ON I.EncomendaId = E.Id
 WHERE E.Numero = '{numero}'
{year_filter}
ORDER BY E.Id DESC, I.Id ASC;
""".strip()

    return _sql.run_select(conn_str, query)
