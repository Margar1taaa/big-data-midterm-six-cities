"""Audit supplied NOAA zip without extracting/modifying source files."""
from pathlib import Path
import argparse,collections,hashlib,io,json,math,zipfile,xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'analysis/noaa_source_card/补充材料'
CITY={'Baltimore':'BALTIMORE','Cleveland':'CLEVELAND','Losangles':'LOS ANGELES','Milwaukee':'MILWAUKEE','NewYork':'NEW YORK','Washington':'WASHINGTON'}
VARS=['TAVG','TMAX','TMIN','PRCP','SNOW']

def xlsx_bytes(data):
    ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        shared=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            shared=[''.join(e.itertext()) for e in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',ns)]
        rows=[]
        for r in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('.//s:sheetData/s:row',ns):
            vals={}
            for c in r.findall('s:c',ns):
                col=''.join(x for x in c.get('r') if x.isalpha());v=c.find('s:v',ns)
                value=v.text if v is not None else ''
                if c.get('t')=='s' and value:value=shared[int(value)]
                elif c.get('t')=='inlineStr':value=''.join(c.find('s:is',ns).itertext())
                vals[col]=value
            rows.append(vals)
        header=rows[0];return pd.DataFrame([{header[k]:v for k,v in r.items() if k in header} for r in rows[1:]])

def distance(lat,lon,clat,clon):
    a,b,c,d=map(math.radians,[lat,lon,clat,clon]);h=math.sin((a-c)/2)**2+math.cos(a)*math.cos(c)*math.sin((b-d)/2)**2
    return 6371.0088*2*math.asin(min(1,math.sqrt(h)))

def run(path):
    OUT.mkdir(parents=True,exist_ok=True)
    points=pd.read_csv(ROOT/'data/cleaned/nhgis/nhgis_points_geo.csv',encoding='utf-8-sig').set_index('tycho_city')
    files=[];mapping=[];weekly=[];city_stats=[];readmes={};inventories={};daily=[]
    with zipfile.ZipFile(path) as z:
        entries=[e for e in z.infolist() if not e.is_dir()]
        station_text=z.read(next(e for e in entries if 'ghcnd-stations' in e.filename)).decode('utf-8')
        stations={line[:11]:{'lat':float(line[12:20]),'lon':float(line[21:30]),'elevation_m':float(line[31:37]),'catalogue_name':line[41:71].strip()} for line in station_text.splitlines() if len(line)>=71}
        for e in entries:
            if e.filename.endswith('README.txt'):readmes[e.filename]=z.read(e).decode('utf-8-sig')
        wide=[e for e in entries if e.filename.endswith('.csv') and '_long' not in e.filename and 'summary' not in e.filename]
        for e in wide:
            city=CITY[e.filename.split('/')[1].removeprefix('NOAA_')]
            raw=z.read(e);fmt='XLSX' if raw[:2]==b'PK' else 'CSV'
            f=xlsx_bytes(raw) if fmt=='XLSX' else pd.read_csv(io.BytesIO(raw),encoding='utf-8-sig',dtype=str)
            if fmt=='XLSX':f['DATE']=pd.to_datetime(pd.to_numeric(f.DATE),unit='D',origin='1899-12-30')
            else:f['DATE']=pd.to_datetime(f.DATE)
            f['city']=city;f['source_file']=Path(e.filename).name
            missing_cols=[c for c in VARS if c not in f]
            for c in VARS:
                if c not in f:f[c]=np.nan
                f[c]=pd.to_numeric(f[c],errors='coerce')
            files.append({'city':city,'source_file':Path(e.filename).name,'archive_path':e.filename,'format':fmt,'bytes':len(raw),'rows':len(f),'actual_station':';'.join(sorted(f.STATION.unique())),
                          'date_start':f.DATE.min().strftime('%Y-%m-%d'),'date_end':f.DATE.max().strftime('%Y-%m-%d'),
                          'missing_columns':';'.join(missing_cols),'sha256':hashlib.sha256(raw).hexdigest(),
                          'has_quality_flags':any('FLAG' in c or 'ATTR' in c for c in f)})
            for station,g in f.groupby('STATION'):
                meta=stations.get(station,{})
                dist=distance(meta['lat'],meta['lon'],points.loc[city,'lat'],points.loc[city,'lon']) if meta else np.nan
                mapping.append({'city':city,'source_file':Path(e.filename).name,'actual_station':station,'station_name':g.NAME.dropna().iloc[0],
                                'date_start':g.DATE.min().strftime('%Y-%m-%d'),'date_end':g.DATE.max().strftime('%Y-%m-%d'),'source_rows':len(g),
                                **meta,'distance_km':dist,'over_50km':dist>50,'over_100km':dist>100})
            # Candidate reconstruction follows file-station grouping inherited by the handoff.
            f['TAVG']=f.TAVG.fillna((f.TMAX+f.TMIN)/2)
            f['sunday_date']=f.DATE-pd.to_timedelta((f.DATE.dt.dayofweek+1)%7,unit='D')
            valid=f[VARS].notna().any(axis=1)
            grouped=f[valid].groupby('sunday_date')
            w=grouped[VARS].mean();w['n_days']=grouped.DATE.nunique();w['city']=city;w['source_file']=Path(e.filename).name
            weekly.append(w.reset_index())
            daily.append(f[['city','STATION','DATE','sunday_date',*VARS]].copy())
        ids={r['actual_station'] for r in mapping}
        inv=z.read(next(e for e in entries if 'ghcnd-inventory' in e.filename)).decode('utf-8')
        for line in inv.splitlines():
            if line[:11] in ids:
                inventories.setdefault(line[:11],[]).append({'element':line[31:35].strip(),'first_year':int(line[36:40]),'last_year':int(line[41:45])})
        for r in mapping:r['inventory_elements']=';'.join(sorted({v['element'] for v in inventories.get(r['actual_station'],[])}))
        categories=collections.Counter()
        for e in entries:
            cat='wide' if e in wide else ('long' if '_long.csv' in e.filename else 'metadata_and_notes')
            categories[cat]+=e.file_size
        summary={'zip_bytes':path.stat().st_size,'uncompressed_bytes':sum(e.file_size for e in entries),'file_count':len(entries),'wide_files':len(wide),'wide_rows':sum(r['rows'] for r in files),
                 'actual_unique_stations':len(ids),'city_station_pairs':len({(r['city'],r['actual_station']) for r in mapping}),
                 'size_by_category':dict(categories),'zip_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                 'quality_flags_present_files':sum(r['has_quality_flags'] for r in files),
                 'readmes':readmes}
    mf=pd.DataFrame(mapping);ff=pd.DataFrame(files)
    for city,g in ff.groupby('city'):
        m=mf[mf.city.eq(city)].drop_duplicates('actual_station')
        city_stats.append({'city':city,'wide_files':len(g),'station_ids':m.actual_station.nunique(),'rows':int(g.rows.sum()),'bytes':int(g.bytes.sum()),'start':g.date_start.min(),'end':g.date_end.max(),
                           'stations_over_50km':int(m.over_50km.sum()),'stations_over_100km':int(m.over_100km.sum()),'max_distance_km':m.distance_km.max()})
    ws=pd.concat(weekly,ignore_index=True)
    # Count a true station once; identical duplicate files do not add observations.
    ds=pd.concat(daily,ignore_index=True).drop_duplicates(['city','STATION','DATE',*VARS])
    ds=ds[ds[VARS].notna().any(axis=1)]
    sg=ds.groupby(['city','STATION','sunday_date'])
    ws=sg[VARS].mean();ws['n_days']=sg.DATE.nunique();ws=ws.reset_index().rename(columns={'STATION':'source_file'})
    rebuilt=ws.groupby(['city','sunday_date'])[VARS+['n_days']].mean().round(2)
    rebuilt['n_days']=rebuilt.n_days.round(1)
    rebuilt['n_stations']=ws.groupby(['city','sunday_date']).source_file.nunique()
    rebuilt=rebuilt.rename(columns=dict(zip(VARS,['tavg_avg','tmax_avg','tmin_avg','prcp_sum','snow_sum']))).reset_index()
    clean=pd.read_csv(ROOT/'data/cleaned/noaa/noaa_weekly_sixcities.csv',encoding='utf-8-sig',parse_dates=['sunday_date'])
    joined=clean.merge(rebuilt,on=['city','sunday_date'],suffixes=('_given','_candidate'),how='outer',indicator=True)
    checks=[]
    for (city,scope),g in pd.concat([joined.assign(scope='all_cleaned'),joined[joined.sunday_date.isin(pd.to_datetime(pd.read_csv(ROOT/'data/integrated/weekly_sixcities_1915_1922_1930_1932.csv',encoding='utf-8-sig').sunday_date.unique()))].assign(scope='study_window')]).groupby(['city','scope']):
        for col in ['tavg_avg','tmax_avg','tmin_avg','prcp_sum','snow_sum','n_days','n_stations']:
            a=g[col+'_given'];b=g[col+'_candidate'];ok=np.isclose(a,b,atol=.011,rtol=0,equal_nan=True)
            checks.append({'city':city,'scope':scope,'field':col,'compared_weeks':len(g),'matching_weeks':int(ok.sum()),'different_weeks':int((~ok).sum()),'max_abs_difference':(a-b).abs().max()})
    dups=ff[ff.duplicated('sha256',keep=False)]
    summary['identical_wide_file_groups']=[g.archive_path.tolist() for _,g in dups.groupby('sha256')]
    summary['unique_wide_bytes_by_hash']=int(ff.drop_duplicates('sha256').bytes.sum())
    for name,frame in [('raw_file_manifest.csv',ff),('raw_station_city_mapping.csv',mf),('raw_coverage_by_city.csv',pd.DataFrame(city_stats)),('raw_weekly_comparison.csv',pd.DataFrame(checks))]:
        frame.to_csv(OUT/name,index=False,encoding='utf-8-sig',float_format='%.6g')
    (OUT/'raw_audit.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='readmes'},ensure_ascii=False,indent=2))
    print(pd.DataFrame(checks).groupby('field').different_weeks.sum().to_string())

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--zip',type=Path,default=Path(r'D:/Homework/大数据信息系统/NOAA_DATA.zip'));args=ap.parse_args();run(args.zip)
