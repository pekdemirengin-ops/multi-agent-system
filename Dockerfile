# Python 3.11 tabanli imaj
FROM python:3.11-slim

# Ortam degiskenleri
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Calisma dizini
WORKDIR /app

# Sistem bagimliliklari (bazi paketler icin gerekli)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# uv'yi kur
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Once sadece pyproject.toml ve uv.lock kopyala (cache icin)
COPY pyproject.toml uv.lock ./

# Bagimliliklari kur (cache-friendly)
RUN uv sync --frozen --no-dev

# Uygulama kodunu kopyala
COPY core/ ./core/
COPY agents/ ./agents/
COPY tools/ ./tools/
COPY api/ ./api/

# PATH'e venv ekle
ENV PATH="/app/.venv/bin:$PATH"

# Port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Uygulamayi baslat
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]