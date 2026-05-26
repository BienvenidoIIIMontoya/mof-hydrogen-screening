#!/usr/bin/env python3
import csv
import math
import os

INP = os.path.expanduser('~/raspa_runs/H2_in_MOF/ALL_corrected_summary_with_sanity.csv')
OUT = os.path.expanduser('~/raspa_runs/H2_in_MOF/MINE_UV_REBASED_BULK_DENSITY.csv')

BULK_GCM3 = [0.3, 0.5, 0.7]


def ffloat(x):
    try:
        s = str(x).strip()
        if s == '':
            return float('nan')
        return float(s)
    except Exception:
        return float('nan')


rows_out = []
with open(INP, newline='', encoding='utf-8') as f:
    r = csv.DictReader(f)
    for row in r:
        mof = row.get('MOF', '').strip()
        rho = ffloat(row.get('PS_high_framework_density_kg_m3', ''))
        uv_ps = ffloat(row.get('UV_PS', ''))
        uv_tps = ffloat(row.get('UV_TPS', ''))

        out = {
            'MOF': mof,
            'rho_crystal_kgm3': '' if math.isnan(rho) else f'{rho:.6f}',
            'rho_crystal_gcm3': '' if math.isnan(rho) else f'{rho/1000.0:.6f}',
            'UV_PS_crystal_gL': '' if math.isnan(uv_ps) else f'{uv_ps:.6f}',
            'UV_TPS_crystal_gL': '' if math.isnan(uv_tps) else f'{uv_tps:.6f}',
        }

        if (not math.isnan(rho)) and rho > 0:
            rho_gcm3 = rho / 1000.0
            for bd in BULK_GCM3:
                kps = f'UV_PS_bulk_{bd}gcm3_gL'
                ktps = f'UV_TPS_bulk_{bd}gcm3_gL'
                if not math.isnan(uv_ps):
                    out[kps] = f'{uv_ps * (bd / rho_gcm3):.6f}'
                else:
                    out[kps] = ''
                if not math.isnan(uv_tps):
                    out[ktps] = f'{uv_tps * (bd / rho_gcm3):.6f}'
                else:
                    out[ktps] = ''
        else:
            for bd in BULK_GCM3:
                out[f'UV_PS_bulk_{bd}gcm3_gL'] = ''
                out[f'UV_TPS_bulk_{bd}gcm3_gL'] = ''

        rows_out.append(out)

cols = [
    'MOF', 'rho_crystal_kgm3', 'rho_crystal_gcm3',
    'UV_PS_crystal_gL', 'UV_TPS_crystal_gL',
    'UV_PS_bulk_0.3gcm3_gL', 'UV_TPS_bulk_0.3gcm3_gL',
    'UV_PS_bulk_0.5gcm3_gL', 'UV_TPS_bulk_0.5gcm3_gL',
    'UV_PS_bulk_0.7gcm3_gL', 'UV_TPS_bulk_0.7gcm3_gL',
]

with open(OUT, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(rows_out)

print('WROTE:', OUT)
