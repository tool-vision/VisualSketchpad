#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="${1:-sketchpad}"

if ! command -v conda >/dev/null 2>&1; then
  echo "conda is required. Install Miniconda or Mambaforge first." >&2
  exit 1
fi

if conda env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
  echo "Environment '${ENV_NAME}' already exists; reusing it."
else
  conda create -y -n "${ENV_NAME}" python=3.9 pip
fi
conda install -y -n "${ENV_NAME}" pip
conda install -y -n "${ENV_NAME}" -c conda-forge cairo
conda run -n "${ENV_NAME}" python -m pip install --upgrade pip
conda run -n "${ENV_NAME}" python -m pip install -r requirements-repro.txt 'pyautogen[jupyter-executor]'

echo "Environment '${ENV_NAME}' is ready."
echo "Activate it with: conda activate ${ENV_NAME}"
