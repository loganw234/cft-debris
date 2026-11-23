# l_panel.py - cft-debris (DEBRIS-L): the results panel. Four bar charts of figures the committed records of rounds DEBRIS-G, I, H and K
# print, and the table that lists every plotted number with its source file and line. Drawn with numpy and l_png; no map, no font file.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-L, 2026-11-23.
#
#   python -I -B l_panel.py --studies DIR --out DIR      (DIR = the repository's studies/; out = studies/debris-l/panel/)
# Writes panel_table.tsv and chart_g.png, chart_i.png, chart_h.png, chart_k.png (+ .sidecar.json each). Nothing is overwritten
# except this script's own earlier outputs of the same names. A figure keeps its source's thousands commas (the table's "value" column).
import argparse
import json
import math
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import k_lib as K  # noqa: E402
import l_font  # noqa: E402
import l_png  # noqa: E402

SCRIPT = os.path.abspath(__file__)
CW, CH = 1280, 720
PLOT_L, PLOT_R, PLOT_T, PLOT_B = 170, 1240, 150, 590
BG, FG, GRID, DIM = (6, 8, 16), (230, 235, 245), (40, 48, 70), (140, 150, 170)
SER_COLORS = [(255, 159, 67), (80, 200, 255), (120, 255, 140), (255, 80, 90), (190, 150, 255), (240, 230, 110)]
BAR_FILL, BAR_OFF = 0.7, 0.15  # a group's bars fill 70% of its width, from 15%

# chart id -> (title, source note, unit, log axis, ticks, tick labels, categories, series, label scale)
# each value: (file, start marker line, row prefix, cell, part); part None = whole cell, "a" = text before " / "
G_FILE, I_FILE, H_FILE, K_FILE = "DEBRIS-G-build.md", "DEBRIS-I-build.md", "DEBRIS-H-build.md", "DEBRIS-K-study.md"
CHARTS = {
    "g": {
        "title": "DEBRIS-G: M1 CAPACITY AT REAL TIME, 36 THREADS", "unit": "OBJECTS AT REAL TIME (MEDIAN OF 3), LOG AXIS", "log": True,
        "ticks": [1e3, 1e4, 1e5, 1e6, 1e7, 1e8], "note": "SOURCE: DEBRIS-G-BUILD.MD, G4 TABLE; AN EXTRAPOLATION OF COST PER OBJECT", "lscale": 2,
        "cats": ["native32", "native64", "native64-cr", "cft32", "cft64", "cft128", "cft256"], "series": ["CAPACITY"],
        "cell": lambda cat, ser: (G_FILE, "**G4 (MEASURED", "| %s |" % cat, 1, None), "unit_short": "objects",
    },
    "i": {
        "title": "DEBRIS-I: THE PROGRAM AND M1 AT THE PROGRAM'S FORCES, 36 WORKERS", "unit": "OBJECT-SECONDS A SECOND (X, W = 36)", "log": False,
        "ticks": [0, 20000, 40000, 60000, 80000, 100000], "note": "SOURCE: DEBRIS-I-BUILD.MD, SECTION 5; M1 CFT = M1 AT THE PROGRAM'S LIGHTER FORCES", "lscale": 2,
        "cats": ["binary64", "binary128", "binary256"], "series": ["PROGRAM", "M1 CFT"],
        "cell": lambda cat, ser: (I_FILE, "**The rates**", "| the program, %s |" % cat if ser == "PROGRAM" else "| M1 at the program's forces, cft%s |" % cat[6:], 3, None),
        "unit_short": "object-seconds a second",
    },
    "h": {
        "title": "DEBRIS-H: MEDIAN MISS AGAINST CELESTRAK, BY HORIZON", "unit": "MEDIAN MISS (KM), LOG AXIS", "log": True,
        "ticks": [0.01, 0.1, 1, 10, 100], "note": "SOURCE: DEBRIS-H-BUILD.MD, SECTION 6; (A256) M1 FROM THE SEED, (B) SGP4 FROM THE SEED SET", "lscale": 2,
        "cats": ["6 to 24 h", "1 to 2 d", "2 to 3 d", "3 to 7 d", "7 d and over"], "series": ["A256", "B"],
        "cell": lambda cat, ser: (H_FILE, "| horizon e - e0 under 6 h", "| %s |" % cat, 2 if ser == "A256" else 4, "a"), "unit_short": "km",
    },
    "k": {
        "title": "DEBRIS-K: PILOT HINDCAST, MEDIAN MISS BY VARIANT", "unit": "MEDIAN MISS (KM), ALL HORIZONS, LINEAR AXIS", "log": False,
        "ticks": [0, 5, 10, 15, 20, 25, 30, 35], "note": "SOURCE: DEBRIS-K-STUDY.MD, Q3'S TABLES; THE VARIANTS' CHECK COUNTS DIFFER (SEE TABLE)", "lscale": 2,
        "cats": ["(A64)", "(B)", "(B')", "(R)", "(H)", "(C)"], "series": ["MEDIAN"],
        "cell": lambda cat, ser: (K_FILE, "### The tables (aggregates", "| all |", 1 + ["(A64)", "(B)", "(B')", "(R)", "(H)", "(C)"].index(cat), "a"), "unit_short": "km",
    },
}
LABEL_OF = {"g": lambda c: c.upper(), "i": lambda c: c.upper(), "h": lambda c: c.upper(), "k": lambda c: c.upper()}


