"""Pós-processamento do .docx gerado pelo pandoc (roda em contêiner Python).

Faz o que o pandoc não faz sozinho: capa, folha de rosto, sumário (campo TOC), seções do Word
(paginação visível só a partir da Introdução), estilos de legenda/fonte, formato das tabelas.
Uso: posprocessar.py <entrada.docx> <capa.local.yaml> <saida.docx>
"""
import copy
import re
import sys

import yaml
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

LARGURA_TWIPS = int(15.7 * 567)  # área útil retrato: 21 cm - 3 cm - 2 cm
LARGURA_PAISAGEM = int(24.7 * 567)  # área útil paisagem: 29,7 cm - 3 cm - 2 cm
COLUNAS_PAISAGEM = 10  # tabelas com tantas colunas ou mais vão para página em paisagem
C, E = WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT


def campo(par, instrucao, texto_provisorio=""):
    """Insere um campo do Word (begin/instr/separate/texto/end) no parágrafo."""
    def run(filho):
        r = OxmlElement("w:r")
        r.append(filho)
        par._p.append(r)
        return r

    b = OxmlElement("w:fldChar")
    b.set(qn("w:fldCharType"), "begin")
    b.set(qn("w:dirty"), "true")
    run(b)
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = f" {instrucao} "
    run(it)
    s = OxmlElement("w:fldChar")
    s.set(qn("w:fldCharType"), "separate")
    run(s)
    t = OxmlElement("w:t")
    t.text = texto_provisorio
    run(t)
    e = OxmlElement("w:fldChar")
    e.set(qn("w:fldCharType"), "end")
    run(e)


def formata(par, alinha=None, linha=None, antes=None, depois=None, recuo=None, esq=None, prox=None):
    pf = par.paragraph_format
    if alinha is not None:
        pf.alignment = alinha
    if linha == 1:
        pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
    elif linha:
        pf.line_spacing = linha
    if antes is not None:
        pf.space_before = Pt(antes)
    if depois is not None:
        pf.space_after = Pt(depois)
    if recuo is not None:
        pf.first_line_indent = recuo
    if esq is not None:
        pf.left_indent = esq
    if prox is not None:
        pf.keep_with_next = prox


def tamanho_runs(elemento, pts):
    for r in elemento.iter(qn("w:r")):
        rpr = r.find(qn("w:rPr"))
        if rpr is None:
            rpr = OxmlElement("w:rPr")
            r.insert(0, rpr)
        for tag in ("w:sz", "w:szCs"):
            antigo = rpr.find(qn(tag))
            if antigo is not None:
                rpr.remove(antigo)
            novo = OxmlElement(tag)
            novo.set(qn("w:val"), str(int(pts * 2)))
            rpr.append(novo)


