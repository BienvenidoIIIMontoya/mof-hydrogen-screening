#!/usr/bin/env python3
"""Generate thesis Figure A/B/C v2 as SVG (pure Python stdlib: csv, math, os)."""

import csv
import math
import os


# Editable defaults
TOP_N = 20
RF_RANKING_CSV = "/mnt/c/Users/bienv/Desktop/final_combined_ranking_RF (2).csv"
TOP3_GCMC_CSV = os.path.expanduser("~/raspa_runs/H2_in_MOF/TOP3_ML_PLUS_GCMC_TABLE.csv")
FINAL_BENCHMARK_CSV = os.path.expanduser("~/raspa_runs/H2_in_MOF/FINAL_BENCHMARK_TABLE.csv")
OUT_DIR = os.path.expanduser("~/raspa_runs/H2_in_MOF/figures_svg_v2")


def normalize_header(name):
    if name is None:
        return ""
    compact = " ".join(str(name).replace("\r", " ").replace("\n", " ").replace("\t", " ").split())
    return "".join(ch for ch in compact.lower() if ch.isalnum())


def xml_escape(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def to_float(value):
    if value is None:
        return None
    txt = str(value).strip().replace(",", "")
    if txt == "" or txt.upper() == "N/A":
        return None
    try:
        return float(txt)
    except ValueError:
        return None


def read_csv_rows(path):
    with open(path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise RuntimeError("CSV has no headers: " + path)
        headers = [("" if h is None else str(h).strip()) for h in reader.fieldnames]
        rows = []
        for row in reader:
            clean = {}
            for h in headers:
                v = row.get(h, "")
                clean[h] = "" if v is None else str(v).strip()
            rows.append(clean)
        return headers, rows


def require_column(headers, candidates, context):
    norm_to_original = {}
    for h in headers:
        nh = normalize_header(h)
        if nh and nh not in norm_to_original:
            norm_to_original[nh] = h

    for cand in candidates:
        key = normalize_header(cand)
        if key in norm_to_original:
            return norm_to_original[key]

    raise RuntimeError(
        "Missing expected column for "
        + context
        + ". Tried: "
        + ", ".join(candidates)
        + ". Available headers: "
        + ", ".join(headers)
    )


def fmt(v, decimals=2):
    if v is None:
        return ""
    return f"{v:.{decimals}f}"


class Svg:
    def __init__(self, width, height, bg="#ffffff"):
        self.width = width
        self.height = height
        self.bg = bg
        self.defs = []
        self.body = []

    def add_def(self, raw):
        self.defs.append(raw)

    def add(self, raw):
        self.body.append(raw)

    def rect(self, x, y, w, h, fill="#fff", stroke="#111", sw=1.0, extra=""):
        self.add(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw:.2f}" {extra}/>'
        )

    def line(self, x1, y1, x2, y2, stroke="#111", sw=1.0, extra=""):
        self.add(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{stroke}" stroke-width="{sw:.2f}" {extra}/>'
        )

    def circle(self, cx, cy, r, fill="#777", stroke="#111", sw=1.0, extra=""):
        self.add(
            f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw:.2f}" {extra}/>'
        )

    def text(self, x, y, text, size=14, anchor="middle", weight="normal", fill="#111", extra=""):
        self.add(
            f'<text x="{x:.2f}" y="{y:.2f}" font-family="Arial, Helvetica, sans-serif" '
            f'font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" fill="{fill}" {extra}>'
            f"{xml_escape(text)}</text>"
        )

    def save(self, path):
        out = []
        out.append('<?xml version="1.0" encoding="UTF-8"?>')
        out.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}">'
        )
        out.append(f'<rect x="0" y="0" width="{self.width}" height="{self.height}" fill="{self.bg}"/>')
        if self.defs:
            out.append("<defs>")
            out.extend(self.defs)
            out.append("</defs>")
        out.extend(self.body)
        out.append("</svg>")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")


def draw_axes_and_grid(svg, x0, y0, w, h, ymax, y_label, panel_title):
    ticks = 5
    ymax = max(ymax, 1e-9)
    for i in range(ticks + 1):
        v = ymax * i / ticks
        y = y0 + h - (v / ymax) * h
        svg.line(x0, y, x0 + w, y, stroke="#d4d4d4", sw=1.0)
        svg.text(x0 - 10, y + 4, fmt(v, 2), size=12, anchor="end", fill="#333")
    svg.line(x0, y0, x0, y0 + h, stroke="#111", sw=1.8)
    svg.line(x0, y0 + h, x0 + w, y0 + h, stroke="#111", sw=1.8)
    svg.text(x0 + w / 2.0, y0 - 16, panel_title, size=20, weight="bold")
    yl_x = x0 - 62
    yl_y = y0 + h / 2.0
    svg.text(yl_x, yl_y, y_label, size=16, weight="bold", extra=f'transform="rotate(-90 {yl_x:.2f} {yl_y:.2f})"')


