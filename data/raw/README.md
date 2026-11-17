# raw 数据说明

本目录的完整原始数据体量约 5.36 GB，保存在组内 OneDrive/本地目录，不提交 GitHub。Git 只保留本说明文件；清洗结果和融合结果分别位于 `data/cleaned/` 与 `data/integrated/`。

| 数据源 | 本地位置 | 当前口径 | GitHub 处理 |
|---|---|---|---|
| Project Tycho | `data/raw/tycho/` | 项目 1900–1960 提取表，2,934,886 行，407.75 MB | 不上传；由 `scripts/collect_project_tycho.py` 按 DOI 下载、校验并提取，manifest 见 `data/metadata/tycho/` |
| NOAA GHCN-Daily | `data/raw/noaa/` | 58 份原始宽表 75.33 MB；完整目录 354.65 MB，含转换长表和目录文件 | 不上传；来源和校验见 `data_sources.md` 及 C 组 manifest |
| NHGIS/Census | `data/raw/nhgis/` | 点位、普查材料及 PDF，28.66 MB | 不上传原件；清洗表保留在仓库 |
| Chronicling America | `data/raw/newspaper/` | 六城 299,358 页 OCR，4.57 GB | 不上传；组内 OneDrive 保存 |

## 恢复目录

从 OneDrive 获取完整数据后，保持以下路径不变：

```text
data/raw/tycho/
data/raw/noaa/
data/raw/nhgis/
data/raw/newspaper/
```

脚本均通过项目根目录的相对路径读取这些文件，无需修改电脑用户名或绝对路径。来源、许可、采集日期、字段与校验信息见根目录 `data_sources.md`；Tycho 采集记录见 `data/metadata/tycho/`。

