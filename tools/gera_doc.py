"""Gera docs/documentacao_tecnica.pdf a partir de docs/documentacao_tecnica.md.

O texto usa um markdown simples: # titulo de capitulo (comeca pagina nova), ## secao,
### subsecao, paragrafos, listas (- e 1.), tabelas (| a | b |), blocos ``` de codigo,
> nota, **negrito** e `codigo`. O sumario e a numeracao de paginas sao automaticos.

Uso (na raiz do projeto; precisa do pacote reportlab):
    python tools/gera_doc.py
"""
import re
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
                                Preformatted, Table, TableStyle, PageBreak, KeepTogether)
from reportlab.platypus.tableofcontents import TableOfContents

CINZA_CODIGO = colors.HexColor("#f3f3f3")
CINZA_BORDA = colors.HexColor("#b0b0b0")
CINZA_CAB = colors.HexColor("#e2e2e2")

base = dict(fontName="Helvetica", fontSize=10, leading=14, textColor=colors.black)
S = {
    "p": ParagraphStyle("p", alignment=TA_JUSTIFY, spaceAfter=6, **base),
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=17, leading=21, spaceBefore=4, spaceAfter=12),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13, leading=17, spaceBefore=12, spaceAfter=6, keepWithNext=1),
    "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=11, leading=14, spaceBefore=9, spaceAfter=4, keepWithNext=1),
    "li": ParagraphStyle("li", leftIndent=16, bulletIndent=5, spaceAfter=3, alignment=TA_JUSTIFY, **base),
    "code": ParagraphStyle("code", fontName="Courier", fontSize=7.8, leading=9.6, backColor=CINZA_CODIGO,
                           borderColor=CINZA_BORDA, borderWidth=0.5, borderPadding=5,
                           spaceBefore=6, spaceAfter=10, leftIndent=5, rightIndent=5),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8.5, leading=10.5),
    "cellh": ParagraphStyle("cellh", fontName="Helvetica-Bold", fontSize=8.5, leading=10.5),
    "nota": ParagraphStyle("nota", fontName="Helvetica-Oblique", fontSize=9, leading=12, leftIndent=10,
                           borderColor=CINZA_BORDA, borderWidth=0, spaceAfter=8, textColor=colors.HexColor("#333333")),
}


def inline(txt):
    """Converte **negrito** e `codigo` para a marcacao do ReportLab."""
    txt = txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    guard = []

    def cod(m):
        guard.append('<font face="Courier" size="8.8">' + m.group(1) + "</font>")
        return f"\x00{len(guard) - 1}\x00"
    txt = re.sub(r"`([^`]+)`", cod, txt)
    txt = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", txt)
    return re.sub(r"\x00(\d+)\x00", lambda m: guard[int(m.group(1))], txt)


class Doc(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(path, pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                         topMargin=2.2 * cm, bottomMargin=2 * cm,
                         title="Guitar Hero ICMC - Documentacao Tecnica", author="Guitar Hero ICMC")
        f = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="f")
        self.addPageTemplates([PageTemplate("capa", [f], onPage=lambda c, d: None),
                               PageTemplate("normal", [f], onPage=self.rodape)])

    def rodape(self, c, d):
        c.saveState()
        c.setFont("Helvetica", 8)
        c.setStrokeColor(CINZA_BORDA)
        c.line(self.leftMargin, A4[1] - 1.6 * cm, A4[0] - self.rightMargin, A4[1] - 1.6 * cm)
        c.drawString(self.leftMargin, A4[1] - 1.45 * cm, "Guitar Hero ICMC - Documentação Técnica")
        c.drawRightString(A4[0] - self.rightMargin, 1.2 * cm, f"{d.page}")
        c.restoreState()

    def afterFlowable(self, fl):
        if isinstance(fl, Paragraph) and fl.style.name in ("h1", "h2"):
            nivel = 0 if fl.style.name == "h1" else 1
            texto = fl.getPlainText()
            chave = f"h{id(fl)}"
            self.canv.bookmarkPage(chave)
            self.canv.addOutlineEntry(texto, chave, level=nivel)
            self.notify("TOCEntry", (nivel, texto, self.page, chave))


