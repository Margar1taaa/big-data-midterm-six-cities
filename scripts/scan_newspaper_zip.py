# -*- coding: utf-8 -*-
"""报刊 OCR 扫描 · zip 直读模式（备用脚本，不落地解压）。

与 scripts\\scan_newspaper.py（目录模式）产出相同格式，但直接从 zip 流式读取：
- 目标 zip：data\\raw\\newspaper\\纽约_华盛顿_密尔沃基.zip（3.59GB / 267,322 页）
- 内部结构：<顶层(中文,cp437乱码需修复)>/<City>/<Paper>/<Year>/<Month>/<Day>/ed-N/seq-N/ocr.txt
- 顶层中文名修复：zipfile 默认 cp437 解码 -> 手动 name.encode('cp437').decode('utf-8')
- 过滤：__MACOSX / .DS_Store / 目录条目 / 非 ocr.txt
- 空缺兼容：路径段不足或日期非法只计数（n_skip），不崩溃；"空缺子目录"由 coverage 矩阵的年/周缺口自然呈现
- 词表（v2，2026-10-21 拓宽，与 scan_newspaper.py 一致；见 docs\\GAPS.md G3）

用法：
  python scan_newspaper_zip.py            # 全量扫描（约 26.7 万页，耗时较长）
  python scan_newspaper_zip.py --verify 5 # 只处理前 N 个 ocr.txt，验证读取/解码/命中逻辑
输出：
  data\\cleaned\\newspaper\\newspaper_coverage_matrix_zip.csv
  data\\cleaned\\newspaper\\newspaper_hits_weekly_zip.csv
"""
import csv
import datetime
import json
import os
from pathlib import Path
import re
import sys
import time
import zipfile
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ZIP = PROJECT_ROOT / "data" / "raw" / "newspaper" / "纽约_华盛顿_密尔沃基.zip"
OUT_DIR = PROJECT_ROOT / "data" / "cleaned" / "newspaper"

# 词表 v2 拆分（2026-10-22 单列口径，用户拍板，与 scan_newspaper.py 一致）：
# STRONG = 强词（正式指标）；WEAK = 弱词（误报率高，单列供敏感性分析）
STRONG = {
    "INFLUENZA": [
        r"influenz\w*", r"influensa\w*", r"influenzy",
        r"grippe\w*", r"gripe\w*",
        r"spanish flu", r"spanish influenza", r"spanish grippe",
        r"spanische grippe", r"grippe espagnole",
        r"gripe espanola", r"gripe española", r"la grippe",
    ],
    "POLIOMYELITIS": [
        r"poliomyelitis\w*", r"poliomyeli\w*",
        r"poliomyletis", r"poliomelitis", r"poliomielitis",
        r"infantile paralysis",
        r"paralisis infantil", r"paralysis infantil",
        r"kinderlahmung", r"kindergahmung", r"kinderlaemung", r"kinderlaehmung", r"kinderlahm\w*",
    ],
    "DIPHTHERIA": [
        r"diphther\w*", r"diphter\w*",
        r"diphtherie", r"diphtheritis",
        r"difteria", r"membranous croup",
    ],
}
WEAK = {
    "INFLUENZA": [r"flu"],
    "POLIOMYELITIS": [r"polio"],
    "DIPHTHERIA": [r"antitoxin"],
}
PATTERNS_S = {d: [re.compile(r"\b" + w + r"\b", re.IGNORECASE)
                  for w in ws] for d, ws in STRONG.items()}
PATTERNS_W = {d: [re.compile(r"\b" + w + r"\b", re.IGNORECASE)
                  for w in ws] for d, ws in WEAK.items()}


def fix_name(name):
    """顶层中文目录名修复：cp437 -> utf-8。"""
    try:
        return name.encode("cp437").decode("utf-8")
    except Exception:
        return name


def sunday_of(d):
    return d - datetime.timedelta(days=(d.weekday() + 1) % 7)


def parse_entry(name):
    """解析 <顶层>/City/Paper/Year/Month/Day/ed-N/seq-N/ocr.txt -> 元组。非法返回 None。"""
    parts = name.split("/")
    if len(parts) < 9 or parts[-1].lower() != "ocr.txt":
        return None
    city, paper = parts[1], parts[2]
    try:
        date = datetime.date(int(parts[3]), int(parts[4]), int(parts[5]))
    except (ValueError, IndexError):
        return None
    return city, paper, date


def read_member(zf, name):
    try:
        raw = zf.read(name)
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        return ""
    except Exception:
        return ""


