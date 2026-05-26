import csv
import os
import re
from statistics import mean, median


ROOT = os.path.expanduser("~/raspa_runs/H2_in_MOF")
PS_CSV = os.path.expanduser("~/datasets/ps.csv")
TPS_CSV = os.path.expanduser("~/datasets/tps.csv")
MINE_CSV = os.path.join(ROOT, "ALL_corrected_summary_with_sanity.csv")

BENCHMARK_OUT = os.path.join(ROOT, "HY_MOF_BENCHMARK.csv")
TOP3_OUT = os.path.join(ROOT, "TOP3_ML_VERIFICATION_TABLE.csv")
SUMMARY_OUT = os.path.join(ROOT, "SUMMARY_STATS.txt")

MISSING_TOKENS = {"", "na", "n/a", "nan"}
TOP3_MOFS = ["VAGMAT", "XAFFIV", "XAFFAN"]
FORCED_HYMARC_NA = {"XAFFIV", "XAFFAN"}


def is_missing(value):
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in MISSING_TOKENS
    return False


def normalize_refcode(value):
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
    return s


def parse_float(value):
    if is_missing(value):
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def fmt_num(value, places=6):
    if value is None:
        return ""
    return f"{value:.{places}f}"


def fmt_na_or_num(value, places=6):
    if value is None:
        return "N/A"
    return f"{value:.{places}f}"


def load_csv_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        headers = [h.strip() for h in next(reader)]
        rows = []
        for raw in reader:
            row = {}
            for i, h in enumerate(headers):
                row[h] = raw[i] if i < len(raw) else ""
            rows.append(row)
    return headers, rows


def choose_preferred_row(existing, candidate, ug_col, uv_col):
    if existing is None:
        return candidate
    ex_ok = (not is_missing(existing.get(ug_col))) and (not is_missing(existing.get(uv_col)))
    ca_ok = (not is_missing(candidate.get(ug_col))) and (not is_missing(candidate.get(uv_col)))
    if ca_ok and not ex_ok:
        return candidate
    return existing


def build_hymarc_index(path, ug_col, uv_col):
    _, rows = load_csv_rows(path)
    idx = {}
    for row in rows:
        key = normalize_refcode(row.get("CSD refc."))
        if key is None:
            key = normalize_refcode(row.get("Name"))
        if key is None:
            continue
        idx[key] = choose_preferred_row(idx.get(key), row, ug_col, uv_col)
    return idx


FLOAT_RE = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?")


def extract_first_float(text):
    m = FLOAT_RE.search(text)
    return float(m.group(0)) if m else None


def parse_raspa_abs_mgg(path):
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


def find_ps_high_mgg_fallback(mof):
    base = os.path.join(ROOT, f"{mof}_H2")
    filename = f"output_{mof}_clean_1.1.1_77.000000_1e+07.data"
    candidates = [
        os.path.join(base, "PS_high_validate_massfix", "Output", "System_0", filename),
        os.path.join(base, "PS_high", "PS_high", "Output", "System_0", filename),
        os.path.join(base, "PS_high", "Output", "System_0", filename),
        os.path.join(ROOT, "PS_high", "Output", "System_0", filename),
    ]
    for path in candidates:
        mgg = parse_raspa_abs_mgg(path)
        if mgg is not None:
            # validate_massfix outputs are already mass-corrected; standard outputs need ratio correction
            return path, mgg
    return None, None


def infer_ps_high_corrected_from_output(row):
    mof = (row.get("MOF") or "").strip().upper()
    density = parse_float(row.get("PS_low_framework_density_kg_m3")) or parse_float(row.get("PS_high_framework_density_kg_m3"))
    if not mof or density is None:
        return None, None, None
    path, mgg = find_ps_high_mgg_fallback(mof)
    if mgg is None:
        return None, None, None

    corrected_mgg = mgg
    if "validate_massfix" not in (path or ""):
        ratio = (
            parse_float(row.get("PS_high_ratio_reported"))
            or parse_float(row.get("PS_low_ratio_reported"))
            or parse_float(row.get("TPS_low_ratio_reported"))
            or 1.0
        )
        if ratio and ratio > 0:
            corrected_mgg = mgg / ratio

    wt_pct = corrected_mgg / 10.0
    uv_gl = (corrected_mgg / 1000.0) * density
    return corrected_mgg, wt_pct, uv_gl


