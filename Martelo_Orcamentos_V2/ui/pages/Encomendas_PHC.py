"""
Encomendas PHC

Este ecrã permite consultar encomendas do PHC e do Cliente Final (apenas leitura).
IMPORTANTE:
 - Apenas consultas SELECT (nunca escrever nas bases de dados externas).
"""

from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path
import subprocess
import tempfile
import re
from typing import Any, Dict, List, Optional

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt

from Martelo_Orcamentos_V2.app.db import SessionLocal
from Martelo_Orcamentos_V2.app.services.settings import get_setting, set_setting
from Martelo_Orcamentos_V2.ui.models.qt_table import SimpleTableModel

logger = logging.getLogger(__name__)

try:
    from dotenv import dotenv_values  # type: ignore
except Exception:  # pragma: no cover
    dotenv_values = None


# --- Settings keys (PHC / SQL Server) ---
KEY_PHC_SERVER = "phc_sql_server"
KEY_PHC_DATABASE = "phc_sql_database"
KEY_PHC_USER = "phc_sql_user"
KEY_PHC_PASSWORD = "phc_sql_password"
KEY_PHC_TRUSTED = "phc_sql_trusted"
KEY_PHC_TRUST_CERT = "phc_sql_trust_server_certificate"

# Defaults (sem password hardcoded; pode vir de settings/.env)
DEFAULT_PHC_SERVER = r"Server_le\phc"
DEFAULT_PHC_DATABASE = "lancaencanto"
DEFAULT_PHC_USER = "adriano.silva"
DEFAULT_PHC_TRUSTED = False
DEFAULT_PHC_TRUST_CERT = True

# Variáveis de ambiente opcionais (ex.: em `.env`)
ENV_PHC_SERVER = "PHC_SQL_SERVER"
ENV_PHC_DATABASE = "PHC_SQL_DATABASE"
ENV_PHC_USER = "PHC_SQL_USER"
ENV_PHC_PASSWORD = "PHC_SQL_PASSWORD"
ENV_PHC_TRUSTED = "PHC_SQL_TRUSTED"
ENV_PHC_TRUST_CERT = "PHC_SQL_TRUST_SERVER_CERTIFICATE"

# --- Settings keys (Cliente Final / Streamlit SQL Server) ---
KEY_ST_SERVER = "streamlit_sql_server"
KEY_ST_DATABASE = "streamlit_sql_database"
KEY_ST_USER = "streamlit_sql_user"
KEY_ST_PASSWORD = "streamlit_sql_password"
KEY_ST_TRUSTED = "streamlit_sql_trusted"
KEY_ST_TRUST_CERT = "streamlit_sql_trust_server_certificate"

# Defaults (sem password hardcoded; pode vir de settings/.env)
DEFAULT_ST_SERVER = r"DESKTOP-9TG3VTH,1433"
DEFAULT_ST_DATABASE = "Lanca_Encanto2026"
DEFAULT_ST_USER = "Streamlit"
DEFAULT_ST_TRUSTED = False
DEFAULT_ST_TRUST_CERT = True

# Variaveis de ambiente opcionais (ex.: em `.env`)
ENV_ST_SERVER = "STREAMLIT_SQL_SERVER"
ENV_ST_DATABASE = "STREAMLIT_SQL_DATABASE"
ENV_ST_USER = "STREAMLIT_SQL_USER"
ENV_ST_PASSWORD = "STREAMLIT_SQL_PASSWORD"
ENV_ST_TRUSTED = "STREAMLIT_SQL_TRUSTED"
ENV_ST_TRUST_CERT = "STREAMLIT_SQL_TRUST_SERVER_CERTIFICATE"


def _read_dotenv() -> Dict[str, str]:
    if dotenv_values is None:
        return {}

    candidates: List[Path] = []
    try:
        candidates.append(Path.cwd() / ".env")
    except Exception:
        pass

    try:
        here = Path(__file__).resolve()
        for parent in here.parents:
            candidates.append(parent / ".env")
    except Exception:
        pass

    seen: set[str] = set()
    for path in candidates:
        p = str(path)
        if p in seen:
            continue
        seen.add(p)
        try:
            if not path.is_file():
                continue
            raw = dotenv_values(p) or {}
        except Exception:
            continue

        out: Dict[str, str] = {}
        for k, v in raw.items():
            if k and v is not None:
                out[str(k)] = str(v)
        if out:
            return out

    return {}


_DOTENV_CACHE: Optional[Dict[str, str]] = None


def _env_get(key: str) -> str:
    global _DOTENV_CACHE
    value = os.environ.get(key)
    if value is not None and str(value).strip() != "":
        return str(value)
    if _DOTENV_CACHE is None:
        _DOTENV_CACHE = _read_dotenv()
    return str(_DOTENV_CACHE.get(key, "") or "")


