"""Keep the result folders concise; retain supplementary artifacts for review."""
from pathlib import Path
import argparse
import html
import json
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
SUPPORT="补充材料"
KEEP={"q3":{"Q3_one_page.html","Q3_report.md","q3_core.png","q3_city_comparison.png","correlations.csv"},
      "noaa_source_card":{"NOAA_one_page.html","NOAA_source_card.md"}}


def organize_folder(root,folder):
    base=(root/"analysis"/folder).resolve()
    support=base/SUPPORT
    support.mkdir(exist_ok=True)
    for p in list(base.iterdir()):
        if p.is_file() and p.name not in KEEP[folder]:
            dest=(support/p.name).resolve()
            assert dest.is_relative_to(base) and p.resolve().is_relative_to(base)
            # Only replace a prior generated copy of this same file.
            try:
                if dest.exists():
                    dest.write_bytes(p.read_bytes());p.unlink()
                else:shutil.move(str(p),str(dest))
            except PermissionError as exc:
                if getattr(exc,"winerror",None) not in (32,33):raise
                # An open Excel workbook can prevent removing the original.
                shutil.copyfile(p,dest)
                print("File is open; supplementary copy saved, original retained:",p.name)
    names={p.name for p in support.iterdir() if p.is_file()}
    for p in base.iterdir():
        if not p.is_file() or p.suffix not in (".html",".md"):continue
        s=p.read_text(encoding="utf-8")
        for name in names:
            # Relative links and code-formatted file references; avoid repeating prefixes.
            s=s.replace(f'href="{name}"',f'href="{SUPPORT}/{name}"')
            s=s.replace(f']({name})',f']({SUPPORT}/{name})')
            s=s.replace(f'`{name}`',f'`{SUPPORT}/{name}`')
        s=s.replace("字段单位、PRCP/SNOW 的跨站聚合顺序和原始质量标志处理不能由当前包完整验证",
                    "PRCP/SNOW已确认先按各站该周有效日求日均、再跨站平均，不是周累计量；字段单位和原始质量标志处理仍待补证")
        s=s.replace("原始单位与日转周细节仍待原作者补证","降水/降雪采用先站内有效日均、再跨站平均；原始单位等细节仍待补证")
        p.write_text(s,encoding="utf-8")


def overview(root):
    rows="".join(f"<tr><td>{d}</td><td>{a}</td><td>{b}</td><td>{t}</td></tr>" for d,a,b,t in [
        ("流感","−0.260","−0.164","较弱负关联，量级对病例取对数敏感"),
        ("脊灰","+0.277","+0.074","调整后明显减弱"),
        ("白喉","−0.371","−0.047","调整后接近零")])
    page=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>Q3与NOAA源卡 · 结果总览</title><style>
body{{font:15px/1.75 "Microsoft YaHei",sans-serif;color:#252525;background:#f4f4f4;margin:0}}main{{max-width:1040px;margin:30px auto;padding:0 20px}}h1,h2{{color:#1a2b4a}}h1{{font-size:28px}}h2{{font-size:20px;margin-top:0}}section{{background:white;border:1px solid #d8d8d8;border-radius:10px;padding:22px;margin:18px 0}}a{{color:#1a2b4a}}.button{{display:inline-block;background:#1a2b4a;color:white;padding:8px 16px;border-radius:5px;text-decoration:none;margin-right:10px}}table{{width:100%;border-collapse:collapse;font-size:14px}}td,th{{text-align:left;padding:9px;border-bottom:1px solid #ddd}}th{{background:#eef1f6}}img{{width:100%;margin-top:15px}}.note{{color:#52647d;font-size:13px}}summary{{cursor:pointer;color:#52647d}}</style>
<main><h1>Q3 与 NOAA 气象源卡：结果总览</h1><p class="note">先看结论与一页材料；系数、方法和溯源材料可按需展开。</p>
<section><h2>任务 3｜气候与疫情关联</h2><a class="button" href="q3/Q3_one_page.html">查看一页结果</a><a href="q3/Q3_report.md">完整报告</a> · <a href="q3/correlations.csv">主相关系数表</a>
<p>平均温度与三病种的周值相关性有明显季节性。控制各城月份与年份后，脊灰、白喉关联减弱；流感仍有较弱负关联。降水未见稳定证据，降雪关联调整后减弱。结果仅支持关联判断。</p>
<table><tr><th>病种</th><th>主分析 r</th><th>调整后 r</th><th>解读</th></tr>{rows}</table><img src="q3/q3_core.png" alt="分病种气候疫情核心图">
<p><a href="q3/q3_city_comparison.png">六城分层对比图</a></p>
<details><summary>补充表格与复核文件</summary><p><a href="q3/补充材料/city_correlations.csv">城市分层系数</a> · <a href="q3/补充材料/sensitivity_comparison.csv">敏感性明细（含主分析对照）</a></p><p class="note">原始敏感性表、汇总表、中间数据、样本数、矢量图及核验记录保存在 q3/补充材料；日常查看无需逐一打开。</p></details></section>
<section><h2>线 B｜NOAA 气象源卡</h2><a class="button" href="noaa_source_card/NOAA_one_page.html">查看一页源卡</a><a href="noaa_source_card/NOAA_source_card.md">详细源卡</a>
<p>降水、降雪采用周内日均口径：先对各站该周有效观测日求日均，再对站点取平均，不是周累计量。站点数用于描述每周参与汇总的站点覆盖。</p><details><summary>字段、映射与采集依据</summary><p><a href="noaa_source_card/补充材料/field_dictionary.csv">字段字典</a> · <a href="noaa_source_card/补充材料/station_city_mapping.csv">站点映射</a> · <a href="noaa_source_card/补充材料/coverage_by_city.csv">覆盖统计</a> · <a href="noaa_source_card/补充材料/collection_record.md">采集记录</a></p></details></section>
<p class="note">更多口径及待补项：<a href="../docs/GAPS.md">GAPS</a>。文件整理仅调整展示和路径，分析数值不变。</p></main></html>'''
    (root/"analysis/结果总览.html").write_text(page,encoding="utf-8")


def organize(root=ROOT):
    for name in KEEP:organize_folder(root,name)
    overview(root)


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path,default=ROOT);args=ap.parse_args()
    organize(args.root.resolve())
    print("Result folders organized; supplementary artifacts retained.")
