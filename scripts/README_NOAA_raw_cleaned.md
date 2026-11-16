# NOAA raw→cleaned 原脚本补录（2026-11-03）

- **脚本来源**：主项目 `scripts\clean_noaa.py`（E 王逸梵编写，2026-10-17 v2 口径定案）。
- **用途**：NOAA 六城日转周清洗（Raw → Cleaned），产出两份 cleaned 文件：
  - `noaa_weekly_sixcities.csv`
  - `noaa_station_mapping_summary.csv`
- **输入 raw 数据**（主项目）：`data\raw\noaa\NOAA_DATA\NOAA_<City>\`——GHCND 根目录宽表 CSV（STATION,NAME,DATE,PRCP,SNOW,SNWD,TMAX,TMIN[,TAVG]）；纽约含 USW 机场站与"USW00094728 (2).csv"带空格文件名；排除 `*_long.csv`、`README.txt`、`conversion_summary.csv`、`file_mapping_and_summary.csv`。
  - 注：交接包体积限制**不含 raw 原始文件**，raw 数据保留在主项目 `data\raw\noaa\`（各城根目录宽表 + `long_chart\`）。
- **运行方式**：从项目根目录执行 `python scripts\clean_noaa.py`。脚本通过 `Path(__file__)` 自动定位项目根目录，不需要修改本机路径。
- **口径要点**（与脚本 docstring 一致）：周日起始对齐 Tycho epi_week；TAVG 缺失用 (TMAX+TMIN)/2 合成；站内周聚合（TAVG/TMAX/TMIN 周均、PRCP/SNOW 周和、n_days 有效天数）后跨站平均代表城市；TMAX/TMIN/TAVG=华氏度(°F)、PRCP/SNOW=英寸(in)；缺周 NA 不补 0，由融合阶段处理。
- **血缘说明**：C 组 Q3（NOAA_气象分析.zip）输入即本脚本产出的 cleaned 数据副本；原脚本此前未随 NOAA 分析包，本次补入 `交接包\scripts\` 后，NOAA 侧可复现范围覆盖 **raw→cleaned→integrated→Q3**。
