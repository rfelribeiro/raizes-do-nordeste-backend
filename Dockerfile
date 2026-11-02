# syntax=docker/dockerfile:1
# Multi-stage: base -> dev (usado pelo docker compose) -> runtime (produção).
ARG PYTHON_VERSION=3.14.10

FROM python:${PYTHON_VERSION}-slim AS base
ARG UID=1000
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src
WORKDIR /app
# Usuário não-root; o UID é ajustável para casar com o do host (arquivos gerados em volumes).
RUN useradd --create-home --uid "${UID}" app

FROM base AS dev
ENV RUFF_CACHE_DIR=/tmp/ruff_cache \
    MYPY_CACHE_DIR=/tmp/mypy_cache
COPY requirements-dev.lock ./
RUN pip install -r requirements-dev.lock
# O código-fonte é montado como volume pelo docker-compose (reload automático).
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
USER app
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "raizes.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--reload", "--no-access-log"]

FROM base AS runtime
COPY requirements.lock ./
RUN pip install -r requirements.lock
COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
USER app
EXPOSE 8000
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "raizes.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
