# 任务 3（Q3）与线 B NOAA 气象源卡交付
当前目录为可交付项目根；原交接包与“查阅”目录保留。
先打开 **[Q3 一页结果](analysis/q3/Q3_one_page.html)** 和 **[NOAA 一页源卡](analysis/noaa_source_card/NOAA_one_page.html)**；详细源卡看 **[NOAA_source_card.md](analysis/noaa_source_card/NOAA_source_card.md)**。

| 交付内容 | 位置 |
|---|---|
| 一页结果＋分病种核心图 | `analysis/q3/Q3_one_page.html`、`q3_core.png`、`q3_core.svg` |
| 完整方法、解读与局限 | `analysis/q3/Q3_report.md` |
| 系数、城市分层、8类敏感性、复核中间表 | `analysis/q3/*.csv` |
| NOAA源卡、字段字典、站点映射、采集记录 | `analysis/noaa_source_card/` |
| 可复现脚本 | `scripts/` |
| 日期口径与缺口记录 | `docs/GAPS.md`（2026-10-31追加） |
| C的AI使用供稿 | `docs/AI_USAGE_C.md` |
| 输入数据 | `data/cleaned/`、`data/integrated/`，来自交接包 |
| 输入SHA、版本、核验结果 | `analysis/q3/run_manifest.json`、`verification.json`、`reproducibility_check.json` |

## 已得结果

平均温度主分析与流感负相关（r=-0.260）、与脊灰正相关（r=0.277）、与白喉负相关（r=-0.371）。控制各城月份与年份后，脊灰和白喉的关联明显减弱；流感仍有较弱负关联（r=-0.164）。降水缺乏稳定证据；降雪关联在季节/年份调整后减弱。
Pearson为主、Spearman为对照。缺失不补0，病例完整4周均值，流感整段排除1915–1919；图上星号使用8周分块置换并经15项BH校正。具体量级对病例偏态、缺失及城市覆盖敏感，详见完整报告。

## 重跑

建议 Python 3.13，终端在本目录运行：

```powershell
python -m pip install -r requirements-lock.txt
python scripts/build_integrated.py --check
python scripts/run_q3.py
```

- CSV一律以`utf-8-sig`读取/写出。`build_integrated.py --check`逐格对照主表，不改数据；不带`--check`时，只有与现有主表零差异才写入重建表。重建时忠实保留原交接口径（包括1933-01-01边界周和报刊分母的继承问题）。
- `run_q3.py`默认置换999次、固定种子20261031，输出Q3和NOAA源卡。用`python scripts/verify_reproducibility.py`对照当前产物与一次重跑的SHA256。
- `requirements-lock.txt`记录本机实测直接依赖；PNG中文字体使用Microsoft YaHei/SimHei，其他系统若缺中文字体应先安装，字体变化会使图像哈希变化。数值复现需固定输入及依赖版本。
- 当前可复现范围：cleaned→integrated→分析/源卡。




## 展示目录整理

analysis/q3顶层仅保留一页结果、完整报告、核心图、城市对比图和主系数表；其他中间数据、城市分层及敏感性表、审计与复现JSON移入补充材料。analysis/noaa_source_card顶层保留一页源卡及详细源卡，字段字典、站点映射、覆盖表、采集记录移入补充材料。旧文件名说明中的辅助文件现在以补充材料内路径为准。重跑run_q3.py会自动保持此目录结构，也可单独运行scripts/organize_analysis.py。
