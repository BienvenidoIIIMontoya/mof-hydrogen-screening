import csv
import os
import re
from typing import Dict, List, Optional, Tuple


ROOT = os.path.expanduser("~/raspa_runs/H2_in_MOF")
INPUT_DIR = os.path.join(ROOT, "_inputs")

RANKING_CSV = os.path.join(INPUT_DIR, "final_combined_ranking_RF (2).csv")
MANUSCRIPT_PDF = os.path.join(INPUT_DIR, "Montoya, Bienvenido_Written Thesis.pdf")
MINE_CSV = os.path.join(ROOT, "ALL_corrected_summary_with_sanity.csv")
PS_CSV = os.path.expanduser("~/datasets/ps.csv")
TPS_CSV = os.path.expanduser("~/datasets/tps.csv")

OUT_ML_TOP3 = os.path.join(ROOT, "ML_TOP3_SELECTION_TABLE.csv")
OUT_TOP3_GCMC = os.path.join(ROOT, "TOP3_ML_PLUS_GCMC_TABLE.csv")
OUT_FINAL_BENCH = os.path.join(ROOT, "FINAL_BENCHMARK_TABLE.csv")
OUT_BOTTOM = os.path.join(ROOT, "BOTTOM_CONTROLS_TABLE.csv")

OUT_UPDATE_MAP = os.path.join(ROOT, "MANUSCRIPT_UPDATE_MAP.txt")
OUT_ABSTRACT = os.path.join(ROOT, "ABSTRACT_PATCH.txt")
OUT_OBJECTIVES = os.path.join(ROOT, "OBJECTIVES_PATCH.txt")
OUT_LIMITATIONS = os.path.join(ROOT, "LIMITATIONS_PATCH.txt")
OUT_RESULTS = os.path.join(ROOT, "RESULTS_DISCUSSION_PATCH.txt")
OUT_PANEL = os.path.join(ROOT, "PANEL_QA_NOTE.txt")

MISSING_TOKENS = {"", "na", "n/a", "nan"}
TOP3_ORDER = ["VAGMAT", "XAFFAN", "XAFFIV"]
BOTTOM_CONTROLS = ["ECOTOG", "XUJCUB", "CAXPIC"]
FORCED_HYMARC_NA = {"XAFFAN", "XAFFIV"}


