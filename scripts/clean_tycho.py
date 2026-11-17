# -*- coding: utf-8 -*-
"""Project Tycho 六城三病种清洗脚本（单源清洗·Raw -> Cleaned）。

口径（2026-10-17 确定）：
- 六城 = (loc, state) 双条件：BALTIMORE+MD / CLEVELAND+OH / LOS ANGELES+CA /
  MILWAUKEE+WI / NEW YORK+NY(仅 loc_type=CITY) / WASHINGTON+DC
- 三病种：DIPHTHERIA / INFLUENZA / POLIOMYELITIS
- 事件：保留 CASES 与 DEATHS 两类（同一行标记 event，融合时按需透视）
- 周标识：epi_week（YYYYWW 格式，与 year/week 字段并存）
- 不截断时间范围，输出 1900-1960 全量；研究窗口 1916-1953 在融合阶段截取

输出：
1) cleaned_tycho_weekly_sixcities.csv  长表（city,disease,event,epi_week,year,week,
   from_date,to_date,number,source_level）
2) tycho_clean_report.json             质量报告（行数/时间范围/重复/缺失/断档）
3) tycho_coverage_matrix.csv           每城x病种x事件的年份覆盖矩阵（断档一览）
4) sample_tycho.csv                    六城x三病种各 1 条病例记录（18 行）
5) field_dictionary_tycho.csv          样本与清洗表字段说明

运行：python clean_tycho.py
"""
import csv
import datetime
import json
import os
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "data" / "raw" / "tycho" / "ProjectTycho_LEVEL2_1900_1960_all_diseases.csv"
OUT_DIR = PROJECT_ROOT / "data" / "cleaned" / "tycho"
METADATA_DIR = PROJECT_ROOT / "data" / "metadata" / "tycho"

CITY_RULES = {
    "BALTIMORE": ("MD", None),
    "CLEVELAND": ("OH", None),
    "LOS ANGELES": ("CA", None),
    "MILWAUKEE": ("WI", None),
    "NEW YORK": ("NY", "CITY"),
    "WASHINGTON": ("DC", None),
}
DISEASES = {"DIPHTHERIA", "INFLUENZA", "POLIOMYELITIS"}
EVENTS = {"CASES", "DEATHS"}


