#!/usr/bin/env python3
"""Score Visual Sketchpad output directories against local fixture labels."""

import argparse
import csv
import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VISION_TASKS = {"blink_depth", "blink_jigsaw", "blink_spatial", "mmvp"}
TASKS = {
    "geometry",
    "graph_connectivity",
    "graph_isomorphism",
    "graph_maxflow",
    "math_convexity",
    "math_parity",
    "winner_id",
    *VISION_TASKS,
}


def message_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    return ""


def extract_answer(output_path):
    try:
        messages = json.loads(output_path.read_text())
    except Exception as error:
        return None, f"invalid output json: {error}"
    if isinstance(messages, dict) and "error" in messages:
        return None, f"run error: {messages['error']}"
    if not isinstance(messages, list):
        return None, "output is not a message list"

    for message in reversed(messages):
        if message.get("role") != "assistant":
            continue
        text = message_text(message.get("content"))
        match = re.search(r"ANSWER\s*:\s*(.*?)(?:\bTERMINATE\b|$)", text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip(), None
    return None, "no ANSWER field found"


def load_truth(instance_dir):
    for filename in ("example.json", "ex.json", "request.json"):
        path = instance_dir / filename
        if path.exists():
            data = json.loads(path.read_text())
            if "label" in data:
                return data["label"], filename
            if "answer" in data:
                return data["answer"], filename
    return None, None


def clean_text(value):
    return re.sub(r"\s+", " ", str(value).strip().lower())


def choice_letter(value):
    text = clean_text(value)
    match = re.search(r"\(([a-d])\)", text)
    if match:
        return match.group(1)
    match = re.search(r"\b([a-d])\b", text)
    if match:
        return match.group(1)
    return None


def first_integer(value):
    match = re.search(r"-?\d+", str(value))
    return int(match.group(0)) if match else None


def last_integer(value):
    matches = re.findall(r"-?\d+", str(value))
    return int(matches[-1]) if matches else None


def normalize_bool(value):
    if isinstance(value, bool):
        return value
    text = clean_text(value)
    if re.search(r"\b(yes|true|connected|isomorphic)\b", text):
        if not re.search(r"\b(no|false|not connected|not isomorphic|non-isomorphic)\b", text):
            return True
    if re.search(r"\b(no|false|not connected|not isomorphic|non-isomorphic)\b", text):
        return False
    return None


def normalize_category(value, options):
    text = clean_text(value)
    for option in options:
        if re.search(rf"\b{re.escape(option)}\b", text):
            return option
    return text if text in options else None


def geometry_truth_value(instance_dir, truth):
    fixture = json.loads((instance_dir / "ex.json").read_text())
    letter = clean_text(truth)
    if len(letter) == 1 and "a" <= letter <= "z":
        index = ord(letter) - ord("a")
        choices = fixture.get("choices") or fixture.get("compact_choices") or []
        if 0 <= index < len(choices):
            return clean_text(choices[index])
    return clean_text(truth)


def geometry_aliases(value, instance_dir, role):
    aliases = set()
    letter = choice_letter(value)
    if letter:
        aliases.add(letter)

    text = clean_text(value)
    if text:
        aliases.add(text)

    fixture_path = instance_dir / "ex.json" if instance_dir else None
    if fixture_path and fixture_path.exists():
        fixture = json.loads(fixture_path.read_text())
        choices = fixture.get("choices") or fixture.get("compact_choices") or []
        if role == "truth" and letter:
            index = ord(letter) - ord("a")
            if 0 <= index < len(choices):
                aliases.add(clean_text(choices[index]))
        if role == "prediction":
            for index, choice in enumerate(choices):
                if clean_text(choice) == text:
                    aliases.add(chr(ord("a") + index))
    return sorted(alias for alias in aliases if alias)


def normalize(task, value, instance_dir=None, role="prediction"):
    if value is None:
        return None
    if task == "graph_maxflow":
        return last_integer(value)
    if task in {"graph_connectivity", "graph_isomorphism"}:
        return normalize_bool(value)
    if task == "math_parity":
        return normalize_category(value, {"even", "odd", "neither"})
    if task == "math_convexity":
        return normalize_category(value, {"convex", "concave"})
    if task == "winner_id":
        return normalize_category(value, {"white", "black", "draw"})
    if task in VISION_TASKS:
        return choice_letter(value) or clean_text(value)
    if task == "geometry":
        aliases = geometry_aliases(value, instance_dir, role)
        return aliases[0] if aliases else None
    return clean_text(value)


def normalized_values(task, value, instance_dir=None, role="prediction"):
    if task == "geometry":
        return geometry_aliases(value, instance_dir, role)
    normalized = normalize(task, value, instance_dir, role)
    return [] if normalized is None else [normalized]


def infer_task(path):
    parts = path.parts
    for part in parts:
        if part in TASKS:
            return part
    return None


def score_instance(instance_dir):
    task = infer_task(instance_dir)
    output_path = instance_dir / "output.json"
    prediction, error = extract_answer(output_path)
    truth, fixture = load_truth(instance_dir)
    if task is None:
        error = error or "could not infer task"
    if truth is None:
        error = error or "missing ground truth"

    prediction_values = normalized_values(task, prediction, instance_dir, "prediction") if task else []
    truth_values = normalized_values(task, truth, instance_dir, "truth") if task else []
    normalized_prediction = prediction_values[0] if prediction_values else None
    normalized_truth = truth_values[0] if truth_values else None
    correct = bool(set(prediction_values) & set(truth_values)) if error is None else False
    parsed = bool(prediction_values) and error is None
    return {
        "task": task,
        "instance": str(instance_dir.relative_to(REPO_ROOT)),
        "fixture": fixture,
        "prediction": prediction,
        "truth": truth,
        "normalized_prediction": normalized_prediction,
        "normalized_truth": normalized_truth,
        "prediction_values": prediction_values,
        "truth_values": truth_values,
        "parsed": parsed,
        "correct": correct,
        "error": error,
    }


def find_instance_dirs(root):
    for output_path in root.rglob("output.json"):
        yield output_path.parent


def aggregate(rows):
    by_task = {}
    for row in rows:
        task = row["task"] or "unknown"
        stats = by_task.setdefault(task, {"total": 0, "correct": 0, "parsed": 0, "failed": 0})
        stats["total"] += 1
        stats["correct"] += int(bool(row["correct"]))
        stats["parsed"] += int(bool(row["parsed"]))
        stats["failed"] += int(bool(row["error"]))
    for stats in by_task.values():
        total = stats["total"] or 1
        stats["accuracy"] = stats["correct"] / total
        stats["parse_rate"] = stats["parsed"] / total
    overall = {"total": 0, "correct": 0, "parsed": 0, "failed": 0}
    for stats in by_task.values():
        for key in ("total", "correct", "parsed", "failed"):
            overall[key] += stats[key]
    total = overall["total"] or 1
    overall["accuracy"] = overall["correct"] / total
    overall["parse_rate"] = overall["parsed"] / total
    return {"overall": overall, "by_task": by_task}


def write_csv(rows, path):
    fieldnames = [
        "task",
        "instance",
        "fixture",
        "prediction",
        "truth",
        "normalized_prediction",
        "normalized_truth",
        "prediction_values",
        "truth_values",
        "parsed",
        "correct",
        "error",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default=str(REPO_ROOT / "outputs_repro"))
    parser.add_argument("--write", action="store_true", help="Write scores.json and scores.csv.")
    args = parser.parse_args()

    root = Path(args.output_root)
    if not root.is_absolute():
        root = REPO_ROOT / root
    rows = [score_instance(path) for path in sorted(find_instance_dirs(root))]
    summary = aggregate(rows)
    result = {"output_root": str(root), "summary": summary, "instances": rows}

    if args.write:
        root.mkdir(parents=True, exist_ok=True)
        (root / "scores.json").write_text(json.dumps(result, indent=2))
        write_csv(rows, root / "scores.csv")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
