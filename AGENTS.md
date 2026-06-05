# Repository Guidelines

## Project Structure & Module Organization

`agent/` contains the core Visual Sketchpad runtime: prompts, parsers, tool clients, execution helpers, and entry points such as `quick_start_math.py`, `quick_start_vision.py`, and `run_task.py`. `tasks/` stores task inputs by benchmark and instance, usually as `example.json`, `ex.json`, or `request.json` plus images. `outputs/` holds reference and generated traces, including `output.json` and `usage_summary.json`. `vision_experts/` vendors optional Gradio-based vision servers for SOM, GroundingDINO, and Depth-Anything. `assets/` contains README images and icons; `record_viewer.ipynb` visualizes saved agent traces.

## Build, Test, and Development Commands

Create the base environment from the README:

```bash
conda create -n sketchpad python=3.9
pip install pyautogen==0.2.26 'pyautogen[jupyter-executor]'
pip install Pillow joblib matplotlib opencv-python numpy gradio gradio_client networkx scipy datasets
```

For the latest full dependency snapshot, use `env.txt` as a reference. Configure `OPENAI_API_KEY` and model settings in `agent/config.py` before running agents.

Run local examples from `agent/`:

```bash
python quick_start_math.py
python quick_start_vision.py
python run_task.py --task geometry
```

Vision tasks also require the servers documented in `vision_experts/installation.md`.

## Coding Style & Naming Conventions

Use Python 3.9-compatible code with 4-space indentation. Follow the existing module style: snake_case functions and variables, PascalCase classes, and task names matching directory names such as `graph_maxflow` or `blink_spatial`. Keep paths relative to the caller conventions already used in `agent/` (`../tasks/...`, `../outputs/...`). Avoid committing local API keys, server URLs, generated caches, or machine-specific files.

## Testing Guidelines

There is no dedicated root test suite. Validate changes with the smallest relevant entry point: math and geometry changes through `python quick_start_math.py` or `python run_task.py --task geometry`; vision-tool changes through `python quick_start_vision.py` after servers are running. For new behavior, add a small reproducible task fixture under the appropriate `tasks/<task>/` subtree and confirm the resulting `outputs/<task>/<instance>/output.json`.

## Commit & Pull Request Guidelines

Recent history uses short imperative or descriptive messages such as `Update README.md` and `add latest environment`; keep commits concise and scoped. Pull requests should include the motivation, commands run, affected task types, and any required configuration changes. For visual or trajectory changes, include representative output paths or screenshots from `record_viewer.ipynb`.

## Security & Configuration Tips

Do not hard-code private keys in shared changes to `agent/config.py`; prefer local-only edits or environment injection. Treat `tasks/` and `outputs/` as potentially large data directories, and avoid broad rewrites unless the change intentionally updates fixtures or reference traces.
