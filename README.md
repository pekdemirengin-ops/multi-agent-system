# Multi-Agent System

![Tests](https://github.com/pekdemirengin-ops/multi-agent-system/actions/workflows/test.yml/badge.svg)

Moduler, dagitik multi-agent sistemi. FastAPI + WebSocket + Redis + Docker.

## Ozellikler

- Multi-Agent: LLM, Planner, Researcher agent'lari
- RAG: Web search (ddgs) + LLM ozetleme
- REST API: FastAPI + Swagger UI (/docs)
- WebSocket: Canli cevap akisi (/ws/ask)
- Redis Bus: Dagitik mesajlasma (opsiyonel)
- Docker: docker compose up ile tek komut
- Test: 18 pytest + GitHub Actions CI

## Hizli Baslangic

### Docker ile (Onerilen)

git clone https://github.com/pekdemirengin-ops/multi-agent-system
cd multi-agent-system
cp .env.example .env
# .env dosyasina GROQ_API_KEY ekle
docker compose up -d

Tarayicida ac: http://localhost:8000/docs

### Yerel Gelistirme

uv sync --extra dev
cp .env.example .env
# GROQ_API_KEY ekle
uv run pytest -v
uv run uvicorn api.main:app --reload

## API Kullanimi

### REST

curl -X POST http://localhost:8000/api/ask -H "Content-Type: application/json" -d "{\"message\": \"Python nedir?\", \"agent\": \"researcher\"}"

### WebSocket

const ws = new WebSocket("ws://localhost:8000/ws/ask");
ws.send(JSON.stringify({message: "Python nedir?", agent: "researcher"}));

## Katmanlar

- core/ - BaseAgent, MessageBus, RedisMessageBus, Registry, Orchestrator
- agents/ai/ - LLMAgent, PlannerAgent, ResearcherAgent
- tools/ - GroqLLMClient, Web Search (ddgs)
- api/ - FastAPI routes (REST + WebSocket)
- tests/ - 18 pytest testleri

## Mimari

Kullanici (REST/WebSocket)
   |
FastAPI (api/main.py)
   |
MessageBus (in-memory | Redis)
   |
Agent'lar (LLM, Planner, Researcher)
   |
Groq LLM + Web Search

## Lisans

MIT