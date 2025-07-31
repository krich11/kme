#!/usr/bin/env python3
"""
KME API Test Runner

Simple script to run the comprehensive API test suite.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from test.test_api_workflows import main
except ImportError:
    print(
        "❌ Could not import test_api_workflows. Make sure you're running from the project root."
    )
    sys.exit(1)


if __name__ == "__main__":
    print("🚀 Starting KME API Test Suite...")
    print("=" * 60)

    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Test suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        sys.exit(2)
