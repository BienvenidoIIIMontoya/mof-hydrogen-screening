#!/usr/bin/env python3
import csv
import math
from pathlib import Path
from statistics import median

ROOT = Path.home() / 'raspa_runs' / 'H2_in_MOF'
DATA = Path.home() / 'datasets'

SUMMARY = ROOT / 'ALL_corrected_summary_with_sanity.csv'
PS = DATA / 'ps.csv'
TPS = DATA / 'tps.csv'

OUT_PS_JOIN = ROOT / 'MINE_vs_DATASETS_PS.csv'
OUT_TPS_JOIN = ROOT / 'MINE_vs_DATASETS_TPS.csv'
OUT_BENCH = ROOT / 'HY_MOF_BENCHMARK.csv'
OUT_TOP3 = ROOT / 'TOP3_ML_VERIFICATION_TABLE.csv'
OUT_STATS = ROOT / 'SUMMARY_STATS.txt'

MISSING_TOKENS = {'', 'na', 'n/a', 'nan', 'none'}
# User-provided truth: not present in HyMARC for comparison stats.
FORCED_NO_HYMARC = {'XAFFIV', 'XAFFAN'}


def clean(s):
    if s is None:
        return ''
    return str(s).replace('\xa0', ' ').strip()


def is_missing(s):
    return clean(s).lower() in MISSING_TOKENS


def to_float(s):
    t = clean(s)
    if t.lower() in MISSING_TOKENS:
        return None
    try:
        return float(t)
    except Exception:
        return None


def norm_mof(s):
    t = clean(s).upper()
    t = t.replace('-', '_').replace(' ', '_')
    for suf in ['_CLEAN', '_H2']:
        if t.endswith(suf):
            t = t[: -len(suf)]
    return t


def read_csv(path):
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append({clean(k): clean(v) for k, v in row.items() if k is not None})
    return rows


def find_col(cols, wants):
    # wants: list of required lowercase substrings
    for c in cols:
        lc = c.lower()
        if all(w in lc for w in wants):
            return c
    return ''


def pct_err(mine, ref):
    if mine is None or ref is None or ref == 0:
        return None
    return 100.0 * (mine - ref) / ref


def fmt(x, nd=6):
    if x is None:
        return ''
    return f'{x:.{nd}f}'


def build_dataset_map(rows, phase):
    cols = list(rows[0].keys()) if rows else []
    ref_col = find_col(cols, ['csd', 'ref']) or find_col(cols, ['ref']) or cols[0]
    ug_col = find_col(cols, ['ug', phase.lower()])
    uv_col = find_col(cols, ['uv', phase.lower()])

    m = {}
    for r in rows:
        ref = norm_mof(r.get(ref_col, ''))
        if not ref:
            continue
        m[ref] = {
            'ref_raw': r.get(ref_col, ''),
            'name': r.get('Name', '') or r.get('Name ', ''),
            'UG': to_float(r.get(ug_col, '')) if ug_col else None,
            'UV': to_float(r.get(uv_col, '')) if uv_col else None,
            'UG_raw': r.get(ug_col, '') if ug_col else '',
            'UV_raw': r.get(uv_col, '') if uv_col else '',
            'ug_col': ug_col,
            'uv_col': uv_col,
            'ref_col': ref_col,
        }
    return m, ref_col, ug_col, uv_col