def formata_tabela(tab, largura_total, tam):
    tbl = tab._tbl
    ncol = len(tab.columns)
    pr = tbl.tblPr
    for filho in list(pr):
        if filho.tag in (qn("w:tblStyle"), qn("w:tblW"), qn("w:tblLayout"), qn("w:tblBorders"), qn("w:tblLook"), qn("w:tblCellMar")):
            pr.remove(filho)
    w = OxmlElement("w:tblW")
    w.set(qn("w:w"), str(largura_total))
    w.set(qn("w:type"), "dxa")
    pr.append(w)
    bordas = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement(f"w:{lado}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), "4")
        b.set(qn("w:space"), "0")
        b.set(qn("w:color"), "000000")
        bordas.append(b)
    pr.append(bordas)
    lay = OxmlElement("w:tblLayout")
    lay.set(qn("w:type"), "fixed")
    pr.append(lay)
    mar = OxmlElement("w:tblCellMar")
    for lado, v in (("top", 30), ("left", 70), ("bottom", 30), ("right", 70)):
        m = OxmlElement(f"w:{lado}")
        m.set(qn("w:w"), str(v))
        m.set(qn("w:type"), "dxa")
        mar.append(m)
    pr.append(mar)

    # larguras proporcionais ao conteúdo (maior palavra e comprimento médio de cada coluna)
    pesos = []
    for j in range(ncol):
        textos = [r.cells[j].text for r in tab.rows if j < len(r.cells)]
        maior_palavra = max((len(p) for t in textos for p in t.split()), default=1)
        media = sum(len(t) for t in textos) / max(1, len(textos))
        pesos.append(max(min(maior_palavra, 12), min(media, 50), 3))
    total = sum(pesos)
    larg = [largura_total * p / total for p in pesos]
    # piso por coluna: a maior palavra tem de caber sem quebrar no meio
    piso = []
    for j in range(ncol):
        textos = [r.cells[j].text for r in tab.rows if j < len(r.cells)]
        mp = max((len(p) for t in textos for p in t.split()), default=1)
        piso.append(min(mp, 9) * tam * 10 + 220)
    for _ in range(5):
        fixas = [i for i in range(ncol) if larg[i] <= piso[i]]
        livres = [i for i in range(ncol) if i not in fixas]
        if not livres:
            break
        sobra = largura_total - sum(piso[i] for i in fixas)
        base = sum(larg[i] for i in livres)
        for i in fixas:
            larg[i] = piso[i]
        for i in livres:
            larg[i] = sobra * larg[i] / base
    larg = [int(v) for v in larg]
    grade = tbl.find(qn("w:tblGrid"))
    for g, v in zip(grade.findall(qn("w:gridCol")), larg):
        g.set(qn("w:w"), str(v))
    for ri, row in enumerate(tab.rows):
        trpr = row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        trpr.append(cs)
        if ri == 0:
            th = OxmlElement("w:tblHeader")
            trpr.append(th)
        for j, cell in enumerate(row.cells):
            if j < len(larg):
                tcpr = cell._tc.get_or_add_tcPr()
                tw = tcpr.find(qn("w:tcW"))
                if tw is None:
                    tw = OxmlElement("w:tcW")
                    tcpr.insert(0, tw)
                tw.set(qn("w:w"), str(larg[j]))
                tw.set(qn("w:type"), "dxa")
            for p in cell.paragraphs:
                formata(p, alinha=E, linha=1, antes=0, depois=0, recuo=Cm(0), esq=Cm(0))
            tamanho_runs(cell._tc, tam)
            if ri == 0:
                for r in cell._tc.iter(qn("w:r")):
                    rpr = r.find(qn("w:rPr"))
                    b = OxmlElement("w:b")
                    rpr.append(b)
                tcpr = cell._tc.get_or_add_tcPr()
                sh = OxmlElement("w:shd")
                sh.set(qn("w:val"), "clear")
                sh.set(qn("w:color"), "auto")
                sh.set(qn("w:fill"), "E7E6E6")
                tcpr.append(sh)


def _estilo(doc, p_elem):
    from docx.text.paragraph import Paragraph
    return Paragraph(p_elem, doc._body).style.name


def main(entrada, capa_yaml, saida):
    capa = yaml.safe_load(open(capa_yaml, encoding="utf-8"))
    doc = Document(entrada)
    corpo = doc.element.body

    # página
    for sec in doc.sections:
        sec.page_width, sec.page_height = Cm(21), Cm(29.7)
        sec.top_margin, sec.left_margin = Cm(3), Cm(3)
        sec.bottom_margin, sec.right_margin = Cm(2), Cm(2)
        sec.header_distance = Cm(1.25)

    # classificação dos parágrafos do corpo
    em_refs = False
    for p in doc.paragraphs:
        nome = p.style.name
        texto = p.text.strip()
        if nome == "Heading 1":
            em_refs = texto.upper().startswith("REFERÊNCIAS")
            if not re.match(r"^\d", texto):
                formata(p, alinha=C)
            continue
        if p._p.findall(".//" + qn("w:drawing")) and not texto:
            p.style = doc.styles["Imagem ABNT"]
            continue
        negrito = bool(p.runs) and all(r.bold for r in p.runs if r.text.strip())
        if re.match(r"^(Figura|Tabela|Quadro)\s+\d+\s+[—–-]", texto) and negrito:
            p.style = doc.styles["Legenda ABNT"]
        elif texto.startswith("Fonte:"):
            p.style = doc.styles["Fonte ABNT"]
        elif em_refs and nome in ("Body Text", "First Paragraph", "Compact", "Normal"):
            p.style = doc.styles["Referencia ABNT"]

    largas = []
    for tab in doc.tables:
        if len(tab.columns) >= COLUNAS_PAISAGEM:
            formata_tabela(tab, LARGURA_PAISAGEM, 9)
            largas.append(tab)
        else:
            formata_tabela(tab, LARGURA_TWIPS, 10 if len(tab.columns) < 8 else 9)

    # ---- capa, folha de rosto e sumário (inseridos no início, na ordem) ----
    ancora = corpo[0]

    def novo(texto="", estilo="Capa ABNT", negrito=False, caixa_alta=False, antes=None, depois=None, quebra=False, esq=None):
        p = doc.add_paragraph(style=estilo)
        if texto:
            r = p.add_run(texto.upper() if caixa_alta else texto)
            r.bold = negrito or None
        formata(p, antes=antes, depois=depois, esq=esq)
        if quebra:
            p.paragraph_format.page_break_before = True
        ancora.addprevious(p._p)
        return p

    # capa
    novo(capa["instituicao"], negrito=True, caixa_alta=True, depois=6)
    novo(capa["curso"], caixa_alta=True, depois=6)
    novo(f'{capa["disciplina"]} — {capa["turma"]}', caixa_alta=True, depois=6)
    novo(capa["trilha"], caixa_alta=True)
    novo(capa["autor"], caixa_alta=True, antes=70)
    novo(f'RU: {capa["ru"]}', antes=0)
    novo(capa["titulo"], negrito=True, caixa_alta=True, antes=90)
    novo("Projeto Multidisciplinar — Trilha Back-end", antes=6)
    novo(f'Polo de apoio: {capa["polo"]}', antes=60)
    novo(f'Semestre: {capa["semestre"]}')
    novo(capa["cidade"], antes=120, depois=0)
    novo(str(capa["ano"]), antes=0)

    # folha de rosto
    novo(capa["autor"], caixa_alta=True, quebra=True)
    novo(f'RU: {capa["ru"]}')
    novo(capa["titulo"], negrito=True, caixa_alta=True, antes=110)
    novo("Projeto Multidisciplinar — Trilha Back-end", antes=6)
    natureza = (
        f'Trabalho apresentado à disciplina {capa["disciplina"]} ({capa["turma"]}) do curso de '
        f'{capa["curso"]} do {capa["instituicao"]}, {capa["trilha"]}, como requisito parcial de avaliação. '
        f'Polo de apoio: {capa["polo"]}. Semestre: {capa["semestre"]}.'
    )
    novo(natureza, estilo="Natureza ABNT", antes=80, depois=8)
    novo("Professores:", estilo="Natureza ABNT", depois=2)
    for prof in capa["professores"]:
        novo(prof, estilo="Natureza ABNT")
    novo(capa["cidade"], antes=110)
    novo(str(capa["ano"]), antes=0)

    # sumário (título centralizado e campo TOC)
    novo("Sumário", estilo="Titulo sem numero")
    ptoc = doc.add_paragraph(style="toc 1")
    campo(ptoc, 'TOC \\o "1-2" \\h \\z \\u', "Atualize o campo para gerar o sumário.")
    ancora.addprevious(ptoc._p)

    # quebra de seção antes da Introdução: tudo acima fica sem número visível
    primeiro_h1 = next(p for p in doc.paragraphs if p.style.name == "Heading 1")
    sect_final = corpo.find(qn("w:sectPr"))
    sp = copy.deepcopy(sect_final)
    for ref in sp.findall(qn("w:headerReference")) + sp.findall(qn("w:footerReference")):
        sp.remove(ref)
    marca = OxmlElement("w:p")
    ppr = OxmlElement("w:pPr")
    ppr.append(sp)
    marca.append(ppr)
    primeiro_h1._p.addprevious(marca)

    # cabeçalho com número de página, só na segunda seção (numeração contínua desde a capa)
    ultima = doc.sections[-1]
    ultima.header.is_linked_to_previous = False
    hp = ultima.header.paragraphs[0]
    hp.text = ""
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    campo(hp, "PAGE", "1")
    for r in hp._p.iter(qn("w:r")):
        rpr = r.find(qn("w:rPr"))
        if rpr is None:
            rpr = OxmlElement("w:rPr")
            r.insert(0, rpr)
        rf = OxmlElement("w:rFonts")
        for a in ("ascii", "hAnsi", "cs"):
            rf.set(qn(f"w:{a}"), "Arial")
        rpr.append(rf)
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), "20")
        rpr.append(sz)

    # tabelas largas: seção em paisagem própria (legenda, tabela e fonte juntas)
    def fim_de_secao(paisagem):
        sp2 = copy.deepcopy(corpo.find(qn("w:sectPr")))  # já traz o cabeçalho com a paginação
        if paisagem:
            pg = sp2.find(qn("w:pgSz"))
            pg.set(qn("w:w"), str(int(29.7 * 567)))
            pg.set(qn("w:h"), str(int(21 * 567)))
            pg.set(qn("w:orient"), "landscape")
        m = OxmlElement("w:p")
        pp = OxmlElement("w:pPr")
        pp.append(sp2)
        m.append(pp)
        return m

    for tab in largas:
        antes = tab._tbl.getprevious()
        if antes is not None and antes.tag == qn("w:p") and _estilo(doc, antes).startswith("Legenda"):
            ini = antes
        else:
            ini = tab._tbl
        ini.addprevious(fim_de_secao(False))
        fim = tab._tbl.getnext()
        if fim is not None and fim.tag == qn("w:p") and _estilo(doc, fim).startswith("Fonte"):
            fim.addnext(fim_de_secao(True))
        else:
            tab._tbl.addnext(fim_de_secao(True))

    # pede ao Word para atualizar o sumário ao abrir
    cfg = doc.settings.element
    uf = OxmlElement("w:updateFields")
    uf.set(qn("w:val"), "true")
    cfg.append(uf)

    doc.core_properties.title = capa["titulo"]
    doc.core_properties.author = capa["autor"]
    doc.save(saida)


if __name__ == "__main__":
    main(*sys.argv[1:4])
