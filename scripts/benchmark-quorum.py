"""Run the deterministic QUORUM benchmark without provider/API calls."""

# isort: off
import json
from aurora.evaluation import run_benchmark
# isort: on


if __name__ == "__main__":
    report = run_benchmark()
    print(json.dumps(report, indent=2, sort_keys=True))
