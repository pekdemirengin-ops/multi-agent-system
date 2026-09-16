# Multi-Agent System

![Tests](https://github.com/pekdemirengin-ops/multi-agent-system/actions/workflows/test.yml/badge.svg)

Moduler, dagitik multi-agent sistemi. FastAPI + WebSocket + Redis + Docker + LLM.

## Canli Demo

**[multi-agent-system-production-9301.up.railway.app](https://multi-agent-system-production-9301.up.railway.app)**

7 agent, web arayuzu ile. Linke tikla, agent sec, soru sor.

## Ozellikler

- 7 Agent: researcher, llm, system, coder, planner, reviewer, summarizer
- Web Arayuzu: Modern chat UI (HTML/CSS/JS)
- RAG: Web search (ddgs) + LLM ozetleme
- Kod Calistirma: LLM kod yazar, guvenli sandbox'ta calistirir
- Sistem Izleme: CPU, RAM, disk, uptime
- Multi-Agent Pipeline: Planner + N agent isbirligi (/api/team)
- WebSocket: Canli cevap akisi (/ws/ask)
- Redis Bus: Dagitik mesajlasma (opsiyonel)
- Docker: docker compose up ile tek komut
- Test: 31 pytest + GitHub Actions CI
- CI/CD: GitHub -> Railway otomatik deploy

## Agent'lar

| Agent | Gorev |
|-------|-------|
| researcher | Web arama + RAG (kaynakli ozet) |
| llm | Genel LLM sohbeti |
| system | Sistem izleme (CPU, RAM, disk, uptime) |
| coder | LLM kod yazar, guvenli sandbox'ta calistirir |
| planner | Gorevi alt adimlara boler |
| reviewer | Kod inceleme, iyilestirme onerileri |
| summarizer | Uzun metinleri ozetler |

## Hizli Baslangic

### Docker ile (Onerilen)

git clone https://github.com/pekdemirengin-ops/multi-agent-system
cd multi-agent-system
cp .env.example .env
# .env dosyasina GROQ_API_KEY ekle
docker compose up -d

Tarayicida ac: http://localhost:8000

### Yerel Gelistirme

uv sync --extra dev
cp .env.example .env
# GROQ_API_KEY ekle
uv run pytest -v
uv run uvicorn api.main:app --reload

## API Kullanimi

### REST

curl -X POST http://localhost:8000/api/ask -H "Content-Type: application/json" -d "{\"message\": \"Python nedir?\", \"agent\": \"researcher\"}"

### Multi-Agent Pipeline

curl -X POST http://localhost:8000/api/team -H "Content-Type: application/json" -d "{\"message\": \"Python'da asal sayi fonksiyonu yaz ve sistem durumunu raporla\"}"

### WebSocket

const ws = new WebSocket("ws://localhost:8000/ws/ask");
ws.send(JSON.stringify({message: "Python nedir?", agent: "researcher"}));
ws.onmessage = (e) => console.log(JSON.parse(e.data));

## Ornek Sorular

- researcher: "2024 Nobel Baris Odulu kime verildi?"
- system: "Sistem durumu nedir?"
- coder: "1'den 10'a kadar asal sayilari yazdir"
- summarizer: "Multi-agent system nedir? Kisaca ozetle"

## Mimari

Kullanici (Web UI / REST / WebSocket)
   |
FastAPI (api/main.py)
   |
MessageBus (in-memory | Redis)
   |
Agent'lar (researcher, llm, system, coder, planner, reviewer, summarizer)
   |
Groq LLM + Web Search + psutil + subprocess

## Katmanlar

- core/ - BaseAgent, MessageBus, RedisMessageBus, Registry, Orchestrator
- agents/ai/ - LLMAgent, PlannerAgent, ResearcherAgent, CoderAgent, ReviewerAgent, SummarizerAgent
- agents/devops/ - SystemAgent
- tools/ - GroqLLMClient, Web Search, Code Runner, System Info
- api/ - FastAPI routes (REST + WebSocket)
- static/ - Web arayuzu (HTML/CSS/JS)
- tests/ - 31 pytest testleri

## Guvenlik

- .env dosyasi .gitignore'da (API key'ler korunur)
- CoderAgent kodu AST ile analiz eder (yasakli import/cagri reddi)
- Sandbox'ta calistirir (timeout, ayrilmis process)

## Teknolojiler

- Backend: Python 3.11, FastAPI, Uvicorn, Pydantic
- LLM: Groq (openai/gpt-oss-120b)
- Web Search: ddgs (DuckDuckGo)
- Database/Cache: Redis
- Container: Docker, docker-compose
- CI/CD: GitHub Actions
- Deploy: Railway
- Test: pytest, pytest-asyncio
- Logging: structlog
- Monitoring: psutil

## Test

uv run pytest -v
# 31 passed in ~3s

## Lisans

MIT