r"""Captura imagens do painel Streamlit (mockup, dados fictícios) como evidência.

Uso (com `make dw-simulado` e `make dashboard` já executados), na raiz do repositório:

    docker run --rm --network host --user "$(id -u)" -e HOME=/tmp \
      -v "$PWD":/work -w /work mcr.microsoft.com/playwright/python:v1.49.1-noble \
      sh -c 'pip install -q --user playwright==1.49.1 &&\
        python3 scripts/evidencias/capturar_dashboard.py'

Variáveis: BASE_URL (padrão http://127.0.0.1:8501), SAIDA (padrão docs/dados/evidencias).
As imagens contêm apenas dados fictícios gerados por simulação.
"""

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8501")
SAIDA = Path(os.environ.get("SAIDA", "docs/dados/evidencias"))


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        nav = p.chromium.launch()
        # Streamlit rola dentro de um contêiner (full_page não funciona): usa viewport alto.
        page = nav.new_page(viewport={"width": 1500, "height": 2900})
        page.goto(BASE)
        page.wait_for_selector("text=Ranking por unidade", timeout=60000)
        page.wait_for_timeout(2500)  # deixa os gráficos terminarem de desenhar
        page.screenshot(path=str(SAIDA / "dashboard-visao-geral.png"))
        page.set_viewport_size({"width": 1500, "height": 1100})
        page.wait_for_timeout(1500)
        page.screenshot(path=str(SAIDA / "dashboard-topo.png"))
        nav.close()


if __name__ == "__main__":
    main()
