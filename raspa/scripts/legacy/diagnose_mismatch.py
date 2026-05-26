#!/usr/bin/env python3
import csv
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path.home() / "raspa_runs" / "H2_in_MOF"
PS_JOIN = ROOT / "MINE_vs_DATASETS_PS.csv"
TPS_JOIN = ROOT / "MINE_vs_DATASETS_TPS.csv"
SUMMARY = ROOT / "ALL_corrected_summary_with_sanity.csv"
OUT_SIG = ROOT / "MISMATCH_SIGNATURES.csv"
OUT_DENS = ROOT / "DENSITY_REBASE_REPORT.csv"


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_float(v: Optional[str]) -> Optional[float]:
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def pct_err(mine: Optional[float], data: Optional[float]) -> Optional[float]:
    if mine is None or data is None or data == 0:
        return None
    return 100.0 * (mine - data) / data


def classify(ug_err: Optional[float], uv_err: Optional[float]) -> str:
    # Per instruction: protocol/model candidate if |UG_err| >= 20 regardless of UV.
    if ug_err is not None and abs(ug_err) >= 20.0:
        return "protocol_or_model_candidate"
    if ug_err is not None and uv_err is not None and abs(uv_err) > abs(ug_err) + 20.0:
        return "density_basis_candidate"
    return "minor"


def pick_cols(rows: List[Dict[str, str]], phase: str):
    cols = list(rows[0].keys()) if rows else []

    def find(req: List[str]) -> str:
        req = [r.lower() for r in req]
        for c in cols:
            lc = c.lower()
            if all(r in lc for r in req):
                return c
        return ""

    mine_ug = find(["my", "ug", phase.lower()]) or find(["my", "ug"])
    mine_uv = find(["my", "uv", phase.lower()]) or find(["my", "uv"])
    data_ug = find(["dataset", "ug", phase.lower()]) or find(["dataset", "ug"])
    data_uv = find(["dataset", "uv", phase.lower()]) or find(["dataset", "uv"])
    mof = "MOF" if "MOF" in cols else cols[0]
    return mof, mine_ug, mine_uv, data_ug, data_uv


def build_signatures() -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []

    for phase, path in [("PS", PS_JOIN), ("TPS", TPS_JOIN)]:
        rows = read_csv(path)
        if not rows:
            continue
        mof_col, mine_ug_col, mine_uv_col, data_ug_col, data_uv_col = pick_cols(rows, phase)

        for r in rows:
            mof = (r.get(mof_col) or "").strip()
            if mof == "":
                continue

            ug_mine = to_float(r.get(mine_ug_col))
            ug_data = to_float(r.get(data_ug_col))
            uv_mine = to_float(r.get(mine_uv_col))
            uv_data = to_float(r.get(data_uv_col))

            ug_err = pct_err(ug_mine, ug_data)
            uv_err = pct_err(uv_mine, uv_data)
            gap = None
            if ug_err is not None and uv_err is not None:
                gap = abs(uv_err) - abs(ug_err)

            row = {
                "phase": phase,
                "MOF": mof,
                "UG_mine": "" if ug_mine is None else f"{ug_mine:.6f}",
                "UG_data": "" if ug_data is None else f"{ug_data:.6f}",
                "UG_pct_err_mine_vs_data": "" if ug_err is None else f"{ug_err:.3f}",
                "UV_mine": "" if uv_mine is None else f"{uv_mine:.6f}",
                "UV_data": "" if uv_data is None else f"{uv_data:.6f}",
                "UV_pct_err_mine_vs_data": "" if uv_err is None else f"{uv_err:.3f}",
                "err_gap_absUV_minus_absUG_pct": "" if gap is None else f"{gap:.3f}",
                "classification": classify(ug_err, uv_err),
                "dataset_refcode": r.get("dataset_refcode", ""),
                "dataset_name": r.get("dataset_name", ""),
            }
            out.append(row)

    with OUT_SIG.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "phase", "MOF", "UG_mine", "UG_data", "UG_pct_err_mine_vs_data",
            "UV_mine", "UV_data", "UV_pct_err_mine_vs_data",
            "err_gap_absUV_minus_absUG_pct", "classification", "dataset_refcode", "dataset_name",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out)

    return out


def get_density_map() -> Dict[str, float]:
    rows = read_csv(SUMMARY)
    d: Dict[str, float] = {}
    for r in rows:
        mof = (r.get("MOF") or "").strip()
        if not mof:
            continue
        rho = to_float(r.get("PS_high_framework_density_kg_m3"))
        if rho is None:
            rho = to_float(r.get("PS_low_framework_density_kg_m3"))
        if rho is None:
            rho = to_float(r.get("TPS_low_framework_density_kg_m3"))
        if rho is not None:
            d[mof] = rho
    return d


def build_density_report(sig_rows: List[Dict[str, str]]) -> None:
    rho_map = get_density_map()
    out = []

    for r in sig_rows:
        mof = r["MOF"]
        phase = r["phase"]
        rho_crystal = rho_map.get(mof)
        uv_mine = to_float(r.get("UV_mine"))
        uv_data = to_float(r.get("UV_data"))

        scale = None
        rho_needed = None
        rho_needed_gcc = None
        plaus = ""

        if rho_crystal is not None and uv_mine is not None and uv_data is not None and uv_mine != 0:
            scale = uv_data / uv_mine
            rho_needed = rho_crystal * scale
            rho_needed_gcc = rho_needed / 1000.0
            plaus = "plausible_bulk" if 0.2 <= rho_needed_gcc <= 1.2 else "implausible_bulk"

        out.append({
            "phase": phase,
            "MOF": mof,
            "rho_crystal_kg_m3": "" if rho_crystal is None else f"{rho_crystal:.6f}",
            "rho_crystal_g_cm3": "" if rho_crystal is None else f"{rho_crystal/1000.0:.6f}",
            "UV_mine_g_L": "" if uv_mine is None else f"{uv_mine:.6f}",
            "UV_data_g_L": "" if uv_data is None else f"{uv_data:.6f}",
            "uv_scale_data_over_mine": "" if scale is None else f"{scale:.6f}",
            "rho_needed_kg_m3": "" if rho_needed is None else f"{rho_needed:.6f}",
            "rho_needed_g_cm3": "" if rho_needed_gcc is None else f"{rho_needed_gcc:.6f}",
            "plausibility": plaus,
            "classification_from_stepA": r.get("classification", ""),
        })

    with OUT_DENS.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "phase", "MOF", "rho_crystal_kg_m3", "rho_crystal_g_cm3", "UV_mine_g_L", "UV_data_g_L",
            "uv_scale_data_over_mine", "rho_needed_kg_m3", "rho_needed_g_cm3", "plausibility",
            "classification_from_stepA",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out)


def main() -> int:
    sig = build_signatures()
    build_density_report(sig)

    print(f"[WRITE] {OUT_SIG}")
    print(f"[WRITE] {OUT_DENS}")

    # concise console output per MOF/phase
    print("\n=== Mismatch Signatures ===")
    for r in sig:
        print(
            f"{r['phase']:>3} {r['MOF']:<8} UG(mine/data/err%)={r['UG_mine']}/{r['UG_data']}/{r['UG_pct_err_mine_vs_data']} "
            f"UV(mine/data/err%)={r['UV_mine']}/{r['UV_data']}/{r['UV_pct_err_mine_vs_data']} "
            f"gap={r['err_gap_absUV_minus_absUG_pct']} class={r['classification']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
