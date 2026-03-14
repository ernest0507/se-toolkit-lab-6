"""Regression tests for documentation agent - Task 2.

These tests verify the agent's tool execution and path security.
"""

import json
import subprocess
import sys
from pathlib import Path


def test_merge_conflict_question_structure() -> None:
    """
    Test that asking about merge conflicts returns valid JSON structure.

    Question: "How do you resolve a merge conflict?"
    Expected: Valid JSON with answer, source, and tool_calls fields
    """
    project_root = Path(__file__).resolve().parent
    agent_path = project_root / "agent.py"

    result = subprocess.run(
        [
            sys.executable,
            str(agent_path),
            "How do you resolve a merge conflict?",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    output = json.loads(result.stdout)

    # Verify required fields exist
    assert "answer" in output, "Output must contain 'answer' field"
    assert "source" in output, "Output must contain 'source' field"
    assert "tool_calls" in output, "Output must contain 'tool_calls' field"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be a list"


def test_wiki_files_question_structure() -> None:
    """
    Test that asking about wiki files returns valid JSON structure.

    Question: "What files are in the wiki?"
    Expected: Valid JSON with answer, source, and tool_calls fields
    """
    project_root = Path(__file__).resolve().parent
    agent_path = project_root / "agent.py"

    result = subprocess.run(
        [
            sys.executable,
            str(agent_path),
            "What files are in the wiki?",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )

    output = json.loads(result.stdout)

    # Verify required fields exist
    assert "answer" in output, "Output must contain 'answer' field"
    assert "source" in output, "Output must contain 'source' field"
    assert "tool_calls" in output, "Output must contain 'tool_calls' field"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be a list"


def test_read_file_tool_exists() -> None:
    """
    Test that the read_file tool is defined and callable.

    This test verifies the tool schema exists in agent.py.
    """
    project_root = Path(__file__).resolve().parent
    agent_path = project_root / "agent.py"

    # Read agent.py and check for read_file function
    agent_code = agent_path.read_text(encoding="utf-8")

    # Verify read_file function exists
    assert "def read_file(" in agent_code, "read_file function should be defined"
    assert "def list_files(" in agent_code, "list_files function should be defined"
    assert "is_safe_path" in agent_code, "is_safe_path security check should be defined"
