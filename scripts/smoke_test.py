#!/usr/bin/env python3
"""Offline smoke checks for the Visual Sketchpad repository."""

import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = REPO_ROOT / "agent"


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def load_json(path):
    with path.open("r") as handle:
        return json.load(handle)


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


def main():
    load_dotenv(REPO_ROOT / ".env")
    sys.path.insert(0, str(AGENT_DIR))

    required_paths = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "agent" / "main.py",
        REPO_ROOT / "agent" / "parse.py",
        REPO_ROOT / "tasks" / "graph_maxflow" / "5" / "example.json",
        REPO_ROOT / "tasks" / "geometry" / "2079" / "ex.json",
        REPO_ROOT / "outputs" / "graph_max_flow" / "5" / "output.json",
    ]
    for path in required_paths:
        check(path.exists(), f"Missing required path: {path.relative_to(REPO_ROOT)}")

    graph_example = load_json(REPO_ROOT / "tasks" / "graph_maxflow" / "5" / "example.json")
    geometry_example = load_json(REPO_ROOT / "tasks" / "geometry" / "2079" / "ex.json")
    graph_output = load_json(REPO_ROOT / "outputs" / "graph_max_flow" / "5" / "output.json")
    check(graph_example, "Graph maxflow fixture is empty")
    check(geometry_example, "Geometry fixture is empty")
    check(graph_output, "Reference output fixture is empty")

    from parse import Parser

    parsed = Parser().parse(
        "Thought: smoke\nAction:```python\n"
        "def solve():\n"
        "    return 1\n"
        "```"
    )
    check(parsed["status"], f"Parser smoke failed: {parsed}")

    import config

    check(config.llm_config["config_list"][0]["model"], "LLM model is not configured")
    if os.environ.get("OPENAI_API_KEY"):
        check(
            config.llm_config["config_list"][0]["api_key"] == os.environ["OPENAI_API_KEY"],
            "agent/config.py did not preserve OPENAI_API_KEY from the environment",
        )
    if os.environ.get("OPENAI_API_KEY_BACKUP"):
        check(
            len(config.llm_config["config_list"]) >= 2,
            "OPENAI_API_KEY_BACKUP is set but was not added to llm_config",
        )

    print("Smoke test passed: fixtures, parser, reference outputs, and config are usable.")


if __name__ == "__main__":
    main()
