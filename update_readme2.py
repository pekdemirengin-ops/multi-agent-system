from pathlib import Path

readme_path = Path("README.md")
content = readme_path.read_text(encoding="utf-8")

# Stats + API bolumunu ekle (Ozellikler'den once)
new_section = """
## Istatistikler

| Metrik | Deger |
|--------|-------|
| Agent sayisi | **15** |
| API endpoint | **11** |
| Web modu | **5** (Auto, CANLI, GUVENLIK, MIC, SES) |
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

"""

# "## Ozellikler" basligindan once ekle
marker = "## Ozellikler"
if marker in content:
    content = content.replace(marker, new_section + marker, 1)
    print("OK: Istatistikler + API Endpoints eklendi")
else:
    print("UYARI: '## Ozellikler' bulunamadi")

readme_path.write_text(content, encoding="utf-8")
print(f"README: {len(content)} karakter")
