#!/usr/bin/env bash
# Gera o .docx e o PDF do documento principal em normas ABNT (tudo em contêineres, versões fixas).
# Saída em docs/entrega/saida/ (fora do git). O RU vem do capa.local.yaml e não aparece no código.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENTREGA="$RAIZ/docs/entrega"
SAIDA="$ENTREGA/saida"
SCRIPTS="$RAIZ/scripts/entrega"

PANDOC_IMG="pandoc/core:3.6.4"
MERMAID_IMG="minlag/mermaid-cli:11.4.2"
PYTHON_IMG="python:3.14.10-slim"
LO_IMG="raizes-libreoffice:ubuntu24.04"
PYDOCX="python-docx==1.1.2"
PYYAML="pyyaml==6.0.2"

[ -f "$ENTREGA/capa.local.yaml" ] || { echo "Falta docs/entrega/capa.local.yaml (dados da capa, fora do git)." >&2; exit 1; }

USUARIO="$(id -u):$(id -g)"
mkdir -p "$SAIDA/diagramas" "$SAIDA/previas"

py() { # executa Python no contêiner fixo, com as bibliotecas em saida/.pylibs
  docker run --rm --user "$USUARIO" -e HOME=/tmp -e PYTHONPATH=/repo/docs/entrega/saida/.pylibs \
    -v "$RAIZ:/repo" -w /repo "$PYTHON_IMG" python "$@"
}

echo "==> Dependências Python (python-docx, pyyaml)"
if [ ! -d "$SAIDA/.pylibs" ]; then
  docker run --rm --user "$USUARIO" -e HOME=/tmp -v "$RAIZ:/repo" -w /repo "$PYTHON_IMG" \
    pip install --quiet --no-cache-dir --target docs/entrega/saida/.pylibs "$PYDOCX" "$PYYAML"
fi

echo "==> Pré-processamento do Markdown"
py scripts/entrega/preprocessar.py /repo --fase extrair
NOME="$(cat "$SAIDA/nome-arquivo.txt")"

echo "==> Diagramas Mermaid -> PNG"
for mmd in "$SAIDA"/diagramas/diagrama-*.mmd; do
  png="${mmd%.mmd}.png"
  docker run --rm --user "$USUARIO" -e HOME=/tmp -v "$RAIZ:/repo" "$MERMAID_IMG" \
    -p /repo/scripts/entrega/puppeteer-config.json \
    -i "/repo/docs/entrega/saida/diagramas/$(basename "$mmd")" \
    -o "/repo/docs/entrega/saida/diagramas/$(basename "$png")" \
    -b white -s 2 -w 1400 >/dev/null
done
py scripts/entrega/preprocessar.py /repo --fase imagens

echo "==> Estilos ABNT (reference.docx)"
docker run --rm --user "$USUARIO" "$PANDOC_IMG" --print-default-data-file reference.docx > "$SAIDA/reference-padrao.docx"
py scripts/entrega/gerar_referencia.py docs/entrega/saida/reference-padrao.docx docs/entrega/saida/reference.docx

echo "==> Markdown -> .docx (pandoc)"
docker run --rm --user "$USUARIO" -v "$RAIZ:/repo" -w /repo/docs/entrega "$PANDOC_IMG" \
  -f commonmark_x-implicit_figures-tex_math_dollars-smart \
  -t docx --reference-doc=saida/reference.docx --no-highlight \
  --resource-path=/repo/docs/entrega:/repo/docs \
  -o saida/pandoc.docx saida/documento.md

echo "==> Capa, folha de rosto, sumário, seções e tabelas (python-docx)"
py scripts/entrega/posprocessar.py docs/entrega/saida/pandoc.docx docs/entrega/capa.local.yaml "docs/entrega/saida/$NOME.docx"

echo "==> .docx -> PDF (LibreOffice)"
docker build -q -t "$LO_IMG" -f "$SCRIPTS/Dockerfile.libreoffice" "$SCRIPTS" >/dev/null
docker run --rm --user "$USUARIO" -e HOME=/tmp -v "$RAIZ:/repo" -w /repo/docs/entrega/saida "$LO_IMG" \
  python3 /repo/scripts/entrega/converter_pdf.py "$NOME.docx" "$NOME.PDF"

echo "Gerado: docs/entrega/saida/$NOME.docx e docs/entrega/saida/$NOME.PDF"
