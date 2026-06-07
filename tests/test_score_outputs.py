#!/usr/bin/env python3
"""Lightweight checks for score_outputs normalization."""

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from score_outputs import normalize, normalized_values  # noqa: E402


def check(actual, expected):
    if actual != expected:
        raise AssertionError(f"expected {expected!r}, got {actual!r}")


def main():
    check(normalize("graph_maxflow", "The maximum flow from node 0 to node 2 is 5."), 5)
    check(normalize("graph_connectivity", "yes, there is a path"), True)
    check(normalize("graph_connectivity", "no path exists"), False)
    check(normalize("graph_isomorphism", "The graphs are not isomorphic."), False)
    check(normalize("math_parity", "ANSWER: odd."), "odd")
    check(normalize("math_convexity", "The function is convex."), "convex")
    check(normalize("winner_id", "White wins by checkmate."), "white")
    check(normalize("blink_spatial", "(A) yes"), "a")
    check(normalize("mmvp", "option (b)"), "b")
    geometry_dir = REPO_ROOT / "tasks" / "geometry" / "2079"
    check("d" in normalized_values("geometry", "90", geometry_dir, "prediction"), True)
    check("90" in normalized_values("geometry", "D", geometry_dir, "truth"), True)
    print("score_outputs normalization checks passed.")


if __name__ == "__main__":
    main()
