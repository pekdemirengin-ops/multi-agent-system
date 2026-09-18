# Multi-Agent System

![Tests](https://github.com/pekdemirengin-ops/multi-agent-system/actions/workflows/test.yml/badge.svg)

Moduler, dagitik multi-agent sistemi. FastAPI + WebSocket + Redis + Docker + LLM.

## Canli Demo

**[multi-agent-system-production-9301.up.railway.app](https://multi-agent-system-production-9301.up.railway.app)**

- Giris: `admin` / `admin123`
- **22 agent** (14 temel + 8 skill-based), web arayuzu, mobil uyumlu
- **Multi-user:** Kayit ol, giris yap, rol yonetimi (admin/user)
- **Admin paneli:** Kullanici listesi, rol degistirme, silme
- Sesli kullanim (MIC + TTS)
- **Streaming:** SSE ile kelime kelime cevap
- **Guvenlik modu:** Log tarama (15+ tehdit)
- Sohbet gecmisi (PostgreSQL + kalici volume)
- **Skill sistemi:** calculator, translation, file_operations
- **Multi-Agent Pipeline:** research, code, content, social, fact
- **Skill sistemi:** calculator, translation, file_operations
- **Multi-Agent Pipeline:** research, code, content, social, fact


## Istatistikler

| Metrik | Deger |
|--------|-------|
| Agent sayisi | **22** (14 temel + 8 skill-based) |
| Skill sayisi | **5** (calculator, translation, file, vs.) |
| Pipeline | **5** (research, code, content, social, fact) |
| API endpoint | **15+** |
| Web modu | **5 + Pipeline** (Auto, CANLI, GUVENLIK, MIC, SES) |
| Test | **80** (pytest + async) |
| Commit | **73+** |
| Veritabani | **PostgreSQL + SQLite fallback** |
| Deploy | **Railway (otomatik)** |
| Auth | **JWT + rol sistemi** |
| Guvenlik | **15+ tehdit pattern** |
| Streaming | **SSE (kelime kelime)** |

## API Endpoints

### Auth
- `POST /api/auth/register` - Yeni kullanici kaydi
- `POST /api/auth/login` - Giris (JWT doner)
- `GET  /api/auth/me` - Mevcut kullanici bilgisi
- `GET  /api/auth/users` - Kullanici listesi (admin)
- `DELETE /api/auth/users/{username}` - Kullanici sil (admin)
- `PATCH /api/auth/users/{username}/role` - Rol guncelle (admin)

### Agent
- `GET  /api/agents` - Agent listesi
- `POST /api/ask` - Agent'a soru sor
- `POST /api/stream` - Streaming cevap (SSE)
- `POST /api/team` - Multi-agent pipeline

### Sistem
- `GET  /api/health` - Sistem sagligi
- `GET  /api/memory/stats` - Hafiza istatistikleri
- `GET  /api/security/scan` - Log tarama

## Ozellikler

### AI & Agent
- **22 Agent:** researcher, llm, coder, planner, reviewer, summarizer, router, system, log_watcher, alert, email, approval, npc, pathfinder + **translator, calculator, file_manager, fact_checker, data_analyst, quiz_maker, email_composer, social_media**
- **5 Skill:** calculator, translation, file_operations, (base + registry)
- **5 Pipeline:** research, code, content, social, fact (multi-agent sirali calistirma)
- **Hibrit Router:** Regex (0ms) + LLM fallback
- **Akilli Arastirma:** LLM'siz + yil ekleme + agresif puanlama
- **RAG:** Web search (ddgs) + LLM ozetleme
- **Kod Calistirma:** LLM kod yazar, guvenli sandbox'ta calistirir
- **Sistem Izleme:** CPU, RAM, disk, uptime
- **Multi-Agent Pipeline:** Planner + N agent isbirligi (`/api/team`)
- **Game AI:** NPC (kisilik) + Pathfinding (A*)
- **Security Agent:** LogWatcher + Alert (15+ tehdit pattern)

### Backend
- **FastAPI:** REST + WebSocket + SSE streaming
- **JWT Authentication:** Token bazli guvenli erisim (role claim)
- **Multi-User:** Kayit, giris, rol sistemi (admin/user)
- **Admin API:** Kullanici listesi, silme, rol guncelleme
- **Rate Limiting:** 30 istek/dk (kullanici bazli)
- **Input Validation:** Bos/tehlikeli mesaj reddi
- **CORS:** Kisitlanmis origin'ler
- **PostgreSQL + SQLite fallback:** Konusma + kullanici deposu
- **Redis Bus:** Dagitik mesajlasma (opsiyonel)
- **Kalici Kullanici Deposu:** bcrypt + PostgreSQL

### Frontend
- **Modern Chat UI:** HTML/CSS/JS
- **Admin Paneli:** Kullanici yonetimi (liste, rol, sil)
- **Login/Register:** JWT token yonetimi
- **5 Web Modu:** Auto, CANLI (streaming), GUVENLIK, MIC, SES
- **Sohbet Gecmisi:** Otomatik yukleme
- **Sesli Kullanim:** Web Speech API (STT + TTS)
- **Mobil Uyumlu:** Responsive tasarim

### DevOps
- **Docker:** `docker compose up` ile tek komut
- **Railway:** Otomatik deploy (GitHub webhook)
- **PostgreSQL:** Production veritabani (Railway managed)
- **Kalici Volume:** 500 MB (SQLite fallback + data)
- **CI/CD:** GitHub Actions
- **Test Suite:** 80 test (pytest + async)
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