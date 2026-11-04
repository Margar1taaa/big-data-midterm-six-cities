# -*- coding: utf-8 -*-
"""
build_integrated.py
将 Tycho(疫情) + NOAA(气象) + NHGIS(人口) + 报刊(六城命中) 融合为
「城 × 周」宽表，裁剪到研究两段窗口：1915–1922 与 1930–1932（共 11 年）。

口径（2026-10-21 用户拍板）：
- 窗口 = 周标签(周日日期) ∈ [1915-01-01, 1922-12-31] ∪ [1930-01-01, 1932-12-31]
- 流感 Tycho 前段(1915–1919)无数据 → NA，该段流感关注度由报刊列承担
- 人口 = 普查年间按年线性插值（推翻 G8 原"不插值"，README/GAPS 已同步）
- 缺值一律 NA（不补 0）；报刊 = 六城（三小城表 + 大三城 zip 表，2026-10-22 并入，
  两表均词表 v2 页级口径；2026-10-22 单列：np_*_hits 为强词命中、np_*_hits_weak 为弱词单列）
- Tycho 同 (city, week, disease, event) 重复取 max（G5 推荐口径）
"""
import csv
import json
import os
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parents[1]
CLEAN = os.path.join(BASE, "data", "cleaned")
OUT_DIR = os.path.join(BASE, "data", "integrated")
os.makedirs(OUT_DIR, exist_ok=True)

CITIES = ["BALTIMORE", "CLEVELAND", "LOS ANGELES", "MILWAUKEE", "NEW YORK", "WASHINGTON"]
CITY_MAP = {"Baltimore": "BALTIMORE", "Cleveland": "CLEVELAND", "Los Angeles": "LOS ANGELES",
            "Milwaukee": "MILWAUKEE", "New York": "NEW YORK", "Washington": "WASHINGTON"}
DIS_EV = [("INFLUENZA", "CASES"), ("INFLUENZA", "DEATHS"),
          ("DIPHTHERIA", "CASES"), ("DIPHTHERIA", "DEATHS"),
          ("POLIOMYELITIS", "CASES")]
COL_FLU = {"INFLUENZA|CASES": "flu_cases", "INFLUENZA|DEATHS": "flu_deaths",
           "DIPHTHERIA|CASES": "diph_cases", "DIPHTHERIA|DEATHS": "diph_deaths",
           "POLIOMYELITIS|CASES": "polio_cases"}

from datetime import date, timedelta


def sunday_of(d):
    """该自然日所在周的周日（周定义：周日开始，标签=周日日期）。"""
    return d + timedelta(days=(6 - d.weekday()))


def window_sundays():
    sundays = set()
    for (s, e) in ((date(1915, 1, 1), date(1922, 12, 31)),
                   (date(1930, 1, 1), date(1932, 12, 31))):
        d = s
        while d <= e:
            sundays.add(sunday_of(d))
            d += timedelta(days=1)
    return sorted(sundays)


def read_tycho():
    """返回 {(city, sunday): {col: value}}，重复键取 max。"""
    path = os.path.join(CLEAN, "tycho", "cleaned_tycho_weekly_sixcities.csv")
    out = defaultdict(dict)
    dup_n = 0
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            city = row["city"]
            if city not in CITIES:
                continue
            key = (city, row["disease"], row["event"], row["from_date"])
            col = COL_FLU.get(row["disease"] + "|" + row["event"])
            if col is None:
                continue
            val = float(row["number"]) if row["number"] not in ("", "NA", "NaN") else None
            if val is None:
                continue
            wk = sunday_of(date.fromisoformat(row["from_date"]))
            ck = (city, wk)
            if col in out[ck]:
                dup_n += 1
                if val > out[ck][col]:
                    out[ck][col] = val
            else:
                out[ck][col] = val
    print("[tycho] dup_rows_taken_max=%d" % dup_n)
    return out


def read_noaa():
    path = os.path.join(CLEAN, "noaa", "noaa_weekly_sixcities.csv")
    out = {}
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            out[(row["city"], row["sunday_date"])] = row
    return out


def read_pop():
    """{city: {year: pop}} + 线性插值函数。"""
    path = os.path.join(CLEAN, "nhgis", "population_clean.csv")
    pts = defaultdict(dict)
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            tc = row["tycho_city"]
            pts[tc][int(row["census_year"])] = float(row["population"])
    return {c: dict(pts[c]) for c in CITIES}


def interp_pop(pts, year):
    ys = sorted(pts.keys())
    if year in pts:
        return pts[year]
    for a, b in zip(ys, ys[1:]):
        if a <= year <= b:
            pa, pb = pts[a], pts[b]
            return pa + (pb - pa) * (year - a) / (b - a)
    return None


