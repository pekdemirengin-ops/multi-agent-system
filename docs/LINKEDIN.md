# LinkedIn Postu

## Kisa Versiyon

Bugun 8 agent'li, production-grade bir multi-agent sistemi yaptim.

Ozellikler:
- FastAPI + WebSocket + Redis + Docker
- JWT auth + rate limiting
- Kalici volume (Railway)
- Web arayuzu (chat + ses + mobil)
- Hibrit router (regex 0ms + LLM fallback)
- 39 test + CI/CD

Canli: https://multi-agent-system-production-9301.up.railway.app

#Python #FastAPI #Docker #LLM #AI #MultiAgent #Groq

---

## Uzun Versiyon

Merhaba LinkedIn!

Bugun sizlerle tek bir gun icinde yaptigim bir projeyi paylasmak istiyorum:
**Multi-Agent System** - 8 agent'li, production-grade bir AI sistemi.

### Ne yapiyor?

7 farkli uzman agent + 1 router:
- researcher: Web'de arastirip kaynakli cevap verir
- llm: Genel sohbet ve tanimlar
- coder: Kod yazip calistirir
- system: CPU/RAM/disk izler
- planner: Karmasik gorevleri planlar
- reviewer: Kod inceler
- summarizer: Ozet cikarir

Router, soruyu analiz edip dogru agent'i secer.

### Teknik Ozellikler

**Backend:**
- Python 3.11 + FastAPI + Uvicorn
- Groq LLM (ucretsiz tier)
- JWT authentication + bcrypt
- Rate limiting (30 istek/dk)
- SQLite hafiza (kalici volume)
- Redis Pub/Sub (dagitik)

**Frontend:**
- HTML/CSS/JS (vanilla)
- Login + Register + Token yonetimi
- Sohbet gecmisi (otomatik yukleme)
- Sesli kullanim (STT + TTS)
- Mobil uyumlu

**DevOps:**
- Docker + docker-compose
- Railway (otomatik deploy)
- GitHub Actions (CI/CD)
- Kalici volume (500 MB)

### Performans

- Router: 0 ms (regex) / 298 ms (LLM fallback)
- Toplam: ~500 ms (regex), ~4s (LLM)
- 39 test geciliyor

### Ogrendiklerim

1. Hibrit router (regex + LLM) cok hizli
2. Kalici volume production icin sart
3. Rate limiting cloud'da farkli calisiyor
4. LLM prompt engineering kritik
5. Web arayuzu olmayan API yarim

### Canli Demo

https://multi-agent-system-production-9301.up.railway.app

Giris: admin / admin123

Kodu inceleyebilirsiniz:
https://github.com/pekdemirengin-ops/multi-agent-system

#Python #FastAPI #Docker #LLM #AI #MultiAgent #Groq #WebDevelopment #Portfolio

---

## Kisa Tweet (280 karakter)

8 agent'li multi-agent sistemi yaptim!

FastAPI + Docker + Redis + Groq LLM
JWT auth + rate limiting
Kalici volume + Web arayuzu
Hibrit router (0ms)
39 test + CI/CD

Canli: https://multi-agent-system-production-9301.up.railway.app

#AI #Python #FastAPI