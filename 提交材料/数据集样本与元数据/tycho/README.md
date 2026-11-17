# Project Tycho 数据采集交付说明

本次采集不预选病种，先完整下载 Project Tycho 官方历史档案 Level 1 v1.0.0 和 Level 2 v1.1.0，再按研究时间范围导出全部疾病记录。当前项目保留 Level 2 的 1900—1960 年全病种提取表；采集脚本可按需重新生成其他范围和辅助元数据。

## 采集记录中的原始数据

- `data/raw/tycho/source_archives/ProjectTycho_Level1_v1.0.0.zip`
  - 3,628,564 字节
  - MD5 `4c3991594d8dbad117e69ef49808eb5b`
  - DOI `10.5281/zenodo.12608992`
- `data/raw/tycho/source_archives/ProjectTycho_Level2_v1.1.0.zip`
  - 22,157,131 字节
  - MD5 `c3f3b1cfa4e8aa54cb730f26283cc194`
  - DOI `10.5281/zenodo.12608994`

两个 MD5 均与 Zenodo 官方记录一致。解压后的原始 CSV 分别有 759,467 行和 3,659,360 行。

## 1916—1953 年历史运行记录

- `data/raw/tycho/ProjectTycho_LEVEL1_1916_1953_all_diseases.csv`
  - 5 种疾病
  - 366,173 行
  - 23,814,264 字节
- `data/raw/tycho/ProjectTycho_LEVEL2_1916_1953_all_diseases.csv`
  - 28 种疾病
  - 2,542,953 行
  - 352,415,005 字节

两份派生主表合计 2,909,126 行，约 376.2 MB。Level 1 与 Level 2 存在重叠，不能直接纵向拼接为独立样本。

## 1900—1960 年全病种数据

以下数据由同一采集脚本按 1900—1960 年重新筛选，保留该时间段内出现的全部疾病：

- `data/raw/tycho/ProjectTycho_LEVEL1_1900_1960_all_diseases.csv`
  - 5 种疾病
  - 401,769 行
  - 26,127,116 字节
  - Level 1 原始数据从 1916 年开始，因此此文件实际覆盖 1916—1960 年。
- `data/raw/tycho/ProjectTycho_LEVEL2_1900_1960_all_diseases.csv`
  - 33 种疾病
  - 2,934,886 行
  - 407,747,781 字节
  - 实际覆盖 1900—1960 年。

已下载原始 ZIP 时，可在项目根目录运行以下命令重新生成：

```powershell
python scripts\collect_project_tycho.py `
  --root . `
  --start-year 1900 `
  --end-year 1960 `
  --chunksize 250000 `
  --skip-download
```

`--skip-download` 表示使用本地已有的原始 ZIP，不再联网下载。若需从头下载，删除该参数即可。Level 2 文件超过 WPS/Excel 单个工作表的行数上限，应使用 Python 分块读取或按疾病拆分后再用表格软件查看。

## 辅助文件

用于最终提交的数据样本与字段说明直接保存在本目录：

- `sample_tycho.csv`：项目实际使用的六座城市与三种疾病各保留 1 条 `CASES` 记录，共 18 行；由 `scripts/clean_tycho.py` 生成。
- `field_dictionary_tycho.csv`：说明样本及 Tycho 清洗表的 10 个字段。

文件名统一采用“材料类型 + 数据来源”的简洁形式。样本只用于展示结构与代表性记录，不用于统计分析。

采集脚本还会将下列过程性文件写入 `data/metadata/tycho/generated/`：

- `disease_coverage_1916_1953.csv` 和 `disease_coverage_1900_1960.csv`：各版本各病种的年份、周数、城市数、州数、事件类型和非零记录数。
- `location_coverage_1916_1953.csv` 和 `location_coverage_1900_1960.csv`：病种—地点层面的起止年、周数和记录数。
- `data_manifest.csv`：最近一次运行的下载地址、文件大小、MD5、筛选范围和输出行数；当前对应 1900—1960 年。
- `run_summary.json`：最近一次运行的机器可读摘要；当前对应 1900—1960 年。

## 复现代码

运行：

```powershell
python scripts/collect_project_tycho.py --root . --start-year 1900 --end-year 1960
```

已下载原始 ZIP 时，可以跳过网络下载：

```powershell
python scripts/collect_project_tycho.py --root . --start-year 1900 --end-year 1960 --skip-download
```

脚本会校验 MD5、解压、按块读取大 CSV、保留全部病种并输出覆盖统计。依赖 Python 3 和 pandas。

## 使用提醒

- Level 1 除白喉外主要为州级数据；城市—周—疾病面板应重点核验 Level 2。
- `number` 无空值并不代表没有缺报。某城市某周没有记录不能直接填 0。
- Level 2 的 `number` 必须结合 `event` 区分病例和死亡。
- 两版本疾病命名不完全一致，例如 `POLIO` 与 `POLIOMYELITIS`，后续需要疾病别名表。
- 历史整包按 Creative Commons Attribution 条款使用，报告中应注明 Project Tycho 来源。
