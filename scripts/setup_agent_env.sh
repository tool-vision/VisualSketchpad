#!/usr/bin/env bash
# Build the `sketchpad` conda env for the agent side (py3.10 to match the
# upstream env.txt: gradio_client 1.11.0 requires >=3.10; the RA's py3.9
# pins cannot import agent/tools.py).
set -eo pipefail
ENV_NAME="${1:-sketchpad}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$(conda info --base)/etc/profile.d/conda.sh"
if ! conda env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
  conda create -y -n "${ENV_NAME}" python=3.10 pip
fi
conda activate "${ENV_NAME}"
if [[ "$CONDA_PREFIX" != *"/envs/${ENV_NAME}" ]]; then
  echo "ERROR: expected env ${ENV_NAME}, got CONDA_PREFIX=$CONDA_PREFIX" >&2
  exit 1
fi
conda install -y -c conda-forge cairo
grep -vE '^(gradio|gradio-client)==' "${REPO_ROOT}/requirements-repro.txt" > /tmp/sketchpad-reqs.txt
pip install -r /tmp/sketchpad-reqs.txt 'pyautogen[jupyter-executor]==0.2.26'
pip install gradio_client==1.11.0
echo "SKETCHPAD_ENV_READY"
