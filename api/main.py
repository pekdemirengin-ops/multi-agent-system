"""FastAPI uygulamasi - agent'lari HTTP uzerinden acar."""
from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import agents, health

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("api.startup")
    await agents.init_agents()
    yield
    logger.info("api.shutdown")


app = FastAPI(
    title="Multi-Agent System API",
    description="Moduler multi-agent sistemi icin REST API",
    version="0.1.0",
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


@app.get("/", tags=["root"])
async def root():
    return {
        "name": "Multi-Agent System API",
        "version": "0.1.0",
        "docs": "/docs",
        "agents_endpoint": "/api/agents",
    }