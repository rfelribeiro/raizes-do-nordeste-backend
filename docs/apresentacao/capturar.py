r"""Captura todos os slides em 1920x1080 para docs/apresentacao/previas/slide-NN.png.

Uso, na raiz do repositório (precisa de internet para as Google Fonts; sem elas, usa a fonte local):

    docker run --rm --user "$(id -u)" -e HOME=/tmp -v "$PWD":/work -w /work \
      mcr.microsoft.com/playwright/python:v1.49.1-noble \
      sh -c 'pip install -q --user playwright==1.49.1 && python3 docs/apresentacao/capturar.py'
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

AQUI = Path(__file__).resolve().parent
SAIDA = AQUI / "previas"


def main() -> None:
    SAIDA.mkdir(exist_ok=True)
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pg = nav.new_page(viewport={"width": 1920, "height": 1080})
        erros = []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.on("console", lambda m: erros.append(m.text) if m.type == "error" else None)
        pg.goto((AQUI / "index.html").as_uri() + "#1")
        pg.wait_for_timeout(1500)
        total = pg.evaluate("document.querySelectorAll('.slide').length")
        for n in range(1, total + 1):
            pg.evaluate(f"location.hash = '#{n}'")
            pg.wait_for_timeout(600)
            pg.screenshot(path=str(SAIDA / f"slide-{n:02d}.png"))
        fontes = pg.evaluate("[...document.fonts].map(f => f.family + ':' + f.status)")
        print("slides:", total, "| fontes:", fontes)
        if erros:
            print("ERROS:", erros)
        nav.close()


if __name__ == "__main__":
    main()
