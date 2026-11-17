# -*- coding: utf-8 -*-
"""NOAA 六城日转周清洗脚本（单源清洗·Raw -> Cleaned）。

口径（2026-10-17 确定，v2）：
- 输入：data\\raw\\noaa\\NOAA_DATA\\NOAA_<City>\\ 根目录宽表 CSV
  （STATION,NAME,DATE,PRCP,SNOW,SNWD,TMAX,TMIN[,TAVG]；纽约含 USW 机场站、XLSX 改名文件）
  - 仅处理根目录宽表：排除 *_long.csv、file_mapping_and_summary.csv、conversion_summary.csv、README
  - TAVG 列仅部分站存在（USW 站）；缺失时用 (TMAX+TMIN)/2 合成
- 城市映射：NOAA_Baltimore->BALTIMORE 等（与 Tycho cleaned 的 city 名一致）
- 周历：周日起始（与 Tycho epi_week 的 from_date 对齐），输出 sunday_date 作为融合主键
- 站内周聚合：TAVG/TMAX/TMIN 周均、PRCP/SNOW 周和、n_days=该站该周有效观测天数
- 城市周聚合：跨站取均值（站间平均代表城市）；n_stations=参与站数；n_days=各站有效天数均值
- 单位：TMAX/TMIN/TAVG=华氏度(°F)；PRCP/SNOW=英寸(in)
- 缺周=NA（不补0），由融合阶段处理；时间范围保留全量，融合时截 1916-1953

输出：
1) noaa_weekly_sixcities.csv
2) noaa_station_mapping_summary.csv（file_mapping_and_summary.csv 或 conversion_summary.csv 整理）

本脚本依据现存原始宽表重建周表。原采集时使用的清洗脚本未保留；与已发布周表
具有相同行数、键和覆盖，个别浮点舍入值最多相差 0.01。推荐先运行：
python clean_noaa.py --check
"""
import argparse
import csv
import datetime
import os
import tempfile
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA = PROJECT_ROOT / "data"
NOAA_ROOT = os.path.join(DATA, "raw", "noaa", "NOAA_DATA")
OUT_DIR = os.path.join(DATA, "cleaned", "noaa")

CITY_DIR_MAP = {
    "BALTIMORE": "NOAA_Baltimore",
    "CLEVELAND": "NOAA_Cleveland",
    "LOS ANGELES": "NOAA_Losangles",
    "MILWAUKEE": "NOAA_Milwaukee",
    "NEW YORK": "NOAA_NewYork",
    "WASHINGTON": "NOAA_Washington",
}
MAPPING_FILES = {"file_mapping_and_summary.csv", "conversion_summary.csv"}
ELEMS = ["TAVG", "TMAX", "TMIN", "PRCP", "SNOW"]


def sunday_of(d):
    return d - datetime.timedelta(days=(d.weekday() + 1) % 7)


def parse_num(s):
    try:
        return float(s)
    except Exception:
        return None


def read_rows(fp):
    """按文件读取，UTF-8 失败回退 latin-1。"""
    for enc in ("utf-8-sig", "latin-1"):
        try:
            with open(fp, encoding=enc, newline="") as fh:
                return list(csv.DictReader(fh))
        except UnicodeDecodeError:
            continue
    return []


