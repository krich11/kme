#!/usr/bin/env python3
"""
Test Runner

Runs KME test stages in sequence.
"""

import datetime
import json
import subprocess
import sys
from pathlib import Path


def run_test_stage(stage_name: str, stage_script: str) -> bool:
    """Run a test stage"""
    print(f"Running {stage_name}...")

    try:
        result = subprocess.run(
            ["python", stage_script], capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Failed to run {stage_name}: {e}")
        return False


def main():
    """Main test runner"""
    stages = [
        ("Stage 0.1: Environment Reset", "stage_0_1_reset.py"),
        ("Stage 0.2: CA Setup", "stage_0_2_ca_setup.py"),
        ("Stage 0.3: SAE Management", "stage_0_3_sae_management.py"),
        ("Stage 0.4: Database Operations", "stage_0_4_database_ops.py"),
    ]

    results = {}

    for stage_name, stage_script in stages:
        script_path = Path(__file__).parent / stage_script
        if script_path.exists():
            success = run_test_stage(stage_name, str(script_path))
            results[stage_name] = "PASSED" if success else "FAILED"
        else:
            print(f"Stage script not found: {script_path}")
            results[stage_name] = "SKIPPED"

    # Generate summary
    print("\n=== Test Results Summary ===")
    for stage_name, result in results.items():
        print(f"{stage_name}: {result}")

    # Save results
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = (
        Path(__file__).parent.parent / "results" / f"test_summary_{timestamp}.json"
    )

    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    main()