def derive_mine_metrics(row):
    values = {
        "UG_PS_mine": parse_float(row.get("UG_PS")),
        "UV_PS_mine": parse_float(row.get("UV_PS")),
        "UG_TPS_mine": parse_float(row.get("UG_TPS")),
        "UV_TPS_mine": parse_float(row.get("UV_TPS")),
    }
    if all(v is not None for v in values.values()):
        return values

    ps_high_wt = parse_float(row.get("PS_high_abs_wt_pct"))
    ps_high_uv = parse_float(row.get("PS_high_abs_uv_gL"))
    ps_low_wt = parse_float(row.get("PS_low_abs_wt_pct"))
    ps_low_uv = parse_float(row.get("PS_low_abs_uv_gL"))
    tps_low_wt = parse_float(row.get("TPS_low_abs_wt_pct"))
    tps_low_uv = parse_float(row.get("TPS_low_abs_uv_gL"))

    if ps_high_wt is None or ps_high_uv is None:
        _, ps_high_wt_fallback, ps_high_uv_fallback = infer_ps_high_corrected_from_output(row)
        if ps_high_wt is None:
            ps_high_wt = ps_high_wt_fallback
        if ps_high_uv is None:
            ps_high_uv = ps_high_uv_fallback

    if values["UG_PS_mine"] is None and ps_high_wt is not None and ps_low_wt is not None:
        values["UG_PS_mine"] = ps_high_wt - ps_low_wt
    if values["UV_PS_mine"] is None and ps_high_uv is not None and ps_low_uv is not None:
        values["UV_PS_mine"] = ps_high_uv - ps_low_uv
    if values["UG_TPS_mine"] is None and ps_high_wt is not None and tps_low_wt is not None:
        values["UG_TPS_mine"] = ps_high_wt - tps_low_wt
    if values["UV_TPS_mine"] is None and ps_high_uv is not None and tps_low_uv is not None:
        values["UV_TPS_mine"] = ps_high_uv - tps_low_uv

    return values


def pct_error(mine, ref):
    if mine is None or ref is None or ref == 0:
        return None
    return ((mine - ref) / ref) * 100.0


def presence_status_in_index(index, key, ug_col, uv_col):
    row = index.get(key)
    if row is None:
        return "not present in dataset"
    if is_missing(row.get(ug_col)) or is_missing(row.get(uv_col)):
        return "present but N/A"
    return "present with values"


