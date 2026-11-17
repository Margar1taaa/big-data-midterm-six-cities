# NOAA raw→cleaned 独立重建核验（更新于2026-11-17）

- **脚本来源**：主项目后补的 `scripts\clean_noaa.py`，用于依据现有raw文件和已确认口径独立重建；它不是原采集时脚本。
- **用途**：NOAA 六城日转周清洗（Raw → Cleaned），产出两份 cleaned 文件：
  - `noaa_weekly_sixcities.csv`
  - `noaa_station_mapping_summary.csv`
- **输入 raw 数据**（主项目）：`data\raw\noaa\NOAA_DATA\NOAA_<City>\`——GHCND 根目录宽表 CSV（STATION,NAME,DATE,PRCP,SNOW,SNWD,TMAX,TMIN[,TAVG]）；纽约含 USW 机场站与"USW00094728 (2).csv"带空格文件名；排除 `*_long.csv`、`README.txt`、`conversion_summary.csv`、`file_mapping_and_summary.csv`。
  - 注：交接包体积限制**不含 raw 原始文件**，raw 数据保留在主项目 `data\raw\noaa\`（各城根目录宽表 + `long_chart\`）。
- **运行方式**：从项目根目录执行 `python scripts\clean_noaa.py --check`。检查模式在临时目录重建，不覆盖权威周表；脚本通过 `Path(__file__)` 定位项目根目录，不需要修改本机路径。
- **口径要点**（与脚本 docstring 一致）：周日起始对齐 Tycho epi_week；TAVG 缺失用 (TMAX+TMIN)/2 合成；各站先按周内有效观测日取均值，再跨站平均；TMAX/TMIN/TAVG=华氏度(°F)，PRCP/SNOW=周内日均英寸(in/day)；缺周 NA 不补 0。
- **复现边界**：原采集时使用的清洗脚本与导出配置未保留。当前补录脚本重建后有相同的20,655个城市周、键和缺失掩码，62个单元存在0.01舍入差异。故 raw→cleaned 属于独立重建核验；从已发布 cleaned 表开始的 integrated→Q3 可精确复现。
