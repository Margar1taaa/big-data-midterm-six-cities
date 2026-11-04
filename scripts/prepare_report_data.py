# -*- coding: utf-8 -*-
"""汇总描述性分析报告数据：读 cleaned 各源 + descriptive CSV，聚合为 report_data.json。

输出：analysis\\descriptive\\report_data.json（供 descriptive_report.html 内联使用）
"""
import csv
import datetime
import json
import os
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
CLN = os.path.join(ROOT, "data", "cleaned")
DESC = os.path.join(ROOT, "analysis", "descriptive")
CITIES = ["BALTIMORE", "CLEVELAND", "LOS ANGELES", "MILWAUKEE", "NEW YORK", "WASHINGTON"]


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    out = {}

    # --- Tycho cleaned: 每城每病种每年病例/死亡合计 ---
    tycho_year = defaultdict(lambda: defaultdict(float))
    for row in read_csv(os.path.join(CLN, "tycho", "cleaned_tycho_weekly_sixcities.csv")):
        y = row["year"].strip()
        if not y.isdigit():
            continue
        num = row["number"].strip()
        if not num:
            continue
        try:
            v = float(num)
        except ValueError:
            continue
        key = "%s|%s|%s" % (row["city"], row["disease"], row["event"])
        tycho_year[key][int(y)] += v
    # 转成六城×病种×事件 的年序列
    out["tycho_year"] = {}
    for k, yd in tycho_year.items():
        out["tycho_year"][k] = {str(y): round(v, 1) for y, v in sorted(yd.items())}

    # --- NOAA cleaned: 每城每年 tavg 均值 / prcp 年总 ---
    noaa_year = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0, 0]))
    for row in read_csv(os.path.join(CLN, "noaa", "noaa_weekly_sixcities.csv")):
        sd = row["sunday_date"].strip()
        y = sd[:4]
        t = row["tavg_avg"].strip()
        p = row["prcp_sum"].strip()
        c = row["city"]
        if t:
            try:
                noaa_year[c][y][0] += float(t)
                noaa_year[c][y][2] += 1
            except ValueError:
                pass
        if p:
            try:
                noaa_year[c][y][1] += float(p)
            except ValueError:
                pass
    out["noaa_year"] = {}
    for c, yd in noaa_year.items():
        out["noaa_year"][c] = {}
        for y, (ts, ps, n) in sorted(yd.items()):
            if n:
                out["noaa_year"][c][y] = {"tavg": round(ts / n, 2), "prcp": round(ps, 2)}

    # --- 人口 ---
    pop = defaultdict(dict)
    for row in read_csv(os.path.join(CLN, "nhgis", "population_clean.csv")):
        pop[row["city_name"]][int(row["census_year"])] = int(row["population"])
    out["population"] = {c: {str(y): v for y, v in sorted(d.items())}
                         for c, d in pop.items()}

    # --- 报刊 ---
    out["news_3cities"] = read_csv(os.path.join(DESC, "newspaper_3cities_stats.csv"))
    out["news_zip"] = read_csv(os.path.join(DESC, "newspaper_zip_stats.csv"))
    out["news_text"] = read_csv(os.path.join(DESC, "newspaper_text_stats.csv"))
    out["tycho_cleaned_stats"] = read_csv(os.path.join(DESC, "tycho_cleaned_stats.csv"))
    out["noaa_cleaned_stats"] = read_csv(os.path.join(DESC, "noaa_cleaned_stats.csv"))
    out["nhgis_stats"] = read_csv(os.path.join(DESC, "nhgis_stats.csv"))

    with open(os.path.join(DESC, "report_data.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("REPORT_DATA_WRITTEN")


if __name__ == "__main__":
    main()
