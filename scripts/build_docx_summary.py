# -*- coding: utf-8 -*-
"""生成《六城数据描述性统计分析》Word 文档（无模板创建，python-docx）。"""
import os
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor, Twips
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE = PROJECT_ROOT / "analysis" / "descriptive"
IMG = os.path.join(BASE, "_imgs")
OUT = os.path.join(BASE, "六城数据描述性统计分析.docx")

BLACK = RGBColor(0, 0, 0)
GRAY_HEAD = "D9D9D9"


def set_font(run, cn="宋体", en="Times New Roman", size=12, bold=False, color=BLACK):
    run.font.name = en
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), cn)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def add_para(doc, text, cn="宋体", size=12, bold=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
             first_indent=True, before=0, after=0, line=1.5, color=BLACK):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = align
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    if first_indent:
        pf.first_line_indent = Pt(size * 2)
    else:
        pf.first_line_indent = Pt(0)
    r = p.add_run(text)
    set_font(r, cn=cn, size=size, bold=bold, color=color)
    return p


def add_heading(doc, text, level=1):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf.first_line_indent = Pt(0)
    if level == 1:
        pf.space_before = Pt(14)
        pf.space_after = Pt(6)
        pf.line_spacing = 1.5
        r = p.add_run(text)
        set_font(r, cn="黑体", size=16, bold=True)
    else:
        pf.space_before = Pt(11)
        pf.space_after = Pt(5)
        pf.line_spacing = 1.5
        r = p.add_run(text)
        set_font(r, cn="黑体", size=14, bold=True)
    return p


def add_caption(doc, text):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf.first_line_indent = Pt(0)
    pf.space_before = Pt(4)
    pf.space_after = Twips(360)
    pf.line_spacing = 1.0
    r = p.add_run(text)
    set_font(r, cn="宋体", size=10.5)
    return p


def add_source(doc, text):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf.first_line_indent = Pt(0)
    pf.space_after = Twips(360)
    pf.line_spacing = 1.5
    r = p.add_run(text)
    set_font(r, cn="宋体", size=10.5)
    return p


def add_fig(doc, path, width_cm, caption, source):
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.keep_with_next = True
    run = p.add_run()
    run.add_picture(path, width=Cm(width_cm))
    cp = add_caption(doc, caption)
    cp.paragraph_format.keep_with_next = True
    add_source(doc, source)


def set_cell(cell, text, bold=False, align="left"):
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    p = cell.paragraphs[0]
    pf = p.paragraph_format
    pf.first_line_indent = Pt(0)
    pf.left_indent = Pt(0)
    pf.right_indent = Pt(0)
    pf.space_before = Pt(2)
    pf.space_after = Pt(2)
    pf.line_spacing = 1.0
    if align == "center":
        pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "right":
        pf.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    else:
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(text)
    set_font(r, cn="宋体", size=10.5, bold=bold)


def shade_cell(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcolor)
    vAlign = tcPr.find(qn("w:vAlign"))
    if vAlign is not None:
        vAlign.addprevious(shd)
    else:
        tcPr.append(shd)


def row_no_split(row):
    trPr = row._tr.get_or_add_trPr()
    cs = OxmlElement("w:cantSplit")
    trPr.append(cs)


def row_header(row):
    trPr = row._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader")
    trPr.append(th)


def add_table(doc, headers, rows, widths_cm, aligns):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.autofit = False
    tbl = table._tbl
    tblPr = tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblLook = tblPr.find(qn("w:tblLook"))
    if tblLook is not None:
        tblLook.addprevious(layout)
    else:
        tblPr.append(layout)
    hdr = table.rows[0]
    row_header(hdr)
    row_no_split(hdr)
    for i, h in enumerate(headers):
        set_cell(hdr.cells[i], h, bold=True, align="center")
        shade_cell(hdr.cells[i], GRAY_HEAD)
    for rdata in rows:
        r = table.add_row()
        row_no_split(r)
        for i, val in enumerate(rdata):
            set_cell(r.cells[i], val, align=aligns[i])
    for i, w in enumerate(widths_cm):
        for cell in table.columns[i].cells:
            cell.width = Cm(w)
    return table


