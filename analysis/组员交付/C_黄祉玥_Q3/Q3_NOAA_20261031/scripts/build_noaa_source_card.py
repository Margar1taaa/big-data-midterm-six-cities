"""Build the source card from the raw-zip audit and current study coverage."""
from pathlib import Path
import hashlib,html,json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'analysis/noaa_source_card'
SUP=OUT/'补充材料'
DATE='2026-10-31'
OFFICIAL='https://www.ncei.noaa.gov/pub/data/ghcn/daily/readme.txt'


def mdtable(frame):
    return '| '+' | '.join(frame.columns)+' |\n|'+'|'.join(['---']*len(frame.columns))+'|\n'+'\n'.join('| '+' | '.join(str(x) for x in row)+' |' for row in frame.itertuples(index=False,name=None))


def make_card():
    if not (SUP/'raw_audit.json').exists():
        raise FileNotFoundError('请先运行 python scripts/audit_noaa_raw.py --zip <NOAA_DATA.zip路径>')
    audit=json.loads((SUP/'raw_audit.json').read_text(encoding='utf-8'))
    raw=pd.read_csv(SUP/'raw_coverage_by_city.csv',encoding='utf-8-sig')
    mapping=pd.read_csv(SUP/'raw_station_city_mapping.csv',encoding='utf-8-sig')
    filemanifest=pd.read_csv(SUP/'raw_file_manifest.csv',encoding='utf-8-sig')
    units=pd.read_csv(SUP/'unit_sample_comparison.csv',encoding='utf-8-sig') if (SUP/'unit_sample_comparison.csv').exists() else None
    unit_evidence=units is not None and len(units)==12 and units['match'].all()
    coverage_path=OUT/'coverage_by_city.csv'
    if not coverage_path.exists():coverage_path=SUP/'coverage_by_city.csv'
    coverage=pd.read_csv(coverage_path,encoding='utf-8-sig')
    for r in raw.itertuples(index=False):
        coverage.loc[coverage.city.eq(r.city),'mapping_files']=r.wide_files
        coverage.loc[coverage.city.eq(r.city),'mapping_unique_station_ids']=r.station_ids
    coverage.to_csv(OUT/'coverage_by_city.csv',index=False,encoding='utf-8-sig',float_format='%.10g')
    mapping.to_csv(OUT/'station_city_mapping.csv',index=False,encoding='utf-8-sig',float_format='%.6g')
    temp_unit='°F（官方原生记录样本换算支持；导出配置未附）' if unit_evidence else '原导出单位待证'
    water_unit='in/day（周内有效日均；官方样本换算支持）' if unit_evidence else '原导出单位/日'
    fields=[('city','string','六城大写英文名，与Tycho连接','—'),
            ('sunday_date','date','周日起始标签，和city组成唯一键','YYYY-MM-DD'),
            ('week_end','date','周六=sunday_date+6天；仅单源周表保留','YYYY-MM-DD'),
            ('tavg_avg','float','站内日平均温度的周均，再跨站平均；缺TAVG以(TMAX+TMIN)/2回退',temp_unit),
            ('tmax_avg','float','日最高温度的周均，再跨站平均；不是周极大值',temp_unit),
            ('tmin_avg','float','日最低温度的周均，再跨站平均；不是周极小值',temp_unit),
            ('prcp_sum','float','先计算各站该周有效观测日的日均降水，再对站点取平均；不是周累计量',water_unit),
            ('snow_sum','float','先计算各站该周有效观测日的日均降雪，再对站点取平均；SNOW不是SNWD雪深',water_unit),
            ('n_days','float','站周有效日数的跨站平均，保留1位小数；不是城市唯一有效日计数','天'),
            ('n_stations','integer','该周参与气象汇总的站点数；不等同于每个要素的有效站点数','站/周')]
    dictionary=pd.DataFrame(fields,columns=['field','type','definition','unit'])
    dictionary['missing_quality_rule']='缺失保留NA，真实0保留；不同气象要素分别按有效观测平均'
    dictionary.to_csv(OUT/'field_dictionary.csv',index=False,encoding='utf-8-sig')
    display=raw[['city','wide_files','station_ids','rows','stations_over_50km','max_distance_km']].copy()
    display.max_distance_km=display.max_distance_km.map(lambda x:f'{x:.1f}')
    display.columns=['城市','宽表文件','真实站号','原始行数','超过50km站点','最远站距km']
    study=coverage[['city','master_weeks','tavg_avg_non_na','prcp_sum_non_na','snow_sum_non_na','n_stations_min','n_stations_max']]
    stationtext='\n'.join('- **'+city+'**：'+'、'.join('`'+v+'`' for v in sorted(g.actual_station.unique()))+'。' for city,g in mapping.groupby('city'))
    unitnote='本次将USC00475474站1947-01-01至01-03的TMAX/TMIN/PRCP/SNOW共12个本地值与NOAA官方原生.dly记录比对：按温度°C→°F、降水/雪mm→inch换算并按导出精度舍入，12项均吻合。因此本地英制导出解释获得逐值证据；这仍不是对58文件全部单位配置的逐份认证，原下载订单/units参数尚未提供。' if unit_evidence else '未取得可用单位样本比对，暂继承原导出单位。'
    card=f'''# NOAA GHCN-Daily 气象数据源卡

负责人：黄祉玥（初始调查表C9）；复核日期：{DATE}。用途：任务3及线B数据源材料。

## 1. 来源与获取方式

数据源为NOAA/NCEI发布的GHCN-Daily。[官方产品页](https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily)、[官方数据目录](https://www.ncei.noaa.gov/pub/data/ghcn/daily/)、[变量和文件格式说明]({OFFICIAL})、[数据DOI](https://doi.org/10.7289/V5D21VHZ)。官方说明核对日期为本次复核日，不冒充原始采集日期。

初始调查表第1、4部分记录拟经官方HTTPS按站下载，无需注册；CDO API是另一个需要Token的访问方式，见[官方API说明](https://www.ncei.noaa.gov/cdo-web/webservices/v2)。原调查C36是“下载后填写”的待办，现已从包中核实纽约中央公园USW00094728实际数据存在，可将样本获取状态改为已获得。原始下载日期、订单/查询参数、具体导出配置未提供。

## 2. 实际文件、记录数和规模

只统计原始宽表，不计转换长表。共有**58个文件、946,693行源记录**，字节合计75,331,206（75.33MB，71.84MiB）；这些行未先做跨文件去重。密尔沃基两份宽表字节完全相同，按文件SHA去掉这一份重复后为73,839,423字节。58个文件中56个是文本CSV，纽约2个虽以.csv结尾，实际为XLSX。不能只按扩展名读取。

宽表识别到57个不同真实站号、59个城市—站点组合。同一站可关联多个城市，一个源文件也可能含多个真实站号，因此文件数、站数、城市站点组合数不同。此前约338MB是含其他文件的整包解压大小，不能作为独立气象日值采集量；仅宽表未达到200MB。

{mdtable(display)}

## 3. 时间、空间范围与站距

初始调查计划为1916–1953、城市50km范围；这是预期方案，不代表实际每站都满足。宽表总体观测日期为1900-01-01至1995-12-21，后者仅华盛顿目录个别站延伸；其他五城最晚到1960-01-01。日期范围不表示逐日连续，各站逐文件起止见补充材料清单。

原包ghcnd-stations目录提供站点经纬度/高程/站名，ghcnd-inventory目录提供要素和起止年份。已按STATION核实六城映射，并以NHGIS城市点位和Haversine距离计算站距。59个城市—站点组合中17个超过50km，0个超过100km，最大96.3km，故实际是近城区域站网，不能声称全数位于50km内。站点目录是当前目录快照，站距不是历史站点迁移后的逐年距离，也不是到城市边界的距离。

{stationtext}

## 4. 字段与单位

原始宽表核心列为STATION、NAME、DATE和PRCP/SNOW/SNWD/TMAX/TMIN，部分站另含TAVG；有些文件完全没有某要素列，例如洛杉矶USC00041779没有SNOW，不能补造为0。原始站点目录另提供LATITUDE/LONGITUDE/ELEVATION，融合主表保留如下周字段。

{mdtable(dictionary[['field','definition','unit']])}

{unitnote} 原生.dly格式的温度单位是0.1°C、PRCP是0.1mm、SNOW/SNWD是mm，不能把这些原生缩放再次套到已导出本地CSV。PRCP/SNOW周字段虽名含sum，实际是日均口径，单位按日均解释。若换成公制，应温度用(F−32)×5/9，日均水量乘25.4；本次源卡更新不修改主表数值。

## 5. 日转周与质量复核

① 识别真实文件格式，读表内STATION，不从文件名猜站号。② 各站日期归入当周周日，week_end为其后第6天。③ TAVG缺值用同日(TMAX+TMIN)/2回退；站内对各要素有效日求均值，再跨站平均。④ PRCP/SNOW分别用有效观测日作分母，是周内日均，不是周累计。⑤ n_days为站周有效日计数的跨站均值，保留1位小数；n_stations描述该周参与汇总的站点数。⑥ 缺失NA，观测0保留，各要素有效站数可以不同。

本次用原始宽表按真实站号和上述日均规则独立重算：当前575周/城研究窗口的五个气象值与交接周表最大绝对差为0.01（保留两位小数的舍入级差异）；n_days和n_stations一致。比较明细记录容差0.011；这是独立核验，不冒充找到了原clean_noaa.py。

窗口外另有缺口：纽约1950年后的两个XLSX伪CSV加入后，497个周标签的站数与旧清洗周表不同，部分气象值也不同。不能把当前11年研究窗口的核验外推为1900–1960全段重建无差异。Q3使用1915–1922＋1930–1932（含1933-01-01边界周），不受这两文件起始年代影响。

## 6. 当前主表覆盖与实际连接

按city×sunday_date关联NOAA和Tycho；气象不需要按病种重复建立观测。流感分析整段排除1915–1919，病例做完整4周均值；这些是当前分析约定。初始调查表第6部分是早期方案，本节以现有主表及实际复核为准。

{mdtable(study)}

三温度各3450有效值，PRCP3449，SNOW3112；缺降水1个（LA）、缺降雪338个（LA291、Milwaukee47），不以0补缺。单源周表20,655行是六城全部清洗标签，和原始日值946,693行是不同粒度。

## 7. 风险、限制与结论

- 可用于本研究窗口内标准化的气候—病例关联，不能推出因果。季节性、站网时变、缺失非随机及城市行政边界不一致仍需在解释中说明。
- 原始宽表57/58个文件未提供显式FLAGS/ATTRIBUTES类列；仅华盛顿USC00181995带属性列。官方数据经过其质量审查，不等于本地导出保留了完整质量标志。不能写成本项目已逐项完成QFLAG筛选。
- 密尔沃基USC00476764.csv和USC00476922.csv内容SHA一致；调查宽表时只记一份独立数据来源。克利夫兰有文件名错配/合并站，以STATION和映射清单为准。纽约两个伪CSV必须识别格式。n_stations无需再写“去重待核实”，本次窗口独立重算的站数与交接表一致。
- 单位由12个逐日样本核验支持英制解释；原始导出订单/日期和完整清洗脚本仍未取得。57个全局站号不代表每周57站；要素覆盖清单不代表项目窗口每周有有效观测。
- 单独按原始宽表计量约75.33MB，采集规模应使用此口径，与课程要求的差额需按实际数据说明。

## 复现与证据

`python scripts/audit_noaa_raw.py --zip <NOAA_DATA.zip路径>` 生成文件清单、六城映射和站距、规模与周值对照；`python scripts/build_noaa_source_card.py`生成本源卡。所需audit JSON/CSV已随交付保留；重建源卡不必重新下载原始数据。

来源证据：用户提供的NOAA_DATA.zip（SHA256见raw_audit.json）；初始调查表Sheet1的A1:E56，使用第1–5部分及第7部分的标题补全风险，不把第6部分旧设想当作当前事实。调查表第5部分原来为空，现已按原始宽表补齐。未改动该工作簿。
'''
    (OUT/'NOAA_source_card.md').write_text(card,encoding='utf-8')
    th=''.join('<th>'+html.escape(c)+'</th>' for c in display.columns)
    tr=''.join('<tr>'+''.join('<td>'+html.escape(str(x))+'</td>' for x in row)+'</tr>' for row in display.itertuples(index=False,name=None))
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>NOAA 气象源卡 · 一页版</title><style>
@page{{size:A4;margin:12mm}}*{{box-sizing:border-box}}body{{max-width:960px;margin:24px auto;font:14px/1.65 'Microsoft YaHei',sans-serif;color:#252525}}h1{{font-size:25px;color:#1a2b4a;margin-bottom:4px}}h2{{font-size:16px;color:#1a2b4a;margin:12px 0 4px}}p{{margin:6px 0}}table{{border-collapse:collapse;width:100%;font-size:12px}}td,th{{padding:5px 7px;border-bottom:1px solid #d8d8d8;text-align:left}}th{{background:#eef1f6}}.meta{{color:#52647d;font-size:12px}}.box{{border-left:4px solid #c8861a;background:#f5f4f1;padding:8px 12px}}a{{color:#1a2b4a}}@media print{{body{{font-size:10px;margin:0}}h1{{font-size:21px}}h2{{font-size:13px;margin-top:8px}}table{{font-size:9px}}td,th{{padding:3px 5px}}.meta{{font-size:9px}}}}
</style><h1>NOAA GHCN-Daily 气象数据源卡</h1><p class="meta">线 B / C · 负责人：黄祉玥 · 原始宽表复核：{DATE}</p>
<h2>来源、获取与规模</h2><p>NOAA/NCEI提供的站点日值。初始调查记录经官方HTTPS按站下载，无需密钥；CDO API另需Token。现有58个宽表文件（56个CSV、2个以.csv结尾的XLSX），共946,693行、75.33MB；一组文件完全相同，按文件SHA排重后73.84MB。识别57个不同真实站号、59个城市—站点组合。这里只计原始宽表。</p>
<h2>实际时空覆盖</h2><p>五城宽表1900-01-01–1960-01-01，华盛顿个别站延至1995-12-21。最初50km是计划；按站点目录坐标及NHGIS城市点核算，17个城市—站点组合超过50km，全部在100km内。当前Q3使用1915–1922＋1930–1932，每城575周，含1933-01-01边界标签。</p><table><tr>{th}</tr>{tr}</table>
<h2>字段与日转周</h2><table><tr><th>字段</th><th>口径</th></tr><tr><td>city / sunday_date / week_end</td><td>城市×周日起始标签；周末为其后第6天（周六）。</td></tr><tr><td>tavg_avg / tmax_avg / tmin_avg</td><td>站内周均后跨站平均；TAVG缺失用同日(TMAX+TMIN)/2回退。</td></tr><tr><td>prcp_sum / snow_sum</td><td>先计算各站该周有效观测日的日均降水/降雪，再对站点取平均；不是周累计量。SNOW不是雪深。</td></tr><tr><td>n_days / n_stations</td><td>站周有效天数的跨站均值（1位小数）/该周参与汇总站点数；不等同每个要素的有效站数。</td></tr></table>
<p><b>单位与缺失：</b>12个本地日值与官方原生记录换算吻合，支持温度°F、日均降水/雪in/day解释；原始导出配置尚未附。气象缺值保留NA，真实0保留0。三温度各3450有效值，降水3449、降雪3112。</p>
<h2>使用结论与局限</h2><div class="box">可用于当前窗口标准化关联分析。原始宽表重算与交接周表的气象值最大差0.01，站数、有效天数一致。纽约1950年后两个特殊格式文件影响窗口外周值，需另行修订。57/58宽表未保留显式质量/属性列，不能宣称逐项QFLAG质控完成。原始下载日期、订单参数及原清洗脚本仍待补；原始宽表约75.33MB，不能以转换文件扩大采集量。</div>
<p class="meta"><a href="NOAA_source_card.md">详细源卡</a> · <a href="补充材料/field_dictionary.csv">字段字典</a> · <a href="补充材料/station_city_mapping.csv">六城映射与站距</a> · <a href="补充材料/raw_file_manifest.csv">原始宽表清单</a> · <a href="补充材料/collection_record.md">采集与复核记录</a> · <a href="补充材料/unit_sample_comparison.csv">单位比对</a> · <a href="{OFFICIAL}">官方说明</a></p></html>'''
    (OUT/'NOAA_one_page.html').write_text(page,encoding='utf-8')
    record=f'''# NOAA 采集与复核记录

- 原始下载日未记录；初始调查表第1、4部分记录数据源、负责人和HTTPS按站下载方案。调查第5部分的规模项为空，现以实测补齐。第6部分旧连接方案不作为当前口径。
- {DATE}：读取用户提供的原始zip，仅以58个宽表统计采集量；SHA256为{audit['zip_sha256']}。读取全部946,693行，识别2个伪CSV/XLSX、1组完全相同文件、57个全局站号；不修改原始包。
- 同日：用原包站点目录核实六城坐标，NHGIS城市点位作距离参考；59个城市—站点组合中17个>50km，0个>100km。
- 同日：官方USC00475474.dly的1947-01前三日4要素与本地12值按英制换算匹配；证据保存在official_unit_sample.json和unit_sample_comparison.csv。官方单位定义见{OFFICIAL}。
- 同日：独立按真站号/周聚合及缺TAVG回退复核；当前窗口气象最大差0.01，站数/天数一致。纽约1950年后的特殊格式站点导致窗口外差异，未用本次源卡修订覆盖旧清洗表或改变Q3数值。
- 本卡生成依赖raw_audit.json和配套证据CSV；原始包可另存，无需重复解压。原始清洗代码未取得，本次审计不是原脚本的字节复现。
'''
    (OUT/'collection_record.md').write_text(record,encoding='utf-8')
    from organize_analysis import organize_folder
    organize_folder(ROOT,'noaa_source_card')


if __name__=='__main__':make_card()
