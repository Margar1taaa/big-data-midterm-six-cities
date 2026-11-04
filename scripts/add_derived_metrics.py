# -*- coding: utf-8 -*-
"""为六城融合表添加两个派生指标列（默认 dry-run，不写文件）。

指标定义（口径已与小组确认）：
  1) np_<dis>_rate        报刊周命中率(%) = 该周该城强词命中页数 / 该周扫描页数 * 100
  2) <dis>_rate_per100k   人均发病率(每10万人口) = 该周病例数 / 人口 * 100000

NA 规则：任一输入为 NA/空 则结果 NA（不补 0）；np_pages<=0 时命中率记 NA。

用法：
  python add_derived_metrics.py            # dry-run：只打印统计与样例，不写文件
  python add_derived_metrics.py --write    # 落盘：在融合表追加 6 列并保存
"""
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "data" / "integrated" / "weekly_sixcities_1915_1922_1930_1932.csv"

NEW_COLS = [
    "np_flu_rate", "np_polio_rate", "np_diph_rate",
    "flu_rate_per100k", "diph_rate_per100k", "polio_rate_per100k",
]


def fnum(x):
    if x is None:
        return None
    s = str(x).strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def compute(row):
    out = {}
    pages = fnum(row.get("np_pages"))
    for dis in ("flu", "polio", "diph"):
        hits = fnum(row.get(f"np_{dis}_hits")) or 0.0
        out[f"np_{dis}_rate"] = round(hits / pages * 100, 2) if pages and pages > 0 else None
    pop = fnum(row.get("population"))
    for dis in ("flu", "diph", "polio"):
        cases = fnum(row.get(f"{dis}_cases"))
        out[f"{dis}_rate_per100k"] = (
            round(cases / pop * 100000, 2) if cases is not None and pop else None
        )
    return out


def main():
    write = "--write" in sys.argv
    with open(SRC, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        hdr = list(reader.fieldnames)
        rows = list(reader)

    # 重复执行保护：已有新列则拒绝
    dup = [c for c in NEW_COLS if c in hdr]
    if dup:
        print(f"ALREADY_EXISTS {dup} -> 已含派生列，跳过（如需重算请先删除对应列）")
        return

    # 先算（纯函数），dry-run 不落盘
    computed = [compute(r) for r in rows]

    if not write:
        print(f"DRY-RUN  rows={len(rows)}  cols={len(hdr)} -> +{len(NEW_COLS)} = {len(hdr)+len(NEW_COLS)}")
        print("NEW_COLS=", NEW_COLS)
        for col in NEW_COLS:
            vals = [c[col] for c in computed if c[col] is not None]
            if vals:
                print(f"  {col}: nonnull={len(vals)} min={min(vals)} max={max(vals)} mean={sum(vals)/len(vals):.2f}")
            else:
                print(f"  {col}: nonnull=0 (全部 NA)")
        print("SAMPLE (前3行):")
        for r, c in zip(rows[:3], computed[:3]):
            print("  city=%s date=%s pages=%s flu_hits=%s pop=%s" % (
                r.get("city"), r.get("sunday_date"), r.get("np_pages"),
                r.get("np_flu_hits"), r.get("population")))
            print("    -> " + "  ".join(f"{k}={c[k]}" for k in NEW_COLS))
        print("NOT_WRITTEN: 使用 --write 落盘")
        return

    # 落盘：保持 utf-8-sig（Excel 兼容），追加列
    with open(SRC, encoding="utf-8-sig", newline="") as f:
        # 读取原始行序，二次打开用文本模式重写
        pass
    with open(SRC, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        orig = list(reader)
    new_hdr = orig[0] + NEW_COLS
    new_rows = []
    for i, line in enumerate(orig[1:]):
        new_rows.append(line + ["" if computed[i][c] is None else str(computed[i][c]) for c in NEW_COLS])
    with open(SRC, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(new_hdr)
        w.writerows(new_rows)
    print(f"WRITTEN rows={len(new_rows)} cols={len(new_hdr)} -> {SRC}")


if __name__ == "__main__":
    main()