def add_table_caption(doc, text):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf.first_line_indent = Pt(0)
    pf.space_before = Pt(6)
    pf.space_after = Pt(4)
    pf.line_spacing = 1.0
    pf.keep_with_next = True
    r = p.add_run(text)
    set_font(r, cn="宋体", size=10.5)
    return p


def add_page_number_footer(doc):
    section = doc.sections[0]
    footer = section.footer
    p = footer.paragraphs[0]
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = "1"
    r.append(t)
    fld.append(r)
    p._p.append(fld)


doc = Document()

# 页面：A4、2.5cm 边距
sec = doc.sections[0]
sec.page_width = Cm(21.0)
sec.page_height = Cm(29.7)
sec.top_margin = Cm(2.5)
sec.bottom_margin = Cm(2.5)
sec.left_margin = Cm(2.5)
sec.right_margin = Cm(2.5)

# Normal 样式
st = doc.styles["Normal"]
st.font.name = "Times New Roman"
st.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
st.font.size = Pt(12)
st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
st.paragraph_format.line_spacing = 1.5
st.paragraph_format.space_before = Pt(0)
st.paragraph_format.space_after = Pt(0)

add_page_number_footer(doc)

# ===== 标题 =====
tp = doc.add_paragraph()
tp.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
tp.paragraph_format.first_line_indent = Pt(0)
tp.paragraph_format.space_after = Pt(18)
r = tp.add_run("六城数据描述性统计分析")
set_font(r, cn="黑体", size=18, bold=True)

sp = doc.add_paragraph()
sp.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
sp.paragraph_format.first_line_indent = Pt(0)
sp.paragraph_format.space_after = Pt(12)
r = sp.add_run("大数据原理与应用·中期大作业数据采集阶段（研究窗口 1916–1953）")
set_font(r, cn="楷体", size=12)

# ===== 1 摘要 =====
add_heading(doc, "1 摘要", 1)
add_para(doc,
    "本项目以 1916–1953 年为研究窗口，围绕流感、白喉、脊灰三种疫情采集 Tycho 疫情记录、"
    "NOAA 气象、普查卷人口与报刊 OCR 四类数据。疫情数据清洗后为 40,318 条周记录（30 个城—病—事件组合），"
    "气象数据 20,655 周，人口数据覆盖 1910–1950 五次普查，报刊 OCR 合计 299,358 页。主要缺口集中在两处："
    "流感缺 1916–1919 与 1949–1953；白喉、脊灰死亡数据 1924 年后系统性缺失。报刊按设计覆盖 1915–1922 与 1930–1932 两段，"
    "1923–1929 与 1933–1953 为设计未采集。全部缺口已登记于 docs/GAPS.md（G1–G10），后续按补源或调整研究窗口处置。")

# ===== 2 数据规模总览 =====
add_heading(doc, "2 数据规模总览", 1)
add_para(doc,
    "四类数据的原始规模、清洗后规模与覆盖范围见表 1。清洗后的疫情与气象数据均以自然周（周日起始）为统一时间主键，"
    "可直接按城—周融合。")
add_table_caption(doc, "表 1　数据规模总览")
add_table(doc,
    ["数据源", "原始规模", "清洗后规模", "覆盖范围"],
    [
        ["Tycho 疫情记录", "2,934,886 行 / 33 病种", "40,318 周行 / 30 组合", "1900–1960（周）"],
        ["NOAA 气象", "58 个站点文件", "20,655 周", "1899–1959（华盛顿至 1995）"],
        ["人口（普查卷）", "6 城市", "30 条（6 城 × 5 普查年）", "1910–1950 普查"],
        ["报刊 OCR", "三小城 32,036 页；大三城 zip 267,322 页", "关键词命中 2,030 页", "1915–1922 / 1930–1932（设计两段）"],
    ],
    [3.0, 4.6, 4.2, 4.2],
    ["left", "left", "left", "left"])

# ===== 3 疫情数据 Tycho =====
add_heading(doc, "3 疫情数据（Tycho）", 1)
add_para(doc,
    "原始表含 2,934,886 行、33 种疾病记录，时间跨 1900–1960；清洗后按“城—病—事件—周”聚合为 40,318 行、"
    "30 个组合（脊灰死亡因数据源无该事件，6 组缺失不计入）。三病年合计趋势见图 1–图 3：流感以 1919 年纽约峰值最高"
    "（单周峰值 30,456 例），其后呈周期性波动；白喉于 1920 年代达峰后长期下降；脊灰在 1940 年代后期明显抬升。")
