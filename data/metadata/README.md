# 提交用数据样本

本目录按数据来源保存小型代表性样本。样本只用于展示字段结构、数据粒度和跨源关联键，不用于替代完整数据进行统计分析。

| 数据 | 样本 | 抽样口径 |
|---|---|---|
| 报刊 | `newspaper/sample_newspaper.csv` | 六城 × 三病种各 1 条有命中记录，共 18 行 |
| Project Tycho | `tycho/sample_tycho.csv` | 六城 × 三病种各 1 条病例记录，共 18 行 |
| NOAA | `noaa/sample_noaa.csv` | 六城各 1 个完整观测周，共 6 行 |
| NHGIS/人口普查 | `nhgis/sample_nhgis.csv` | 六城 1930 年人口与点位，共 6 行 |
| 融合主表 | `integrated/sample_integrated.csv` | 六城各 1 个 1920 年完整城市周，共 6 行 |

所有样本由 `scripts/build_submission_samples.py` 从项目清洗数据确定性生成。行数和覆盖范围见 `samples_validation.json`。

报刊另提供原始OCR样本：`newspaper/sample_newspaper_raw.csv` 是文件清单，原文件副本保存在 `newspaper/sample_newspaper_raw/`。该样本由 `scripts/sample_newspaper_raw.py` 在45秒时限内生成，只逐层查看单一目录分支，不递归扫描；当前只抽取三个已展开城市，不打开约3.85GB的三城ZIP。

## 元数据与校验

- `dataset_manifest.csv`：核心清洗文件、融合表和全部样本的路径、字节数、行列数及 SHA-256。
- `samples_validation.json`：各样本的行数与城市、疾病或年份覆盖范围。
- 报刊来源说明：`../../analysis/组员交付/A_周莉婕_Q1/01_主要成果/报刊数据源卡.md`
- Project Tycho 来源说明：`tycho/source_card.md`
- NOAA 来源说明：`../../analysis/组员交付/C_黄祉玥_Q3/Q3_NOAA_20261031/analysis/noaa_source_card/NOAA_source_card.md`
- NHGIS 与人口数据说明：`../raw/nhgis/数据说明卡.md`
- 融合表字段与口径：`../integrated/README.md`
