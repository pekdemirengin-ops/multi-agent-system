# CV Ozeti - Multi-Agent System

## Proje Adi
Multi-Agent System

## Sure
1 gun (16 Eylul 2026) - 0'dan production'a

## Aciklama
8 agent'li, dagitik, bulutta calisan multi-agent sistemi.
FastAPI + WebSocket + Redis + Docker + Groq LLM + Railway.

## Kullanilan Teknolojiler
- Backend: Python 3.11, FastAPI, Uvicorn, Pydantic
- LLM: Groq (openai/gpt-oss-120b, llama-3.1-8b-instant)
- Auth: python-jose (JWT), bcrypt
- Web Search: ddgs (DuckDuckGo)
- Cache: Redis (Pub/Sub)
- Database: SQLite (kalici volume)
- Container: Docker, docker-compose
- CI/CD: GitHub Actions
- Cloud: Railway (otomatik deploy)
- Test: pytest, pytest-asyncio (39 test)
- Frontend: HTML/CSS/JavaScript (vanilla)
- Monitoring: psutil, structlog
- Async: asyncio, redis.asyncio

## Onemli Ozellikler
1. 8 Agent: researcher, llm, system, coder, planner, reviewer, summarizer, router
2. Hibrit Router: Regex (0ms) + LLM fallback
3. RAG: Web arama + LLM ozetleme, kaynak gosterir
4. Kod Calistirma: LLM kod yazar, AST guvenlik kontrolu, sandbox
5. JWT Authentication + bcrypt
6. Rate Limiting (30 istek/dk)
7. Input Validation
8. CORS kisitlama
9. Kalici Volume (500 MB, SQLite)
10. WebSocket (canli cevap akisi)
11. Multi-Agent Pipeline (POST /api/team)
12. Web UI (login + chat + ses + gecmis)
13. Sesli Kullanim (STT + TTS)
14. Mobil Uyumlu
15. Otomatik Deploy (GitHub -> Railway)

## Basarilar
- 39 unit test (hepsi geciyor)
- 42+ commit GitHub'da
- ~5000 satir kod
- CI/CD yesil rozet
- Bulut deploy canli
- Public URL erisilebilir
- Volume kalici (38 MB)

## Canli Demo
https://multi-agent-system-production-9301.up.railway.app
Giris: admin / admin123

## GitHub
https://github.com/pekdemirengin-ops/multi-agent-system

## Ogrenilen Beceriler
- Multi-agent mimarisi tasarimi
- Hibrit router (regex + LLM)
- Async Python (asyncio, FastAPI)
- Docker + docker-compose
- Redis Pub/Sub
- CI/CD (GitHub Actions)
- Bulut deployment (Railway)
- JWT authentication + bcrypt
- Rate limiting (kullanici bazli)
- LLM prompt engineering
- Sandbox guvenligi (AST)
- Web frontend (HTML/CSS/JS)
- Web Speech API (STT + TTS)
- Kalici volume yonetimi
- Git workflow

## CV Icin Kisa Metin (2 satir)

Multi-Agent System - FastAPI + Docker + Redis + Groq LLM tabanli, 8 agent'li dagitik sistem.
Hibrit router (0ms), JWT auth, rate limiting, kalici volume, web arayuzu, 39 test, CI/CD, bulut deploy.
Canli: https://multi-agent-system-production-9301.up.railway.app

## CV Icin Orta Metin (4 satir)

Multi-Agent System (Kisisel Proje, 2026)
8 agent'li (researcher, llm, system, coder, planner, reviewer, summarizer, router), dagitik multi-agent sistemi.
FastAPI + WebSocket + Redis Pub/Sub + Docker + Groq LLM + JWT auth + Railway.
Hibrit router (regex 0ms), kalici volume (SQLite), web arayuzu (chat + ses + gecmis), 39 test, CI/CD.
Canli: https://multi-agent-system-production-9301.up.railway.app

## Mulakat Icin Hazir Cevaplar

### "Bu projede ne yaptin?"
"Sifirdan production-grade bir multi-agent sistemi yazdim. 8 farkli agent, FastAPI backend, JWT auth, rate limiting, kalici volume, web arayuzu, mobil uyumlu. Docker'ladim, Railway'e deploy ettim, CI/CD kurdum. 42 commit, 39 test."

### "En zor kisim neydi?"
"Windows'ta WSL 2.6.3 + Docker Desktop kurulumu. Windows 10, WSL 2.7.x'i desteklemiyordu, manuel olarak 2.6.3 kurmam gerekti."

### "Hibrit router nedir?"
"Router, soruyu analiz edip hangi agent'a gidecegini secer. Once regex ile hizli kontrol (0ms), eslesme yoksa LLM'e sorar (298ms). Bu, %80 sorulari 0ms'de cevaplar."

### "Olceklenebilir mi?"
"Evet. Redis Pub/Sub sayesinde agent'lar farkli container'larda calisabilir. Su an tek container'da, ama yatay olarak olceklenebilir."

### "Guvenlik nasil?"
"JWT auth (bcrypt hash), rate limiting (30/dk), input validation, CORS kisitlama, .env gitignore'da, CoderAgent AST analizi + sandbox."