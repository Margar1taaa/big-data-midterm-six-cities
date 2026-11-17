"""Q3: deterministic descriptive climate/disease analysis and NOAA source audit.

python scripts/run_q3.py  (CSV input/output encoding: utf-8-sig)
"""
from pathlib import Path
import os
import sys
ROOT = Path(__file__).resolve().parents[1]
if (ROOT / ".runtime").exists():
    sys.path.append(str(ROOT / ".runtime"))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplconfig"))
import argparse
import hashlib
import html
import json
import platform
import numpy as np
import pandas as pd
import scipy
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from build_integrated import read, build, compare, NAME, WX

OUT = ROOT / "analysis/q3"
CARD = ROOT / "analysis/noaa_source_card"
FEATURES = WX[:5]
DISEASES = {"flu": "流感", "polio": "脊髓灰质炎", "diph": "白喉"}
LABELS = {"tavg_avg": "平均温度", "tmax_avg": "最高温度", "tmin_avg": "最低温度", "prcp_sum": "降水", "snow_sum": "降雪"}
SEED = 20261031
DATE = "2026-10-31"


def write_csv(f, p):
    f.to_csv(p, index=False, encoding="utf-8-sig", float_format="%.10g", lineterminator="\n")


def zscore(s):
    sd = s.std(ddof=0)
    return (s-s.mean())/sd if pd.notna(sd) and sd > 1e-12 else s*float("nan")


def prepare(master, disease, variant="main"):
    f = master.copy()
    if disease == "flu":
        f = f[f.sunday_date.ge("1920-01-01")].copy()
    if variant == "exclude_boundary":
        f = f[f.sunday_date.lt("1933-01-01")].copy()
    if variant in ("weather_prev_week", "weather_next_week"):
        offset = 7 if variant == "weather_prev_week" else -7
        w = master[["city", "sunday_date", *WX]].copy()
        w["sunday_date"] += pd.Timedelta(days=offset)
        f = f.drop(columns=WX).merge(w, on=["city", "sunday_date"], how="left", validate="one_to_one")
    parts = []
    for city, g in f.groupby("city", sort=True):
        # A complete calendar is essential: never bridge missing weeks or 1923-1929.
        g = g.set_index("sunday_date").sort_index()
        idx = pd.date_range(g.index.min(), g.index.max(), freq="W-SUN")
        g = g.reindex(idx).rename_axis("sunday_date")
        g["city"] = city
        g["in_window"] = g.year.notna()
        g["period"] = np.where(g.index.year <= 1922, "early", "late")
        raw = g[disease+"_cases"].copy()
        if variant == "per100k":
            raw = raw/g.population*100000  # full precision, unlike rounded delivered per100k
        g["cases_raw"] = raw
        g["cases_4w"] = raw.rolling(1 if variant == "unsmoothed" else 4,
                                    min_periods=1 if variant == "unsmoothed" else 4).mean()
        if variant == "log1p":
            g["cases_4w"] = np.log1p(g.cases_4w)
        g["y"] = zscore(g.cases_4w)
        threshold = g.loc[g.in_window, "n_stations"].quantile(.25)
        quality = g.n_days.ge(6.5) & g.n_stations.ge(threshold)
        if variant == "strict_quality":
            quality = g.n_days.ge(7) & g.n_stations.ge(g.loc[g.in_window, "n_stations"].median())
        g["quality_keep"] = quality
        for c in FEATURES:
            if variant in ("quality", "strict_quality"):
                g.loc[~quality, c] = np.nan
            g[c+"_z"] = zscore(g[c])
        parts.append(g[g.in_window].reset_index())
    return pd.concat(parts, ignore_index=True)