add_fig(doc, os.path.join(IMG, "fig_flu.png"), 14,
    "图 1　六城流感病例年合计（对数轴）",
    "数据来源：Tycho Project 疫情记录（cleaned_tycho_weekly_sixcities.csv），据原始数据整理。")
add_fig(doc, os.path.join(IMG, "fig_diph.png"), 14,
    "图 2　六城白喉病例年合计",
    "数据来源：Tycho Project 疫情记录（cleaned_tycho_weekly_sixcities.csv），据原始数据整理。")
add_fig(doc, os.path.join(IMG, "fig_polio.png"), 14,
    "图 3　六城脊灰病例年合计",
    "数据来源：Tycho Project 疫情记录（cleaned_tycho_weekly_sixcities.csv），据原始数据整理。")
add_para(doc,
    "各组合的实际覆盖窗口与主要缺口见表 2。")
add_table_caption(doc, "表 2　Tycho 覆盖窗口与主要缺口")
add_table(doc,
    ["病种·事件", "覆盖区间", "主要缺口"],
    [
        ["流感·病例", "1920–1948（纽约 1919 起）", "缺 1916–1919、1949–1953；密尔沃基止于 1947"],
        ["流感·死亡", "1920–1948", "缺 1916–1919、1949–1953；密尔沃基 1921–1922 断档"],
        ["白喉·病例", "1906–1953（华盛顿止 1952）", "六城一致缺 1949–1951"],
        ["白喉·死亡", "1900–1923", "1924–1953 全部缺失"],
        ["脊灰·病例", "1912 / 1916–1953", "缺 1949–1951；华盛顿缺 1913、1919–1920；巴尔的摩缺 1913–1914"],
        ["脊灰·死亡", "无", "数据源无该事件"],
    ],
    [2.8, 4.6, 8.6],
    ["left", "left", "left"])

# ===== 4 气象数据 NOAA =====
add_heading(doc, "4 气象数据（NOAA）", 1)
add_para(doc,
    "58 个站点文件清洗为 20,655 周。除华盛顿外五城在 1899-12-31 至 1959-12-27 间均满 3,131 周、无缺失；"
    "华盛顿记录延至 1995 年（5,000 周，缺 8 周）。各城平均参与站点数为 3.4–9.6 个（华盛顿最少、巴尔的摩最多），"
    "周均气温趋势见图 4。")
add_fig(doc, os.path.join(IMG, "fig_tavg.png"), 14,
    "图 4　NOAA 六城周均气温趋势",
    "数据来源：NOAA 全球历史气候网络（GHCN-D），据原始数据整理。")

# ===== 5 人口数据（普查卷） =====
add_heading(doc, "5 人口数据（Census 普查卷）", 1)
add_para(doc,
    "六城中心点坐标经核验偏差小于 1.3 km；人口取 1910、1920、1930、1940、1950 五次普查共 30 条记录。"
    "洛杉矶 1910–1930 增长最快（十年增速最高 114.7%），纽约 1950 年人口 789 万为六城最大（图 5）。")
add_fig(doc, os.path.join(IMG, "fig_pop.png"), 14,
    "图 5　六城人口（1910–1950，普查卷）",
    "数据来源：美国 Census Bureau《1950 Census of Population, Volume I》Table 4，据原始数据整理。")

# ===== 6 报刊数据 =====
add_heading(doc, "6 报刊数据", 1)
add_para(doc,
    "三小城 6 家报纸共 32,036 页，关键词命中流感 1,618 页、脊灰 324 页、白喉 88 页；命中率最高为 La Prensa"
    "（流感 16.8%）与 Cleveland Gazette（流感 12.3%），德文报命中率偏低（约 2.5%，词表以英文为主）。"
    "各报覆盖与命中情况见表 3，命中率见图 6。")
add_fig(doc, os.path.join(IMG, "fig_hit.png"), 14,
    "图 6　三小城报刊关键词命中率",
    "数据来源：Chronicling America OCR 母集关键词检索，据原始数据整理。")