def main(output_dir=OUT_DIR):
    os.makedirs(output_dir, exist_ok=True)
    out_csv = os.path.join(output_dir, "noaa_weekly_sixcities.csv")
    out_map = os.path.join(output_dir, "noaa_station_mapping_summary.csv")

    rows_all = []
    mapping_rows = []
    city_report = {}

    for city, dname in CITY_DIR_MAP.items():
        cdir = os.path.join(NOAA_ROOT, dname)
        if not os.path.isdir(cdir):
            print("MISSING DIR:", cdir)
            continue
        # 宽表文件列表
        wide_files = [fn for fn in os.listdir(cdir)
                      if fn.endswith(".csv") and not fn.endswith("_long.csv")
                      and fn not in MAPPING_FILES]
        # 站内周聚合： (station, sunday) -> {elem: [sum, cnt]} + _days:set
        def _agg_default():
            d = {e: [0.0, 0] for e in ELEMS}
            d["_days"] = set()
            return d
        agg = defaultdict(_agg_default)
        station_days = defaultdict(set)
        n_files = 0
        n_lines = 0
        for fn in sorted(wide_files):
            fp = os.path.join(cdir, fn)
            rows = read_rows(fp)
            if not rows:
                continue
            n_files += 1
            for row in rows:
                n_lines += 1
                station = (row.get("STATION") or "").strip()
                try:
                    d = datetime.date.fromisoformat((row.get("DATE") or "").strip())
                except Exception:
                    continue
                sd = sunday_of(d)
                vals = {}
                for e in ELEMS:
                    v = parse_num(row.get(e) or "")
                    if e == "TAVG" and v is None:
                        tx = parse_num(row.get("TMAX") or "")
                        tn = parse_num(row.get("TMIN") or "")
                        if tx is not None and tn is not None:
                            v = (tx + tn) / 2.0
                    vals[e] = v
                if not any(v is not None for v in vals.values()):
                    continue
                agg[(station, sd)]["_days"].add(d)
                for e in ELEMS:
                    if vals[e] is not None:
                        agg[(station, sd)][e][0] += vals[e]
                        agg[(station, sd)][e][1] += 1
                station_days[station].add(sd)
        # 城市周聚合：跨站均值
        city_week = defaultdict(lambda: {e: [] for e in ELEMS})
        city_daycount = defaultdict(list)
        for (station, sd), vals in agg.items():
            for e in ELEMS:
                if vals[e][1] > 0:
                    city_week[sd][e].append(vals[e][0] / vals[e][1])
            city_daycount[sd].append(len(vals["_days"]))
        for sd in sorted(city_week):
            rows_all.append({
                "city": city,
                "sunday_date": sd.isoformat(),
                "week_end": (sd + datetime.timedelta(days=6)).isoformat(),
                "tavg_avg": _mean(city_week[sd]["TAVG"]),
                "tmax_avg": _mean(city_week[sd]["TMAX"]),
                "tmin_avg": _mean(city_week[sd]["TMIN"]),
                "prcp_sum": _mean(city_week[sd]["PRCP"]),
                "snow_sum": _mean(city_week[sd]["SNOW"]),
                "n_days": round(sum(city_daycount[sd]) / len(city_daycount[sd]), 1),
                "n_stations": len(city_daycount[sd]),
            })
        city_report[city] = {"files": n_files, "lines": n_lines,
                             "stations": len(station_days),
                             "weeks": len(city_week)}
        # mapping 表整理（两种文件名，列名自适应）
        for mname in MAPPING_FILES:
            mfile = os.path.join(cdir, mname)
            if os.path.isfile(mfile):
                for row in read_rows(mfile):
                    mapping_rows.append({
                        "city": city,
                        "source_file": row.get("source_file", ""),
                        "actual_station": (row.get("actual_station") or
                                           row.get("actual_stations") or ""),
                        "station_name": row.get("station_name", ""),
                        "output_file": row.get("output_file", ""),
                        "date_start": row.get("date_start", ""),
                        "date_end": row.get("date_end", ""),
                        "source_rows": row.get("source_rows", ""),
                    })
                break

    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["city", "sunday_date", "week_end", "tavg_avg", "tmax_avg",
                    "tmin_avg", "prcp_sum", "snow_sum", "n_days", "n_stations"])
        for row in rows_all:
            w.writerow([row["city"], row["sunday_date"], row["week_end"],
                        row["tavg_avg"], row["tmax_avg"], row["tmin_avg"],
                        row["prcp_sum"], row["snow_sum"], row["n_days"],
                        row["n_stations"]])

    with open(out_map, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["city", "source_file", "actual_station", "station_name",
                    "output_file", "date_start", "date_end", "source_rows"])
        for row in mapping_rows:
            w.writerow([row["city"], row["source_file"], row["actual_station"],
                        row["station_name"], row["output_file"], row["date_start"],
                        row["date_end"], row["source_rows"]])

    print("WEEKS_TOTAL=%d CITIES=%d MAPPING_ROWS=%d" %
          (len(rows_all), len(city_report), len(mapping_rows)))
    for city, rep in city_report.items():
        print("%s files=%d lines=%d stations=%d weeks=%d" %
              (city, rep["files"], rep["lines"], rep["stations"], rep["weeks"]))
    print("OUT_CSV=%s" % out_csv)
    print("OUT_MAP=%s" % out_map)
    return out_csv, out_map


def _mean(vals):
    if not vals:
        return ""
    return round(sum(vals) / len(vals), 2)


def compare_weekly(candidate, reference):
    with open(candidate, encoding="utf-8-sig", newline="") as f:
        rebuilt = {(r["city"], r["sunday_date"]): r for r in csv.DictReader(f)}
    with open(reference, encoding="utf-8-sig", newline="") as f:
        published = {(r["city"], r["sunday_date"]): r for r in csv.DictReader(f)}
    if rebuilt.keys() != published.keys():
        raise RuntimeError("NOAA weekly keys differ from the published table")
    numeric = ["tavg_avg", "tmax_avg", "tmin_avg", "prcp_sum", "snow_sum", "n_days", "n_stations"]
    max_delta = 0.0
    differing_cells = 0
    for key in rebuilt:
        for field in numeric:
            left, right = rebuilt[key][field], published[key][field]
            if left == right:
                continue
            if left == "" or right == "":
                raise RuntimeError(f"NOAA missing-value mask differs at {key} {field}")
            delta = abs(float(left) - float(right))
            max_delta = max(max_delta, delta)
            differing_cells += 1
    print("CHECK_ROWS=%d DIFFERING_CELLS=%d MAX_ABS_DELTA=%.6f" %
          (len(rebuilt), differing_cells, max_delta))
    if max_delta > 0.0100001:
        raise RuntimeError("NOAA rebuilt values differ by more than 0.01")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="rebuild in a temporary directory and compare with the published table")
    parser.add_argument("--output-dir", help="write rebuilt files to a separate directory")
    args = parser.parse_args()
    if args.check:
        with tempfile.TemporaryDirectory(prefix="noaa_rebuild_") as temp_dir:
            rebuilt_csv, _ = main(temp_dir)
            compare_weekly(rebuilt_csv, os.path.join(OUT_DIR, "noaa_weekly_sixcities.csv"))
    else:
        main(args.output_dir or OUT_DIR)
