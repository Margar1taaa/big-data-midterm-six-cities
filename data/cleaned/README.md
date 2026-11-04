# data\cleaned 数据字典（单源清洗产物）

> 本目录存放 Raw → Cleaned 阶段的全部可复现产物，按数据源分子目录：
> `tycho\` / `noaa\` / `nhgis\` / `newspaper\`。
> 每个文件由 `scripts\` 下对应脚本生成，脚本头部注释记录口径；
> 重新运行脚本即可复现（输入为 `data\raw\` 下原始文件，不修改 Raw）。
> 更新：2026-10-18（目录重组后路径同步）

## 目录结构
```
data\cleaned\
├── tycho\      cleaned_tycho_weekly_sixcities.csv / tycho_clean_report.json / tycho_coverage_matrix.csv
├── noaa\       noaa_weekly_sixcities.csv / noaa_station_mapping_summary.csv
├── nhgis\      nhgis_points_geo.csv / population_clean.csv
├── newspaper\  newspaper_coverage_matrix.csv / newspaper_hits_weekly.csv
└── README.md   本文件
```

## 1. tycho\cleaned_tycho_weekly_sixcities.csv
- 来源：`data\raw\tycho\ProjectTycho_LEVEL2_1900_1960_all_diseases.csv`（293.49 万行全量）
- 生成：`scripts\clean_tycho.py`
- 行数：40,318；时间：1900–1960（全量保留，分析窗口 1916–1953 在融合阶段截取）
- 口径：
  - 六城用 (loc, state) 双条件：BALTIMORE+MD / CLEVELAND+OH / LOS ANGELES+CA /
    MILWAUKEE+WI / NEW YORK+NY（仅 loc_type=CITY，排除州级）/ WASHINGTON+DC（排除 PA/WA 同名）
  - 三病种：DIPHTHERIA / INFLUENZA / POLIOMYELITIS；事件：CASES / DEATHS
  - 脊灰仅有 CASES，无 DEATHS（Tycho 数据事实）
- 列：city, disease, event, epi_week, year, week, from_date, to_date, number, source_level
- 已知问题：110 个 (city,disease,event,epi_week) 重复键（见 GAPS G5，融合时聚合）

## 2. tycho\tycho_clean_report.json
- 生成：`scripts\clean_tycho.py`；每组 (city×disease×event) 的行数、时间范围、缺失年份、缺失周数、重复数
- 用途：质量审计 + 报告引用

## 3. tycho\tycho_coverage_matrix.csv
- 生成：`scripts\clean_tycho.py`；30 组（六城×三病种×事件）的年份覆盖一览
- 关键发现：流感 1920–1948 覆盖（缺 1918–1919，见 GAPS G2）；白喉死亡 1900–1923 止；
  1949–1951 各病种病例普遍缺失；周级缺口为当时周报非每周发布的正常现象

## 4. noaa\noaa_weekly_sixcities.csv
- 来源：`data\raw\noaa\NOAA_DATA\NOAA_<City>\` 根目录宽表 CSV（每文件可能为多源站合并，
  合并关系见 `file_mapping_and_summary.csv` 或纽约的 `conversion_summary.csv`）
- 生成：`scripts\clean_noaa.py`
- 行数：20,655 周/6 城（每城 3,131 周，1900–1959；华盛顿含站至 1995，融合时截窗口）
- 口径：
  - 周历 = 周日起始（与 Tycho epi_week 的 from_date 对齐），输出周起始日期 sunday_date 作为融合主键
  - 站内聚合：TAVG/TMAX/TMIN 周均、PRCP/SNOW 周和、n_days 周内有效观测天数
  - 城市级：多站取均值，n_stations 记录参与站数
  - TAVG 缺失站（仅纽约 USW 站有该列）用 (TMAX+TMIN)/2 合成；排除 *_long.csv 长表与 README
- 列：city, sunday_date, week_end, tavg_avg, tmax_avg, tmin_avg, prcp_sum, snow_sum, n_days, n_stations
- 纽约站数偏少（6 站，早期每周仅 2 站参与），已在融合敏感性分析中记录 n_stations

## 5. noaa\noaa_station_mapping_summary.csv
- 生成：`scripts\clean_noaa.py`；六城 38 行（纽约 8 文件含 "USW00094728 (2).csv" 带空格文件名）
- 列：city, source_file, actual_station, station_name, output_file, date_start, date_end, source_rows

## 6. nhgis\nhgis_points_geo.csv / population_clean.csv
- 来源：`data\raw\nhgis\处理后数据\`
- 生成：`scripts\convert_nhgis.py`
- 口径：NHGIS 点位 x 与 EPSG:5070（USA Contiguous Albers Equal Area Conic, NAD83, meters）吻合，
  y 差常量 1,606,780m → y+偏移后转 EPSG:4326（六城经纬度与真实坐标误差 <1.3km，见脚本验证注释）；
  人口为普查年观测值不插值，DC 为 city_dc_equivalent，boundary 未统一
- 列（nhgis_points_geo）：city_id, city_name, nhgisplace, x_m, y_m, lon, lat, tycho_city
- 列（population_clean）：city_id, city_name, state_abbr, census_year, population, tycho_city, source_title, boundary_comparability
- 说明：tycho_city 列用于与 Tycho/NOAA cleaned 的 city 名对齐（融合主键之一）

## 7. newspaper\newspaper_coverage_matrix.csv / newspaper_hits_weekly.csv（仅本地三城）
- 来源：`data\raw\newspaper\`（Baltimore/Cleveland/Los Angeles，32,036 个 ocr.txt）
- 生成：`scripts\scan_newspaper.py`
- 口径：页路径解析 City/Paper/Year/Month/Day；周按周日起始归并；命中为 OCR 文本关键词匹配
  （词表 v1 = 英文基线+初步德西，见脚本头部与 GAPS G3）
- 行数：coverage 1,576 行 / hits 4,716 行
- 覆盖：Baltimore（Der Deutsche Correspondent 1915–1917、Telegraf 1918–1932）、Cleveland（The Gazette 1915–1932）、
  Los Angeles（California Eagle 1915–1930、La Opinion 1930–1932、La Prensa 1917–1922）——仅 1915–1932，缺 1933–1953（GAPS G9）
- 列（coverage）：city, paper, year, sunday_date, n_issues, n_pages
- 列（hits）：city, paper, disease, sunday_date, n_hits, n_pages
- 关键事实：INFLUENZA 命中页 1,618（页命中率 5.05%）、POLIOMYELITIS 324、DIPHTHERIA 88；1918–1919 流感年命中显著抬升

## 复现命令（PowerShell）
```
python scripts\clean_tycho.py
python scripts\clean_noaa.py
python scripts\convert_nhgis.py
python scripts\scan_newspaper.py
```
依赖：Python 3.10+、pyproj（pip install pyproj）