class EncomendasPHCTab(QtWidgets.QWidget):
    """
    Consulta de encomendas no PHC (BI/BO/BO2/CL), apenas leitura.
    """

    def __init__(self, current_user=None, parent=None) -> None:
        super().__init__(parent)
        self.current_user = current_user
        self.db = SessionLocal()

        self._build_ui()
        self._load_saved_settings()

    # ---------------- UI ----------------
    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        info = QtWidgets.QLabel(
            "Encomendas PHC - consulta apenas de leitura.\n"
            "IMPORTANTE: aqui só existem queries do tipo SELECT."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        grp = QtWidgets.QGroupBox("Ligação PHC (SQL Server)")
        g = QtWidgets.QGridLayout(grp)
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(6)

        self.ed_server = QtWidgets.QLineEdit()
        self.ed_server.setPlaceholderText(rf"Ex.: {DEFAULT_PHC_SERVER} ou 192.168.x.x")
        self.ed_database = QtWidgets.QLineEdit()
        self.ed_database.setPlaceholderText(f"Ex.: {DEFAULT_PHC_DATABASE}")

        self.chk_trusted = QtWidgets.QCheckBox("Autenticação Windows (Trusted_Connection)")
        self.chk_trust_cert = QtWidgets.QCheckBox("TrustServerCertificate=yes (recomendado em redes internas)")

        self.ed_user = QtWidgets.QLineEdit()
        self.ed_user.setPlaceholderText("Utilizador SQL (se não for Trusted)")
        self.ed_password = QtWidgets.QLineEdit()
        self.ed_password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.ed_password.setPlaceholderText("Password SQL (se não for Trusted)")

        self.btn_save = QtWidgets.QPushButton("Guardar Configuração")
        self.btn_save.setToolTip("Guardar configuração PHC. Atalho: Ctrl+G.")
        self.btn_test = QtWidgets.QPushButton("Testar Ligação")
        self.btn_load = QtWidgets.QPushButton("Carregar Encomendas (PHC)")
        self.btn_test.clicked.connect(self.on_test_connection)
        self.btn_load.clicked.connect(self.on_load_encomendas)
        self.btn_save.clicked.connect(self.on_save_settings)
        self._shortcut_save = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+G"), self)
        self._shortcut_save.setContext(Qt.WidgetWithChildrenShortcut)
        self._shortcut_save.activated.connect(self.on_save_settings)
        self._shortcut_save = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+G"), self)
        self._shortcut_save.setContext(Qt.WidgetWithChildrenShortcut)
        self._shortcut_save.activated.connect(self.on_save_settings)

        self.lbl_status = QtWidgets.QLabel("")
        self.lbl_status.setWordWrap(True)

        row = 0
        g.addWidget(QtWidgets.QLabel("Servidor:"), row, 0)
        g.addWidget(self.ed_server, row, 1)
        g.addWidget(QtWidgets.QLabel("Base de Dados:"), row, 2)
        g.addWidget(self.ed_database, row, 3)
        row += 1
        g.addWidget(self.chk_trusted, row, 1, 1, 2)
        g.addWidget(self.chk_trust_cert, row, 3)
        row += 1
        g.addWidget(QtWidgets.QLabel("Utilizador:"), row, 0)
        g.addWidget(self.ed_user, row, 1)
        g.addWidget(QtWidgets.QLabel("Password:"), row, 2)
        g.addWidget(self.ed_password, row, 3)
        row += 1

        self.sp_min_year = QtWidgets.QSpinBox()
        self.sp_min_year.setRange(2000, 2100)
        self.sp_min_year.setValue(2026)
        self.sp_min_year.setToolTip("Filtra a Data Encomenda (BI.DATAOBRA) a partir deste ano.")

        self.sp_max_rows = QtWidgets.QSpinBox()
        self.sp_max_rows.setRange(0, 200000)
        self.sp_max_rows.setSingleStep(1000)
        self.sp_max_rows.setValue(5000)
        self.sp_max_rows.setToolTip("Máximo de linhas a carregar (0 = sem limite).")

        g.addWidget(QtWidgets.QLabel("Ano mínimo:"), row, 0)
        g.addWidget(self.sp_min_year, row, 1)
        g.addWidget(QtWidgets.QLabel("Máx. linhas:"), row, 2)
        g.addWidget(self.sp_max_rows, row, 3)
        row += 1

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addWidget(self.btn_save)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_test)
        btn_row.addWidget(self.btn_load)
        g.addLayout(btn_row, row, 0, 1, 4)
        row += 1
        g.addWidget(self.lbl_status, row, 0, 1, 4)

        layout.addWidget(grp)

        # Search + table
        search_row = QtWidgets.QHBoxLayout()
        self.ed_search = QtWidgets.QLineEdit()
        self.ed_search.setPlaceholderText("Pesquisar (filtra a tabela)…")
        self.btn_clear = QtWidgets.QToolButton()
        self.btn_clear.setText("X")
        self.btn_clear.clicked.connect(lambda: self.ed_search.setText(""))
        search_row.addWidget(self.ed_search, 1)
        search_row.addWidget(self.btn_clear)
        layout.addLayout(search_row)

        self.model = SimpleTableModel(
            columns=[
                ("Cliente", "Cliente"),
                ("Cliente Abreviado", "Cliente_Abre"),
                ("Enc.Nº", "Enc_No"),
                ("Num_PHC", "Num_PHC"),
                ("Ref.ª PHC", "Ref_PHC"),
                ("Telefone", "Telefone"),
                ("Ref. Cliente", "Ref_Cliente"),
                ("Descrição artigo", "Descricao_Artigo"),
                ("Data Encomenda", "Data_Encomenda"),
                ("Data Entrega", "Data_Entrega"),
            ]
        )
        self.proxy = QtCore.QSortFilterProxyModel(self)
        self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy.setFilterKeyColumn(-1)
        self.proxy.setSourceModel(self.model)

        self.table = QtWidgets.QTableView()
        self.table.setModel(self.proxy)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        header.setStretchLastSection(True)

        layout.addWidget(self.table, 1)

        self.ed_search.textChanged.connect(self._on_search_changed)

    def _on_search_changed(self, text: str) -> None:
        self.proxy.setFilterFixedString(text.strip())

    # ---------------- Settings ----------------
    def _load_saved_settings(self) -> None:
        try:
            server = (get_setting(self.db, KEY_PHC_SERVER, "") or "").strip()
            database = (get_setting(self.db, KEY_PHC_DATABASE, "") or "").strip()
            user = (get_setting(self.db, KEY_PHC_USER, "") or "").strip()
            password = get_setting(self.db, KEY_PHC_PASSWORD, "") or ""

            if not server:
                server = _env_get(ENV_PHC_SERVER).strip() or DEFAULT_PHC_SERVER
            if not database:
                database = _env_get(ENV_PHC_DATABASE).strip() or DEFAULT_PHC_DATABASE
            if not user:
                user = _env_get(ENV_PHC_USER).strip() or DEFAULT_PHC_USER
            if not password:
                password = _env_get(ENV_PHC_PASSWORD) or ""

            self.ed_server.setText(server)
            self.ed_database.setText(database)
            self.ed_user.setText(user)
            self.ed_password.setText(password)

            trusted_raw = (get_setting(self.db, KEY_PHC_TRUSTED, "") or "").strip()
            if not trusted_raw:
                trusted_raw = _env_get(ENV_PHC_TRUSTED).strip()
            if trusted_raw:
                trusted = trusted_raw in {"1", "true", "True", "sim", "on"}
            else:
                trusted = DEFAULT_PHC_TRUSTED
            self.chk_trusted.setChecked(bool(trusted))

            trust_cert_raw = (get_setting(self.db, KEY_PHC_TRUST_CERT, "") or "").strip()
            if not trust_cert_raw:
                trust_cert_raw = _env_get(ENV_PHC_TRUST_CERT).strip()
            if trust_cert_raw:
                trust_cert = trust_cert_raw in {"1", "true", "True", "sim", "on"}
            else:
                trust_cert = DEFAULT_PHC_TRUST_CERT
            self.chk_trust_cert.setChecked(bool(trust_cert))
        except Exception:
            pass

    def on_save_settings(self) -> None:
        try:
            set_setting(self.db, KEY_PHC_SERVER, self.ed_server.text().strip())
            set_setting(self.db, KEY_PHC_DATABASE, self.ed_database.text().strip())
            set_setting(self.db, KEY_PHC_USER, self.ed_user.text().strip())
            set_setting(self.db, KEY_PHC_PASSWORD, self.ed_password.text())
            set_setting(self.db, KEY_PHC_TRUSTED, "1" if self.chk_trusted.isChecked() else "0")
            set_setting(self.db, KEY_PHC_TRUST_CERT, "1" if self.chk_trust_cert.isChecked() else "0")
            self.db.commit()
            QtWidgets.QMessageBox.information(self, "OK", "Configuração PHC gravada.")
        except Exception as exc:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao gravar configuração PHC: {exc}")

    # ---------------- PHC Query ----------------
    def _build_connection_string(self) -> str:
        server = self.ed_server.text().strip()
        database = self.ed_database.text().strip()
        trusted = self.chk_trusted.isChecked()
        trust_cert = self.chk_trust_cert.isChecked()
        user = self.ed_user.text().strip()
        password = self.ed_password.text()

        if not server or not database:
            raise ValueError("Servidor e Base de Dados são obrigatórios.")

        # Connection string para .NET SqlClient (usado via PowerShell).
        parts = [f"Server={server}", f"Database={database}"]
        if trusted:
            parts.append("Integrated Security=True")
        else:
            if not user:
                raise ValueError("Utilizador em falta (ou ative Trusted_Connection).")
            parts.append(f"User ID={user}")
            parts.append(f"Password={password}")
        if trust_cert:
            parts.append("TrustServerCertificate=True")
        return ";".join(parts) + ";"

    def _query_encomendas(self) -> List[Dict[str, Any]]:
        min_year = int(getattr(self, "sp_min_year", None).value()) if hasattr(self, "sp_min_year") else 2026
        max_rows = int(getattr(self, "sp_max_rows", None).value()) if hasattr(self, "sp_max_rows") else 0
        top_clause = f"TOP ({max_rows})" if max_rows and max_rows > 0 else ""
        date_from = f"{min_year}0101"

        query = """
SELECT {top_clause}
    BI.NOME AS Cliente,
    CL.NOME2 AS Cliente_Abre,
    BI.OBRANO AS Enc_No,
    CL.NO AS Num_PHC,
    BI.REF AS Ref_PHC,
    BO2.TELEFONE AS Telefone,
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
  AND BI.DATAOBRA >= '{date_from}'
ORDER BY BI.DATAOBRA DESC, BI.OBRANO DESC, BI.LORDEM DESC;
""".format(top_clause=top_clause, date_from=date_from).strip()

        self._assert_select_only(query)

        logger.info("Encomendas PHC: a executar SELECT em BI/BO/BO2/CL (read-only).")

        conn_str = self._build_connection_string()
        return self._run_sql_select(conn_str, query)

    @staticmethod
    def _assert_select_only(query: str) -> None:
        """
        Segurança extra: garante que a query é apenas SELECT (sem múltiplas statements).
        Nota: isto não substitui permissões de SQL, mas evita acidentes.
        """

        q = (query or "").strip()
        if not q.upper().startswith("SELECT"):
            raise RuntimeError("Query inválida: apenas SELECT é permitido.")

        # Permitir ';' apenas no fim
        q_no_trailing = q.rstrip(";").strip()
        if ";" in q_no_trailing:
            raise RuntimeError("Query inválida: múltiplos statements não são permitidos.")

        banned = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "MERGE", "EXEC", "CREATE")
        for token in banned:
            if re.search(rf"\b{re.escape(token)}\b", q_no_trailing, flags=re.IGNORECASE):
                raise RuntimeError("Query inválida: apenas SELECT é permitido.")

    def _run_sql_select(self, conn_str: str, query: str) -> List[Dict[str, Any]]:
        self._assert_select_only(query)
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
  $cmd.CommandTimeout = 180

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
  # Devolve base64(utf-8(json)) para evitar problemas de encoding ao capturar stdout
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
                timeout=180,
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

    def on_test_connection(self) -> None:
        self.lbl_status.setText("")
        try:
            conn_str = self._build_connection_string()
            self._run_sql_select(conn_str, "SELECT 1 AS OK;")
            self.lbl_status.setText("Ligação OK.")
        except Exception as exc:
            logger.exception("Encomendas PHC: falha ao testar ligação: %s", exc)
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao testar ligação PHC:\n\n{exc}")

    def on_load_encomendas(self) -> None:
        self.lbl_status.setText("")
        try:
            rows = self._query_encomendas()
            self.model.set_rows(rows)
            self.lbl_status.setText(f"{len(rows)} encomendas carregadas.")
        except Exception as exc:
            logger.exception("Encomendas PHC: falha ao carregar encomendas: %s", exc)
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar encomendas do PHC:\n\n{exc}")


