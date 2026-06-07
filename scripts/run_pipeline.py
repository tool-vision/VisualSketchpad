#!/usr/bin/env python3
"""Run a reproducibility pipeline from a JSON config."""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]


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


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def check_url(name, url, timeout):
    try:
        with urlopen(url, timeout=timeout) as response:
            return response.status < 500
    except (OSError, URLError):
        raise SystemExit(f"{name} is not reachable: {url}")


def apply_environment(config_env, override=False):
    for key, value in config_env.items():
        if override:
            os.environ[str(key)] = str(value)
        else:
            os.environ.setdefault(str(key), str(value))


def task_command(task_config, defaults, require_api_key):
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_experiment.py"),
        "--task",
        task_config["name"],
        "--output-dir",
        str(REPO_ROOT / defaults.get("output_dir", "outputs_repro")),
        "--max-instances",
        str(task_config.get("max_instances", defaults.get("max_instances", 1))),
        "--start-index",
        str(task_config.get("start_index", defaults.get("start_index", 0))),
    ]
    if require_api_key:
        cmd.append("--require-api-key")
    return cmd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Path to a JSON pipeline config.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print commands without running them.")
    parser.add_argument("--no-score", action="store_true", help="Skip scoring after a completed run.")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue running later tasks after a task fails.")
    parser.add_argument("--override-env", action="store_true", help="Let config environment values override existing env/.env values.")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = REPO_ROOT / config_path
    config = json.loads(config_path.read_text())

    load_dotenv(REPO_ROOT / ".env")
    apply_environment(config.get("environment", {}), override=args.override_env)

    requirements = config.get("requirements", {})
    require_api_key = bool(requirements.get("api_key", True))
    if require_api_key:
        require(os.environ.get("OPENAI_API_KEY"), "OPENAI_API_KEY is required. Set it in .env or the environment.")

    if requirements.get("vision_servers") and args.dry_run:
        print("Dry run: skipping vision server reachability checks.")
    elif requirements.get("vision_servers"):
        timeout = float(requirements.get("server_timeout_seconds", 5))
        check_url("SOM_ADDRESS", os.environ.get("SOM_ADDRESS", ""), timeout)
        check_url("GROUNDING_DINO_ADDRESS", os.environ.get("GROUNDING_DINO_ADDRESS", ""), timeout)
        check_url("DEPTH_ANYTHING_ADDRESS", os.environ.get("DEPTH_ANYTHING_ADDRESS", ""), timeout)

    tasks = config.get("tasks", [])
    require(tasks, "Config must include at least one task.")

    defaults = config.get("defaults", {})
    run_root = REPO_ROOT / defaults.get("output_dir", "outputs_repro")
    run_root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "pipeline": config.get("name", config_path.stem),
        "config": str(config_path.relative_to(REPO_ROOT)),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o"),
        "tasks": tasks,
        "continue_on_error": args.continue_on_error,
        "override_env": args.override_env,
        "task_results": [],
    }
    (run_root / "pipeline_manifest.json").write_text(json.dumps(manifest, indent=2))

    commands = [task_command(task, defaults, require_api_key) for task in tasks]
    for cmd in commands:
        print(" ".join(cmd))

    if args.dry_run:
        return

    failures = []
    for task, cmd in zip(tasks, commands):
        result = subprocess.run(cmd, cwd=REPO_ROOT, env=os.environ.copy(), check=False)
        task_result = {"task": task["name"], "returncode": result.returncode, "command": cmd}
        manifest["task_results"].append(task_result)
        (run_root / "pipeline_manifest.json").write_text(json.dumps(manifest, indent=2))
        if result.returncode != 0:
            failures.append(task_result)
            if not args.continue_on_error:
                break

    if not args.no_score:
        subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "score_outputs.py"),
                "--output-root",
                str(run_root),
                "--write",
            ],
            cwd=REPO_ROOT,
            env=os.environ.copy(),
            check=True,
        )

    if failures:
        failed_tasks = ", ".join(item["task"] for item in failures)
        raise SystemExit(f"Pipeline completed with failed tasks: {failed_tasks}")


if __name__ == "__main__":
    main()
