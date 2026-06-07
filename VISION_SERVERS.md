# Vision Expert Server Guide

This guide explains how to start the Visual Sketchpad vision expert Gradio servers on a compatible machine and connect them to the reproducibility pipeline.

## 1. Compatible Machine

Use a Linux CUDA GPU machine for the full vision stack. SOM/Semantic-SAM uses CUDA-only code paths in this repository, including `.cuda()` and `torch.autocast(device_type="cuda")`. A CPU-only or Apple Silicon machine can run the agent pipeline, but should call vision servers hosted elsewhere.

Expected prerequisites:

- NVIDIA GPU with working `nvidia-smi`
- CUDA-compatible PyTorch
- `conda`, `pip`, `git`, and `wget`
- enough disk space for model checkpoints and build artifacts
- inbound access to ports `8080`, `8081`, and `8082` from the agent machine, or Gradio share links

## 2. Install Vision Experts

On the GPU host:

```bash
git clone <repo-url> VisualSketchpad
cd VisualSketchpad/vision_experts
```

Follow the detailed dependency steps in `vision_experts/installation.md`. In short, install:

- Semantic-SAM and Detectron2-compatible dependencies for SOM
- GroundingDINO plus `weights/groundingdino_swint_ogc.pth`
- Depth-Anything requirements
- Gradio server/client versions

For SOM, build the Deformable-DETR ops after setting the CUDA architecture list:

```bash
cd simplified_som
export TORCH_CUDA_ARCH_LIST="5.0;5.2;5.3;6.0;6.1;6.2;7.0;7.2;7.5;8.0;8.6;8.7;8.9;9.0+PTX"
cd ops && sh make.sh && cd ..
wget https://github.com/UX-Decoder/Semantic-SAM/releases/download/checkpoint/swinl_only_sam_many2many.pth
cd ..
```

For GroundingDINO:

```bash
cd GroundingDINO
pip install -e .
mkdir -p weights
wget -O weights/groundingdino_swint_ogc.pth \
  https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha/groundingdino_swint_ogc.pth
cd ..
```

For Depth-Anything:

```bash
cd Depth-Anything
pip install -r requirements.txt
cd ..
```

## 3. Start Servers

Open three terminal sessions on the GPU host.

SOM, port `8080`:

```bash
cd VisualSketchpad/vision_experts/simplified_som
python som_server.py
```

GroundingDINO, port `8081`:

```bash
cd VisualSketchpad/vision_experts/GroundingDINO
python grounding_dino_server.py
```

Depth-Anything, port `8082`:

```bash
cd VisualSketchpad/vision_experts/Depth-Anything
python depthanything_server.py
```

Each script launches a Gradio app with `server_name="localhost"` and `share=True`. If the agent runs on the same host, use local URLs. If the agent runs on another machine, either use the printed Gradio share URLs or edit the server scripts to bind to `0.0.0.0` behind your firewall.

## 4. Configure the Agent Machine

On the machine running `scripts/run_pipeline.py`, set `.env` values to the reachable URLs:

```bash
OPENAI_API_KEY=...
OPENAI_API_KEY_BACKUP=...
OPENAI_MODEL=gpt-4o
SOM_ADDRESS=http://gpu-host:8080/
GROUNDING_DINO_ADDRESS=http://gpu-host:8081/
DEPTH_ANYTHING_ADDRESS=http://gpu-host:8082/
```

If you use Gradio share links, use the full HTTPS URL printed by each server.

Pipeline config environment values are defaults only; `.env` takes precedence unless `--override-env` is passed.

## 5. Check Readiness

From the agent machine:

```bash
conda activate sketchpad
python scripts/check_readiness.py --check-servers
```

Expected result: all three server URLs report reachable. If a server is not reachable, check firewall rules, whether the process is still running, and whether the URL in `.env` matches the server log.

## 6. Run Vision Pipeline

Start with a dry run:

```bash
python scripts/run_pipeline.py --config configs/vision_subset_template.json --dry-run
```

Then run a bounded subset:

```bash
python scripts/run_pipeline.py --config configs/vision_subset_template.json --continue-on-error
```

For one instance from every locally available task family, including vision:

```bash
python scripts/run_pipeline.py --config configs/all_available_task_smoke.json --continue-on-error
```

Outputs and scores are written under the configured `outputs_repro/...` directory.

## 7. Operational Notes

- Keep the three server terminals open during agent runs.
- One set of servers can handle multiple agent runs, but large models may bottleneck on GPU memory.
- Use `--continue-on-error` for long runs so completed outputs are still scored if one task fails.
- Do not commit server URLs, private share links, API keys, checkpoints, or generated outputs.
