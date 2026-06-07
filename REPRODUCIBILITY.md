# Reproducibility Pipeline

This repository reproduces Visual Sketchpad by running task fixtures through the agent in `agent/main.py` and saving trajectories under an output directory. The pipeline below separates offline checks, CPU/API agent runs, and optional GPU vision expert servers.

## 1. Create the Environment

```bash
bash scripts/setup_env.sh sketchpad
conda activate sketchpad
```

If dependency resolution fails on another machine, use `env.txt` as the full reference environment. Vision tasks require the additional setup in [VISION_SERVERS.md](VISION_SERVERS.md) and `vision_experts/installation.md`.

## 2. Configure Runtime Inputs

Set credentials and optional endpoints through environment variables or a local `.env` file instead of editing source files:

```bash
export OPENAI_API_KEY="..."
export OPENAI_API_KEY_BACKUP="..."
export OPENAI_MODEL="gpt-4o"
export SOM_ADDRESS="http://localhost:8080/"
export GROUNDING_DINO_ADDRESS="http://localhost:8081/"
export DEPTH_ANYTHING_ADDRESS="http://localhost:8082/"
```

When both OpenAI keys are present, the primary key is placed first in the AutoGen `config_list` and the backup key is placed second.

Math and geometry tasks only need the agent environment and an OpenAI-compatible API key. Vision tasks also need the Gradio expert servers running locally or on reachable GPU hosts.

## 3. Run the Offline Smoke Test

```bash
python scripts/smoke_test.py
```

This is the machine-feasible smoke check. It validates required fixtures, reference outputs, parser behavior, and environment-driven config without making API calls or starting GPU models.

## 4. Run a Bounded Agent Experiment

```bash
python scripts/run_experiment.py --task graph_maxflow --max-instances 1 --require-api-key
python scripts/run_experiment.py --task geometry --max-instances 1 --require-api-key
```

Outputs are written to `outputs_repro/<task>/`. Each run also writes `run_manifest.json` with task, model, selected instances, and timestamp. Increase `--max-instances` to reproduce larger subsets once the smoke and one-instance runs pass.

If the runner reports that `autogen` is missing, activate the `sketchpad` conda environment or rerun `bash scripts/setup_env.sh sketchpad`.

## 5. Run a Configured Pipeline

Use JSON configs in `configs/` to make experiments portable across compatible machines:

```bash
python scripts/run_pipeline.py --config configs/smoke.json --dry-run
python scripts/run_pipeline.py --config configs/smoke.json
python scripts/run_pipeline.py --config configs/all_nonvision_smoke.json
python scripts/run_pipeline.py --config configs/math_geometry_subset.json
```

Each config declares the model, output directory, per-task instance counts, and device requirements. Edit `max_instances` upward to reproduce larger subsets or full local data once the configured smoke passes. `scripts/run_pipeline.py` writes `pipeline_manifest.json` at the configured output root and each task still writes its own `run_manifest.json`.

Completed pipeline runs score automatically. To rescore any output root, run:

```bash
python scripts/score_outputs.py --output-root outputs_repro --write
```

By default, environment values from `.env` take precedence over config defaults. Use `--override-env` only when a config should replace existing values. Use `--continue-on-error` for larger runs so completed task outputs are scored even if a later task fails.

## 6. Run Vision Tasks

After launching the vision expert servers with [VISION_SERVERS.md](VISION_SERVERS.md):

```bash
python scripts/run_experiment.py --task blink_spatial --max-instances 1 --require-api-key
python scripts/run_pipeline.py --config configs/vision_subset_template.json
python scripts/run_pipeline.py --config configs/all_available_task_smoke.json
```

Use remote server URLs for machines without a GPU. Keep generated trajectories separate from committed references unless intentionally updating benchmark artifacts.

## Expected Artifacts

Each completed instance should contain the copied input files plus `output.json` and `usage_summary.json`. Use `record_viewer.ipynb` to inspect trajectories and compare them against reference files in `outputs/`.
Scored output roots additionally contain `scores.json` and `scores.csv`.
