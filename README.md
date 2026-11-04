# 大数据原理与应用 · 中期大作业

## 项目简介

研究 1915–1922 与 1930–1932 两个窗口内，美国六城（Baltimore、Cleveland、Los Angeles、Milwaukee、New York、Washington DC）的流感、白喉、脊髓灰质炎疫情，与**报刊媒体关注、气候异常、人口结构**之间的跨源关联。数据来自四个独立来源（疫情周报、气象、人口普查、历史报刊 OCR），完成采集 → 清洗 → 融合 → 分析的完整流程，并回答五个子问题（Q1–Q5）。

- `data/raw` 目录磁盘占用约 **5.36 GB**：报刊 OCR 4.57 GB、Tycho 项目提取表 407.75 MB（388.86 MiB）、NOAA 目录 354.65 MB（338.22 MiB，含转换长表与目录文件）、NHGIS 28.66 MB（27.33 MiB）。NOAA 的 **58 份原始宽表本体为 75.33 MB / 946,693 行**，不得把转换长表重复表述为新增采集量。项目覆盖 ≥4 个独立源、≥3 类形态、总量 ≥2GB；按目录占用口径报刊、Tycho、NOAA 均超过 200MB，按原始采集文件口径 NOAA 为 75.33MB，两种口径分列说明并以助教认定为准。报刊占 raw 目录约 **85.3%**，80% 上限已获助教确认（docs/GAPS.md G7）。
- 主键：`city × sunday_date`（周粒度，周日起始标签）。

## 目录结构

```
中期大作业/
├── 中期大作业.docx            # 作业要求原文（留根级便于对照）
├── README.md                  # 本文件
├── data_sources.md            # 数据源清单与采集日志（作业 3.3）
├── AI_USAGE.md                # AI 使用说明（全组汇总）
├── data/
│   ├── raw/                   # 原始数据（按源分子目录；报刊 ZIP 原件另存）
│   ├── cleaned/               # 单源清洗产物（Tycho/NOAA/人口报刊周表 + README 数据字典）
│   └── integrated/            # 融合宽表 weekly_sixcities_1915_1922_1930_1932.csv
├── scripts/                   # 全部可复现脚本（19 个，功能分类见下）
├── analysis/
│   ├── briefing/              # 项目简报
│   ├── descriptive/           # 描述性统计（md/html/docx + 图）
│   ├── 组员分析报告/           # 00 交接总览 + 01–04 四份组员分析报告（md 底稿）
│   └── 组员交付/              # A~D 四组完整交付（解压合并入库，含各组 README）
├── docs/
│   ├── GAPS.md                # 数据缺口登记（G1–G10）
│   ├── 分析交接包.md
│   ├── 研究提纲_简版.docx
│   ├── 大数据清洗融合交接包.zip  # 历史清洗融合交接包归档
│   └── 多源数据血缘图.png / .svg  # 作业必交的多源数据关联图
└── 组员分析任务交接/           # 四个组员交付 ZIP 原件（溯源保留）
```

## 数据组织（三层）

| 层 | 位置 | 内容 |
|---|---|---|
| raw | `data\raw\` | 四个数据源原始文件（Tycho Level 2 官方 CSV、NOAA 六城站点原始表、NHGIS 点位、报刊 OCR 文本与原始 ZIP；人口普查 PDF 于源机器存档，转录 30 条见 cleaned） |
| cleaned | `data\cleaned\` | 单源清洗产物：`tycho\cleaned_tycho_weekly_sixcities.csv`（40,318 行）、`noaa\` 周表（20,655 行）、人口插值表、报刊周命中表；字段字典见 `data\cleaned\README.md` |
| integrated | `data\integrated\` | 融合宽表 `weekly_sixcities_1915_1922_1930_1932.csv`（3450 行 × 29 列，六城 575 周 × 2 窗口） |

## 权威口径（全组统一）

- 强词为主指标、弱词仅敏感性；分母按页数；`np_pages=0` 时率 = NA；
- 4 周滚动均值；城市内 z-score（ddof=0）；Pearson 主 + Spearman 对照；缺失 NA 不补 0；
- 流感整段排除 1915–1919（含纽约 1919 尾）；不跨 1922→1930 空档；报告 575 周/城（含 1933-01-01 边界标签周）勿写 574；
- 人口 = 普查年线性插值（Census 1950 普查卷 Table 4，不是 NHGIS 人口）；prcp/snow 为周内日均非周累计（℉/英寸）；
- 报刊总扫描页正式口径 **299,358**（三小城 32,036 + 大三城 267,322）；口径依据与数据缺口登记见 docs/GAPS.md（G10）。

## 复现流程

```
报刊 OCR ZIP ── scan_newspaper_zip.py ──> 词表 v2 命中表
Tycho        ── clean_tycho.py      ──> 六城三病种周表
NOAA         ── clean_noaa.py       ──> 日转周气象表
人口/点位    ── convert_nhgis.py    ──> 人口插值 + 点位坐标
        └────── build_integrated.py ──────> 融合宽表
                    └── add_derived_metrics.py ──> 派生指标（命中率/发病率等）
                        └── 各分析脚本（Q1–Q5，见 组员交付\A~D）＋ describe_sources.py
