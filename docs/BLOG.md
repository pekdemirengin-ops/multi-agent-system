# Multi-Agent Sistemi Nasil Yaptim?

Bu yazi, tek bir gun icinde sifirdan production-ready bir multi-agent sistemi nasil insa ettigimi anlatir.

Canli demo: https://multi-agent-system-production-9301.up.railway.app

## Problem

Modern LLM uygulamalari tek bir agent'a bagli. Ama gercek dunyada:
- Farkli gorevler farkli uzmanlik ister
- Bilgi toplama + kod yazma + analiz ayni anda gerekebilir
- Tek bir LLM cagrisi cogu zaman yetersiz

Cozum: Multi-agent mimarisi. Her agent bir gorevde uzmanlasir, birbirleriyle konusur.

## Mimari

Kullanici (Web UI)
   |
   v
FastAPI (REST + WebSocket)
   |
   v
MessageBus (in-memory | Redis)
   |
   +---> ResearcherAgent (web arama + RAG)
   +---> CoderAgent (kod yaz + calistir)
   +---> SystemAgent (CPU/RAM/disk)
   +---> PlannerAgent (gorevi bol)
   +---> ReviewerAgent (kod incele)
   +---> SummarizerAgent (ozet cikar)
   +---> LLMAgent (genel sohbet)

## 7 Agent Nasil Calisir?

### 1. BaseAgent (Soyut Sinif)

Tum agent'lar bundan turer. Iki metod:
- handle(message) - gelen mesaji isle
- send(receiver, content) - mesaj gonder

### 2. MessageBus (In-Memory)

Agent'lar arasi iletisim. Async Python ile:
- publish(message) - mesaj yayinla
- subscribe(topic, callback) - abone ol
- Broadcast, direct mesaj, topic destegi

### 3. RedisMessageBus (Dagitik)

Ayni API, ama Redis Pub/Sub uzerinden. Boylece agent'lar farkli process/container'larda calisabilir.

### 4. Uzman Agent'lar

- ResearcherAgent: DuckDuckGo'da arar, LLM ile ozetler, kaynaklari doner
- CoderAgent: LLM kod yazar, AST ile guvenlik kontrolu yapar, subprocess'te calistirir
- SystemAgent: psutil ile CPU/RAM/disk olcer, LLM'e yorumlatir
- PlannerAgent: Gorevi alt adimlara boler (JSON doner)
- ReviewerAgent: Kodu inceler, oneriler sunar
- SummarizerAgent: Uzun metni ozetler

## Multi-Agent Pipeline

POST /api/team endpoint'i:

1. Planner gorevi alt adimlara boler
2. Her adim ilgili agent'a gonderilir
3. Sonuclar toplanir
4. Birlesik cevap doner

## Guvenlik

CoderAgent AST analizi yapar:
- Yasakli import: os, subprocess, requests
- Yasakli fonksiyon: eval, exec
- Timeout: 10 saniye
- Ayri process (sandbox)

## Tech Stack

- Backend: FastAPI + Uvicorn
- LLM: Groq (openai/gpt-oss-120b)
- Async: asyncio
- Cache: Redis
- Container: Docker + docker-compose
- CI/CD: GitHub Actions + Railway
- Test: pytest (31 test)
- Frontend: Vanilla HTML/CSS/JS

## Ogrendiklerim

1. Async Python multi-agent sistemler icin mukemmel
2. Redis Pub/Sub dagitik agent'lar icin basit ve guclu
3. AST analizi LLM kodunu guvene almak icin pratik
4. Docker ve CI/CD production-ready proje icin zorunlu
5. Web arayuzu olmayan API yarim kalmis demek
6. Prompt engineering LLM cagrilarinda kritik

## Sonuc

Tek bir gun icinde:
- 7-agent sistemi yazildi
- Docker'landi
- 31 test yazildi
- CI/CD kuruldu
- Buluta deploy edildi (Railway)
- Web arayuzu eklendi

Canli: https://multi-agent-system-production-9301.up.railway.app

## Kaynaklar

- GitHub: https://github.com/pekdemirengin-ops/multi-agent-system
- FastAPI: https://fastapi.tiangolo.com
- Groq: https://console.groq.com
- Railway: https://railway.app