# -*- coding: utf-8 -*-
"""用 playwright 对 HTML 中的图表元素截图（供 Word 文档插图）。"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
D = PROJECT_ROOT / "analysis" / "descriptive"
OUT = os.path.join(D, "_imgs")
os.makedirs(OUT, exist_ok=True)

TARGETS = [
    (os.path.join(D, "descriptive_report.html"), "#ch_flu", "fig_flu.png"),
    (os.path.join(D, "descriptive_report.html"), "#ch_diph", "fig_diph.png"),
    (os.path.join(D, "descriptive_report.html"), "#ch_polio", "fig_polio.png"),
    (os.path.join(D, "descriptive_report.html"), "#ch_tavg", "fig_tavg.png"),
    (os.path.join(D, "descriptive_report.html"), "#ch_pop", "fig_pop.png"),
    (os.path.join(D, "descriptive_report.html"), "#ch_hit", "fig_hit.png"),
    (os.path.join(D, "gap_matrix.html"), "#mx", "fig_gap.png"),
]


def shot():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = None
        for kwargs in ({}, {"channel": "msedge"}, {"channel": "chrome"}):
            try:
                browser = p.chromium.launch(**kwargs)
                break
            except Exception:
                continue
        if browser is None:
            print("NO_BROWSER")
            return 1
        page = browser.new_page(viewport={"width": 1280, "height": 1000},
                                device_scale_factor=2)
        for html_path, sel, name in TARGETS:
            page.goto("file:///" + html_path.replace("\\", "/"))
            try:
                page.wait_for_selector(sel + " canvas, " + sel + " > *", timeout=20000)
            except Exception:
                pass
            page.wait_for_timeout(2200)
            loc = page.locator(sel).first
            try:
                loc.screenshot(path=os.path.join(OUT, name))
                print("OK " + name)
            except Exception as e:
                print("FAIL " + name + " " + str(e))
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(shot())
