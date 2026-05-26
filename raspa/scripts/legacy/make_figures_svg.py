#!/usr/bin/env python3
"""Generate thesis figures as pure SVG using only Python standard library."""

import csv
import math
import os
import textwrap


# Editable defaults
TOP_N = 20
RF_RANKING_CSV = "/mnt/c/Users/bienv/Desktop/final_combined_ranking_RF (2).csv"
TOP3_GCMC_CSV = os.path.expanduser("~/raspa_runs/H2_in_MOF/TOP3_ML_PLUS_GCMC_TABLE.csv")
OUTPUT_DIR = os.path.expanduser("~/raspa_runs/H2_in_MOF/figures_svg")


def normalize_header(name):
    """Normalize header labels to handle whitespace/newline/punctuation quirks."""
    if name is None:
        return ""
    cleaned = " ".join(str(name).replace("\r", " ").replace("\n", " ").replace("\t", " ").split())
    return "".join(ch for ch in cleaned.lower() if ch.isalnum())


def xml_escape(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def fmt_num(value):
    if value is None:
        return ""
    if abs(value) >= 100:
        return f"{value:.1f}"
    if abs(value) >= 10:
        return f"{value:.2f}"
    return f"{value:.3f}"


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


def read_csv_robust(path):
    with open(path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no headers: {path}")
        fieldnames = [("" if h is None else str(h).strip()) for h in reader.fieldnames]
        rows = []
        for row in reader:
            clean_row = {}
            for k in fieldnames:
                v = row.get(k, "")
                clean_row[k] = "" if v is None else str(v).strip()
            rows.append(clean_row)
    return fieldnames, rows


def find_column(fieldnames, candidate_names, context_label):
    normalized_map = {}
    for original in fieldnames:
        key = normalize_header(original)
        if key and key not in normalized_map:
            normalized_map[key] = original

    for candidate in candidate_names:
        key = normalize_header(candidate)
        if key in normalized_map:
            return normalized_map[key]

    tried = ", ".join(candidate_names)
    available = ", ".join(fieldnames)
    raise ValueError(
        f"ERROR: Missing expected column for {context_label}. "
        f"Tried [{tried}]. Available headers: [{available}]"
    )


class SvgWriter:
    def __init__(self, width, height, bg="#ffffff"):
        self.width = width
        self.height = height
        self.bg = bg
        self.defs = []
        self.elements = []

    def add_def(self, raw_svg):
        self.defs.append(raw_svg)

    def add(self, raw_svg):
        self.elements.append(raw_svg)

    def rect(self, x, y, w, h, fill="#fff", stroke="#000", stroke_width=1.0, extra=""):
        self.add(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width:.2f}" {extra}/>'
        )

    def line(self, x1, y1, x2, y2, stroke="#000", stroke_width=1.0, extra=""):
        self.add(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{stroke}" stroke-width="{stroke_width:.2f}" {extra}/>'
        )

    def text(
        self,
        x,
        y,
        value,
        size=14,
        anchor="middle",
        weight="normal",
        fill="#111",
        extra="",
        family="Arial, Helvetica, sans-serif",
    ):
        self.add(
            f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" text-anchor="{anchor}" '
            f'font-weight="{weight}" fill="{fill}" font-family="{family}" {extra}>'
            f"{xml_escape(value)}</text>"
        )

    def save(self, path):
        lines = []
        lines.append('<?xml version="1.0" encoding="UTF-8"?>')
        lines.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}">'
        )
        lines.append(f'<rect x="0" y="0" width="{self.width}" height="{self.height}" fill="{self.bg}"/>')
        if self.defs:
            lines.append("<defs>")
            lines.extend(self.defs)
            lines.append("</defs>")
        lines.extend(self.elements)
        lines.append("</svg>")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def wrapped_lines(text, box_width, font_size):
    char_w = max(1.0, font_size * 0.58)
    max_chars = max(8, int(box_width / char_w))
    lines = []
    for paragraph in str(text).split("\n"):
        wrapped = textwrap.wrap(paragraph, width=max_chars) or [""]
        lines.extend(wrapped)
    return lines


