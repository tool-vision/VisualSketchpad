# Visual Sketchpad User Guide

This guide explains how to run the reproducibility pipeline added for Visual Sketchpad. Use it when you want a quick local check, a bounded CPU/API experiment, or a vision-task run on a compatible device.

## 1. What You Can Run

- **Offline smoke**: validates files, parser behavior, and config loading. No API key or GPU needed.
- **API smoke**: runs one small `graph_maxflow` task end to end with AutoGen, Jupyter, and OpenAI.
- **Math/geometry subset**: runs bounded samples from non-vision paper task families.
- **Vision subset**: runs bounded vision samples when SOM, GroundingDINO, and Depth-Anything servers are reachable.

Generated outputs go to `outputs_repro/` by default and are ignored by git.

## 2. Set Up the Environment

Create the conda environment:

```bash
bash scripts/setup_env.sh sketchpad
conda activate sketchpad
```

The setup script installs Python 3.9, PyAutoGen, Jupyter execution support, plotting/data libraries, and compatibility pins needed by this codebase.

## 3. Configure Credentials

Create a local `.env` file or export variables in your shell:

```bash
OPENAI_API_KEY=your-primary-key
OPENAI_API_KEY_BACKUP=your-backup-key
OPENAI_MODEL=gpt-4o
```

If both keys are present, the primary key is used first and the backup is registered second in AutoGen’s `config_list`.

For vision tasks, also configure:

```bash
SOM_ADDRESS=http://localhost:8080/
GROUNDING_DINO_ADDRESS=http://localhost:8081/
DEPTH_ANYTHING_ADDRESS=http://localhost:8082/
```

## 4. Run Checks

Start with the offline smoke:

```bash
python scripts/smoke_test.py
```

Preview a configured API run without spending API calls:

```bash
python scripts/run_pipeline.py --config configs/smoke.json --dry-run
```

Check local readiness:

```bash
python scripts/check_readiness.py
python scripts/check_readiness.py --check-servers
```

Run the one-task API smoke:

```bash
python scripts/run_pipeline.py --config configs/smoke.json
```

## 5. Run Experiment Subsets

Run bounded non-vision tasks:

```bash
python scripts/run_pipeline.py --config configs/all_nonvision_smoke.json
python scripts/run_pipeline.py --config configs/math_geometry_subset.json
```

Run a single task directly:

```bash
python scripts/run_experiment.py --task geometry --max-instances 1 --require-api-key
python scripts/run_experiment.py --task graph_maxflow --max-instances 5 --start-index 10 --require-api-key
```

To scale a config, edit `max_instances` in `configs/*.json`. Keep small values until the smoke run works reliably on the target machine.

## 6. Run Vision Tasks

First install and start the vision experts using [VISION_SERVERS.md](VISION_SERVERS.md) and `vision_experts/installation.md`. Confirm the server URLs are in `.env`, then run:

```bash
python scripts/run_pipeline.py --config configs/vision_subset_template.json --dry-run
python scripts/run_pipeline.py --config configs/vision_subset_template.json
python scripts/run_pipeline.py --config configs/all_available_task_smoke.json
```

Use remote URLs if the agent machine has no GPU but can reach GPU-hosted Gradio servers.

## 7. Inspect Outputs

Each completed task instance contains:

- `output.json`: full agent dialogue and observations.
- `usage_summary.json`: model usage reported by AutoGen.
- copied input files such as `example.json`, `ex.json`, or `request.json`.
- generated PNGs when the agent visualizes a graph, plot, or image.

Each task output directory also has `run_manifest.json`. Configured pipelines write `pipeline_manifest.json` at the output root. Use `record_viewer.ipynb` to inspect trajectories visually.

## 8. Score Outputs

Configured pipeline runs score automatically unless `--no-score` is passed. To score an existing output directory:

```bash
python scripts/score_outputs.py --output-root outputs_repro --write
python scripts/score_outputs.py --output-root outputs_repro/graph_maxflow --write
```

The scorer writes `scores.json` and `scores.csv`. It extracts the final `ANSWER:` from `output.json`, normalizes predictions by task type, compares against the copied fixture label, and reports overall plus per-task accuracy.

For long runs, keep scoring completed tasks even if later tasks fail:

```bash
python scripts/run_pipeline.py --config configs/math_geometry_subset.json --continue-on-error
```

Config `environment` values fill defaults without overriding `.env`. Pass `--override-env` only when you intentionally want the config to replace existing environment values.

## 9. Troubleshooting

- **Missing `autogen`**: activate `sketchpad` or rerun `bash scripts/setup_env.sh sketchpad`.
- **Jupyter runtime errors**: run from the repository root; the runner redirects Jupyter caches into `.cache/`.
- **OpenAI errors**: check `.env`, model access, and whether the backup key is present.
- **Vision server errors**: verify all three server URLs are reachable before running a vision config.
- **Unparsed score rows**: inspect `prediction`, `normalized_prediction`, and `error` in `scores.csv`.
- **Dependency drift**: use `env.txt` as a reference if a new machine resolves incompatible package versions.
