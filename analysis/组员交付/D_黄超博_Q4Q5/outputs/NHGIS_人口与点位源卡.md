# 人口与历史点位数据源卡（组员D）

负责人：黄超博。整理日期：2026-10-28。用于交给E合并到data_sources.md。

## 1. 来源必须分开写

本模块包含两类辅助数据：**人口值来自美国人口普查局官方PDF，历史城市点位来自IPUMS NHGIS**。小组分工中简称“NHGIS人口源卡”，但不能据此把所有人口值归到NHGIS。

人口来源：U.S. Census Bureau，《1950 Census of Population, Volume I, Number of Inhabitants》，各州/特区卷Table 4中的历史人口回顾表。来源入口：[官方人口卷目录](https://www.census.gov/library/publications/1952/dec/population-vol-01.html)。记录的是1910、1920、1930、1940、1950五个普查年，而不是只有1950年。

点位来源：IPUMS NHGIS，1930 Place (Points)图层。[NHGIS地点点位说明](https://www.nhgis.org/place-points)。原始全国图层的记录数16712来自前期说明卡，本次未重新扫描全国DBF来验证该总数。

## 2. 采集记录与范围

- 六城：New York City、Washington DC、Milwaukee、Los Angeles、Cleveland、Baltimore。
- 人口转录表：6城×5个普查年=30条记录，单位人；点位表：6城×1930年=6条记录。
- 前期说明卡更新日期为2026-10-14，不能当成精确下载日期；本包未提供每份文件的下载时间日志。
- 人口处理方法：从官方PDF视觉转录，逐行保留机构、报告、链接、文件、页码、表号、原地点名等追溯字段。
- 点位处理方法：按州和完整地点名称精确匹配，属性来自DBF，坐标来自SHP；没有根据现代代码生成地点标识。
- 人工复核（2026-11-03 完成）：负责人黄超博按源卡每城 PDF 页码逐行核对 30 条人口转录（含新增三城），确认无误；日期与范围已注明。
- 本次分析输入使用小组融合主表，不直接从PDF重建疫情/气象/报刊数据。

## 3. 人口原始页面定位

原PDF目录：`D:\AllFolders\senior1\大数据原理与应用\大作业\黄超博_第一步材料汇总\原始数据\人口普查PDF`。

| 城市 | PDF | PDF页序号（1起） | 印刷页码 | 表号 |
|---|---|---:|---|---:|
| New York City | vol-01-35.pdf | 9 | 32-9 | 4 |
| Washington DC | vol-01-12.pdf | 3 | 9-4 | 4 |
| Milwaukee | vol-01-52.pdf | 9 | 49-9 | 4 |
| Los Angeles | vol-01-08.pdf | 10 | 5-10 | 4 |
| Cleveland | vol-01-38.pdf | 8 | 35-8 | 4 |
| Baltimore | vol-01-23.pdf | 7 | 20-8 | 4 |

每条记录的实际PDF下载链接保留在随包`inputs/population_sample.csv`的`source_url`，不以总目录链接代替逐行追溯。六份PDF本次均确认存在，所列页序号均在文档范围内。

## 4. 人口字段字典

| 字段 | 含义与口径 |
|---|---|
| city_id | 项目自建城市标识，不是官方地点代码 |
| city_name / state_abbr / state_name | 标准城市名称、州缩写、州或特区全名 |
| census_year | 普查年份：1910/1920/1930/1940/1950 |
| population / unit | 总人口，单位persons（人）；原始表为普查观测值 |
| geography_type | 城市统计口径；Washington DC为city_dc_equivalent |
| source_agency / source_title | 来源机构和报告标题 |
| source_url / source_pdf | 官方PDF链接与文件名 |
| source_pdf_page | PDF页序号，从1开始 |
| source_printed_page / source_table | 原书印刷页码与表号 |
| source_location_label | 原表地点名称，供逐行核对 |
| extraction_method | visual_transcription_from_official_pdf，官方PDF视觉转录 |
| population_method | census_observed，普查观测值 |
| boundary_comparability | not_harmonized，历史边界未统一 |
| tycho_city | 清洗表新增的疫情侧城市匹配名称，例如NEW YORK；原始population_sample无此列 |

清洗表`population_clean.csv`仅保留8列：city_id、city_name、state_abbr、census_year、population、tycho_city、source_title、boundary_comparability。完整来源字段仍需回查population_sample，不能认为清洗后来源信息不存在。

## 5. 点位字段字典

| 字段 | 含义与口径 |
|---|---|
| city_id / city_name / state_name | 项目城市标识、名称、州名 |
| place_1930 | NHGIS原始完整地点名 |
| nhgisplace | NHGIS地点标识，文本保存 |
| year | 点位年份，均为1930 |
| x_m / y_m | 原始投影坐标，单位米，不是经纬度 |
| crs_name | USA_Contiguous_Albers_Equal_Area_Conic，NAD83 |
| match_status | exact_state_and_place_name，按州和地点名精确匹配 |
| lon / lat | 后续清洗点位表新增的经度/纬度；不是原始x_m/y_m的直接改名 |
| tycho_city | 后续清洗表新增的跨源城市名称 |

原PRJ参数（据前期说明卡）：GRS1980椭球、中央经线−96°、原点纬度37.5°、标准纬线29.5°与45.5°、假东和假北均为0米。交接包GAPS记载了坐标转换修正；本次Q4/Q5不使用点位做空间计算，也未重新执行坐标变换。

## 6. 从普查到融合主表

人口原PDF → population_sample.csv（30条普查记录）→ population_clean.csv（对齐城市名）→ 按年线性插值 → 按city和year写入每个周日记录 → 与疫情、NOAA、报刊组成融合主表。

两次相邻普查年份a、b之间，年份y的人口：

`P(y) = P(a) + [P(b)-P(a)] × (y-a)/(b-a)`

融合表同城同年各周使用同一个年度估计。普查年保留原值。研究窗口1915–1922与1930–1932均处于已知普查年范围内，不需要超出范围外推。

人均发病率：`病例数 / 当年插值人口 × 100000`。病例缺失则发病率缺失，不填0。原始普查观测表不改写为插值表。

连接键：原始人口与点位按city_id；清洗后的疫情名称通过tycho_city对齐融合主表city；融合主键为city×sunday_date。点位仅1930年，不把它称为所有年份实测位置。

## 7. 局限与适用范围

- 人口序列为线性插值，不是逐年实测，也不能描述迁移或疫情冲击导致的短期人口变化。
- not_harmonized表示城市历史边界未统一。扩界可能导致人口增加；不将变化全部归因于自然增长。
- New York为全市，不是New York County或单个borough；Los Angeles为city不是county；Baltimore city与county区分；Cleveland不包含Cleveland Heights/East Cleveland；Milwaukee为city；DC不是Washington州。
- NHGIS点位不是行政边界，不能计算城市面积或人口密度。当前数据不包含收入、年龄、职业等社会结构指标。
- 跨源城市名称一致不等于统计辖区已经逐条一致；此限制在城市比较中继续保留。
- 前期源卡报告PDF共23,100,361字节、ZIP611,820字节。ZIP与解压图层是同一份数据，不能重复计入有效数据量；全国/全州文件体积也不等于六城有效数据规模。

## 8. 本次核验记录

运行`scripts/verify.py`独立检查30条原始转录值与清洗值、融合人口插值、各病种每十万人率公式；详细通过/失败状态见`outputs/validation.json`。本次同时定位原PDF相关页并进行AI页面抽查；负责人人工复核已于 2026-11-03 完成。
