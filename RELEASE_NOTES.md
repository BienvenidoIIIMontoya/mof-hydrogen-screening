# Release Notes

## v0.1.0-handoff draft

- Packaged six ML notebooks with repository-relative paths.
- Added 12,986-MOF descriptor CSV and recovered RF ranking source.
- Added deterministic train/test split index CSV/JSON files for all six model notebooks and four target tasks.
- Curated RASPA/GCMC templates, force fields, hydrogen definitions, validation CIFs, run inputs, stdout, raw `.data` outputs, and summary tables.
- Added data, RASPA, source, model, and handoff manifests.
- Rebuilt saved `.joblib` artifacts for RF, ERT, HGB, LGBM, KNN, and SVR from recovered best hyperparameters.

Remaining before final tag:

- Confirm the final environment resolves `shap` and `mapie` for the next interpretability/uncertainty notebooks.
