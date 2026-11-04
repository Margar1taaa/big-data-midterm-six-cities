# -*- coding: utf-8 -*-
"""描述性分析：对 raw 与 cleaned 全部数据源做描述统计。

覆盖（输出到 analysis\\descriptive\\）：
1) tycho_raw_stats.csv        raw Tycho 全量概况（行/列/疾病/时间/六城/缺失）
2) tycho_cleaned_stats.csv    清洗后每 (city,disease,event) 行数/数值分布/覆盖
3) noaa_raw_stats.csv         raw NOAA 每城每文件概况（行/日期范围/要素缺失率）
4) noaa_cleaned_stats.csv     清洗后每城周数/气温降水分布/站数/缺周
5) nhgis_stats.csv            六城坐标范围 + 人口普查序列与十年增长率
6) newspaper_3cities_stats.csv 三城报刊每城每报页数/年份/命中汇总
7) newspaper_text_stats.csv   三城报刊每城每报字符统计（min/median/mean/max/空页）
8) newspaper_zip_stats.csv    zip 三城结构统计（页数/年份覆盖/空缺，只读 namelist）
9) all_summary.json           汇总

运行：python describe_sources.py（报刊文本统计约 3-5 分钟）
"""
import csv
import datetime
import json
import os
from pathlib import Path
import statistics
import zipfile
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DATA = os.path.join(ROOT, "data")
RAW = os.path.join(DATA, "raw")
CLN = os.path.join(DATA, "cleaned")
OUT = os.path.join(ROOT, "analysis", "descriptive")

CITIES = ["BALTIMORE", "CLEVELAND", "LOS ANGELES", "MILWAUKEE", "NEW YORK", "WASHINGTON"]
ZIP_PATH = os.path.join(RAW, "newspaper", "纽约_华盛顿_密尔沃基.zip")


def pct(x):
    return round(x, 4)


