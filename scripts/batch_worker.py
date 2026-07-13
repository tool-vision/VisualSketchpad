"""Batch worker: run the Visual Sketchpad agent over a manifest of instances.

Reads a JSONL manifest where each line is:
    {"id": "<unique id>", "query": "<question text with <img src='...'> tags>",
     "images": ["/abs/path/img.jpg", ...]}

For each instance it prepares a task-input dir (request.json), runs the unchanged
agent loop (agent/main.py:run_agent, task_type="vision"), extracts the final
"ANSWER: ..." from the trace, and writes one result JSON per instance under
<output-root>/results/<id>.json. Already-finished ids are skipped, so reruns
resume for free.

Run inside the `sketchpad` conda env, e.g.:
    python scripts/batch_worker.py --manifest m.jsonl --output-root out/ --num-workers 32
"""

import argparse
import json
import multiprocessing as mp
import os
import re
import signal
import sys
import traceback

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(REPO_ROOT, "agent")
if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

ANSWER_RE = re.compile(r"ANSWER\s*:\s*(.*?)(?:TERMINATE|$)", re.DOTALL)


class InstanceTimeout(Exception):
    pass


def _alarm_handler(signum, frame):
    raise InstanceTimeout("instance timed out")


def extract_answer(messages):
    """Pull the final ANSWER: ... out of the planner message trace."""
    if isinstance(messages, dict):
        if "error" in messages:
            return None
        messages = messages.get("messages", [])
    answer = None
    for msg in messages:
        content = msg.get("content") if isinstance(msg, dict) else msg
        if isinstance(content, list):  # multimodal content blocks
            content = " ".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        if not isinstance(content, str):
            continue
        m = ANSWER_RE.search(content)
        if m:
            answer = m.group(1).strip()
    return answer


def solve_instance(job):
    instance, output_root, timeout = job
    instance_id = str(instance["id"])
    result_path = os.path.join(output_root, "results", f"{instance_id}.json")
    input_dir = os.path.join(output_root, "inputs", instance_id)
    runs_dir = os.path.join(output_root, "runs")

    os.makedirs(input_dir, exist_ok=True)
    with open(os.path.join(input_dir, "request.json"), "w") as f:
        json.dump(
            {"query": instance["query"], "images": instance["images"]}, f, indent=2
        )

    result = {"id": instance_id, "answer": None, "error": None}
    old_handler = signal.signal(signal.SIGALRM, _alarm_handler)
    signal.alarm(timeout)
    try:
        from main import run_agent

        run_agent(input_dir, runs_dir, task_type="vision")
        output_json = os.path.join(runs_dir, instance_id, "output.json")
        with open(output_json) as f:
            messages = json.load(f)
        if isinstance(messages, dict) and "error" in messages:
            result["error"] = messages["error"]
        result["answer"] = extract_answer(messages)
    except Exception:
        result["error"] = traceback.format_exc()
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

    tmp_path = result_path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(result, f, indent=2)
    os.replace(tmp_path, result_path)
    status = "ok" if result["answer"] is not None else "no-answer"
    print(f"[{status}] {instance_id}", flush=True)
    return instance_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--num-workers", type=int, default=32)
    parser.add_argument(
        "--instance-timeout", type=int, default=900, help="seconds per instance"
    )
    parser.add_argument(
        "--tasks-per-child",
        type=int,
        default=4,
        help="recycle worker processes after this many instances (guards against leaked jupyter kernels)",
    )
    args = parser.parse_args()

    # Fail fast on unreachable endpoints (LLM + the three vision servers);
    # otherwise every instance would burn a full agent attempt and error out.
    import urllib.request

    checks = []
    base_url = os.environ.get("OPENAI_BASE_URL")
    if base_url:
        checks.append(("LLM", base_url.rstrip("/") + "/models"))
    for env_name, default in (
        ("SOM_ADDRESS", "http://localhost:8080/"),
        ("GROUNDING_DINO_ADDRESS", "http://localhost:8081/"),
        ("DEPTH_ANYTHING_ADDRESS", "http://localhost:8082/"),
    ):
        checks.append((env_name, os.environ.get(env_name, default)))
    for label, url in checks:
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                r.read(64)
        except Exception as exc:
            print(f"FATAL: {label} endpoint {url} unreachable: {exc}", flush=True)
            sys.exit(2)

    instances = []
    with open(args.manifest) as f:
        for line in f:
            line = line.strip()
            if line:
                instances.append(json.loads(line))

    results_dir = os.path.join(args.output_root, "results")
    os.makedirs(results_dir, exist_ok=True)
    pending = [
        inst
        for inst in instances
        if not os.path.exists(os.path.join(results_dir, f"{inst['id']}.json"))
    ]
    print(
        f"{len(instances)} instances, {len(instances) - len(pending)} done, {len(pending)} to run",
        flush=True,
    )
    if not pending:
        print("BATCH_COMPLETE", flush=True)
        return

    jobs = [(inst, args.output_root, args.instance_timeout) for inst in pending]
    ctx = mp.get_context("spawn")
    with ctx.Pool(
        processes=min(args.num_workers, len(jobs)),
        maxtasksperchild=args.tasks_per_child,
    ) as pool:
        for _ in pool.imap_unordered(solve_instance, jobs):
            pass
    print("BATCH_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
