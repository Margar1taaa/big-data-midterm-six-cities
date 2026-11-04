"""组员 D：从固定输入重建 Q4/Q5、图表和中文报告。无网络调用。"""
from pathlib import Path
import hashlib
import html
import json
import platform
import importlib.metadata

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from scipy.cluster.hierarchy import linkage, dendrogram, cut_tree
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import silhouette_score, adjusted_rand_score

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
SOURCE = ROOT / "inputs/weekly_sixcities_1915_1922_1930_1932.csv"
CITIES = ["BALTIMORE", "CLEVELAND", "LOS ANGELES", "MILWAUKEE", "NEW YORK", "WASHINGTON"]
NAMES = dict(zip(CITIES, ["巴尔的摩", "克利夫兰", "洛杉矶", "密尔沃基", "纽约", "华盛顿"] ))
FEATURES = ["diph_rate_per100k", "np_diph_rate", "tavg_avg", "prcp_sum", "snow_sum", "population"]
LABELS = ["白喉发病率", "白喉报刊命中率", "气温（℉）", "周内日均降水", "周内日均降雪", "人口"]


def save_csv(frame, name, index=False):
    frame.to_csv(OUT / name, index=index, encoding="utf-8-sig", float_format="%.12g")


def zscore(frame):
    sd = frame.std(ddof=0)
    if (sd == 0).any() or frame.isna().any().any():
        raise ValueError("标准化输入存在缺失或常数列")
    return (frame - frame.mean()) / sd


def prepare_window(data, start, end, smooth=True, min_pages=1):
    """城市内按完整周历滚动；先平滑，再取六城共同有效周。"""
    dates = pd.date_range(f"{start}-01-01", f"{end}-12-31", freq="W-SUN")
    parts = []
    for city in CITIES:
        part = data.loc[data.city.eq(city) & data.year.between(start, end)].set_index("sunday_date").reindex(dates)
        part.index.name = "sunday_date"
        part.loc[part.np_pages.lt(min_pages), "np_diph_rate"] = np.nan
        if smooth:
            for col in ["diph_rate_per100k", "np_diph_rate"]:
                part[col] = part[col].rolling(4, min_periods=4).mean()
        part["city"] = city
        parts.append(part.reset_index())
    return pd.concat(parts, ignore_index=True)


def aggregate_common(prepared, fields):
    valid = prepared.dropna(subset=fields)
    count = valid.groupby("sunday_date").city.nunique()
    dates = count.index[count.eq(len(CITIES))]
    selected = prepared[prepared.sunday_date.isin(dates)]
    if len(dates) < 12:
        raise ValueError(f"共同有效周不足：{len(dates)}")
    means = selected.groupby("city")[fields].mean().reindex(CITIES)
    return means, selected, len(dates)


def cluster(frame, k):
    zs = zscore(frame)
    tree = linkage(zs.to_numpy(), method="ward", metric="euclidean")
    labels = cut_tree(tree, n_clusters=k).ravel() + 1
    return zs, tree, labels, silhouette_score(zs, labels)


def corr_row(window, metric, x, y):
    pear = pearsonr(x, y)
    spear = spearmanr(x, y)
    return dict(window=window, metric=metric, n_cities=len(x), pearson_r=pear.statistic,
                pearson_p=pear.pvalue, spearman_r=spear.statistic, spearman_p=spear.pvalue)


def table(df):
    return df.to_html(index=False, border=0, float_format=lambda v: f"{v:.4f}", escape=True)


