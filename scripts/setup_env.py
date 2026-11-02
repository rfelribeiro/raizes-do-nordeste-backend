#!/usr/bin/env python3
"""Cria o .env a partir do .env.example com uma senha de banco aleatória.

- Nunca sobrescreve um .env existente.
- Nunca imprime a senha gerada.
"""

import re
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / ".env.example"
TARGET = ROOT / ".env"


def main() -> int:
    if TARGET.exists():
        print(".env já existe: nada a fazer (não é sobrescrito).")
        return 0
    if not EXAMPLE.exists():
        print("ERRO: .env.example não encontrado.", file=sys.stderr)
        return 1

    password = secrets.token_urlsafe(24)
    content, count = re.subn(
        r"^POSTGRES_PASSWORD=.*$",
        lambda _: f"POSTGRES_PASSWORD={password}",
        EXAMPLE.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    if count != 1:
        print("ERRO: POSTGRES_PASSWORD não encontrado no .env.example.", file=sys.stderr)
        return 1

    TARGET.write_text(content, encoding="utf-8")
    TARGET.chmod(0o600)
    print(".env criado com senha de banco aleatória (não exibida). Próximo passo: make up")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
