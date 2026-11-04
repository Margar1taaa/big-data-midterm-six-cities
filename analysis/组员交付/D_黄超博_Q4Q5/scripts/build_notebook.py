"""生成带教学说明的笔记本；分析逻辑集中在 analyze.py，避免两套代码漂移。"""
from pathlib import Path
import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
nb = nbf.v4.new_notebook()
nb.metadata = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3.11"}}
md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell
nb.cells = [
    md("# 组员 D：Q4 城市差异、Q5 综合特征聚类\n\n运行方式：打开本文件后选择 **Restart Kernel and Run All Cells**。所有计算都在本机运行，不访问网络。\n\n主分析为1930–1932年白喉；Q4另有1915–1922对照。详细方法见`outputs/分析口径与待核对事项.md`。完整实现保留在`scripts/analyze.py`，本笔记本负责按步骤展示输入、计算和结果。"),
    code("from pathlib import Path\nimport sys\nimport pandas as pd\nfrom IPython.display import display, Image, Markdown\nROOT = Path.cwd()\nif not (ROOT / 'scripts/analyze.py').exists():\n    raise RuntimeError('请从组员D_分析交付目录打开笔记本')\nsys.path.insert(0, str(ROOT / 'scripts'))\nimport analyze\nimport verify\nprint('Python:', sys.executable)\nprint('工作目录:', ROOT)"),
    md("## 1. 读取已冻结的输入\n\n`inputs`是原文件副本，防止上游更新后无法解释旧结果。CSV带BOM，用utf-8-sig读取。缺失留空，不填0。"),
    code("data = pd.read_csv(analyze.SOURCE, encoding='utf-8-sig', parse_dates=['sunday_date'])\nprint('主表形状:', data.shape)\ndisplay(data.head())"),
    md("## 2. 看覆盖，再确定比较范围\n\n先检查各病种数据完整性，不能把缺失视为零病例。本次白喉覆盖较好。"),
    code("display(data[data.year.between(1930,1932)].groupby('city')[['flu_rate_per100k','diph_rate_per100k','polio_rate_per100k','np_diph_rate','snow_sum']].count())"),
    md("## 3. Q4：按城市做4周平滑，再取共同有效周\n\n完整4周才计算，不跨城市或研究时段滚动；六城使用同一批周。图中使用跨城z-score，表中保留原单位。"),
    code("prepared = analyze.prepare_window(data, 1930, 1932)\nsummary, common, n_weeks = analyze.aggregate_common(prepared, ['population','diph_rate_per100k','np_diph_rate'])\nprint('共同有效周:', n_weeks)\ndisplay(summary)\ndisplay(analyze.zscore(summary))"),
    md("## 4. Q5：标准化后聚类\n\n气温单位为华氏度（℉），降水与降雪单位为英寸。prcp_sum/snow_sum先对各站该周有效观测日求日均，再对站点平均，并非周累计；Q5再对共同有效周求时段均值。口径据2026-10-29用户转述答复确认，详见inputs/气象口径确认.md。人口、气候和报刊指标单位不同，逐列标准化后用Ward层次聚类。只有六城，仅比较K=2、3。轮廓系数用于比较当前候选，不证明真实类别。"),
    code("features, cluster_rows, cluster_weeks = analyze.aggregate_common(prepared, analyze.FEATURES)\ndisplay(features)\nfor k in [2,3]:\n    z, tree, labels, score = analyze.cluster(features, k)\n    print('K=', k, '轮廓系数=', round(score,4), '分组=', dict(zip(features.index, labels)))"),
    md("## 5. 生成全部结果\n\n此步骤会重建outputs中的计算结果和两幅图，不修改inputs。对照分析与报告也在同一次运行生成。"),
    code("analyze.main()\ndisplay(Image(filename=str(ROOT / 'outputs/Q4_城市对比.png')))\ndisplay(Image(filename=str(ROOT / 'outputs/Q5_城市聚类.png')))"),
    md("## 6. 检查结论与稳健性\n\nPearson和Spearman方向不一致时需如实解释；ARI低说明分组依赖设置。不要把六城聚类说成普遍城市规律。"),
    code("display(pd.read_csv(ROOT / 'outputs/q4_correlations.csv'))\ndisplay(pd.read_csv(ROOT / 'outputs/q5_sensitivity.csv'))\ndisplay(Markdown((ROOT / 'outputs/Q4_Q5_结果摘要.md').read_text(encoding='utf-8')))"),
    md("## 7. 独立核验\n\n通过代表所列计算一致，气象单位与汇总定义来自已记录的用户转述答复；自动核验不代表NOAA原始站点清洗、历史边界和因果关系已经验证。运行失败时停下查看具体检查项。"),
    code("verify.main()"),
    md("## 8. 提交前自己检查\n\n1. 打开HTML报告并解释两图。\n2. 从人口源卡找到原PDF页码，至少人工核对六城各一行，并记录真实复核范围。\n3. 将已确认的气象口径同步给E：℉、英寸，降水降雪为周内日均，不是周累计。\n4. 将整包交E；由E决定是否接受白喉范围和分析细则。\n5. 按真实使用情况确认AI_USAGE_D.md。")
]
nbf.write(nb, ROOT / "组员D分析.ipynb")
print(ROOT / "组员D分析.ipynb")