def write_csv(path, headers, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for row in rows:
            w.writerow([row.get(h, "") for h in headers])


def main():
    ps_idx = build_hymarc_index(PS_CSV, "UG at PS", "UV at PS")
    tps_idx = build_hymarc_index(TPS_CSV, "UG at TPS", "UV at TPS")
    _, mine_rows = load_csv_rows(MINE_CSV)

    benchmark_headers = [
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
    benchmark_rows = []

    top3_headers = [
        "MOF",
        "UG_PS_mine",
        "UV_PS_mine",
        "UG_TPS_mine",
        "UV_TPS_mine",
        "UG_PS_hymarc",
        "UV_PS_hymarc",
        "UG_TPS_hymarc",
        "UV_TPS_hymarc",
        "hymarc_status",
    ]
    top3_rows = []

    abs_errs = {"UG_PS": [], "UV_PS": [], "UG_TPS": [], "UV_TPS": []}
    excluded_hymarc_na = 0
    skipped_missing_mine = 0

    mine_by_key = {}
    for row in mine_rows:
        key = normalize_refcode(row.get("MOF"))
        if key:
            mine_by_key[key] = row

    for row in mine_rows:
        mof = (row.get("MOF") or "").strip()
        key = normalize_refcode(mof)
        if not key:
            continue

        mine = derive_mine_metrics(row)
        ps = ps_idx.get(key)
        tps = tps_idx.get(key)

        if key in FORCED_HYMARC_NA:
            hymarc = {
                "UG_PS_hymarc": None,
                "UV_PS_hymarc": None,
                "UG_TPS_hymarc": None,
                "UV_TPS_hymarc": None,
            }
        else:
            hymarc = {
                "UG_PS_hymarc": parse_float(ps.get("UG at PS")) if ps else None,
                "UV_PS_hymarc": parse_float(ps.get("UV at PS")) if ps else None,
                "UG_TPS_hymarc": parse_float(tps.get("UG at TPS")) if tps else None,
                "UV_TPS_hymarc": parse_float(tps.get("UV at TPS")) if tps else None,
            }

        hymarc_complete = all(v is not None for v in hymarc.values())
        if not hymarc_complete:
            excluded_hymarc_na += 1
        else:
            if all(mine[k] is not None for k in ("UG_PS_mine", "UV_PS_mine", "UG_TPS_mine", "UV_TPS_mine")):
                ug_ps_err = pct_error(mine["UG_PS_mine"], hymarc["UG_PS_hymarc"])
                uv_ps_err = pct_error(mine["UV_PS_mine"], hymarc["UV_PS_hymarc"])
                ug_tps_err = pct_error(mine["UG_TPS_mine"], hymarc["UG_TPS_hymarc"])
                uv_tps_err = pct_error(mine["UV_TPS_mine"], hymarc["UV_TPS_hymarc"])
                benchmark_rows.append(
                    {
                        "MOF": mof,
                        "UG_PS_mine": fmt_num(mine["UG_PS_mine"]),
                        "UV_PS_mine": fmt_num(mine["UV_PS_mine"]),
                        "UG_PS_hymarc": fmt_num(hymarc["UG_PS_hymarc"]),
                        "UV_PS_hymarc": fmt_num(hymarc["UV_PS_hymarc"]),
                        "UG_PS_%err": fmt_num(ug_ps_err),
                        "UV_PS_%err": fmt_num(uv_ps_err),
                        "UG_TPS_mine": fmt_num(mine["UG_TPS_mine"]),
                        "UV_TPS_mine": fmt_num(mine["UV_TPS_mine"]),
                        "UG_TPS_hymarc": fmt_num(hymarc["UG_TPS_hymarc"]),
                        "UV_TPS_hymarc": fmt_num(hymarc["UV_TPS_hymarc"]),
                        "UG_TPS_%err": fmt_num(ug_tps_err),
                        "UV_TPS_%err": fmt_num(uv_tps_err),
                    }
                )
                if ug_ps_err is not None:
                    abs_errs["UG_PS"].append(abs(ug_ps_err))
                if uv_ps_err is not None:
                    abs_errs["UV_PS"].append(abs(uv_ps_err))
                if ug_tps_err is not None:
                    abs_errs["UG_TPS"].append(abs(ug_tps_err))
                if uv_tps_err is not None:
                    abs_errs["UV_TPS"].append(abs(uv_tps_err))
            else:
                skipped_missing_mine += 1

    for mof in TOP3_MOFS:
        key = normalize_refcode(mof)
        row = mine_by_key.get(key, {})
        mine = derive_mine_metrics(row) if row else {
            "UG_PS_mine": None,
            "UV_PS_mine": None,
            "UG_TPS_mine": None,
            "UV_TPS_mine": None,
        }
        ps = ps_idx.get(key)
        tps = tps_idx.get(key)

        if mof in FORCED_HYMARC_NA:
            status = "N/A (not in dataset)"
            ug_ps_h = uv_ps_h = ug_tps_h = uv_tps_h = None
        else:
            status = "OK"
            ug_ps_h = parse_float(ps.get("UG at PS")) if ps else None
            uv_ps_h = parse_float(ps.get("UV at PS")) if ps else None
            ug_tps_h = parse_float(tps.get("UG at TPS")) if tps else None
            uv_tps_h = parse_float(tps.get("UV at TPS")) if tps else None

        top3_rows.append(
            {
                "MOF": mof,
                "UG_PS_mine": fmt_na_or_num(mine["UG_PS_mine"]),
                "UV_PS_mine": fmt_na_or_num(mine["UV_PS_mine"]),
                "UG_TPS_mine": fmt_na_or_num(mine["UG_TPS_mine"]),
                "UV_TPS_mine": fmt_na_or_num(mine["UV_TPS_mine"]),
                "UG_PS_hymarc": fmt_na_or_num(ug_ps_h),
                "UV_PS_hymarc": fmt_na_or_num(uv_ps_h),
                "UG_TPS_hymarc": fmt_na_or_num(ug_tps_h),
                "UV_TPS_hymarc": fmt_na_or_num(uv_tps_h),
                "hymarc_status": status,
            }
        )

    benchmark_rows.sort(key=lambda r: r["MOF"])
    write_csv(BENCHMARK_OUT, benchmark_headers, benchmark_rows)
    write_csv(TOP3_OUT, top3_headers, top3_rows)

    presence_lines = []
    for mof in TOP3_MOFS:
        key = normalize_refcode(mof)
        ps_status = presence_status_in_index(ps_idx, key, "UG at PS", "UV at PS")
        tps_status = presence_status_in_index(tps_idx, key, "UG at TPS", "UV at TPS")
        presence_lines.append(f"{mof} in ps.csv: {ps_status}")
        presence_lines.append(f"{mof} in tps.csv: {tps_status}")

    with open(SUMMARY_OUT, "w", encoding="utf-8") as f:
        f.write(f"benchmarkable MOFs: {len(benchmark_rows)}\n")
        f.write(f"excluded due to HyMARC N/A: {excluded_hymarc_na}\n")
        f.write(f"skipped due to missing mine values (non-HyMARC issue): {skipped_missing_mine}\n")
        f.write("\n")
        for metric in ("UG_PS", "UV_PS", "UG_TPS", "UV_TPS"):
            vals = abs_errs[metric]
            f.write(
                f"mean absolute % error ({metric}): "
                f"{(f'{mean(vals):.6f}' if vals else 'N/A')}\n"
            )
        f.write("\n")
        for metric in ("UG_PS", "UV_PS", "UG_TPS", "UV_TPS"):
            vals = abs_errs[metric]
            f.write(
                f"median absolute % error ({metric}): "
                f"{(f'{median(vals):.6f}' if vals else 'N/A')}\n"
            )
        f.write("\n")
        f.write("Explicit dataset search (raw ps.csv/tps.csv presence check):\n")
        for line in presence_lines:
            f.write(f"- {line}\n")
        f.write("\n")
        f.write(
            "Note: XAFFIV and XAFFAN are intentionally forced to HyMARC N/A in the benchmark/top-3 "
            "verification logic per user-specified benchmark policy, even if raw ps.csv/tps.csv contain rows.\n"
        )


if __name__ == "__main__":
    main()
