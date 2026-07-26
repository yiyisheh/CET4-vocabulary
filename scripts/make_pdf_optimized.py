"""Render the optimized 背诵版 PDF from intermediate/entries_full.json.

Differences vs make_pdf.py:
  * no 词频 line, no 变形 line
  * 释义 shown without the "释义:" label (just the text)
  * adds a 词根/词缀 block below the example (screenshot-style tags + summary)

Output: 英语四级高频单词彩色背诵版(优化).pdf  (repo root)
"""
import json
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame,
                                Paragraph, Spacer, KeepTogether, PageBreak,
                                NextPageTemplate)

ROOT = Path(__file__).parent.parent
DATA = json.loads((ROOT / "intermediate" / "entries_full.json").read_text())
OUT = ROOT / "英语四级高频单词彩色背诵版(优化).pdf"

FONT_PATH = "/Library/Fonts/Arial Unicode.ttf"
FONT = "ArialUni"
pdfmetrics.registerFont(TTFont(FONT, FONT_PATH))

BLUE = HexColor("#1f5fa8")
GRAY = HexColor("#666666")
ROOT_TAG = HexColor("#2e8b74")     # 词根标签绿色
ROOT_SUM = HexColor("#3a3a3a")

PAGE_W, PAGE_H = A4
MARGIN = 1.5 * cm
GUTTER = 0.8 * cm
COL_W = (PAGE_W - 2 * MARGIN - GUTTER) / 2

ST = {
    "word": ParagraphStyle("word", fontName=FONT, fontSize=11, textColor=BLUE,
                           spaceBefore=7, spaceAfter=1, leading=13),
    "ipa": ParagraphStyle("ipa", fontName=FONT, fontSize=7.5, textColor=GRAY,
                          leading=10),
    "field": ParagraphStyle("field", fontName=FONT, fontSize=8.5, leading=11.5),
    "root": ParagraphStyle("root", fontName=FONT, fontSize=8, leading=11,
                           textColor=GRAY, leftIndent=6),
    "rootsum": ParagraphStyle("rootsum", fontName=FONT, fontSize=8, leading=11,
                              textColor=GRAY, leftIndent=6, spaceBefore=1),
    "section": ParagraphStyle("section", fontName=FONT, fontSize=13,
                              textColor=BLUE, alignment=1, spaceBefore=6,
                              spaceAfter=14, leading=16),
    "title": ParagraphStyle("title", fontName=FONT, fontSize=26, textColor=BLUE,
                            alignment=1, leading=34),
    "sub": ParagraphStyle("sub", fontName=FONT, fontSize=12, textColor=GRAY,
                          alignment=1, leading=20),
    "intro": ParagraphStyle("intro", fontName=FONT, fontSize=10.5, leading=19),
}


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def entry_block(e):
    head = e["syl"] or e["word"]
    blk = [Paragraph(f'<b>{e["rank"]}. {esc(head)}</b>', ST["word"])]
    if e["uk"] or e["us"]:
        blk.append(Paragraph(f'英[{esc(e["uk"])}]&nbsp;&nbsp;美[{esc(e["us"])}]',
                             ST["ipa"]))
    if e["def"]:
        blk.append(Paragraph(esc(e["def"]), ST["field"]))
    if e["ex"]:
        blk.append(Paragraph(f'<b>{e["ex_label"]}</b>: {esc(e["ex"])}',
                             ST["field"]))
    if e["root"]:
        for p in e["root"]["parts"]:
            tag = esc(p["type"])
            txt = esc(p["text"])
            mean = esc(p["meaning"])
            blk.append(Paragraph(
                f'{tag} <b>{txt}</b> = {mean}', ST["root"]))
        if e["root"]["summary"]:
            blk.append(Paragraph(f'▸ {esc(e["root"]["summary"])}',
                                 ST["rootsum"]))
    blk.append(Spacer(1, 3))
    return KeepTogether(blk)


INTRO = (
    "最佳背诵彩色打印版（优化版）：\n"
    "在 英语四级高频单词彩色背诵版.pdf 基础上——\n"
    "· 去掉了「释义:」标签与「变形」行，更简洁；\n"
    "· 词头改用音节点划分（如 com·po·si·tion），便于拼读；\n"
    "· 为可拆解的单词补充了「词根/词缀」助记块。\n"
    "\n"
    "绝大部分例句均取自四级试卷原文，其中“(自编)”标志区分出非原文。\n"
    "词根拆解由 AI 生成，仅供助记参考。\n"
    "\n"
    "作者：yiyisheh@outlook.com\n"
    "GitHub：https://github.com/yiyisheh/CET4-vocabulary"
)


def main():
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
        str(OUT), pagesize=A4,
        pageTemplates=[PageTemplate(id="cover", frames=[cover]),
                       PageTemplate(id="body", frames=body, onPage=on_page)])

    story = [Spacer(1, 3.5 * cm),
             Paragraph("英语四级真题高频词汇", ST["title"]),
             Spacer(1, 0.8 * cm),
             Paragraph("彩色背诵版（优化）· 含词根词缀 · top 1250 · 2021–2025 真题",
                       ST["sub"]),
             Spacer(1, 1.3 * cm),
             Paragraph(esc(INTRO).replace("\n", "<br/>"), ST["intro"]),
             NextPageTemplate("body"), PageBreak()]

    last_section = None
    for e in DATA:
        if e["section"] != last_section:
            story.append(Paragraph(f'Section {e["section"]}', ST["section"]))
            last_section = e["section"]
        story.append(entry_block(e))
    doc.build(story)
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
