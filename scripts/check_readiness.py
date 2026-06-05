#!/usr/bin/env python3
"""Report which Visual Sketchpad task families are runnable on this machine."""

import argparse
import os
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = REPO_ROOT / "agent"

VISION_TASKS = ["blink_depth", "blink_jigsaw", "blink_spatial", "mmvp"]
NON_VISION_TASKS = [
    "geometry",
    "graph_connectivity",
    "graph_isomorphism",
    "graph_maxflow",
    "math_convexity",
    "math_parity",
    "winner_id",
]


def load_dotenv(path):
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def count_instances(task):
    if task in VISION_TASKS:
        root = REPO_ROOT / "tasks" / task / "processed"
    else:
        root = REPO_ROOT / "tasks" / task
    if not root.exists():
        return 0
    return sum(1 for path in root.iterdir() if path.is_dir())


def import_status(module):
    try:
        __import__(module)
        return "ok"
    except Exception as error:
        return f"missing ({type(error).__name__}: {error})"


def check_url(name, url, timeout):
    try:
        with urlopen(url, timeout=timeout) as response:
            return f"reachable status={response.status}"
    except (OSError, URLError) as error:
        return f"not reachable ({type(error).__name__}: {error})"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-servers", action="store_true", help="Probe configured vision server URLs.")
    parser.add_argument("--timeout", type=float, default=3)
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    cache_root = REPO_ROOT / ".cache"
    matplotlib_cache = cache_root / "matplotlib"
    matplotlib_cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_cache))
    sys.path.insert(0, str(AGENT_DIR))

    print("Environment")
    print(f"- OPENAI_API_KEY: {'set' if os.environ.get('OPENAI_API_KEY') else 'missing'}")
    print(f"- OPENAI_API_KEY_BACKUP: {'set' if os.environ.get('OPENAI_API_KEY_BACKUP') else 'missing'}")
    print(f"- OPENAI_MODEL: {os.environ.get('OPENAI_MODEL', 'gpt-4o')}")
    print(f"- autogen: {import_status('autogen')}")
    print(f"- networkx: {import_status('networkx')}")
    print(f"- matplotlib: {import_status('matplotlib')}")
    print(f"- gradio_client: {import_status('gradio_client')}")
    print(f"- chess: {import_status('chess')}")
    print(f"- cairosvg: {import_status('cairosvg')}")

    print("\nNon-vision task fixtures")
    for task in NON_VISION_TASKS:
        print(f"- {task}: {count_instances(task)} instances")

    print("\nVision task fixtures")
    for task in VISION_TASKS:
        print(f"- {task}: {count_instances(task)} instances")

    if args.check_servers:
        print("\nVision servers")
        defaults = {
            "SOM_ADDRESS": "http://localhost:8080/",
            "GROUNDING_DINO_ADDRESS": "http://localhost:8081/",
            "DEPTH_ANYTHING_ADDRESS": "http://localhost:8082/",
        }
        for name, default in defaults.items():
            url = os.environ.get(name, default)
            print(f"- {name}: {check_url(name, url, args.timeout)} ({url})")


if __name__ == "__main__":
    main()
