"""Reconstruct the 29-column handoff table from supplied cleaned CSVs.

This is a reconstruction of the documented rules, not the missing original script.
Run --check to compare every value and NA mask without changing the input.
"""
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
NAME = "weekly_sixcities_1915_1922_1930_1932.csv"
YEARS = list(range(1915, 1923)) + list(range(1930, 1933))
DISEASES = {"INFLUENZA": "flu", "DIPHTHERIA": "diph", "POLIOMYELITIS": "polio"}
WX = ["tavg_avg", "tmax_avg", "tmin_avg", "prcp_sum", "snow_sum", "n_days", "n_stations"]
COLUMNS = ["city", "sunday_date", "year", "flu_cases", "flu_deaths", "diph_cases",
           "diph_deaths", "polio_cases", *WX, "population", "np_flu_hits",
           "np_flu_hits_weak", "np_polio_hits", "np_polio_hits_weak", "np_diph_hits",
           "np_diph_hits_weak", "np_pages", "np_flu_rate", "np_polio_rate", "np_diph_rate",
           "flu_rate_per100k", "diph_rate_per100k", "polio_rate_per100k"]


def read(path):
    return pd.read_csv(path, encoding="utf-8-sig")


def build(root=ROOT):
    clean = root / "data/cleaned"
    pop = read(clean / "nhgis/population_clean.csv")
    # Handoff includes the Sunday 1933-01-01 as the 1932 end-boundary label.
    dates = pd.date_range("1915-01-01", "1933-01-01", freq="W-SUN")
    dates = dates[dates.year.isin(YEARS) | (dates == pd.Timestamp("1933-01-01"))]
    f = pd.MultiIndex.from_product([sorted(pop.tycho_city.unique()), dates],
                                  names=["city", "sunday_date"]).to_frame(index=False)
    f["year"] = f.sunday_date.dt.year
    ty = read(clean / "tycho/cleaned_tycho_weekly_sixcities.csv")
    starts = pd.to_datetime(ty.from_date)
    ty["sunday_date"] = starts + pd.to_timedelta((6-starts.dt.dayofweek) % 7, unit="D")
    ty["field"] = ty.disease.map(DISEASES) + "_" + ty.event.str.lower()
    ty = ty[ty.field.isin(["flu_cases", "flu_deaths", "diph_cases", "diph_deaths", "polio_cases"])]
    tw = ty.pivot_table(index=["city", "sunday_date"], columns="field", values="number", aggfunc="max").reset_index()
    f = f.merge(tw, how="left", on=["city", "sunday_date"], validate="one_to_one")
    w = read(clean / "noaa/noaa_weekly_sixcities.csv")
    w["sunday_date"] = pd.to_datetime(w.sunday_date)
    f = f.merge(w[["city", "sunday_date", *WX]], how="left", on=["city", "sunday_date"], validate="one_to_one")
    for city, g in pop.groupby("tycho_city"):
        g = g.sort_values("census_year")
        m = f.city.eq(city)
        f.loc[m, "population"] = np.rint(np.interp(f.loc[m, "year"], g.census_year, g.population))
    f["population"] = f.population.astype("int64")
    n = pd.concat([read(clean / "newspaper/newspaper_hits_weekly.csv"),
                   read(clean / "newspaper/newspaper_hits_weekly_zip.csv")], ignore_index=True)
    n["city"] = n.city.str.upper()
    n["sunday_date"] = pd.to_datetime(n.sunday_date)
    for disease, short in DISEASES.items():
        g = n[n.disease.eq(disease)].groupby(["city", "sunday_date"])[["n_hits_strong", "n_hits_weak", "n_pages"]].sum()
        rename = {"n_hits_strong": f"np_{short}_hits", "n_hits_weak": f"np_{short}_hits_weak"}
        g = g.rename(columns=rename).reset_index().drop(columns="n_pages")
        f = f.merge(g, how="left", on=["city", "sunday_date"], validate="one_to_one")
    # Match the handed-off table: denominator is max across papers, hits are summed.
    # This inherited inconsistency is logged in GAPS; Q3 does not use these fields.
    pages = n.groupby(["city", "sunday_date"])["n_pages"].max().rename("np_pages").reset_index()
    f = f.merge(pages, how="left", on=["city", "sunday_date"], validate="one_to_one")
    for c in [c for c in f if c.startswith("np_")]:
        f[c] = f[c].fillna(0).astype("int64")  # no pages is known zero coverage; rates remain NA
    for short in DISEASES.values():
        f[f"np_{short}_rate"] = (100*f[f"np_{short}_hits"]/f.np_pages.where(f.np_pages.gt(0))).round(2)
        f[f"{short}_rate_per100k"] = (100000*f[f"{short}_cases"]/f.population).round(2)
    f["sunday_date"] = f.sunday_date.dt.strftime("%Y-%m-%d")
    return f[COLUMNS].sort_values(["city", "sunday_date"]).reset_index(drop=True)


def compare(a, b):
    assert list(a.columns) == list(b.columns), "column mismatch"
    assert a.shape == b.shape, "shape mismatch"
    mismatches = []
    for c in a:
        av, bv = a[c], b[c]
        if pd.api.types.is_numeric_dtype(av):
            ok = np.isclose(av.to_numpy(dtype=float), bv.to_numpy(dtype=float), rtol=0, atol=1e-9, equal_nan=True)
        else:
            ok = av.fillna("<NA>").eq(bv.fillna("<NA>")).to_numpy()
        for i in np.flatnonzero(~ok):
            mismatches.append({"row": int(i), "column": c, "expected": str(av.iloc[i]), "rebuilt": str(bv.iloc[i])})
    return mismatches


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="compare all cells, do not write master")
    args = ap.parse_args()
    rebuilt = build()
    dest = ROOT / "data/integrated" / NAME
    diff = compare(read(dest), rebuilt)
    audit = {"rows": len(rebuilt), "columns": len(rebuilt.columns), "different_cells": len(diff), "examples": diff[:20],
             "scope": "cleaned -> integrated only; original raw cleaning scripts unavailable"}
    out = ROOT / "analysis/q3"
    out.mkdir(parents=True, exist_ok=True)
    if (out / "补充材料").exists():
        out = out / "补充材料"
    (out / "rebuild_check.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    if diff:
        raise SystemExit("Reconstruction differs; master was not changed.")
    if not args.check:
        rebuilt.to_csv(dest, index=False, encoding="utf-8-sig", lineterminator="\n")
