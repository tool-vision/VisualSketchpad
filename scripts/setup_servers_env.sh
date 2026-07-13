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

# cuda 12.1 nvcc rejects host gcc > 12
conda install -y -c conda-forge "gcc_linux-64=12" "gxx_linux-64=12"
export CC="$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-gcc"
export CXX="$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-g++"

# detectron2's setup.py needs pkg_resources (removed in setuptools>=81)
pip install "setuptools<81"

# Semantic-SAM + detectron2 fork (both need torch at build time -> no build isolation)
pip install --no-build-isolation git+https://github.com/UX-Decoder/Semantic-SAM.git@package
pip install --no-build-isolation 'git+https://github.com/MaureenZOU/detectron2-xyz.git'

# Deformable-DETR CUDA ops
export TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0+PTX"
cd "${REPO_ROOT}/vision_experts/simplified_som/ops"
sh make.sh

# GroundingDINO (setup.py imports torch -> no build isolation)
cd "${REPO_ROOT}/vision_experts/GroundingDINO"
pip install --no-build-isolation -e .

# Depth-Anything
cd "${REPO_ROOT}/vision_experts/Depth-Anything"
pip install -r requirements.txt

# gradio for the servers + misc deps used by server scripts
pip install gradio==5.38.2 gradio_client==1.11.0 supervision opencv-python

# post-install fixes:
# - wandb (pulled in by semantic-sam via old timm) crashes on import with new
#   protobuf; timm guards `import wandb` so removing it is safe
# - gradio upgrades huggingface-hub to >=1.0 which transformers 4.34 rejects
pip uninstall -y wandb
pip install "huggingface-hub==0.36.0"

echo "SERVERS_ENV_READY"