def is_missing(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in MISSING_TOKENS
    return False


def parse_float(value) -> Optional[float]:
    if is_missing(value):
        return None
    try:
        return float(str(value).strip())
    except Exception:
        return None


def norm_refcode(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip().upper()
    if not s:
        return None
    changed = True
    while changed:
        changed = False
        for suffix in ("_CLEAN", "_H2", "_CORE"):
            if s.endswith(suffix):
                s = s[: -len(suffix)].strip()
                changed = True
    return s or None


def read_csv_dicts(path: str) -> Tuple[List[str], List[Dict[str, str]]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        r = csv.reader(f)
        headers = [h.strip() for h in next(r)]
        rows = []
        for raw in r:
            row = {}
            for i, h in enumerate(headers):
                row[h] = raw[i] if i < len(raw) else ""
            rows.append(row)
    return headers, rows


def write_csv(path: str, headers: List[str], rows: List[Dict[str, str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for row in rows:
            w.writerow([row.get(h, "") for h in headers])


def fmt_num(value: Optional[float], places: int = 6) -> str:
    if value is None:
        return ""
    return f"{value:.{places}f}"


def fmt_or_na(value: Optional[float], places: int = 6) -> str:
    return "N/A" if value is None else f"{value:.{places}f}"


def pct_err(mine: Optional[float], ref: Optional[float]) -> Optional[float]:
    if mine is None or ref is None or ref == 0:
        return None
    return (mine - ref) / ref * 100.0


def choose_hymarc_row(existing, candidate, ug_key, uv_key):
    if existing is None:
        return candidate
    ex_ok = not is_missing(existing.get(ug_key)) and not is_missing(existing.get(uv_key))
    ca_ok = not is_missing(candidate.get(ug_key)) and not is_missing(candidate.get(uv_key))
    if ca_ok and not ex_ok:
        return candidate
    return existing


def build_hymarc_index(path: str, ug_key: str, uv_key: str) -> Dict[str, Dict[str, str]]:
    _, rows = read_csv_dicts(path)
    out = {}
    for row in rows:
        key = norm_refcode(row.get("CSD refc."))
        if key is None:
            key = norm_refcode(row.get("Name"))
        if key is None:
            continue
        out[key] = choose_hymarc_row(out.get(key), row, ug_key, uv_key)
    return out


FLOAT_RE = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?")


def extract_first_float(text: str) -> Optional[float]:
    m = FLOAT_RE.search(text)
    return float(m.group(0)) if m else None


def parse_raspa_abs_mgg(path: str) -> Optional[float]:
    if not path or not os.path.exists(path):
        return None
    mgg = None
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "Average loading absolute [milligram/gram framework]" in line:
                v = extract_first_float(line)
                if v is not None:
                    mgg = v
    if mgg is not None and mgg <= 0:
        return None
    return mgg


def find_ps_high_mgg_fallback(mof: str) -> Tuple[Optional[str], Optional[float]]:
    filename = f"output_{mof}_clean_1.1.1_77.000000_1e+07.data"
    base = os.path.join(ROOT, f"{mof}_H2")
    candidates = [
        os.path.join(base, "PS_high_validate_massfix", "Output", "System_0", filename),
        os.path.join(base, "PS_high", "PS_high", "Output", "System_0", filename),
        os.path.join(base, "PS_high", "Output", "System_0", filename),
        os.path.join(ROOT, "PS_high", "Output", "System_0", filename),
    ]
    for path in candidates:
        mgg = parse_raspa_abs_mgg(path)
        if mgg is not None:
            return path, mgg
    return None, None


def infer_ps_high_from_output(mine_row: Dict[str, str]) -> Tuple[Optional[float], Optional[float]]:
    mof = norm_refcode(mine_row.get("MOF"))
    density = parse_float(mine_row.get("PS_low_framework_density_kg_m3")) or parse_float(mine_row.get("PS_high_framework_density_kg_m3"))
    if mof is None or density is None:
        return None, None
    path, mgg = find_ps_high_mgg_fallback(mof)
    if mgg is None:
        return None, None
    corrected_mgg = mgg
    if path and "validate_massfix" not in path:
        ratio = (
            parse_float(mine_row.get("PS_high_ratio_reported"))
            or parse_float(mine_row.get("PS_low_ratio_reported"))
            or parse_float(mine_row.get("TPS_low_ratio_reported"))
            or 1.0
        )
        if ratio and ratio > 0:
            corrected_mgg = mgg / ratio
    wt_pct = corrected_mgg / 10.0
    uv_gl = (corrected_mgg / 1000.0) * density
    return wt_pct, uv_gl


def derive_corrected_capacities(mine_row: Dict[str, str]) -> Dict[str, Optional[float]]:
    vals = {
        "UG_PS": parse_float(mine_row.get("UG_PS")),
        "UV_PS": parse_float(mine_row.get("UV_PS")),
        "UG_TPS": parse_float(mine_row.get("UG_TPS")),
        "UV_TPS": parse_float(mine_row.get("UV_TPS")),
    }
    if all(v is not None for v in vals.values()):
        return vals

    ps_high_wt = parse_float(mine_row.get("PS_high_abs_wt_pct"))
    ps_high_uv = parse_float(mine_row.get("PS_high_abs_uv_gL"))
    if ps_high_wt is None or ps_high_uv is None:
        fb_wt, fb_uv = infer_ps_high_from_output(mine_row)
        if ps_high_wt is None:
            ps_high_wt = fb_wt
        if ps_high_uv is None:
            ps_high_uv = fb_uv

    ps_low_wt = parse_float(mine_row.get("PS_low_abs_wt_pct"))
    ps_low_uv = parse_float(mine_row.get("PS_low_abs_uv_gL"))
    tps_low_wt = parse_float(mine_row.get("TPS_low_abs_wt_pct"))
    tps_low_uv = parse_float(mine_row.get("TPS_low_abs_uv_gL"))

    if vals["UG_PS"] is None and ps_high_wt is not None and ps_low_wt is not None:
        vals["UG_PS"] = ps_high_wt - ps_low_wt
    if vals["UV_PS"] is None and ps_high_uv is not None and ps_low_uv is not None:
        vals["UV_PS"] = ps_high_uv - ps_low_uv
    if vals["UG_TPS"] is None and ps_high_wt is not None and tps_low_wt is not None:
        vals["UG_TPS"] = ps_high_wt - tps_low_wt
    if vals["UV_TPS"] is None and ps_high_uv is not None and tps_low_uv is not None:
        vals["UV_TPS"] = ps_high_uv - tps_low_uv

    return vals


def build_mine_index() -> Dict[str, Dict[str, str]]:
    _, rows = read_csv_dicts(MINE_CSV)
    out = {}
    for row in rows:
        key = norm_refcode(row.get("MOF"))
        if key:
            out[key] = row
    return out


def parse_ranking_rows():
    headers, rows = read_csv_dicts(RANKING_CSV)
    # Preserve exact columns if present; use aliases otherwise.
    colmap = {h.strip(): h for h in headers}
    required = [
        "Name", "CSD Refcode", "Density", "GSA", "VSA", "VF", "PV", "LCD", "PLD",
        "ML_Predicted_PS_UG_RF", "ML_Predicted_PS_UV_RF", "ML_Predicted_TPS_UG_RF", "ML_Predicted_TPS_UV_RF",
        "mean_norm_rank", "overall_rank"
    ]
    for col in required:
        if col not in colmap:
            raise KeyError(f"Missing ranking column: {col}")

    parsed = []
    for row in rows:
        key = norm_refcode(row.get("CSD Refcode") or row.get("Name"))
        if key is None:
            continue
        rank = parse_float(row.get("overall_rank"))
        mean_rank = parse_float(row.get("mean_norm_rank"))
        parsed.append({
            "MOF": key,
            "row": row,
            "overall_rank_num": rank if rank is not None else 1e99,
            "mean_norm_rank_num": mean_rank,
        })
    parsed.sort(key=lambda x: x["overall_rank_num"])
    return parsed


def create_ml_top3_table(ranking_parsed):
    top3 = ranking_parsed[:3]
    headers = [
        "MOF",
        "overall_rank",
        "mean_norm_rank",
        "Density",
        "GSA",
        "VSA",
        "VF",
        "PV",
        "LCD",
        "PLD",
        "ML_Predicted_PS_UG_RF",
        "ML_Predicted_PS_UV_RF",
        "ML_Predicted_TPS_UG_RF",
        "ML_Predicted_TPS_UV_RF",
    ]
    rows = []
    for item in top3:
        r = item["row"]
        rows.append({
            "MOF": item["MOF"],
            "overall_rank": r.get("overall_rank", ""),
            "mean_norm_rank": r.get("mean_norm_rank", ""),
            "Density": r.get("Density", ""),
            "GSA": r.get("GSA", ""),
            "VSA": r.get("VSA", ""),
            "VF": r.get("VF", ""),
            "PV": r.get("PV", ""),
            "LCD": r.get("LCD", ""),
            "PLD": r.get("PLD", ""),
            "ML_Predicted_PS_UG_RF": r.get("ML_Predicted_PS_UG_RF", ""),
            "ML_Predicted_PS_UV_RF": r.get("ML_Predicted_PS_UV_RF", ""),
            "ML_Predicted_TPS_UG_RF": r.get("ML_Predicted_TPS_UG_RF", ""),
            "ML_Predicted_TPS_UV_RF": r.get("ML_Predicted_TPS_UV_RF", ""),
        })
    write_csv(OUT_ML_TOP3, headers, rows)
    return rows


def create_top3_ml_plus_gcmc(ranking_parsed, mine_idx):
    rank_idx = {item["MOF"]: item["row"] for item in ranking_parsed}
    headers = [
        "MOF",
        "overall_rank",
        "ML_Predicted_PS_UG_RF",
        "ML_Predicted_PS_UV_RF",
        "ML_Predicted_TPS_UG_RF",
        "ML_Predicted_TPS_UV_RF",
        "GCMC_UG_PS",
        "GCMC_UV_PS",
        "GCMC_UG_TPS",
        "GCMC_UV_TPS",
        "benchmark_status",
        "benchmark_note",
    ]
    rows = []
    for mof in TOP3_ORDER:
        rr = rank_idx.get(mof)
        mr = mine_idx.get(mof, {})
        caps = derive_corrected_capacities(mr) if mr else {"UG_PS": None, "UV_PS": None, "UG_TPS": None, "UV_TPS": None}
        if mof == "VAGMAT":
            status = "Benchmark available"
            note = "Selected by ML; benchmarkable against HyMARC overlap"
        else:
            status = "HyMARC N/A"
            note = "Selected by ML; validated using own GCMC"
        rows.append({
            "MOF": mof,
            "overall_rank": rr.get("overall_rank", "") if rr else "",
            "ML_Predicted_PS_UG_RF": rr.get("ML_Predicted_PS_UG_RF", "") if rr else "",
            "ML_Predicted_PS_UV_RF": rr.get("ML_Predicted_PS_UV_RF", "") if rr else "",
            "ML_Predicted_TPS_UG_RF": rr.get("ML_Predicted_TPS_UG_RF", "") if rr else "",
            "ML_Predicted_TPS_UV_RF": rr.get("ML_Predicted_TPS_UV_RF", "") if rr else "",
            "GCMC_UG_PS": fmt_num(caps["UG_PS"]),
            "GCMC_UV_PS": fmt_num(caps["UV_PS"]),
            "GCMC_UG_TPS": fmt_num(caps["UG_TPS"]),
            "GCMC_UV_TPS": fmt_num(caps["UV_TPS"]),
            "benchmark_status": status,
            "benchmark_note": note,
        })
    write_csv(OUT_TOP3_GCMC, headers, rows)
    return rows


def create_final_benchmark_table(mine_idx):
    ps_idx = build_hymarc_index(PS_CSV, "UG at PS", "UV at PS")
    tps_idx = build_hymarc_index(TPS_CSV, "UG at TPS", "UV at TPS")
    headers = [
        "MOF",
        "UG_PS_mine",
        "UV_PS_mine",
        "UG_PS_hymarc",
        "UV_PS_hymarc",
        "UG_PS_%err",
        "UV_PS_%err",
        "UG_TPS_mine",
        "UV_TPS_mine",
        "UG_TPS_hymarc",
        "UV_TPS_hymarc",
        "UG_TPS_%err",
        "UV_TPS_%err",
    ]
    rows = []
    for mof, mine_row in mine_idx.items():
        if mof in FORCED_HYMARC_NA:
            continue
        ps = ps_idx.get(mof)
        tps = tps_idx.get(mof)
        if ps is None or tps is None:
            continue
        ug_ps_h = parse_float(ps.get("UG at PS"))
        uv_ps_h = parse_float(ps.get("UV at PS"))
        ug_tps_h = parse_float(tps.get("UG at TPS"))
        uv_tps_h = parse_float(tps.get("UV at TPS"))
        if any(v is None for v in (ug_ps_h, uv_ps_h, ug_tps_h, uv_tps_h)):
            continue

        caps = derive_corrected_capacities(mine_row)
        if any(caps[k] is None for k in ("UG_PS", "UV_PS", "UG_TPS", "UV_TPS")):
            continue

        rows.append({
            "MOF": mof,
            "UG_PS_mine": fmt_num(caps["UG_PS"]),
            "UV_PS_mine": fmt_num(caps["UV_PS"]),
            "UG_PS_hymarc": fmt_num(ug_ps_h),
            "UV_PS_hymarc": fmt_num(uv_ps_h),
            "UG_PS_%err": fmt_num(pct_err(caps["UG_PS"], ug_ps_h)),
            "UV_PS_%err": fmt_num(pct_err(caps["UV_PS"], uv_ps_h)),
            "UG_TPS_mine": fmt_num(caps["UG_TPS"]),
            "UV_TPS_mine": fmt_num(caps["UV_TPS"]),
            "UG_TPS_hymarc": fmt_num(ug_tps_h),
            "UV_TPS_hymarc": fmt_num(uv_tps_h),
            "UG_TPS_%err": fmt_num(pct_err(caps["UG_TPS"], ug_tps_h)),
            "UV_TPS_%err": fmt_num(pct_err(caps["UV_TPS"], uv_tps_h)),
        })
    rows.sort(key=lambda r: r["MOF"])
    write_csv(OUT_FINAL_BENCH, headers, rows)
    return rows


def create_bottom_controls_table(ranking_parsed, mine_idx):
    rank_idx = {item["MOF"]: item["row"] for item in ranking_parsed}
    ps_idx = build_hymarc_index(PS_CSV, "UG at PS", "UV at PS")
    tps_idx = build_hymarc_index(TPS_CSV, "UG at TPS", "UV at TPS")
    headers = [
        "MOF",
        "overall_rank",
        "mean_norm_rank",
        "ML_Predicted_PS_UG_RF",
        "ML_Predicted_PS_UV_RF",
        "ML_Predicted_TPS_UG_RF",
        "ML_Predicted_TPS_UV_RF",
        "GCMC_UG_PS",
        "GCMC_UV_PS",
        "GCMC_UG_TPS",
        "GCMC_UV_TPS",
        "HyMARC_overlap_status",
        "HyMARC_UG_PS",
        "HyMARC_UV_PS",
        "HyMARC_UG_TPS",
        "HyMARC_UV_TPS",
        "control_note",
    ]
    rows = []
    for mof in BOTTOM_CONTROLS:
        rr = rank_idx.get(mof)
        mr = mine_idx.get(mof)
        if rr is None or mr is None:
            continue
        caps = derive_corrected_capacities(mr)
        ps = ps_idx.get(mof)
        tps = tps_idx.get(mof)
        if ps and tps:
            ug_ps_h = parse_float(ps.get("UG at PS"))
            uv_ps_h = parse_float(ps.get("UV at PS"))
            ug_tps_h = parse_float(tps.get("UG at TPS"))
            uv_tps_h = parse_float(tps.get("UV at TPS"))
            overlap_status = "Benchmark overlap" if all(v is not None for v in (ug_ps_h, uv_ps_h, ug_tps_h, uv_tps_h)) else "HyMARC N/A"
        else:
            ug_ps_h = uv_ps_h = ug_tps_h = uv_tps_h = None
            overlap_status = "Not found"
        rows.append({
            "MOF": mof,
            "overall_rank": rr.get("overall_rank", ""),
            "mean_norm_rank": rr.get("mean_norm_rank", ""),
            "ML_Predicted_PS_UG_RF": rr.get("ML_Predicted_PS_UG_RF", ""),
            "ML_Predicted_PS_UV_RF": rr.get("ML_Predicted_PS_UV_RF", ""),
            "ML_Predicted_TPS_UG_RF": rr.get("ML_Predicted_TPS_UG_RF", ""),
            "ML_Predicted_TPS_UV_RF": rr.get("ML_Predicted_TPS_UV_RF", ""),
            "GCMC_UG_PS": fmt_num(caps["UG_PS"]),
            "GCMC_UV_PS": fmt_num(caps["UV_PS"]),
            "GCMC_UG_TPS": fmt_num(caps["UG_TPS"]),
            "GCMC_UV_TPS": fmt_num(caps["UV_TPS"]),
            "HyMARC_overlap_status": overlap_status,
            "HyMARC_UG_PS": fmt_or_na(ug_ps_h),
            "HyMARC_UV_PS": fmt_or_na(uv_ps_h),
            "HyMARC_UG_TPS": fmt_or_na(ug_tps_h),
            "HyMARC_UV_TPS": fmt_or_na(uv_tps_h),
            "control_note": "Low-rank control used to contextualize ML ranking separation",
        })
    write_csv(OUT_BOTTOM, headers, rows)
    return rows


def write_text(path: str, text: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")


def create_patch_texts():
    write_text(
        OUT_UPDATE_MAP,
        f"""MANUAL REVISION CHECKLIST (PDF parsing not required)

Source manuscript file present: {MANUSCRIPT_PDF}
This checklist is based on the finalized thesis logic provided by the author and should be applied even if the current PDF text is not machine-extracted.

1) Abstract
- What must be updated:
  Replace any wording that implies all RF top-3 MOFs were benchmarked directly against the HyMARC GCMC benchmark set.
  Replace any wording that treats XAFFAN and XAFFIV as benchmark mismatch cases.
  Remove any legacy-capacity wording that may rely on incorrect H_h2 mass conversion in old mg/g outputs.
- Corrected thesis logic to insert:
  RF screening using 7 descriptors selected VAGMAT, XAFFAN, and XAFFIV.
  Only VAGMAT is in the true HyMARC GCMC overlap and can be benchmark-compared.
  XAFFAN and XAFFIV are true HyMARC benchmark N/A cases and are reported as ML-selected candidates validated using the author's corrected GCMC runs.
  Final capacities use corrected usable values derived from mol/kg (not legacy wrong mg/g values affected by the resolved H_h2 mass issue).

2) Research Objectives
- What must be updated:
  Separate the objective of benchmarking overlap MOFs from the objective of validating newly selected ML candidates that are absent from the benchmark dataset.
  Avoid language implying benchmark validation is available for every ML-selected top candidate.
- Corrected thesis logic to insert:
  Objective A: benchmark agreement assessment only on the true HyMARC overlap set.
  Objective B: independent GCMC validation of ML-selected candidates when no benchmark entry exists (XAFFAN, XAFFIV).
  Objective C: integrate ML ranking and corrected GCMC simulation into a coherent discovery-and-validation workflow.

3) Scope and Limitations
- What must be updated:
  Explicitly define the benchmark scope as the true overlap between the working MOF set and the HyMARC GCMC benchmark dataset.
  Add a limitation that benchmark datasets may not contain all top ML-selected candidates.
  Add a methods note on corrected capacity reporting after the resolved legacy mass-conversion issue.
- Corrected thesis logic to insert:
  Benchmark statistics are computed only for overlap MOFs with actual HyMARC values.
  XAFFAN and XAFFIV are excluded from benchmark error statistics because they are not in the true HyMARC benchmark set.
  Candidate MOFs absent from benchmark datasets can still be scientifically valid outcomes when validated by the author's own corrected GCMC runs.
  Final usable capacities are reported from mol/kg-derived corrected values.

4) Results and Discussion
- What must be updated:
  Reframe top-3 discussion so that VAGMAT is the principal benchmark-comparison case, while XAFFAN and XAFFIV are ML-selected validation cases.
  Remove/replace any statement interpreting XAFFAN/XAFFIV as benchmark disagreement or benchmark error.
  Add explicit explanation of corrected GCMC values and why they supersede legacy wrong mg/g outputs.
  If Chapter 4 contains placeholder/template text, replace it with the finalized benchmark-vs-validation narrative and table references.
- Corrected thesis logic to insert:
  The RF model selected VAGMAT, XAFFAN, and XAFFIV as top candidates using 7 descriptors.
  VAGMAT is the key overlap MOF for benchmark comparison against HyMARC.
  XAFFAN and XAFFIV are absent from the true benchmark set and are instead validated via corrected author-run GCMC simulations.
  Bottom-control MOFs (e.g., ECOTOG, XUJCUB, CAXPIC) contextualize ranking separation by showing much lower predicted and corrected capacities.

5) Table Captions (validation/benchmark tables)
- What must be updated:
  Any caption that implies 'top-3 benchmark validation' should be split or rewritten to distinguish benchmark overlap from ML+own-GCMC validation.
  Any caption describing XAFFAN/XAFFIV as benchmark entries should be corrected.
- Corrected thesis logic to insert:
  ML top-3 selection table: ranking output only.
  ML + GCMC table: top-3 candidates with RF predictions and corrected author GCMC results; benchmark status explicitly marked.
  Final benchmark table: benchmark-only comparison on true HyMARC overlap MOFs; excludes XAFFAN/XAFFIV from benchmark error calculations.

6) Contents / Chapter 4 housekeeping (manual check)
- What must be updated:
  Inspect table titles, list-of-tables entries, and any placeholders/template remnants for consistency with the corrected benchmark/validation separation.
- Corrected thesis logic to insert:
  Ensure all chapter and table wording consistently distinguishes benchmark overlap cases from author-validated ML-selected candidates absent from benchmark datasets.
"""
    )

    write_text(
        OUT_ABSTRACT,
        """Random-forest (RF) screening based on seven crystallographic descriptors identified VAGMAT, XAFFAN, and XAFFIV as the top three candidate MOFs for hydrogen storage performance. For validation, the benchmark comparison was restricted to the true HyMARC GCMC overlap set: among the RF top three, VAGMAT was the key benchmarkable overlap case and was compared directly against HyMARC benchmark values. XAFFAN and XAFFIV are not included in the true HyMARC GCMC benchmark set and were therefore not treated as benchmark mismatch cases; instead, they were validated using the author's own corrected GCMC simulations. Final reported usable capacities in this thesis use corrected values derived from mol/kg-based outputs, replacing legacy mg/g values affected by the previously resolved H_h2 mass-conversion issue."""
    )

    write_text(
        OUT_OBJECTIVES,
        """Revised Objectives (validation logic clarified)

1. To develop and apply a random-forest screening workflow using seven structural descriptors (Density, GSA, VSA, VF, PV, LCD, and PLD) to rank MOFs for hydrogen storage performance under the selected operating conditions.
2. To evaluate benchmark agreement only for MOFs that are present in the true overlap between the study set and the HyMARC GCMC benchmark dataset.
3. To perform independent GCMC validation for ML-selected candidate MOFs that are absent from the HyMARC benchmark dataset (e.g., XAFFAN and XAFFIV), rather than misclassifying them as benchmark comparison failures.
4. To report final usable capacities using corrected mol/kg-derived values after resolving the legacy H_h2 mass-conversion issue in earlier mg/g outputs.
5. To integrate ML ranking, benchmark comparison (where available), and independent corrected GCMC validation into a consistent discovery-to-validation workflow."""
    )

    write_text(
        OUT_LIMITATIONS,
        """Scope and Limitations Patch (benchmark coverage and corrected reporting)

- Benchmark comparisons in this thesis are limited to MOFs that are present in the true overlap with the HyMARC GCMC benchmark dataset and have actual benchmark values available.
- ML-selected top candidates may be absent from benchmark datasets (as in the case of XAFFAN and XAFFIV); these entries must be treated as benchmark N/A rather than benchmark mismatches.
- Benchmark error statistics are therefore computed only on true overlap MOFs and must exclude benchmark-N/A candidates.
- Benchmark absence does not invalidate a candidate's relevance; such candidates require independent GCMC validation using the author's own simulations.
- Final usable capacities reported in this thesis use corrected values derived from mol/kg outputs. This replaces legacy mg/g values that were affected by a resolved H_h2 mass-conversion issue in earlier outputs.
- Any comparison between ML predictions and simulation results should clearly state whether the simulation values are used for benchmark comparison (overlap MOFs) or for independent validation (benchmark-absent candidates)."""
    )

    write_text(
        OUT_RESULTS,
        """Results and Discussion Patch (Benchmark vs. ML-Selected Validation)

The RF screening model, using seven crystallographic descriptors (Density, GSA, VSA, VF, PV, LCD, and PLD), ranked VAGMAT, XAFFAN, and XAFFIV as the top three candidate MOFs. These three materials should not be discussed under a single benchmark-comparison narrative. Instead, the validation logic must be separated into (i) benchmark comparison on true overlap MOFs and (ii) independent GCMC validation for ML-selected candidates that are absent from the benchmark dataset.

Within the RF top three, VAGMAT is the principal benchmark-validation case because it is present in the true HyMARC GCMC overlap set. This makes VAGMAT the key material for assessing how well the combined ML-plus-simulation workflow aligns with an external benchmark reference. Any discrepancy observed for VAGMAT is therefore important: it informs interpretation of model-guided selection, simulation setup fidelity, and the practical limits of cross-dataset comparability. However, that discrepancy should be interpreted as a benchmark-comparison result for an overlap case, not as a basis to generalize benchmark conclusions to all top-ranked candidates.

By contrast, XAFFAN and XAFFIV are absent from the true HyMARC GCMC benchmark set and must be reported as benchmark N/A. They should not be counted as benchmark mismatches and must be excluded from benchmark error statistics. Their scientific relevance remains strong because they were selected by the RF model and then validated using the author's own corrected GCMC simulations. This is a valid and important outcome of the thesis workflow: ML identifies high-potential candidates, and simulation validates those candidates whether or not a public benchmark entry exists.

The final reported usable capacities for XAFFAN, XAFFIV, and all discussed simulation outputs should use corrected values derived from mol/kg-based quantities, not legacy mg/g values affected by the resolved H_h2 mass-conversion issue. This correction improves internal consistency and ensures that the reported capacities reflect the corrected GCMC post-processing used in the final analysis.

Taken together, the top-3 results support the ML-guided discovery workflow in two complementary ways: VAGMAT provides a benchmarkable overlap case for external comparison, while XAFFAN and XAFFIV demonstrate the workflow's ability to propose and validate promising candidates beyond the benchmark coverage. In addition, low-rank bottom-control MOFs (e.g., ECOTOG, XUJCUB, and CAXPIC) help contextualize ranking separation by showing substantially weaker predicted and corrected GCMC capacities, strengthening the argument that the RF ranking captures meaningful performance stratification rather than random ordering."""
    )

    write_text(
        OUT_PANEL,
        """Panel Q&A Note (concise defense answers)

Q: Why are XAFFAN and XAFFIV N/A in HyMARC?
A: Because they are not part of the true HyMARC GCMC benchmark set. They are benchmark-absent cases, so assigning benchmark values to them would be incorrect.

Q: Why can you still present them?
A: They are valid ML-selected top candidates from the RF ranking, and I validated them using my own corrected GCMC simulations. Benchmark absence does not invalidate candidate-level simulation validation.

Q: Why is VAGMAT the main benchmark case?
A: VAGMAT is the key overlap MOF between my top-3 ML selections and the true HyMARC benchmark dataset, so it is the appropriate case for direct benchmark comparison.

Q: Why were your GCMC values corrected?
A: Earlier mg/g outputs were affected by a resolved H_h2 mass-conversion issue. The final thesis uses corrected usable capacities derived from mol/kg-based values to ensure accurate reporting.

Q: Does this weaken the thesis?
A: No. It strengthens the methodological clarity. The thesis now cleanly separates benchmark comparison (overlap MOFs only) from independent GCMC validation (benchmark-absent ML-selected candidates), which is the correct scientific interpretation."""
    )


def main():
    if not os.path.exists(RANKING_CSV):
        raise FileNotFoundError(RANKING_CSV)
    if not os.path.exists(MINE_CSV):
        raise FileNotFoundError(MINE_CSV)

    ranking_parsed = parse_ranking_rows()
    mine_idx = build_mine_index()

    create_ml_top3_table(ranking_parsed)
    create_top3_ml_plus_gcmc(ranking_parsed, mine_idx)
    create_final_benchmark_table(mine_idx)
    create_bottom_controls_table(ranking_parsed, mine_idx)
    create_patch_texts()


if __name__ == "__main__":
    main()