def num_stats(vals):
    if not vals:
        return {"n": 0}
    v = sorted(vals)
    n = len(v)
    return {"n": n,
            "min": round(v[0], 2),
            "p25": round(v[n // 4], 2),
            "median": round(v[n // 2], 2),
            "mean": round(sum(v) / n, 2),
            "p75": round(v[(3 * n) // 4], 2),
            "max": round(v[-1], 2)}


def wcsv(path, header, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main():
    os.makedirs(OUT, exist_ok=True)
    summary = {}

    # ---------- 1) Tycho raw ----------
    src_tycho = os.path.join(RAW, "tycho", "ProjectTycho_LEVEL2_1900_1960_all_diseases.csv")
    n = 0
    cols = None
    diseases = defaultdict(int)
    events = defaultdict(int)
    years = set()
    n_missing = 0
    city_hits = defaultdict(int)
    with open(src_tycho, encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        cols = list(r.fieldnames or [])
        for row in r:
            n += 1
            diseases[row.get("disease", "")] += 1
            events[row.get("event", "")] += 1
            y = row.get("year", "").strip()
            if y.isdigit():
                years.add(int(y))
            num = row.get("number", "").strip()
            if num in ("", "NA", "NULL"):
                n_missing += 1
            loc = row.get("loc", "").strip()
            st = row.get("state", "").strip()
            if loc == "BALTIMORE" and st == "MD":
                city_hits["BALTIMORE"] += 1
            elif loc == "CLEVELAND" and st == "OH":
                city_hits["CLEVELAND"] += 1
            elif loc == "LOS ANGELES" and st == "CA":
                city_hits["LOS ANGELES"] += 1
            elif loc == "MILWAUKEE" and st == "WI":
                city_hits["MILWAUKEE"] += 1
            elif loc == "NEW YORK" and st == "NY":
                city_hits["NEW YORK"] += 1
            elif loc == "WASHINGTON" and st == "DC":
                city_hits["WASHINGTON"] += 1
    rows = [["rows", n], ["columns", ";".join(cols)],
            ["year_min", min(years) if years else ""],
            ["year_max", max(years) if years else ""],
            ["n_diseases", len(diseases)], ["diseases", ";".join(sorted(diseases))],
            ["events", ";".join(sorted(events))],
            ["missing_number", n_missing], ["missing_number_pct", pct(n_missing / n)]]
    for c in CITIES:
        rows.append(["raw_rows_%s" % c, city_hits[c]])
    wcsv(os.path.join(OUT, "tycho_raw_stats.csv"), ["metric", "value"], rows)
    summary["tycho_raw"] = {"rows": n, "diseases": len(diseases), "years": [min(years), max(years)],
                            "missing_number_pct": pct(n_missing / n),
                            "city_raw_rows": dict(city_hits)}
    print("TYCHO_RAW rows=%d" % n)

    # ---------- 2) Tycho cleaned ----------
    cln_tycho = os.path.join(CLN, "tycho", "cleaned_tycho_weekly_sixcities.csv")
    grp = defaultdict(list)  # (city,disease,event) -> numbers
    grp_rows = defaultdict(int)
    grp_years = defaultdict(set)
    grp_dates = defaultdict(set)
    with open(cln_tycho, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            key = (row["city"], row["disease"], row["event"])
            grp_rows[key] += 1
            y = row["year"].strip()
            if y.isdigit():
                grp_years[key].add(int(y))
            d = row["from_date"].strip()
            if d:
                try:
                    grp_dates[key].add(datetime.date.fromisoformat(d))
                except ValueError:
                    pass
            num = row["number"].strip()
            if num:
                try:
                    grp[key].append(float(num))
                except ValueError:
                    pass
    trows = []
    for c in CITIES:
        for dis in ("DIPHTHERIA", "INFLUENZA", "POLIOMYELITIS"):
            for ev in ("CASES", "DEATHS"):
                key = (c, dis, ev)
                if key not in grp_rows:
                    continue
                s = num_stats(grp[key])
                dates = grp_dates[key]
                d0, d1 = (min(dates), max(dates)) if dates else (None, None)
                missing_weeks = ""
                if d0 and d1:
                    exp = (d1 - d0).days // 7 + 1
                    missing_weeks = exp - len(dates)
                ys = grp_years[key]
                trows.append([c, dis, ev, grp_rows[key],
                              (min(ys) if ys else ""), (max(ys) if ys else ""),
                              s.get("min", ""), s.get("median", ""),
                              s.get("mean", ""), s.get("max", ""),
                              s["n"] - grp_rows[key], missing_weeks])
    wcsv(os.path.join(OUT, "tycho_cleaned_stats.csv"),
         ["city", "disease", "event", "rows", "year_min", "year_max",
          "number_min", "number_median", "number_mean", "number_max",
          "missing_number", "missing_weeks"], trows)
    summary["tycho_cleaned"] = {"total_rows": sum(grp_rows.values()), "groups": len(grp_rows)}
    print("TYCHO_CLEANED groups=%d rows=%d" % (len(grp_rows), sum(grp_rows.values())))

    # ---------- 3) NOAA raw ----------
    noaa_root = os.path.join(RAW, "noaa", "NOAA_DATA")
    nrows = []
    for city in CITIES:
        cdir = os.path.join(noaa_root, "NOAA_" + {"BALTIMORE": "Baltimore", "CLEVELAND": "Cleveland",
                                                  "LOS ANGELES": "Losangles", "MILWAUKEE": "Milwaukee",
                                                  "NEW YORK": "NewYork", "WASHINGTON": "Washington"}[city])
        if not os.path.isdir(cdir):
            continue
        for fn in sorted(os.listdir(cdir)):
            if not fn.endswith(".csv") or fn.endswith("_long.csv") or fn in (
                    "file_mapping_and_summary.csv", "conversion_summary.csv"):
                continue
            fp = os.path.join(cdir, fn)
            total = 0
            dmin, dmax = None, None
            missing = defaultdict(int)
            any_value = 0
            try:
                fh = None
                for enc in ("utf-8-sig", "latin-1"):
                    try:
                        fh = open(fp, encoding=enc, newline="")
                        rows = list(csv.DictReader(fh))
                        break
                    except UnicodeDecodeError:
                        if fh:
                            fh.close()
                        continue
                if fh is None:
                    nrows.append([city, fn, 0, "", "", "", "", "", "", "", 0])
                    continue
                for row in rows:
                    total += 1
                    d = row.get("DATE", "").strip()
                    if d:
                        try:
                            dd = datetime.date.fromisoformat(d)
                            dmin = dd if dmin is None or dd < dmin else dmin
                            dmax = dd if dmax is None or dd > dmax else dmax
                        except ValueError:
                            pass
                    has_any = False
                    for e in ("PRCP", "SNOW", "SNWD", "TMAX", "TMIN", "TAVG"):
                        if (row.get(e) or "").strip() in ("",):
                            missing[e] += 1
                        else:
                            has_any = True
                    if has_any:
                        any_value += 1
                fh.close()
            except Exception:
                nrows.append([city, fn, 0, "", "", "", "", "", "", "", 0])
                continue
            nrows.append([city, fn, total,
                          dmin.isoformat() if dmin else "", dmax.isoformat() if dmax else "",
                          pct(missing["PRCP"] / total), pct(missing["SNOW"] / total),
                          pct(missing["TMIN"] / total), pct(missing["TMAX"] / total),
                          pct(missing["TAVG"] / total), any_value])
    wcsv(os.path.join(OUT, "noaa_raw_stats.csv"),
         ["city", "file", "rows", "date_min", "date_max", "prcp_missing_pct",
          "snow_missing_pct", "tmin_missing_pct", "tmax_missing_pct", "tavg_missing_pct",
          "rows_with_any_value"], nrows)
    summary["noaa_raw"] = {"files": len(nrows)}
    print("NOAA_RAW files=%d" % len(nrows))

    # ---------- 4) NOAA cleaned ----------
    cln_noaa = os.path.join(CLN, "noaa", "noaa_weekly_sixcities.csv")
    nw = defaultdict(lambda: defaultdict(list))
    ns_days = defaultdict(list)
    weeks_city = defaultdict(set)
    with open(cln_noaa, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            c = row["city"]
            weeks_city[c].add(row["sunday_date"])
            for e in ("tavg_avg", "tmax_avg", "tmin_avg", "prcp_sum", "snow_sum"):
                v = row[e].strip()
                if v:
                    try:
                        nw[c][e].append(float(v))
                    except ValueError:
                        pass
            ns_days[c].append((int(row["n_stations"]), float(row["n_days"])))
    nwrows = []
    for c in CITIES:
        if c not in weeks_city:
            continue
        d0 = datetime.date.fromisoformat(min(weeks_city[c]))
        d1 = datetime.date.fromisoformat(max(weeks_city[c]))
        expected = (d1 - d0).days // 7 + 1
        st = [x[0] for x in ns_days[c]]
        dy = [x[1] for x in ns_days[c]]
        row = [c, len(weeks_city[c]), expected, expected - len(weeks_city[c]),
               d0.isoformat(), d1.isoformat(),
               min(st), max(st), round(sum(st) / len(st), 2),
               round(min(dy), 2), round(max(dy), 2), round(sum(dy) / len(dy), 2)]
        for e in ("tavg_avg", "tmax_avg", "tmin_avg", "prcp_sum", "snow_sum"):
            s = num_stats(nw[c][e])
            row += [s.get("min", ""), s.get("median", ""), s.get("mean", ""), s.get("max", "")]
        nwrows.append(row)
    wcsv(os.path.join(OUT, "noaa_cleaned_stats.csv"),
         ["city", "weeks", "expected_weeks", "missing_weeks", "date_min", "date_max",
          "n_stations_min", "n_stations_max", "n_stations_mean",
          "n_days_min", "n_days_max", "n_days_mean",
          "tavg_min", "tavg_median", "tavg_mean", "tavg_max",
          "tmax_min", "tmax_median", "tmax_mean", "tmax_max",
          "tmin_min", "tmin_median", "tmin_mean", "tmin_max",
          "prcp_min", "prcp_median", "prcp_mean", "prcp_max",
          "snow_min", "snow_median", "snow_mean", "snow_max"], nwrows)
    summary["noaa_cleaned"] = {"total_weeks": sum(len(v) for v in weeks_city.values())}
    print("NOAA_CLEANED weeks=%d" % summary["noaa_cleaned"]["total_weeks"])

    # ---------- 5) NHGIS ----------
    nh_pts = os.path.join(CLN, "nhgis", "nhgis_points_geo.csv")
    nh_pop = os.path.join(CLN, "nhgis", "population_clean.csv")
    pts = []
    with open(nh_pts, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            pts.append([row["city_name"], row["nhgisplace"], row["lon"], row["lat"]])
    pop = defaultdict(dict)
    with open(nh_pop, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            pop[row["city_name"]][int(row["census_year"])] = int(float(row["population"]))
    prows = []
    for c in sorted(pop):
        ys = sorted(pop[c])
        for i, y in enumerate(ys):
            prev = pop[c].get(ys[i - 1]) if i > 0 else None
            growth = "" if prev is None else round((pop[c][y] / prev - 1) * 100, 2)
            prows.append([c, y, pop[c][y], growth])
    wcsv(os.path.join(OUT, "nhgis_stats.csv"),
         ["city", "census_year", "population", "decadal_growth_pct"], prows)
    pts_summary = []
    with open(nh_pts, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            pts_summary.append({"city": row["city_name"], "lon": row["lon"], "lat": row["lat"]})
    summary["nhgis"] = {"points": pts_summary, "population_years": sorted(set(
        y for d in pop.values() for y in d))}
    print("NHGIS done")

    # ---------- 6) newspaper 三城 cleaned ----------
    cov_f = os.path.join(CLN, "newspaper", "newspaper_coverage_matrix.csv")
    hit_f = os.path.join(CLN, "newspaper", "newspaper_hits_weekly.csv")
    cp_pages = defaultdict(int)
    cp_year = defaultdict(set)
    with open(cov_f, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            cp_pages[(row["city"], row["paper"])] += int(row["n_pages"])
            cp_year[(row["city"], row["paper"])].add(int(row["year"]))
    cp_hits = defaultdict(lambda: {"hits": 0, "pages": 0})
    with open(hit_f, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            k = (row["city"], row["paper"])
            cp_hits[(k, row["disease"])]["hits"] += int(row["n_hits"])
            cp_hits[(k, row["disease"])]["pages"] += int(row["n_pages"])
    nrows6 = []
    for (c, paper), pages in sorted(cp_pages.items()):
        ys = cp_year[(c, paper)]
        row = [c, paper, pages, min(ys), max(ys), len(ys)]
        for dis in ("INFLUENZA", "POLIOMYELITIS", "DIPHTHERIA"):
            h = cp_hits[((c, paper), dis)]
            row += [h["hits"], pct(h["hits"] / h["pages"]) if h["pages"] else ""]
        nrows6.append(row)
    wcsv(os.path.join(OUT, "newspaper_3cities_stats.csv"),
         ["city", "paper", "pages", "year_min", "year_max", "n_years",
          "flu_hits", "flu_rate", "polio_hits", "polio_rate", "diph_hits", "diph_rate"],
         nrows6)
    summary["newspaper_3cities"] = {"total_pages": sum(cp_pages.values()),
                                    "papers": len(cp_pages)}
    print("NEWS_3CITIES pages=%d" % summary["newspaper_3cities"]["total_pages"])

    # ---------- 7) newspaper 三城文本字符统计（重读 ocr.txt） ----------
    news_root = os.path.join(RAW, "newspaper")
    txt = defaultdict(list)
    empty = defaultdict(int)
    total_chars = defaultdict(int)
    total_pages = defaultdict(int)
    n_files = 0
    for city in os.listdir(news_root):
        cdir = os.path.join(news_root, city)
        if not os.path.isdir(cdir):
            continue
        for root, _, files in os.walk(cdir):
            for fn in files:
                if fn.lower() != "ocr.txt":
                    continue
                fp = os.path.join(root, fn)
                parts = root.split(os.sep)
                paper = parts[-6] if len(parts) >= 6 else "?"
                try:
                    with open(fp, encoding="utf-8-sig", errors="replace") as f:
                        t = f.read()
                except OSError:
                    continue
                k = (city, paper)
                txt[k].append(len(t))
                total_chars[k] += len(t)
                total_pages[k] += 1
                if not t.strip():
                    empty[k] += 1
                n_files += 1
    nrows7 = []
    for (c, paper), lens in sorted(txt.items()):
        s = num_stats(lens)
        nrows7.append([c, paper, total_pages[(c, paper)], total_chars[(c, paper)],
                       s.get("min", ""), s.get("median", ""), s.get("mean", ""),
                       s.get("max", ""), empty[(c, paper)]])
    wcsv(os.path.join(OUT, "newspaper_text_stats.csv"),
         ["city", "paper", "pages", "total_chars", "chars_min", "chars_median",
          "chars_mean", "chars_max", "empty_pages"], nrows7)
    summary["newspaper_text"] = {"files": n_files}
    print("NEWS_TEXT files=%d" % n_files)

    # ---------- 8) newspaper zip 结构 ----------
    zrows = []
    zsum = 0
    with zipfile.ZipFile(ZIP_PATH) as zf:
        names = []
        for n in zf.namelist():
            try:
                names.append(n.encode("cp437").decode("utf-8"))
            except Exception:
                names.append(n)
        real = [n for n in names if not n.startswith("__MACOSX") and not n.endswith("/")
                and n.split("/")[-1].lower() == "ocr.txt"]
        zsum = len(real)
        zcp_pages = defaultdict(int)
        zcp_year = defaultdict(set)
        for n in real:
            parts = n.split("/")
            zcp_pages[(parts[1], parts[2])] += 1
            if parts[3].isdigit():
                zcp_year[(parts[1], parts[2])].add(int(parts[3]))
        for (c, paper), pg in sorted(zcp_pages.items()):
            ys = zcp_year[(c, paper)]
            miss = [y for y in range(min(ys), max(ys) + 1) if y not in ys]
            zrows.append([c, paper, pg, min(ys), max(ys), len(ys),
                          ";".join(map(str, miss))])
    wcsv(os.path.join(OUT, "newspaper_zip_stats.csv"),
         ["city", "paper", "pages", "year_min", "year_max", "n_years", "missing_years"],
         zrows)
    summary["newspaper_zip"] = {"total_pages": zsum, "papers": len(zrows)}
    print("NEWS_ZIP pages=%d" % zsum)

    with open(os.path.join(OUT, "all_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("ALL_DONE -> %s" % OUT)


if __name__ == "__main__":
    main()