add_para(doc,
    "大三城报刊以 zip 压缩包存放（直接流式读取、不落地解压），4 家报纸合计 267,322 页：Evening Star 148,432 页、"
    "New-York Tribune 75,355 页、Milwaukee Leader 39,381 页、Daily Worker 4,154 页。按原定采集窗口，"
    "Tribune 覆盖 1915–1922，其余报纸覆盖 1915–1922 与 1930–1932 两段；1923–1929 与 1933–1953 为设计未采集。")
add_table_caption(doc, "表 3　报刊覆盖与命中明细")
add_table(doc,
    ["报纸", "城市", "页数", "年份", "备注"],
    [
        ["Der Deutsche Correspondent", "巴尔的摩", "10,612", "1915–1917", "流感命中 2.5%"],
        ["Telegraf", "巴尔的摩", "3,314", "1918–1932", "流感命中 1.6%"],
        ["The Gazette", "克利夫兰", "2,296", "1915–1932", "流感命中 12.3%"],
        ["California Eagle", "洛杉矶", "662", "1915–1930", "流感命中 5.9%"],
        ["La Opinion", "洛杉矶", "13,510", "1930–1932", "流感命中 5.2%"],
        ["La Prensa", "洛杉矶", "1,642", "1917–1922", "流感命中 16.8%"],
        ["Evening Star", "华盛顿", "148,432", "1915–1922 / 1930–1931", "设计未采 1923–1929"],
        ["New-York Tribune", "纽约", "75,355", "1915–1922", "—"],
        ["Milwaukee Leader", "密尔沃基", "39,381", "1915–1922 / 1930–1931", "设计未采 1923–1929"],
        ["Daily Worker", "纽约", "4,154", "1930–1932", "覆盖 1930–1932 段"],
    ],
    [3.4, 1.9, 2.2, 2.6, 5.9],
    ["left", "left", "right", "center", "left"])

# ===== 7 数据覆盖缺口 =====
add_heading(doc, "7 数据覆盖缺口", 1)
add_para(doc,
    "图 7 给出六城 × 三病 × 两事件在 1916–1953 年的逐年覆盖矩阵（脊灰死亡全部缺失，未列入）。")
add_fig(doc, os.path.join(IMG, "fig_gap.png"), 13.5,
    "图 7　数据覆盖缺口矩阵（1916–1953 逐年）",
    "数据来源：Tycho Project 疫情记录（cleaned_tycho_weekly_sixcities.csv），据原始数据整理。")
add_para(doc,
    "系统性缺口共六条：第一，流感病例与死亡：六城均缺 1916–1919（含 1918 大流感）与 1949–1953，密尔沃基病例止于 1947；"
    "第二，白喉病例：六城一致缺 1949–1951，华盛顿另缺 1953；第三，白喉死亡：1924–1953 六城全部缺失；"
    "第四，脊灰病例：六城一致缺 1949–1951，华盛顿另缺 1913、1919–1920，巴尔的摩缺 1913–1914；"
    "第五，脊灰死亡：数据源本身无该事件，全部缺失；第六，报刊按设计覆盖 1915–1922 与 1930–1932 两段，"
    "1923–1929 与 1933–1953 为设计未采集（非缺失）。")
add_para(doc,
    "综上，1920–1948 为疫情与气象组合最完整的融合窗口；报刊作为补充证据源覆盖设计内两段（含 1918 大流感与 1930–31 流感季）。"
    "报刊数据量远超单源 80% 占比限制，已获助教豁免（G7），缺口按“先标记、后续补源或调整窗口”处理。")

# ===== 8 口径与文件说明 =====
add_heading(doc, "8 口径与文件说明", 1)
add_para(doc,
    "清洗口径、字段说明与过程脚本见 data/cleaned/README.md 与 docs/GAPS.md（G1–G10）；"
    "上述全部统计可由 scripts/ 目录脚本复现；原始数据按 raw→cleaned→integrated 三层目录组织，"
    "各层按数据源分子目录（tycho / noaa / nhgis / newspaper）。")

doc.save(OUT)
print("SAVED", OUT)