```

依赖：Python 3.10+；`pyproj`（NHGIS 坐标转换）、`python-docx`（Word 文档）、`playwright`（HTML 截图）。完整锁定清单见各组 `requirements*.txt`。

安装根目录统一依赖：

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
```

## GitHub 协作

- 仓库建议设为 Private；完整 raw 数据继续保存在组内 OneDrive，不进入 GitHub。
- `.gitignore` 已排除 `data/raw`、ZIP 交接包、缓存、日志和 Office 临时文件；raw 的恢复方式见 `data/raw/README.md`。
- 分支命名、Pull Request、Word/PPT 单人整合规则和任务分工见 `docs/GITHUB_COLLABORATION.md`。
- `中期大作业_最终报告.docx` 可以持续更新，但同一时间只由一名负责人编辑，避免二进制文件冲突。

## scripts 功能分类

| 类别 | 脚本 | 说明 |
|---|---|---|
| 报刊扫描 | `scan_newspaper.py` / `scan_newspaper_zip.py` | OCR 文本母集索引 + 词表 v2 关键词检索（zip 流式版，不落地解压） |
| 报刊扫描 | `spot_check_newspaper.py` | 抽查 OCR 页命中质量 |
| 进度监控 | `monitor_scan_progress.ps1` / `monitor_progress_server.py` | 大规模扫描的平滑进度显示 |
| 单源清洗 | `clean_tycho.py` | Tycho 六城三病种 Raw→Cleaned |
| 单源清洗 | `clean_noaa.py` | NOAA 六城日转周（口径说明见 `README_NOAA_raw_cleaned.md`） |
| 单源清洗 | `convert_nhgis.py` | NHGIS 点位坐标转换 + 人口透传清洗 |
| 单源清洗 | `coverage_gaps.py` | 报刊覆盖率缺口检查 |
| 融合构建 | `build_integrated.py` | 四源融合为城×周宽表（np_pages 取 max） |
| 融合构建 | `add_derived_metrics.py` | 派生指标列（命中率/发病率，默认 dry-run） |
| 描述性分析 | `describe_sources.py` | raw+cleaned 全源描述性统计 |
| 描述性分析 | `prepare_report_data.py` / `build_report_html.py` | 报告数据 → 描述性报告 HTML |
| 描述性分析 | `capture_figs.py` / `build_docx_summary.py` | HTML 图表截图 / 描述性统计 Word 文档 |
| 工具/校验 | `len_check.py` | 行数规模检查 |
| 工具/校验 | `emit_renderer_gap.py` / `make_renderer_gap_data.py` | Word 渲染器缺口检测数据 |

## 必交材料对照（作业要求）

| 必交项 | 位置 |
|---|---|
| 项目报告（Word） | 根级 `中期大作业_最终报告.docx`（当前整合稿，提交前在 Word 中更新目录） |
| 项目展示 PPT | 待制作（2026-11-03 待排期） |
| 代码仓库/压缩包（含 README） | 本目录 + `组员分析任务交接\` 四个组员 ZIP |
| 数据源清单与采集日志 | 根 `data_sources.md` |
| 数据集（样本+元数据+校验值） | `data\raw + cleaned + integrated`；校验见各组 `validation.json` / `verification.json` |
| 多源数据关联图（必交一张） | `docs\多源数据血缘图.png` |
| AI 使用说明 | 根 `AI_USAGE.md`（各组明细在 `组员交付\A~D`） |

## 组员分工

| 组员 | 负责问题 | 交付位置 |
|---|---|---|
| A 周莉婕 | Q1 疫情与报刊关注同步关系 | `analysis\组员交付\A_周莉婕_Q1` |
| B 组 | Q2 媒体关注领先/滞后疫情（Tycho 采集） | `analysis\组员交付\B组_Q2` |
| C 黄祉玥 | Q3 气候异常与疫情强度（NOAA） | `analysis\组员交付\C_黄祉玥_Q3` |
| D 黄超博 | Q4 人口×城市差异、Q5 城市聚类 | `analysis\组员交付\D_黄超博_Q4Q5` |
| E 数据组（逸梵） | 全流程清洗、融合、扫描与口径管理 | 本目录 data/scripts/docs |