class EncomendasPHCPage(QtWidgets.QWidget):
    """
    Container do menu "Encomendas PHC" com separadores.
    """

    def __init__(self, current_user=None, parent=None) -> None:
        super().__init__(parent)
        self.current_user = current_user
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.tabs = QtWidgets.QTabWidget(self)
        layout.addWidget(self.tabs, 1)

        self.tab_phc = EncomendasPHCTab(current_user=self.current_user, parent=self)
        self.tabs.addTab(self.tab_phc, "Encomendas PHC")

        self.tab_cliente_final = EncomendasClienteFinalTab(parent=self)
        self.tabs.addTab(self.tab_cliente_final, "Encomendas Cliente Final")


class EncomendasClienteFinalTab(QtWidgets.QWidget):
    """
    Consulta de encomendas na BD de Cliente Final (Streamlit), apenas leitura.

    IMPORTANTE:
      - Apenas consultas SELECT (nunca escrever nesta base de dados).
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.db = SessionLocal()
        self._last_encomenda_id: Optional[int] = None

        self._build_ui()
        self._load_saved_settings()

    # ---------------- UI ----------------
    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        info = QtWidgets.QLabel(
            "Encomendas Cliente Final - consulta apenas de leitura.\n"
            "IMPORTANTE: aqui só existem queries do tipo SELECT."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        grp = QtWidgets.QGroupBox("Ligacao Cliente Final (SQL Server)")
        g = QtWidgets.QGridLayout(grp)
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(6)

        self.ed_server = QtWidgets.QLineEdit()
        self.ed_server.setPlaceholderText(rf"Ex.: {DEFAULT_ST_SERVER} ou 192.168.x.x,1433")
        self.ed_database = QtWidgets.QLineEdit()
        self.ed_database.setPlaceholderText(f"Ex.: {DEFAULT_ST_DATABASE}")

        self.chk_trusted = QtWidgets.QCheckBox("Autenticacao Windows (Trusted_Connection)")
        self.chk_trust_cert = QtWidgets.QCheckBox("TrustServerCertificate=yes (recomendado em redes internas)")

        self.ed_user = QtWidgets.QLineEdit()
        self.ed_user.setPlaceholderText("Utilizador SQL (se nao for Trusted)")
        self.ed_password = QtWidgets.QLineEdit()
        self.ed_password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.ed_password.setPlaceholderText("Password SQL (se nao for Trusted)")

        self.btn_save = QtWidgets.QPushButton("Guardar Configuracao")
        self.btn_save.setToolTip("Guardar configuração Cliente Final. Atalho: Ctrl+G.")
        self.btn_test = QtWidgets.QPushButton("Testar Ligacao")
        self.btn_load = QtWidgets.QPushButton("Carregar Encomendas (Cliente Final)")
        self.btn_test.clicked.connect(self.on_test_connection)
        self.btn_load.clicked.connect(self.on_load_encomendas)
        self.btn_save.clicked.connect(self.on_save_settings)

        self.lbl_status = QtWidgets.QLabel("")
        self.lbl_status.setWordWrap(True)

        row = 0
        g.addWidget(QtWidgets.QLabel("Servidor:"), row, 0)
        g.addWidget(self.ed_server, row, 1)
        g.addWidget(QtWidgets.QLabel("Base de Dados:"), row, 2)
        g.addWidget(self.ed_database, row, 3)
        row += 1
        g.addWidget(self.chk_trusted, row, 1, 1, 2)
        g.addWidget(self.chk_trust_cert, row, 3)
        row += 1
        g.addWidget(QtWidgets.QLabel("Utilizador:"), row, 0)
        g.addWidget(self.ed_user, row, 1)
        g.addWidget(QtWidgets.QLabel("Password:"), row, 2)
        g.addWidget(self.ed_password, row, 3)
        row += 1

        self.sp_min_year = QtWidgets.QSpinBox()
        self.sp_min_year.setRange(2000, 2100)
        self.sp_min_year.setValue(2026)
        self.sp_min_year.setToolTip("Filtra Encomendas por ano (coluna Ano).")

        self.sp_max_rows = QtWidgets.QSpinBox()
        self.sp_max_rows.setRange(0, 200000)
        self.sp_max_rows.setSingleStep(1000)
        self.sp_max_rows.setValue(5000)
        self.sp_max_rows.setToolTip("Maximo de encomendas a carregar (0 = sem limite).")

        self.sp_max_itens = QtWidgets.QSpinBox()
        self.sp_max_itens.setRange(0, 200000)
        self.sp_max_itens.setSingleStep(1000)
        self.sp_max_itens.setValue(20000)
        self.sp_max_itens.setToolTip("Maximo de itens a carregar (0 = sem limite).")

        g.addWidget(QtWidgets.QLabel("Ano minimo:"), row, 0)
        g.addWidget(self.sp_min_year, row, 1)
        g.addWidget(QtWidgets.QLabel("Max. encomendas:"), row, 2)
        g.addWidget(self.sp_max_rows, row, 3)
        row += 1
        g.addWidget(QtWidgets.QLabel("Max. itens:"), row, 2)
        g.addWidget(self.sp_max_itens, row, 3)
        row += 1

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addWidget(self.btn_save)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_test)
        btn_row.addWidget(self.btn_load)
        g.addLayout(btn_row, row, 0, 1, 4)
        row += 1
        g.addWidget(self.lbl_status, row, 0, 1, 4)

        layout.addWidget(grp)

        # Search + tables
        search_row = QtWidgets.QHBoxLayout()
        self.ed_search = QtWidgets.QLineEdit()
        self.ed_search.setPlaceholderText("Pesquisar (filtra as tabelas)")
        self.btn_clear = QtWidgets.QToolButton()
        self.btn_clear.setText("X")
        self.btn_clear.clicked.connect(lambda: self.ed_search.setText(""))
        search_row.addWidget(self.ed_search, 1)
        search_row.addWidget(self.btn_clear)
        layout.addLayout(search_row)

        self.model_enc = SimpleTableModel(
            columns=[
                ("Id", "Id"),
                ("Numero", "Numero"),
                ("Ano", "Ano"),
                ("Cliente", "Cliente"),
                ("Cliente Abreviado", "Cliente_Abre"),
                ("Contacto", "Contacto"),
                ("RefCliente", "RefCliente"),
                ("DataRecepcao", "DataRecepcao"),
                ("Responsavel", "Responsavel"),
                ("DataEntrega", "DataEntrega"),
                ("PrazoObrigatorio", "PrazoObrigatorio"),
                ("Status", "Status"),
                ("NumPaletes", "NumPaletes"),
                ("TipoPaletes", "TipoPaletes"),
                ("FormatoPalete", "FormatoPalete"),
                ("ExisteMontagem", "ExisteMontagem"),
                ("Anulada", "Anulada"),
                ("Observacoes", "Observacoes"),
            ],
            parent=self,
        )
        self.proxy_enc = QtCore.QSortFilterProxyModel(self)
        self.proxy_enc.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_enc.setFilterKeyColumn(-1)
        self.proxy_enc.setSourceModel(self.model_enc)

        self.tbl_enc = QtWidgets.QTableView(self)
        self.tbl_enc.setModel(self.proxy_enc)
        self.tbl_enc.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl_enc.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tbl_enc.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tbl_enc.setAlternatingRowColors(True)
        self.tbl_enc.setSortingEnabled(True)
        hdr = self.tbl_enc.horizontalHeader()
        hdr.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        hdr.setStretchLastSection(True)

        self.grp_itens = QtWidgets.QGroupBox("Itens Encomenda (selecione uma Encomenda)")
        self.model_itens = SimpleTableModel(
            columns=[
                ("Id", "Id"),
                ("EncomendaId", "EncomendaId"),
                ("RefObra", "RefObra"),
                ("Referencia", "Referencia"),
                ("Designacao", "Designacao"),
                ("X", "X"),
                ("Y", "Y"),
                ("Z", "Z"),
                ("Quantidade", "Quantidade"),
                ("Unidade", "Unidade"),
                ("Venda", "Venda"),
                ("ValorVenda", "ValorVenda"),
                ("UnidadeAlt", "UnidadeAlternativa"),
                ("QtdAlt", "QuantidadeAlternativa"),
            ],
            parent=self,
        )
        self.proxy_itens = QtCore.QSortFilterProxyModel(self)
        self.proxy_itens.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_itens.setFilterKeyColumn(-1)
        self.proxy_itens.setSourceModel(self.model_itens)

        self.tbl_itens = QtWidgets.QTableView(self)
        self.tbl_itens.setModel(self.proxy_itens)
        self.tbl_itens.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl_itens.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tbl_itens.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tbl_itens.setAlternatingRowColors(True)
        self.tbl_itens.setSortingEnabled(True)
        hdr2 = self.tbl_itens.horizontalHeader()
        hdr2.setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        hdr2.setStretchLastSection(True)

        enc_box = QtWidgets.QGroupBox("Encomendas")
        enc_lay = QtWidgets.QVBoxLayout(enc_box)
        enc_lay.addWidget(self.tbl_enc, 1)

        it_lay = QtWidgets.QVBoxLayout(self.grp_itens)
        it_lay.addWidget(self.tbl_itens, 1)

        splitter = QtWidgets.QSplitter(Qt.Vertical)
        splitter.addWidget(enc_box)
        splitter.addWidget(self.grp_itens)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        self.ed_search.textChanged.connect(self._on_search_changed)
        try:
            self.tbl_enc.selectionModel().selectionChanged.connect(self._on_encomenda_selection_changed)
        except Exception:
            pass

    def _on_search_changed(self, text: str) -> None:
        needle = (text or "").strip()
        self.proxy_enc.setFilterFixedString(needle)
        self.proxy_itens.setFilterFixedString(needle)

    def _clear_itens(self) -> None:
        self._last_encomenda_id = None
        self.grp_itens.setTitle("Itens Encomenda (selecione uma Encomenda)")
        self.model_itens.set_rows([])

    def _on_encomenda_selection_changed(self, *_args) -> None:
        try:
            sel = self.tbl_enc.selectionModel().selectedRows() if self.tbl_enc.selectionModel() else []
            if not sel:
                self._clear_itens()
                return

            proxy_index = sel[0]
            src_index = self.proxy_enc.mapToSource(proxy_index)
            row_obj = self.model_enc.get_row(src_index.row())
            encomenda_id = row_obj.get("Id") if isinstance(row_obj, dict) else getattr(row_obj, "Id", None)
            try:
                encomenda_id_int = int(encomenda_id)
            except Exception:
                return

            if self._last_encomenda_id == encomenda_id_int:
                return
            self._last_encomenda_id = encomenda_id_int

            self._load_itens_for_encomenda(encomenda_id_int)
        except Exception:
            self._clear_itens()

    # ---------------- Settings ----------------
    def _load_saved_settings(self) -> None:
        try:
            server = (get_setting(self.db, KEY_ST_SERVER, "") or "").strip()
            database = (get_setting(self.db, KEY_ST_DATABASE, "") or "").strip()
            user = (get_setting(self.db, KEY_ST_USER, "") or "").strip()
            password = get_setting(self.db, KEY_ST_PASSWORD, "") or ""

            if not server:
                server = _env_get(ENV_ST_SERVER).strip() or DEFAULT_ST_SERVER
            if not database:
                database = _env_get(ENV_ST_DATABASE).strip() or DEFAULT_ST_DATABASE
            if not user:
                user = _env_get(ENV_ST_USER).strip() or DEFAULT_ST_USER
            if not password:
                password = _env_get(ENV_ST_PASSWORD) or ""

            self.ed_server.setText(server)
            self.ed_database.setText(database)
            self.ed_user.setText(user)
            self.ed_password.setText(password)

            trusted_raw = (get_setting(self.db, KEY_ST_TRUSTED, "") or "").strip()
            if not trusted_raw:
                trusted_raw = _env_get(ENV_ST_TRUSTED).strip()
            if trusted_raw:
                trusted = trusted_raw in {"1", "true", "True", "sim", "on"}
            else:
                trusted = DEFAULT_ST_TRUSTED
            self.chk_trusted.setChecked(bool(trusted))

            trust_cert_raw = (get_setting(self.db, KEY_ST_TRUST_CERT, "") or "").strip()
            if not trust_cert_raw:
                trust_cert_raw = _env_get(ENV_ST_TRUST_CERT).strip()
            if trust_cert_raw:
                trust_cert = trust_cert_raw in {"1", "true", "True", "sim", "on"}
            else:
                trust_cert = DEFAULT_ST_TRUST_CERT
            self.chk_trust_cert.setChecked(bool(trust_cert))
        except Exception:
            pass

    def on_save_settings(self) -> None:
        try:
            set_setting(self.db, KEY_ST_SERVER, self.ed_server.text().strip())
            set_setting(self.db, KEY_ST_DATABASE, self.ed_database.text().strip())
            set_setting(self.db, KEY_ST_USER, self.ed_user.text().strip())
            set_setting(self.db, KEY_ST_PASSWORD, self.ed_password.text())
            set_setting(self.db, KEY_ST_TRUSTED, "1" if self.chk_trusted.isChecked() else "0")
            set_setting(self.db, KEY_ST_TRUST_CERT, "1" if self.chk_trust_cert.isChecked() else "0")
            self.db.commit()
            QtWidgets.QMessageBox.information(self, "OK", "Configuracao Cliente Final gravada.")
        except Exception as exc:
            self.db.rollback()
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao gravar configuracao Cliente Final: {exc}")

    # ---------------- Query ----------------
    def _build_connection_string(self) -> str:
        server = self.ed_server.text().strip()
        database = self.ed_database.text().strip()
        trusted = self.chk_trusted.isChecked()
        trust_cert = self.chk_trust_cert.isChecked()
        user = self.ed_user.text().strip()
        password = self.ed_password.text()

        if not server or not database:
            raise ValueError("Servidor e Base de Dados sao obrigatorios.")

        parts = [f"Server={server}", f"Database={database}", "Connection Timeout=30"]
        if trusted:
            parts.append("Integrated Security=True")
        else:
            if not user:
                raise ValueError("Utilizador em falta (ou ative Trusted_Connection).")
            parts.append(f"User ID={user}")
            parts.append(f"Password={password}")
        if trust_cert:
            parts.append("TrustServerCertificate=True")
        return ";".join(parts) + ";"

    def _query_encomendas(self) -> List[Dict[str, Any]]:
        min_year = int(getattr(self, "sp_min_year", None).value()) if hasattr(self, "sp_min_year") else 2026
        max_rows = int(getattr(self, "sp_max_rows", None).value()) if hasattr(self, "sp_max_rows") else 0
        top_clause = f"TOP ({max_rows})" if max_rows and max_rows > 0 else ""

        query = """