def draw_box_with_text(svg, cx, cy, w, h, text, font_size=22):
    x = cx - w / 2.0
    y = cy - h / 2.0
    svg.rect(x, y, w, h, fill="#ffffff", stroke="#111111", stroke_width=2.0, extra='rx="8" ry="8"')
    lines = wrapped_lines(text, w - 28, font_size)
    line_h = font_size * 1.25
    start_y = cy - ((len(lines) - 1) * line_h) / 2.0
    for i, line in enumerate(lines):
        svg.text(cx, start_y + i * line_h, line, size=font_size, anchor="middle")


def make_figure_a(output_path):
    fieldnames, rows = read_csv_robust(RF_RANKING_CSV)
    mof_col = find_column(fieldnames, ["CSD Refcode", "MOF", "Name"], "Figure A MOF label")
    rank_col = find_column(fieldnames, ["overall_rank", "overall rank"], "Figure A overall rank")
    score_col = find_column(fieldnames, ["mean_norm_rank", "mean norm rank"], "Figure A mean norm rank")

    filtered = []
    for row in rows:
        rank = to_float(row.get(rank_col))
        score = to_float(row.get(score_col))
        name = row.get(mof_col, "").strip()
        if rank is None or score is None or not name:
            continue
        filtered.append({"mof": name, "rank": rank, "score": score})

    filtered.sort(key=lambda r: r["rank"])
    top_rows = filtered[:TOP_N]
    if not top_rows:
        raise ValueError("ERROR: Figure A has no valid rows after parsing.")

    width = 1600
    height = 1000
    left = 120
    right = 40
    top = 110
    bottom = 300
    plot_w = width - left - right
    plot_h = height - top - bottom

    svg = SvgWriter(width, height, bg="#ffffff")
    svg.add_def(
        '<pattern id="diagHatchA" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">'
        '<line x1="0" y1="0" x2="0" y2="8" stroke="#777" stroke-width="2"/>'
        "</pattern>"
    )

    y_max = max(r["score"] for r in top_rows)
    y_max = max(1e-9, y_max * 1.12)
    y_ticks = 6

    # Grid and axes
    for i in range(y_ticks + 1):
        v = y_max * i / y_ticks
        y = top + plot_h - (v / y_max) * plot_h
        svg.line(left, y, left + plot_w, y, stroke="#d0d0d0", stroke_width=1.0)
        svg.text(left - 12, y + 5, fmt_num(v), size=14, anchor="end", fill="#333")

    svg.line(left, top, left, top + plot_h, stroke="#111", stroke_width=2.0)
    svg.line(left, top + plot_h, left + plot_w, top + plot_h, stroke="#111", stroke_width=2.0)

    n = len(top_rows)
    step = plot_w / float(n)
    bar_w = step * 0.68

    for i, row in enumerate(top_rows):
        x = left + i * step + (step - bar_w) / 2.0
        bar_h = (row["score"] / y_max) * plot_h
        y = top + plot_h - bar_h

        is_top3 = i < 3
        fill = "#bfbfbf" if not is_top3 else "url(#diagHatchA)"
        stroke_w = 1.1 if not is_top3 else 2.8
        svg.rect(x, y, bar_w, bar_h, fill=fill, stroke="#111", stroke_width=stroke_w)

        if is_top3:
            svg.text(x + bar_w / 2.0, y - 8, f"Top {i + 1}", size=14, anchor="middle", weight="bold")

        label_x = x + bar_w / 2.0
        label_y = top + plot_h + 22
        svg.text(
            label_x,
            label_y,
            row["mof"],
            size=12,
            anchor="end",
            extra=f'transform="rotate(-60 {label_x:.2f} {label_y:.2f})"',
        )

    svg.text(width / 2.0, 50, f"Figure A: Random Forest Ranking Overview (Top {n})", size=30, weight="bold")
    svg.text(width / 2.0, height - 45, "MOF (CSD Refcode)", size=20, weight="bold")
    svg.text(
        36,
        top + plot_h / 2.0,
        "Mean Normalized Rank",
        size=20,
        weight="bold",
        extra=f'transform="rotate(-90 36 {top + plot_h / 2.0:.2f})"',
    )

    svg.save(output_path)


