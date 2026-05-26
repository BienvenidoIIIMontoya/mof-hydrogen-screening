# RASPA Scripts

The `legacy/` scripts were copied from the recovered RASPA workspace as part of the scientific provenance.

The portable run inputs for publication handoff are in `raspa/runs/`, and the reusable templates are in `raspa/templates/`. Some historical helper scripts in `legacy/` still contain defaults from the original WSL workspace; review and update those defaults before using them for a new analysis pass.

For direct RASPA reruns, prefer:

```bash
cd raspa/runs/<MOF>/<case>
export RASPA_DIR="$HOME/RASPA/simulations"
bash run.sh
```
