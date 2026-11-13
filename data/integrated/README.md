# data/integrated 融合产物目录

> 存放多源融合（Cleaned → Integrated）阶段的产物。
> 更新：2026-11-04（融合、派生指标、站距核验、血缘图与 Q1–Q5 分析均已产出）

## 已产出
1. **`weekly_sixcities_1915_1922_1930_1932.csv`** —— 周级主表（3,450 行 = 6 城 × 575 周，**29 列**），主键 `city × sunday_date`：
   - Tycho：flu_cases / flu_deaths / diph_cases / diph_deaths / polio_cases（周值，重复键取 max，见 G5；周标签 = `sunday_of(from_date)`，周一~周日归并到当周周日，故 tycho 偶发非周日重复行会并入下一周日标签周）
   - NOAA：tavg_avg / tmax_avg / tmin_avg / prcp_sum / snow_sum / n_days / n_stations（prcp_sum/snow_sum = 站内周有效日均、跨站平均，单位 in/day，**非周累计**）
   - 报刊（**六城，2026-10-22 并入**）：np_flu_hits / np_polio_hits / np_diph_hits / np_pages（关注度；同城周多报并存时 np_pages 取 **max**，2026-11-03 定案；目录批次表 + ZIP 批次表，均采用词表 **v2** 页级命中口径，命中为**强词**计数，弱词在 *_hits_weak 列）
   - 人口：population（普查年**线性插值**，见 G8 更新）
   - **派生指标（2026-10-25 落地，见 scripts\add_derived_metrics.py）**：
     - np_flu_rate / np_polio_rate / np_diph_rate —— 报刊周命中率（%）= 强词命中页数 ÷ 该周扫描页数 × 100；无报刊覆盖周（np_pages=0）记 NA
     - flu_rate_per100k / diph_rate_per100k / polio_rate_per100k —— 人均发病率（每 10 万人口）= 病例数 ÷ 人口 × 100,000；病例或人口缺失记 NA（流感 1915–1919 全 NA，见 G2）
   - 窗口：**1915–1922 ＋ 1930–1932**（11 年，2026-10-21 拍板；流感 1915–1919 缺 Tycho 见 G2，报刊承担该段）
2. `integrated_summary.json` —— 覆盖统计与人口插值明细
3. `README.md` —— 口径与字段说明（本文件）

## 报刊覆盖（六城，词表 v2）
| 城市 | 有报刊数据的周数 / 575 |
|---|---|
| Baltimore | 572 |
| Cleveland | 572 |
| Los Angeles | 402 |
| Milwaukee | 547 |
| New York | 574 |
| Washington | 574 |

## 关联产物（已产出）
1. NOAA 站距核验：`analysis\组员交付\C_黄祉玥_Q3\Q3_NOAA_20261031\analysis\noaa_source_card\补充材料\raw_station_city_mapping.csv`（59 个城市—站点组合，含 `distance_km`）。
2. 多源血缘图：`docs\多源数据血缘图.png` / `.svg`。
3. Q1–Q5 派生分析表与图：见 `analysis\组员交付\A_周莉婕_Q1`、`B组_Q2`、`C_黄祉玥_Q3`、`D_黄超博_Q4Q5`。

## 已拍板决策（2026-10-21，见 docs\GAPS.md）
- G2 流感 1915–1919：Tycho 记 NA，报刊描述该段关注度
- G5 重复键：取 max（窗口内 138 个已聚合）
- G8 人口：普查年间按年线性插值（推翻原"不插值"）
- G9 报刊窗口：1915–1922 ＋ 1930–1932 为设计采集范围（非缺失）

