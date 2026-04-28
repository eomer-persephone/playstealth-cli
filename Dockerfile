# Dockerfile
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# System & Python Setup
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.playwright-browsers
ENV PLAYSTEALTH_STATE_DIR=/app/data/state
ENV PLAYSTEALTH_MANIFEST_PATH=/app/data/manifest.json
ENV PLAYSTEALTH_DOCKER=true

WORKDIR /app

# Abhängigkeiten installieren
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir -e '.[dev]'

# Playwright Chromium explizit im App-Dir cachen
RUN playwright install chromium

# App-Code kopieren
COPY . .

# Datenverzeichnis & Permissions
RUN mkdir -p /app/data && \
    chown -R pwuser:pwuser /app /app/data && \
    chmod -R 755 /app

# Non-Root User (Playwright Image bringt pwuser mit)
USER pwuser

# Entrypoint
# ENTRYPOINT not yet configured; use: docker run playstealth:ci python -m playstealth_cli --help
CMD ["python", "-m", "playstealth_cli", "--help"]
