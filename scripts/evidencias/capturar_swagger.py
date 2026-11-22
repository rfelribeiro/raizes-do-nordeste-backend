r"""Captura imagens do Swagger (/docs) como evidência de funcionamento.

Uso (com `make up`, `make migrate` e `make seed` já executados), na raiz do repositório:

    docker run --rm --network host --user "$(id -u)" -e HOME=/tmp \
      -e BASE_URL=http://localhost:8080 \
      -v "$PWD":/work -w /work mcr.microsoft.com/playwright/python:v1.49.1-noble \
      sh -c 'pip install -q --user playwright==1.49.1 &&\
        python3 scripts/evidencias/capturar_swagger.py'

Troque a porta de BASE_URL pela API_PORT do seu .env.

Variáveis: BASE_URL (padrão http://localhost:8080), SAIDA (padrão docs/testes/evidencias).
A senha de demonstração (fictícia) é lida de scripts/seed.py. Os tokens ficam só em memória:
nunca são gravados em arquivo nem impressos, e o comando curl do Swagger (que os exibiria) é
ocultado nas imagens.
"""

import json
import os
import re
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE = os.environ.get("BASE_URL", "http://localhost:8080")
SAIDA = Path(os.environ.get("SAIDA", "docs/testes/evidencias"))
RAIZ = Path(__file__).resolve().parents[2]
SENHA = re.search(r'DEMO_PASSWORD = "([^"]+)"', (RAIZ / "scripts/seed.py").read_text()).group(1)

UNIDADE = "00000000-0000-4000-8000-000000000101"
TAPIOCA = "00000000-0000-4000-8000-000000000301"  # estoque alto
CARNE_SOL = "00000000-0000-4000-8000-000000000304"  # estoque 2
API = "/api/v1"


def _http(metodo: str, caminho: str, corpo: dict | None = None, token: str | None = None) -> dict:
    cab = {"Content-Type": "application/json"}
    if token:
        cab["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        BASE + caminho,
        data=json.dumps(corpo).encode() if corpo is not None else None,
        headers=cab,
        method=metodo,
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def login(email: str) -> str:
    return _http("POST", f"{API}/auth/login", {"email": email, "senha": SENHA})["accessToken"]


def fechar_modal(page: Page) -> None:
    page.locator(".modal-ux .close-modal, button.btn-done").first.click()


def autorizar(page: Page, token: str, arquivo: str | None = None) -> None:
    page.locator(".btn.authorize").first.click()
    modal = page.locator(".dialog-ux .modal-ux")
    modal.locator("input").first.fill(token)
    modal.locator("button.modal-btn.auth").first.click()
    if arquivo:
        page.wait_for_timeout(300)
        modal.screenshot(path=str(SAIDA / arquivo))
    fechar_modal(page)


def desautorizar(page: Page) -> None:
    page.locator(".btn.authorize").first.click()
    page.locator(".modal-ux button.modal-btn.auth").first.click()
    fechar_modal(page)


def bloco(page: Page, metodo: str, caminho: str):
    return page.locator(
        f".opblock-{metodo}:has(.opblock-summary-path[data-path='{caminho}'])"
    ).first


def executar(page: Page, metodo: str, caminho: str, corpo: str | None, params: dict, arquivo: str):
    b = bloco(page, metodo, caminho)
    if "is-open" not in (b.get_attribute("class") or ""):
        b.locator(".opblock-summary-control").click()
    if b.locator("button.try-out__btn.cancel").count():
        b.locator("button.try-out__btn.cancel").click()  # limpa a resposta anterior
    b.locator("button.try-out__btn:not(.cancel):not(.reset)").click()
    for nome, valor in params.items():
        b.locator(f"tr[data-param-name='{nome}'] input").fill(valor)
    if corpo is not None:
        b.locator("textarea.body-param__text").fill(corpo)
    b.locator("button.execute").click()
    b.locator(".live-responses-table .response").first.wait_for()
    page.wait_for_timeout(500)
    b.scroll_into_view_if_needed()
    b.screenshot(path=str(SAIDA / arquivo))
    codigo = b.locator(".live-responses-table tbody .response-col_status").first.inner_text()
    b.locator(".opblock-summary-control").click()  # recolhe para o próximo não empilhar
    return codigo.split()[0]


def corpo_pedido(produto: str, qtd: int, canal: bool = True) -> str:
    d = {"unidadeId": UNIDADE, "itens": [{"produtoId": produto, "quantidade": qtd}]}
    if canal:
        d["canalPedido"] = "APP"
    return json.dumps(d, indent=2)


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    tok_cliente = login("cliente@exemplo.com")
    tok_admin = login("admin@exemplo.com")
    # Pedido preparado por API para a captura do pagamento (a captura do 201 usa a interface).
    pedido_pag = _http("POST", f"{API}/pedidos", json.loads(corpo_pedido(TAPIOCA, 1)), tok_cliente)[
        "id"
    ]

    with sync_playwright() as p:
        nav = p.chromium.launch()
        page = nav.new_page(viewport={"width": 1400, "height": 900})
        page.goto(f"{BASE}/docs")
        page.wait_for_selector(".opblock")
        # Oculta o comando curl, que exibiria o token completo.
        page.add_style_tag(content=".curl-command, .curl-command + * {display:none !important}")
        page.add_style_tag(content=".models {display:none !important}")  # só os endpoints
        page.screenshot(path=str(SAIDA / "swagger-visao-geral.png"), full_page=True)
        # Nas demais capturas, oculta a tabela estática de respostas (mostra só a resposta real).
        page.add_style_tag(
            content=".responses-table:not(.live-responses-table) {display:none !important}"
        )

        autorizar(page, tok_cliente, "swagger-autorizado.png")

        r = executar(
            page,
            "post",
            f"{API}/pedidos",
            corpo_pedido(TAPIOCA, 1),
            {},
            "swagger-criar-pedido-201.png",
        )
        print("criar pedido:", r)
        r = executar(
            page,
            "post",
            f"{API}/pedidos",
            corpo_pedido(TAPIOCA, 1, canal=False),
            {},
            "swagger-erro-422-canal.png",
        )
        print("422 canal:", r)
        r = executar(
            page,
            "post",
            f"{API}/pedidos",
            corpo_pedido(CARNE_SOL, 3),
            {},
            "swagger-erro-409-estoque.png",
        )
        print("409 estoque:", r)
        for tok, arq in (
            ("tok_recusado", "swagger-pagamento-recusado.png"),
            ("tok_aprovado", "swagger-pagamento-aprovado.png"),
        ):
            corpo = json.dumps({"formaPagamento": "PIX", "tokenPagamento": tok}, indent=2)
            r = executar(
                page,
                "post",
                f"{API}/pedidos/{{order_id}}/pagamentos",
                corpo,
                {"order_id": pedido_pag},
                arq,
            )
            print(tok, r)

        desautorizar(page)
        autorizar(page, tok_admin)
        r = executar(
            page,
            "get",
            f"{API}/auditoria",
            None,
            {"acao": "PEDIDO_CRIADO"},
            "swagger-auditoria.png",
        )
        print("auditoria:", r)
        nav.close()


if __name__ == "__main__":
    main()
