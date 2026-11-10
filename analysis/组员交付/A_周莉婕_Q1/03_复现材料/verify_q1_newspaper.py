"""Independent Q1 rolling/correlation check; run from the project root."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import rankdata, t

ROOT = next((p for p in Path(__file__).resolve().parents
             if (p / 'data' / 'integrated').is_dir()), Path(__file__).resolve().parents[1])
OUT = ROOT / '02_统计结果' if (ROOT / '02_统计结果').is_dir() else ROOT / 'analysis/组员交付/A_周莉婕_Q1/02_统计结果'
source = ROOT / 'data/integrated/weekly_sixcities_1915_1922_1930_1932.csv'
df = pd.read_csv(source, parse_dates=['sunday_date'])
observed = pd.read_csv(OUT / 'q1_pooled_correlations.csv').set_index('disease')
city_observed = pd.read_csv(OUT / 'q1_city_correlations.csv')
stored_pairs = pd.read_csv(OUT / 'q1_paired_city_weeks.csv', float_precision='round_trip')
rank_sensitivity = {}
checks = {}
checks['shape'] = df.shape == (3450,29)
checks['unique_keys'] = not df.duplicated(['city','sunday_date']).any()
checks['575_weeks_per_city'] = bool(df.groupby('city').size().eq(575).all())
checks['max_denominator_total'] = int(df.np_pages.sum()) == 298820
checks['uncovered_rates_missing'] = bool(df.loc[df.np_pages.eq(0), ['np_flu_rate','np_diph_rate','np_polio_rate']].isna().all().all())

def smooth(g, col):
    a = g[col].to_numpy(dtype=float)
    dates = g.sunday_date.to_numpy()
    result = np.full(len(a), np.nan)
    for i in range(3,len(a)):
        if all(dates[j]-dates[j-1] == np.timedelta64(7,'D') for j in range(i-2,i+1)):
            result[i] = np.mean(a[i-3:i+1])
    sd = np.nanstd(result,ddof=0)
    return (result-np.nanmean(result))/sd if sd>0 else result*np.nan

def stats(x,y):
    r = np.corrcoef(x,y)[0,1]
    rho = np.corrcoef(rankdata(x),rankdata(y))[0,1]
    ps = [2*t.sf(abs(v)*np.sqrt((len(x)-2)/(1-v*v)),len(x)-2) for v in (r,rho)]
    return [r,ps[0],rho,ps[1]]

for disease,prefix in [('INFLUENZA','flu'),('DIPHTHERIA','diph'),('POLIOMYELITIS','polio')]:
    arrays=[]
    for city,g in df.groupby('city'):
        g=g.sort_values('sunday_date')
        if prefix=='flu': g=g[g.sunday_date.ge('1920-01-01')]
        x=smooth(g,'np_'+prefix+'_rate'); y=smooth(g,prefix+'_rate_per100k')
        keep=np.isfinite(x)&np.isfinite(y)
        x,y=x[keep],y[keep]
        arrays.append((x,y))
        row=city_observed[(city_observed.disease==disease)&(city_observed.city.str.upper()==city)].iloc[0]
        saved=stored_pairs[(stored_pairs.disease==disease)&(stored_pairs.city==city)]
        checks[disease+'_'+city+'_manual_rolling_pearson'] = bool(len(x)==row.n_city_weeks and np.allclose(stats(x,y)[:2], row[['pearson_r','pearson_p']].to_numpy(float),rtol=1e-9,atol=1e-12))
        checks[disease+'_'+city+'_exported_pairs_spearman'] = bool(np.allclose(stats(saved.newspaper_z,saved.incidence_z)[2:],row[['spearman_rho','spearman_p']].to_numpy(float),rtol=1e-9,atol=1e-12))
        rank_sensitivity[disease+'_'+city] = float(stats(x,y)[2]-row.spearman_rho)
    x=np.concatenate([a[0] for a in arrays]); y=np.concatenate([a[1] for a in arrays])
    row=observed.loc[disease]
    checks[disease+'_pooled_manual_rolling_pearson'] = bool(len(x)==row.n_city_weeks and np.allclose(stats(x,y)[:2],row[['pearson_r','pearson_p']].to_numpy(float),rtol=1e-9,atol=1e-12))
    saved=stored_pairs[stored_pairs.disease==disease]
    checks[disease+'_pooled_exported_pairs_spearman'] = bool(np.allclose(stats(saved.newspaper_z,saved.incidence_z)[2:],row[['spearman_rho','spearman_p']].to_numpy(float),rtol=1e-9,atol=1e-12))

report = {'passed':all(checks.values()),'checks':checks,'method':'Manual 4-week windows independently verify sample counts and Pearson. Spearman recomputed with rankdata from exported paired values. t distribution p values checked. All 18 city and 3 pooled primary results.','manual_window_minus_pandas_spearman_by_city':rank_sensitivity,'floating_point_note':'Mathematically tied rolling values may differ near machine precision across algorithms; raw Spearman ranks can differ slightly. Published main output retains project pandas calculation.','input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'limitations':'Checks numerical reproduction, not causal validity, all OCR accuracy, or autocorrelation-adjusted inference.'}
(OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
assert report['passed'], 'Q1 verification failed'
