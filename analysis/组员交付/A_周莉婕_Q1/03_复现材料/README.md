# Q1 报刊关注与疫情同步关系交付

- `Q1_疫情与报刊关注同步关系_1页结果.md`：一页结果与结论。
- `fig_q1_newspaper_disease_sync.png`：核心周序列图。
- `q1_pooled_correlations.csv`：六城池化主结果。
- `q1_city_correlations.csv`：分城市结果。
- `q1_sensitivity_strong_plus_weak_pooled.csv`：强词＋弱词敏感性结果。
- `q1_sensitivity_strong_plus_weak_by_city.csv`：分城市敏感性结果。
- `q1_paired_city_weeks.csv`：清洗、平滑、标准化后的成对城市周数据。
- `q1_plot_weekly_series.csv`：核心图的数据。
- `q1_data_quality_checks.csv`：输入表质量检查。
- `q1_newspaper_coverage_by_city.csv`：六城报刊覆盖周数。
- `报刊数据源卡.md`：材料线数据源卡。
- `AI_USAGE_A_报刊分析.md`：AI 使用说明；原始记录未保存具体工具、模型、使用时间与逐字 Prompt，文档按现有证据如实标注。

重跑命令：

```bash
MPLBACKEND=Agg python3 scripts/analyze_q1_newspaper.py
```

输入为 `data/integrated/weekly_sixcities_1915_1922_1930_1932.csv`。
