"""Email gonderme araci (simulasyon + SMTP)."""
from __future__ import annotations

import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Sent emails klasoru (log icin)
SENT_DIR = Path(os.getenv("DATA_DIR", "data")) / "sent_emails"
SENT_DIR.mkdir(parents=True, exist_ok=True)


def send_email(
    to: str,
    subject: str,
    body: str,
    from_addr: str = "noreply@multi-agent-system.local",
    dry_run: bool = True,
) -> dict[str, Any]:
    """Email gonderir (varsayilan: dry_run - sadece loglar).

    Args:
        to: Alici email
        subject: Konu
        body: Icerik
        from_addr: Gonderen
        dry_run: True ise gercekten gondermez, sadece kaydeder

    Returns:
        {"status": "sent" | "dry_run" | "error", "message_id": str, ...}
    """
    message_id = f"msg-{datetime.now().strftime('%Y%m%d%H%M%S')}-{os.urandom(4).hex()}"

    # Email olustur
    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # Her durumda logla (dosyaya kaydet)
    log_entry = {
        "message_id": message_id,
        "timestamp": datetime.now().isoformat(),
        "from": from_addr,
        "to": to,
        "subject": subject,
        "body": body,
        "dry_run": dry_run,
    }

    try:
        # Dosyaya kaydet
        file_path = SENT_DIR / f"{message_id}.txt"
        file_path.write_text(
            f"From: {from_addr}\n"
            f"To: {to}\n"
            f"Subject: {subject}\n"
            f"Date: {log_entry['timestamp']}\n"
            f"\n{body}\n",
            encoding="utf-8",
        )

        if dry_run:
            logger.info("email.dry_run", to=to, subject=subject, message_id=message_id)
            return {
                "status": "dry_run",
                "message_id": message_id,
                "to": to,
                "subject": subject,
                "saved_to": str(file_path),
            }

        # Gercek SMTP
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")

        if not smtp_host:
            return {
                "status": "dry_run",
                "message_id": message_id,
                "reason": "SMTP_HOST ayarlanmamis",
                "saved_to": str(file_path),
            }

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.starttls()
            if smtp_user and smtp_pass:
                server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        logger.info("email.sent", to=to, subject=subject, message_id=message_id)
        return {"status": "sent", "message_id": message_id, "to": to, "subject": subject}

    except Exception as e:
        logger.exception("email.error", to=to, error=str(e))
        return {"status": "error", "message_id": message_id, "error": str(e)}


def list_sent_emails(limit: int = 20) -> list[dict[str, Any]]:
    """Gonderilmis emailleri listeler (en yeni once)."""
    emails = []
    files = sorted(SENT_DIR.glob("msg-*.txt"), reverse=True)[:limit]
    for f in files:
        content = f.read_text(encoding="utf-8")
        lines = content.split("\n")
        header = {}
        for line in lines[:4]:
            if ": " in line:
                k, v = line.split(": ", 1)
                header[k.lower()] = v
        emails.append(
            {
                "message_id": f.stem,
                "to": header.get("to", ""),
                "subject": header.get("subject", ""),
                "timestamp": header.get("date", ""),
            }
        )
    return emails