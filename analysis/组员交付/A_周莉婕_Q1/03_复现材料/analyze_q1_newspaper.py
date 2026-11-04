#!/usr/bin/env python3
"""Q1: newspaper attention and same-week disease incidence."""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "integrated" / "weekly_sixcities_1915_1922_1930_1932.csv"
OUT = ROOT / "analysis" / "q1_newspaper"

DISEASES = {
    "INFLUENZA": ("np_flu_rate", "flu_rate_per100k", "Influenza"),
    "DIPHTHERIA": ("np_diph_rate", "diph_rate_per100k", "Diphtheria"),
    "POLIOMYELITIS": ("np_polio_rate", "polio_rate_per100k", "Poliomyelitis"),
}

CITY_LABELS = {
    "BALTIMORE": "Baltimore",
    "CLEVELAND": "Cleveland",
    "LOS ANGELES": "Los Angeles",
    "MILWAUKEE": "Milwaukee",
    "NEW YORK": "New York",
    "WASHINGTON": "Washington",
}


def p_text(value: float) -> str:
    return "<0.001" if value < 0.001 else f"={value:.3f}"


def zscore(series: pd.Series) -> pd.Series:
    sd = series.std(ddof=0)
    if pd.isna(sd) or sd == 0:
        return pd.Series(np.nan, index=series.index)
    return (series - series.mean()) / sd


def rolling_within_segments(frame: pd.DataFrame, column: str) -> pd.Series:
    segment = frame["sunday_date"].diff().dt.days.ne(7).cumsum()
    return frame.groupby(segment, sort=False)[column].transform(
        lambda values: values.rolling(4, min_periods=4).mean()
    )


def correlations(paired: pd.DataFrame, disease: str, city: str) -> dict[str, object]:
    x = paired["newspaper_z"].to_numpy()
    y = paired["incidence_z"].to_numpy()
    if len(paired) < 4 or np.std(x) == 0 or np.std(y) == 0:
        return {
            "disease": disease,
            "city": city,
            "n_city_weeks": len(paired),
            "pearson_r": np.nan,
            "pearson_p": np.nan,
            "spearman_rho": np.nan,
            "spearman_p": np.nan,
        }
    pr, pp = pearsonr(x, y)
    sr, sp = spearmanr(x, y)
    return {
        "disease": disease,
        "city": city,
        "n_city_weeks": len(paired),
        "pearson_r": pr,
        "pearson_p": pp,
        "spearman_rho": sr,
        "spearman_p": sp,
    }


