"""Render the printable PDFs from intermediate/entries_full.json (repo root):

  英语四级高频单词彩色背诵版.pdf   beginners: IPA, 真题释义, 核心意象 / 词根词缀, 短语, 例句; blue headwords
  英语四级高频单词黑白背诵版.pdf   same content, all black (black-and-white printing)
  英语四级高频单词查缺补漏版.pdf   for learners who already know most words: headword + every
                                  真题 sense + 短语, three columns, no IPA / cards / examples

Entry order matches the web page: 释义 → 核心意象 / 词根词缀 → 短语 → 例句.
"""
import json
import re
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
SENSES = json.loads((ROOT / "intermediate" / "senses.json").read_text())

FONT_PATH = "/Library/Fonts/Arial Unicode.ttf"
FONT = "ArialUni"
pdfmetrics.registerFont(TTFont(FONT, FONT_PATH))
# Arial Unicode has no bold face; headwords (Latin only) borrow Arial Bold
BOLD = "ArialBold"
pdfmetrics.registerFont(TTFont(BOLD, "/System/Library/Fonts/Supplemental/Arial Bold.ttf"))

BLUE = HexColor("#1f5fa8")
GRAY = HexColor("#666666")

PAGE_W, PAGE_H = A4
MARGIN = 1.5 * cm
SITE = "https://yiyisheh.github.io/CET4-vocabulary/"
REPO = "https://github.com/yiyisheh/CET4-vocabulary"


def styles(accent, small=False):
    fs = 0.92 if small else 1.0
    return {
        "word": ParagraphStyle("word", fontName=FONT, fontSize=11, textColor=accent,
                               spaceBefore=7, spaceAfter=1, leading=13),
        "ipa": ParagraphStyle("ipa", fontName=FONT, fontSize=7.5, textColor=GRAY,
                              leading=10),
        # wordWrap="CJK": break inside Chinese runs too; the default only breaks at spaces
        "field": ParagraphStyle("field", fontName=FONT, fontSize=8.5 * fs, leading=11.5 * fs,
                                wordWrap="CJK"),
        "gap": ParagraphStyle("gap", fontName=FONT, fontSize=8 * fs, leading=10.6 * fs,
                              spaceBefore=3.5, wordWrap="CJK"),
        "root": ParagraphStyle("root", fontName=FONT, fontSize=8 * fs, leading=11 * fs,
                               textColor=GRAY, leftIndent=6, wordWrap="CJK"),
        "rootsum": ParagraphStyle("rootsum", fontName=FONT, fontSize=8 * fs, leading=11 * fs,
                                  textColor=GRAY, leftIndent=6, spaceBefore=1, wordWrap="CJK"),
        "section": ParagraphStyle("section", fontName=FONT, fontSize=13,
                                  textColor=accent, alignment=1, spaceBefore=6,
                                  spaceAfter=14, leading=16),
        "title": ParagraphStyle("title", fontName=FONT, fontSize=26, textColor=accent,
                                alignment=1, leading=34),
        "sub": ParagraphStyle("sub", fontName=FONT, fontSize=12, textColor=GRAY,
                              alignment=1, leading=20),
        "intro": ParagraphStyle("intro", fontName=FONT, fontSize=10.5, leading=19),
    }


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def phrase_line(e):
    return "短语 " + "；".join(f'<b>{esc(p["p"])}</b> {esc(p["zh"])}' for p in e["phr"])


def entry_block(e, ST):
    head = e["syl"] or e["word"]
    blk = [Paragraph(f'<b>{e["rank"]}. {esc(head)}</b>', ST["word"])]
    if e["uk"] or e["us"]:
        blk.append(Paragraph(f'英[{esc(e["uk"])}]&nbsp;&nbsp;美[{esc(e["us"])}]',
                             ST["ipa"]))
    if e["def"]:
        blk.append(Paragraph(esc(e["def"]), ST["field"]))
    if e.get("core"):
        blk.append(Paragraph(f'核心 <b>{esc(e["core"]["image"])}</b>', ST["root"]))
        blk.append(Paragraph(f'▸ {esc(e["core"]["derive"])}', ST["rootsum"]))
    if e["root"]:
        for p in e["root"]["parts"]:
            blk.append(Paragraph(
                f'{esc(p["type"])} <b>{esc(p["text"])}</b> = {esc(p["meaning"])}', ST["root"]))
        if e["root"]["summary"]:
            blk.append(Paragraph(f'▸ {esc(e["root"]["summary"])}', ST["rootsum"]))
    if e.get("phr"):
        blk.append(Paragraph(phrase_line(e), ST["root"]))
    if e["ex"]:
        blk.append(Paragraph(f'<b>{e["ex_label"]}</b>: {esc(e["ex"])}', ST["field"]))
    blk.append(Spacer(1, 3))
    return KeepTogether(blk)


POS = re.compile(r"^((?:[a-z]+ )?[a-z]+\.)?(.*)$")


