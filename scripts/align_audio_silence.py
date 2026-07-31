#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""开头静音对齐 —— 把 intermediate/audio/{us,uk}/*.mp3 每条发音开头的静音补齐到 ≥314ms。

背景:有道 mp3 开头一般有 314–415ms 静音,网页用 skipMs 跳过它秒出声(现已改为逐条起音检测,滑块 0..100)。
但 `been` 等个别词开头静音不足 314ms,默认 skip 会切进单词本体。本脚本检测每条的真实起音,
把不足的补零到 ≥314ms,使 0–314 全滑块范围都不切词。见 WEB_HANDOFF.md §7。

两种检测(US/UK 音源结构不同):
  - US:开头是"精确零",第一个非零采样即真实起点(无损无余量)。
  - UK:开头非精确零,用短窗 RMS(需持续能量,忽略孤立 ±1 抖动样本)、且刻意偏早检测。
两者都单向安全:检测点只会 ≤ 真实起音 → 补齐后真实起音必 ≥314ms → 绝不切词。

幂等:已 ≥314ms 的文件跳过不动(不重编码,保持字节不变)。可安全重复运行。
重下音频(fetch_audio.py)后请重跑本脚本,否则 been 等词又会被切。

用法:
  python scripts/align_audio_silence.py            # 对齐 intermediate/audio
  python scripts/align_audio_silence.py --dry-run  # 只扫描报告,不改文件
依赖:ffmpeg / ffprobe(命令行)、numpy。
"""
import os, sys, json, shutil, subprocess, argparse
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO = os.path.join(ROOT, "intermediate", "audio")
BACKUP = os.path.join(ROOT, "intermediate", "audio_orig_backup")  # 首次原件备份(gitignore 建议)
TARGET_MS = 314.0   # 对齐目标:真实起音 ≥ 此值

def probe_sr(p):
    return int(subprocess.run(["ffprobe","-v","error","-select_streams","a:0",
        "-show_entries","stream=sample_rate","-of","default=nk=1:nw=1",p],
        capture_output=True, text=True).stdout.strip())

def bitrate(p):
    r = subprocess.run(["ffprobe","-v","error","-select_streams","a:0","-show_entries",
        "stream=bit_rate","-of","default=nk=1:nw=1",p], capture_output=True, text=True).stdout.strip()
    if r in ("","N/A"):
        r = subprocess.run(["ffprobe","-v","error","-show_entries","format=bit_rate",
            "-of","default=nk=1:nw=1",p], capture_output=True, text=True).stdout.strip()
    return int(r) if r not in ("","N/A") else 64000

def decode(p, sr):
    o = subprocess.run(["ffmpeg","-v","quiet","-i",p,"-ac","1","-ar",str(sr),"-f","s16le","-"],
                       capture_output=True).stdout
    return np.frombuffer(o, dtype="<i2")

def us_zero_samples(a):
    """US:开头精确零结束处 = 第一个非零采样下标。"""
    nz = np.nonzero(a != 0)[0]
    return int(nz[0]) if len(nz) else len(a)

def uk_onset_samples(a, sr, K=3.0, floor_pct=5.0):
    """UK:短窗 RMS 首次超过(底噪×K)处,再往前退 5ms(偏早=安全)。"""
    m = np.abs(a.astype(np.float64))
    win = max(1, int(sr*0.005)); hop = max(1, int(sr*0.001))
    if len(m) <= win: return 0
    sq = np.concatenate([[0.0], np.cumsum(m*m)])
    starts = np.arange(0, len(m)-win, hop)
    rms = np.sqrt((sq[starts+win]-sq[starts]) / win)
    floor = np.percentile(rms, floor_pct)
    thr = max(floor*K, 1.0)
    idx = np.nonzero(rms > thr)[0]
    on = int(starts[idx[0]]) if len(idx) else len(m)
    return max(0, on - int(sr*0.005))

def word_onset_ms(a, sr, thr=300):
    """真实词起音(振幅>thr),用于对齐后验证。"""
    m = np.abs(a.astype(np.int32)); idx = np.nonzero(m > thr)[0]
    return (idx[0]/sr*1000.0) if len(idx) else len(a)/sr*1000.0

def detect_ms(a, sr, acc):
    det = us_zero_samples(a) if acc == "us" else uk_onset_samples(a, sr)
    return det/sr*1000.0

def encode(padded, sr, br, out):
    return subprocess.run(["ffmpeg","-v","error","-y","-f","s16le","-ar",str(sr),"-ac","1",
        "-i","-","-codec:a","libmp3lame","-b:a",str(br), out],
        input=padded.tobytes(), capture_output=True).returncode == 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只扫描报告,不改文件")
    ap.add_argument("--audio", default=AUDIO, help="音频根目录(默认 intermediate/audio)")
    args = ap.parse_args()

    padded = skipped = 0
    lows = []
    for acc in ("us", "uk"):
        d = os.path.join(args.audio, acc)
        if not os.path.isdir(d): continue
        files = sorted(os.listdir(d), key=lambda n: int(n.split(".")[0]) if n.split(".")[0].isdigit() else 0)
        for name in files:
            if not name.endswith(".mp3"): continue
            p = os.path.join(d, name)
            sr = probe_sr(p); a = decode(p, sr)
            # 幂等的关键:用"真实词起音"(振幅>300,响、稳定)判断是否已安全,
            # 而不是用检测点/纯零边界——后者会被有损重编码抹动 2–3ms,导致反复重编码退化。
            # 补齐用检测点(零边界/RMS)算量,判定用 word_onset:两者都保证 word_onset≥314。
            if word_onset_ms(a, sr) >= TARGET_MS:
                skipped += 1; continue
            if args.dry_run:
                padded += 1
                print(f"  would pad {acc}/{name}: word_onset={word_onset_ms(a,sr):.1f}ms")
                continue
            br = bitrate(p)
            # 首次备份原件(仅当该文件尚无备份)
            bkp = os.path.join(BACKUP, acc, name)
            if not os.path.exists(bkp):
                os.makedirs(os.path.dirname(bkp), exist_ok=True); shutil.copy2(p, bkp)
            # 补零到目标;若因 mp3 编码器延迟导致成品仍 <314,自增余量重试
            target = TARGET_MS
            for _ in range(4):
                det = detect_ms(a, sr, acc)
                npad = int(round((target-det)/1000.0*sr))
                buf = np.concatenate([np.zeros(max(0,npad), dtype="<i2"), a])
                tmp = p + ".tmp.mp3"
                if not encode(buf, sr, br, tmp):
                    print(f"  ENCODE FAIL {acc}/{name}", file=sys.stderr); break
                wo = word_onset_ms(decode(tmp, sr), sr)
                if wo >= TARGET_MS:
                    os.replace(tmp, p); padded += 1; break
                os.remove(tmp); target += 4.0   # 加 4ms 余量再试
            else:
                lows.append(f"{acc}/{name} word_onset<314 after retries");
    print(f"\n对齐完成:padded={padded}  skipped(已≥314)={skipped}")
    if lows:
        print("⚠️ 仍未达标(需人工看):"); [print("  ", x) for x in lows]

if __name__ == "__main__":
    main()
