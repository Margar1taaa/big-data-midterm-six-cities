# data 三层数据目录

> 按大作业 Raw / Cleaned / Integrated 三层组织，每层按数据源分子目录。
> 更新：2026-11-04

```
data\
├── raw\          项目保留的采集/提取层数据（GitHub 仅上传样本、元数据与校验值）
│   ├── tycho\        Level 2 的 1900–1960 项目提取表（2,934,886 行；407.75MB）
│   ├── noaa\         NOAA 六城站点数据：58 份原始宽表 75.33MB；目录共 354.65MB，含 long_chart 与目录文件
│   ├── nhgis\        NHGIS 点位 + 普查卷人口材料（28.66MB）
│   └── newspaper\    六城报刊 OCR，299,358 页，4.57GB（目录批次 + ZIP 批次）
├── cleaned\      单源清洗产物（见 cleaned\README.md 数据字典）
│   ├── tycho\       六城三病种疫情周长表（40,318 行）
│   ├── noaa\        六城气象周表（20,655 行）+ 站映射
│   ├── nhgis\       六城经纬度 + 30 条普查年人口
│   └── newspaper\   六城报刊覆盖矩阵 + 强/弱关键词命中
├── integrated\   已完成的周级融合主表（3,450 行 × 29 列）
└── README.md     本文件
```

## 各层职责

- **raw**：保留下载原件或项目使用的提取表。Tycho 当前文件已筛选为 1900–1960，并增加 `year/week/source_level`，不是未改动的官方 11 列完整表。
- **cleaned**：每个源的清洗结果，统一周历、城市名和缺失值口径，可由 `scripts\` 下脚本复现。
- **integrated**：跨源融合主表、派生指标和覆盖摘要，供 Q1–Q5 分析使用。

## 复现

从项目根目录运行；脚本以自身位置定位项目根目录，不依赖本机绝对路径。

```
python scripts\clean_tycho.py
python scripts\clean_noaa.py
python scripts\convert_nhgis.py
python scripts\scan_newspaper.py
python scripts\scan_newspaper_zip.py
python scripts\build_integrated.py
python scripts\add_derived_metrics.py --write
```

依赖：Python 3.10+、pyproj；生成 Word/截图时另需 python-docx、playwright。
