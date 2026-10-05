# Backend image only — connects to the MariaDB/FreeRADIUS that already run
# on the target host (see CLAUDE.md "Infrastructure"). Point DB_HOST at that
# host's reachable address (e.g. the Docker host gateway), never "localhost".
FROM python:3.12-slim AS builder
WORKDIR /app

# asyncmy and bcrypt are C extensions; build-essential covers platforms
# without a prebuilt wheel (e.g. arm64).
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY app ./app
RUN python -m venv /venv \
    && /venv/bin/pip install --no-cache-dir --upgrade pip \
    && /venv/bin/pip install --no-cache-dir .

FROM python:3.12-slim AS runtime
WORKDIR /app

# radclient, used for PoD/CoA (ENABLE_POD/ENABLE_COA) — see
# app/services/radclient.py and RADCLIENT_PATH in .env.example.
RUN apt-get update && apt-get install -y --no-install-recommends freeradius-utils \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser

COPY --from=builder /venv /venv
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh && chown -R appuser:appuser /app

USER appuser
ENV PATH="/venv/bin:${PATH}"
EXPOSE 8001
ENTRYPOINT ["./docker-entrypoint.sh"]