def draw_y_axis_with_grid(svg, left, top, plot_w, plot_h, y_max, label, tick_count=5):
    for i in range(tick_count + 1):
        v = y_max * i / tick_count
        y = top + plot_h - (v / y_max) * plot_h
        svg.line(left, y, left + plot_w, y, stroke="#d8d8d8", stroke_width=1.0)
        svg.text(left - 10, y + 4, fmt_num(v), size=13, anchor="end", fill="#333")
    svg.line(left, top, left, top + plot_h, stroke="#111", stroke_width=2.0)
    svg.line(left, top + plot_h, left + plot_w, top + plot_h, stroke="#111", stroke_width=2.0)
    svg.text(
        left - 62,
        top + plot_h / 2.0,
        label,
        size=18,
        weight="bold",
        extra=f'transform="rotate(-90 {left - 62:.2f} {top + plot_h / 2.0:.2f})"',
    )


def bar_top_y(value, y_max, top, plot_h):
    if y_max <= 0:
        return top + plot_h
    return top + plot_h - (value / y_max) * plot_h


def draw_panel_grouped(svg, left, top, plot_w, plot_h, mofs, panel_title, y_label, series):
    # series keys: ps_pred, ps_gcmc, tps_pred, tps_gcmc
    all_vals = series["ps_pred"] + series["ps_gcmc"] + series["tps_pred"] + series["tps_gcmc"]
    y_max = max(all_vals) if all_vals else 1.0
    y_max = max(1e-9, y_max * 1.18)
    draw_y_axis_with_grid(svg, left, top, plot_w, plot_h, y_max, y_label, tick_count=5)
    svg.text(left + plot_w / 2.0, top - 18, panel_title, size=22, weight="bold")

    n = len(mofs)
    group_w = plot_w / float(max(1, n))
    bar_w = group_w * 0.14
    inner_gap = group_w * 0.03
    cluster_gap = group_w * 0.12
    left_margin = group_w * 0.08

    for i, mof in enumerate(mofs):
        gx = left + i * group_w + left_margin
        ps_pred_x = gx
        ps_gcmc_x = gx + bar_w + inner_gap
        tps_pred_x = gx + (2 * bar_w + inner_gap + cluster_gap)
        tps_gcmc_x = tps_pred_x + bar_w + inner_gap

        positions = [
            (ps_pred_x, series["ps_pred"][i], False),
            (ps_gcmc_x, series["ps_gcmc"][i], True),
            (tps_pred_x, series["tps_pred"][i], False),
            (tps_gcmc_x, series["tps_gcmc"][i], True),
        ]
        for x, val, is_gcmc in positions:
            y = bar_top_y(val, y_max, top, plot_h)
            h = top + plot_h - y
            fill = "#bdbdbd" if not is_gcmc else "url(#diagHatchB)"
            stroke_w = 1.2 if not is_gcmc else 1.8
            extra = ''
            if is_gcmc:
                extra = 'stroke-dasharray="5,2"'
            svg.rect(x, y, bar_w, h, fill=fill, stroke="#111", stroke_width=stroke_w, extra=extra)

        ps_center = ps_pred_x + (bar_w + inner_gap + bar_w) / 2.0
        tps_center = tps_pred_x + (bar_w + inner_gap + bar_w) / 2.0
        mof_center = (ps_center + tps_center) / 2.0
        svg.text(ps_center, top + plot_h + 16, "PS", size=12, anchor="middle", fill="#444")
        svg.text(tps_center, top + plot_h + 16, "TPS", size=12, anchor="middle", fill="#444")
        svg.text(mof_center, top + plot_h + 36, mof, size=13, anchor="middle", weight="bold")


