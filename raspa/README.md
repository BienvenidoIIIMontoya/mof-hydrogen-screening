# RASPA/GCMC Materials

This folder contains the curated RASPA materials for the journal handoff.

- `templates/` - reusable `simulation.input` and `run.sh`.
- `forcefields/` - recovered `Generic` and `Generic_H2fix` force-field parameter directories.
- `molecules/` - hydrogen molecule definition files.
- `validation_cifs/` - six cleaned validation CIFs.
- `runs/` - curated run folders with `simulation.input`, `run.sh`, stdout, and raw RASPA `.data` output files.
- `outputs/summary_tables/` - recovered GCMC summary tables and manuscript patch notes.
- `manifests/raspa_file_manifest.csv` - file-level RASPA manifest with hashes.

The historical recovery manifests in `docs/recovery/` retain original WSL paths for provenance. Portable run scripts in `runs/` should use `RASPA_DIR` from the current environment.
