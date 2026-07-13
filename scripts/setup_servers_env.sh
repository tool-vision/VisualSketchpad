#!/usr/bin/env bash
# Build the `sketchpad_servers` conda env hosting the three GPU vision experts
# (Semantic-SAM/SoM, GroundingDINO, Depth-Anything) as gradio servers.
set -eo pipefail

ENV_NAME="${1:-sketchpad_servers}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

source "$(conda info --base)/etc/profile.d/conda.sh"

if ! conda env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
  conda create -y -n "${ENV_NAME}" python=3.10 pip
fi
conda activate "${ENV_NAME}"

pip install --upgrade pip
# torch 2.1.2+cu121: known-good for Semantic-SAM deformable ops, GroundingDINO, Depth-Anything
pip install torch==2.1.2 torchvision==0.16.2 --index-url https://download.pytorch.org/whl/cu121

# nvcc for building deformable-DETR ops (matches torch cu121)
conda install -y -c nvidia/label/cuda-12.1.1 cuda-toolkit
export CUDA_HOME="$CONDA_PREFIX"

# Semantic-SAM + detectron2 fork
pip install git+https://github.com/UX-Decoder/Semantic-SAM.git@package
pip install 'git+https://github.com/MaureenZOU/detectron2-xyz.git'

# Deformable-DETR CUDA ops
export TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0+PTX"
cd "${REPO_ROOT}/vision_experts/simplified_som/ops"
sh make.sh

# GroundingDINO
cd "${REPO_ROOT}/vision_experts/GroundingDINO"
pip install -e .

# Depth-Anything
cd "${REPO_ROOT}/vision_experts/Depth-Anything"
pip install -r requirements.txt

# gradio for the servers + misc deps used by server scripts
pip install gradio==5.38.2 gradio_client==1.11.0 supervision opencv-python

echo "SERVERS_ENV_READY"
