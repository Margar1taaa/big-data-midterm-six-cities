# -*- coding: utf-8 -*-
"""用 renderer_gap_data.json 生成 renderer HTML 代码片段（嵌入回复用）。"""
import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
D = PROJECT_ROOT / "analysis" / "descriptive"
with open(os.path.join(D, "renderer_gap_data.json"), encoding="utf-8") as f:
    data = json.load(f)

CITY_ZH = {"BALTIMORE": "巴尔的摩", "CLEVELAND": "克利夫兰", "LOS ANGELES": "洛杉矶",
           "MILWAUKEE": "密尔沃基", "NEW YORK": "纽约", "WASHINGTON": "华盛顿"}
DIS_ZH = {"DIPHTHERIA": "白喉", "INFLUENZA": "流感", "POLIOMYELITIS": "脊灰"}
EV_ZH = {"CASES": "病例", "DEATHS": "死亡"}

print("RENDERER_ROWS=%d" % len(data["rows"]))
# 输出紧凑 JS 数组供手写嵌入
js = "var ROWS=" + json.dumps(data["rows"], ensure_ascii=False) + ";"
print(js)
