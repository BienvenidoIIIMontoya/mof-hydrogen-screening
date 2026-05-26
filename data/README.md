# Data

Important packaged data files:

- `descriptors/mof_descriptors_12986.csv` - descriptor/features table for the 12,986-MOF handoff set.
- `descriptors/final_combined_ranking_rf_12986.csv` - recovered RF ranking source that also contains predictions and ranks.
- `raw/ps_usable_hydrogen_storage_capacity_gcmcv2_real_cleaned.csv` - PS labeled training data.
- `raw/balanced_tps_canonical.csv` - TPS labeled/canonical data found locally.
- `processed/ps_cleaned_canonical.csv` and `processed/tps_cleaned_canonical.csv` - notebook fallback training tables aligned to the Cell A cleaning logic.
- `processed/real_cleaned_canonical_19248_provenance.csv` - earlier recovered 19,248-row REAL canonical table retained for provenance.

See `../manifests/data_manifest.json` for rows, columns, and provenance notes.
