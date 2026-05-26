# Handoff Notes

## What Was Packaged

- Six ML notebooks from the local `MACHINE LEARNING` folder.
- The recovered 12,986-row RF ranking CSV from the RASPA `_inputs` folder.
- A descriptor-only 12,986-row CSV derived from that ranking source.
- PS and TPS labeled training tables found in local Downloads.
- Deterministic train/test split indices for all six model notebooks and four prediction tasks.
- Curated RASPA templates, force fields, hydrogen molecule definitions, validation CIFs, run inputs, stdout, raw `.data` outputs, and summary tables.
- Advisor plan PDF copied to `docs/advisor/Bien_plan.pdf`.

## Nontrivial Changes

- Notebook paths were changed from Colab `/content/...` paths to repository-relative paths.
- Notebook stale outputs were cleared to avoid shipping old machine-specific execution state.
- Notebook model outputs now target `models/<algorithm>/`.
- Notebook split outputs now target `splits/<algorithm>/`.
- `data/processed/` was aligned to the notebook Cell A cleaning output so precomputed split indices match notebook execution.
- RASPA `run.sh` files now use `RASPA_DIR` from the environment, with a portable default, instead of hardcoding one recovered WSL location.
- The descriptor-only `data/descriptors/mof_descriptors_12986.csv` was derived from `data/descriptors/final_combined_ranking_rf_12986.csv` by retaining identifiers and descriptor columns.

## Missing Or Blocked Items

- Saved trained `.joblib` model files were not present in the scanned source folders or nearby local Downloads/Documents files. RF, ERT, HGB, LGBM, KNN, and SVR artifacts were rebuilt from recovered notebook best-parameter outputs.
- The exact original file named `tps_usable_hydrogen_storage_capacity_gcmcv2_REAL_cleaned.csv` was not found. The packaged TPS source is `balanced_tps_canonical.csv`, which contains canonical descriptor columns and TPS target columns.
- `shap`, `mapie`, `nbformat`, and `nbclient` were not installed in the active local Python environment during packaging. They are included in `environment.yml`.

## Hardcoded Path Audit

- ML notebooks: converted away from `/content/...`.
- RASPA run scripts: converted to use `RASPA_DIR`.
- Recovery manifests and some recovered output CSVs retain original WSL paths as provenance, not executable configuration.
- Some historical RASPA helper scripts in `raspa/scripts/` still contain original path defaults from the recovered workspace. Treat these as provenance scripts unless they are updated for a new analysis pass.
