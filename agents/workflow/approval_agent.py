"""Onay akisi agent'i - insan onayini bekler."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from core.base_agent import BaseAgent, Message

logger = structlog.get_logger(__name__)


class ApprovalAgent(BaseAgent):
    """Onay gerektiren islemleri yonetir.

    Kullanim:
    - Agent bir islem icin onay ister
    - ApprovalAgent bekleyen onaylar listesine ekler
    - Kullanici onaylar/reddeder
    - Agent bilgilendirilir
    """

    def __init__(self, name: str, bus: Any, timeout_seconds: int = 300) -> None:
        super().__init__(name, bus)
        self.pending: dict[str, dict[str, Any]] = {}
        self.timeout = timeout_seconds

    async def handle(self, message: Message) -> None:
        content = message.content if isinstance(message.content, dict) else {"action": str(message.content)}

        if message.msg_type == "approval_request":
            # Yeni onay istegi
            request_id = str(uuid.uuid4())[:8]
            self.pending[request_id] = {
                "id": request_id,
                "requester": message.sender,
                "action": content.get("action", "bilinmeyen"),
                "details": content.get("details", ""),
                "requested_at": datetime.now(timezone.utc).isoformat(),
                "status": "pending",
            }
            logger.info("approval.requested", id=request_id, requester=message.sender)

            await self.send(
                message.sender,
                {
                    "research": f"Onay bekleniyor (ID: {request_id}).\n\n"
                    f"Islem: {content.get('action', '')}\n"
                    f"Detay: {content.get('details', '')[:200]}\n\n"
                    f"Onaylamak icin: /api/ask ile 'onayla {request_id}' yaz.",
                    "sources": [],
                    "source_count": 0,
                    "request_id": request_id,
                    "status": "pending",
                },
                msg_type="result",
            )
            return

        if message.msg_type == "task":
            action = content.get("action", "").lower()

            # Onaylama
            if action.startswith("onayla") or action.startswith("approve"):
                request_id = action.split()[-1] if " " in action else ""
                await self._handle_approve(message.sender, request_id)
                return

            # Reddetme
            if action.startswith("reddet") or action.startswith("reject"):
                request_id = action.split()[-1] if " " in action else ""
                await self._handle_reject(message.sender, request_id)
                return

            # Listeleme
            if "listele" in action or "bekleyen" in action:
                await self._handle_list(message.sender)
                return

            # Bilinmeyen
            await self.send(
                message.sender,
                {"error": "Anlasilamadi. 'onayla X', 'reddet X' veya 'bekleyenleri listele' yazin."},
                msg_type="error",
            )

    async def _handle_approve(self, sender: str, request_id: str) -> None:
        if request_id not in self.pending:
            await self.send(sender, {"error": f"Onay bulunamadi: {request_id}"}, msg_type="error")
            return
        self.pending[request_id]["status"] = "approved"
        self.pending[request_id]["decided_at"] = datetime.now(timezone.utc).isoformat()
        logger.info("approval.approved", id=request_id)
        await self.send(
            sender,
            {
                "research": f"Onaylandi: {request_id}",
                "sources": [],
                "source_count": 0,
                "request_id": request_id,
                "status": "approved",
            },
            msg_type="result",
        )

    async def _handle_reject(self, sender: str, request_id: str) -> None:
        if request_id not in self.pending:
            await self.send(sender, {"error": f"Onay bulunamadi: {request_id}"}, msg_type="error")
            return
        self.pending[request_id]["status"] = "rejected"
        self.pending[request_id]["decided_at"] = datetime.now(timezone.utc).isoformat()
        logger.info("approval.rejected", id=request_id)
        await self.send(
            sender,
            {
                "research": f"Reddedildi: {request_id}",
                "sources": [],
                "source_count": 0,
                "request_id": request_id,
                "status": "rejected",
            },
            msg_type="result",
        )

    async def _handle_list(self, sender: str) -> None:
        pending_only = [r for r in self.pending.values() if r["status"] == "pending"]
        if not pending_only:
            answer = "Bekleyen onay yok."
        else:
            lines = [f"Bekleyen {len(pending_only)} onay:"]
            for r in pending_only:
                lines.append(f"- [{r['id']}] {r['action']} (isteyen: {r['requester']})")
            answer = "\n".join(lines)
        await self.send(
            sender,
            {"research": answer, "sources": [], "source_count": 0},
            msg_type="result",
        )

    def __repr__(self) -> str:
        return f"<ApprovalAgent pending={len(self.pending)}>"