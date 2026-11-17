# -*- coding: utf-8 -*-
"""覆盖缺口矩阵（不重复已有描述性分析）。

1) coverage_gaps_matrix.csv：六城 × 三病 × 两事件的覆盖区间与缺口清单
   - 依据 data\\cleaned\\tycho\\cleaned_tycho_weekly_sixcities.csv 实际年份集合
   - 中间断档 = [data_min, data_max] 内未覆盖年份；窗口缺口 = 研究窗口 1916–1953 内未覆盖年份
报刊ZIP约3.85GB，本脚本不再打开或枚举其中央目录。报刊覆盖统计直接使用
data/cleaned/newspaper/newspaper_coverage_matrix_zip.csv。

运行：python coverage_gaps.py
"""
import csv
import datetime
import json
import os
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA = os.path.join(ROOT, "data")
CLN = os.path.join(DATA, "cleaned")
OUT = os.path.join(ROOT, "analysis", "descriptive")

CITIES = ["BALTIMORE", "CLEVELAND", "LOS ANGELES", "MILWAUKEE", "NEW YORK", "WASHINGTON"]
DISEASES = ["DIPHTHERIA", "INFLUENZA", "POLIOMYELITIS"]
WINDOW = (1916, 1953)


def yr_range(lo, hi, present):
    """[lo, hi] 内未覆盖年份列表（连续段压缩为 'a–b' 字符串列表）。"""
    missing = [y for y in range(lo, hi + 1) if y not in present]
    if not missing:
        return []
    segs = []
    s = p = missing[0]
    for y in missing[1:]:
        if y == p + 1:
            p = y
        else:
            segs.append(str(s) if s == p else "%d–%d" % (s, p))
            s = p = y
    segs.append(str(s) if s == p else "%d–%d" % (s, p))
    return segs


def main():
    os.makedirs(OUT, exist_ok=True)

    # ---------- 1) Tycho 覆盖缺口矩阵 ----------
    grp_years = defaultdict(set)
    with open(os.path.join(CLN, "tycho", "cleaned_tycho_weekly_sixcities.csv"),
              encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            y = row["year"].strip()
            if y.isdigit():
                grp_years[(row["city"], row["disease"], row["event"])].add(int(y))

    rows = []
    for city in CITIES:
        for dis in DISEASES:
            for ev in ("CASES", "DEATHS"):
                key = (city, dis, ev)
                ys = grp_years.get(key)
                if not ys:
                    rows.append([city, dis, ev, "", "", 0, 0, 0, "全部缺失", "", ""])
                    continue
                lo, hi = min(ys), max(ys)
                inside = yr_range(lo, hi, ys)                       # 区间内断档
                win_lo = max(WINDOW[0], lo)
                win_hi = min(WINDOW[1], hi)
                win_missing = [y for y in range(win_lo, win_hi + 1) if y not in ys]
                before = yr_range(WINDOW[0], lo - 1, set()) if lo > WINDOW[0] else []
                after = yr_range(hi + 1, WINDOW[1], set()) if hi < WINDOW[1] else []
                gap_desc = ";".join((["区间内断档:" + ",".join(inside)] if inside else [])
                                     + (["窗口前缺:" + ",".join(before)] if before else [])
                                     + (["窗口后缺:" + ",".join(after)] if after else []))
                if not gap_desc:
                    gap_desc = "窗口内连续覆盖"
                rows.append([city, dis, ev, lo, hi, len(ys),
                             len(set(range(WINDOW[0], WINDOW[1] + 1)) & ys),
                             len(win_missing), gap_desc,
                             ";".join(map(str, win_missing)),
                             ";".join(map(str, sorted(ys)))])
    header = ["city", "disease", "event", "data_min_year", "data_max_year",
              "n_years_covered", "n_years_in_window", "n_missing_in_window",
              "gap_description", "missing_years_in_window", "all_years"]
    with open(os.path.join(OUT, "coverage_gaps_matrix.csv"), "w",
              encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

    # 汇总 JSON（供报告渲染）
    summary = defaultdict(list)
    for r in rows:
        summary[r[1]].append({"city": r[0], "event": r[2], "min": r[3], "max": r[4],
                              "gap": r[8]})
    with open(os.path.join(OUT, "coverage_gaps_summary.json"), "w",
              encoding="utf-8") as f:
        json.dump({k: v for k, v in summary.items()}, f, ensure_ascii=False, indent=1)
    print("GAPS_ROWS=%d" % len(rows))

    # ---------- 2) ZIP 批次年度覆盖：只读小型 cleaned coverage，不打开大型 ZIP ----------
    zcp = defaultdict(lambda: {"pages": 0, "months": set()})
    coverage_path = os.path.join(CLN, "newspaper", "newspaper_coverage_matrix_zip.csv")
    with open(coverage_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            date = datetime.date.fromisoformat(row["sunday_date"])
            year = int(row["year"])
            key = (row["city"], row["paper"], year)
            zcp[key]["pages"] += int(row["n_pages"])
            zcp[key]["months"].add(date.month)
    zrows = []
    for (city, paper, y), v in sorted(zcp.items()):
        mset = sorted(v["months"])
        miss_m = [m for m in range(1, 13) if m not in mset]
        zrows.append([city, paper, y, v["pages"], len(mset),
                      ";".join(map(str, miss_m)) if miss_m else ""])
    with open(os.path.join(OUT, "newspaper_zip_yearly_stats.csv"), "w",
              encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["city", "paper", "year", "pages", "n_months", "missing_months"])
        w.writerows(zrows)
    print("ZIP_YEARLY_ROWS=%d" % len(zrows))


if __name__ == "__main__":
    main()