def draw_bar_panel(svg, x0, y0, w, h, labels, values, y_label, panel_title, top3_indices, show_top3_value_labels):
    ymax = max(values) if values else 1.0
    ymax = max(1e-9, ymax * 1.15)
    draw_axes_and_grid(svg, x0, y0, w, h, ymax, y_label, panel_title)

    n = max(1, len(labels))
    step = w / float(n)
    bar_w = step * 0.68

    for i, (lab, val) in enumerate(zip(labels, values)):
        bx = x0 + i * step + (step - bar_w) / 2.0
        by = y0 + h - (val / ymax) * h
        bh = y0 + h - by
        is_top3 = i in top3_indices
        fill = "#bfbfbf" if not is_top3 else "url(#diagHatch)"
        sw = 1.0 if not is_top3 else 2.6
        svg.rect(bx, by, bar_w, bh, fill=fill, stroke="#111", sw=sw)
        if is_top3:
            rank_num = i + 1
            svg.text(bx + bar_w / 2.0, by - 10, f"Top {rank_num}", size=12, weight="bold")
            if show_top3_value_labels:
                svg.text(bx + bar_w / 2.0, by - 24, fmt(val, 2), size=11, weight="bold")

        tx = bx + bar_w / 2.0
        ty = y0 + h + 20
        svg.text(tx, ty, lab, size=11, anchor="end", extra=f'transform="rotate(-60 {tx:.2f} {ty:.2f})"')


def make_figure_a(path):
    headers, rows = read_csv_rows(RF_RANKING_CSV)
    mof_col = require_column(headers, ["CSD Refcode", "MOF", "Name"], "Figure A MOF labels")
    rank_col = require_column(headers, ["overall_rank", "overall rank"], "Figure A overall rank")
    ug_col = require_column(headers, ["ML_Predicted_PS_UG_RF"], "Figure A panel A1")
    uv_col = require_column(headers, ["ML_Predicted_PS_UV_RF"], "Figure A panel A2")

    clean = []
    for r in rows:
        rank = to_float(r.get(rank_col))
        ug = to_float(r.get(ug_col))
        uv = to_float(r.get(uv_col))
        mof = r.get(mof_col, "").strip()
        if rank is None or ug is None or uv is None or mof == "":
            continue
        clean.append({"rank": rank, "mof": mof, "ug": ug, "uv": uv})

    clean.sort(key=lambda z: z["rank"])
    top = clean[:TOP_N]
    if not top:
        raise RuntimeError("Figure A has no valid rows after parsing.")

    labels = [r["mof"] for r in top]
    ug_vals = [r["ug"] for r in top]
    uv_vals = [r["uv"] for r in top]
    top3 = set([0, 1, 2])

    W, H = 1700, 1400
    svg = Svg(W, H)
    svg.add_def(
        '<pattern id="diagHatch" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">'
        '<line x1="0" y1="0" x2="0" y2="8" stroke="#777" stroke-width="2"/>'
        "</pattern>"
    )

    svg.text(W / 2.0, 48, "Figure A v2: RF Predicted Capacities for Top-20 MOFs", size=30, weight="bold")
    svg.text(W / 2.0, 82, "Panel A1 and A2 show predicted performance magnitudes (not flat rank scores)", size=18, weight="bold")

    left = 130
    width = W - 180
    panel_h = 360
    y1 = 130
    y2 = 760

    draw_bar_panel(
        svg,
        x0=left,
        y0=y1,
        w=width,
        h=panel_h,
        labels=labels,
        values=ug_vals,
        y_label="Predicted PS UG (wt%)",
        panel_title="A1: ML_Predicted_PS_UG_RF",
        top3_indices=top3,
        show_top3_value_labels=True,
    )
    draw_bar_panel(
        svg,
        x0=left,
        y0=y2,
        w=width,
        h=panel_h,
        labels=labels,
        values=uv_vals,
        y_label="Predicted PS UV (g/L)",
        panel_title="A2: ML_Predicted_PS_UV_RF",
        top3_indices=top3,
        show_top3_value_labels=True,
    )
    svg.text(W / 2.0, H - 30, "MOF Refcode (Top-N ordered by overall_rank)", size=17, weight="bold")
    svg.save(path)


