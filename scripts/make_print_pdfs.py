"""Generate the print-optimized 背诵版 PDFs.

Final versions  -> repo root (tracked):
    英语四级高频单词彩色背诵版.pdf   词头蓝色，例句纯黑
    英语四级高频单词黑白背诵版.pdf   全黑，例句纯黑
Earlier variant -> _print/ (git-ignored, kept only for visual comparison):
    same names, but examples in dark gray + studied word highlighted blue.

All derive from the DF table with self-composed examples marked, 词频 removed.
"""
from pathlib import Path

from make_pdf import build

ROOT = Path(__file__).parent.parent
SRC = ROOT / "output" / "high_freq_cet4_df.txt"
CMP = ROOT / "_print"
CMP.mkdir(exist_ok=True)

TITLE = "英语四级真题高频词汇"

# --- final-version cover text -------------------------------------------------
GITHUB = "GitHub：https://github.com/yiyisheh/CET4-vocabulary"

COLOR_INTRO = (
    "最佳背诵彩色打印版：\n"
    "将 英语四级DF自编例句标注top-1250.pdf 去掉了词频信息。\n"
    "\n"
    "绝大部分例句均取自四级试卷原文，其中“(自编)”标志区分出非原文。\n"
    "\n"
    "作者：yiyisheh@outlook.com\n"
    + GITHUB
)
BW_INTRO = (
    "最佳背诵黑白打印版：\n"
    "将 英语四级DF自编例句标注top-1250.pdf 去掉了词频信息，单词部分变成黑色。\n"
    "\n"
    "绝大部分例句均取自四级试卷原文，其中“(自编)”标志区分出非原文。\n"
    "\n"
    "作者：yiyisheh@outlook.com\n"
    + GITHUB
)

# --- earlier variant cover text (gray examples + blue word) ------------------
COLOR_INTRO_OLD = (
    "最佳背诵彩色打印版：\n"
    "将 英语四级DF自编例句标注top-1250.pdf 去掉了词频信息，"
    "例句变为了黑灰体，其中例句中出现的该单词变成了蓝色。\n"
    "\n"
    "绝大部分例句均取自四级试卷原文，其中“(自编)”标志区分出非原文。\n"
    "\n"
    "作者：yiyisheh@outlook.com\n"
    + GITHUB
)
BW_INTRO_OLD = (
    "最佳背诵黑白打印版：\n"
    "将 英语四级DF自编例句标注top-1250.pdf 去掉了词频信息，"
    "单词部分变成黑色，例句变为了黑灰体。\n"
    "\n"
    "绝大部分例句均取自四级试卷原文，其中“(自编)”标志区分出非原文。\n"
    "\n"
    "作者：yiyisheh@outlook.com\n"
    + GITHUB
)


def main():
    # final versions -> repo root
    build(SRC, ROOT / "英语四级高频单词彩色背诵版.pdf", TITLE,
          "彩色背诵版 · top 1250 · 2021–2025 真题", intro=COLOR_INTRO,
          show_freq=False, mark_selfmade=True, mono=False)
    build(SRC, ROOT / "英语四级高频单词黑白背诵版.pdf", TITLE,
          "黑白背诵版 · top 1250 · 2021–2025 真题", intro=BW_INTRO,
          show_freq=False, mark_selfmade=True, mono=True)

    # earlier variant -> _print/ (comparison only)
    build(SRC, CMP / "英语四级高频单词彩色背诵版.pdf", TITLE,
          "彩色背诵版 · top 1250 · 2021–2025 真题", intro=COLOR_INTRO_OLD,
          show_freq=False, mark_selfmade=True, mono=False,
          example_gray=True, highlight_word=True)
    build(SRC, CMP / "英语四级高频单词黑白背诵版.pdf", TITLE,
          "黑白背诵版 · top 1250 · 2021–2025 真题", intro=BW_INTRO_OLD,
          show_freq=False, mark_selfmade=True, mono=True,
          example_gray=True, highlight_word=False)


if __name__ == "__main__":
    main()
