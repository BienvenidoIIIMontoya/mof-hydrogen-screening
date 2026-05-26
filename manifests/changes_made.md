# Changes Made During Packaging

- Created the clean repository structure under `mof-h2-screening/`.
- Renamed the six ML notebooks for readability while preserving their algorithm identity.
- Patched notebook data/model/output/split paths to be repository-relative.
- Cleared stale notebook outputs.
- Copied and organized data, RASPA inputs, force fields, validation CIFs, run outputs, and advisor plan materials.
- Created `data/descriptors/mof_descriptors_12986.csv` from the recovered 12,986-row RF ranking source.
- Generated train/test split CSV and JSON files under `splits/`.
- Rebuilt RF, ERT, HGB, LGBM, KNN, and SVR `.joblib` model artifacts from recovered best hyperparameters and saved split indices.
- Added manifests for data, source inventory, RASPA files, models, and the handoff checklist.
- Added standard repo files: `README.md`, `environment.yml`, `requirements.txt`, `LICENSE`, `.gitignore`, and `RELEASE_NOTES.md`.
