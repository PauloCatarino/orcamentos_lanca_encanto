import os
from email.message import EmailMessage
import smtplib
from datetime import datetime

import sys
print("Python exe:", sys.executable)

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def _env_bool(var_name: str, default: str = "false") -> bool:
    return os.getenv(var_name, default).lower() in {"1", "true", "yes"}


def load_signature() -> str:
    assinatura_path = os.getenv("ASSINATURA_HTML")
    if assinatura_path and os.path.exists(assinatura_path):
        with open(assinatura_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def send_email(destino: str, assunto: str, corpo_html: str, anexos=None) -> None:
    host = os.getenv("SMTP_HOST", "localhost")
    port = int(os.getenv("SMTP_PORT", "25"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    use_ssl = _env_bool("SMTP_SSL", "false")
    use_tls = _env_bool("SMTP_TLS", "false")

    assinatura = load_signature()
    corpo_html = corpo_html.replace("{{assinatura}}", assinatura)

    msg = EmailMessage()
    msg["Subject"] = assunto or "Orçamento"
    msg["From"] = user
    msg["To"] = destino
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
        _log_result(destino, assunto, "OK", anexos)
    except Exception as e:
        _log_result(destino, assunto, f"ERRO: {e}", anexos)
        raise


def _log_result(destino: str, assunto: str, status: str, anexos=None) -> None:
    linha = f"{datetime.now().isoformat()} | {os.getenv('SMTP_USER')} -> {destino} | {assunto} | {status} | {anexos}\n"
    with open("envio_emails.log", "a", encoding="utf-8") as log:
        log.write(linha)