def residual_pair(f, c):
    """Remove additive month and year fixed effects within each city, on pairwise data."""
    f = f.copy()
    f["x"] = f[c+"_z"]
    # Only paired observations have residuals. Keep all other positions NA so
    # permutations cannot move unadjusted y into the adjusted null distribution.
    incomplete=f[["x","y"]].isna().any(axis=1)
    f.loc[incomplete,["x","y"]]=np.nan
    for _, g in f.groupby("city", sort=True):
        valid = g[["x", "y"]].notna().all(axis=1)
        v = g.loc[valid]
        if len(v) < 30:
            f.loc[g.index, ["x", "y"]] = np.nan
            continue
        design = pd.get_dummies(pd.DataFrame({"month": v.sunday_date.dt.month.astype(str),
                                              "year": v.sunday_date.dt.year.astype(str)}), drop_first=True, dtype=float)
        a = np.column_stack([np.ones(len(v)), design.to_numpy()])
        for col in ["x", "y"]:
            data = v[col].to_numpy(dtype=float)
            resid = data-a@np.linalg.lstsq(a, data, rcond=None)[0]
            f.loc[v.index, col] = zscore(pd.Series(resid)).to_numpy()
    return f


def corr(x, y):
    valid = np.isfinite(x)&np.isfinite(y)
    a,b = np.asarray(x)[valid], np.asarray(y)[valid]
    n = len(a)
    if n < 10 or np.std(a) < 1e-12 or np.std(b) < 1e-12:
        return {"n": n, "pearson_r": np.nan, "pearson_p_iid": np.nan,
                "spearman_rho": np.nan, "spearman_p_iid": np.nan, "agreement": "不足/常数"}
    r,p = stats.pearsonr(a,b)
    rho,sp = stats.spearmanr(a,b)
    agree = "一致" if r*rho > 0 and abs(r-rho) <= .15 else "差异需注明"
    return {"n": n, "pearson_r": r, "pearson_p_iid": p,
            "spearman_rho": rho, "spearman_p_iid": sp, "agreement": agree}


def block_permutation(f, b, block, seed):
    """Permute complete 8-calendar-week blocks of y, separately by city and window.

    NA positions travel with the blocks; x stays fixed. This is an exploratory
    dependent-data null, not a causal test. The final short block is retained.
    """
    rng = np.random.default_rng(seed)
    x = f.x.to_numpy(dtype=float)
    original = f.y.to_numpy(dtype=float)
    observed = corr(x, original)["pearson_r"]
    if not np.isfinite(observed):
        return np.nan
    ys = np.full((b, len(f)), np.nan)
    for _, g in f.groupby(["city", "period"], sort=True):
        idx = g.index.to_numpy()
        values = original[idx]
        blocks = [np.arange(i,min(i+block,len(idx))) for i in range(0,len(idx),block)]
        for j in range(b):
            order = np.concatenate([blocks[k] for k in rng.permutation(len(blocks))])
            ys[j,idx] = values[order]
    mask = np.isfinite(ys)&np.isfinite(x)[None,:]
    count = mask.sum(axis=1)
    a = np.where(mask, x, 0.)
    yy = np.where(mask, ys, 0.)
    sx, sy = a.sum(axis=1), yy.sum(axis=1)
    cov = (a*yy).sum(axis=1)-sx*sy/count
    den = np.sqrt(np.maximum((a*a).sum(axis=1)-sx*sx/count,0)*
                  np.maximum((yy*yy).sum(axis=1)-sy*sy/count,0))
    null = np.divide(cov, den, out=np.full(b,np.nan), where=den>1e-12)
    null = null[np.isfinite(null)]
    return (1+np.count_nonzero(np.abs(null)>=abs(observed)))/(1+len(null))


def bh(values):
    p=np.asarray(values,dtype=float)
    out=np.full(len(p),np.nan)
    idx=np.flatnonzero(np.isfinite(p))
    order=idx[np.argsort(p[idx],kind="stable")]
    if len(order):
        out[order]=np.minimum.accumulate((p[order]*len(order)/np.arange(1,len(order)+1))[::-1])[::-1].clip(0,1)
    return out


