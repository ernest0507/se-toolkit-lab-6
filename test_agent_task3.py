#!/usr/bin/env python3
"""Regression tests for the system agent tools (Task 3).

These tests verify that the agent correctly uses tools for different question types.
"""

import json
import subprocess
import sys
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent


def run_agent(query: str) -> dict:
    """Run the agent with the given query and return the JSON response."""
    result = subprocess.run(
        [sys.executable, "agent.py", query],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=60,
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"Agent failed: {result.stderr}")
    
    return json.loads(result.stdout)


def test_backend_framework_question():
    """Test that agent uses read_file for backend framework questions.
    
    Question: "What framework does the backend use?"
    Expected: read_file tool should be called to read backend source code.
    """
    query = "What framework does the backend use?"
    result = run_agent(query)
    
    # Check that answer exists and is not empty
    assert "answer" in result, "Missing 'answer' field"
    assert result["answer"], "Answer is empty"
    
    # Check that source is provided
    assert "source" in result, "Missing 'source' field"
    assert result["source"], "Source is empty"
    
    # Check that read_file was called
    assert "tool_calls" in result, "Missing 'tool_calls' field"
    tools_used = [tc.get("tool") for tc in result["tool_calls"]]
    assert "read_file" in tools_used, (
        f"Expected read_file in tool_calls, got: {tools_used}"
    )
    
    # Check that answer mentions FastAPI
    answer_lower = result["answer"].lower()
    assert "fastapi" in answer_lower, (
        f"Answer should mention FastAPI: {result['answer']}"
    )
    
    print(f"[PASS] Test passed: backend framework question")
    print(f"  Answer: {result['answer'][:100]}...")
    print(f"  Tools: {tools_used}")


def test_database_items_count_question():
    """Test that agent uses query_api for database count questions.
    
    Question: "How many items are in the database?"
    Expected: query_api tool should be called to query the /items/ endpoint.
    """
    query = "How many items are in the database?"
    result = run_agent(query)
    
    # Check that answer exists
    assert "answer" in result, "Missing 'answer' field"
    
    # Check that source is provided
    assert "source" in result, "Missing 'source' field"
    
    # Check that query_api was called
    assert "tool_calls" in result, "Missing 'tool_calls' field"
    tools_used = [tc.get("tool") for tc in result["tool_calls"]]
    assert "query_api" in tools_used, (
        f"Expected query_api in tool_calls, got: {tools_used}"
    )
    
    # Check that answer contains a number
    import re
    numbers = re.findall(r"\d+", result["answer"])
    assert numbers, f"Answer should contain a number: {result['answer']}"
    
    print(f"[PASS] Test passed: database items count question")
    print(f"  Answer: {result['answer'][:100]}...")
    print(f"  Tools: {tools_used}")


if __name__ == "__main__":
    print("Running regression tests for system agent tools...\n")
    
    try:
        test_backend_framework_question()
        print()
        test_database_items_count_question()
        print()
        print("All tests passed!")
    except AssertionError as e:
        print(f"[FAIL] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        sys.exit(1)
