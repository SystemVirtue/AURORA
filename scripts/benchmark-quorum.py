"""Run the deterministic QUORUM benchmark without provider/API calls."""

from aurora.evaluation import run_benchmark

import json


if __name__ == "__main__":
    report = run_benchmark()
    print(json.dumps(report, indent=2, sort_keys=True))