def full_def(e):
    """释义 with every 真题 sense: words with a 核心意象 card show only the first 5 in
    entries_full; the rest are appended here, grouped by part of speech."""
    s = SENSES.get(e["word"]) or {}
    extra = (s.get("all") or [])[s.get("shown", 0):]
    if not extra:
        return e["def"]
    groups = {}
    for item in extra:
        pos, zh = POS.match(item).groups()
        groups.setdefault(pos or "", []).append(zh)
    return e["def"] + " " + " ".join(f"{pos}{'; '.join(zs)}." for pos, zs in groups.items())


def gap_block(e, ST):
    # same size as the 释义: mixing sizes in one paragraph makes reportlab misjudge its height
    blk = [Paragraph(f'<font name="{BOLD}">{e["rank"]}. {esc(e["word"])}</font> {esc(full_def(e) or "")}',
                     ST["gap"])]
    if e.get("phr"):
        blk.append(Paragraph(phrase_line(e), ST["root"]))
    return KeepTogether(blk)


FOOT = (
    "\n"
    f"配套背单词网页（可发音、划掉已掌握、自测）：{SITE}\n"
    "\n"
    "作者：yiyisheh@outlook.com\n"
    f"GitHub：{REPO}"
)

INTRO_FULL = (
    "适合从零开始背四级单词的人：\n"
    "· 1250 个词按「在多少套真题里出现过」排序，越靠前越常考；\n"
    "· 释义只列真题里出现过的义项，最核心的排在第一；\n"
    "· 多义小词配「核心意象」，用一个画面串起各个意思；长词配「词根词缀」拆解；\n"
    "· 「短语」是真题里出现 3 次以上的固定搭配；\n"
    "· 例句取自真题原文（用的是第一个义项），附中文翻译；“(自编)”标出的是非原文；\n"
    "· 词头用音节点划分（如 com·po·si·tion），便于拼读。\n"
    "\n"
    "有核心意象的多义词，释义只列前 5 个义项，全部义项见核心意象。\n"
    "词根拆解与核心意象由 AI 生成，仅供助记参考。\n"
) + FOOT

INTRO_GAP = (
    "适合已经背过一轮、想查缺补漏的人：\n"
    "· 只留单词、释义和真题短语，去掉音标、例句和助记卡片，三栏排版，扫得快；\n"
    "· 释义列出真题里出现过的全部义项。熟词的生僻意思也在里面——比如 take 除了「拿」，"
    "还有「修（课程）」「服用（药）」——这正是最容易漏的地方；\n"
    "· 「短语」是真题里出现 3 次以上的固定搭配。\n"
    "\n"
    "用法：遮住释义从头扫一遍，说不出意思、或者只认得第一个意思的词做个记号，"
    "再到彩色背诵版或背单词网页里看核心意象、词根和例句。\n"
) + FOOT

VARIANTS = [
    {"out": "英语四级高频单词彩色背诵版.pdf", "accent": BLUE, "cols": 2, "block": entry_block,
     "sub": "彩色背诵版 · top 1250 · 2021–2025 真题", "intro": INTRO_FULL},
    {"out": "英语四级高频单词黑白背诵版.pdf", "accent": black, "cols": 2, "block": entry_block,
     "sub": "黑白背诵版 · top 1250 · 2021–2025 真题", "intro": INTRO_FULL},
    {"out": "英语四级高频单词查缺补漏版.pdf", "accent": black, "cols": 3, "block": gap_block,
     "sub": "查缺补漏版 · top 1250 · 2021–2025 真题", "intro": INTRO_GAP, "small": True},
]


def build(v):
    ST = styles(v["accent"], v.get("small", False))
    out = ROOT / v["out"]

    def on_page(canvas, doc):
        canvas.setFont(FONT, 8)
        canvas.setFillColor(GRAY)
        canvas.drawCentredString(PAGE_W / 2, 0.8 * cm, str(doc.page))

    gutter = (0.8 if v["cols"] == 2 else 0.6) * cm
    col_w = (PAGE_W - 2 * MARGIN - gutter * (v["cols"] - 1)) / v["cols"]
    cover = Frame(MARGIN, MARGIN, PAGE_W - 2 * MARGIN, PAGE_H - 2 * MARGIN, id="cover")
    body = [Frame(MARGIN + i * (col_w + gutter), MARGIN, col_w, PAGE_H - 2 * MARGIN, id=f"c{i}")
            for i in range(v["cols"])]
    doc = BaseDocTemplate(
        str(out), pagesize=A4,
        pageTemplates=[PageTemplate(id="cover", frames=[cover]),
                       PageTemplate(id="body", frames=body, onPage=on_page)])

    story = [Spacer(1, 3.5 * cm),
             Paragraph("英语四级真题高频词汇", ST["title"]),
             Spacer(1, 0.8 * cm),
             Paragraph(v["sub"], ST["sub"]),
             Spacer(1, 1.3 * cm),
             Paragraph(esc(v["intro"]).replace("\n", "<br/>"), ST["intro"]),
             NextPageTemplate("body"), PageBreak()]

    last_section = None
    for e in DATA:
        if e["section"] != last_section:
            story.append(Paragraph(f'Section {e["section"]}', ST["section"]))
            last_section = e["section"]
        story.append(v["block"](e, ST))
    doc.build(story)
    print(f"-> {out.name}  {doc.page} pages")


def main():
    for v in VARIANTS:
        build(v)


if __name__ == "__main__":
    main()
