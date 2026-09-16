"""WebSocket endpoint - canli cevap akisi."""
from __future__ import annotations

import asyncio
import json
import uuid

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.routes.agents import _agents, get_agent, init_agents
from core.base_agent import Message

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["websocket"])


@router.websocket("/ws/ask")
async def ws_ask(websocket: WebSocket) -> None:
    """WebSocket uzerinden agent'a soru sor, cevabi parca parca al.

    Kullanim (tarayici):
        ws = new WebSocket("ws://localhost:8000/ws/ask");
        ws.send(JSON.stringify({message: "...", agent: "researcher"}));
        ws.onmessage = (e) => console.log(e.data);
    """
    await websocket.accept()
    logger.info("ws.connected", client=websocket.client)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "error": "Gecersiz JSON"})
                continue

            message_text = payload.get("message", "").strip()
            agent_name = payload.get("agent", "researcher")

            if not message_text:
                await websocket.send_json({"type": "error", "error": "message bos"})
                continue

            # Sistem hazir mi?
            await init_agents()
            try:
                agent = get_agent(agent_name)
            except Exception as e:
                await websocket.send_json({"type": "error", "error": str(e)})
                continue

            # Cevabi yakalamak icin gecici bir dinleyici agent kullan
            # Not: Mevcut agent'lar mesaji handle edip result gonderir
            # Biz de o result'i yakalamak icin bir "bridge" agent kullaniyoruz
            await websocket.send_json(
                {
                    "type": "start",
                    "message": message_text,
                    "agent": agent_name,
                }
            )

            # Basit yaklasim: mevcut /api/ask mantigini kullan
            # Ama streaming icin once result'i future ile yakalayip
            # sonra parcalara bolup gonderiyoruz
            from api.routes.agents import _response_futures

            fid = str(uuid.uuid4())
            loop = asyncio.get_running_loop()
            future: asyncio.Future = loop.create_future()
            _response_futures[fid] = future

            msg = Message(
                sender="__api_collector__",
                receiver=agent_name,
                content=message_text,
                msg_type="task",
                id=fid,
            )
            from api.routes.agents import _bus

            await _bus.publish(msg)

            try:
                result = await asyncio.wait_for(future, timeout=60)
            except asyncio.TimeoutError:
                _response_futures.pop(fid, None)
                await websocket.send_json(
                    {"type": "error", "error": "Zaman asimi"}
                )
                continue

            # Sonucu gonder
            if isinstance(result, dict):
                answer = result.get("research") or result.get("answer") or str(result)
                sources = result.get("sources", [])

                # Cevabi kelime kelime akit (streaming simulasyonu)
                words = answer.split(" ")
                for i, word in enumerate(words):
                    await websocket.send_json(
                        {
                            "type": "chunk",
                            "content": word + (" " if i < len(words) - 1 else ""),
                            "index": i,
                        }
                    )
                    await asyncio.sleep(0.02)  # kucuk gecikme - gercekci gorunsun

                # Kaynaklari gonder
                if sources:
                    await websocket.send_json(
                        {
                            "type": "sources",
                            "sources": [
                                {"title": s.get("title", ""), "url": s.get("url", "")}
                                for s in sources
                            ],
                        }
                    )

                await websocket.send_json({"type": "done"})
            else:
                await websocket.send_json(
                    {"type": "chunk", "content": str(result)}
                )
                await websocket.send_json({"type": "done"})

    except WebSocketDisconnect:
        logger.info("ws.disconnected", client=websocket.client)
    except Exception as e:
        logger.exception("ws.error", error=str(e))
        try:
            await websocket.send_json({"type": "error", "error": str(e)})
        except Exception:
            pass