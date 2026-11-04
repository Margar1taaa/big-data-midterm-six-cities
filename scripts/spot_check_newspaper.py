# -*- coding: utf-8 -*-
"""
spot_check_newspaper.py
报刊关键词命中抽查检验（词表 v1 -> v2 拓宽的效果与命中质量）。

两部分：
1) 命中质量：三小城 × 三病 各抽 3 个命中周（n_hits>0），每周随机取 1 个 v1 命中页，
   输出命中词 + 前后 45 字符上下文，供人工判定「真命中 / 误报」。
2) 漏检检验：随机抽 20 个「窗口内、三病均未命中」的页，用 v2 词表重扫，
   统计 v2 新增命中（估算 v1 漏检率上界）。

输出：analysis\\descriptive\\spot_check\\spot_check_hits.csv / spot_check_miss.csv / spot_check_summary.json
"""
import csv
import datetime
import json
import os
from pathlib import Path
import random
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_newspaper import PATTERNS as V2, WORDSETS as V2W, NEWS_ROOT, sunday_of

BASE = Path(__file__).resolve().parents[1]
HITS_CSV = os.path.join(BASE, "data", "cleaned", "newspaper", "newspaper_hits_weekly.csv")
OUT_DIR = os.path.join(BASE, "analysis", "descriptive", "spot_check")
os.makedirs(OUT_DIR, exist_ok=True)

CITIES = {"Baltimore": "Baltimore", "Cleveland": "Cleveland", "Los Angeles": "Los Angeles"}
DISEASES = ["INFLUENZA", "POLIOMYELITIS", "DIPHTHERIA"]

# v1 词表（原基线，用于对照）
V1 = {
    "INFLUENZA": ["influenza", "grippe", "grip", "flu", "spanish influenza"],
    "POLIOMYELITIS": ["polio", "poliomyelitis", "infantile paralysis",
                      "kinderlahmung", "kindergahmung", "poliomielitis"],
    "DIPHTHERIA": ["diphtheria", "diphtheritic", "antitoxin", "diphtherie", "difteria"],
}
V1P = {d: [re.compile(r"\b" + re.escape(w) + r"\b", re.IGNORECASE) for w in ws]
       for d, ws in V1.items()}


def read_text(fp):
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(fp, encoding=enc) as fh:
                return fh.read()
        except (UnicodeDecodeError, OSError):
            continue
    return ""


def pages_in_week(city, paper, sunday):
    """该报该周全部 ocr.txt（sunday..+6 天）。"""
    base = os.path.join(NEWS_ROOT, city, paper)
    if not os.path.isdir(base):
        return []
    out = []
    for i in range(7):
        d = sunday + datetime.timedelta(days=i)
        daydir = os.path.join(base, str(d.year), "%02d" % d.month, "%02d" % d.day)
        if not os.path.isdir(daydir):
            continue
        for ed in sorted(os.listdir(daydir)):
            eddir = os.path.join(daydir, ed)
            if not os.path.isdir(eddir):
                continue
            for seq in sorted(os.listdir(eddir)):
                seqdir = os.path.join(eddir, seq)
                if not os.path.isdir(seqdir):
                    continue
                for fn in os.listdir(seqdir):
                    if fn.lower() == "ocr.txt":
                        out.append(os.path.join(seqdir, fn))
    return out


def match_words(text, patterns):
    """返回命中的具体模式词（去重）与首处上下文。"""
    hits = []
    ctx = None
    for p in patterns:
        m = p.search(text)
        if m:
            hits.append(m.group(0))
            if ctx is None:
                s = max(0, m.start() - 45)
                e = min(len(text), m.end() + 45)
                ctx = text[s:e].replace("\n", " ")
    return hits, ctx


