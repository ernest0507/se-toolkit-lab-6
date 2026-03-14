"""Regression tests for agent.py - Task 1."""

import json
import subprocess
import sys
from pathlib import Path


def test_agent_output_contains_answer_and_tool_calls() -> None:
    """
    Test that agent.py outputs valid JSON with 'answer', 'source', and 'tool_calls' fields.

    This test runs agent.py as a subprocess with a sample query,
    parses the stdout JSON, and verifies the required fields are present.
    """
    # Get the project root directory
    project_root = Path(__file__).resolve().parent
    agent_path = project_root / "agent.py"

    # Run agent.py with a test query
    result = subprocess.run(
        [sys.executable, str(agent_path), "Hello, test query"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    # Parse stdout as JSON
    output = json.loads(result.stdout)

    # Verify required fields are present
    assert "answer" in output, "Output must contain 'answer' field"
    assert "source" in output, "Output must contain 'source' field"
    assert "tool_calls" in output, "Output must contain 'tool_calls' field"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be a list"
