"""Pull the timing diagnostics (kind "tlog") and per-day study time (kind "time") for one sync
code from Supabase and print where the time went, minute by minute. Read-only (sync_pull only).

    python scripts/devtest/tlog_report.py <同步码> [YYYYMMDD]     # default: today

tlog row item = "设备id|YYYYMMDDHHmm|c,g,s,o,t,f,h,n,L,x" (seconds except n/L), see the 计时诊断
block in web/template.html:
  c 计入 | g 背诵页里间隔超过 STUDY_GAP（现为 2 分钟）被丢掉 | s 背诵页但状态池/自测没开 | o 其他页面 |
  t 切后台前最后一次操作之后 | f 回前台后第一次操作之前 | h 在后台 | n 心跳 | L 长间隔次数 | x 最长间隔
"""
import json
import sys
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
cfg = json.loads((ROOT / "web" / "supabase-config.json").read_text())
code = sys.argv[1]
day = sys.argv[2] if len(sys.argv) > 2 else date.today().strftime("%Y%m%d")


def pull():
    rows, off = [], 0
    while True:
        req = urllib.request.Request(
            cfg["url"] + "/rest/v1/rpc/sync_pull",
            data=json.dumps({"p_code": code, "p_offset": off}).encode(),
            headers={"apikey": cfg["key"], "Authorization": "Bearer " + cfg["key"],
                     "Content-Type": "application/json"})
        page = json.loads(urllib.request.urlopen(req).read())
        if not page:
            return rows
        rows += page
        off += len(page)


rows = pull()
kinds = defaultdict(int)
for r in rows:
    kinds[r["kind"]] += 1
print("rows by kind:", dict(kinds))
print("\nstudy time (kind time):")
for r in sorted((r for r in rows if r["kind"] == "time"), key=lambda r: r["item"]):
    print(f"  {r['item']:<32} {int(r['t']) / 60000:6.1f} min")

F = ["c", "g", "s", "o", "t", "f", "h", "n", "L", "x"]
mins = []
for r in rows:
    if r["kind"] != "tlog":
        continue
    dev, mk, vals = r["item"].split("|")
    if not mk.startswith(day):
        continue
    mins.append((mk, dev, dict(zip(F, map(float, vals.split(","))))))
mins.sort()
if not mins:
    print(f"\nno tlog rows for {day}")
    sys.exit()
print(f"\ntlog {day} (seconds): " + "  ".join(F))
tot = defaultdict(float)
for mk, dev, v in mins:
    print(f"  {mk[8:10]}:{mk[10:]} {dev[:6]} " + " ".join(f"{v[f]:6.0f}" for f in F))
    for f in F:
        tot[f] = max(tot[f], v[f]) if f == "x" else tot[f] + v[f]
print("total  " + "  ".join(f"{f}={tot[f] / 60:.1f}m" if f not in "nLx" else f"{f}={tot[f]:.0f}" for f in F))
span = (int(mins[-1][0][8:10]) * 60 + int(mins[-1][0][10:])) - (int(mins[0][0][8:10]) * 60 + int(mins[0][0][10:])) + 1
print(f"active minutes {len(mins)}, wall span {span} min")

# ---- 操作日志 (kind "tev"): item = "设备id|YYYYMMDDHHmm|序号|<秒> <中文一句>\n<秒> <中文一句>..." ----
chunks = defaultdict(dict)
for r in rows:
    if r["kind"] != "tev":
        continue
    dev, mk, seq, body = r["item"].split("|", 3)
    if mk.startswith(day):
        chunks[(dev, mk)][int(seq)] = body
events = []                                      # (abs seconds since midnight, dev, text)
for (dev, mk), parts in chunks.items():
    base = int(mk[8:10]) * 3600 + int(mk[10:12]) * 60
    for line in "\n".join(parts[i] for i in sorted(parts)).split("\n"):
        line = line.strip()
        if line:
            sec, _, text = line.partition(" ")
            events.append((base + float(sec), dev, text))
events.sort()
if not events:
    print(f"\nno tev rows for {day}")
    sys.exit()


def hms(t):
    return f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{t % 60:04.1f}"


devs = sorted({d for _, d, _ in events})
print(f"\n操作日志 {day}：{len(events)} 条" + (f"（{len(devs)} 台设备）" if len(devs) > 1 else ""))
for t, dev, text in events:
    print(f"  {hms(t)}  " + (f"[{dev[:4]}] " if len(devs) > 1 else "") + text)
