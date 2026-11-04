# -*- coding: utf-8 -*-
"""把 report_data.json 注入 report_template.html -> descriptive_report.html。"""
import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
D = PROJECT_ROOT / "analysis" / "descriptive"
tpl = os.path.join(D, "report_template.html")
data_f = os.path.join(D, "report_data.json")
out_f = os.path.join(D, "descriptive_report.html")

with open(tpl, encoding="utf-8") as f:
    html = f.read()
with open(data_f, encoding="utf-8") as f:
    data = json.load(f)

payload = json.dumps(data, ensure_ascii=False)
payload = payload.replace("</", "<\\/")
html = html.replace("__DATA_JSON__", payload)

with open(out_f, "w", encoding="utf-8") as f:
    f.write(html)
print("HTML_BYTES=%d" % len(html.encode("utf-8")))
print("OK")
