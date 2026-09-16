# CV Ozeti - Multi-Agent System

## Proje Adi
Multi-Agent System

## Sure
1 gun (16 Eylul 2026) - 0'dan production'a

## Aciklama
7 agent'li, dagitik, bulutta calisan multi-agent sistemi. Web arayuzu, REST API, WebSocket, Docker, CI/CD.

## Kullanilan Teknolojiler
- Backend: Python 3.11, FastAPI, Uvicorn, Pydantic
- LLM: Groq (openai/gpt-oss-120b)
- Async: asyncio, redis.asyncio
- Container: Docker, docker-compose
- Cache: Redis (Pub/Sub)
- CI/CD: GitHub Actions
- Cloud: Railway
- Test: pytest (31 test)
- Frontend: HTML/CSS/JavaScript
- Logging: structlog, psutil, ddgs

## Onemli Ozellikler
1. 7 Agent: researcher, llm, system, coder, planner, reviewer, summarizer
2. Multi-Agent Pipeline: Planner + N agent isbirligi (POST /api/team)
3. RAG: Web arama + LLM ozetleme, kaynak gosterir
4. Kod Calistirma: LLM kod yazar, AST guvenlik kontrolu, sandbox'ta calistirir
5. Dagitik: Redis bus ile birden fazla process/container
6. WebSocket: Canli cevap akisi
7. Web UI: Modern chat arayuzu
8. Otomatik Deploy: GitHub -> Railway (42 saniye)
9. Healthcheck: Docker + Railway
10. API Docs: Swagger UI + ReDoc

## Basarilar
- 31 unit test (hepsi geciyor)
- 18 commit GitHub'da
- ~4500 satir kod
- CI/CD yesil rozet
- Bulut deploy canli
- Public URL erisilebilir

## Canli Demo
https://multi-agent-system-production-9301.up.railway.app

## GitHub
https://github.com/pekdemirengin-ops/multi-agent-system

## Ogrenilen Beceriler
- Multi-agent mimarisi tasarimi
- Async Python (asyncio, FastAPI)
- Docker + docker-compose
- Redis Pub/Sub
- CI/CD (GitHub Actions)
- Bulut deployment (Railway)
- LLM prompt engineering
- Sandbox guvenligi (AST)
- Web frontend
- Git workflow

## CV Icin Kisa Metin

Multi-Agent System - FastAPI + Docker + Redis + Groq LLM tabanli, 7 agent'li dagitik sistem. Web arayuzu, REST API, WebSocket, 31 test, CI/CD. Bulutta canli (Railway).
Canli: https://multi-agent-system-production-9301.up.railway.app

## CV Icin Orta Metin

Multi-Agent System (Kisisel Proje, 2026)
7 agent'li (researcher, coder, system, planner, reviewer, summarizer, llm), dagitik multi-agent sistemi.
FastAPI + WebSocket + Redis Pub/Sub + Docker + Groq LLM.
Web arayuzu, REST API, 31 unit test, CI/CD (GitHub Actions), bulut deploy (Railway).