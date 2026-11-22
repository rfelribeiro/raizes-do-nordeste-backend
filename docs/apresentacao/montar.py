#!/usr/bin/env python3
"""Gera docs/apresentacao/dados/mercado.js a partir de dados/mercado.json.

Por que existe: a apresentação é aberta por file://, onde fetch() falha. Então os dados de
mercado e as contagens de decisões entram como <script src> com variáveis globais.

Uso (na raiz do repositório):  python3 docs/apresentacao/montar.py

- window.MERCADO  = dados/mercado.json (se não existir, usa dados/mercado-exemplo.json, marcado PENDENTE)
- window.DECISOES = contagem de decisões por origem em docs/uso-de-ia/decisoes.md
- window.DASHBOARD = imagens docs/dados/evidencias/dashboard-*.png (slide 12); vazio mantém o espaço reservado
"""

import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
ORIGENS = {"🧑": "humana", "🤝": "conjunta", "🤖": "ia"}


def contar_decisoes() -> dict:
    cont = {v: 0 for v in ORIGENS.values()}
    for linha in (RAIZ / "docs/uso-de-ia/decisoes.md").read_text(encoding="utf-8").splitlines():
        if not re.match(r"\|\s*D-\d+", linha):
            continue
        colunas = [c.strip() for c in linha.strip().strip("|").split("|")]
        if len(colunas) < 4:
            continue
        achadas = [nome for emoji, nome in ORIGENS.items() if emoji in colunas[3]]
        if len(achadas) == 1:
            cont[achadas[0]] += 1
        elif achadas:  # mais de uma origem na mesma decisão (ex.: D-053): conta como mista
            cont["mista"] = cont.get("mista", 0) + 1
    cont["total"] = sum(cont.values())
    return cont


def listar_dashboard() -> list:
    pasta = RAIZ / "docs/dados/evidencias"
    return ["../dados/evidencias/" + p.name for p in sorted(pasta.glob("dashboard-*.png"))]


def main() -> int:
    fonte = AQUI / "dados/mercado.json"
    pendente = not fonte.exists()
    if pendente:
        fonte = AQUI / "dados/mercado-exemplo.json"
        print("AVISO: dados/mercado.json não existe; usando dados de exemplo (PENDENTE).", file=sys.stderr)
    mercado = json.loads(fonte.read_text(encoding="utf-8"))
    if pendente:
        mercado["pendente"] = True
    decisoes = contar_decisoes()
    saida = AQUI / "dados/mercado.js"
    saida.write_text(
        "/* Gerado por montar.py; não edite à mão. */\n"
        f"window.MERCADO = {json.dumps(mercado, ensure_ascii=False, indent=1)};\n"
        f"window.DECISOES = {json.dumps(decisoes, ensure_ascii=False)};\n"
        f"window.DASHBOARD = {json.dumps(listar_dashboard())};\n",
        encoding="utf-8",
    )
    print(f"OK: {saida.relative_to(RAIZ)} (decisões: {decisoes}; imagens do painel: {len(listar_dashboard())})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