def main():
    verify_n = 0
    args = sys.argv[1:]
    if args and args[0] == "--verify":
        verify_n = int(args[1]) if len(args) > 1 else 5

    os.makedirs(OUT_DIR, exist_ok=True)
    cov = defaultdict(lambda: {"days": set(), "pages": 0})
    hits = defaultdict(lambda: {"strong": 0, "weak": 0, "pages": 0})
    n_files = n_skip = 0
    v_bytes = 0
    v_hits = 0
    per_city = defaultdict(int)

    with zipfile.ZipFile(ZIP) as zf:
        # 原始条目名用于 zf.read；fix_name 后的名字用于路径解析
        pairs = [(n, fix_name(n)) for n in zf.namelist()]
        ocr_pairs = [(orig, fixed) for orig, fixed in pairs
                     if not fixed.startswith("__MACOSX")
                     and not fixed.endswith("/")
                     and fixed.split("/")[-1].lower() == "ocr.txt"
                     and ".DS_Store" not in fixed]
        if verify_n:
            ocr_pairs = ocr_pairs[:verify_n]
        t0 = time.time()
        t_last = 0.0
        for orig, fixed in ocr_pairs:
            ent = parse_entry(fixed)
            if ent is None:
                n_skip += 1
                continue
            city, paper, date = ent
            sd = sunday_of(date)
            n_files += 1
            per_city[city] += 1
            cov[(city, paper, date.year, sd)]["days"].add((date.month, date.day))
            cov[(city, paper, date.year, sd)]["pages"] += 1
            text = read_member(zf, orig)
            v_bytes += len(text)
            for dis in STRONG:
                key = (city, paper, dis, sd)
                hits[key]["pages"] += 1
                s_hit = any(p.search(text) for p in PATTERNS_S[dis])
                w_hit = any(p.search(text) for p in PATTERNS_W[dis])
                if s_hit:
                    hits[key]["strong"] += 1
                    v_hits += 1
                elif w_hit:
                    hits[key]["weak"] += 1
                    v_hits += 1
            if not verify_n and time.time() - t_last >= 2.0:
                t_last = time.time()
                el = t_last - t0
                rate = n_files / el
                eta = el / n_files * (len(ocr_pairs) - n_files)
                print("PROGRESS files=%d elapsed=%.0fs rate=%.1f/s eta=%.0fs"
                      % (n_files, el, rate, eta), flush=True)
                try:
                    with open(os.path.join(OUT_DIR, "scan_progress.json"), "w",
                              encoding="utf-8") as f:
                        json.dump({"processed": n_files, "total": len(ocr_pairs),
                                   "pct": round(n_files / len(ocr_pairs) * 100, 2),
                                   "rate": round(rate, 1), "eta": round(eta, 0)}, f)
                except Exception:
                    pass

    if verify_n:
        print("VERIFY_MODE files=%d skip=%d text_bytes=%d avg_bytes=%.0f hits_total=%d"
              % (n_files, n_skip, v_bytes, v_bytes / n_files if n_files else 0, v_hits))
        for c in sorted(per_city):
            print("  CITY %s files=%d" % (c, per_city[c]))
        print("OK: zip read/decode/parse/match chain usable (text non-empty & hits>0 required)")
        return

    out_cov = os.path.join(OUT_DIR, "newspaper_coverage_matrix_zip.csv")
    out_hits = os.path.join(OUT_DIR, "newspaper_hits_weekly_zip.csv")
    with open(out_cov, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["city", "paper", "year", "sunday_date", "n_issues", "n_pages"])
        for (c, paper, y, sd), v in sorted(cov.items()):
            w.writerow([c, paper, y, sd.isoformat(), len(v["days"]), v["pages"]])
    with open(out_hits, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["city", "paper", "disease", "sunday_date",
                    "n_hits", "n_hits_strong", "n_hits_weak", "n_pages"])
        for (c, paper, dis, sd), v in sorted(hits.items()):
            w.writerow([c, paper, dis, sd.isoformat(),
                        v["strong"] + v["weak"], v["strong"], v["weak"], v["pages"]])

    print("FILES=%d SKIP=%d" % (n_files, n_skip))
    for c in sorted(per_city):
        print("CITY %s files=%d" % (c, per_city[c]))
    print("COV_ROWS=%d HIT_ROWS=%d" % (len(cov), len(hits)))
    print("OUT_COV=%s" % out_cov)
    print("OUT_HITS=%s" % out_hits)


if __name__ == "__main__":
    main()
