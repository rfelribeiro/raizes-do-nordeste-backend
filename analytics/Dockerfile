# syntax=docker/dockerfile:1
# Imagem do pipeline analítico (dbt + DuckDB). Contexto de build: ./analytics
ARG PYTHON_VERSION=3.14.10

FROM python:${PYTHON_VERSION}-slim
ARG UID=1000
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/analytics \
    DBT_PROJECT_DIR=/app/analytics/dbt/raizes_dw \
    DBT_PROFILES_DIR=/app/analytics/dbt/raizes_dw \
    DBT_SEND_ANONYMOUS_USAGE_STATS=False
WORKDIR /app
# Usuário não-root; o UID casa com o do host para que ./data pertença ao usuário.
RUN useradd --create-home --uid "${UID}" app
COPY requirements.lock ./
RUN pip install -r requirements.lock
USER app
CMD ["dbt", "--version"]
