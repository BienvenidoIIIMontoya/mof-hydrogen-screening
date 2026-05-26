# Train/Test Splits

This directory contains deterministic train/test split indices generated from the packaged canonical PS and TPS training CSVs.

All model notebooks use:

- `random_state = 42`
- `test_size = 0.25`
- `shuffle = True`
- features `Density`, `PV`, `GSA`, `VSA`, `VF`, `PLD`, `LCD`

Each model folder contains CSV indices plus a JSON manifest for `PS_UG`, `PS_UV`, `TPS_UG`, and `TPS_UV`.
