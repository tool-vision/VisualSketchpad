#!/usr/bin/env bash
# Launch the three Visual Sketchpad vision-expert gradio servers on one GPU.
# Usage: bash scripts/start_vision_servers.sh [GPU_ID]   (default GPU 7)
# Logs: <repo>/outputs_servers/{som,gdino,depth}.log ; stop with scripts/stop_vision_servers.sh
set -eo pipefail

GPU_ID="${1:-7}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${REPO_ROOT}/outputs_servers"
mkdir -p "$LOG_DIR"

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate sketchpad_servers

export CUDA_VISIBLE_DEVICES="$GPU_ID"
export GRADIO_SHARE=0
export GRADIO_HOST=127.0.0.1

cd "${REPO_ROOT}/vision_experts/simplified_som"
GRADIO_PORT=8080 nohup python som_server.py > "$LOG_DIR/som.log" 2>&1 &
echo "SOM (Semantic-SAM) starting on :8080, pid $! (log: $LOG_DIR/som.log)"

cd "${REPO_ROOT}/vision_experts/GroundingDINO"
GRADIO_PORT=8081 nohup python grounding_dino_server.py > "$LOG_DIR/gdino.log" 2>&1 &
echo "GroundingDINO starting on :8081, pid $! (log: $LOG_DIR/gdino.log)"

cd "${REPO_ROOT}/vision_experts/Depth-Anything"
GRADIO_PORT=8082 nohup python depthanything_server.py > "$LOG_DIR/depth.log" 2>&1 &
echo "Depth-Anything starting on :8082, pid $! (log: $LOG_DIR/depth.log)"

echo "Waiting for servers to come up (model loading can take a few minutes)..."
for port in 8080 8081 8082; do
  for i in $(seq 1 120); do
    if curl -s -m 2 "http://127.0.0.1:${port}/" > /dev/null 2>&1; then
      echo "  port ${port}: UP"
      break
    fi
    if [ "$i" -eq 120 ]; then echo "  port ${port}: TIMED OUT (check logs)"; fi
    sleep 5
  done
done
echo "Done. Servers run in background; use scripts/stop_vision_servers.sh to stop."