def make_figure_b(output_path):
    fieldnames, rows = read_csv_robust(TOP3_GCMC_CSV)
    rank_col = find_column(fieldnames, ["overall_rank", "overall rank"], "Figure B overall rank")
    mof_col = find_column(fieldnames, ["MOF", "CSD Refcode", "Name"], "Figure B MOF")

    cols = {
        "ug_ps_pred": find_column(fieldnames, ["ML_Predicted_PS_UG_RF"], "Figure B UG PS predicted"),
        "ug_ps_gcmc": find_column(fieldnames, ["GCMC_UG_PS"], "Figure B UG PS GCMC"),
        "ug_tps_pred": find_column(fieldnames, ["ML_Predicted_TPS_UG_RF"], "Figure B UG TPS predicted"),
        "ug_tps_gcmc": find_column(fieldnames, ["GCMC_UG_TPS"], "Figure B UG TPS GCMC"),
        "uv_ps_pred": find_column(fieldnames, ["ML_Predicted_PS_UV_RF"], "Figure B UV PS predicted"),
        "uv_ps_gcmc": find_column(fieldnames, ["GCMC_UV_PS"], "Figure B UV PS GCMC"),
        "uv_tps_pred": find_column(fieldnames, ["ML_Predicted_TPS_UV_RF"], "Figure B UV TPS predicted"),
        "uv_tps_gcmc": find_column(fieldnames, ["GCMC_UV_TPS"], "Figure B UV TPS GCMC"),
    }

    parsed = []
    for row in rows:
        rank = to_float(row.get(rank_col))
        mof = row.get(mof_col, "").strip()
        if rank is None or not mof:
            continue
        entry = {"rank": rank, "mof": mof}
        valid = True
        for key, col in cols.items():
            val = to_float(row.get(col))
            if val is None:
                valid = False
                break
            entry[key] = val
        if valid:
            parsed.append(entry)

    parsed.sort(key=lambda r: r["rank"])
    if not parsed:
        raise ValueError("ERROR: Figure B has no valid rows after parsing.")

    mofs = [r["mof"] for r in parsed]

    width = 1600
    height = 1260
    svg = SvgWriter(width, height, bg="#ffffff")
    svg.add_def(
        '<pattern id="diagHatchB" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">'
        '<line x1="0" y1="0" x2="0" y2="8" stroke="#777" stroke-width="2"/>'
        "</pattern>"
    )

    svg.text(width / 2.0, 48, "Figure B: Corrected Capacity Comparison", size=30, weight="bold")
    svg.text(width / 2.0, 82, "RF Predicted vs Corrected GCMC", size=20, weight="bold")

    # Legend
    lx = width - 430
    ly = 100
    svg.rect(lx, ly, 28, 18, fill="#bdbdbd", stroke="#111", stroke_width=1.2)
    svg.text(lx + 38, ly + 14, "Predicted (RF)", size=14, anchor="start")
    svg.rect(
        lx + 190,
        ly,
        28,
        18,
        fill="url(#diagHatchB)",
        stroke="#111",
        stroke_width=1.6,
        extra='stroke-dasharray="5,2"',
    )
    svg.text(lx + 228, ly + 14, "Corrected GCMC", size=14, anchor="start")

    left = 130
    plot_w = width - left - 70
    panel_h = 420
    top1 = 150
    top2 = 700

    draw_panel_grouped(
        svg,
        left=left,
        top=top1,
        plot_w=plot_w,
        plot_h=panel_h,
        mofs=mofs,
        panel_title="UG Metrics (wt%)",
        y_label="Capacity (wt%)",
        series={
            "ps_pred": [r["ug_ps_pred"] for r in parsed],
            "ps_gcmc": [r["ug_ps_gcmc"] for r in parsed],
            "tps_pred": [r["ug_tps_pred"] for r in parsed],
            "tps_gcmc": [r["ug_tps_gcmc"] for r in parsed],
        },
    )

    draw_panel_grouped(
        svg,
        left=left,
        top=top2,
        plot_w=plot_w,
        plot_h=panel_h,
        mofs=mofs,
        panel_title="UV Metrics (g/L)",
        y_label="Capacity (g/L)",
        series={
            "ps_pred": [r["uv_ps_pred"] for r in parsed],
            "ps_gcmc": [r["uv_ps_gcmc"] for r in parsed],
            "tps_pred": [r["uv_tps_pred"] for r in parsed],
            "tps_gcmc": [r["uv_tps_gcmc"] for r in parsed],
        },
    )

    svg.save(output_path)