def analyze(master, b):
    main, cityrows, sensitivities, transforms = [], [], [], []
    for di,disease in enumerate(DISEASES):
        f=prepare(master,disease)
        transforms.append(f.assign(disease=disease))
        for ci,c in enumerate(FEATURES):
            pair=f.assign(x=f[c+"_z"])
            for analysis,pairdata in [("main",pair),("season_year_adjusted",residual_pair(f,c))]:
                row={"analysis":analysis,"disease":disease,"climate":c,**corr(pairdata.x.to_numpy(),pairdata.y.to_numpy())}
                row["n_cities"]=int(pairdata.loc[pairdata[["x","y"]].notna().all(axis=1),"city"].nunique())
                row["p_block"]=block_permutation(pairdata,b,8,SEED+100*di+ci)
                main.append(row)
            for city,g in pair.groupby("city"):
                cityrows.append({"disease":disease,"climate":c,"city":city,**corr(g.x.to_numpy(),g.y.to_numpy())})
        for variant in ["unsmoothed","quality","strict_quality","per100k","log1p",
                        "weather_prev_week","weather_next_week","exclude_boundary"]:
            v=prepare(master,disease,variant)
            for c in FEATURES:
                sensitivities.append({"variant":variant,"disease":disease,"climate":c,
                                      **corr(v[c+"_z"].to_numpy(),v.y.to_numpy())})
    results=pd.DataFrame(main)
    for _,g in results.groupby("analysis"):
        results.loc[g.index,"q_block_bh"]=bh(g.p_block)
    cities=pd.DataFrame(cityrows)
    sens=pd.DataFrame(sensitivities)
    transformed=pd.concat(transforms,ignore_index=True)
    write_csv(results,OUT/"correlations.csv")
    write_csv(cities,OUT/"city_correlations.csv")
    write_csv(sens,OUT/"sensitivity.csv")
    write_csv(transformed[["city","sunday_date","period","disease","cases_raw","cases_4w","y",
                           *FEATURES,*[c+"_z" for c in FEATURES],"n_days","n_stations","quality_keep"]], OUT/"analysis_input.csv")
    return results,cities,sens,transformed


def source_audit(master):
    weekly=read(ROOT/"data/cleaned/noaa/noaa_weekly_sixcities.csv")
    mapping=read(ROOT/"data/cleaned/noaa/noaa_station_mapping_summary.csv")
    expanded=[]
    for r in mapping.fillna("").to_dict("records"):
        ids=r["actual_station"].split(";")
        names=r["station_name"].split(";")
        for i,station in enumerate(ids):
            expanded.append({**r,"actual_station":station,"station_name":names[i] if i<len(names) else "",
                             "mapping_kind":"merged_source" if len(ids)>1 else "single_source",
                             "filename_matches_station":r["source_file"].split(".")[0].replace(" (2)","")==station})
    expanded=pd.DataFrame(expanded)
    write_csv(expanded,CARD/"station_city_mapping.csv")
    rows=[]
    for city,g in master.groupby("city"):
        s=weekly[weekly.city.eq(city)]
        m=mapping[mapping.city.eq(city)]
        e=expanded[expanded.city.eq(city)]
        rows.append({"city":city,"master_weeks":len(g),"cleaned_weeks":len(s),
                     "cleaned_start":s.sunday_date.min(),"cleaned_end":s.sunday_date.max(),
                     "mapping_files":len(m),"mapping_unique_station_ids":e.actual_station.nunique(),
                     "n_days_min":g.n_days.min(),"n_days_max":g.n_days.max(),
                     "n_stations_min":g.n_stations.min(),"n_stations_max":g.n_stations.max(),
                     **{c+"_non_na":int(g[c].notna().sum()) for c in FEATURES},
                     **{c+"_missing":int(g[c].isna().sum()) for c in FEATURES}})
    coverage=pd.DataFrame(rows)
    write_csv(coverage,CARD/"coverage_by_city.csv")
    ty=read(ROOT/"data/cleaned/tycho/cleaned_tycho_weekly_sixcities.csv")
    starts=pd.to_datetime(ty.from_date)
    shifted=starts+pd.to_timedelta((6-starts.dt.dayofweek)%7,unit="D")
    auditrows=ty[(starts.dt.dayofweek.ne(6)) & shifted.isin(master.sunday_date.unique())].copy()
    auditrows["integrated_sunday"]=shifted.loc[auditrows.index].dt.strftime("%Y-%m-%d")
    write_csv(auditrows,OUT/"tycho_non_sunday_audit.csv")
    hits=pd.concat([read(ROOT/"data/cleaned/newspaper/newspaper_hits_weekly.csv"),
                    read(ROOT/"data/cleaned/newspaper/newspaper_hits_weekly_zip.csv")],ignore_index=True)
    hits["city"]=hits.city.str.upper()
    hits["sunday_date"]=pd.to_datetime(hits.sunday_date)
    sum_pages=(hits.drop_duplicates(["city","paper","sunday_date"])
               .groupby(["city","sunday_date"]).n_pages.sum().rename("sum_pages").reset_index())
    pagecheck=master.merge(sum_pages,on=["city","sunday_date"],how="left")
    discrepancy=pagecheck[pagecheck.np_pages.ne(pagecheck.sum_pages.fillna(0))]
    write_csv(discrepancy[["city","sunday_date","np_pages","sum_pages"]],OUT/"inherited_newspaper_denominator_audit.csv")
    return coverage,mapping,expanded


