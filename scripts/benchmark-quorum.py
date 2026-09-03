"""Run the deterministic QUORUM benchmark without provider/API calls."""

import json

from aurora.evaluation import run_benchmark  # noqa: I001


if __name__ == "__main__":
    report = run_benchmark()
    print(json.dumps(report, indent=2, sort_keys=True))
