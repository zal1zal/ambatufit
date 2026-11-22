# AmbatuFit STB Core Service Dockerfile
# Optimized for STB ARM & x86_64, strictly lightweight (no AI/ML models on STB)
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install lightweight backend dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user and persistent data dir
RUN addgroup --system --gid 1001 ambatugroup && \
    adduser --system --uid 1001 --ingroup ambatugroup ambatuuser && \
    mkdir -p /data && chown -R ambatuuser:ambatugroup /data

# Copy core service code, reviewed rule assets, and seed script ONLY
COPY app/ ./app/
COPY rules/ ./rules/
COPY scripts/seed_demo.py ./scripts/seed_demo.py

USER ambatuuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