def tabela(linhas, largura):
    """Monta uma tabela do PDF a partir das linhas | a | b | do texto."""
    cab, corpo = linhas[0], linhas[1:]
    n = len(cab)
    maxlen = [max(len(l[i]) if i < len(l) else 0 for l in linhas) for i in range(n)]
    pesos = [min(max(m, 5), 60) for m in maxlen]
    tot = sum(pesos)
    larg = [largura * p / tot for p in pesos]
    dados = [[Paragraph(inline(c), S["cellh"]) for c in cab]]
    for l in corpo:
        l = l + [""] * (n - len(l))
        dados.append([Paragraph(inline(c), S["cell"]) for c in l])
    t = Table(dados, colWidths=larg, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), CINZA_CAB),
        ("GRID", (0, 0), (-1, -1), 0.4, CINZA_BORDA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def parse(texto, largura):
    """Transforma o texto em markdown simples nos blocos do PDF."""
    story, buf, linhas = [], [], texto.splitlines()
    i = 0
    primeiro_h1 = True

    def flush():
        if buf:
            story.append(Paragraph(inline(" ".join(buf)), S["p"]))
            buf.clear()
    while i < len(linhas):
        l = linhas[i]
        s = l.strip()
        if s.startswith("```"):
            flush()
            bloco = []
            i += 1
            while not linhas[i].strip().startswith("```"):
                bloco.append(linhas[i])
                i += 1
            # tab vira um quadrado preto na fonte do PDF; KeepTogether nao parte o bloco entre paginas
            story.append(KeepTogether([Preformatted("\n".join(bloco).expandtabs(4), S["code"])]))
        elif s.startswith("# "):
            flush()
            if not primeiro_h1:
                story.append(PageBreak())
            primeiro_h1 = False
            story.append(Paragraph(inline(s[2:]), S["h1"]))
        elif s.startswith("## "):
            flush()
            story.append(Paragraph(inline(s[3:]), S["h2"]))
        elif s.startswith("### "):
            flush()
            story.append(Paragraph(inline(s[4:]), S["h3"]))
        elif s.startswith("|"):
            flush()
            rows = []
            while i < len(linhas) and linhas[i].strip().startswith("|"):
                r = linhas[i].strip()
                if not re.fullmatch(r"\|[\s\-|:]+\|", r):
                    cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", r.strip("|"))]
                    rows.append(cells)
                i += 1
            story.append(tabela(rows, largura))
            story.append(Spacer(1, 8))
            continue
        elif s.startswith("- "):
            flush()
            story.append(Paragraph(inline(s[2:]), S["li"], bulletText="•"))
        elif re.match(r"\d+\. ", s):
            flush()
            num, resto = s.split(" ", 1)
            story.append(Paragraph(inline(resto), S["li"], bulletText=num))
        elif s.startswith("> "):
            flush()
            story.append(Paragraph(inline(s[2:]), S["nota"]))
        elif not s:
            flush()
        else:
            buf.append(s)
        i += 1
    flush()
    return story


def capa():
    """Monta a pagina de capa."""
    t = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=28, leading=34, alignment=TA_CENTER)
    st = ParagraphStyle("st", fontName="Helvetica", fontSize=14, leading=20, alignment=TA_CENTER)
    pe = ParagraphStyle("pe", fontName="Helvetica", fontSize=10, leading=14, alignment=TA_CENTER)
    return [Spacer(1, 6 * cm), Paragraph("Guitar Hero ICMC", t), Spacer(1, 0.6 * cm),
            Paragraph("Documentação Técnica", st), Spacer(1, 0.3 * cm),
            Paragraph("Jogo de ritmo em Assembly do Processador ICMC, instrução SNDN, "
                      "simulador, ferramentas e testes", pe),
            Spacer(1, 7 * cm),
            Paragraph("SSC0511 - Organização de Computadores Digitais - ICMC/USP", pe),
            Paragraph("Prof. Eduardo do Valle Simões", pe)]


def main():
    conteudo = sys.argv[1] if len(sys.argv) > 1 else "docs/documentacao_tecnica.md"
    saida = sys.argv[2] if len(sys.argv) > 2 else "docs/documentacao_tecnica.pdf"
    doc = Doc(saida)
    from reportlab.platypus.doctemplate import NextPageTemplate
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("toc1", fontName="Helvetica-Bold", fontSize=10, leading=14, leftIndent=0, spaceBefore=3),
        ParagraphStyle("toc2", fontName="Helvetica", fontSize=9, leading=12, leftIndent=14),
    ]
    with open(conteudo, encoding="utf-8") as f:
        texto = f.read()
    story = capa() + [NextPageTemplate("normal"), PageBreak(),
                      Paragraph("Sumário", ParagraphStyle("sum", fontName="Helvetica-Bold", fontSize=17,
                                                          leading=21, spaceAfter=12)),
                      toc, PageBreak()]
    story += parse(texto, doc.width)
    doc.multiBuild(story)
    print("ok", saida)


if __name__ == "__main__":
    main()
