"""Gera o reference.docx (estilos ABNT NBR 14724) a partir do modelo padrão do pandoc.

Uso: gerar_referencia.py <modelo-padrao.docx> <saida.docx>
"""

import sys

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONTE = "Arial"
MONO = "Courier New"


def fonte(estilo, nome=FONTE, tam=12, negrito=None, italico=None, caps=None):
    f = estilo.font
    f.name = nome
    f.size = Pt(tam)
    f.color.rgb = RGBColor(0, 0, 0)
    if negrito is not None:
        f.bold = negrito
    if italico is not None:
        f.italic = italico
    if caps is not None:
        f.all_caps = caps
    rpr = estilo.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for a in ("ascii", "hAnsi", "cs", "eastAsia"):
        rf.set(qn(f"w:{a}"), nome)
    for a in ("asciiTheme", "hAnsiTheme", "cstheme", "eastAsiaTheme"):
        rf.attrib.pop(qn(f"w:{a}"), None)


SEM_RECUO = Cm(0)


def par(
    estilo,
    linha=1.5,
    antes=0,
    depois=0,
    alinha=None,
    recuo=SEM_RECUO,
    esq=None,
    quebra=None,
    prox=None,
):
    p = estilo.paragraph_format
    p.line_spacing_rule = WD_LINE_SPACING.MULTIPLE if linha != 1 else WD_LINE_SPACING.SINGLE
    p.line_spacing = linha
    p.space_before = Pt(antes)
    p.space_after = Pt(depois)
    if alinha is not None:
        p.alignment = alinha
    p.first_line_indent = recuo
    if esq is not None:
        p.left_indent = esq
    if quebra is not None:
        p.page_break_before = quebra
    if prox is not None:
        p.keep_with_next = prox


def main(origem: str, destino: str) -> None:
    doc = Document(origem)
    st = doc.styles
    nomes = {s.name: s for s in st}

    def get(n):
        return nomes.get(n)

    J, E, C = WD_ALIGN_PARAGRAPH.JUSTIFY, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER

    fonte(st["Normal"])
    par(st["Normal"])
    for n in ("Body Text", "First Paragraph"):
        if get(n):
            fonte(get(n))
            par(get(n), alinha=J, recuo=Cm(1.25))
    if get("Compact"):
        fonte(get("Compact"))
        par(get("Compact"), alinha=J)
    # títulos
    h = {
        1: dict(depois=18, caps=True),
        2: dict(antes=12, depois=12),
        3: dict(antes=12, depois=6),
        4: dict(antes=6, depois=6),
    }
    for nivel, cfg in h.items():
        s = get(f"Heading {nivel}")
        if s is None:
            continue
        fonte(s, negrito=True, italico=(nivel == 4), caps=cfg.get("caps", False))
        par(
            s,
            alinha=E,
            antes=cfg.get("antes", 0),
            depois=cfg["depois"],
            quebra=(nivel == 1),
            prox=True,
        )
    # texto menor (10) com espaçamento simples
    for n in (
        "Block Text",
        "Footnote Text",
        "Image Caption",
        "Table Caption",
        "Caption",
        "Captioned Figure",
        "Figure",
    ):
        s = get(n)
        if s:
            fonte(s, tam=10)
            par(s, linha=1, alinha=E)
    if get("Block Text"):
        par(get("Block Text"), linha=1, alinha=J, esq=Cm(4), antes=6, depois=6)
    if get("Footnote Text"):
        par(get("Footnote Text"), linha=1, alinha=J)
    if get("Bibliography"):
        fonte(get("Bibliography"))
        par(get("Bibliography"), linha=1, alinha=E, depois=12)
    if get("Source Code"):
        fonte(get("Source Code"), nome=MONO, tam=9)
        par(get("Source Code"), linha=1, alinha=E, antes=6, depois=6)
    if get("Verbatim Char"):
        fonte(get("Verbatim Char"), nome=MONO, tam=10)
    if get("Hyperlink"):
        get("Hyperlink").font.color.rgb = RGBColor(0, 0, 0)
    if get("Table"):
        fonte(get("Table"), tam=10)

    # estilos próprios
    def novo(nome, base="Normal", tipo=WD_STYLE_TYPE.PARAGRAPH):
        s = st.add_style(nome, tipo)
        s.base_style = st[base]
        s.quick_style = True
        return s

    leg = novo("Legenda ABNT")
    fonte(leg, tam=10)
    par(leg, linha=1, alinha=C, antes=6, depois=6, prox=True)
    fonte_ = novo("Fonte ABNT")
    fonte(fonte_, tam=10)
    par(fonte_, linha=1, alinha=C, antes=3, depois=12)
    img = novo("Imagem ABNT")
    fonte(img, tam=10)
    par(img, linha=1, alinha=C, antes=3, depois=3, prox=True)
    capa = novo("Capa ABNT")
    fonte(capa)
    par(capa, linha=1.5, alinha=C)
    natureza = novo("Natureza ABNT")
    fonte(natureza, tam=10)
    par(natureza, linha=1, alinha=J, esq=Cm(8))
    sumt = novo("Titulo sem numero")
    fonte(sumt, negrito=True, caps=True)
    par(sumt, linha=1.5, alinha=C, depois=18, quebra=True)
    ref = novo("Referencia ABNT")
    fonte(ref)
    par(ref, linha=1, alinha=E, depois=12)
    for i, esq in ((1, 0), (2, 0.6)):
        t = st.add_style(f"toc {i}", WD_STYLE_TYPE.PARAGRAPH)
        t.base_style = st["Normal"]
        fonte(t, negrito=(i == 1))
        par(t, linha=1, alinha=E, antes=6 if i == 1 else 0, depois=3 if i == 1 else 0, esq=Cm(esq))

    # página A4 e margens 3/2/3/2
    for sec in doc.sections:
        sec.page_width, sec.page_height = Cm(21), Cm(29.7)
        sec.top_margin, sec.left_margin = Cm(3), Cm(3)
        sec.bottom_margin, sec.right_margin = Cm(2), Cm(2)
        sec.header_distance = Cm(1.25)
    doc.save(destino)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
