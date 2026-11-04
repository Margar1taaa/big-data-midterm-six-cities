# -*- coding: utf-8 -*-
"""从 coverage_gaps_matrix.csv 生成 renderer 内联数据（每行 1916-1953 覆盖 0/1）。"""
import csv
import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
D = PROJECT_ROOT / "analysis" / "descriptive"
WINDOW = (1916, 1953)

rows = []
with open(os.path.join(D, "coverage_gaps_matrix.csv"), encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        if r["event"] == "DEATHS" and r["disease"] == "POLIOMYELITIS":
            continue  # 全缺，单独说明
        present = set(int(x) for x in r["all_years"].split(";") if x.isdigit())
        cells = []
        for y in range(WINDOW[0], WINDOW[1] + 1):
            cells.append(1 if y in present else 0)
        rows.append({"c": r["city"], "d": r["disease"], "e": r["event"], "cells": cells})

with open(os.path.join(D, "renderer_gap_data.json"), "w", encoding="utf-8") as f:
    json.dump({"window": WINDOW, "rows": rows}, f, ensure_ascii=False)
print("ROWS=%d" % len(rows))
print(json.dumps(rows, ensure_ascii=False)[:400])
