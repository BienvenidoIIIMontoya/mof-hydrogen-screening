#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(pwd)"
export RASPA_DIR="${HOME}/RASPA/simulations/"
CIF="VAGMAT_clean.cif"
SUMMARY_CSV="VAGMAT_PS_TPS_summary.csv"

if [[ ! -f "${ROOT_DIR}/${CIF}" ]]; then
  echo "ERROR: missing file/path ${ROOT_DIR}/${CIF}" >&2
  exit 1
fi

if [[ ! -x "${RASPA_DIR}/bin/simulate" ]]; then
  echo "ERROR: missing file/path ${RASPA_DIR}/bin/simulate" >&2
  exit 1
fi

# Ensure hydrogen.def exists where MoleculeDefinitions points.
if [[ ! -f "${RASPA_DIR}/share/raspa/molecules/ExampleDefinitions/hydrogen.def" ]]; then
  echo "ERROR: missing file/path ${RASPA_DIR}/share/raspa/molecules/ExampleDefinitions/hydrogen.def" >&2
  exit 1
fi

cases=("PS_high:77.0:10000000" "PS_low:77.0:500000" "TPS_low:160.0:500000")

for item in "${cases[@]}"; do
  IFS=':' read -r case_name t p <<< "${item}"
  case_dir="${ROOT_DIR}/${case_name}"
  mkdir -p "${case_dir}"

  cp -f "${ROOT_DIR}/${CIF}" "${case_dir}/${CIF}"

  cat > "${case_dir}/run.sh" <<RUNEOF
#!/usr/bin/env bash
set -euo pipefail
export RASPA_DIR="${RASPA_DIR}"
"\${RASPA_DIR}/bin/simulate" simulation.input
RUNEOF
  chmod +x "${case_dir}/run.sh"

  cat > "${case_dir}/simulation.input" <<SIMEOF
SimulationType                MonteCarlo
Ensemble                      GCMC
NumberOfCycles                500000
NumberOfInitializationCycles  50000
PrintEvery                    5000
PrintPropertiesEvery          5000

ForceField                    Generic
UseChargesFromCIFFile         no

Framework 0
FrameworkName                 VAGMAT_clean
UnitCells                     1 1 1

ExternalTemperature           ${t}
ExternalPressure              ${p}

MoleculeDefinitions           ExampleDefinitions

Component 0 MoleculeName               hydrogen
            MoleculeDefinition         ExampleDefinitions
            MolFraction                1.0
            TranslationProbability     1.0
            RotationProbability        1.0
            SwapProbability            1.0
SIMEOF

  echo "Running ${case_name} (T=${t} K, P=${p} Pa)..."
  (
    cd "${case_dir}"
    ./run.sh 2>&1 | tee raspa_run_stdout.txt
  )
done

python3 - <<'PY'
import csv
import glob
import os
import re

root = os.getcwd()
cases = [
    ("PS_high", 77.0, 10000000.0),
    ("PS_low", 77.0, 500000.0),
    ("TPS_low", 160.0, 500000.0),
]

results = {}

for case, t, p in cases:
    pattern = os.path.join(root, case, "Output", "System_0", "output_*.data")
    files = glob.glob(pattern)
    if not files:
        raise SystemExit(f"ERROR: missing file/path {pattern}")
    path = files[0]

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    def get_float(pattern, name):
        m = re.search(pattern, text)
        if not m:
            raise SystemExit(f"ERROR: {name} not found in {path}")
        return float(m.group(1))

    mg_g = get_float(r"Average loading absolute \[milligram/gram framework\]\s+([0-9Ee+\-.]+)", "mg/g")
    molkg = get_float(r"Average loading absolute \[mol/kg framework\]\s+([0-9Ee+\-.]+)", "mol/kg")
    density = get_float(r"Framework Density:\s+([0-9Ee+\-.]+)\s+\[kg/m\^3\]", "Framework Density")

    add_sec = re.search(r"Performance of the swap addition move:\n=+\n(.*?)\n\n", text, re.S)
    del_sec = re.search(r"Performance of the swap deletion move:\n=+\n(.*?)\n\n", text, re.S)
    if not add_sec or not del_sec:
        raise SystemExit(f"ERROR: swap performance section not found in {path}")

    add_acc = re.search(r"accepted:\s+([0-9Ee+\-.]+)", add_sec.group(1))
    del_acc = re.search(r"accepted:\s+([0-9Ee+\-.]+)", del_sec.group(1))
    if not add_acc or not del_acc:
        raise SystemExit(f"ERROR: swap accepted count not found in {path}")

    swap_add = float(add_acc.group(1))
    swap_del = float(del_acc.group(1))

    wt = mg_g / 10.0
    gL = molkg * density * 2.01588 / 1000.0

    results[case] = {
        "temperature_K": t,
        "pressure_Pa": p,
        "mg_per_g": mg_g,
        "mol_per_kg": molkg,
        "density_kg_m3": density,
        "swap_add_accepted": swap_add,
        "swap_del_accepted": swap_del,
        "wt_percent": wt,
        "g_H2_per_L": gL,
        "output_file": path,
    }

UG_PS = results["PS_high"]["wt_percent"] - results["PS_low"]["wt_percent"]
UV_PS = results["PS_high"]["g_H2_per_L"] - results["PS_low"]["g_H2_per_L"]
UG_TPS = results["PS_high"]["wt_percent"] - results["TPS_low"]["wt_percent"]
UV_TPS = results["PS_high"]["g_H2_per_L"] - results["TPS_low"]["g_H2_per_L"]

summary_csv = os.path.join(root, "VAGMAT_PS_TPS_summary.csv")
with open(summary_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow([
        "record_type", "case", "temperature_K", "pressure_Pa",
        "avg_loading_mg_per_g", "avg_loading_mol_per_kg", "framework_density_kg_per_m3",
        "swap_add_accepted", "swap_del_accepted", "wt_percent", "g_H2_per_L", "output_file"
    ])
    for case in ["PS_high", "PS_low", "TPS_low"]:
        r = results[case]
        w.writerow([
            "case", case, r["temperature_K"], r["pressure_Pa"],
            r["mg_per_g"], r["mol_per_kg"], r["density_kg_m3"],
            r["swap_add_accepted"], r["swap_del_accepted"], r["wt_percent"], r["g_H2_per_L"], r["output_file"]
        ])
    w.writerow([])
    w.writerow(["record_type", "metric", "value"])
    w.writerow(["deliverable", "UG_PS_wt_percent", UG_PS])
    w.writerow(["deliverable", "UV_PS_g_per_L", UV_PS])
    w.writerow(["deliverable", "UG_TPS_wt_percent", UG_TPS])
    w.writerow(["deliverable", "UV_TPS_g_per_L", UV_TPS])

for case in ["PS_high", "PS_low", "TPS_low"]:
    r = results[case]
    print(f"{case}: wt%={r['wt_percent']:.6f}, g-H2/L={r['g_H2_per_L']:.6f}, "
          f"mg/g={r['mg_per_g']:.6f}, mol/kg={r['mol_per_kg']:.6f}, "
          f"density={r['density_kg_m3']:.6f}, "
          f"swap_add_accepted={int(round(r['swap_add_accepted']))}, "
          f"swap_del_accepted={int(round(r['swap_del_accepted']))}")

print(f"UG_PS (wt%) = {UG_PS:.6f}")
print(f"UV_PS (g/L) = {UV_PS:.6f}")
print(f"UG_TPS (wt%) = {UG_TPS:.6f}")
print(f"UV_TPS (g/L) = {UV_TPS:.6f}")
print(f"Saved: {summary_csv}")
PY
