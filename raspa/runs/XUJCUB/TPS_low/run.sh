#!/usr/bin/env bash
set -euo pipefail
: "${RASPA_DIR:=${HOME}/RASPA/simulations}"
export RASPA_DIR
"${RASPA_DIR}/bin/simulate" simulation.input
