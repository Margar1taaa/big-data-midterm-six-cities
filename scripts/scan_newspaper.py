# -*- coding: utf-8 -*-
"""报刊 OCR 母集索引与关键词检索（单源清洗·Raw -> Cleaned，仅本地三城）。

输入：data\\raw\\newspaper\\<City>\\<Paper>\\<Year>\\<Month>\\<Day>\\ed-N\\seq-N\\ocr.txt
解析：路径段 = [city, paper, year, month, day, ed, seq, ocr.txt]

输出：
1) newspaper_coverage_matrix.csv
   city, paper, year, sunday_date, n_issues(该周不同日期期数), n_pages(该周页数)
2) newspaper_hits_weekly.csv
   city, paper, disease, sunday_date, n_hits(命中页数), n_pages(扫描页数)
3) 每城每报每年覆盖摘要打印

词表（v2，2026-10-21 拓宽：词干匹配 + 历史/OCR 变体 + 德西短语；见 docs/GAPS.md G3）：
- INFLUENZA: influenz*（词干）、influensa*/influenzy（OCR 变体）、grippe*/gripe*（英德法西）、
  flu、spanish flu/influenza/grippe、spanische grippe（德）、grippe espagnole（法）、gripe espanola/ñ（西）、la grippe
- POLIOMYELITIS: poliomyelitis*/poliomyeli*、poliomyletis/poliomelitis（OCR 变体）、polio、
  infantile paralysis、paralisis/paralysis infantil（西）、kinderlahmung/kindergahmung/kinderlaemung/kinderlahm*（德）
- DIPHTHERIA: diphther*/diphter*（词干含 OCR 丢 h）、diphtherie/diphtheritis（德）、difteria（西）、
  membranous croup（旧称）、antitoxin（相关词，抽查复核）
命中规则：页级匹配（一页含该病种任一模式计 1 命中），大小写不敏感；
本脚本处理目录形式的三小城；华盛顿、纽约、密尔沃基由 scan_newspaper_zip.py 处理。

运行：python scan_newspaper.py
"""
import csv
import datetime
import os
from pathlib import Path
import re
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NEWS_ROOT = PROJECT_ROOT / "data" / "raw" / "newspaper"
OUT_DIR = PROJECT_ROOT / "data" / "cleaned" / "newspaper"

# 词表 v2 拆分（2026-10-22 单列口径，用户拍板）：
# STRONG = 强词（疾病语境明确，作正式指标）；WEAK = 弱词（误报率高，单列供敏感性分析）
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
# 编译正则（词边界，忽略大小写；模式为词干时以 \w* 控制后缀）
PATTERNS_S = {}
PATTERNS_W = {}
for dis, words in STRONG.items():
    PATTERNS_S[dis] = [re.compile(r"\b" + w + r"\b", re.IGNORECASE) for w in words]
for dis, words in WEAK.items():
    PATTERNS_W[dis] = [re.compile(r"\b" + w + r"\b", re.IGNORECASE) for w in words]


def sunday_of(d):
    return d - datetime.timedelta(days=(d.weekday() + 1) % 7)


def read_text(fp):
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(fp, encoding=enc) as fh:
                return fh.read()
        except (UnicodeDecodeError, OSError):
            continue
    return ""


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    out_cov = os.path.join(OUT_DIR, "newspaper_coverage_matrix.csv")
    out_hits = os.path.join(OUT_DIR, "newspaper_hits_weekly.csv")

    # (city, paper, year, sunday) -> set(day), pages
    cov = defaultdict(lambda: {"days": set(), "pages": 0})
    # (city, paper, disease, sunday) -> strong/weak hits, pages
    hits = defaultdict(lambda: {"strong": 0, "weak": 0, "pages": 0})
    n_files = 0
    n_bad = 0
    per_city = defaultdict(int)

    for city in sorted(os.listdir(NEWS_ROOT)):
        cdir = os.path.join(NEWS_ROOT, city)
        if not os.path.isdir(cdir):
            continue
        for root, _, files in os.walk(cdir):
            for fn in files:
                if fn.lower() != "ocr.txt":
                    continue
                fp = os.path.join(root, fn)
                rel = os.path.relpath(fp, NEWS_ROOT).split(os.sep)
                # [city, paper, year, month, day, ed, seq, ocr.txt]
                if len(rel) < 8:
                    n_bad += 1
                    continue
                c, paper, y, m, d = rel[0], rel[1], rel[2], rel[3], rel[4]
                try:
                    date = datetime.date(int(y), int(m), int(d))
                except ValueError:
                    n_bad += 1
                    continue
                sd = sunday_of(date)
                n_files += 1
                per_city[c] += 1
                key_cov = (c, paper, int(y), sd)
                cov[key_cov]["days"].add((int(m), int(d)))
                cov[key_cov]["pages"] += 1

                text = read_text(fp)
                for dis in STRONG:
                    s_hit = any(p.search(text) for p in PATTERNS_S[dis])
                    w_hit = any(p.search(text) for p in PATTERNS_W[dis])
                    key_h = (c, paper, dis, sd)
                    hits[key_h]["pages"] += 1
                    if s_hit:
                        hits[key_h]["strong"] += 1
                    elif w_hit:
                        hits[key_h]["weak"] += 1

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

    print("FILES=%d BAD=%d" % (n_files, n_bad))
    for c in sorted(per_city):
        print("CITY %s files=%d" % (c, per_city[c]))
    print("COV_ROWS=%d HIT_ROWS=%d" % (len(cov), len(hits)))
    # 每城每报每年覆盖摘要
    print("=== 每城每报每年覆盖（年份: 期数周数） ===")
    by = defaultdict(list)
    for (c, paper, y, sd), v in sorted(cov.items()):
        by[(c, paper)].append(y)
    for (c, paper), ys in sorted(by.items()):
        print("%-11s %-30s years=%s..%s n=%d" %
              (c, paper, min(ys), max(ys), len(set(ys))))
    print("OUT_COV=%s" % out_cov)
    print("OUT_HITS=%s" % out_hits)


if __name__ == "__main__":
    main()
