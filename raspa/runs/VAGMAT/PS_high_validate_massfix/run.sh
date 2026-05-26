#!/usr/bin/env bash
set -euo pipefail
: "${RASPA_DIR:=${HOME}/RASPA_H2FIX}"
export RASPA_DIR
"${RASPA_DIR}/bin/simulate" simulation.input