SELECT {top_clause}
    Id,
    Numero,
    Ano,
    Cliente,
    Contacto,
    RefCliente,
    CONVERT(VARCHAR(10), DataRecepcao, 104) AS DataRecepcao,
    Responsavel,
    CONVERT(VARCHAR(10), DataEntrega, 104) AS DataEntrega,
    PrazoObrigatorio,
    Status,
    NumPaletes,
    TipoPaletes,
    FormatoPalete,
    ExisteMontagem,
    Anulada,
    Observacoes,
    Cliente_Abre
FROM dbo.Encomendas WITH (NOLOCK)
WHERE Ano >= {min_year}
ORDER BY Ano DESC, Id DESC;
""".format(top_clause=top_clause, min_year=min_year).strip()

        self._assert_select_only(query)
        logger.info("Encomendas Cliente Final: a executar SELECT em dbo.Encomendas (read-only).")
        conn_str = self._build_connection_string()
        return self._run_sql_select(conn_str, query)

    def _load_itens_for_encomenda(self, encomenda_id: int) -> None:
        self.lbl_status.setText("")
        try:
            max_rows = int(getattr(self, "sp_max_itens", None).value()) if hasattr(self, "sp_max_itens") else 0
            top_clause = f"TOP ({max_rows})" if max_rows and max_rows > 0 else ""

            query = """