# ------------------------------------------------------------------ the table
def read_lines(path):
    with open(path, "r", encoding="utf-8", newline=None) as f:  # universal newlines
        return f.read().split("\n")


def find_line(lines, marker, prefix):
    start = next(i for i, ln in enumerate(lines) if ln.startswith(marker))
    for i in range(start, len(lines)):
        if lines[i].startswith(prefix):
            return i + 1
    raise KeyError((marker, prefix))


def cell_text(line, cell):
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return cells[cell]


def extract(line, cell, part):
    txt = cell_text(line, cell)
    if part == "a":
        m = re.match(r"^(?:n \d+: )?([0-9][0-9,.]*) / ", txt)
        if not m:
            m = re.match(r"^n \d+: ([0-9][0-9,.]*)$", txt)  # a cell with one number only
        return m.group(1)
    assert re.match(r"^[0-9][0-9,.]*$", txt), txt
    return txt


def build_rows(studies):
    rows = []
    cache = {}
    for cid, c in CHARTS.items():
        for cat in c["cats"]:
            for ser in c["series"]:
                f, marker, prefix, cell, part = c["cell"](cat, ser)
                if f not in cache:
                    cache[f] = read_lines(os.path.join(studies, f))
                ln = find_line(cache[f], marker, prefix)
                val = extract(cache[f][ln - 1], cell, part)
                rows.append({"chart": cid, "category": cat, "series": ser, "value": val, "unit": c["unit_short"], "source": f, "line": ln, "cell": cell, "part": part or ""})
    return rows


def num(s):
    return float(s.replace(",", ""))


def write_table(path, rows):
    if os.path.exists(path):
        os.remove(path)
    with open(path, "x", encoding="utf-8", newline="\n") as f:
        f.write("# cft-debris DEBRIS-L panel source table: every plotted number, with the committed record and the line it is read from.\n")
        f.write("# cell = the table cell (0-based, between the pipes) of that line; part a = the text before ' / '. Values keep their sources' commas.\n")
        f.write("chart\tcategory\tseries\tvalue\tunit\tsource\tline\tcell\tpart\n")
        for r in rows:
            f.write("\t".join([r["chart"], r["category"], r["series"], r["value"], r["unit"], r["source"], str(r["line"]), str(r["cell"]), r["part"]]) + "\n")


# ------------------------------------------------------------------ the charts
def frac_of(v, c):
    lo, hi = c["ticks"][0], c["ticks"][-1]
    if c["log"]:
        return (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo))
    return (v - lo) / (hi - lo)


def bar_top(v, c):
    return PLOT_B - int(round(frac_of(v, c) * (PLOT_B - PLOT_T)))


def bar_x(gi, si, c):
    gw = (PLOT_R - PLOT_L) / len(c["cats"])
    bw = gw * BAR_FILL / len(c["series"])
    x0 = int(round(PLOT_L + gi * gw + BAR_OFF * gw + si * bw))
    return x0, x0 + int(bw) - 2


