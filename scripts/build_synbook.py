"""Build the synonym-discrimination book from synbook_content/*.md + 四级高频词同义辨析.json.

Output:
  docs/synbook.html        hosted copy (picked up by build_html.py into the PWA precache)
  synbook.html (root)      sibling of the single-file 英语四级单词背诵.html (AirDrop pair)

Content source is synbook_content/G001.md … G207.md, one per group, in the format of
分类页内容参考.md (G001 IS that file). The JSON supplies the TOC/index data and each
group's title line; the md supplies the prose. Run this BEFORE build_html.py.
"""
import html as htmllib
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONTENT = ROOT / "synbook_content"
BOOK = json.loads((ROOT / "四级高频词同义辨析.json").read_text())
TPL = (ROOT / "web" / "synbook.html").read_text()


def inline(s):
    """markdown inline: **bold** / *italic* (+ HTML escape first)."""
    s = htmllib.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)
    return s


def md_to_blocks(md):
    """One group's markdown -> [block html] (each later wrapped in .blk)."""
    lines = [l.rstrip() for l in md.replace("\r\n", "\n").split("\n")]
    blocks, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i].strip()
        if not line or line == "---":
            i += 1
            continue
        if line.startswith("### "):
            blocks.append(f'<div class="h3">{inline(line[4:].strip())}</div>')
            i += 1
            continue
        if line.startswith("|"):                       # table
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            if rows:
                h = '<table class="gr"><tr>' + "".join(f"<th>{inline(c)}</th>" for c in rows[0]) + "</tr>"
                for r in rows[1:]:
                    h += "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>"
                blocks.append(h + "</table>")
            continue
        if line.startswith("* "):                      # bullet run (blank lines allowed inside)
            items = []
            while i < n and (not lines[i].strip() or lines[i].strip().startswith("* ")):
                if lines[i].strip():
                    items.append(lines[i].strip()[2:].strip())
                i += 1
            cur = None
            for t in items:
                if t.startswith("**"):                 # **word（…）：** → 新条目卡
                    if cur:
                        blocks.append("".join(cur) + "</div>")
                    cur = [f'<div class="blt">{inline(t)}']
                elif t.startswith("*") and t.endswith("*"):   # 整行斜体 = 例句行
                    ex = f'<span class="exq">{inline(t.strip("*").strip())}</span>'
                    if cur:
                        cur.append(ex)
                    else:
                        cur = [f'<div class="blt">{ex}']
                else:
                    if cur:
                        cur.append("<br>" + inline(t))
                    else:
                        cur = [f'<div class="blt">{inline(t)}']
            if cur:
                blocks.append("".join(cur) + "</div>")
            continue
        # paragraph: consecutive non-blank plain lines
        para = []
        while i < n and lines[i].strip() and not lines[i].strip().startswith(("### ", "|", "* ", "---")):
            para.append(lines[i].strip())
            i += 1
        body = "<br>".join(inline(p) for p in para)
        if para[0].startswith("**总结一下：**") or para[0].startswith("**总结一下:**"):
            blocks.append(f'<div class="sumbox">{body}</div>')
        else:
            blocks.append(f'<div class="para">{body}</div>')
    return blocks


groups_out, idx_rows, problems = [], [], []
for g in BOOK["groups"]:
    p = CONTENT / f"{g['id']}.md"
    if not p.exists():
        problems.append(f"{g['id']} 缺文件")
        continue
    blocks = md_to_blocks(p.read_text(encoding="utf-8"))
    if not any("sumbox" in b for b in blocks):
        problems.append(f"{g['id']} 缺总结块")
    words = [m["word"] for m in g["members"]]
    head = (f'<div class="blk"><div class="gtopic">{htmllib.escape(g["topic"])}'
            f'<span class="gmeta">{g["id"]} · {g["member_count"]} 词 · '
            f'{" / ".join(words[:4])}{" …" if len(words) > 4 else ""}</span></div></div>')
    body = "".join(f'<div class="blk">{b}</div>' for b in blocks)
    groups_out.append({"id": g["id"], "topic": g["topic"], "n": g["member_count"],
                       "words": words[:4], "html": head + body})
    for m in g["members"]:
        idx_rows.append({"w": m["word"], "rank": m["rank"], "gid": g["id"], "topic": g["topic"]})

idx_rows.sort(key=lambda r: r["w"].lower())
if problems:
    print("!! 问题:", problems)

total_kb = sum(len(g["html"]) for g in groups_out) // 1024
out = (TPL
       .replace("__GROUPS__", json.dumps(groups_out, ensure_ascii=False, separators=(",", ":")))
       .replace("__IDX__", json.dumps(idx_rows, ensure_ascii=False, separators=(",", ":"))))

# hosted copy: back link falls back to the hosted shell
hosted = out.replace("__BACK__", "index.html")
(ROOT / "docs" / "synbook.html").write_text(hosted)
# root copy: sibling of the AirDrop single file
single = out.replace("__BACK__", "英语四级单词背诵.html")
(ROOT / "synbook.html").write_text(single)

print(f"-> docs/synbook.html + synbook.html  {len(hosted)//1024} KB, "
      f"{len(groups_out)} 组正文 {total_kb} KB, 索引 {len(idx_rows)} 词")
