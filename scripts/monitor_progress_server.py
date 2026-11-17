# -*- coding: utf-8 -*-
"""
monitor_progress_server.py
ZIP 批次报刊扫描实时进度条页面服务（本地，仅供进度查看）。

启动：python scripts/monitor_progress_server.py [端口]
浏览器打开 http://127.0.0.1:8765/ 即可看到实时进度条（每 2 秒自动刷新）。
数据源：data\\cleaned\\newspaper\\scan_progress.json（由 scan_newspaper_zip.py 写入）
"""
import http.server
import json
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROGRESS = PROJECT_ROOT / "data" / "cleaned" / "newspaper" / "scan_progress.json"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765

HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>ZIP 批次报刊扫描进度</title>
<style>
  body { font-family: "Segoe UI", "Microsoft YaHei", sans-serif; background:#f4f6f9;
         display:flex; align-items:center; justify-content:center; min-height:100vh; margin:0; }
  .card { width:560px; background:#fff; border-radius:14px; box-shadow:0 6px 24px rgba(0,0,0,.10);
          padding:34px 40px; }
  h1 { font-size:17px; color:#1a2b4a; margin:0 0 6px; }
  .sub { font-size:12px; color:#767676; margin:0 0 22px; }
  .pct { font-size:52px; font-weight:700; color:#1a2b4a; margin:6px 0 14px; }
  .bar { height:20px; background:#e4e8ee; border-radius:10px; overflow:hidden; }
  .bar > div { height:100%; width:0%; background:linear-gradient(90deg,#52647d,#1a2b4a);
               border-radius:10px; transition:width .8s ease; }
  .meta { display:flex; justify-content:space-between; font-size:13px; color:#52647d;
          margin-top:14px; }
  .meta b { color:#1a2b4a; font-weight:600; }
  .done { color:#1a7f3d; font-size:16px; font-weight:600; margin-top:18px; }
</style>
</head>
<body>
<div class="card">
  <h1>ZIP 批次报刊 OCR 关键词扫描（zip 直读）</h1>
  <p class="sub">New York / Washington / Milwaukee · 词表 v2 · 按页数口径</p>
  <div class="pct" id="pct">--</div>
  <div class="bar"><div id="fill"></div></div>
  <div class="meta">
    <span>已处理 <b id="proc">--</b> / <b id="total">--</b> 页</span>
    <span>速率 <b id="rate">--</b> 页/秒</span>
    <span>预计剩余 <b id="eta">--</b> 分钟</span>
  </div>
  <div class="done" id="done" style="display:none">扫描完成 ✓</div>
</div>
<script>
async function tick(){
  try{
    const r = await fetch('/progress');
    const d = await r.json();
    const pct = Math.min(100, +(d.pct||0));
    document.getElementById('pct').textContent = pct.toFixed(1) + '%';
    document.getElementById('fill').style.width = pct + '%';
    document.getElementById('proc').textContent = (d.processed||0).toLocaleString();
    document.getElementById('total').textContent = (d.total||0).toLocaleString();
    document.getElementById('rate').textContent = (d.rate||0).toFixed(1);
    const eta = Math.max(0, Math.round((d.eta||0)/60));
    document.getElementById('eta').textContent = eta;
    if(pct>=100) document.getElementById('done').style.display='block';
  }catch(e){}
}
tick(); setInterval(tick, 1000);
</script>
</body>
</html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/progress"):
            try:
                with open(PROGRESS, encoding="utf-8") as f:
                    data = f.read()
            except Exception:
                data = "{}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data.encode("utf-8"))
        else:
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("SERVE http://127.0.0.1:%d/" % PORT, flush=True)
    srv.serve_forever()
