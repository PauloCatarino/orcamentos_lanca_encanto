import os
import importlib
import re
import html
from pathlib import Path
from email.message import EmailMessage
import smtplib
from datetime import datetime
from typing import Any, Optional, Sequence

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def _env_bool(var_name: str, default: str = "false") -> bool:
    return os.getenv(var_name, default).lower() in {"1", "true", "yes"}


def _require_win32com_client() -> Any:
    """
    Carrega `win32com.client` apenas quando necessário (USE_OUTLOOK=true).

    Requer o pacote `pywin32` instalado no mesmo Python/venv.
    """
    try:
        return importlib.import_module("win32com.client")
    except Exception as exc:
        raise RuntimeError(
            "USE_OUTLOOK=true requer o pacote 'pywin32' instalado no mesmo Python/venv.\n"
            "Ex.: .venv_Martelo\\Scripts\\python.exe -m pip install pywin32"
        ) from exc


def load_signature() -> str:
    assinatura_path = os.getenv("ASSINATURA_HTML")
    if assinatura_path and os.path.exists(assinatura_path):
        with open(assinatura_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def _split_recipients(value: str) -> list[str]:
    parts = re.split(r"[;,]+", str(value or ""))
    return [p.strip() for p in parts if p and p.strip()]


def _find_outlook_account(session: Any, smtp_address: str) -> Any | None:
    try:
        accounts = session.Accounts
    except Exception:
        return None

    wanted = (smtp_address or "").strip().lower()
    if not wanted:
        return None

    try:
        count = int(accounts.Count)
    except Exception:
        count = 0

    for i in range(1, count + 1):
        try:
            account = accounts.Item(i)
        except Exception:
            continue
        try:
            addr = str(getattr(account, "SmtpAddress", "") or "").strip().lower()
        except Exception:
            continue
        if addr == wanted:
            return account

    return None


def send_email(
    destino: str,
    assunto: str,
    corpo_html: str,
    anexos: Optional[Sequence[str]] = None,
    *,
    remetente_email: str | None = None,
    remetente_nome: str | None = None,
    cc: str | None = None,
) -> None:
    host = os.getenv("SMTP_HOST", "localhost")
    port = int(os.getenv("SMTP_PORT", "25"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    use_ssl = _env_bool("SMTP_SSL", "false")
    use_tls = _env_bool("SMTP_TLS", "false")
    # Opcional: emails em cópia (se definido). Por defeito não envia para nenhum endereço.
    copia = os.getenv("EMAIL_COPIA", "").strip()

    remetente_email = (remetente_email or "").strip() or None
    from_email = remetente_email or user

    cc_list: list[str] = []
    if copia:
        cc_list.extend(_split_recipients(copia))
    if remetente_email:
        cc_list.extend(_split_recipients(remetente_email))
    if cc:
        cc_list.extend(_split_recipients(cc))

    seen = set()
    cc_unique: list[str] = []
    for addr in cc_list:
        key = addr.lower()
        if key in seen:
            continue
        seen.add(key)
        cc_unique.append(addr)

    cc_outlook = ";".join(cc_unique)
    cc_rfc = ", ".join(cc_unique)
    log_dest = destino + (f";{cc_outlook}" if cc_outlook else "")

    assinatura_nome = (remetente_nome or "").strip()
    assinatura = html.escape(assinatura_nome) if assinatura_nome else load_signature()
    corpo_html = corpo_html.replace("{{assinatura}}", assinatura)
    use_outlook = _env_bool("USE_OUTLOOK", "false")
    if use_outlook:
        try:
            win32_client = _require_win32com_client()
            outlook = win32_client.Dispatch("Outlook.Application")
            mail = outlook.CreateItem(0)
            if remetente_email:
                account = _find_outlook_account(outlook.Session, remetente_email)
                if account is not None:
                    mail.SendUsingAccount = account
                else:
                    mail.SentOnBehalfOfName = remetente_email
            mail.To = destino
            if cc_outlook:
                mail.CC = cc_outlook
            mail.Subject = assunto or "Orçamento"
            mail.HTMLBody = corpo_html
            for path in anexos or []:
                if os.path.exists(path):
                    mail.Attachments.Add(path)
            # garante que fica em "Items Enviados"
            mail.SaveSentMessageFolder = outlook.Session.GetDefaultFolder(5)
            mail.Send()
            _safe_log_result(from_email or "<outlook>", log_dest, assunto, "OK", anexos)
            return
        except Exception as e:
            _safe_log_result(from_email or "<outlook>", log_dest, assunto, f"ERRO: {e}", anexos)
            raise

    msg = EmailMessage()
    msg["Subject"] = assunto or "Orçamento"
    msg["From"] = from_email
    msg["To"] = destino
    if cc_rfc:
        msg["Cc"] = cc_rfc
    msg.set_content("Este email requer visualização em HTML.")
    msg.add_alternative(corpo_html, subtype="html")

    for path in anexos or []:
        if os.path.exists(path):
            with open(path, "rb") as f:
                msg.add_attachment(
                    f.read(), maintype="application", subtype="octet-stream", filename=os.path.basename(path)
                )

    try:
        import sys

        print("=== DEBUG ENVIO EMAIL ===")
        print("SMTP_HOST:", host)
        print("SMTP_PORT:", port)
        print("SMTP_USER:", user)
        print("DESTINATARIO:", destino)
        print("CC:", cc_outlook)
        print("ASSUNTO:", assunto)
        print("Corpo tamanho:", len(corpo_html))
        print("Python exe:", sys.executable)
        if use_ssl:
            with smtplib.SMTP_SSL(host, port) as smtp:
                if user:
                    smtp.login(user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port) as smtp:
                if use_tls:
                    smtp.starttls()
                if user:
                    smtp.login(user, password)
                smtp.send_message(msg)
        _safe_log_result(from_email, log_dest, assunto, "OK", anexos)
    except Exception as e:
        _safe_log_result(from_email, log_dest, assunto, f"ERRO: {e}", anexos)
        raise


def get_email_log_path() -> Path:
    """
    Devolve um caminho seguro para o ficheiro `envio_emails.log`.

    Nota: evitar escrever em `Program Files` (normalmente sem permissões para utilizadores).
    Preferimos um caminho por máquina (ProgramData) e, se falhar, por utilizador (LocalAppData).
    """
    filename = "envio_emails.log"

    explicit = (os.getenv("MARTELO_EMAIL_LOG_PATH") or "").strip()
    if explicit:
        try:
            return Path(explicit).expanduser()
        except Exception:
            pass

    candidates: list[Path] = []
    programdata = (os.getenv("PROGRAMDATA") or "").strip()
    if programdata:
        candidates.append(Path(programdata) / "Martelo Orcamentos V2" / filename)
    localappdata = (os.getenv("LOCALAPPDATA") or "").strip()
    if localappdata:
        candidates.append(Path(localappdata) / "Martelo Orcamentos V2" / filename)
    candidates.append(Path.home() / "Martelo Orcamentos V2" / filename)

    for path in candidates:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as _:
                pass
            return path
        except Exception:
            continue

    # fallback final: diretório atual (pode falhar, mas não há melhor alternativa)
    return Path(filename).resolve()


def _log_result(remetente: str, destino: str, assunto: str, status: str, anexos=None) -> None:
    log_path = get_email_log_path()
    linha = f"{datetime.now().isoformat()} | {remetente} -> {destino} | {assunto} | {status} | {anexos}\n"
    with log_path.open("a", encoding="utf-8") as log:
        log.write(linha)


def _safe_log_result(remetente: str, destino: str, assunto: str, status: str, anexos=None) -> None:
    """
    Regista o envio de email sem nunca bloquear/lançar exceções.
    """
    try:
        _log_result(remetente, destino, assunto, status, anexos)
    except Exception:
        # não interrompe o fluxo principal (email pode ter sido enviado)
        pass