def parse_date(s):
    try:
        return datetime.date.fromisoformat(s.strip())
    except Exception:
        return None


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(METADATA_DIR, exist_ok=True)
    out_csv = os.path.join(OUT_DIR, "cleaned_tycho_weekly_sixcities.csv")
    out_json = os.path.join(OUT_DIR, "tycho_clean_report.json")
    out_cov = os.path.join(OUT_DIR, "tycho_coverage_matrix.csv")
    out_sample = os.path.join(METADATA_DIR, "sample_tycho.csv")
    out_fields = os.path.join(METADATA_DIR, "field_dictionary_tycho.csv")

    # 组级统计
    groups = defaultdict(lambda: {
        "rows": 0, "n_missing_number": 0, "n_dup": 0,
        "min_epi": None, "max_epi": None,
        "years": set(), "dates": set(),
    })
    seen_keys = set()
    n_scanned = 0
    n_kept = 0
    n_other_event = 0
    sample_rows = {}
    output_fields = ["city", "disease", "event", "epi_week", "year", "week",
                     "from_date", "to_date", "number", "source_level"]

    with open(SRC, encoding="utf-8", newline="") as fin, \
         open(out_csv, "w", encoding="utf-8-sig", newline="") as fout:
        reader = csv.DictReader(fin)
        writer = csv.writer(fout)
        writer.writerow(output_fields)
        for row in reader:
            n_scanned += 1
            loc = (row.get("loc") or "").strip()
            st = (row.get("state") or "").strip()
            if loc not in CITY_RULES:
                continue
            want_state, want_loctype = CITY_RULES[loc]
            if st != want_state:
                continue
            if want_loctype and (row.get("loc_type") or "").strip() != want_loctype:
                continue
            disease = (row.get("disease") or "").strip()
            if disease not in DISEASES:
                continue
            event = (row.get("event") or "").strip()
            if event not in EVENTS:
                n_other_event += 1
                continue

            epi = (row.get("epi_week") or "").strip()
            number = (row.get("number") or "").strip()
            try:
                num = int(number) if number not in ("", "NA", "NULL") else None
            except ValueError:
                num = None
            from_date = parse_date(row.get("from_date") or "")

            # 组级统计按 (city, disease, event) 分组；重复检测按 (city, disease, event, epi_week)
            g = groups[(loc, disease, event)]
            dup_key = (loc, disease, event, epi)
            if dup_key in seen_keys:
                g["n_dup"] += 1
            else:
                seen_keys.add(dup_key)
            g["rows"] += 1
            if num is None:
                g["n_missing_number"] += 1
            if g["min_epi"] is None or epi < g["min_epi"]:
                g["min_epi"] = epi
            if g["max_epi"] is None or epi > g["max_epi"]:
                g["max_epi"] = epi
            try:
                g["years"].add(int((row.get("year") or "").strip()))
            except ValueError:
                pass
            if from_date is not None:
                g["dates"].add(from_date)

            output_row = [loc, disease, event, epi,
                          (row.get("year") or "").strip(),
                          (row.get("week") or "").strip(),
                          (row.get("from_date") or "").strip(),
                          (row.get("to_date") or "").strip(),
                          "" if num is None else num,
                          (row.get("source_level") or "").strip()]
            writer.writerow(output_row)
            sample_key = (loc, disease)
            if event == "CASES" and sample_key not in sample_rows:
                sample_rows[sample_key] = output_row
            n_kept += 1

    # 汇总报告
    report = {"scanned_rows": n_scanned, "kept_rows": n_kept,
              "other_event_skipped": n_other_event,
              "diseases": sorted(DISEASES),
              "city_rules": {k: list(v) for k, v in CITY_RULES.items()},
              "groups": {}}
    cov_rows = []
    for key, g in sorted(groups.items()):
        city, disease, event = key
        dates_sorted = sorted(g["dates"])
        missing_weeks = None
        if dates_sorted:
            d0, d1 = dates_sorted[0], dates_sorted[-1]
            expected = {(d0 + datetime.timedelta(days=7 * i)) for i in range((d1 - d0).days // 7 + 1)}
            missing_weeks = len(expected - g["dates"])
        ymin, ymax = (min(g["years"]), max(g["years"])) if g["years"] else (None, None)
        missing_years = [y for y in range(ymin or 0, (ymax or 0) + 1) if y not in g["years"]]
        report["groups"]["|".join(key)] = {
            "rows": g["rows"], "n_missing_number": g["n_missing_number"],
            "n_dup": g["n_dup"], "min_epi_week": g["min_epi"], "max_epi_week": g["max_epi"],
            "min_year": ymin, "max_year": ymax, "missing_years": missing_years,
            "n_missing_weeks": missing_weeks,
        }
        cov_rows.append([city, disease, event, g["rows"], g["min_epi"], g["max_epi"],
                         ymin, ymax, ";".join(map(str, missing_years)),
                         "" if missing_weeks is None else missing_weeks])

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(out_cov, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["city", "disease", "event", "rows", "min_epi_week", "max_epi_week",
                    "min_year", "max_year", "missing_years", "missing_weeks_count"])
        w.writerows(cov_rows)

    with open(out_sample, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(output_fields)
        for key in sorted(sample_rows):
            w.writerow(sample_rows[key])

    field_rows = [
        ("city", "标准化城市名", "城市关联"),
        ("disease", "疾病名称", "疾病筛选与分组"),
        ("event", "事件类型：CASES 或 DEATHS", "区分病例与死亡"),
        ("epi_week", "流行病学年周，YYYYWW", "周级时间关联"),
        ("year", "由 epi_week 提取的年份", "年度筛选"),
        ("week", "由 epi_week 提取的周序号", "周级面板"),
        ("from_date", "报告周期起始日", "日期关联"),
        ("to_date", "报告周期结束日", "日期核验"),
        ("number", "该周病例数或死亡数", "疫情强度指标"),
        ("source_level", "Project Tycho 数据层级", "来源追踪"),
    ]
    with open(out_fields, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["field", "meaning", "project_use"])
        w.writerows(field_rows)

    print("SCANNED=%d KEPT=%d OTHER_EVENT=%d GROUPS=%d" %
          (n_scanned, n_kept, n_other_event, len(groups)))
    print("OUT_CSV=%s" % out_csv)
    print("OUT_JSON=%s" % out_json)
    print("OUT_COV=%s" % out_cov)
    print("OUT_SAMPLE=%s ROWS=%d" % (out_sample, len(sample_rows)))
    print("OUT_FIELDS=%s" % out_fields)


if __name__ == "__main__":
    main()