def figures(results,cities,transformed):
    plt.rcParams.update({"font.sans-serif":["Microsoft YaHei","SimHei","DejaVu Sans"],
                         "axes.unicode_minus":False,"font.size":11,"savefig.facecolor":"white",
                         "svg.hashsalt":"q3-20261031"})
    cmap=LinearSegmentedColormap.from_list("research",["#52647D","#FFFFFF","#C8861A"])
    fig,axes=plt.subplots(1,2,figsize=(14,4.7),gridspec_kw={"wspace":.24})
    for ax,kind,title in zip(axes,["main","season_year_adjusted"],["A  按城市 z-score 的周值关联","B  控制各城月份与年份后的关联"]):
        rows=results[results.analysis.eq(kind)]
        data=rows.pivot(index="disease",columns="climate",values="pearson_r").reindex(index=DISEASES,columns=FEATURES)
        im=ax.imshow(data,vmin=-.5,vmax=.5,cmap=cmap,aspect="auto")
        ax.set_xticks(range(5),[LABELS[c] for c in FEATURES]);ax.set_yticks(range(3),DISEASES.values())
        ax.set_title(title,loc="left",fontsize=12,pad=12,color="#1A2B4A")
        for i,d in enumerate(DISEASES):
            for j,c in enumerate(FEATURES):
                r=rows[rows.disease.eq(d)&rows.climate.eq(c)].iloc[0]
                mark="*" if r.q_block_bh<.05 else ""
                if r.agreement=="差异需注明":mark+="†"
                ax.text(j,i,f"r={r.pearson_r:+.2f}{mark}\nρ={r.spearman_rho:+.2f}\nn={r.n:,}",ha="center",va="center",fontsize=9.2)
        ax.set_xticks(np.arange(-.5,5,1),minor=True);ax.set_yticks(np.arange(-.5,3,1),minor=True)
        ax.grid(which="minor",color="#D8D8D8");ax.tick_params(which="minor",bottom=False,left=False)
        for sp in ax.spines.values():sp.set_visible(False)
    fig.suptitle("温度、降水和降雪异常与疫情强度有关吗？",x=.04,y=.99,ha="left",fontsize=17,fontweight="bold",color="#1A2B4A")
    fig.text(.04,.055,"范围：六城 1915–1922、1930–1932，含 1933-01-01 边界周；流感排除 1915–1919。单位：r / ρ（无量纲）。",fontsize=9,color="#52647D")
    fig.text(.04,.015,"来源：交接包 NOAA + Tycho；病例先做完整 4 周均值。*：8 周分块置换经 15 项 BH 校正后 q<0.05。†：r 与 ρ 方向或量级不一致。",fontsize=9,color="#52647D")
    fig.subplots_adjust(top=.78,bottom=.22,left=.1,right=.98)
    fig.savefig(OUT/"q3_core.png",dpi=190)
    fig.savefig(OUT/"q3_core.svg",metadata={"Date":None})
    plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(14,4.8),sharey=True)
    city_order=sorted(cities.city.unique())
    for ax,d in zip(axes,DISEASES):
        g=cities[cities.disease.eq(d)]
        for k,c in enumerate(["tavg_avg","prcp_sum","snow_sum"]):
            s=g[g.climate.eq(c)].set_index("city").reindex(city_order)
            ax.scatter(s.pearson_r,np.arange(6)+(k-1)*.18,label=LABELS[c],s=35,color=["#1A2B4A","#C8861A","#3E6B4F"][k])
        ax.axvline(0,color="#C9D0D9");ax.set_xlim(-.65,.65);ax.set_title(DISEASES[d]);ax.set_xlabel("Pearson r（无量纲）")
        ax.grid(axis="x",alpha=.2)
    axes[0].set_yticks(range(6),city_order);axes[-1].legend(loc="lower right",fontsize=9)
    fig.suptitle("六座城市的气候—疫情关联方向一致吗？",x=.03,ha="left",fontsize=16,color="#1A2B4A")
    fig.text(.03,.015,"范围与处理同核心图；来源：NOAA + Tycho。城市点仅作描述，不按普通周独立假设宣称显著；n 见 city_correlations.csv。",fontsize=9)
    fig.subplots_adjust(left=.13,right=.98,top=.81,bottom=.18,wspace=.14)
    fig.savefig(OUT/"q3_city_comparison.png",dpi=180);plt.close(fig)


