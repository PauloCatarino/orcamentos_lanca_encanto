"""
PHC (SQL Server) - acesso READ-ONLY via SELECT.

Nota:
 - Este módulo NUNCA deve escrever no PHC (apenas SELECT).
 - A execução é feita via PowerShell + System.Data.SqlClient para evitar dependências
   nativas (ex.: pyodbc) em Python 3.13.
"""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, TypedDict

from sqlalchemy.orm import Session

from Martelo_Orcamentos_V2.app.config import settings
from Martelo_Orcamentos_V2.app.services.settings import get_setting


# --- Settings keys (armazenados na tabela app_settings) ---
KEY_PHC_SERVER = "phc_sql_server"
KEY_PHC_DATABASE = "phc_sql_database"
KEY_PHC_USER = "phc_sql_user"
KEY_PHC_PASSWORD = "phc_sql_password"
KEY_PHC_TRUSTED = "phc_sql_trusted"
KEY_PHC_TRUST_CERT = "phc_sql_trust_server_certificate"


# --- Defaults ---
DEFAULT_PHC_SERVER = r"Server_le\phc"
DEFAULT_PHC_DATABASE = "lancaencanto"
DEFAULT_PHC_USER = "adriano.silva"
DEFAULT_PHC_TRUSTED = False
DEFAULT_PHC_TRUST_CERT = True


class PHCConfig(TypedDict):
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


def load_phc_config(db: Session) -> PHCConfig:
    server = (get_setting(db, KEY_PHC_SERVER, "") or "").strip()
    if not server:
        server = (settings.PHC_SQL_SERVER or "").strip() or DEFAULT_PHC_SERVER

    database = (get_setting(db, KEY_PHC_DATABASE, "") or "").strip()
    if not database:
        database = (settings.PHC_SQL_DATABASE or "").strip() or DEFAULT_PHC_DATABASE

    user = (get_setting(db, KEY_PHC_USER, "") or "").strip()
    if not user:
        user = (settings.PHC_SQL_USER or "").strip() or DEFAULT_PHC_USER

    trusted_raw = (get_setting(db, KEY_PHC_TRUSTED, "") or "").strip()
    if trusted_raw:
        trusted = _parse_bool(trusted_raw, default=DEFAULT_PHC_TRUSTED)
    else:
        trusted = bool(settings.PHC_SQL_TRUSTED) if settings.PHC_SQL_TRUSTED is not None else DEFAULT_PHC_TRUSTED

    trust_cert_raw = (get_setting(db, KEY_PHC_TRUST_CERT, "") or "").strip()
    if trust_cert_raw:
        trust_cert = _parse_bool(trust_cert_raw, default=DEFAULT_PHC_TRUST_CERT)
    else:
        trust_cert = (
            bool(settings.PHC_SQL_TRUST_SERVER_CERTIFICATE)
            if settings.PHC_SQL_TRUST_SERVER_CERTIFICATE is not None
            else DEFAULT_PHC_TRUST_CERT
        )

    password = get_setting(db, KEY_PHC_PASSWORD, "") or ""
    if not str(password).strip():
        password = (settings.PHC_SQL_PASSWORD or "").strip()

    return {
        "server": server,
        "database": database,
        "trusted": bool(trusted),
        "trust_server_certificate": bool(trust_cert),
        "user": user,
        "password": str(password),
    }


def build_connection_string(cfg: PHCConfig) -> str:
    server = (cfg.get("server") or "").strip()
    database = (cfg.get("database") or "").strip()
    user = (cfg.get("user") or "").strip()
    password = cfg.get("password") or ""
    trusted = bool(cfg.get("trusted"))
    trust_cert = bool(cfg.get("trust_server_certificate"))

    if not server or not database:
        raise ValueError("Configuração PHC incompleta: Servidor e Base de Dados são obrigatórios.")

    parts = [f"Server={server}", f"Database={database}"]
    if trusted:
        parts.append("Integrated Security=True")
    else:
        if not user:
            raise ValueError("Configuração PHC incompleta: Utilizador em falta (ou ative Trusted_Connection).")
        if not str(password).strip():
            raise ValueError("Configuração PHC incompleta: Password em falta.")
        parts.append(f"User ID={user}")
        parts.append(f"Password={password}")
    if trust_cert:
        parts.append("TrustServerCertificate=True")
    return ";".join(parts) + ";"


def assert_select_only(query: str) -> None:
    q = (query or "").strip()
    if not q.upper().startswith("SELECT"):
        raise RuntimeError("Query inválida: apenas SELECT é permitido.")

    q_no_trailing = q.rstrip(";").strip()
    if ";" in q_no_trailing:
        raise RuntimeError("Query inválida: múltiplos statements não são permitidos.")

    banned = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "MERGE", "EXEC", "CREATE")
    for token in banned:
        if re.search(rf"\\b{re.escape(token)}\\b", q_no_trailing, flags=re.IGNORECASE):
            raise RuntimeError("Query inválida: apenas SELECT é permitido.")


