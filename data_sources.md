# 数据源清单与采集日志（data_sources.md）

> 对应作业要求 3.3"数据来源记录"。全项目共 **5 个数据源**（4 个独立主源 + 1 个辅助点位源），汇总自 A–E 各组数据源卡；各源卡的完整字段字典、复核记录见 `analysis\组员交付\` 对应目录。

## 总表

| 数据源 | 来源 | 获取方式 | 数据类型 | 原始规模 / 时间范围 | 采集时间 | 许可 / 使用说明 | 主要字段 | 跨源关联字段 |
|---|---|---|---|---|---|---|---|---|
| Project Tycho Level 2 v1.1.0（美国历史疾病周报） | [Zenodo 数据集](https://zenodo.org/records/12608994)，DOI `10.5281/zenodo.12608994` | 下载官方 ZIP、核对 MD5；项目表筛选 1900–1960 并增加 `year/week/source_level` | 历史周级病例/死亡计数，CSV | 官方完整 Level 2 表 **3,659,360 行**（1888–2014）；项目实际使用的 1900–1960 提取表 **2,934,886 行 / 33 病种**；六城三病种清洗长表 **40,318 行** | 下载日期 **2026-09-25**（当日下载日志+文件时间交叉确认）；六城清洗 2026-10-17 | **CC BY 4.0**（官方许可页为准）；使用注明作者与 Project Tycho、版本与 DOI；缺报不当作零病例 | `epi_week/from_date/to_date/state/loc/disease/event/number` → 清洗：`city/year/week/flu_cases/polio_cases/diph_cases` | `city × sunday_date`（`from_date` 所在周的周日） |
| NOAA GHCN-Daily（气象） | NOAA/NCEI [产品页](https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily)，数据 DOI `10.7289/V5D21VHZ` | 官方 HTTPS 按站下载（无注册） | 站点日值气象，宽表 CSV（纽约 2 个实为 XLSX） | 原始宽表 **58 文件 / 946,693 行 / 75.33 MB**；`data/raw/noaa` 目录 **354.65 MB（338.22 MiB）**，含转换长表与目录文件；观测 1900-01-01 至 1995-12-21 | 原始下载日期未记录；源卡复核 2026-10-31 | NOAA/NCEI 公开数据（GHCN-Daily 无附加许可限制）；17 个城-站组合 >50km、0 个 >100km（最大 96.3km），为近城站网 | `STATION/NAME/DATE/PRCP/SNOW/SNWD/TMAX/TMIN` → 周表：`tavg_avg/tmax_avg/tmin_avg/prcp_sum/snow_sum`（℉、周内日均 in/day） | `city × sunday_date`（站按城市映射，NHGIS 点位作距离参考） |
| U.S. Census 1950 普查卷（人口） | Census Bureau《1950 Census of Population, Volume I》各州/特区卷 **Table 4**（历史人口回顾表） | 官方 PDF 逐页视觉转录 | 普查人口，PDF→CSV | 6 城 × 5 普查年（1910/1920/1930/1940/1950）= **30 条**；六份 PDF 均核验存在 | 前期说明卡 2026-10-14；**人工复核 2026-11-03**（30 条逐行核对） | 美国政府出版物，公开可用 | `census_year/population/unit/city_name/source_url/source_pdf_page/printed_page/table` | `city_id → tycho_city`（融合主键 city × sunday_date；年份线性插值） |
| IPUMS NHGIS 1930 Place Points（城市点位，辅助源） | IPUMS NHGIS [Place Points](https://www.nhgis.org/place-points) 图层 | 官方图层下载 | 空间点位（投影坐标），DBF+SHP | 6 城 × 1930 年 = 6 条；全国图层 16,712 条 | 2026-10 月内（具体日志未逐文件记录） | NHGIS 学术使用条款（登录下载） | `place_1930/nhgisplace/x_m/y_m`（Albers 等积，NAD83）→ 清洗加 `lon/lat` | 城市点位仅用于站距校验与坐标参考，不进融合主表 |
| Chronicling America（报刊 OCR） | Library of Congress Chronicling America（NDNP） | 官方 ZIP 流式读取（不落地解压） | 历史报纸逐页 OCR 文本 | 六城研究窗内扫描页 **299,358 页**（正式口径）；raw 原始数据 **4.57 GB** | 扫描 2026-10-17~22 分批完成 | 美国公有领域报纸 OCR，公开可用；保留 OCR 误差与覆盖不均说明 | `city/paper/sunday_date/n_issues/n_pages/np_*_hits_strong/np_*_hits_weak` | `city × sunday_date`（报纸日期归入周日） |

## 各源说明与数据缺口

### 1. Project Tycho（疫情）
- 版本：Level 2 v1.1.0；官方 ZIP **22,157,131 字节**，MD5 `c3f3b1cfa4e8aa54cb730f26283cc194`。官方完整表为 1888–2014、11 列、3,659,360 行；项目 `data/raw/tycho` 文件是 1900–1960 提取表，增加 `year/week/source_level` 后为 14 列、2,934,886 行。两个数字对应不同范围与处理阶段，并非清洗丢行。
- 清洗口径：`disease` 映射 `INFLUENZA → flu_cases / POLIOMYELITIS → polio_cases / DIPHTHERIA → diph_cases`，只取 `event=CASES`；同城同病同事件同周重复键取 `max(number)`（窗口内实际聚合 138 个）；Level 1 与 Level 2 不能相加。
- 流感缺口：六城 1915–1918 为 0 行、1919 年仅 5 行；Q2 按统一口径整段排除 1915–1919（纽约 1919 年末真实病例仍保留在主表）。登记于 `docs\GAPS.md` G2。
- 源卡：`analysis\组员交付\B_杨川誉_Q2\data_sources.md`。

### 2. NOAA GHCN-Daily（气象）
- 规模：58 份原始宽表合计 **75,331,206 字节（75.33 MB / 71.84 MiB）**、946,693 行；`data/raw/noaa` 整个目录为 **354,652,952 字节（354.65 MB / 338.22 MiB）**，差额来自 `long_chart` 转换表和 GHCN 目录/辅助文件。密尔沃基 1 组完全相同文件按 SHA 去重后原始宽表为 73,839,423 字节；共 57 个真实站号、59 个城-站组合。
- 口径：TAVG 缺值用 (TMAX+TMIN)/2 回退；**PRCP/SNOW 为周内有效观测日日均、非周累计**；缺失 NA 不补 0；缺 TAVG 列的文件不补造。
- **原始下载日期与导出单位配置未记录**（官方 README 单位换算已用 12 个本地值与官方 .dly 原生记录比对验证）；`source_card.md` 生成脚本 `scripts/audit_noaa_raw.py`、`build_noaa_source_card.py`。
- 源卡：`analysis\组员交付\C_黄祉玥_Q3\Q3_NOAA_20261031\analysis\noaa_source_card\NOAA_source_card.md`；采集记录：同目录 `补充材料\collection_record.md`。

### 3. 人口普查（人口）
- 来源必须与 NHGIS 分开：人口值来自 Census 官方 PDF（Table 4），点位来自 NHGIS。
- 每城 PDF 页码已定位：NY `vol-01-35.pdf` p.9 / DC `vol-01-12.pdf` p.3 / Milwaukee `vol-01-52.pdf` p.9 / LA `vol-01-08.pdf` p.10 / Cleveland `vol-01-38.pdf` p.8 / Baltimore `vol-01-23.pdf` p.7（均为印刷页 Table 4）。
- 插值：`P(y) = P(a) + (P(b)-P(a))×(y-a)/(b-a)`；研究窗口均在普查年范围内不外推。
- 源卡：`analysis\组员交付\D_黄超博_Q4Q5\outputs\NHGIS_人口与点位源卡.md`。

### 4. NHGIS 点位（辅助）
- 1930 Place Points 图层；原始投影 `USA_Contiguous_Albers_Equal_Area_Conic`（EPSG:5070，NAD83）；按州+完整地点名精确匹配；坐标转换修正已登记 GAPS。

### 5. Chronicling America 报刊（媒体关注代理）
- 指标：`np_<dis>_rate = 强词命中页数 / 当周扫描页数 × 100`；`np_pages=0` 时命中率 NA；弱词（flu/polio/antitoxin）仅敏感性分析。
- **页数口径**：正式 **299,358**（目录批次 32,036 页 + ZIP 批次 267,322 页）；口径依据与缺口登记见 `docs\GAPS.md`（G10）。
- 风险声明：关键词命中是关注代理指标，不等于疫情或公众态度；报纸出版地不等于报道事件地；OCR 误差、多语种、题名更替可能引入系统偏差。
- 源卡：`analysis\组员交付\A_周莉婕_Q1\01_主要成果\报刊数据源卡.md`。

## 采集日志摘要

| 日期 | 事项 |
|---|---|
| 2026-09-25 | B：Tycho Level 2 官方 ZIP 下载、MD5 核验（下载日志+文件时间确认） |
| 2026-10-14 | D：人口普查 PDF 与 NHGIS 点位前期说明卡 |
| 2026-10-17 | E：报刊目录批次首轮扫描、Tycho 六城清洗、NOAA 清洗 v2、NHGIS 坐标转换、采集计划落提纲 |
| 2026-10-17~22 | E：报刊六城扫描分批完成（词表 v2、强弱词拆分） |
| 2026-10-21 | E：融合口径确定，融合宽表构建 |
| 2026-10-28~29 | B：Q2 分析；D：Q4/Q5 分析（气象口径更新 10-29） |
| 2026-10-30 | A：Q1 分析；C：NOAA 源卡复核 |
| 2026-10-31 | C：Q3 分析、run_manifest/verification/reproducibility 检查 |
| 2026-11-03 | E：页数正式口径 299,358；B/D 交接包同步；D 人工复核 30 条；全项目口径统一；本清单汇总 |
