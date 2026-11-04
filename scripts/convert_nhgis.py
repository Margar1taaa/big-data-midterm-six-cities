# -*- coding: utf-8 -*-
"""NHGIS 点位坐标转换与人口透传清洗（单源清洗·Raw -> Cleaned）。

口径（2026-10-17 确定）：
- 点位：USA_Contiguous_Albers_Equal_Area_Conic; NAD83; meters = EPSG:5070，
  经 pyproj 转 WGS84（EPSG:4326）经纬度
- 人口：普查年观测值，不插值；DC=city_dc_equivalent；boundary 未统一（沿用黄超博数据说明卡）
- 增加 tycho_city 列，将 city_id 映射为与 Tycho/NOAA cleaned 一致的 city 名（融合主键之一）

输出：
1) nhgis_points_geo.csv（city_id, city_name, nhgisplace, x_m, y_m, lon, lat）
2) population_clean.csv（city_id, city_name, state_abbr, census_year, population,
   tycho_city, source_title, boundary_comparability）

运行：python convert_nhgis.py  （依赖：pip install pyproj）
"""
import csv
import os
from pathlib import Path

import pyproj

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA = PROJECT_ROOT / "data"
OUT_DIR = os.path.join(DATA, "cleaned", "nhgis")
SRC_DIR = os.path.join(DATA, "raw", "nhgis", "处理后数据")

CITY_ID_TO_TYCHO = {
    "US_MD_BALTIMORE": "BALTIMORE",
    "US_OH_CLEVELAND": "CLEVELAND",
    "US_CA_LOS_ANGELES": "LOS ANGELES",
    "US_WI_MILWAUKEE": "MILWAUKEE",
    "US_NY_NEW_YORK": "NEW YORK",
    "US_DC_WASHINGTON": "WASHINGTON",
}


def find_file(name_part):
    for fn in os.listdir(SRC_DIR):
        if name_part in fn.lower() and fn.lower().endswith(".csv"):
            return os.path.join(SRC_DIR, fn)
    return None


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    trans = pyproj.Transformer.from_crs(5070, 4326, always_xy=True)

    pt_src = find_file("nhgis_place_points")
    pp_src = find_file("population")
    print("PT_SRC:", pt_src)
    print("PP_SRC:", pp_src)

    # 1) 点位转换
    # 验证发现：NHGIS 的 x 与 EPSG:5070 完全吻合（误差<100m），y 差常量 1,606,780m
    # （NHGIS 的 y 原点与 EPSG:5070 不同），因此 y 加常量后按 5070 投影。
    Y_OFFSET = 1606780.0
    out_pt = os.path.join(OUT_DIR, "nhgis_points_geo.csv")
    pts = []
    with open(pt_src, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            x = float(row["x_m"])
            y = float(row["y_m"]) + Y_OFFSET
            lon, lat = trans.transform(x, y)
            pts.append({
                "city_id": row["city_id"],
                "city_name": row["city_name"],
                "nhgisplace": row["nhgisplace"],
                "x_m": row["x_m"],
                "y_m": row["y_m"],
                "lon": round(lon, 6),
                "lat": round(lat, 6),
                "tycho_city": CITY_ID_TO_TYCHO.get(row["city_id"], ""),
            })
    with open(out_pt, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["city_id", "city_name", "nhgisplace", "x_m", "y_m",
                    "lon", "lat", "tycho_city"])
        for p in pts:
            w.writerow([p["city_id"], p["city_name"], p["nhgisplace"],
                        p["x_m"], p["y_m"], p["lon"], p["lat"], p["tycho_city"]])

    # 2) 人口透传
    out_pp = os.path.join(OUT_DIR, "population_clean.csv")
    with open(pp_src, encoding="utf-8-sig", newline="") as f, \
         open(out_pp, "w", encoding="utf-8-sig", newline="") as fo:
        r = csv.DictReader(f)
        w = csv.writer(fo)
        w.writerow(["city_id", "city_name", "state_abbr", "census_year",
                    "population", "tycho_city", "source_title", "boundary_comparability"])
        n = 0
        for row in r:
            w.writerow([row["city_id"], row["city_name"], row["state_abbr"],
                        row["census_year"], row["population"],
                        CITY_ID_TO_TYCHO.get(row["city_id"], ""),
                        row["source_title"], row["boundary_comparability"]])
            n += 1

    print("POINTS=%d POPULATION_ROWS=%d" % (len(pts), n))
    print("OUT_PT=%s" % out_pt)
    print("OUT_PP=%s" % out_pp)
    for p in pts:
        print("%-20s lon=%.4f lat=%.4f" % (p["tycho_city"], p["lon"], p["lat"]))


if __name__ == "__main__":
    main()
