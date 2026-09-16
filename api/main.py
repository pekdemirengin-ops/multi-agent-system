"""FastAPI uygulamasi - agent'lari HTTP uzerinden acar."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import agents, health, team, ws

logger = structlog.get_logger(__name__)

STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("api.startup")
    await agents.init_agents()
    yield
    logger.info("api.shutdown")


app = FastAPI(
    title="Multi-Agent System API",
    description="Moduler multi-agent sistemi icin REST + WebSocket API",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(agents.router)
app.include_router(team.router)
app.include_router(ws.router)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def root():
    """Ana sayfa - web arayuzu."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "name": "Multi-Agent System API",
        "version": "0.3.0",
        "docs": "/docs",
        "agents_endpoint": "/api/agents",
        "team_endpoint": "/api/team",
    }