# 提交材料说明

项目：六座城市公共卫生、报刊关注与气象条件的多源数据分析

GitHub：<https://github.com/Margar1taaa/big-data-midterm-six-cities>

## 文件清单

| 文件或目录 | 内容 |
|---|---|
| `研究报告.docx` | 项目研究报告 |
| `大数据中期汇报.pptx` | 项目展示 PPT |
| `big-data-midterm-six-cities_code.zip` | 代码仓库压缩包，含 README、采集/清洗/融合/分析脚本、分析产物、cleaned 与 integrated 数据，不含体积较大的 raw 原始数据 |
| `data_sources.md` | 数据源清单、来源、时间范围、规模、许可/访问说明与采集记录 |
| `数据集样本与元数据/` | 五类代表性样本、Tycho 字段字典与来源卡、数据集清单、SHA256 校验值及样本验证结果 |
| `多源数据血缘图.png` | 报刊、Tycho、NOAA、人口数据到融合表及分析结果的数据血缘图 |
| `AI_USAGE.md` | 分工级 AI 使用记录、采用范围、人工核验方式与复现边界 |

## 数据与复现说明

- 原始大文件未放入提交压缩包或 Git 仓库；获取方式、来源链接与校验信息见 `data_sources.md`、代码包内 `data/raw/README.md` 及 `data/metadata/`。
- 代表性样本覆盖报刊 raw OCR、报刊 cleaned、Tycho、NOAA、NHGIS 和最终融合表；`samples_validation.json` 记录样本存在性、字段与哈希检查结果。
- Tycho 可通过项目采集脚本按来源记录重新获取并校验；报刊数据为按目录结构人工采集后由脚本扫描；NOAA 与 NHGIS 原始文件为人工下载归档。
- NOAA 原采集时清洗脚本与导出配置未保留。项目内 `clean_noaa.py --check` 是独立重建核验：键和缺失掩码一致，62 个数值单元最大相差 0.01；从权威 cleaned 表到 integrated 与 Q3 可精确复现。
- 代码压缩包 SHA256：`8598E28BA78116132E47D402745793FC0BDA87F640837AC9019BCEB68027D99F`。

## 提交前检查结果

- 项目及提交材料共 50 个 Markdown 文件的本地相对链接检查：0 个缺失。
- 数据集清单覆盖 15 个样本/元数据文件，并记录文件大小与 SHA256。
- Git 差异格式检查无错误；本目录（含代码 ZIP）随公开仓库同步，远端状态以 GitHub `main` 分支最新提交为准。
