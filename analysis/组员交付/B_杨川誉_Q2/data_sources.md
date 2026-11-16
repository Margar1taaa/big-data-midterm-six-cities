# 数据源卡：Project Tycho（B 部分）

记录日期：2026-10-29。本卡只记录 B 部分负责的 **Tycho 疫情数据源**。按作业 3.3，全组最终提交的数据源清单还需汇入其他组员负责的来源；本卡不能单独代表全组完整清单。Q2 分析另使用报刊指标，但其来源卡由相应数据负责人补入全组清单。

## 3.3 数据来源记录

| 数据源 | 来源 | 获取方式 | 数据类型 | 原始规模 / 时间范围 | 采集时间 | 许可 / 使用说明 | 主要字段 | 跨源关联字段 |
|---|---|---|---|---|---|---|---|---|
| Project Tycho Level 2 v1.1.0，美国历史疾病周报 | [Zenodo 数据集记录](https://zenodo.org/records/12608994)，DOI `10.5281/zenodo.12608994`；本地采集清单 `data/processed/project_tycho/data_manifest.csv` | 采集脚本下载官方 ZIP，核对 MD5 后解压、分块读取 CSV，再筛选六城、病种和研究窗口；交接包提供清洗表与融合表 | 历史周级病例/死亡计数，CSV 结构化数据 | 官方 Level 2 原始 CSV **3,659,360 行**；六城三病种清洗长表 **40,318 行**，覆盖 1900–1960 范围内有记录的周；Q2 研究窗口为 **1915–1922、1930–1932**，流感相关分析仅使用 1920 年起的数据 | 原始 ZIP 实际下载日期 = **2026-09-25**（2026-11-03 经当日下载完成日志与文件时间交叉确认）；六城清洗于 **2026-10-17** 完成，融合口径于 **2026-10-21** 确定 | Project Tycho 官网公布 **Creative Commons Attribution 4.0 International（CC BY 4.0，署名 4.0 国际许可）**，见[官方许可协议](https://www.tycho.pitt.edu/license/)。使用或分享数据时应注明作者及 Project Tycho、版本与 DOI，附来源和许可链接，并说明对数据所作修改；不得暗示原作者为本项目背书。本项目的修改包括六城/病种/年份筛选、同周重复键取 max、周标签归并和 Q2 流感年份排除。原始缺报不能当作零病例（本项目数据处理口径）。 | 原始：`epi_week`, `state`, `loc`, `loc_type`, `disease`, `event`, `number`, `from_date`, `to_date`, `url`；清洗：另有 `city`, `year`, `week`, `source_level`；Q2：`flu_cases`, `polio_cases`, `diph_cases` | 地点 `state + loc → city`；日期 `from_date → sunday_date`；与其他来源按 `city × sunday_date` 合并，病名由 `disease` 映射到三个主表病例列 |

## 字段字典与病名映射

| 原始/清洗字段 | 含义 | 本题用途 |
|---|---|---|
| `epi_week`、`from_date`、`to_date` | 原报告的流行病学年周及报告起止日期 | 校核时间；融合主表按 `from_date` 所在周的周日标为 `sunday_date`。 |
| `state`、`loc`、`loc_type` | 州缩写、地点名称、地点类型 | 选择城市级记录并规范为六城 `city`。 |
| `disease` | 原始疾病名称 | `INFLUENZA → flu_cases`；`POLIOMYELITIS → polio_cases`；`DIPHTHERIA → diph_cases`，且只取 `event=CASES`。另一版本 Level 1 中的 `POLIO` 与 Level 2 `POLIOMYELITIS` 为病名别称，不能当成两种病；本题病例来自 Level 2。 |
| `event`、`number` | 事件类型（`CASES` / `DEATHS`）及报告数量 | Q2 只分析病例；死亡数不混入病例列。 |
| `url`、`source_level` | 原始报告链接；派生的来源层级 | 追查单条报告来源、区分 Level 1 / Level 2。 |

原始字段定义对照项目根目录 `data/processed/project_tycho/field_dictionary.csv`；交接包清洗表为 `data/cleaned/tycho/cleaned_tycho_weekly_sixcities.csv`，融合字段定义见 `data/integrated/README.md`。上述路径分别相对于**项目根目录**或**交接包根目录**，不是本独立 Q2 文件夹中的重复原始数据。

## 采集记录与质量口径

| 环节 | 已有记录 | 复核位置 |
|---|---|---|
| 下载与完整性 | Level 2 v1.1.0 官方 ZIP 大小 **22,157,131 字节**，MD5 `c3f3b1cfa4e8aa54cb730f26283cc194`；解压后 CSV **3,659,360 行**。 | 项目根目录 `data/processed/project_tycho/data_manifest.csv`、`outputs/tycho_collection_20260925/README.md`。 |
| 六城三病种清洗 | Level 2 派生清洗长表 **40,318 行**，保留 `CASES` 与 `DEATHS` 并用 `event` 区分。 | 交接包 `data/cleaned/tycho/cleaned_tycho_weekly_sixcities.csv`、`tycho_clean_report.json`。 |
| 重复键 | 交接记录称原长表有 **110 个** `city × disease × event × epi_week` 重复键；在融合窗口内，按规范化的同城、同病、同事件、同周键取 **`max(number)`**，实际聚合 **138 个**重复，后者含日期周界归并产生的重复。不能简单相加。 | 交接包 `GAPS.md` 的 G5、`data/integrated/README.md`。 |
| 流感缺失 | 六城 `INFLUENZA` 在 **1915–1918 为 0 行**、1919 年仅 **5 行**；交接主表 1915–1919 流感值主要为 **NA**，纽约 1919 年末真实病例仍在主表保留。**B/Q2 根据口径 07 在平滑和配对前整体排除 1915–1919**，因此 Q2 流感曲线仅用 1920–1922、1930–1932。缺报不填 0，也不以报刊命中率代替病例。 | 交接包 `GAPS.md` 的 G2、`分析交接包.md`；本文件夹 `scripts/q2_media_epidemic_lag.py`。 |

待补证据：原始下载的实际日期。其他来源的来源卡应由全组汇总，不在此卡内编造。