def main():
    random.seed(42)
    # 1) 命中周列表
    hit_weeks = defaultdict(set)  # (city, paper, disease) -> set(sunday_date)
    with open(HITS_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if int(row["n_hits"] or 0) > 0:
                hit_weeks[(row["city"], row["paper"], row["disease"])].add(row["sunday_date"])

    hit_rows = []
    per = 3
    for dis in DISEASES:
        for city in CITIES:
            cands = [(p, w) for (c, p, d), wset in hit_weeks.items()
                     if c == city and d == dis for w in wset]
            if not cands:
                hit_rows.append({"city": city, "disease": dis, "paper": "", "sunday_date": "",
                                 "file": "(no hit weeks)", "v1_words": "", "context": ""})
                continue
            random.shuffle(cands)
            for paper, wk in cands[:per]:
                files = pages_in_week(city, paper, datetime.date.fromisoformat(wk))
                v1_pages = []
                for fp in files:
                    txt = read_text(fp)
                    ws1, _ = match_words(txt, V1P[dis])
                    if ws1:
                        v1_pages.append((fp, ws1, txt))
                if not v1_pages:
                    hit_rows.append({"city": city, "disease": dis, "paper": paper, "sunday_date": wk,
                                     "file": "(week missing in raw)", "v1_words": "", "context": ""})
                    continue
                fp, ws1, txt = random.choice(v1_pages)
                v2w, ctx = match_words(txt, V2[dis])
                hit_rows.append({"city": city, "disease": dis, "paper": paper, "sunday_date": wk,
                                 "file": os.path.relpath(fp, NEWS_ROOT), "v1_words": "|".join(ws1),
                                 "v2_extra": "|".join([w for w in v2w if w not in ws1]),
                                 "context": (ctx or "")[:220]})

    # 2) 漏检抽样：随机 20 页（窗口内、对三病 v1 均未命中）
    miss_rows = []
    all_papers = {}
    for city in CITIES:
        for paper in os.listdir(os.path.join(NEWS_ROOT, city)):
            if paper.startswith("."):
                continue
            all_papers[(city, paper)] = True
    picked = 0
    while picked < 20:
        (city, paper) = random.choice(list(all_papers.keys()))
        # 随机取一个窗口年内某周
        year = random.choice([1916, 1917, 1918, 1919, 1920, 1921, 1922, 1930, 1931, 1932])
        try:
            d0 = datetime.date(year, 1, 1) + datetime.timedelta(days=random.randint(0, 350))
        except ValueError:
            continue
        wk = sunday_of(d0)
        if not (datetime.date(1915, 1, 1) <= wk <= datetime.date(1922, 12, 31) or
                datetime.date(1930, 1, 1) <= wk <= datetime.date(1932, 12, 31)):
            continue
        files = pages_in_week(city, paper, wk)
        if not files:
            continue
        fp = random.choice(files)
        txt = read_text(fp)
        anyv1 = any(match_words(txt, V1P[d])[0] for d in DISEASES)
        if anyv1:
            continue
        v2_new = []
        for d in DISEASES:
            ws2, ctx2 = match_words(txt, V2[d])
            if ws2:
                v2_new.append(d + ":" + "|".join(ws2) + " :: " + (ctx2 or "")[:120])
        miss_rows.append({"file": os.path.relpath(fp, NEWS_ROOT), "v2_new_hits": "; ".join(v2_new)})
        picked += 1

    with open(os.path.join(OUT_DIR, "spot_check_hits.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(hit_rows[0].keys()))
        w.writeheader()
        w.writerows(hit_rows)
    with open(os.path.join(OUT_DIR, "spot_check_miss.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "v2_new_hits"])
        w.writeheader()
        w.writerows(miss_rows)

    n_v2new = sum(1 for r in miss_rows if r["v2_new_hits"])
    summary = {
        "hit_samples": len(hit_rows),
        "hit_samples_missing_raw": sum(1 for r in hit_rows if r["file"] == "(week missing in raw)"),
        "miss_samples": len(miss_rows),
        "miss_with_v2_new_hits": n_v2new,
        "v2_recall_extra_rate_est": n_v2new / len(miss_rows) if miss_rows else None,
        "note": "v2_extra 为 v2 新增模式；context 供人工判定真命中/误报",
    }
    with open(os.path.join(OUT_DIR, "spot_check_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print("HITS SAMPLES:")
    for r in hit_rows:
        print(" | ".join([r["city"], r["disease"], r["paper"], r["sunday_date"], r["v1_words"], r["v2_extra"], r["context"][:90]]))
    print("MISS v2-new:")
    for r in miss_rows:
        if r["v2_new_hits"]:
            print(r["file"], "->", r["v2_new_hits"])


if __name__ == "__main__":
    main()
