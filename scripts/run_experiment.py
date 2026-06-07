#!/usr/bin/env python3
"""Run a bounded Visual Sketchpad benchmark split reproducibly."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = REPO_ROOT / "agent"

VISION_TASKS = {
    "vstar",
    "blink_viscorr",
    "blink_semcorr",
    "blink_depth",
    "blink_jigsaw",
    "blink_spatial",
    "mmvp",
}
GEO_TASKS = {"geometry"}
MATH_TASKS = {
    "graph_connectivity",
    "graph_isomorphism",
    "graph_maxflow",
    "math_convexity",
    "math_parity",
    "winner_id",
}
ALL_TASKS = sorted(VISION_TASKS | GEO_TASKS | MATH_TASKS)


def load_dotenv(path):
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


def natural_key(path):
    value = path.name
    return (0, int(value)) if value.isdigit() else (1, value)


def task_settings(task):
    if task in VISION_TASKS:
        return "vision", None, REPO_ROOT / "tasks" / task / "processed"
    if task in GEO_TASKS:
        return "geo", None, REPO_ROOT / "tasks" / task
    if task in MATH_TASKS:
        return "math", task, REPO_ROOT / "tasks" / task
    raise ValueError(f"Unsupported task: {task}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, choices=ALL_TASKS)
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "outputs_repro"))
    parser.add_argument("--max-instances", type=int, default=1)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--require-api-key", action="store_true")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    cache_root = REPO_ROOT / ".cache"
    cache_paths = {
        "MPLCONFIGDIR": cache_root / "matplotlib",
        "JUPYTER_RUNTIME_DIR": cache_root / "jupyter" / "runtime",
        "JUPYTER_CONFIG_DIR": cache_root / "jupyter" / "config",
        "JUPYTER_DATA_DIR": cache_root / "jupyter" / "data",
        "IPYTHONDIR": cache_root / "ipython",
    }
    for env_name, path in cache_paths.items():
        path.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault(env_name, str(path))
    if args.require_api_key and not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is required for agent runs.")

    task_type, task_name, input_root = task_settings(args.task)
    if not input_root.exists():
        raise SystemExit(f"Task input directory not found: {input_root}")

    instances = sorted((p for p in input_root.iterdir() if p.is_dir()), key=natural_key)
    selected = instances[args.start_index : args.start_index + args.max_instances]
    if not selected:
        raise SystemExit("No task instances selected.")

    output_dir = Path(args.output_dir) / args.task
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "task": args.task,
        "task_type": task_type,
        "task_name": task_name,
        "max_instances": args.max_instances,
        "start_index": args.start_index,
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o"),
        "has_backup_api_key": bool(os.environ.get("OPENAI_API_KEY_BACKUP")),
        "instances": [str(path.relative_to(REPO_ROOT)) for path in selected],
    }
    (output_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2))

    try:
        import autogen  # noqa: F401
    except ImportError as error:
        raise SystemExit(
            "Missing dependency 'autogen'. Create the environment with "
            "'bash scripts/setup_env.sh sketchpad' or install the README dependencies."
        ) from error

    sys.path.insert(0, str(AGENT_DIR))
    from main import run_agent

    for instance in selected:
        print(f"Running {args.task}: {instance.relative_to(REPO_ROOT)}")
        run_agent(str(instance), str(output_dir), task_type=task_type, task_name=task_name)

    print(f"Wrote outputs to {output_dir}")


if __name__ == "__main__":
    main()
