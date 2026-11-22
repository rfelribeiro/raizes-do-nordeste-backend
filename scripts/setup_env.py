#!/usr/bin/env python3
"""Cria ou completa o .env a partir do .env.example, gerando segredos aleatórios.

- .env ausente: é criado com senha de banco, chave de pseudonimização e segredo JWT aleatórios.
- .env existente: NUNCA é sobrescrito; apenas chaves que faltam são acrescentadas ao final
  (com segredos aleatórios quando for o caso). Valores existentes não são alterados.
- Nunca imprime valores de segredos (apenas os NOMES das chaves acrescentadas).
"""

import re
import secrets
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / ".env.example"
TARGET = ROOT / ".env"

# Chaves cujo valor é um segredo gerado localmente (o valor do modelo é apenas um espaço vazio).
GERADORES: dict[str, Callable[[], str]] = {
    "POSTGRES_PASSWORD": lambda: secrets.token_urlsafe(24),
    "ANALYTICS_PSEUDONYM_KEY": lambda: secrets.token_hex(32),
    "JWT_SECRET": lambda: secrets.token_urlsafe(48),
}

LINHA_CHAVE = re.compile(r"^([A-Z][A-Z0-9_]*)=(.*)$")


def chaves_do_modelo(texto: str) -> dict[str, str]:
    encontradas: dict[str, str] = {}
    for linha in texto.splitlines():
        casou = LINHA_CHAVE.match(linha)
        if casou:
            encontradas[casou.group(1)] = casou.group(2)
    return encontradas


def criar(exemplo: str) -> str:
    conteudo = exemplo
    for chave, gerar in GERADORES.items():
        conteudo, total = re.subn(
            rf"^{chave}=.*$",
            lambda _, chave=chave, gerar=gerar: f"{chave}={gerar()}",
            conteudo,
            flags=re.MULTILINE,
        )
        if total != 1:
            raise ValueError(f"{chave} não encontrado no .env.example")
    return conteudo


def completar(atual: str, exemplo: str) -> tuple[str, list[str]]:
    """Acrescenta ao .env existente as chaves do modelo que faltam. Devolve (texto, chaves)."""
    presentes = set(chaves_do_modelo(atual))
    novas = [(c, v) for c, v in chaves_do_modelo(exemplo).items() if c not in presentes]
    if not novas:
        return atual, []
    linhas = [] if atual.endswith("\n") or not atual else [""]
    linhas.append("# Chaves acrescentadas automaticamente pelo `make setup`")
    for chave, valor in novas:
        gerar = GERADORES.get(chave)
        linhas.append(f"{chave}={gerar() if gerar else valor}")
    return atual + "\n".join(linhas) + "\n", [c for c, _ in novas]


def main() -> int:
    if not EXAMPLE.exists():
        print("ERRO: .env.example não encontrado.", file=sys.stderr)
        return 1
    exemplo = EXAMPLE.read_text(encoding="utf-8")

    if not TARGET.exists():
        try:
            conteudo = criar(exemplo)
        except ValueError as erro:
            print(f"ERRO: {erro}.", file=sys.stderr)
            return 1
        TARGET.write_text(conteudo, encoding="utf-8")
        TARGET.chmod(0o600)
        print(
            ".env criado com senha do banco e chave de pseudonimização aleatórias "
            "(não exibidas). Próximo passo: make up"
        )
        return 0

    novo, acrescentadas = completar(TARGET.read_text(encoding="utf-8"), exemplo)
    if not acrescentadas:
        print(".env já existe e está completo: nada a fazer (não é sobrescrito).")
        return 0
    TARGET.write_text(novo, encoding="utf-8")
    TARGET.chmod(0o600)
    print(".env existente preservado; chaves acrescentadas: " + ", ".join(acrescentadas))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
