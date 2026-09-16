# Multi-Agent System

![Tests](https://github.com/pekdemirengin-ops/multi-agent-system/actions/workflows/test.yml/badge.svg)

Moduler, dagitik multi-agent sistemi. FastAPI + WebSocket + Redis + Docker.

## Ozellikler

- Multi-Agent: 4 farkli agent (researcher, llm, system, coder)
- RAG: Web search (ddgs) + LLM ozetleme
- Coder: LLM kod yazar, guvenli sandbox'ta calistirir
- System Monitoring: CPU, RAM, disk, uptime raporu
- REST API: FastAPI + Swagger UI (/docs)
- WebSocket: Canli cevap akisi (/ws/ask)
- Redis Bus: Dagitik mesajlasma (opsiyonel)
- Docker: docker compose up ile tek komut
- Test: 29 pytest + GitHub Actions CI

## Agent'lar

| Agent | Gorev |
|-------|-------|
| `researcher` | Web arama + RAG (kaynakli ozet) |
| `llm` | Genel LLM sohbeti |
| `system` | Sistem izleme (CPU, RAM, disk, uptime) |
| `coder` | LLM kod yazar, guvenli sandbox'ta calistirir |

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

### Ornek Sorular

- `{"message": "2024 Nobel Baris Odulu kime verildi?", "agent": "researcher"}`
- `{"message": "Sistem durumu nedir?", "agent": "system"}`
- `{"message": "Fibonacci sayilarini yazdir", "agent": "coder"}`

### WebSocket

const ws = new WebSocket("ws://localhost:8000/ws/ask");
ws.send(JSON.stringify({message: "Python nedir?", agent: "researcher"}));

## Katmanlar

- `core/` - BaseAgent, MessageBus, RedisMessageBus, Registry, Orchestrator
- `agents/ai/` - LLMAgent, PlannerAgent, ResearcherAgent, CoderAgent
- `agents/devops/` - SystemAgent
- `tools/` - GroqLLMClient, Web Search (ddgs), Code Runner, System Info
- `api/` - FastAPI routes (REST + WebSocket)
- `tests/` - 29 pytest testleri

## Mimari

Kullanici (REST/WebSocket)
   |
FastAPI (api/main.py)
   |
MessageBus (in-memory | Redis)
   |
Agent'lar (researcher, llm, system, coder)
   |
Groq LLM + Web Search + psutil + subprocess

## Guvenlik

- `.env` dosyasi `.gitignore`'da (API key'ler korunur)
- CoderAgent kodu AST ile analiz eder, yasakli import/cagrilari reddeder
- Sandbox'ta calistirir (timeout, ayrilmis process)

## Lisans

MIT