def draw_two_bar_panel(svg, x0, y0, w, h, panel_title, y_label, mofs, pred_vals, gcmc_vals):
    ymax = 0.0
    for v in pred_vals + gcmc_vals:
        if v is not None:
            ymax = max(ymax, v)
    ymax = max(1e-9, ymax * 1.18)
    draw_axes_and_grid(svg, x0, y0, w, h, ymax, y_label, panel_title)

    n = max(1, len(mofs))
    group_w = w / float(n)
    bw = group_w * 0.24
    gap = group_w * 0.10
    left_pad = (group_w - (2 * bw + gap)) / 2.0

    for i, mof in enumerate(mofs):
        gx = x0 + i * group_w
        x_pred = gx + left_pad
        x_gcmc = x_pred + bw + gap
        pv = pred_vals[i]
        gv = gcmc_vals[i]
        py = y0 + h - (pv / ymax) * h
        gy = y0 + h - (gv / ymax) * h
        ph = y0 + h - py
        gh = y0 + h - gy
        svg.rect(x_pred, py, bw, ph, fill="#bdbdbd", stroke="#111", sw=1.2)
        svg.rect(x_gcmc, gy, bw, gh, fill="url(#diagHatchB)", stroke="#111", sw=1.6, extra='stroke-dasharray="5,2"')
        svg.text(x_pred + bw / 2.0, py - 7, fmt(pv, 2), size=11, anchor="middle")
        svg.text(x_gcmc + bw / 2.0, gy - 7, fmt(gv, 2), size=11, anchor="middle")
        svg.text(gx + group_w / 2.0, y0 + h + 20, mof, size=12, weight="bold")


def make_figure_b(path):
    headers, rows = read_csv_rows(TOP3_GCMC_CSV)
    mof_col = require_column(headers, ["MOF", "CSD Refcode", "Name"], "Figure B MOF")
    rank_col = require_column(headers, ["overall_rank", "overall rank"], "Figure B overall rank")
    cols = {
        "ug_ps_pred": require_column(headers, ["ML_Predicted_PS_UG_RF"], "Figure B UG_PS predicted"),
        "uv_ps_pred": require_column(headers, ["ML_Predicted_PS_UV_RF"], "Figure B UV_PS predicted"),
        "ug_tps_pred": require_column(headers, ["ML_Predicted_TPS_UG_RF"], "Figure B UG_TPS predicted"),
        "uv_tps_pred": require_column(headers, ["ML_Predicted_TPS_UV_RF"], "Figure B UV_TPS predicted"),
        "ug_ps_gcmc": require_column(headers, ["GCMC_UG_PS"], "Figure B UG_PS corrected"),
        "uv_ps_gcmc": require_column(headers, ["GCMC_UV_PS"], "Figure B UV_PS corrected"),
        "ug_tps_gcmc": require_column(headers, ["GCMC_UG_TPS"], "Figure B UG_TPS corrected"),
        "uv_tps_gcmc": require_column(headers, ["GCMC_UV_TPS"], "Figure B UV_TPS corrected"),
    }

    clean = []
    for r in rows:
        rank = to_float(r.get(rank_col))
        mof = r.get(mof_col, "").strip()
        if rank is None or mof == "":
            continue
        values = {}
        ok = True
        for k, c in cols.items():
            v = to_float(r.get(c))
            if v is None:
                ok = False
                break
            values[k] = v
        if ok:
            values["rank"] = rank
            values["mof"] = mof
            clean.append(values)

    clean.sort(key=lambda z: z["rank"])
    if not clean:
        raise RuntimeError("Figure B has no valid rows after parsing.")

    mofs = [r["mof"] for r in clean]

    W, H = 1700, 1300
    svg = Svg(W, H)
    svg.add_def(
        '<pattern id="diagHatchB" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">'
        '<line x1="0" y1="0" x2="0" y2="8" stroke="#777" stroke-width="2"/>'
        "</pattern>"
    )
    svg.text(W / 2.0, 46, "Figure B v2: Predicted vs Corrected GCMC (Top-3)", size=30, weight="bold")

    # Legend
    lx = W - 530
    ly = 68
    svg.rect(lx, ly, 28, 18, fill="#bdbdbd", stroke="#111", sw=1.2)
    svg.text(lx + 36, ly + 14, "Predicted", size=14, anchor="start")
    svg.rect(lx + 160, ly, 28, 18, fill="url(#diagHatchB)", stroke="#111", sw=1.4, extra='stroke-dasharray="5,2"')
    svg.text(lx + 196, ly + 14, "Corrected GCMC", size=14, anchor="start")

    left = 110
    top = 120
    right = 60
    bottom = 80
    hgap = 120
    vgap = 120
    pw = (W - left - right - hgap) / 2.0
    ph = (H - top - bottom - vgap) / 2.0

    x1 = left
    x2 = left + pw + hgap
    y1 = top
    y2 = top + ph + vgap

    draw_two_bar_panel(
        svg, x1, y1, pw, ph, "UG_PS (wt%)", "Capacity (wt%)", mofs,
        [r["ug_ps_pred"] for r in clean], [r["ug_ps_gcmc"] for r in clean]
    )
    draw_two_bar_panel(
        svg, x2, y1, pw, ph, "UV_PS (g/L)", "Capacity (g/L)", mofs,
        [r["uv_ps_pred"] for r in clean], [r["uv_ps_gcmc"] for r in clean]
    )
    draw_two_bar_panel(
        svg, x1, y2, pw, ph, "UG_TPS (wt%)", "Capacity (wt%)", mofs,
        [r["ug_tps_pred"] for r in clean], [r["ug_tps_gcmc"] for r in clean]
    )
    draw_two_bar_panel(
        svg, x2, y2, pw, ph, "UV_TPS (g/L)", "Capacity (g/L)", mofs,
        [r["uv_tps_pred"] for r in clean], [r["uv_tps_gcmc"] for r in clean]
    )
    svg.save(path)