def main():
    mine_rows = read_csv(SUMMARY)
    ps_rows = read_csv(PS)
    tps_rows = read_csv(TPS)

    ps_map, ps_ref_col, ps_ug_col, ps_uv_col = build_dataset_map(ps_rows, 'PS')
    tps_map, tps_ref_col, tps_ug_col, tps_uv_col = build_dataset_map(tps_rows, 'TPS')

    ps_join = []
    tps_join = []
    bench = []

    excluded_no_hymarc = 0

    for r in mine_rows:
        mof = clean(r.get('MOF', ''))
        mof_norm = norm_mof(mof)

        mine_ug_ps = to_float(r.get('UG_PS', ''))
        mine_uv_ps = to_float(r.get('UV_PS', ''))
        mine_ug_tps = to_float(r.get('UG_TPS', ''))
        mine_uv_tps = to_float(r.get('UV_TPS', ''))

        ps_d = ps_map.get(mof_norm)
        tps_d = tps_map.get(mof_norm)

        # Forced N/A policy for XAFFIV/XAFFAN per user truth.
        forced_na = mof_norm in FORCED_NO_HYMARC

        hymarc_ug_ps = None if forced_na else (ps_d.get('UG') if ps_d else None)
        hymarc_uv_ps = None if forced_na else (ps_d.get('UV') if ps_d else None)
        hymarc_ug_tps = None if forced_na else (tps_d.get('UG') if tps_d else None)
        hymarc_uv_tps = None if forced_na else (tps_d.get('UV') if tps_d else None)

        ps_status = 'OK' if (hymarc_ug_ps is not None and hymarc_uv_ps is not None) else 'NO_HYMARC_VALUE'
        tps_status = 'OK' if (hymarc_ug_tps is not None and hymarc_uv_tps is not None) else 'NO_HYMARC_VALUE'

        if ps_status != 'OK' or tps_status != 'OK':
            excluded_no_hymarc += 1

        ps_join.append({
            'MOF': mof,
            'MOF_norm': mof_norm,
            'dataset_refcode': '' if forced_na else clean(ps_d.get('ref_raw', '') if ps_d else ''),
            'dataset_name': '' if forced_na else clean(ps_d.get('name', '') if ps_d else ''),
            'UG_PS_mine': fmt(mine_ug_ps, 6),
            'UV_PS_mine': fmt(mine_uv_ps, 6),
            'UG_PS_hymarc': fmt(hymarc_ug_ps, 6),
            'UV_PS_hymarc': fmt(hymarc_uv_ps, 6),
            'UG_PS_delta': fmt(None if (mine_ug_ps is None or hymarc_ug_ps is None) else (mine_ug_ps - hymarc_ug_ps), 6),
            'UV_PS_delta': fmt(None if (mine_uv_ps is None or hymarc_uv_ps is None) else (mine_uv_ps - hymarc_uv_ps), 6),
            'UG_PS_pct_err': fmt(pct_err(mine_ug_ps, hymarc_ug_ps), 3),
            'UV_PS_pct_err': fmt(pct_err(mine_uv_ps, hymarc_uv_ps), 3),
            'status': ps_status,
        })

        tps_join.append({
            'MOF': mof,
            'MOF_norm': mof_norm,
            'dataset_refcode': '' if forced_na else clean(tps_d.get('ref_raw', '') if tps_d else ''),
            'dataset_name': '' if forced_na else clean(tps_d.get('name', '') if tps_d else ''),
            'UG_TPS_mine': fmt(mine_ug_tps, 6),
            'UV_TPS_mine': fmt(mine_uv_tps, 6),
            'UG_TPS_hymarc': fmt(hymarc_ug_tps, 6),
            'UV_TPS_hymarc': fmt(hymarc_uv_tps, 6),
            'UG_TPS_delta': fmt(None if (mine_ug_tps is None or hymarc_ug_tps is None) else (mine_ug_tps - hymarc_ug_tps), 6),
            'UV_TPS_delta': fmt(None if (mine_uv_tps is None or hymarc_uv_tps is None) else (mine_uv_tps - hymarc_uv_tps), 6),
            'UG_TPS_pct_err': fmt(pct_err(mine_ug_tps, hymarc_ug_tps), 3),
            'UV_TPS_pct_err': fmt(pct_err(mine_uv_tps, hymarc_uv_tps), 3),
            'status': tps_status,
        })

        # Benchmark row only when HyMARC provides all UG/UV values (PS+TPS) and not forced N/A
        hymarc_present_all = (
            hymarc_ug_ps is not None and hymarc_uv_ps is not None and
            hymarc_ug_tps is not None and hymarc_uv_tps is not None
        )
        if hymarc_present_all:
            bench.append({
                'MOF': mof,
                'UG_PS_mine': fmt(mine_ug_ps, 6),
                'UV_PS_mine': fmt(mine_uv_ps, 6),
                'UG_PS_hymarc': fmt(hymarc_ug_ps, 6),
                'UV_PS_hymarc': fmt(hymarc_uv_ps, 6),
                'UG_PS_%err': fmt(pct_err(mine_ug_ps, hymarc_ug_ps), 3),
                'UV_PS_%err': fmt(pct_err(mine_uv_ps, hymarc_uv_ps), 3),
                'UG_TPS_mine': fmt(mine_ug_tps, 6),
                'UV_TPS_mine': fmt(mine_uv_tps, 6),
                'UG_TPS_hymarc': fmt(hymarc_ug_tps, 6),
                'UV_TPS_hymarc': fmt(hymarc_uv_tps, 6),
                'UG_TPS_%err': fmt(pct_err(mine_ug_tps, hymarc_ug_tps), 3),
                'UV_TPS_%err': fmt(pct_err(mine_uv_tps, hymarc_uv_tps), 3),
            })

    # Write corrected joins
    with open(OUT_PS_JOIN, 'w', newline='', encoding='utf-8') as f:
        cols = ['MOF','MOF_norm','dataset_refcode','dataset_name','UG_PS_mine','UV_PS_mine','UG_PS_hymarc','UV_PS_hymarc','UG_PS_delta','UV_PS_delta','UG_PS_pct_err','UV_PS_pct_err','status']
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader(); w.writerows(ps_join)

    with open(OUT_TPS_JOIN, 'w', newline='', encoding='utf-8') as f:
        cols = ['MOF','MOF_norm','dataset_refcode','dataset_name','UG_TPS_mine','UV_TPS_mine','UG_TPS_hymarc','UV_TPS_hymarc','UG_TPS_delta','UV_TPS_delta','UG_TPS_pct_err','UV_TPS_pct_err','status']
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader(); w.writerows(tps_join)

    # HY_MOF_BENCHMARK.csv
    with open(OUT_BENCH, 'w', newline='', encoding='utf-8') as f:
        cols = ['MOF','UG_PS_mine','UV_PS_mine','UG_PS_hymarc','UV_PS_hymarc','UG_PS_%err','UV_PS_%err','UG_TPS_mine','UV_TPS_mine','UG_TPS_hymarc','UV_TPS_hymarc','UG_TPS_%err','UV_TPS_%err']
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader(); w.writerows(bench)

    # TOP3_ML_VERIFICATION_TABLE.csv
    forced_top = ['VAGMAT', 'XAFFIV', 'XAFFAN']
    # make lookup from bench and join rows
    mine_map = {norm_mof(r.get('MOF','')): r for r in mine_rows}
    ps_join_map = {norm_mof(r['MOF']): r for r in ps_join}
    tps_join_map = {norm_mof(r['MOF']): r for r in tps_join}

    top_rows = []
    for m in forced_top:
        mr = mine_map.get(m, {})
        pjr = ps_join_map.get(m, {})
        tjr = tps_join_map.get(m, {})

        hymarc_ok = (pjr.get('status') == 'OK' and tjr.get('status') == 'OK')
        top_rows.append({
            'MOF': m,
            'UG_PS_mine': fmt(to_float(mr.get('UG_PS', '')), 6),
            'UV_PS_mine': fmt(to_float(mr.get('UV_PS', '')), 6),
            'UG_TPS_mine': fmt(to_float(mr.get('UG_TPS', '')), 6),
            'UV_TPS_mine': fmt(to_float(mr.get('UV_TPS', '')), 6),
            'UG_PS_hymarc': pjr.get('UG_PS_hymarc', ''),
            'UV_PS_hymarc': pjr.get('UV_PS_hymarc', ''),
            'UG_TPS_hymarc': tjr.get('UG_TPS_hymarc', ''),
            'UV_TPS_hymarc': tjr.get('UV_TPS_hymarc', ''),
            'hymarc_status': 'OK' if hymarc_ok else 'N/A',
        })

    with open(OUT_TOP3, 'w', newline='', encoding='utf-8') as f:
        cols = ['MOF','UG_PS_mine','UV_PS_mine','UG_TPS_mine','UV_TPS_mine','UG_PS_hymarc','UV_PS_hymarc','UG_TPS_hymarc','UV_TPS_hymarc','hymarc_status']
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader(); w.writerows(top_rows)

    # Optional sanity check for forced N/A refcodes in source files
    def exists_in(rows, ref_col, target):
        t = target.upper()
        for rr in rows:
            if norm_mof(rr.get(ref_col, '')) == t:
                return True
        return False

    ps_exists_xaffiv = exists_in(ps_rows, ps_ref_col, 'XAFFIV')
    ps_exists_xaffan = exists_in(ps_rows, ps_ref_col, 'XAFFAN')
    tps_exists_xaffiv = exists_in(tps_rows, tps_ref_col, 'XAFFIV')
    tps_exists_xaffan = exists_in(tps_rows, tps_ref_col, 'XAFFAN')

    # Summary stats over benchmark rows only (numeric abs % only)
    metrics = {
        'UG_PS_%err': [],
        'UV_PS_%err': [],
        'UG_TPS_%err': [],
        'UV_TPS_%err': [],
    }
    for b in bench:
        for k in metrics:
            v = to_float(b.get(k, ''))
            if v is not None:
                metrics[k].append(abs(v))

    all_vals = []
    for vals in metrics.values():
        all_vals.extend(vals)

    lines = []
    lines.append('SUMMARY STATS (HY_MOF_BENCHMARK only)')
    lines.append(f'benchmark_row_count={len(bench)}')
    lines.append(f'excluded_rows_due_to_NA_or_forced_NA={excluded_no_hymarc}')
    lines.append('')
    for k, vals in metrics.items():
        if vals:
            lines.append(f'{k}: count={len(vals)} mean_abs_pct_err={sum(vals)/len(vals):.3f} median_abs_pct_err={median(vals):.3f}')
        else:
            lines.append(f'{k}: count=0 mean_abs_pct_err=NA median_abs_pct_err=NA')
    lines.append('')
    if all_vals:
        lines.append(f'overall_abs_pct_err: count={len(all_vals)} mean={sum(all_vals)/len(all_vals):.3f} median={median(all_vals):.3f}')
    else:
        lines.append('overall_abs_pct_err: count=0 mean=NA median=NA')
    lines.append('')
    lines.append('Sanity check (forced N/A refcodes in source files):')
    lines.append(f'ps.csv contains XAFFIV={ps_exists_xaffiv} XAFFAN={ps_exists_xaffan}')
    lines.append(f'tps.csv contains XAFFIV={tps_exists_xaffiv} XAFFAN={tps_exists_xaffan}')
    if (not ps_exists_xaffiv and not ps_exists_xaffan and not tps_exists_xaffiv and not tps_exists_xaffan):
        lines.append('Interpretation: XAFFIV/XAFFAN not in dataset (not a join bug).')
    else:
        lines.append('Interpretation: XAFFIV/XAFFAN rows exist in files, but treated as HyMARC N/A by user-provided ground truth.')

    with open(OUT_STATS, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    print('WROTE:', OUT_PS_JOIN)
    print('WROTE:', OUT_TPS_JOIN)
    print('WROTE:', OUT_BENCH)
    print('WROTE:', OUT_TOP3)
    print('WROTE:', OUT_STATS)


if __name__ == '__main__':
    main()
