"""Pré-processamento do documento principal (roda em contêiner Python).

Lê docs/entrega/documento-principal.md (sem alterá-lo) e gera, em docs/entrega/saida/:
  - documento.md: cópia limpa (sem comentários HTML, sem front matter, sem capa/sumário,
    com títulos de seção primária em MAIÚSCULAS e blocos mermaid trocados por imagens PNG);
  - diagramas/diagrama-NN.mmd: fonte de cada diagrama Mermaid;
  - nome-arquivo.txt: nome base do arquivo final, montado com o RU do capa.local.yaml.
Uso: preprocessar.py <raiz-do-repositorio> --fase {extrair,imagens}
  extrair: gera os .mmd e o documento.md provisório (imagens ainda sem tamanho);
  imagens: calcula o tamanho de cada PNG e grava o documento.md final.
"""
import argparse
import re
import struct
import sys
from pathlib import Path

import yaml

LARGURA_UTIL_CM = 15.7  # A4 (21 cm) - margens esquerda 3 cm e direita 2 cm
ALTURA_MAX_CM = 21.5  # deixa folga para a legenda e a fonte na mesma página
ESCALA_MERMAID = 2  # igual ao -s do mermaid-cli
DPI_TELA = 96


def tamanho_png(caminho: Path) -> tuple[int, int]:
    """Lê largura e altura (px) do cabeçalho do PNG, sem dependências externas."""
    with caminho.open("rb") as f:
        cab = f.read(24)
    return struct.unpack(">II", cab[16:24])


def dimensoes_cm(larg_px: int, alt_px: int, escala: float) -> tuple[float, float]:
    """Tamanho natural em cm, limitado à área útil da página."""
    larg = larg_px / escala / DPI_TELA * 2.54
    alt = alt_px / escala / DPI_TELA * 2.54
    fator = min(1.0, LARGURA_UTIL_CM / larg, ALTURA_MAX_CM / alt)
    return larg * fator, alt * fator


def segmentos(texto: str):
    """Divide o texto em (é_cerca, trecho) preservando blocos de código cercados."""
    saida, buf, cerca, marca = [], [], False, ""
    for linha in texto.split("\n"):
        m = re.match(r"^(`{3,}|~{3,})(.*)$", linha)
        if not cerca and m:
            if buf:
                saida.append((False, "\n".join(buf)))
            buf, cerca, marca = [linha], True, m.group(1)
        elif cerca and linha.startswith(marca) and linha.strip() == marca:
            buf.append(linha)
            saida.append((True, "\n".join(buf)))
            buf, cerca = [], False
        else:
            buf.append(linha)
    if buf:
        saida.append((cerca, "\n".join(buf)))
    return saida


def limpar(texto: str) -> str:
    # 1. front matter YAML
    texto = re.sub(r"\A---\n.*?\n---\n", "", texto, flags=re.S)
    partes = []
    for cerca, trecho in segmentos(texto):
        if not cerca:
            trecho = re.sub(r"<!--.*?-->", "", trecho, flags=re.S)
        partes.append((cerca, trecho))
    # recompõe e remove capítulos gerados pelo pipeline (capa e sumário)
    linhas, cerca_atual = [], False
    descartando = False
    for cerca, trecho in partes:
        for linha in trecho.split("\n"):
            if not cerca and re.match(r"^# ", linha):
                descartando = bool(re.match(r"^# (Capa e folha de rosto|Sumário)\s*$", linha))
                if not descartando:
                    linha = "# " + linha[2:].upper()
            if not descartando:
                linhas.append(linha)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(linhas)).strip() + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("raiz")
    ap.add_argument("--fase", choices=["extrair", "imagens"], required=True)
    args = ap.parse_args()
    raiz = Path(args.raiz)
    entrega = raiz / "docs" / "entrega"
    saida = entrega / "saida"
    diag = saida / "diagramas"
    diag.mkdir(parents=True, exist_ok=True)

    if args.fase == "extrair":
        capa = yaml.safe_load((entrega / "capa.local.yaml").read_text(encoding="utf-8"))
        ru = str(capa["ru"]).strip()
        (saida / "nome-arquivo.txt").write_text(f"{ru}_Projeto_Back_End", encoding="utf-8")
        texto = limpar((entrega / "documento-principal.md").read_text(encoding="utf-8"))
        # extrai os blocos mermaid
        n = 0
        saida_md = []
        for cerca, trecho in segmentos(texto):
            m = re.match(r"^```mermaid\n(.*)\n```$", trecho, flags=re.S) if cerca else None
            if m:
                n += 1
                (diag / f"diagrama-{n:02d}.mmd").write_text(m.group(1) + "\n", encoding="utf-8")
                saida_md.append(f"@@DIAGRAMA{n:02d}@@")
            else:
                saida_md.append(trecho)
        (saida / "documento-bruto.md").write_text("\n".join(saida_md), encoding="utf-8")
        print(f"{n} diagramas extraídos.")
        return

    # fase "imagens": troca marcadores e imagens existentes por imagens sem legenda e com tamanho
    texto = (saida / "documento-bruto.md").read_text(encoding="utf-8")

    def tag(caminho_rel: str, arquivo: Path, escala: float) -> str:
        larg, alt = dimensoes_cm(*tamanho_png(arquivo), escala)
        return f"![]({caminho_rel}){{width={larg:.2f}cm height={alt:.2f}cm}}"

    def troca_diag(m):
        num = m.group(1)
        arq = diag / f"diagrama-{num}.png"
        return tag(f"saida/diagramas/diagrama-{num}.png", arq, ESCALA_MERMAID)

    texto = re.sub(r"@@DIAGRAMA(\d\d)@@", troca_diag, texto)

    def troca_img(m):
        caminho = m.group(1)
        arq = (entrega / caminho).resolve()
        if not arq.exists():
            sys.exit(f"Imagem não encontrada: {caminho}")
        return tag(caminho, arq, 1.0)

    texto = re.sub(r"!\[[^\]]*\]\(((?!saida/)[^)\s]+\.png)\)", troca_img, texto)
    (saida / "documento.md").write_text(texto, encoding="utf-8")
    print("documento.md gerado.")


if __name__ == "__main__":
    main()