def main():
    OUT.mkdir(exist_ok=True)
    fonts = {f.name for f in font_manager.fontManager.ttflist}
    plt.rcParams.update({"font.family": next((f for f in ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC"] if f in fonts), "DejaVu Sans"),
                         "axes.unicode_minus": False, "font.size": 11, "axes.spines.top": False,
                         "axes.spines.right": False, "savefig.dpi": 180})
    data = pd.read_csv(SOURCE, encoding="utf-8-sig", parse_dates=["sunday_date"])
    if data.duplicated(["city", "sunday_date"]).any():
        raise ValueError("主表有重复城市周")
    coverage = []
    for start, end in [(1915, 1922), (1920, 1922), (1930, 1932)]:
        subset = data[data.year.between(start, end)]
        for city, part in subset.groupby("city"):
            for col in ["flu_rate_per100k", "diph_rate_per100k", "polio_rate_per100k", "np_diph_rate", "tavg_avg", "prcp_sum", "snow_sum"]:
                coverage.append(dict(window=f"{start}-{end}", city=city, field=col, expected_weeks=len(part),
                                     valid_weeks=int(part[col].notna().sum()), coverage=part[col].notna().mean()))
    save_csv(pd.DataFrame(coverage), "coverage.csv")
    results = {}
    correlations = []
    for start, end in [(1915, 1922), (1930, 1932)]:
        window = f"{start}-{end}"
        prepared = prepare_window(data, start, end)
        means, selected, n = aggregate_common(prepared, ["population", "diph_rate_per100k", "np_diph_rate"])
        save_csv(means.reset_index().assign(n_common_weeks=n), f"q4_summary_{window}.csv")
        save_csv(selected[["city", "sunday_date", "population", "diph_rate_per100k", "np_diph_rate"]], f"q4_common_weeks_{window}.csv")
        results[window] = (means, n)
        for metric in ["diph_rate_per100k", "np_diph_rate"]:
            correlations.append(corr_row(window, metric, means.population, means[metric]))
    correlations = pd.DataFrame(correlations)
    save_csv(correlations, "q4_correlations.csv")
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    colors = ["#B84C3A", "#52647D", "#C8861A", "#3E6B4F", "#1A2B4A", "#7866A2"]
    for row, (window, (means, n)) in enumerate(results.items()):
        zs = zscore(means)
        for col, metric in enumerate(["diph_rate_per100k", "np_diph_rate"]):
            ax = axes[row, col]
            for city, color in zip(CITIES, colors):
                ax.scatter(zs.loc[city, "population"], zs.loc[city, metric], s=80, color=color, edgecolor="white", linewidth=.6)
                # Explicit offsets keep nearby city labels legible.
                offsets = {"BALTIMORE": (7, 12), "CLEVELAND": (7, -17), "LOS ANGELES": (7, 5), "MILWAUKEE": (7, -14), "NEW YORK": (-35, 9), "WASHINGTON": (7, 9)}
                if row == 0 and col == 0:
                    offsets.update({"BALTIMORE": (5, -30), "CLEVELAND": (15, 12), "WASHINGTON": (-58, 0)})
                if row == 0 and col == 1:
                    offsets.update({"LOS ANGELES": (-40, -28), "BALTIMORE": (15, -5), "CLEVELAND": (15, 14)})
                if row == 1 and col == 1:
                    offsets.update({"BALTIMORE": (-65, -8), "CLEVELAND": (10, -25)})
                ax.annotate(NAMES[city], (zs.loc[city, "population"], zs.loc[city, metric]), xytext=offsets[city], textcoords="offset points", fontsize=9,
                            arrowprops={"arrowstyle": "-", "color": "#999999", "lw": .5})
            cr = correlations[(correlations.window == window) & (correlations.metric == metric)].iloc[0]
            ax.set_title(f"{window} · 共同有效周 {n}\nPearson r={cr.pearson_r:.2f}, p={cr.pearson_p:.3f}; Spearman ρ={cr.spearman_r:.2f}", fontsize=10)
            ax.set_xlabel("人口规模（六城间 z-score）")
            ax.set_ylabel(("白喉每十万人发病率" if col == 0 else "白喉报刊命中率") + "（z-score）")
            ax.axhline(0, color="#CBD1DA", lw=.8)
            ax.axvline(0, color="#CBD1DA", lw=.8)
            ax.grid(alpha=.15)
            ax.margins(x=.22, y=.25)
    fig.suptitle("Q4：人口较多的城市，白喉发病率和报刊关注是否也更高？", fontsize=18, y=.98)
    fig.text(.06, .025, "来源：交接包融合主表；人口来源 Census Bureau，疫情 Tycho，报刊强词页级命中。\n4 周后向均值，完整 4 周才有效；同一面板六城使用相同周。每时段 n=6 城，结果仅描述关联。", fontsize=10, color="#52647D")
    fig.tight_layout(rect=[0, .08, 1, .94])
    for ext in ["png", "svg"]:
        fig.savefig(OUT / f"Q4_城市对比.{ext}")
    plt.close(fig)

    prepared = prepare_window(data, 1930, 1932)
    means, selected, n = aggregate_common(prepared, FEATURES)
    save_csv(means.reset_index(), "q5_features_raw.csv")
    save_csv(selected[["city", "sunday_date"] + FEATURES], "q5_common_weeks.csv")
    choices = []
    for k in [2, 3]:
        zs, tree, labels, score = cluster(means, k)
        choices.append(dict(k=k, silhouette=score, group_sizes="/".join(str(int((labels == v).sum())) for v in sorted(set(labels)))))
    scores = pd.DataFrame(choices)
    k = int(scores.sort_values(["silhouette", "k"], ascending=[False, True]).iloc[0].k)
    zs, tree, labels, score = cluster(means, k)
    save_csv(scores, "q5_k_scores.csv")
    save_csv(zs.reset_index(), "q5_features_zscore.csv")
    membership = pd.DataFrame({"city": CITIES, "城市": [NAMES[c] for c in CITIES], "cluster": labels})
    save_csv(membership, "q5_clusters.csv")
    sensitivity = []
    variants = {"不做4周平滑": (prepare_window(data, 1930, 1932, smooth=False), FEATURES),
                "每周至少10页": (prepare_window(data, 1930, 1932, min_pages=10), FEATURES),
                "排除人口": (prepared, [f for f in FEATURES if f != "population"]),
                "排除气象": (prepared, ["diph_rate_per100k", "np_diph_rate", "population"])}
    for feature in FEATURES:
        variants[f"去掉_{feature}"] = (prepared, [f for f in FEATURES if f != feature])
    for name, (variant, fields) in variants.items():
        try:
            if variant is prepared:
                vm, vn = means[fields], n
            else:
                vm, _, vn = aggregate_common(variant, fields)
        except ValueError as exc:
            sensitivity.append(dict(variant=name, n_common_weeks=0, k=k, silhouette=np.nan, ari_vs_main=np.nan, labels="", status=str(exc)))
            continue
        _, _, vl, vs = cluster(vm, k)
        sensitivity.append(dict(variant=name, n_common_weeks=vn, k=k, silhouette=vs, ari_vs_main=adjusted_rand_score(labels, vl), labels="/".join(map(str, vl)), status="已执行"))
    sens = pd.DataFrame(sensitivity)
    save_csv(sens, "q5_sensitivity.csv")
    # Leave-one-city-out Q4 checks expose the influence of the largest city.
    loo = []
    primary = results["1930-1932"][0]
    for city in CITIES:
        rem = primary.drop(city)
        for metric in ["diph_rate_per100k", "np_diph_rate"]:
            loo.append(dict(excluded_city=city, **corr_row("1930-1932", metric, rem.population, rem[metric])))
    save_csv(pd.DataFrame(loo), "q4_leave_one_city_out.csv")
    fig = plt.figure(figsize=(14, 8))
    grid = fig.add_gridspec(1, 2, width_ratios=[1, 2.6], wspace=.05)
    ax_tree = fig.add_subplot(grid[0])
    den = dendrogram(tree, orientation="left", labels=CITIES, ax=ax_tree, color_threshold=0, above_threshold_color="#52647D")
    ax_tree.set_yticklabels([])
    ax_tree.set_xlabel("Ward 合并距离")
    ax_tree.set_title("相似城市逐步合并", fontsize=12)
    order = den["leaves"]
    ax = fig.add_subplot(grid[1])
    vmax = max(2, abs(zs.to_numpy()).max())
    im = ax.imshow(zs.iloc[order], cmap="RdBu_r", vmin=-vmax, vmax=vmax, origin="lower", aspect="auto")
    ax.set_yticks(range(6), [f"{NAMES[CITIES[i]]}  /  组{labels[i]}" for i in order])
    ax.yaxis.tick_right()
    ax.set_xticks(range(6), LABELS, rotation=25, ha="right")
    for r, i in enumerate(order):
        for c in range(6):
            val = zs.iloc[i, c]
            ax.text(c, r, f"{val:+.2f}", ha="center", va="center", color="white" if abs(val) > 1.3 else "#252525")
    ax.set_title(f"1930–1932 · 白喉 · {n} 个共同有效周 · K={k}", fontsize=12)
    fig.colorbar(im, ax=ax, fraction=.035, pad=.24, label="六城间 z-score")
    fig.suptitle("Q5：哪些城市的疫情、气候与媒体综合特征相似？", fontsize=18, y=.97)
    fig.text(.06, .03, "来源：交接包融合主表（Tycho、NOAA、报刊、Census Bureau）；每列等权，Ward 层次聚类。\n气温单位℉，降水/降雪单位英寸；先各站周内有效观测日求日均，再对站点平均，非周累计。\n各列标准化后聚类；分组为探索性综合画像，不代表因果、时滞或稳定城市类型。", fontsize=10, color="#52647D")
    fig.subplots_adjust(top=.85, bottom=.22, left=.06, right=.86)
    for ext in ["png", "svg"]:
        fig.savefig(OUT / f"Q5_城市聚类.{ext}", bbox_inches="tight")
    plt.close(fig)

    groups = []
    for label in sorted(set(labels)):
        members = membership[membership.cluster.eq(label)]
        centroid = zs.loc[members.city].mean().sort_values()
        groups.append(f"组 {label}：{'、'.join(members['城市'])}。相对偏高：{LABELS[FEATURES.index(centroid.index[-1])]}（平均 z={centroid.iloc[-1]:.2f}）；相对偏低：{LABELS[FEATURES.index(centroid.index[0])]}（平均 z={centroid.iloc[0]:.2f}）。")
    q4_text = []
    for metric, title in [("diph_rate_per100k", "人口与白喉发病率"), ("np_diph_rate", "人口与白喉报刊命中率")]:
        cr = correlations[(correlations.window == "1930-1932") & (correlations.metric == metric)].iloc[0]
        q4_text.append(f"{title}：Pearson r={cr.pearson_r:.3f}，p={cr.pearson_p:.3f}；Spearman ρ={cr.spearman_r:.3f}，p={cr.spearman_p:.3f}。" + ("两种相关方向不同，不能概括为一致关联。" if np.sign(cr.pearson_r) != np.sign(cr.spearman_r) else "方向一致，但仍需结合六城样本量和逐城剔除结果解读。") + ("两种检验均未达到p<0.05，本样本未提供人口规模与该指标显著关联的证据；这不等于证明人口没有影响。" if cr.pearson_p >= .05 and cr.spearman_p >= .05 else ""))
    min_ari = sens.ari_vs_main.min()
    report = f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>组员D分析报告</title>
<style>body{{font:16px/1.8 'Microsoft YaHei',sans-serif;color:#252525;background:#f4f5f7;margin:0}}main{{max-width:1120px;margin:30px auto;background:white;padding:40px}}h1,h2{{color:#1A2B4A}}img{{width:100%;height:auto}}table{{border-collapse:collapse;width:100%;font-size:13px;display:block;overflow:auto}}th,td{{padding:8px;border-bottom:1px solid #ddd;text-align:left}}th{{background:#eef1f6}}.note{{border-left:4px solid #C8861A;padding:12px;background:#fff8ea}}a{{color:#24518a}}@media print{{main{{margin:0;padding:0}}h2{{break-after:avoid}}img{{break-inside:avoid}}}}</style><main>
<h1>组员 D：城市差异与城市综合特征聚类</h1><p>初版日期：2026-10-28；气象口径更新：2026-10-29。研究对象为六城；主分析为1930–1932年白喉。完整代码、输入快照与数值结果随包交付。</p>
<p class="note">选择白喉是因为覆盖率更高，而非根据相关结果挑选病种。主分析不代表全部疾病。气象口径已据2026-10-29用户转述的答复补充：气温为℉，降水、降雪为英寸；prcp_sum和snow_sum为各站周内有效观测日的日均值再对站点取平均，不是周累计量。Q5仍为六城小样本的探索性分析。</p>
<h2>Q4：人口规模能否解释城市差异？</h2><p>将各城市白喉每十万人发病率、报刊命中率做4周后向均值，保留完整4周；再筛选六城共同有效周，按城市等周权求均值。人口取同一批周的均值。主时段有 {results['1930-1932'][1]} 个共同周，1915–1922对照时段有 {results['1915-1922'][1]} 个共同周。z-score在每个时段的六城汇总值之间、逐列计算（总体标准差ddof=0），不在每个城市内部先标准化。</p>
<img src="Q4_城市对比.png" alt="Q4城市对比"><p>{'</p><p>'.join(q4_text)}</p>
<p>上述检验每次仅6个城市，p值为未经多重比较校正的探索性数值。不能把一座城市的每周观测当作数百个独立城市样本。没有年龄、收入或职业结构，无法检验社会结构机制；人口同时用于发病率分母，关联解释还需考虑这一数学关系。</p>
<p>两时段结果可能不同，应分别陈述。报刊命中率均值表示“典型有效周”的关注比例，不等于全部命中页之和除以全部扫描页之和。</p>
{table(correlations)}<h3>主时段原始单位汇总（发病率：每十万人；命中率：%；人口：人）</h3>{table(primary.reset_index())}
<h2>Q5：哪些城市的综合特征相似？</h2><p>使用同一时段 {n} 个六城共同有效周。六项特征分别是白喉发病率、白喉报刊命中率、气温（℉）、周内日均降水（英寸）、周内日均降雪（英寸）和人口在共同周上的时段均值；前两项先平滑。降水、降雪先在每个站点内按该周有效观测日求日均，再对站点取平均，因此不能将这两个_sum字段解释为周累计；若各站有效天数不同，也不等同于合并所有站点日记录统一求均值。逐列z-score后使用欧氏距离和Ward层次聚类。六项特征等权，因此气象占3/6维，领域权重并不相等。</p>
<img src="Q5_城市聚类.png" alt="Q5聚类热力图"><p>仅比较 K=2 和 K=3，选择轮廓系数较高者（并列优先较小K）。本次 K={k}，轮廓系数={score:.3f}。小样本下这个选择不证明真实类别数；单城一组要视作异常画像而非稳定类型。</p>{table(scores)}
<p>{'</p><p>'.join(groups)}</p><p>这里只比较平均水平，没有把时滞、事件响应或季节曲线纳入特征，故不将结果解释为严格的“响应机制类型”。</p>
<h3>稳健性对照</h3><p>保持主分析K不变，改变平滑、每周最低扫描页数（1→10）、删除人口、删除气象、逐项删除特征。ARI=1表示分组相同，越小表示越不一致。最低ARI={min_ari:.3f}。每周10页是分析者提出的对照阈值，不是小组已拍板规则。</p>{table(sens)}
<h2>口径、来源与局限</h2><ul><li>所有缺失保留NA，不补0。病例真实0值保留。报刊无覆盖时命中率为NA。</li><li>严格按每年周日序列重建周历；两研究窗口分别处理，不跨1922–1930断档滚动。</li><li>共同周筛选改善可比性，但仍可能偏向记录更完整的季节，不能推断为完整年度负担；详见 common_week_seasons.csv。</li><li>所有流感扩展分析应排除1915–1919；本报告不做流感定量推断。</li><li>人口来自普查年线性插值，边界未统一；NHGIS提供1930点位，不提供本包所用人口数字。</li><li>气象单位与周表口径已据用户转述的答复确认，记录见inputs/气象口径确认.md。原字段名保持兼容，prcp_sum与snow_sum的sum不表示周累计；本次未将其乘7或改造成累计量。气温保留℉、降水降雪保留英寸，标准化输入数值不变。</li><li>本分析不重新清洗NOAA、不验证站点归属；PDF原表的负责人手工复核状态也不被改写为完成。</li></ul>
<h2>交付索引</h2><p><a href="NHGIS_人口与点位源卡.md">人口与点位源卡</a> · <a href="分析口径与待核对事项.md">分析口径与待核对事项</a> · <a href="validation.json">自动核验结果</a> · <a href="q4_correlations.csv">Q4相关表</a> · <a href="q5_sensitivity.csv">Q5对照表</a></p></main></html>"""
    (OUT / "组员D_分析报告.html").write_text(report, encoding="utf-8")
    seasons = []
    for name, (_, selected_frame, _) in [("q5", (means, selected, n))]:
        counts = selected_frame.drop_duplicates("sunday_date").sunday_date.dt.month.value_counts().sort_index()
        for month in range(1, 13):
            total = pd.date_range("1930-01-01", "1932-12-31", freq="W-SUN").month
            seasons.append(dict(analysis=name, month=month, selected_weeks=int(counts.get(month, 0)), possible_weeks=int((total == month).sum())))
    save_csv(pd.DataFrame(seasons), "common_week_seasons.csv")
    versions = {p: importlib.metadata.version(p) for p in ["numpy", "pandas", "scipy", "matplotlib", "scikit-learn", "nbformat", "nbclient", "ipykernel"]}
    manifest = {"date": "2026-10-29", "weather_metadata_source": "inputs/气象口径确认.md", "weather_units": {"tavg_avg": "℉", "prcp_sum": "英寸", "snow_sum": "英寸"}, "precipitation_aggregation": "各站周内有效观测日日均，再对站点取平均；非周累计", "python": platform.python_version(), "packages": versions,
                "inputs_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT / "inputs").iterdir()) if p.is_file()},
                "q4_common_weeks": {w: n for w, (_, n) in results.items()}, "q5_common_weeks": n, "selected_k": k,
                "features": FEATURES, "analysis_window": [1930, 1932], "disease": "diph", "standardization_ddof": 0}
    (OUT / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "requirements.txt").write_text("\n".join(f"{p}=={v}" for p, v in versions.items()) + "\n", encoding="utf-8")
    (OUT / "Q4_Q5_结果摘要.md").write_text("# Q4 结果\n\n" + "\n\n".join(q4_text) + "\n\n# Q5 结果\n\n" + "\n\n".join(groups) + f"\n\nK={k}，轮廓系数={score:.3f}；对照最低ARI={min_ari:.3f}。六城小样本、白喉单病种、共同有效周条件下的探索性发现；气象单位与周内日均口径已于2026-10-29据用户转述答复确认，标准化输入数值不变。详见HTML报告。\n", encoding="utf-8")
    print(json.dumps({"q4_common_weeks": manifest["q4_common_weeks"], "q5_common_weeks": n, "k": k, "silhouette": score, "min_ari": min_ari}, ensure_ascii=False))


if __name__ == "__main__":
    main()