def prepare_pairs(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    all_pairs = []
    city_rows = []
    pooled_rows = []

    for disease, (newspaper_col, incidence_col, _) in DISEASES.items():
        disease_pairs = []
        for city, group in data.groupby("city", sort=True):
            frame = group.sort_values("sunday_date").copy()
            if disease == "INFLUENZA":
                frame = frame[frame["sunday_date"] >= pd.Timestamp("1920-01-01")].copy()
            frame["newspaper_roll4"] = rolling_within_segments(frame, newspaper_col)
            frame["incidence_roll4"] = rolling_within_segments(frame, incidence_col)
            frame["newspaper_z"] = zscore(frame["newspaper_roll4"])
            frame["incidence_z"] = zscore(frame["incidence_roll4"])
            paired = frame.dropna(subset=["newspaper_z", "incidence_z"]).copy()
            paired["disease"] = disease
            paired["city_label"] = CITY_LABELS.get(city, city.title())
            paired = paired[
                [
                    "city",
                    "city_label",
                    "sunday_date",
                    "year",
                    "disease",
                    "np_pages",
                    "newspaper_roll4",
                    "incidence_roll4",
                    "newspaper_z",
                    "incidence_z",
                ]
            ]
            all_pairs.append(paired)
            disease_pairs.append(paired)
            city_rows.append(correlations(paired, disease, CITY_LABELS.get(city, city.title())))
        pooled = pd.concat(disease_pairs, ignore_index=True)
        pooled_rows.append(correlations(pooled, disease, "ALL_CITIES_POOLED"))

    return (
        pd.concat(all_pairs, ignore_index=True),
        pd.DataFrame(city_rows),
        pd.DataFrame(pooled_rows),
    )


def save_figure(plot_data: pd.DataFrame, pooled: pd.DataFrame, output: Path) -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "font.size": 10,
        }
    )
    fig, axes = plt.subplots(3, 1, figsize=(13.2, 9.2), sharex=True)
    media_color = "#1A5A96"
    disease_color = "#C45D2D"

    for axis, (disease, (_, _, label)) in zip(axes, DISEASES.items()):
        subset = plot_data[plot_data["disease"] == disease].sort_values("sunday_date")
        stat = pooled[pooled["disease"] == disease].iloc[0]
        right = axis.twinx()
        segment = subset["sunday_date"].diff().dt.days.ne(7).cumsum()
        for _, section in subset.groupby(segment, sort=False):
            axis.plot(
                section["sunday_date"], section["newspaper_z_mean"],
                color=media_color, linewidth=1.8,
            )
            right.plot(
                section["sunday_date"], section["incidence_z_mean"],
                color=disease_color, linewidth=1.6, alpha=0.92,
            )
        values = np.concatenate(
            [subset["newspaper_z_mean"].to_numpy(), subset["incidence_z_mean"].to_numpy()]
        )
        bound = max(2.0, min(5.0, np.ceil(np.nanmax(np.abs(values)) * 2) / 2))
        axis.set_ylim(-bound, bound)
        right.set_ylim(-bound, bound)
        axis.axhline(0, color="#9B9B9B", linewidth=0.7, linestyle="--")
        axis.grid(axis="y", color="#D9D9D9", linewidth=0.6, alpha=0.8)
        axis.set_ylabel("Newspaper attention\n4-week z-score", color=media_color)
        right.set_ylabel("Incidence per 100k\n4-week z-score", color=disease_color)
        axis.tick_params(axis="y", labelcolor=media_color)
        right.tick_params(axis="y", labelcolor=disease_color)
        axis.set_title(
            f"{label}   |   Pearson r={stat.pearson_r:.2f}, p{p_text(stat.pearson_p)}; "
            f"Spearman ρ={stat.spearman_rho:.2f}",
            loc="left", fontsize=11, fontweight="bold", pad=7,
        )
        axis.spines[["top", "right"]].set_visible(False)
        right.spines[["top", "left"]].set_visible(False)

    axes[-1].set_xlabel(
        "Week (Sunday label); 1923–1929 intentionally outside the newspaper collection window"
    )
    fig.suptitle(
        "When disease incidence rose, did local newspaper attention rise at the same time?",
        x=0.07, y=0.985, ha="left", fontsize=16, fontweight="bold", color="#1A2B4A",
    )
    fig.text(
        0.07, 0.952,
        "Six U.S. cities | weekly city panel | 4-week rolling means | within-city z-scores | "
        "influenza excludes 1915–1919",
        ha="left", fontsize=10.5, color="#555555",
    )
    fig.text(
        0.07, 0.018,
        "Source: Chronicling America OCR strong-term hit-page rate; Project Tycho cases; "
        "NHGIS population. Lines are weekly means of paired city-level z-scores.",
        ha="left", fontsize=9, color="#666666",
    )
    fig.subplots_adjust(left=0.12, right=0.88, top=0.90, bottom=0.09, hspace=0.36)
    fig.savefig(output, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(INPUT, encoding="utf-8-sig")
    data["sunday_date"] = pd.to_datetime(data["sunday_date"], errors="raise")
    if data.duplicated(["city", "sunday_date"]).any():
        raise ValueError("Integrated table has duplicate city+sunday_date keys")

    pairs, city_stats, pooled = prepare_pairs(data)

    sensitivity_data = data.copy()
    for prefix in ("flu", "diph", "polio"):
        numerator = (
            sensitivity_data[f"np_{prefix}_hits"].fillna(0)
            + sensitivity_data[f"np_{prefix}_hits_weak"].fillna(0)
        )
        sensitivity_data[f"np_{prefix}_rate"] = np.where(
            sensitivity_data["np_pages"].fillna(0).gt(0),
            numerator / sensitivity_data["np_pages"] * 100,
            np.nan,
        )
    _, sensitivity_city, sensitivity_pooled = prepare_pairs(sensitivity_data)
    sensitivity_pooled.insert(2, "measure", "strong_plus_weak")
    sensitivity_city.insert(2, "measure", "strong_plus_weak")
    plot_data = (
        pairs.groupby(["disease", "sunday_date"], as_index=False)
        .agg(
            newspaper_z_mean=("newspaper_z", "mean"),
            incidence_z_mean=("incidence_z", "mean"),
            n_cities=("city", "nunique"),
        )
        .sort_values(["disease", "sunday_date"])
    )

    pairs.to_csv(OUT / "q1_paired_city_weeks.csv", index=False, encoding="utf-8-sig")
    city_stats.to_csv(OUT / "q1_city_correlations.csv", index=False, encoding="utf-8-sig")
    pooled.to_csv(OUT / "q1_pooled_correlations.csv", index=False, encoding="utf-8-sig")
    sensitivity_pooled.to_csv(
        OUT / "q1_sensitivity_strong_plus_weak_pooled.csv", index=False, encoding="utf-8-sig"
    )
    sensitivity_city.to_csv(
        OUT / "q1_sensitivity_strong_plus_weak_by_city.csv", index=False, encoding="utf-8-sig"
    )
    plot_data.to_csv(OUT / "q1_plot_weekly_series.csv", index=False, encoding="utf-8-sig")

    quality = {
        "rows": len(data),
        "unique_city_week_keys": data[["city", "sunday_date"]].drop_duplicates().shape[0],
        "columns": len(data.columns),
        "newspaper_covered_city_weeks": int(data["np_pages"].fillna(0).gt(0).sum()),
        "newspaper_uncovered_city_weeks": int(data["np_pages"].fillna(0).eq(0).sum()),
    }
    with (OUT / "q1_data_quality_checks.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["check", "value"])
        writer.writerows(quality.items())

    coverage = (
        data.assign(has_newspaper=data["np_pages"].fillna(0).gt(0))
        .groupby("city")["has_newspaper"].sum().astype(int).rename("covered_weeks")
    )
    coverage.to_csv(OUT / "q1_newspaper_coverage_by_city.csv", encoding="utf-8-sig")
    save_figure(plot_data, pooled, OUT / "fig_q1_newspaper_disease_sync.png")

    print(pooled.to_string(index=False))
    print("\nSENSITIVITY: STRONG + WEAK TERMS")
    print(sensitivity_pooled.to_string(index=False))
    print(city_stats.to_string(index=False))
    print(f"Wrote Q1 outputs to {OUT}")


if __name__ == "__main__":
    main()
