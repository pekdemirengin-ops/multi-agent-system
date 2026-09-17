from pathlib import Path

readme_path = Path("README.md")
content = readme_path.read_text(encoding="utf-8")

# 1) Canli Demo bolumunu guncelle
old_demo = """## Canli Demo

**[multi-agent-system-production-9301.up.railway.app](https://multi-agent-system-production-9301.up.railway.app)**

- Giris: `admin` / `admin123`
- 8 agent, web arayuzu, mobil uyumlu
- Sesli kullanim (MIC + TTS)
- Sohbet gecmisi (kalici volume)"""

new_demo = """## Canli Demo

**[multi-agent-system-production-9301.up.railway.app](https://multi-agent-system-production-9301.up.railway.app)**

- Giris: `admin` / `admin123`
- **15 agent**, web arayuzu, mobil uyumlu
- **Multi-user:** Kayit ol, giris yap, rol yonetimi (admin/user)
- **Admin paneli:** Kullanici listesi, rol degistirme, silme
- Sesli kullanim (MIC + TTS)
- **Streaming:** SSE ile kelime kelime cevap
- **Guvenlik modu:** Log tarama (15+ tehdit)
- Sohbet gecmisi (PostgreSQL + kalici volume)"""

if old_demo in content:
    content = content.replace(old_demo, new_demo, 1)
    print("OK: Canli Demo guncellendi")

# 2) Ozellikler > AI & Agent bolumunu guncelle
old_ai = """### AI & Agent
- **8 Agent:** researcher, llm, system, coder, planner, reviewer, summarizer, router
- **Hibrit Router:** Regex (0ms) + LLM fallback
- **RAG:** Web search (ddgs) + LLM ozetleme
- **Kod Calistirma:** LLM kod yazar, guvenli sandbox'ta calistirir
- **Sistem Izleme:** CPU, RAM, disk, uptime
- **Multi-Agent Pipeline:** Planner + N agent isbirligi (`/api/team`)"""

new_ai = """### AI & Agent
- **15 Agent:** researcher, llm, coder, planner, reviewer, summarizer, router, system, log_watcher, alert, email, approval, npc, pathfinder, api_collector
- **Hibrit Router:** Regex (0ms) + LLM fallback
- **Akilli Arastirma:** LLM'siz + yil ekleme + agresif puanlama
- **RAG:** Web search (ddgs) + LLM ozetleme
- **Kod Calistirma:** LLM kod yazar, guvenli sandbox'ta calistirir
- **Sistem Izleme:** CPU, RAM, disk, uptime
- **Multi-Agent Pipeline:** Planner + N agent isbirligi (`/api/team`)
- **Game AI:** NPC (kisilik) + Pathfinding (A*)
- **Security Agent:** LogWatcher + Alert (15+ tehdit pattern)"""

if old_ai in content:
    content = content.replace(old_ai, new_ai, 1)
    print("OK: AI & Agent guncellendi")

# 3) Backend bolumunu guncelle (multi-user + PostgreSQL)
old_backend = """### Backend
- **FastAPI:** REST + WebSocket
- **JWT Authentication:** Token bazli guvenli erisim
- **Rate Limiting:** 30 istek/dk (kullanici bazli)
- **Input Validation:** Bos/tehlikeli mesaj reddi
- **CORS:** Kisitlanmis origin'ler
- **SQLite Hafiza:** Konusma gecmisi
- **Redis Bus:** Dagitik mesajlasma (opsiyonel)"""

new_backend = """### Backend
- **FastAPI:** REST + WebSocket + SSE streaming
- **JWT Authentication:** Token bazli guvenli erisim (role claim)
- **Multi-User:** Kayit, giris, rol sistemi (admin/user)
- **Admin API:** Kullanici listesi, silme, rol guncelleme
- **Rate Limiting:** 30 istek/dk (kullanici bazli)
- **Input Validation:** Bos/tehlikeli mesaj reddi
- **CORS:** Kisitlanmis origin'ler
- **PostgreSQL + SQLite fallback:** Konusma + kullanici deposu
- **Redis Bus:** Dagitik mesajlasma (opsiyonel)
- **Kalici Kullanici Deposu:** bcrypt + PostgreSQL"""

if old_backend in content:
    content = content.replace(old_backend, new_backend, 1)
    print("OK: Backend guncellendi")

# 4) Frontend bolumunu guncelle
old_frontend = """### Frontend
- **Modern Chat UI:** HTML/CSS/JS
- **Login/Register:** JWT token yonetimi
- **Sohbet Gecmisi:** Otomatik yukleme
- **Sesli Kullanim:** Web Speech API (STT + TTS)
- **Mobil Uyumlu:** Responsive tasarim"""

new_frontend = """### Frontend
- **Modern Chat UI:** HTML/CSS/JS
- **Admin Paneli:** Kullanici yonetimi (liste, rol, sil)
- **Login/Register:** JWT token yonetimi
- **5 Web Modu:** Auto, CANLI (streaming), GUVENLIK, MIC, SES
- **Sohbet Gecmisi:** Otomatik yukleme
- **Sesli Kullanim:** Web Speech API (STT + TTS)
- **Mobil Uyumlu:** Responsive tasarim"""

if old_frontend in content:
    content = content.replace(old_frontend, new_frontend, 1)
    print("OK: Frontend guncellendi")

# 5) DevOps bolumunu guncelle
old_devops = """### DevOps
- **Docker:** `docker compose up` ile tek komut
- **Railway:** Otomatik deploy (GitHub webhook)
- **Kalici Volume:** 500 MB (SQLite)
- **CI/CD:** GitHub Actions
- **Healthcheck:** Docker + Railway"""

new_devops = """### DevOps
- **Docker:** `docker compose up` ile tek komut
- **Railway:** Otomatik deploy (GitHub webhook)
- **PostgreSQL:** Production veritabani (Railway managed)
- **Kalici Volume:** 500 MB (SQLite fallback + data)
- **CI/CD:** GitHub Actions
- **Test Suite:** 80 test (pytest + async)
- **Healthcheck:** Docker + Railway"""

if old_devops in content:
    content = content.replace(old_devops, new_devops, 1)
    print("OK: DevOps guncellendi")

readme_path.write_text(content, encoding="utf-8")
print()
print(f"README guncellendi: {len(content)} karakter")
