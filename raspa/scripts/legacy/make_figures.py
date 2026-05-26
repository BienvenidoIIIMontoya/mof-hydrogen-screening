#!/usr/bin/env python3
"""Generate thesis figures A, B, and C from local CSV tables."""

from __future__ import annotations

import csv
from pathlib import Path


# Easy-to-change defaults
TOP_N = 20
RF_RANKING_CSV = Path("/mnt/c/Users/bienv/Desktop/final_combined_ranking_RF (2).csv")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def to_float(value: str) -> float | None:
    if value is None:
        return None
    text = value.strip()
    if not text or text.upper() == "N/A":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def save_png_pdf(fig, out_dir: Path, stem: str) -> list[Path]:
    out_png = out_dir / f"{stem}.png"
    out_pdf = out_dir / f"{stem}.pdf"
    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    return [out_png.resolve(), out_pdf.resolve()]


def make_figure_a(rf_path: Path, out_dir: Path, top_n: int) -> list[Path]:
    import matplotlib.pyplot as plt

    rows = read_csv_rows(rf_path)
    rows = [r for r in rows if to_float(r.get("overall_rank", "")) is not None]
    rows.sort(key=lambda r: to_float(r.get("overall_rank", "")) or 1e9)
    top_rows = rows[:top_n]

    labels = [r.get("CSD Refcode", "").strip() for r in top_rows]
    values = [to_float(r.get("mean_norm_rank", "")) or 0.0 for r in top_rows]

    fig_w = max(10, min(22, 0.55 * len(labels)))
    fig, ax = plt.subplots(figsize=(fig_w, 6))
    bars = ax.bar(labels, values, linewidth=0.8, edgecolor="black")

    for i, bar in enumerate(bars[:3]):
        bar.set_hatch("///")
        bar.set_linewidth(1.6)
        ax.annotate(
            f"Top {i + 1}",
            xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    ax.set_title(f"Random Forest Ranking Overview (Top {len(top_rows)})")
    ax.set_ylabel("Mean Normalized Rank")
    ax.set_xlabel("MOF (CSD Refcode)")
    ax.tick_params(axis="x", rotation=75, labelsize=8)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()

    out = save_png_pdf(fig, out_dir, "Figure_A_RF_ranking_overview")
    plt.close(fig)
    return out


def _metric_values(rows: list[dict[str, str]], key: str) -> list[float]:
    vals = []
    for row in rows:
        num = to_float(row.get(key, ""))
        vals.append(num if num is not None else 0.0)
    return vals


def make_figure_b(top3_path: Path, out_dir: Path) -> list[Path]:
    import matplotlib.pyplot as plt

    rows = read_csv_rows(top3_path)
    rows.sort(key=lambda r: to_float(r.get("overall_rank", "")) or 1e9)

    mofs = [r.get("MOF", "").strip() for r in rows]
    x = list(range(len(mofs)))

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.8), sharex=True)
    width = 0.18
    offsets = [-1.5 * width, -0.5 * width, 0.5 * width, 1.5 * width]

    ug_ps_pred = _metric_values(rows, "ML_Predicted_PS_UG_RF")
    ug_ps_gcmc = _metric_values(rows, "GCMC_UG_PS")
    ug_tps_pred = _metric_values(rows, "ML_Predicted_TPS_UG_RF")
    ug_tps_gcmc = _metric_values(rows, "GCMC_UG_TPS")

    uv_ps_pred = _metric_values(rows, "ML_Predicted_PS_UV_RF")
    uv_ps_gcmc = _metric_values(rows, "GCMC_UV_PS")
    uv_tps_pred = _metric_values(rows, "ML_Predicted_TPS_UV_RF")
    uv_tps_gcmc = _metric_values(rows, "GCMC_UV_TPS")

    ax0 = axes[0]
    ax0.bar([i + offsets[0] for i in x], ug_ps_pred, width=width, label="UG_PS Pred", edgecolor="black")
    ax0.bar(
        [i + offsets[1] for i in x],
        ug_ps_gcmc,
        width=width,
        label="UG_PS GCMC",
        edgecolor="black",
        hatch="//",
    )
    ax0.bar([i + offsets[2] for i in x], ug_tps_pred, width=width, label="UG_TPS Pred", edgecolor="black")
    ax0.bar(
        [i + offsets[3] for i in x],
        ug_tps_gcmc,
        width=width,
        label="UG_TPS GCMC",
        edgecolor="black",
        hatch="//",
    )
    ax0.set_title("UG Metrics (wt%)")
    ax0.set_ylabel("Capacity (wt%)")
    ax0.set_xlabel("MOF")
    ax0.set_xticks(x, mofs)
    ax0.grid(axis="y", linestyle="--", alpha=0.4)
    ax0.legend(fontsize=8)

    ax1 = axes[1]
    ax1.bar([i + offsets[0] for i in x], uv_ps_pred, width=width, label="UV_PS Pred", edgecolor="black")
    ax1.bar(
        [i + offsets[1] for i in x],
        uv_ps_gcmc,
        width=width,
        label="UV_PS GCMC",
        edgecolor="black",
        hatch="//",
    )
    ax1.bar([i + offsets[2] for i in x], uv_tps_pred, width=width, label="UV_TPS Pred", edgecolor="black")
    ax1.bar(
        [i + offsets[3] for i in x],
        uv_tps_gcmc,
        width=width,
        label="UV_TPS GCMC",
        edgecolor="black",
        hatch="//",
    )
    ax1.set_title("UV Metrics (g/L)")
    ax1.set_ylabel("Capacity (g/L)")
    ax1.set_xlabel("MOF")
    ax1.set_xticks(x, mofs)
    ax1.grid(axis="y", linestyle="--", alpha=0.4)
    ax1.legend(fontsize=8)

    fig.suptitle("Corrected Capacity Comparison: RF Predicted vs Corrected GCMC", fontsize=12, y=1.02)
    fig.tight_layout()

    out = save_png_pdf(fig, out_dir, "Figure_B_corrected_capacity_comparison")
    plt.close(fig)
    return out