def run_select(conn_str: str, query: str) -> List[Dict[str, Any]]:
    assert_select_only(query)
    payload = {"conn": conn_str, "query": query}
    payload_b64 = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("ascii")

    ps_script = r"""
param(
  [Parameter(Mandatory=$true)][string]$PayloadB64
)
$ErrorActionPreference = 'Stop'

$payloadJson = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($PayloadB64))
$p = $payloadJson | ConvertFrom-Json
$connStr = [string]$p.conn
$query = [string]$p.query

if (-not $query.TrimStart().ToUpper().StartsWith('SELECT')) {
  throw 'Query inválida: apenas SELECT é permitido.'
}
$q2 = $query.Trim()
$q2 = $q2.TrimEnd(';').Trim()
if ($q2.Contains(';')) { throw 'Query inválida: múltiplos statements não são permitidos.' }
$banned = @('INSERT','UPDATE','DELETE','DROP','ALTER','TRUNCATE','MERGE','EXEC','CREATE')
foreach ($t in $banned) {
  if ([regex]::IsMatch($q2, ('\b' + [regex]::Escape($t) + '\b'), [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
    throw 'Query inválida: apenas SELECT é permitido.'
  }
}

Add-Type -AssemblyName System.Data
$conn = New-Object System.Data.SqlClient.SqlConnection $connStr
$conn.Open()
try {
  $cmd = $conn.CreateCommand()
  $cmd.CommandText = $query
  $cmd.CommandTimeout = 30

  $dt = New-Object System.Data.DataTable
  $da = New-Object System.Data.SqlClient.SqlDataAdapter $cmd
  [void]$da.Fill($dt)

  $rows = @()
  foreach ($r in $dt.Rows) {
    $obj = [ordered]@{}
    foreach ($c in $dt.Columns) {
      $val = $r[$c.ColumnName]
      if ($val -is [System.DBNull]) { $val = $null }
      $obj[$c.ColumnName] = $val
    }
    $rows += [pscustomobject]$obj
  }
  $json = ConvertTo-Json -InputObject $rows -Depth 6 -Compress
  [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
} finally {
  $conn.Close()
}
"""

    temp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".ps1", delete=False) as tf:
            tf.write(ps_script)
            temp_path = tf.name

        cmd = [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            temp_path,
            payload_b64,
        ]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
            creationflags=creationflags,
        )
        if result.returncode != 0:
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            detail = "\n".join([s for s in (stderr, stdout) if s])
            raise RuntimeError(detail or f"Código de saída: {result.returncode}")

        raw_b64 = (result.stdout or "").strip()
        if not raw_b64:
            return []

        decoded = base64.b64decode(raw_b64).decode("utf-8", errors="replace")
        data = json.loads(decoded)
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return data
        return []
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except Exception:
                pass


def query_phc_clients(db: Session) -> List[Dict[str, Any]]:
    """
    Consulta (read-only) à tabela dbo.CL no PHC.

    Returns: lista de dicts com as colunas:
      Nome, Simplex, Morada, Email, WEB, Telemovel, Telefone, Num_PHC, Info_1
    """
    query = """
SELECT
    NOME AS Nome,
    NOME2 AS Simplex,
    MORADA AS Morada,
    EMAIL AS Email,
    URL AS WEB,
    TLMVL AS Telemovel,
    TELEFONE AS Telefone,
    NO AS Num_PHC,
    OBS AS Info_1
FROM dbo.CL WITH (NOLOCK)
ORDER BY NOME;
""".strip()

    cfg = load_phc_config(db)
    conn_str = build_connection_string(cfg)
    return run_select(conn_str, query)


def query_phc_encomenda_itens(
    db: Session,
    *,
    num_enc_phc: str | int,
    ano: str | int | None = None,
) -> List[Dict[str, Any]]:
    """
    Consulta (read-only) à tabela de Encomendas no PHC via BI/BO/BO2/CL.

    Filtra por número de encomenda PHC (BI.OBRANO).
    """
    enc_digits = re.sub(r"\D", "", str(num_enc_phc or ""))
    if not enc_digits:
        raise ValueError("Num_Enc_PHC inválido.")
    enc_int = int(enc_digits)

    year_filter = ""
    if ano is not None and str(ano).strip():
        try:
            ano_int = int(re.sub(r"\\D", "", str(ano)))
        except Exception as exc:
            raise ValueError("Ano inválido.") from exc
        if ano_int < 1900 or ano_int > 2200:
            raise ValueError("Ano inválido.")
        start = f"{ano_int:04d}-01-01"
        end = f"{ano_int + 1:04d}-01-01"
        year_filter = f"  AND BI.DATAOBRA >= '{start}' AND BI.DATAOBRA < '{end}'\n"

    query = f"""
SELECT
    YEAR(BI.DATAOBRA) AS Ano,
    BI.NOME AS Cliente,
    CL.NOME2 AS Cliente_Abreviado,
    BI.OBRANO AS Enc_No,
    CL.NO AS Num_PHC,
    BO.U_ORCC AS Ref_Cliente,
    BI.DESIGN AS Descricao_Artigo,
    CONVERT(VARCHAR(10), BI.DATAOBRA, 104) AS Data_Encomenda,
    CONVERT(VARCHAR(10), BO.U_ENTREGA, 104) AS Data_Entrega
FROM BI WITH (NOLOCK)
INNER JOIN BO  WITH (NOLOCK) ON BO.BOSTAMP  = BI.BOSTAMP
INNER JOIN BO2 WITH (NOLOCK) ON BO.BOSTAMP  = BO2.BO2STAMP
LEFT JOIN  CL  WITH (NOLOCK) ON CL.NOME     = BI.NOME
WHERE BI.NDOS = 1
  AND BO2.ANULADO = 0
  AND BI.OBRANO = {enc_int}
{year_filter.rstrip()}
ORDER BY BI.LORDEM ASC;
""".strip()

    cfg = load_phc_config(db)
    conn_str = build_connection_string(cfg)
    return run_select(conn_str, query)
