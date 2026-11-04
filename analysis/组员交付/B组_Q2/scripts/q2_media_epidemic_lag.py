"""Q2: city-wise media/epidemic lag correlations, reproducibly from the integrated CSV.

Positive lag means newspaper attention follows case counts by that many weeks.
Run: python scripts/q2_media_epidemic_lag.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/integrated/weekly_sixcities_1915_1922_1930_1932.csv"
OUTPUT = ROOT / "analysis/q2"
DISEASES = {
    "flu": ("流感", "flu_cases", "np_flu_rate"),
    "polio": ("脊灰", "polio_cases", "np_polio_rate"),
    "diph": ("白喉", "diph_cases", "np_diph_rate"),
}
LAGS = range(-4, 5)


def read_source() -> pd.DataFrame:
    df = pd.read_csv(INPUT, encoding="utf-8-sig", parse_dates=["sunday_date"])
    required = {"city", "sunday_date"} | {c for _, x, y in DISEASES.values() for c in (x, y)}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Integrated table is missing columns: {sorted(missing)}")
    if df.duplicated(["city", "sunday_date"]).any():
        raise ValueError("Duplicate city × sunday_date keys in integrated table")
    if (df.sunday_date.dt.dayofweek != 6).any():
        raise ValueError("sunday_date contains non-Sunday dates")
    return df.sort_values(["city", "sunday_date"]).reset_index(drop=True)


def smooth_one_disease(source: pd.DataFrame, disease: str) -> pd.DataFrame:
    _, case_col, news_col = DISEASES[disease]
    d = source[["city", "sunday_date", case_col, news_col]].copy()
    if disease == "flu":
        d = d.loc[d.sunday_date.dt.year >= 1920].copy()  # agreed rule 07
    d["cases"] = pd.to_numeric(d[case_col], errors="coerce")
    d["media"] = pd.to_numeric(d[news_col], errors="coerce")
    d = d.drop(columns=[case_col, news_col])
    # A four-week window must contain four consecutive, observed weeks.
    gap = d.groupby("city").sunday_date.diff().ne(pd.Timedelta(days=7))
    d["segment"] = gap.groupby(d.city).cumsum()
    for col in ("cases", "media"):
        d[f"{col}_ma4"] = d.groupby(["city", "segment"])[col].transform(
            lambda s: s.rolling(window=4, min_periods=4).mean()
        )
    return d


def city_correlations(d: pd.DataFrame, disease: str) -> list[dict]:
    records = []
    cases = d[["city", "sunday_date", "cases_ma4"]].rename(columns={"sunday_date": "case_date"})
    media = d[["city", "sunday_date", "media_ma4"]]
    for lag in LAGS:
        # At lag +k, compare cases at t to media at t+k.
        shifted = media.assign(case_date=media.sunday_date - pd.Timedelta(weeks=lag))
        paired = cases.merge(shifted[["city", "case_date", "media_ma4"]],
                             on=["city", "case_date"], how="inner").dropna()
        for city, group in paired.groupby("city", sort=True):
            x = group.cases_ma4.to_numpy(dtype=float)
            y = group.media_ma4.to_numpy(dtype=float)
            if len(x) < 12 or np.std(x) == 0 or np.std(y) == 0:
                continue
            pearson = pearsonr(x, y)
            spearman = spearmanr(x, y)
            records.append({
                "disease": disease, "city": city, "lag_weeks": lag,
                "n_pairs": len(x), "pearson_r": float(pearson.statistic),
                "pearson_p_naive": float(pearson.pvalue),
                "spearman_rho": float(spearman.statistic),
                "spearman_p_naive": float(spearman.pvalue),
            })
    return records


def fisher_pool(city_results: pd.DataFrame) -> pd.DataFrame:
    """Combine within-city coefficients; avoids raw case-count scale dominating cities."""
    records = []
    for (disease, lag), g in city_results.groupby(["disease", "lag_weeks"], sort=True):
        weights = np.maximum(g.n_pairs.to_numpy(dtype=float) - 3, 0)
        row = {"disease": disease, "lag_weeks": int(lag),
               "n_cities": len(g), "n_pairs_total": int(g.n_pairs.sum())}
        for src, dest in (("pearson_r", "pearson_r"), ("spearman_rho", "spearman_rho")):
            z = np.arctanh(np.clip(g[src].to_numpy(dtype=float), -0.999999, 0.999999))
            row[dest] = float(np.tanh(np.average(z, weights=weights)))
        records.append(row)
    return pd.DataFrame(records).sort_values(["disease", "lag_weeks"])


def make_figure(pooled: pd.DataFrame) -> None:
    plt.rcParams.update({"font.sans-serif": ["SimHei", "Microsoft YaHei", "DejaVu Sans"],
                         "axes.unicode_minus": False, "font.size": 11})
    fig, axes = plt.subplots(1, 3, figsize=(14.6, 5.6), sharey=True)
    for ax, (disease, (name, _, _)) in zip(axes, DISEASES.items()):
        g = pooled.loc[pooled.disease.eq(disease)].sort_values("lag_weeks")
        ax.plot(g.lag_weeks, g.pearson_r, marker="o", lw=2.2, color="#24547a", label="Pearson")
        ax.plot(g.lag_weeks, g.spearman_rho, marker="s", ls="--", lw=1.8,
                color="#c27542", label="Spearman")
        ax.axvline(0, color="#667788", lw=1, ls=":")
        ax.axhline(0, color="#b5c2cc", lw=0.8)
        peak = g.loc[g.pearson_r.idxmax()]
        panel_title = (f"白喉｜Pearson 峰值 {int(peak.lag_weeks):+d} 周（相关弱）" if disease == "diph"
                       else f"{name}｜Pearson 峰值 {int(peak.lag_weeks):+d} 周")
        ax.set(title=panel_title,
               xlabel="滞后周数（周）")
        ax.set_xticks(list(LAGS))
        # Correlation coefficients are bounded by [-1, 1]; show the full scale.
        ax.set_ylim(-1, 1)
        ax.set_yticks([-1, -0.5, 0, 0.5, 1])
        ax.grid(axis="y", alpha=0.2)
    axes[0].set_ylabel("城内相关系数（无单位）")
    axes[-1].legend(frameon=False, loc="upper right")
    fig.suptitle("Q2：媒体关注领先还是滞后疫情？", fontsize=16, weight="bold", y=0.99)
    fig.text(0.5, 0.025,
             "正数：比较病例之后的媒体关注；负数：比较病例之前的媒体关注。各城先做 4 周均值，再汇总六城相关。",
             ha="center", fontsize=9)
    fig.text(0.5, 0.002,
             "主表覆盖：1915–1922、1930–1932。来源：六城融合主表（Tycho 病例、报刊强词命中率）。",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.065, 1, 0.92))
    fig.savefig(OUTPUT / "q2_lag_correlation.png", dpi=200)
    plt.close(fig)


def make_report(pooled: pd.DataFrame, city: pd.DataFrame) -> None:
    lines = ["# Q2 媒体关注领先还是滞后疫情？", "",
             "数据：`data/integrated/weekly_sixcities_1915_1922_1930_1932.csv`（`utf-8-sig`）。",
             "图：`q2_lag_correlation.png`；汇总：`lag_correlations.csv`；各城：`city_lag_correlations.csv`。", "",
             "## 方法", "",
             "- 六城各按 `sunday_date` 排序；病例与报刊强词命中率各做完整 4 个连续周的滚动均值，缺值不填 0。1915–1922 与 1930–1932 不跨段平滑或配对。",
             "- 流感先整段排除 1915–1919，再做平滑与配对；纽约 1919 年末的少量病例也不进入本题。",
             "- 定义 `lag = +k` 为病例在第 t 周、媒体在第 t+k 周：正值是媒体滞后，负值是媒体领先。只按相差恰好 k×7 天的同城周配对。",
             "- 每城计算 Pearson 与 Spearman；再用样本数减 3 为权重的 Fisher z 合并六城相关系数，避免大城市原始病例量主导曲线。", "",
             "- `city_lag_correlations.csv` 包含两种相关的常规 p 值；若标注显著，沿用 p<0.05 口径。但这些 p 值未校正周序列自相关及 9 个滞后择峰，不能作为确认性证据；合并曲线不报告显著性。", "",
             "## 结果", "", "| 病种 | Pearson 峰值滞后 | 峰值 r | 同一滞后 Spearman ρ | 六城有效配对总数 |", "|---|---:|---:|---:|---:|"]
    for disease, (name, _, _) in DISEASES.items():
        g = pooled.loc[pooled.disease.eq(disease)]
        p = g.loc[g.pearson_r.idxmax()]
        lines.append(f"| {name} | {int(p.lag_weeks):+d} 周 | {p.pearson_r:.3f} | {p.spearman_rho:.3f} | {int(p.n_pairs_total)} |")
    lines += ["", "流感的 Pearson 与 Spearman 均在 +1 周附近较高，但峰值处 0.543 与 0.348 量级有差异；部分城市峰值为负滞后或相关很弱，故不作六城一致滞后的断言。",
              "脊灰两种系数在 +2 周附近均达到峰值，但各城峰值从 -1 到 +3 周，说明合并结果掩盖城市差异。",
              "白喉相关较弱、曲线平坦，Pearson 的 +1 周峰值与 0 周相差很小，Spearman 峰值则在 +4 周；不能判定明确的领先或滞后方向。", "",
              "上表峰值是在 -4～+4 周中寻找的最大正相关，属于探索性时序关联；周序列自相关、共同季节性和窗口内择峰会影响显著性，不能据此推断因果或精确传播时延。完整曲线与各城差异见 CSV。", "",
              "## 覆盖与复现", "",
              f"本次主表 {len(read_source())} 行；分析结果含 {len(city)} 个城市×病种×滞后系数与 {len(pooled)} 个汇总系数。",
              "在交接包根目录运行：`python scripts/q2_media_epidemic_lag.py`。脚本只读取融合主表，不改写主表；重建主表后可重跑本脚本。", ""]
    (OUTPUT / "Q2_结果说明.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source = read_source()
    results = []
    for disease in DISEASES:
        results.extend(city_correlations(smooth_one_disease(source, disease), disease))
    city = pd.DataFrame(results).sort_values(["disease", "city", "lag_weeks"])
    pooled = fisher_pool(city)
    city.to_csv(OUTPUT / "city_lag_correlations.csv", index=False, encoding="utf-8-sig")
    pooled.to_csv(OUTPUT / "lag_correlations.csv", index=False, encoding="utf-8-sig")
    make_figure(pooled)
    make_report(pooled, city)
    print(pooled.loc[pooled.groupby("disease").pearson_r.idxmax()].to_string(index=False))


if __name__ == "__main__":
    main()