def md_table(f):
    columns=list(f.columns)
    return "| "+" | ".join(columns)+" |\n|"+"|".join(["---"]*len(columns))+"|\n"+"\n".join("| "+" | ".join(str(v) for v in row)+" |" for row in f.itertuples(index=False,name=None))


def reports(results,cities,sens,transformed,coverage,b):
    compact=results.copy()
    compact["病种"]=compact.disease.map(DISEASES);compact["气象"]=compact.climate.map(LABELS)
    compact["处理"]=compact.analysis.map({"main":"主分析","season_year_adjusted":"月份+年份调整"})
    for c in ["pearson_r","spearman_rho","p_block","q_block_bh"]:
        compact[c]=compact[c].map(lambda x:f"{x:.3f}")
    table=md_table(compact[["处理","病种","气象","n","pearson_r","spearman_rho","p_block","q_block_bh","agreement"]])
    headlines=[]
    for d in DISEASES:
        a=results[results.analysis.eq("main")&results.disease.eq(d)&results.climate.eq("tavg_avg")].iloc[0]
        s=results[results.analysis.eq("season_year_adjusted")&results.disease.eq(d)&results.climate.eq("tavg_avg")].iloc[0]
        headlines.append(f"{DISEASES[d]}：平均温度主分析 r={a.pearson_r:+.3f}、ρ={a.spearman_rho:+.3f}（n={a.n}）；月份/年份调整后 r={s.pearson_r:+.3f}、q={s.q_block_bh:.4f}。")
    water="降水：三病种主分析及调整后均未见校正后显著关联。降雪：流感、白喉主分析为弱正相关，但控制月份/年份后证据减弱；脊灰的 Pearson 与 Spearman 量级不同，不作稳定结论。"
    main=results[results.analysis.eq("main")].set_index(["disease","climate"])
    compare=sens.merge(main[["pearson_r"]].rename(columns={"pearson_r":"main_r"}),left_on=["disease","climate"],right_index=True)
    compare["delta_r"]=compare.pearson_r-compare.main_r
    write_csv(compare,OUT/"sensitivity_comparison.csv")
    summary=compare.groupby("variant").agg(max_abs_delta_r=("delta_r",lambda x:x.abs().max()),min_n=("n","min"),max_n=("n","max")).reset_index()
    write_csv(summary,OUT/"sensitivity_summary.csv")
    counts=transformed.groupby("disease").agg(raw_non_na=("cases_raw","count"),smoothed_non_na=("cases_4w","count"))
    write_csv(counts.reset_index(),OUT/"smoothing_counts.csv")
    text=f"""# Q3 结果：气候异常与疫情强度

日期：{DATE}。输入：融合主表 3,450 行 × 29 列；原始读取 `utf-8-sig`。

## 可直接供整合的结论

"""+"\n\n".join(headlines)+"\n\n"+water+f"""

上述为历史报告病例的描述性关联。周值 z-score 保留了季节周期，不能直接称为“超出季节常态的异常效应”；控制月份与年份的结果用于判断这一区别。Pearson 与 Spearman 异号或相差 >0.15 的单元格标为“差异需注明”，不作稳定关联结论。统计显著与效应大小分别解释，不据此推断因果。

![分病种核心图](q3_core.png)

## 处理口径

1. 按 `city × sunday_date` 唯一键排序，研究主窗口沿用交接表；1933-01-01 是额外边界标签，保留并做剔除敏感性。1923–1929 为设计外时期，不补入分析。
2. 流感分析先整段排除 1915–1919，包括纽约 1919 年尾已有记录；其他病种保留全表。病例缺失一律 NA，不当零病例。
3. 每城重建完整周日历后，病例做向后看的 4 周均值（含当周，`min_periods=4`）。任何一周缺失则该滚动结果为 NA，不能跳过缺周或跨七年空档平滑。气象使用当周值，不另平滑。
4. 每个病种的可用研究窗口内，气象与平滑病例分别按城市 z-score，`ddof=0`。主结果合并标准化后的城市周，按每项指标成对剔除 NA；因此有效周更多的城市权重更大。z-score 是相对本研究窗口的标准化周值，不是 30 年气候常年距平。
5. 相关：Pearson 为主，Spearman 对照。普通独立样本 p 仅供对照（CSV 的 `*_p_iid`），不能忽略平滑和时序相关。主图标记使用城市×连续窗口内 8 周分块置换，B={b}，双侧 p=(1+更极端次数)/(B+1)，固定种子 {SEED}。NA 随病例块一起移动，短尾块保留。此置换依赖块交换近似，属于探索性推断。
6. 主分析与月份/年份调整各自对 3 病种×5 气象变量的 15 项 p 做 BH 校正。p<0.05 为名义阈值，图中 * 用 q<0.05；0.05≤q<0.10 仅记边缘证据，不称显著。
7. 调整版在每城有效配对样本内，分别用月份与年份虚拟变量残差化气象和病例，再分别标准化后相关。该调整只控制粗粒度季节和年度差异，不能排除所有混杂。

## 完整结果

{table}

## 敏感性

`sensitivity.csv` 与 `sensitivity_comparison.csv` 含不平滑、质量筛选、严格质量筛选、人均病例、log1p、前/后移气象一周、删除边界周 8 类 × 15 项结果；这里只比较 r、ρ、n，不为每项额外制造显著性结论。

- 质量筛选：气象当周 `n_days≥6.5` 且 `n_stations≥该城窗口内25%分位数`；严格筛选用 `n_days≥7` 且站数≥城市中位数。各城相对阈值避免直接排除历史站网较小的纽约/华盛顿。阈值是本次分析约定，不是 NOAA 官方质控标准。质量筛选作用于气象周，病例仍按原有效日历平滑。
- 人均敏感性从病例/插值人口×100,000 以完整精度计算，再平滑与标准化，避免主表四舍五入后的稀疏小值；人口并非逐周实测。
- `weather_prev_week`：把气象日期加 7 天后与病例周匹配；`weather_next_week` 相反。不跨研究窗口插入外部气象，也不能据此定义因果方向。
- 城市分层结果见 `city_correlations.csv` 与城市对比图，常数/有效配对不足时不计算相关。
- 对数敏感性使流感与平均温度 r 从-0.260变为-0.492，方向一致但量级不稳定，提示极端病例/偏态会影响线性相关强度；不能笼统写“所有口径均稳健”。站点质量筛选最大|Δr|约0.020，严格筛选约0.032，人口口径约0.009，删除边界周约0.0045。城市样本不均，例如密尔沃基流感只有36个平滑有效周，巴尔的摩脊灰温度r接近0；六城不能视作同质重复样本。

{md_table(summary.round(4))}

## 缺失、溯源与局限

{md_table(counts.reset_index())}

NOAA 温度三列覆盖全表；降水 1 个 NA；降雪 338 个 NA，洛杉矶 291、密尔沃基 47。本次补充原始宽表后已补齐六城映射、站点坐标和站距，详见NOAA源卡；原采集时清洗脚本和导出配置未留存，主项目后补脚本属于独立重建核验。字段单位、PRCP/SNOW 的跨站聚合顺序和原始质量标志处理不能由当前包完整验证，因此图用无量纲标准化值，不将现有数值换算成物理效应。站数敏感性不能代替站点级重建。

重建脚本从 cleaned 表逐格复现主表，检查 NA 掩码及全部 29 列；raw→cleaned为后补独立核验，不冒充原脚本字节复现。主表报刊分母采用项目冻结的同城周最大页数口径，不影响本题 NOAA×Tycho 的计算。

## 复现

```powershell
python -m pip install -r requirements.txt
python scripts/build_integrated.py --check
python scripts/run_q3.py
```

完整数据、脚本、依赖版本、输入 SHA256 与核验结果见 `run_manifest.json`、`verification.json`。结果与复现边界写入 `docs/GAPS.md` 的 {DATE} 条目，展示整理后相关 JSON 位于 `analysis/q3/补充材料/`。
"""
    (OUT/"Q3_report.md").write_text(text,encoding="utf-8")
    bullets="".join(f"<li>{html.escape(t)}</li>" for t in headlines)
    one=f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>Q3 一页结果</title><style>
    @page{{size:A4;margin:12mm}}*{{box-sizing:border-box}}body{{font-family:'Microsoft YaHei',sans-serif;color:#252525;max-width:1000px;margin:24px auto;line-height:1.6;font-size:14px}}h1{{font-size:25px;color:#1A2B4A;margin-bottom:4px}}.meta{{color:#52647D;font-size:12px}}img{{width:100%;display:block;margin:12px 0}}.box{{border-left:4px solid #C8861A;background:#f5f4f1;padding:10px 15px;margin:10px 0}}li{{margin:4px 0}}a{{color:#1A2B4A}}@media print{{body{{font-size:10.5px;max-width:none;margin:0}}h1{{font-size:21px}}img{{margin:8px 0}}.box{{padding:7px 10px}}}}
    </style><h1>温度、降水和降雪异常与疫情强度有关吗？</h1><div class="meta">任务 3 · {DATE} · 六城 1915–1922＋1930–1932（含 1933-01-01 边界周） · 来源：NOAA + Tycho</div>
    <img src="q3_core.png" alt="分病种气候疫情关联图"><div class="box"><b>可报告的温度结果</b><ul>{bullets}</ul></div>
    <p><b>方法：</b>病例先做完整 4 周滚动均值；气象周值与病例在各城内 z-score，成对排除 NA。流感整段排除 1915–1919。Pearson 为主、Spearman 为对照。* 表示 8 周分块置换（{b} 次）经 15 项 BH 校正后 q&lt;0.05。</p>
    <p><b>降水/降雪：</b>{water}</p>
    <p><b>解释边界：</b>主图 A 的周值关联仍含季节性；B 控制各城月份与年份。†表示r与ρ方向或量级不同。流感温度关联的量级对log1p敏感。结果仅为统计关联，不能据此推断因果。</p>
    <p><b>质量与交接：</b>降水缺 1 周，降雪缺 338 城市周，均未补零；提供站数/天数筛选、人口与 log1p、前后一周、边界周对照。六城映射与站距已由原始宽表补齐；单位有逐日样本证据，原始导出配置未记录。</p>
    <p class="meta"><a href="Q3_report.md">完整方法与结果</a> · <a href="correlations.csv">相关系数表</a> · <a href="sensitivity_comparison.csv">敏感性表</a> · <a href="../noaa_source_card/NOAA_source_card.md">NOAA 气象源卡</a></p></html>"""
    (OUT/"Q3_one_page.html").write_text(one,encoding="utf-8")
    return headlines


def verify(master,results,transformed):
    failures=[]
    def check(ok,detail):
        if not ok:failures.append(detail)
    check(master.shape==(3450,29),"master dimensions")
    check(not master.duplicated(["city","sunday_date"]).any(),"duplicate master keys")
    check(master.sunday_date.dt.dayofweek.eq(6).all(),"non-Sunday master label")
    check(not compare(read(ROOT/"data/integrated"/NAME),build()),"rebuilt master mismatch")
    check(not transformed[transformed.disease.eq("flu")].sunday_date.lt("1920-01-01").any(),"flu pre1920")
    check(len(results)==30,"result rows")
    check(results.pearson_r.abs().le(1).all(),"invalid correlation")
    check(results.q_block_bh.between(0,1).all(),"invalid q")
    w=read(ROOT/"data/cleaned/noaa/noaa_weekly_sixcities.csv")
    w["sunday_date"]=pd.to_datetime(w.sunday_date)
    check((pd.to_datetime(w.week_end)-w.sunday_date).dt.days.eq(6).all(),"NOAA week interval")
    joined=master[["city","sunday_date",*WX]].merge(w[["city","sunday_date",*WX]],on=["city","sunday_date"],suffixes=("_master","_source"),validate="one_to_one")
    check(len(joined)==len(master),"NOAA join coverage")
    for c in WX:
        check(np.allclose(joined[c+"_master"],joined[c+"_source"],equal_nan=True),"NOAA source differs: "+c)
    for _,g in transformed.groupby(["disease","city","period"]):
        check(g.head(3).cases_4w.isna().all(),"rolling crosses segment edge")
    # Directly validate every rolling result against its four calendar inputs.
    for _,g in transformed.groupby(["disease","city"]):
        s=g.set_index("sunday_date").cases_raw.asfreq("W-SUN")
        expected=s.rolling(4,min_periods=4).mean().reindex(g.sunday_date).to_numpy()
        check(np.allclose(expected,g.cases_4w,equal_nan=True),"rolling NA/calendar mismatch")
    report={"passed":not failures,"failures":failures,"checks":"dimensions; keys; Sunday labels; all-cell rebuild; NOAA intervals and source equality; flu exclusion; complete-calendar rolling and NA; r and q bounds"}
    (OUT/"verification.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if failures:raise RuntimeError(failures)
    return report


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--permutations",type=int,default=999);args=ap.parse_args()
    if args.permutations < 99:raise SystemExit("Use at least 99 permutations; default 999 for final output.")
    OUT.mkdir(parents=True,exist_ok=True);CARD.mkdir(parents=True,exist_ok=True)
    master=read(ROOT/"data/integrated"/NAME);master["sunday_date"]=pd.to_datetime(master.sunday_date)
    coverage,mapping,expanded=source_audit(master)
    from build_noaa_source_card import make_card
    make_card()
    results,cities,sens,transformed=analyze(master,args.permutations)
    figures(results,cities,transformed)
    headlines=reports(results,cities,sens,transformed,coverage,args.permutations)
    verification=verify(master,results,transformed)
    inputs=sorted((ROOT/"data").rglob("*.csv"))
    manifest={"date":DATE,"seed":SEED,"permutations":args.permutations,"block_weeks":8,
              "versions":{"python":platform.python_version(),"numpy":np.__version__,"pandas":pd.__version__,"scipy":scipy.__version__,"matplotlib":matplotlib.__version__},
              "inputs_sha256":{str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
              "verification":verification,"headlines":headlines}
    (OUT/"run_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    from organize_analysis import organize
    organize(ROOT)
    print(json.dumps({"headlines":headlines,"verification":verification},ensure_ascii=False,indent=2))