def draw_scatter_panel(svg, x0, y0, w, h, title, x_label, y_label, points):
    vmax = 0.0
    for p in points:
        vmax = max(vmax, p["mine"], p["hymarc"])
    vmax = max(1e-9, vmax * 1.15)
    ticks = 5

    # grid + axes
    for i in range(ticks + 1):
        v = vmax * i / ticks
        x = x0 + (v / vmax) * w
        y = y0 + h - (v / vmax) * h
        svg.line(x0, y, x0 + w, y, stroke="#d6d6d6", sw=1.0)
        svg.line(x, y0, x, y0 + h, stroke="#ececec", sw=1.0)
        svg.text(x0 - 10, y + 4, fmt(v, 2), size=12, anchor="end", fill="#333")
        svg.text(x, y0 + h + 18, fmt(v, 2), size=12, anchor="middle", fill="#333")

    svg.line(x0, y0, x0, y0 + h, stroke="#111", sw=1.8)
    svg.line(x0, y0 + h, x0 + w, y0 + h, stroke="#111", sw=1.8)
    svg.text(x0 + w / 2.0, y0 - 16, title, size=20, weight="bold")
    svg.text(x0 + w / 2.0, y0 + h + 44, x_label, size=15, weight="bold")
    yl_x = x0 - 66
    yl_y = y0 + h / 2.0
    svg.text(yl_x, yl_y, y_label, size=15, weight="bold", extra=f'transform="rotate(-90 {yl_x:.2f} {yl_y:.2f})"')

    # y=x line
    svg.line(x0, y0 + h, x0 + w, y0, stroke="#666", sw=1.5, extra='stroke-dasharray="6,4"')

    for i, p in enumerate(points):
        px = x0 + (p["hymarc"] / vmax) * w
        py = y0 + h - (p["mine"] / vmax) * h
        svg.circle(px, py, 4.5, fill="#777", stroke="#111", sw=1.0)
        dx = 7
        dy = -7 if i % 2 == 0 else 14
        svg.text(px + dx, py + dy, p["mof"], size=12, anchor="start", weight="bold")