def fmt_tick(t):
    return ("%d" % t if t >= 1 else ("%g" % t)).replace("e+", "E") if t < 1000 else "{:,}".format(int(t))


def centred(img, cx, y, s, color, scale):
    w = l_font.text_mask(s, scale).shape[1]
    l_font.draw_text(img, int(cx - w / 2), y, s, color, scale)


def draw_chart(c, values):
    """values[cat][series] = (float, the source's text); returns the image"""
    img = np.zeros((CH, CW, 3), dtype=np.uint8)
    img[:] = BG
    l_font.draw_text(img, 20, 16, c["title"], FG, 3)
    l_font.draw_text(img, 20, 54, c["unit"], DIM, 2)
    l_font.draw_text(img, 20, 76, c["note"], DIM, 2)
    for t in c["ticks"]:
        y = PLOT_B - int(round(frac_of(t, c) * (PLOT_B - PLOT_T))) if (not c["log"] or t > 0) else PLOT_B
        img[y, PLOT_L:PLOT_R] = GRID
        lab = fmt_tick(t)
        w = l_font.text_mask(lab, 2).shape[1]
        l_font.draw_text(img, PLOT_L - 10 - w, y - 7, lab, DIM, 2)
    img[PLOT_T:PLOT_B + 1, PLOT_L - 1] = DIM
    img[PLOT_B, PLOT_L:PLOT_R] = DIM
    gw = (PLOT_R - PLOT_L) / len(c["cats"])
    for gi, cat in enumerate(c["cats"]):
        for si, ser in enumerate(c["series"]):
            v, label = values[cat][ser]
            x0, x1 = bar_x(gi, si, c)
            top = bar_top(v, c)
            img[top:PLOT_B, x0:x1 + 1] = SER_COLORS[si % len(SER_COLORS)]
            centred(img, (x0 + x1) / 2, top - 8 - 7 * c["lscale"], label, FG, c["lscale"])
        centred(img, PLOT_L + (gi + 0.5) * gw, PLOT_B + 14, LABEL_OF["g"](cat), FG, 2)
    if len(c["series"]) > 1:
        x = PLOT_L
        for si, ser in enumerate(c["series"]):
            img[100:112, x:x + 12] = SER_COLORS[si]
            x += 20 + l_font.draw_text(img, x + 20, 98, ser, FG, 2) + 14
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--studies", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rows = build_rows(a.studies)
    tp = os.path.join(a.out, "panel_table.tsv")
    write_table(tp, rows)
    for cid, c in CHARTS.items():
        vals = {cat: {ser: None for ser in c["series"]} for cat in c["cats"]}
        for r in rows:
            if r["chart"] == cid:
                vals[r["category"]][r["series"]] = (num(r["value"]), r["value"])
        img = draw_chart(c, vals)
        p = os.path.join(a.out, "chart_%s.png" % cid)
        l_png.write_png(p, img, 9)
        side = {"file": os.path.basename(p), "sha256": K.sha256(p), "data": {"panel_table.tsv": K.sha256(tp)},
                "scripts": {os.path.basename(SCRIPT): K.sha256(SCRIPT), "l_png.py": K.sha256(os.path.join(os.path.dirname(SCRIPT), "l_png.py")),
                            "l_font.py": K.sha256(os.path.join(os.path.dirname(SCRIPT), "l_font.py"))},
                "sources": {f: K.sha256(os.path.join(a.studies, f)) for f in sorted({r["source"] for r in rows if r["chart"] == cid})}}
        sp = p + ".sidecar.json"
        if os.path.exists(sp):
            os.remove(sp)
        with open(sp, "x", encoding="utf-8", newline="\n") as f:
            json.dump(side, f, indent=1, sort_keys=True)
            f.write("\n")
        print("wrote", os.path.basename(p), len([r for r in rows if r["chart"] == cid]), "values")
    print("table", len(rows), "rows, sha256", K.sha256(tp))
    return 0


if __name__ == "__main__":
    sys.exit(main())