SELECT {top_clause}
    EncomendaId,
    RefObra,
    Referencia,
    Designacao,
    X,
    Y,
    Z,
    Quantidade,
    Unidade,
    Venda,
    ValorVenda,
    UnidadeAlternativa,
    QuantidadeAlternativa,
    Id
FROM dbo.ItensEncomenda WITH (NOLOCK)
WHERE EncomendaId = {encomenda_id}
ORDER BY Id ASC;
""".format(top_clause=top_clause, encomenda_id=int(encomenda_id)).strip()

            self._assert_select_only(query)
            logger.info("Encomendas Cliente Final: a executar SELECT em dbo.ItensEncomenda (read-only).")

            conn_str = self._build_connection_string()
            rows = self._run_sql_select(conn_str, query)
            self.model_itens.set_rows(rows)
            self.grp_itens.setTitle(f"Itens Encomenda (EncomendaId={encomenda_id})")
            self.lbl_status.setText(f"{len(rows)} itens carregados.")
        except Exception as exc:
            logger.exception("Encomendas Cliente Final: falha ao carregar itens: %s", exc)
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar itens da encomenda:\n\n{exc}")
            self._clear_itens()

    @staticmethod
    def _assert_select_only(query: str) -> None:
        q = (query or "").strip()
        if not q.upper().startswith("SELECT"):
            raise RuntimeError("Query invalida: apenas SELECT e permitido.")

        q_no_trailing = q.rstrip(";").strip()
        if ";" in q_no_trailing:
            raise RuntimeError("Query invalida: multiplos statements nao sao permitidos.")

        banned = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "MERGE", "EXEC", "CREATE")
        for token in banned:
            if re.search(rf"\b{re.escape(token)}\b", q_no_trailing, flags=re.IGNORECASE):
                raise RuntimeError("Query invalida: apenas SELECT e permitido.")

    def _run_sql_select(self, conn_str: str, query: str) -> List[Dict[str, Any]]:
        self._assert_select_only(query)
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
  throw 'Query invÇ­lida: apenas SELECT Ç¸ permitido.'
}
$q2 = $query.Trim()
$q2 = $q2.TrimEnd(';').Trim()
if ($q2.Contains(';')) { throw 'Query invÇ­lida: mÇ§ltiplos statements nÇœo sÇœo permitidos.' }
$banned = @('INSERT','UPDATE','DELETE','DROP','ALTER','TRUNCATE','MERGE','EXEC','CREATE')
foreach ($t in $banned) {
  if ([regex]::IsMatch($q2, ('\b' + [regex]::Escape($t) + '\b'), [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
    throw 'Query invÇ­lida: apenas SELECT Ç¸ permitido.'
  }
}

Add-Type -AssemblyName System.Data
$conn = New-Object System.Data.SqlClient.SqlConnection $connStr
$conn.Open()
try {
  $cmd = $conn.CreateCommand()
  $cmd.CommandText = $query
  $cmd.CommandTimeout = 180

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
  # Devolve base64(utf-8(json)) para evitar problemas de encoding ao capturar stdout
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
                timeout=180,
                creationflags=creationflags,
            )
            if result.returncode != 0:
                stdout = (result.stdout or "").strip()
                stderr = (result.stderr or "").strip()
                detail = "\n".join([s for s in (stderr, stdout) if s])
                raise RuntimeError(detail or f"CÇüdigo de saÇðda: {result.returncode}")

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

    def on_test_connection(self) -> None:
        self.lbl_status.setText("")
        try:
            conn_str = self._build_connection_string()
            self._run_sql_select(conn_str, "SELECT 1 AS OK;")
            self.lbl_status.setText("Ligacao OK.")
        except Exception as exc:
            logger.exception("Encomendas Cliente Final: falha ao testar ligacao: %s", exc)
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao testar ligacao Cliente Final:\n\n{exc}")

    def on_load_encomendas(self) -> None:
        self.lbl_status.setText("")
        try:
            rows = self._query_encomendas()
            self.model_enc.set_rows(rows)
            self.lbl_status.setText(f"{len(rows)} encomendas carregadas. Selecione uma encomenda para ver itens.")
            self._clear_itens()
        except Exception as exc:
            logger.exception("Encomendas Cliente Final: falha ao carregar encomendas: %s", exc)
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao carregar encomendas do Cliente Final:\n\n{exc}")
            self._clear_itens()
