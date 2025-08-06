#!/usr/bin/env python3
"""
Test Report Generator

Generates HTML and JSON reports from test results.
"""

import json
import sys
from datetime import datetime
from pathlib import Path


def generate_html_report(test_results: dict, output_path: str):
    """Generate HTML report"""
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>KME Test Results</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 10px; border-radius: 5px; }}
        .stage {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }}
        .passed {{ background-color: #d4edda; border-color: #c3e6cb; }}
        .failed {{ background-color: #f8d7da; border-color: #f5c6cb; }}
        .test {{ margin: 5px 0; padding: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>KME Test Results</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
"""

    for stage_name, stage_data in test_results.get("stages", {}).items():
        status = stage_data.get("status", "UNKNOWN")
        css_class = "passed" if status == "PASSED" else "failed"

        html_content += f"""
    <div class="stage {css_class}">
        <h3>{stage_data.get('name', stage_name)}</h3>
        <p>Status: {status}</p>
        <p>Duration: {stage_data.get('duration_seconds', 0):.2f} seconds</p>
"""

        for test_name, test_data in stage_data.get("tests", {}).items():
            test_status = test_data.get("status", "UNKNOWN")
            test_css_class = "passed" if test_status == "PASSED" else "failed"

            html_content += f"""
        <div class="test {test_css_class}">
            <strong>{test_data.get('name', test_name)}</strong>: {test_status}
            <br><small>{test_data.get('details', '')}</small>
        </div>
"""

        html_content += """
    </div>
"""

    html_content += """
</body>
</html>
"""

    with open(output_path, "w") as f:
        f.write(html_content)


def main():
    """Main report generator"""
    if len(sys.argv) < 2:
        print("Usage: python report_generator.py <test_results.json>")
        sys.exit(1)

    results_file = sys.argv[1]

    if not Path(results_file).exists():
        print(f"Results file not found: {results_file}")
        sys.exit(1)

    with open(results_file) as f:
        test_results = json.load(f)

    # Generate HTML report
    html_path = results_file.replace(".json", ".html")
    generate_html_report(test_results, html_path)

    print(f"✅ HTML report generated: {html_path}")


if __name__ == "__main__":
    main()