def make_figure_c(output_path):
    width = 1400
    height = 900
    svg = SvgWriter(width, height, bg="#ffffff")
    svg.add_def(
        '<marker id="arrowHead" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#111"/>'
        "</marker>"
    )

    svg.text(width / 2.0, 52, "Figure C: Benchmark Status Diagram", size=32, weight="bold")

    b1 = (700, 150, 520, 90)
    b2 = (700, 320, 560, 90)
    b3a = (390, 550, 560, 130)
    b3b = (1010, 560, 680, 150)
    footer = (700, 805, 860, 66)

    draw_box_with_text(svg, *b1, "RF screening (7 descriptors)", font_size=28)
    draw_box_with_text(svg, *b2, "Top 3: VAGMAT, XAFFAN, XAFFIV", font_size=28)
    draw_box_with_text(svg, *b3a, "Benchmark overlap: VAGMAT \u2192 compare to HyMARC", font_size=24)
    draw_box_with_text(
        svg,
        *b3b,
        "HyMARC N/A: XAFFAN, XAFFIV \u2192 validated using corrected author-run GCMC",
        font_size=24,
    )
    draw_box_with_text(
        svg,
        *footer,
        "All reported capacities use corrected mol/kg-derived values",
        font_size=23,
    )

    # Arrows
    b1_bottom_x = b1[0]
    b1_bottom_y = b1[1] + b1[3] / 2.0
    b2_top_x = b2[0]
    b2_top_y = b2[1] - b2[3] / 2.0
    svg.line(
        b1_bottom_x,
        b1_bottom_y + 4,
        b2_top_x,
        b2_top_y - 4,
        stroke="#111",
        stroke_width=2.6,
        extra='marker-end="url(#arrowHead)"',
    )

    b2_left = (b2[0] - b2[2] / 2.0 + 70, b2[1] + b2[3] / 2.0)
    b2_right = (b2[0] + b2[2] / 2.0 - 70, b2[1] + b2[3] / 2.0)
    b3a_top = (b3a[0], b3a[1] - b3a[3] / 2.0)
    b3b_top = (b3b[0], b3b[1] - b3b[3] / 2.0)

    svg.line(
        b2_left[0],
        b2_left[1],
        b3a_top[0],
        b3a_top[1] - 6,
        stroke="#111",
        stroke_width=2.4,
        extra='marker-end="url(#arrowHead)"',
    )
    svg.line(
        b2_right[0],
        b2_right[1],
        b3b_top[0],
        b3b_top[1] - 6,
        stroke="#111",
        stroke_width=2.4,
        extra='marker-end="url(#arrowHead)"',
    )

    svg.save(output_path)


def write_readme(path):
    content = """SVG Export to PDF (No extra tools required)

1) Open each SVG file in a web browser (Firefox/Chrome/Edge).
2) Press Ctrl+P (Print).
3) Destination/Printer: Save as PDF.
4) Set layout/orientation as needed, then save.

Files:
- Figure_A_RF_ranking_overview.svg
- Figure_B_corrected_capacity_comparison.svg
- Figure_C_benchmark_status_diagram.svg
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    created = []
    try:
        out_a = os.path.abspath(os.path.join(OUTPUT_DIR, "Figure_A_RF_ranking_overview.svg"))
        out_b = os.path.abspath(os.path.join(OUTPUT_DIR, "Figure_B_corrected_capacity_comparison.svg"))
        out_c = os.path.abspath(os.path.join(OUTPUT_DIR, "Figure_C_benchmark_status_diagram.svg"))
        out_readme = os.path.abspath(os.path.join(OUTPUT_DIR, "README_EXPORT_TO_PDF.txt"))

        if not os.path.isfile(RF_RANKING_CSV):
            raise FileNotFoundError(f"Missing input file: {RF_RANKING_CSV}")
        if not os.path.isfile(TOP3_GCMC_CSV):
            raise FileNotFoundError(f"Missing input file: {TOP3_GCMC_CSV}")

        make_figure_a(out_a)
        created.append(out_a)
        make_figure_b(out_b)
        created.append(out_b)
        make_figure_c(out_c)
        created.append(out_c)
        write_readme(out_readme)
        created.append(out_readme)
    except Exception as exc:
        print(str(exc))
        return 1

    print("Created files:")
    for p in created:
        print(p)

    print("\nOutput folder listing:")
    for name in sorted(os.listdir(OUTPUT_DIR)):
        print(os.path.abspath(os.path.join(OUTPUT_DIR, name)))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