def make_figure_c(path):
    headers, rows = read_csv_rows(FINAL_BENCHMARK_CSV)
    mof_col = require_column(headers, ["MOF", "CSD Refcode", "Name"], "Figure C MOF")
    col_map = {
        "ug_ps_mine": require_column(headers, ["UG_PS_mine"], "Figure C UG_PS mine"),
        "ug_ps_hymarc": require_column(headers, ["UG_PS_hymarc"], "Figure C UG_PS hymarc"),
        "uv_ps_mine": require_column(headers, ["UV_PS_mine"], "Figure C UV_PS mine"),
        "uv_ps_hymarc": require_column(headers, ["UV_PS_hymarc"], "Figure C UV_PS hymarc"),
        "ug_tps_mine": require_column(headers, ["UG_TPS_mine"], "Figure C UG_TPS mine"),
        "ug_tps_hymarc": require_column(headers, ["UG_TPS_hymarc"], "Figure C UG_TPS hymarc"),
        "uv_tps_mine": require_column(headers, ["UV_TPS_mine"], "Figure C UV_TPS mine"),
        "uv_tps_hymarc": require_column(headers, ["UV_TPS_hymarc"], "Figure C UV_TPS hymarc"),
    }

    pts = []
    for r in rows:
        mof = r.get(mof_col, "").strip()
        if mof == "":
            continue
        vals = {}
        ok = True
        for k, c in col_map.items():
            v = to_float(r.get(c))
            if v is None:
                ok = False
                break
            vals[k] = v
        if ok:
            vals["mof"] = mof
            pts.append(vals)

    if not pts:
        raise RuntimeError("Figure C has no valid benchmark rows after parsing.")

    W, H = 1700, 1300
    svg = Svg(W, H)
    svg.text(W / 2.0, 46, "Figure C v2: Benchmark Agreement (Mine vs HyMARC)", size=30, weight="bold")

    left = 110
    top = 120
    right = 60
    bottom = 80
    hgap = 120
    vgap = 120
    pw = (W - left - right - hgap) / 2.0
    ph = (H - top - bottom - vgap) / 2.0

    x1 = left
    x2 = left + pw + hgap
    y1 = top
    y2 = top + ph + vgap

    draw_scatter_panel(
        svg, x1, y1, pw, ph, "UG_PS", "HyMARC", "Mine",
        [{"mof": p["mof"], "mine": p["ug_ps_mine"], "hymarc": p["ug_ps_hymarc"]} for p in pts]
    )
    draw_scatter_panel(
        svg, x2, y1, pw, ph, "UV_PS", "HyMARC", "Mine",
        [{"mof": p["mof"], "mine": p["uv_ps_mine"], "hymarc": p["uv_ps_hymarc"]} for p in pts]
    )
    draw_scatter_panel(
        svg, x1, y2, pw, ph, "UG_TPS", "HyMARC", "Mine",
        [{"mof": p["mof"], "mine": p["ug_tps_mine"], "hymarc": p["ug_tps_hymarc"]} for p in pts]
    )
    draw_scatter_panel(
        svg, x2, y2, pw, ph, "UV_TPS", "HyMARC", "Mine",
        [{"mof": p["mof"], "mine": p["uv_tps_mine"], "hymarc": p["uv_tps_hymarc"]} for p in pts]
    )
    svg.save(path)


def write_readme(path):
    txt = (
        "How to export SVG to PDF (browser only)\n"
        "\n"
        "1) Open the SVG file in your browser (Firefox/Chrome/Edge).\n"
        "2) Press Ctrl+P.\n"
        "3) Choose destination: Save as PDF.\n"
        "4) Set orientation/scale if needed, then save.\n"
        "\n"
        "Files generated:\n"
        "- Figure_A_v2_RF_predicted_top20.svg\n"
        "- Figure_B_v2_predicted_vs_corrected_GCMC.svg\n"
        "- Figure_C_v2_benchmark_agreement.svg\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    if not os.path.isfile(RF_RANKING_CSV):
        raise RuntimeError("Missing input file: " + RF_RANKING_CSV)
    if not os.path.isfile(TOP3_GCMC_CSV):
        raise RuntimeError("Missing input file: " + TOP3_GCMC_CSV)
    if not os.path.isfile(FINAL_BENCHMARK_CSV):
        raise RuntimeError("Missing input file: " + FINAL_BENCHMARK_CSV)

    out_a = os.path.abspath(os.path.join(OUT_DIR, "Figure_A_v2_RF_predicted_top20.svg"))
    out_b = os.path.abspath(os.path.join(OUT_DIR, "Figure_B_v2_predicted_vs_corrected_GCMC.svg"))
    out_c = os.path.abspath(os.path.join(OUT_DIR, "Figure_C_v2_benchmark_agreement.svg"))
    out_r = os.path.abspath(os.path.join(OUT_DIR, "README_EXPORT_TO_PDF.txt"))

    make_figure_a(out_a)
    make_figure_b(out_b)
    make_figure_c(out_c)
    write_readme(out_r)

    print("Generated files:")
    print(out_a)
    print(out_b)
    print(out_c)
    print(out_r)
    print("")
    print("Figure A uses predicted capacities (not mean_norm_rank) because rank scores were too flat to visualize.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
