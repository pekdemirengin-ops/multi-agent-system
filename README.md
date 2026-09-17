# Multi-Agent System

![Tests](https://github.com/pekdemirengin-ops/multi-agent-system/actions/workflows/test.yml/badge.svg)

Moduler, dagitik multi-agent sistemi. FastAPI + WebSocket + Redis + Docker + LLM.

## Canli Demo

**[multi-agent-system-production-9301.up.railway.app](https://multi-agent-system-production-9301.up.railway.app)**

- Giris: `admin` / `admin123`
- 8 agent, web arayuzu, mobil uyumlu
- Sesli kullanim (MIC + TTS)
- Sohbet gecmisi (kalici volume)

## Ozellikler

### AI & Agent
- **8 Agent:** researcher, llm, system, coder, planner, reviewer, summarizer, router
- **Hibrit Router:** Regex (0ms) + LLM fallback
- **RAG:** Web search (ddgs) + LLM ozetleme
- **Kod Calistirma:** LLM kod yazar, guvenli sandbox'ta calistirir
- **Sistem Izleme:** CPU, RAM, disk, uptime
- **Multi-Agent Pipeline:** Planner + N agent isbirligi (`/api/team`)

### Backend
- **FastAPI:** REST + WebSocket
- **JWT Authentication:** Token bazli guvenli erisim
- **Rate Limiting:** 30 istek/dk (kullanici bazli)
- **Input Validation:** Bos/tehlikeli mesaj reddi
- **CORS:** Kisitlanmis origin'ler
- **SQLite Hafiza:** Konusma gecmisi
- **Redis Bus:** Dagitik mesajlasma (opsiyonel)

### Frontend
- **Modern Chat UI:** HTML/CSS/JS
- **Login/Register:** JWT token yonetimi
- **Sohbet Gecmisi:** Otomatik yukleme
- **Sesli Kullanim:** Web Speech API (STT + TTS)
- **Mobil Uyumlu:** Responsive tasarim

### DevOps
- **Docker:** `docker compose up` ile tek komut
- **Railway:** Otomatik deploy (GitHub webhook)
- **Kalici Volume:** 500 MB (SQLite)
- **CI/CD:** GitHub Actions
- **Healthcheck:** Docker + Railway

## Agent'lar

| Agent | Gorev | Ornek |
|-------|-------|-------|
| `researcher` | Web arama + RAG | "2026 Dunya Kupasi sampiyonu kim?" |
| `llm` | Genel LLM sohbet | "Python nedir?" |
| `system` | Sistem izleme | "CPU ne kadar?" |
| `coder` | Kod yaz + calistir | "Fibonacci yazdir" |
| `planner` | Gorevi alt adimlara boler | "X ve Y yap" |
| `reviewer` | Kod inceleme | "Su kodu incele: ..." |
| `summarizer` | Ozet cikarma | "Bu metni ozetle: ..." |
| `router` | Hibrit yonlendirme | (Otomatik) |

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

### Auth

# Login
curl -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d "{\"username\":\"admin\",\"password\":\"admin123\"}"

# Response: {"access_token": "eyJ...", "token_type": "bearer"}

### Soru Sor

curl -X POST http://localhost:8000/api/ask -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" -d "{\"message\": \"Python nedir?\", \"agent\": \"auto\"}"

### Ornek Sorular

- `{"message": "2026 Dunya Kupasi sampiyonu kim?", "agent": "auto"}`
- `{"message": "Fibonacci yazdir", "agent": "auto"}`
- `{"message": "Sistem durumu nedir?", "agent": "auto"}`

## Mimari

Kullanici (Web UI / REST / WebSocket)
   |
FastAPI (api/main.py)
   |
Router (regex + LLM)
   |
MessageBus (in-memory | Redis)
   |
Agent'lar (researcher, llm, system, coder, planner, reviewer, summarizer)
   |
Groq LLM + Web Search + psutil + subprocess

## Katmanlar

- core/ - BaseAgent, MessageBus, RedisMessageBus, Registry, Auth, Security, Memory
- agents/ai/ - LLMAgent, PlannerAgent, ResearcherAgent, CoderAgent, ReviewerAgent, SummarizerAgent, RouterAgent
- agents/devops/ - SystemAgent
- tools/ - GroqLLMClient, Web Search, Code Runner, System Info
- api/ - FastAPI routes (REST + WebSocket + Auth)
- static/ - Web arayuzu (HTML/CSS/JS)
- tests/ - 39 pytest testleri

## Teknolojiler

- **Backend:** Python 3.11, FastAPI, Uvicorn, Pydantic
- **LLM:** Groq (openai/gpt-oss-120b, llama-3.1-8b-instant)
- **Auth:** python-jose (JWT), bcrypt
- **Web Search:** ddgs
- **Cache:** Redis (Pub/Sub)
- **Database:** SQLite (kalici volume)
- **Container:** Docker, docker-compose
- **CI/CD:** GitHub Actions
- **Cloud:** Railway
- **Test:** pytest, pytest-asyncio
- **Logging:** structlog
- **Monitoring:** psutil

## Guvenlik

- JWT authentication (bcrypt sifre hash)
- Rate limiting (30 istek/dk, kullanici bazli)
- Input validation (bos/uzun/tehlikeli mesaj reddi)
- CORS kisitlama
- .env dosyasi .gitignore'da
- CoderAgent: AST analizi + sandbox

## Test

uv run pytest -v
# 39 passed in ~7s

## Lisans

MIT