# syntax=docker/dockerfile:1
# Imagem do painel Streamlit (mockup). Contexto de build: ./dashboard
# Python 3.14.10 (o mesmo do restante do projeto): streamlit, pandas, pyarrow, numpy e duckdb
# publicam wheels para 3.14 (verificado no `make dashboard-lock` e neste build).
ARG PYTHON_VERSION=3.14.10

FROM python:${PYTHON_VERSION}-slim
ARG UID=1000
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_CLIENT_TOOLBAR_MODE=minimal \
    STREAMLIT_THEME_PRIMARY_COLOR=#2F5D50
WORKDIR /app/dashboard
# Usuário não-root; o UID casa com o do host.
RUN useradd --create-home --uid "${UID}" app
COPY requirements.lock ./
RUN pip install -r requirements.lock
COPY app.py unidades_mockup.csv ./
USER app
EXPOSE 8501
HEALTHCHECK --interval=10s --timeout=3s --retries=10 \
    CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=2)"
CMD ["streamlit", "run", "app.py"]