def make_figure_c(out_dir: Path, include_bottom_note: bool) -> list[Path]:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, 6.5))
    ax.axis("off")

    box_main = dict(boxstyle="round,pad=0.4", fc="white", ec="black", lw=1.2)
    box_branch = dict(boxstyle="round,pad=0.35", fc="white", ec="black", lw=1.0)

    ax.text(
        0.5,
        0.88,
        "RF screening (7 descriptors)",
        ha="center",
        va="center",
        bbox=box_main,
        fontsize=11,
    )
    ax.text(
        0.5,
        0.67,
        "Top 3: VAGMAT, XAFFAN, XAFFIV",
        ha="center",
        va="center",
        bbox=box_main,
        fontsize=11,
    )

    ax.text(
        0.23,
        0.36,
        "Benchmark overlap:\nVAGMAT -> compare to HyMARC",
        ha="center",
        va="center",
        bbox=box_branch,
        fontsize=10,
    )
    ax.text(
        0.77,
        0.36,
        "HyMARC N/A:\nXAFFAN, XAFFIV -> validate with\ncorrected author-run GCMC",
        ha="center",
        va="center",
        bbox=box_branch,
        fontsize=10,
    )

    ax.annotate("", xy=(0.5, 0.72), xytext=(0.5, 0.84), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.annotate("", xy=(0.30, 0.43), xytext=(0.48, 0.62), arrowprops=dict(arrowstyle="->", lw=1.3))
    ax.annotate("", xy=(0.70, 0.43), xytext=(0.52, 0.62), arrowprops=dict(arrowstyle="->", lw=1.3))

    if include_bottom_note:
        ax.text(
            0.5,
            0.12,
            "Bottom controls contextualize ranking separation",
            ha="center",
            va="center",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="black", lw=1.0),
            fontsize=9.5,
        )

    ax.set_title("Benchmark Status Diagram", fontsize=13, pad=12)
    fig.tight_layout()

    out = save_png_pdf(fig, out_dir, "Figure_C_benchmark_status_diagram")
    plt.close(fig)
    return out


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    out_dir = base_dir / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    top3_path = base_dir / "TOP3_ML_PLUS_GCMC_TABLE.csv"
    bottom_controls_path = base_dir / "BOTTOM_CONTROLS_TABLE.csv"

    created: list[Path] = []
    missing: list[Path] = []
    dependency_note = None

    try:
        import matplotlib  # noqa: F401
    except ModuleNotFoundError:
        dependency_note = (
            "Dependency missing: matplotlib\n"
            "Install with: python3 -m pip install --user matplotlib"
        )

    if RF_RANKING_CSV.exists():
        if dependency_note is None:
            created.extend(make_figure_a(RF_RANKING_CSV, out_dir, TOP_N))
    else:
        missing.append(RF_RANKING_CSV)

    if top3_path.exists():
        if dependency_note is None:
            created.extend(make_figure_b(top3_path, out_dir))
    else:
        missing.append(top3_path)

    if dependency_note is None:
        created.extend(make_figure_c(out_dir, include_bottom_note=bottom_controls_path.exists()))
    if not bottom_controls_path.exists():
        missing.append(bottom_controls_path)

    if dependency_note is not None:
        print(dependency_note)
        print()

    print("Created files:")
    if created:
        for p in sorted(created):
            print(str(p))
    else:
        print("(none)")

    if missing:
        print("\nMissing input files:")
        for p in missing:
            print(str(p.resolve() if p.is_absolute() else (base_dir / p).resolve()))
    else:
        print("\nMissing input files: none")


if __name__ == "__main__":
    main()
