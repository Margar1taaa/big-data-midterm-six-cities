"""独立数值验收：失败时非零退出，详细结果写入 outputs/validation.json。"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, cut_tree
from sklearn.metrics import adjusted_rand_score

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"


def main():
    checks = []

    def check(name, ok, detail=""):
        checks.append({"check": name, "passed": bool(ok), "detail": str(detail)})

    data = pd.read_csv(ROOT / "inputs/weekly_sixcities_1915_1922_1930_1932.csv", parse_dates=["sunday_date"])
    raw = pd.read_csv(ROOT / "inputs/population_sample.csv")
    clean = pd.read_csv(ROOT / "inputs/population_clean.csv")
    manifest = json.loads((OUT / "run_manifest.json").read_text(encoding="utf-8"))
    check("输入文件哈希一致", all(hashlib.sha256((ROOT / "inputs" / name).read_bytes()).hexdigest() == value for name, value in manifest["inputs_sha256"].items()))
    check("主表3450行29列", data.shape == (3450, 29))
    check("城市周主键唯一", not data.duplicated(["city", "sunday_date"]).any())
    check("周标签均为周日", data.sunday_date.dt.dayofweek.eq(6).all())
    merged = raw.merge(clean, on=["city_id", "census_year"], suffixes=("_raw", "_clean"), validate="one_to_one")
    check("原始30个人口值与清洗表一致", len(merged) == 30 and merged.population_raw.eq(merged.population_clean).all())
    pop_errors = []
    for city, group in data.groupby("city"):
        obs = clean[clean.tycho_city.eq(city)].sort_values("census_year")
        expected = np.interp(group.year, obs.census_year, obs.population)
        pop_errors.extend(abs(expected - group.population))
    check("融合人口符合普查年线性插值", max(pop_errors) <= 1, f"最大误差 {max(pop_errors):.6f} 人（容许整数舍入1人）")
    for disease in ["flu", "diph", "polio"]:
        expected_rate = data[f"{disease}_cases"] / data.population * 100000
        rate = data[f"{disease}_rate_per100k"]
        check(f"{disease}每十万人率公式", np.allclose(expected_rate, rate, equal_nan=True, atol=.00500001, rtol=0), f"主表保留2位小数；最大绝对差{(expected_rate-rate).abs().max():.9f}")
        expected_np = (data[f"np_{disease}_hits"] / data.np_pages.where(data.np_pages.gt(0))) * 100
        check(f"{disease}强词命中率公式", np.allclose(expected_np, data[f"np_{disease}_rate"], equal_nan=True, atol=.00500001, rtol=0), f"主表保留2位小数；最大绝对差{(expected_np-data[f'np_{disease}_rate']).abs().max():.9f}")
    check("无报刊覆盖周命中率为NA", data.loc[data.np_pages.eq(0), ["np_flu_rate", "np_diph_rate", "np_polio_rate"]].isna().all().all())
    for start, end in [(1915, 1922), (1930, 1932)]:
        exported = pd.read_csv(OUT / f"q4_common_weeks_{start}-{end}.csv", parse_dates=["sunday_date"])
        dates = pd.date_range(f"{start}-01-01", f"{end}-12-31", freq="W-SUN")
        pivot = data[data.year.between(start, end)].pivot(index="sunday_date", columns="city", values=["diph_rate_per100k", "np_diph_rate"]).reindex(dates)
        rolled = pivot.rolling(4, min_periods=4).mean()
        valid_dates = rolled.index[rolled.notna().all(axis=1)]
        check(f"Q4 {start}-{end}共同周独立重算", set(exported.sunday_date) == set(valid_dates))
        check(f"Q4 {start}-{end}每周六城齐全", exported.groupby("sunday_date").city.nunique().eq(6).all())
        check(f"Q4 {start}-{end}不跨窗口平滑", exported.sunday_date.min() >= dates[3] and exported.sunday_date.max() <= dates[-1])
        for metric in ["diph_rate_per100k", "np_diph_rate"]:
            expected = rolled[metric].loc[valid_dates].stack()
            actual = exported.set_index(["sunday_date", "city"])[metric].reindex(expected.index)
            check(f"Q4 {start}-{end} {metric}滚动值", np.allclose(actual, expected, atol=1e-9))
        summary = pd.read_csv(OUT / f"q4_summary_{start}-{end}.csv").set_index("city")
        check(f"Q4 {start}-{end}均值与导出样本一致", np.allclose(summary[["population", "diph_rate_per100k", "np_diph_rate"]], exported.groupby("city")[["population", "diph_rate_per100k", "np_diph_rate"]].mean().reindex(summary.index)))
    features = pd.read_csv(OUT / "q5_features_raw.csv").set_index("city")
    zs = pd.read_csv(OUT / "q5_features_zscore.csv").set_index("city")
    rows = pd.read_csv(OUT / "q5_common_weeks.csv")
    check("Q5特征来自共同周均值", np.allclose(features, rows.groupby("city")[features.columns].mean().reindex(features.index)))
    check("Q5无缺失", features.notna().all().all() and zs.notna().all().all())
    check("Q5标准化均值0方差1", np.allclose(zs.mean(), 0, atol=1e-10) and np.allclose(zs.std(ddof=0), 1, atol=1e-10))
    recomputed = (features - features.mean()) / features.std(ddof=0)
    labels = cut_tree(linkage(recomputed, method="ward"), n_clusters=manifest["selected_k"]).ravel()
    saved_labels = pd.read_csv(OUT / "q5_clusters.csv").set_index("city").loc[features.index, "cluster"]
    check("Q5分组可独立重现", adjusted_rand_score(labels, saved_labels) == 1)
    scores = pd.read_csv(OUT / "q5_k_scores.csv")
    expected_k = int(scores.sort_values(["silhouette", "k"], ascending=[False, True]).iloc[0].k)
    check("K选择符合已声明规则", expected_k == manifest["selected_k"])
    check("两幅PNG和SVG存在", all((OUT / f"{name}.{ext}").stat().st_size > 1000 for name in ["Q4_城市对比", "Q5_城市聚类"] for ext in ["png", "svg"]))
    result = {"all_passed": all(c["passed"] for c in checks), "passed": sum(c["passed"] for c in checks), "total": len(checks), "checks": checks,
              "not_verified": ["负责人对全部原始PDF的人工复核", "NOAA原始站点记录、站点归属及清洗脚本实现（单位与汇总定义已据用户转述答复确认）", "跨源行政统计边界一致性", "人口或媒体对疫情的因果影响"]}
    (OUT / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
