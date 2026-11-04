# -*- coding: utf-8 -*-
"""生成 renderer 代码块（缺口矩阵），读 renderer_gap_data.json。"""
import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
D = PROJECT_ROOT / "analysis" / "descriptive"
with open(os.path.join(D, "renderer_gap_data.json"), encoding="utf-8") as f:
    data = json.load(f)

rows_js = json.dumps(data["rows"], ensure_ascii=False)
print("LEN=%d" % len(rows_js))