def read_newspaper():
    """按 (city, sunday) 汇总三病 strong/weak 命中页数与总页数（六城，单列口径）。
    兼容旧表：无 strong/weak 列时 n_hits 全计入 strong、weak=0。"""
    hits = defaultdict(lambda: {"INFLUENZA": {"strong": 0, "weak": 0},
                                "POLIOMYELITIS": {"strong": 0, "weak": 0},
                                "DIPHTHERIA": {"strong": 0, "weak": 0}})
    pages = defaultdict(int)
    for path in ("newspaper_hits_weekly.csv", "newspaper_hits_weekly_zip.csv"):
        p = os.path.join(CLEAN, "newspaper", path)
        if not os.path.exists(p):
            print("[newspaper] skip missing %s" % p)
            continue
        with open(p, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                city = CITY_MAP.get(row["city"])
                if city is None:
                    continue
                wk = row["sunday_date"]
                key = (city, wk)
                dis = row["disease"].upper()
                if dis not in hits[key]:
                    continue
                if "n_hits_strong" in row and row["n_hits_strong"] != "":
                    st = int(row["n_hits_strong"] or 0)
                    wk_ = int(row["n_hits_weak"] or 0)
                else:
                    st = int(row["n_hits"] or 0)
                    wk_ = 0
                hits[key][dis]["strong"] += st
                hits[key][dis]["weak"] += wk_
                np_ = int(row["n_pages"] or 0)
                if np_ > pages[key]:
                    pages[key] = np_
    return hits, pages


def main():
    sundays = window_sundays()
    print("[window] sunday_weeks=%d" % len(sundays))
    tycho = read_tycho()
    noaa = read_noaa()
    pts = read_pop()
    np_hits, np_pages = read_newspaper()

    cols = ["city", "sunday_date", "year",
            "flu_cases", "flu_deaths", "diph_cases", "diph_deaths", "polio_cases",
            "tavg_avg", "tmax_avg", "tmin_avg", "prcp_sum", "snow_sum", "n_days", "n_stations",
            "population",
            "np_flu_hits", "np_flu_hits_weak",
            "np_polio_hits", "np_polio_hits_weak",
            "np_diph_hits", "np_diph_hits_weak",
            "np_pages"]
    rows = []
    stats = defaultdict(lambda: defaultdict(int))  # source -> col -> non-na
    for city in CITIES:
        for wk in sundays:
            r = {"city": city, "sunday_date": wk.isoformat(), "year": wk.year}
            t = tycho.get((city, wk), {})
            for col in ["flu_cases", "flu_deaths", "diph_cases", "diph_deaths", "polio_cases"]:
                v = t.get(col)
                r[col] = "" if v is None else round(v, 1)
                if v is not None:
                    stats["tycho"][col] += 1
            n = noaa.get((city, wk.isoformat()))
            for col in ["tavg_avg", "tmax_avg", "tmin_avg", "prcp_sum", "snow_sum", "n_days", "n_stations"]:
                v = n.get(col, "") if n else ""
                r[col] = v
                if v not in ("", None):
                    stats["noaa"][col] += 1
            p = interp_pop(pts[city], wk.year)
            r["population"] = "" if p is None else round(p)
            if p is not None:
                stats["nhgis"]["population"] += 1
            nh = np_hits.get((city, wk.isoformat()), {})
            r["np_flu_hits"] = nh.get("INFLUENZA", {}).get("strong", 0)
            r["np_flu_hits_weak"] = nh.get("INFLUENZA", {}).get("weak", 0)
            r["np_polio_hits"] = nh.get("POLIOMYELITIS", {}).get("strong", 0)
            r["np_polio_hits_weak"] = nh.get("POLIOMYELITIS", {}).get("weak", 0)
            r["np_diph_hits"] = nh.get("DIPHTHERIA", {}).get("strong", 0)
            r["np_diph_hits_weak"] = nh.get("DIPHTHERIA", {}).get("weak", 0)
            r["np_pages"] = np_pages.get((city, wk.isoformat()), 0)
            if r["np_pages"] > 0:
                stats["newspaper"]["np_pages"] += 1
            rows.append(r)

    out_csv = os.path.join(OUT_DIR, "weekly_sixcities_1915_1922_1930_1932.csv")
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    summary = {
        "window_weeks_per_city": len(sundays),
        "total_rows": len(rows),
        "non_na": {k: dict(v) for k, v in stats.items()},
        "pop_interp_years": {c: {str(y): interp_pop(pts[c], y) for y in range(1915, 1933)} for c in CITIES},
    }
    with open(os.path.join(OUT_DIR, "integrated_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    print("[integrated] rows=%d -> %s" % (len(rows), out_csv))
    print("[stats] %s" % json.dumps({k: dict(v) for k, v in stats.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
