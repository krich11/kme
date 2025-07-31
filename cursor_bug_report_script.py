#!/usr/bin/env python3
"""
Cursor Bug Report Script
Simulates the exact conditions where terminal output fails to reach the Cursor LLM agent.

This script reproduces the communication failure pattern we've observed:
- Works: Simple commands, basic output
- Fails: Complex imports, pytest execution, module initialization
"""

import importlib
import os
import sys
import time
from datetime import datetime


def log_with_timestamp(message):
    """Log message with precise timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {message}")
    sys.stdout.flush()


def test_simple_imports():
    """Test 1: Simple imports that work"""
    log_with_timestamp("TEST_1_START: Simple imports")
    try:
        import os
        import sys
        import time

        log_with_timestamp("TEST_1_SUCCESS: Basic imports completed")
    except Exception as e:
        log_with_timestamp(f"TEST_1_FAILED: {e}")
    log_with_timestamp("TEST_1_END")


def test_pytest_import():
    """Test 2: Pytest import (this works)"""
    log_with_timestamp("TEST_2_START: Pytest import")
    try:
        import pytest

        log_with_timestamp("TEST_2_SUCCESS: Pytest import completed")
    except Exception as e:
        log_with_timestamp(f"TEST_2_FAILED: {e}")
    log_with_timestamp("TEST_2_END")


def test_kme_imports():
    """Test 3: KME service imports (this is where it fails)"""
    log_with_timestamp("TEST_3_START: KME service imports")
    try:
        # These are the imports that cause communication failure
        log_with_timestamp("TEST_3_STEP1: Attempting to import KME services...")

        # Add the app directory to Python path
        sys.path.insert(0, os.path.join(os.getcwd(), "app"))

        log_with_timestamp("TEST_3_STEP2: Importing key_storage_service...")
        from services.key_storage_service import KeyStorageService

        log_with_timestamp("TEST_3_STEP3: KeyStorageService imported successfully")

        log_with_timestamp("TEST_3_STEP4: Importing key_pool_service...")
        from services.key_pool_service import KeyPoolService

        log_with_timestamp("TEST_3_STEP5: KeyPoolService imported successfully")

        log_with_timestamp("TEST_3_STEP6: Importing key_service...")
        from services.key_service import KeyService

        log_with_timestamp("TEST_3_STEP7: KeyService imported successfully")

        log_with_timestamp("TEST_3_SUCCESS: All KME services imported")

    except Exception as e:
        log_with_timestamp(f"TEST_3_FAILED: {e}")
        import traceback

        log_with_timestamp(f"TEST_3_TRACEBACK: {traceback.format_exc()}")

    log_with_timestamp("TEST_3_END")


def test_pytest_execution():
    """Test 4: Actual pytest execution (this is where it hangs)"""
    log_with_timestamp("TEST_4_START: Pytest execution")
    try:
        log_with_timestamp("TEST_4_STEP1: Starting pytest collection...")

        # This is the command that hangs
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "test/phase3/test_key_management_comprehensive.py::TestPhase3KeyManagement::TestSecureKeyStorage::test_key_encryption_at_rest",
                "--collect-only",
                "-v",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        log_with_timestamp(
            f"TEST_4_SUCCESS: Pytest completed with return code {result.returncode}"
        )
        log_with_timestamp(f"TEST_4_STDOUT: {result.stdout[:200]}...")

    except subprocess.TimeoutExpired:
        log_with_timestamp("TEST_4_FAILED: Pytest timed out after 30 seconds")
    except Exception as e:
        log_with_timestamp(f"TEST_4_FAILED: {e}")

    log_with_timestamp("TEST_4_END")


def test_environment_setup():
    """Test 5: Environment setup that might cause issues"""
    log_with_timestamp("TEST_5_START: Environment setup")

    # Set environment variables that might affect communication
    os.environ["CURSOR_AGENT"] = "1"
    os.environ["KME_MASTER_KEY"] = "HUY30kx6Q2McrX6Nqaw9YpyRbZ3ChpbxKV2mEEYS9jw="

    log_with_timestamp(f"TEST_5_ENV: CURSOR_AGENT={os.getenv('CURSOR_AGENT')}")
    log_with_timestamp(
        f"TEST_5_ENV: KME_MASTER_KEY set: {'yes' if os.getenv('KME_MASTER_KEY') else 'no'}"
    )

    log_with_timestamp("TEST_5_SUCCESS: Environment setup completed")
    log_with_timestamp("TEST_5_END")


def main():
    """Main test sequence"""
    log_with_timestamp("=== CURSOR BUG REPORT SCRIPT START ===")
    log_with_timestamp(
        f"Script started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    log_with_timestamp(f"Python version: {sys.version}")
    log_with_timestamp(f"Working directory: {os.getcwd()}")
    log_with_timestamp(f"User: {os.getenv('USER', 'unknown')}")
    log_with_timestamp(f"Terminal: {os.getenv('TERM', 'unknown')}")

    # Run tests in order of increasing complexity
    test_simple_imports()
    time.sleep(1)

    test_pytest_import()
    time.sleep(1)

    test_environment_setup()
    time.sleep(1)

    test_kme_imports()
    time.sleep(1)

    test_pytest_execution()
    time.sleep(1)

    log_with_timestamp("=== CURSOR BUG REPORT SCRIPT END ===")
    log_with_timestamp("If you see this message, the script completed successfully")
    log_with_timestamp(
        "If the agent didn't see this message, there's a communication failure"
    )

    # Final flush to ensure all output is sent
    sys.stdout.flush()
    sys.stderr.flush()


if __name__ == "__main__":
    main()
