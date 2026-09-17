"""Email gonderme agent'i."""
from __future__ import annotations

import re
from typing import Any

import structlog

from core.base_agent import BaseAgent, Message
from tools.email_tool import list_sent_emails, send_email
from tools.llm_client import GroqLLMClient

logger = structlog.get_logger(__name__)


EMAIL_SYSTEM_PROMPT = """Sen bir email asistanisin. Kullanicinin istegine gore
email icerigi olusturursun.

Cikti formatini SADECE su sekilde dondur:
TO: alici@example.com
SUBJECT: Konu
BODY:
Email icerigi burada.
"""


class EmailAgent(BaseAgent):
    """Email gonderme + icerik olusturma agent'i."""

    def __init__(self, name: str, bus: Any, model: str | None = None) -> None:
        super().__init__(name, bus)
        self.llm = GroqLLMClient(model=model)

    async def handle(self, message: Message) -> None:
        if message.msg_type != "task":
            return

        try:
            content = str(message.content)
            content_lower = content.lower()

            # Listeleme istegi
            if any(k in content_lower for k in ["listele", "goster", "sent", "gonderilen"]):
                emails = list_sent_emails(limit=10)
                if not emails:
                    answer = "Henuz gonderilmis email yok."
                else:
                    lines = [f"Son {len(emails)} email:"]
                    for e in emails:
                        lines.append(f"- [{e['message_id']}] {e['to']} - {e['subject']}")
                    answer = "\n".join(lines)

                await self.send(
                    message.sender,
                    {"research": answer, "sources": [], "source_count": 0},
                    msg_type="result",
                )
                return

            # Email gonderme istegi
            # LLM'den email icerigi olustur
            raw = self.llm.chat(prompt=content, system=EMAIL_SYSTEM_PROMPT)

            # Parse et
            parsed = self._parse_email(raw)
            to = parsed["to"]
            subject = parsed["subject"]
            body = parsed["body"]

            if not to:
                await self.send(
                    message.sender,
                    {
                        "research": "Email gonderilemedi: alici adresi bulunamadi.\n\nLLM cikitisi:\n" + raw[:300],
                        "sources": [],
                        "source_count": 0,
                    },
                    msg_type="result",
                )
                return

            # Gonder (dry_run - gercekten gondermez, kaydeder)
            result = send_email(to=to, subject=subject, body=body, dry_run=True)

            # Format cevap
            if result["status"] == "dry_run":
                answer = (
                    f"Email hazirlandi (dry run - gonderilmedi):\n\n"
                    f"Kime: {to}\n"
                    f"Konu: {subject}\n"
                    f"Icerik:\n{body}\n\n"
                    f"Mesaj ID: {result['message_id']}\n"
                    f"Kaydedildi: {result.get('saved_to', 'N/A')}"
                )
            elif result["status"] == "sent":
                answer = f"Email gonderildi:\n- Kime: {to}\n- Konu: {subject}\n- ID: {result['message_id']}"
            else:
                answer = f"Email hatasi: {result.get('error', 'bilinmeyen')}"

            logger.info("email_agent.done", to=to, status=result["status"])

            await self.send(
                message.sender,
                {"research": answer, "sources": [], "source_count": 0},
                msg_type="result",
            )

        except Exception as e:
            logger.exception("email_agent.error", error=str(e))
            await self.send(message.sender, {"error": str(e)}, msg_type="error")

    @staticmethod
    def _parse_email(raw: str) -> dict[str, str]:
        """LLM ciktisindan TO/SUBJECT/BODY parse eder."""
        to_match = re.search(r"TO:\s*(.+)", raw, re.IGNORECASE)
        subject_match = re.search(r"SUBJECT:\s*(.+)", raw, re.IGNORECASE)
        body_match = re.search(r"BODY:\s*\n?(.+)", raw, re.IGNORECASE | re.DOTALL)

        return {
            "to": to_match.group(1).strip() if to_match else "",
            "subject": subject_match.group(1).strip() if subject_match else "(konu yok)",
            "body": body_match.group(1).strip() if body_match else raw[:500],
        }

    def __repr__(self) -> str:
        return f"<EmailAgent name={self.name!r}>"