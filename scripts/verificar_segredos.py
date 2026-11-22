#!/usr/bin/env python3
"""Verificador de segredos e dados sensíveis (somente biblioteca padrão).

Uso:
  verificar_segredos.py --staged   verifica o conteúdo staged no git (pre-commit)
  verificar_segredos.py --todos    verifica todos os arquivos rastreados (e novos não ignorados)

Linhas com o marcador `segredos:permitir` são ignoradas.
Termos privados opcionais ficam em `.registro-ia.local` (um por linha, `#` = comentário,
sem diferenciar maiúsculas). Esses termos NUNCA são impressos. Também nunca se imprime
o valor de um achado: apenas arquivo:linha e o tipo.
Limitação: a detecção de "senha literal" é heurística; não substitui revisão humana.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRIVATE_TERMS_FILE = ROOT / ".registro-ia.local"
ALLOW_MARKER = "segredos:permitir"
PUBLIC_REPO_URL = re.compile(r"github\.com/[a-z0-9-]+/raizes-do-nordeste-backend(?:\.git)?")
MAX_BYTES = 2_000_000

TOKEN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("chave privada", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY")),
    ("token Anthropic", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("token estilo sk-", re.compile(r"\bsk-[A-Za-z0-9_-]{32,}")),
    ("token GitHub", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("token GitHub (fine-grained)", re.compile(r"github_pat_[A-Za-z0-9_]{22,}")),
    ("chave de acesso AWS", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("token Slack", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}")),
    (
        "JWT",
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}"),
    ),
]

ASSIGNMENT = re.compile(
    r"""(?ix)
    [A-Za-z0-9_]*(?:password|passwd|senha|secret|token|api[_-]?key)[A-Za-z0-9_]*
    ["']?\s*[:=]\s*
    (?:"(?P<dq>[^"]*)"|'(?P<sq>[^']*)'|(?P<raw>[^\s"'#,;)\]}]+))
    """
)
FICTITIOUS_HINTS = (
    "changeme", "troque", "ficticio", "fictício", "exemplo", "example", "dummy", "fake",
    "placeholder", "teste", "test", "xxx", "***", "...", "your", "seu_", "sua_", "aqui",
    "secret_name", "none", "null", "true", "false",
)  # fmt: skip


def is_fictitious(value: str) -> bool:
    lowered = value.lower()
    if not value or value[0] in "${<%@" or "${" in value or "(" in value:
        return True
    if len(set(value)) <= 2:
        return True
    return any(hint in lowered for hint in FICTITIOUS_HINTS)


def literal_secret_kind(line: str, suffix: str) -> bool:
    for match in ASSIGNMENT.finditer(line):
        quoted = match.group("dq") if match.group("dq") is not None else match.group("sq")
        if quoted is not None:
            value = quoted
            # Literais só letras/underscore parecem nomes de variáveis, não senhas.
            if len(value) < 8 or re.fullmatch(r"[A-Za-z_ .-]+", value):
                continue
        else:
            value = match.group("raw") or ""
            if suffix == ".py":
                continue  # em código, valor sem aspas é expressão, não literal
            if len(value) < 8 or not (re.search(r"\d", value) and re.search(r"[A-Za-z]", value)):
                continue
        if not is_fictitious(value):
            return True
    return False


def load_private_terms() -> list[str]:
    if not PRIVATE_TERMS_FILE.exists():
        return []
    terms = []
    for raw in PRIVATE_TERMS_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
        term = raw.strip()
        if term and not term.startswith("#"):
            terms.append(term.lower())
    return terms


def is_env_file(path: str) -> bool:
    name = Path(path).name
    return (name == ".env" or name.startswith(".env.")) and name != ".env.example"


def scan_text(path: str, text: str, terms: list[str]) -> list[tuple[int, str]]:
    findings: list[tuple[int, str]] = []
    suffix = Path(path).suffix.lower()
    for number, line in enumerate(text.splitlines(), start=1):
        if ALLOW_MARKER in line:
            continue
        for kind, pattern in TOKEN_PATTERNS:
            if pattern.search(line):
                findings.append((number, kind))
        if literal_secret_kind(line, suffix):
            findings.append((number, "senha/segredo com valor literal"))
        # Exceção autorizada pelo autor (D-061): o endereço público do próprio repositório pode
        # aparecer; o nome da conta continua termo privado em qualquer outro contexto.
        lowered = PUBLIC_REPO_URL.sub("", line.lower())
        if any(term in lowered for term in terms):
            findings.append((number, "termo privado (.registro-ia.local)"))
    return findings


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True).stdout


def list_files(mode: str) -> list[str]:
    if mode == "staged":
        out = git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    else:
        out = git("ls-files", "-z", "--cached", "--others", "--exclude-standard")
    return sorted({p for p in out.decode("utf-8").split("\0") if p})


def read_content(mode: str, path: str) -> bytes | None:
    try:
        if mode == "staged":
            return git("show", f":{path}")
        file = ROOT / path
        return file.read_bytes() if file.is_file() else None
    except subprocess.CalledProcessError, OSError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--staged", action="store_true")
    group.add_argument("--todos", action="store_true")
    mode = "staged" if parser.parse_args().staged else "todos"

    terms = load_private_terms()
    total = 0
    for path in list_files(mode):
        if is_env_file(path) or Path(path).name == PRIVATE_TERMS_FILE.name:
            print(f"{path}: [arquivo de ambiente/privado não pode ser versionado]")
            total += 1
            continue
        data = read_content(mode, path)
        if data is None or len(data) > MAX_BYTES or b"\0" in data:
            continue
        text = data.decode("utf-8", errors="ignore")
        for number, kind in scan_text(path, text, terms):
            print(f"{path}:{number}: [{kind}] valor omitido")
            total += 1

    if total:
        print(
            f"\n{total} achado(s). Remova o dado sensível ou, se for falso positivo, "
            f"marque a linha com `{ALLOW_MARKER}`.",
            file=sys.stderr,
        )
        return 1
    print("Nenhum segredo encontrado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
