"""Render a vocabulary .txt table into a liut969-style two-column PDF.

Usage:
    python scripts/make_pdf.py <input.txt> <output.pdf> "<title>" "<subtitle>"
        [--intro "<intro>"] [--no-freq] [--mark-selfmade]

    --no-freq        omit the 词频 line entirely
    --mark-selfmade  label self-composed examples as 例句（自编）
                     (default: all examples shown plainly as 例句)
"""
import argparse
import re
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame,
                                Paragraph, Spacer, KeepTogether, PageBreak,
                                NextPageTemplate)

FONT_PATH = "/Library/Fonts/Arial Unicode.ttf"
FONT = "ArialUni"
pdfmetrics.registerFont(TTFont(FONT, FONT_PATH))

BLUE = HexColor("#1f5fa8")
GRAY = HexColor("#666666")

PAGE_W, PAGE_H = A4
MARGIN = 1.5 * cm
GUTTER = 0.8 * cm
COL_W = (PAGE_W - 2 * MARGIN - GUTTER) / 2

ENTRY_RE = re.compile(r"^\[(\d+)\]\s+(.+)$")
SECTION_RE = re.compile(r"——+\s*Section\s*(\d+)\s*——+")
DF_FREQ_RE = re.compile(r"见于\s*(\d+\s*/\s*\d+)")


def styles():
    return {
        "word": ParagraphStyle("word", fontName=FONT, fontSize=11,
                               textColor=BLUE, spaceBefore=7, spaceAfter=1,
                               leading=13),
        "ipa": ParagraphStyle("ipa", fontName=FONT, fontSize=7.5,
                              textColor=GRAY, leading=10),
        "field": ParagraphStyle("field", fontName=FONT, fontSize=8.5,
                                leading=11.5),
        "section": ParagraphStyle("section", fontName=FONT, fontSize=13,
                                  textColor=BLUE, alignment=1,
                                  spaceBefore=6, spaceAfter=14, leading=16),
        "title": ParagraphStyle("title", fontName=FONT, fontSize=26,
                                textColor=BLUE, alignment=1, leading=34),
        "sub": ParagraphStyle("sub", fontName=FONT, fontSize=12,
                              textColor=GRAY, alignment=1, leading=20),
        "intro": ParagraphStyle("intro", fontName=FONT, fontSize=10,
                                leading=18),
    }


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def parse(txt_path: Path):
    """Yield ('section', n) and ('entry', dict) items in order."""
    lines = txt_path.read_text().splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        sm = SECTION_RE.search(line)
        if sm:
            yield "section", sm.group(1)
            i += 1
            continue
        em = ENTRY_RE.match(line)
        if em:
            rec = {"rank": em.group(1), "word": em.group(2).strip(),
                   "ipa": "", "freq": "", "def": "", "forms": "",
                   "ex_label": "例句", "ex": ""}
            i += 1
            while i < len(lines):
                s = lines[i].strip()
                if not s or ENTRY_RE.match(s) or SECTION_RE.search(s):
                    break
                val = s.split(":", 1)[-1].split("：", 1)[-1].strip()
                if s.startswith("英["):
                    rec["ipa"] = s
                elif s.startswith("词频"):
                    rec["freq"] = val
                elif s.startswith("释义"):
                    rec["def"] = val
                elif s.startswith("变形"):
                    rec["forms"] = val
                elif s.startswith("例句"):
                    rec["ex_label"] = ("例句（自编）" if "自编" in s[:6]
                                       else "例句")
                    rec["ex"] = val
                i += 1
            yield "entry", rec
            continue
        i += 1


def fmt_freq(raw: str) -> str:
    """DF 词频 '见于 31/31 套真题，共 7072 次' -> '31/31'; TF count kept as-is."""
    m = DF_FREQ_RE.search(raw)
    return m.group(1).replace(" ", "") if m else raw


def entry_flowables(rec, st, show_freq: bool, mark_selfmade: bool):
    blk = [Paragraph(f'<b>{rec["rank"]}. {esc(rec["word"])}</b>', st["word"])]
    if rec["ipa"]:
        blk.append(Paragraph(esc(rec["ipa"]), st["ipa"]))
    if show_freq and rec["freq"]:
        blk.append(Paragraph(f'<b>词频</b>: {esc(fmt_freq(rec["freq"]))}',
                             st["field"]))
    if rec["def"]:
        blk.append(Paragraph(f'<b>释义</b>: {esc(rec["def"])}', st["field"]))
    if rec["forms"]:
        blk.append(Paragraph(f'<b>变形</b>: {esc(rec["forms"])}', st["field"]))
    if rec["ex"]:
        label = rec["ex_label"] if mark_selfmade else "例句"
        blk.append(Paragraph(f'<b>{label}</b>: {esc(rec["ex"])}', st["field"]))
    blk.append(Spacer(1, 3))
    return KeepTogether(blk)


def build(txt_path, pdf_path, title, subtitle, intro,
          show_freq=True, mark_selfmade=False):
    st = styles()

    def on_page(canvas, doc):
        canvas.setFont(FONT, 8)
        canvas.setFillColor(GRAY)
        canvas.drawCentredString(PAGE_W / 2, 0.8 * cm, str(doc.page))

    cover = Frame(MARGIN, MARGIN, PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN,
                  id="cover")
    body = [Frame(MARGIN, MARGIN, COL_W, PAGE_H - 2 * MARGIN, id="L"),
            Frame(MARGIN + COL_W + GUTTER, MARGIN, COL_W, PAGE_H - 2 * MARGIN,
                  id="R")]
    doc = BaseDocTemplate(
        str(pdf_path), pagesize=A4,
        pageTemplates=[PageTemplate(id="cover", frames=[cover]),
                       PageTemplate(id="body", frames=body, onPage=on_page)])

    story = [Spacer(1, 5 * cm),
             Paragraph(esc(title), st["title"]),
             Spacer(1, 0.8 * cm),
             Paragraph(esc(subtitle), st["sub"])]
    if intro:
        story += [Spacer(1, 1.5 * cm), Paragraph(esc(intro), st["intro"])]
    story += [NextPageTemplate("body"), PageBreak()]

    for kind, payload in parse(Path(txt_path)):
        if kind == "section":
            story.append(Paragraph(f"Section {payload}", st["section"]))
        else:
            story.append(entry_flowables(payload, st, show_freq, mark_selfmade))

    doc.build(story)
    print(f"-> {pdf_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("title")
    ap.add_argument("subtitle")
    ap.add_argument("--intro", default="")
    ap.add_argument("--no-freq", action="store_true")
    ap.add_argument("--mark-selfmade", action="store_true")
    a = ap.parse_args()
    build(a.input, a.output, a.title, a.subtitle, a.intro,
          show_freq=not a.no_freq, mark_selfmade=a.mark_selfmade)
