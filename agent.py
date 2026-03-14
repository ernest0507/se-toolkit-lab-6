#!/usr/bin/env python3
# pyright: reportUnknownMemberType=none, reportUnknownVariableType=none, reportAttributeAccessIssue=none, reportArgumentType=none, reportUnknownArgumentType=none
"""
Documentation Agent for SE Toolkit Lab 6 - Task 2.

This agent accepts a user query and returns a JSON response with:
- answer: The agent's response to the query
- source: Path to the file(s) used as source
- tool_calls: List of tool calls made during execution

Tools available:
- read_file: Read contents of a file
- list_files: List files in a directory
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
    ChatCompletionUserMessageParam,
)

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent

# System prompt for the agent
SYSTEM_PROMPT = f"""You are a documentation assistant for the SE Toolkit Lab 6 project.
Your role is to answer questions about the project documentation by reading files from the wiki directory.

You have access to the following tools:
1. read_file(path: str) - Read the contents of a file. Use this to read documentation files.
2. list_files(path: str) - List files in a directory. Use this to explore directory contents.

The project root is: {PROJECT_ROOT}

When answering questions:
1. First, determine which files might contain the answer
2. Use read_file to read relevant documentation files
3. Use list_files to explore directories if needed
4. Provide a concise answer based on the file contents

Always format your final response as JSON with the following structure:
{{
  "answer": "your response here",
  "source": "path/to/file/used.md",
  "tool_calls": [{{"name": "read_file", "arguments": {{"path": "path/to/file.md"}}}}]
}}

If you need to read multiple files, include all tool calls in the tool_calls array.
The "source" field should contain the path(s) of files you read to answer the question."""


# Tool definitions for OpenAI function calling
TOOLS: list[ChatCompletionToolParam] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the project directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file (e.g., 'wiki/git.md')",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory within the project",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the directory (e.g., 'wiki/')",
                    }
                },
                "required": ["path"],
            },
        },
    },
]


def is_safe_path(requested_path: str) -> bool:
    """
    Check if the requested path is within the project directory.

    Prevents directory traversal attacks by ensuring the resolved path
    starts with the project root.
    """
    try:
        resolved = (PROJECT_ROOT / requested_path).resolve()
        return str(resolved).startswith(str(PROJECT_ROOT.resolve()))
    except (ValueError, OSError):
        return False


def read_file(path: str) -> dict[str, Any]:
    """
    Read the contents of a file.

    Args:
        path: Relative path to the file

    Returns:
        Dictionary with 'success', 'content' or 'error' keys
    """
    if not is_safe_path(path):
        return {"success": False, "error": f"Path not allowed: {path}"}

    file_path = PROJECT_ROOT / path
    if not file_path.exists():
        return {"success": False, "error": f"File not found: {path}"}

    if not file_path.is_file():
        return {"success": False, "error": f"Not a file: {path}"}

    try:
        content = file_path.read_text(encoding="utf-8")
        return {"success": True, "content": content}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_files(path: str) -> dict[str, Any]:
    """
    List files in a directory.

    Args:
        path: Relative path to the directory

    Returns:
        Dictionary with 'success', 'files' or 'error' keys
    """
    if not is_safe_path(path):
        return {"success": False, "error": f"Path not allowed: {path}"}

    dir_path = PROJECT_ROOT / path
    if not dir_path.exists():
        return {"success": False, "error": f"Directory not found: {path}"}

    if not dir_path.is_dir():
        return {"success": False, "error": f"Not a directory: {path}"}

    try:
        files = [f.name for f in dir_path.iterdir() if not f.name.startswith(".")]
        return {"success": True, "files": sorted(files)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Execute a tool by name with the given arguments.

    Args:
        name: Name of the tool to execute
        arguments: Arguments for the tool

    Returns:
        Result of the tool execution
    """
    if name == "read_file":
        return read_file(arguments.get("path", ""))
    elif name == "list_files":
        return list_files(arguments.get("path", ""))
    else:
        return {"success": False, "error": f"Unknown tool: {name}"}


def get_llm_client() -> OpenAI:
    """Create and return an OpenAI-compatible LLM client."""
    api_key = os.environ.get("LLM_API_KEY", "")
    api_base = os.environ.get("LLM_API_BASE", "http://localhost:8000/v1")

    return OpenAI(api_key=api_key, base_url=api_base)


def run_agent(query: str) -> dict[str, Any]:
    """
    Run the agent with the given query using the agentic loop.

    The loop:
    1. Call LLM with query and available tools
    2. If LLM requests tool calls, execute them
    3. Send tool results back to LLM
    4. Get final answer and return JSON

    Args:
        query: The user's input query

    Returns:
        A dictionary with 'answer', 'source', and 'tool_calls' keys
    """
    client = get_llm_client()
    model = os.environ.get("LLM_MODEL", "qwen3-coder-plus")

    try:
        # First LLM call - get initial response with potential tool calls
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            tools=TOOLS,
            temperature=0.7,
        )

        message = response.choices[0].message
        tool_calls = message.tool_calls or []
        executed_tools: list[dict[str, Any]] = []
        sources: list[str] = []

        # Execute tools if requested
        if tool_calls:
            for tool_call in tool_calls:
                if tool_call.function.name in ["read_file", "list_files"]:
                    name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    result = execute_tool(name, arguments)

                    executed_tools.append(
                        {"name": name, "arguments": arguments, "result": result}
                    )

                    # Track sources
                    if name == "read_file" and result.get("success"):
                        sources.append(arguments.get("path", ""))

            # Second LLM call - send tool results and get final answer
            messages: list[ChatCompletionMessageParam] = [
                ChatCompletionSystemMessageParam(role="system", content=SYSTEM_PROMPT),
                ChatCompletionUserMessageParam(role="user", content=query),
                ChatCompletionAssistantMessageParam(
                    role="assistant", tool_calls=tool_calls
                ),
            ]

            # Add tool results as tool messages
            for idx, tool_result in enumerate(executed_tools):
                messages.append(
                    ChatCompletionToolMessageParam(
                        role="tool",
                        tool_call_id=tool_calls[idx].id,
                        content=json.dumps(tool_result["result"]),
                    )
                )

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS,
                temperature=0.7,
            )

            content = response.choices[0].message.content or ""
        else:
            content = message.content or ""

        # Parse final response as JSON
        try:
            result: dict[str, Any] = json.loads(content)
            # Ensure required fields exist
            if "answer" not in result:
                result["answer"] = content
            if "source" not in result:
                result["source"] = sources[0] if sources else ""
            if "tool_calls" not in result:
                result["tool_calls"] = [
                    {"name": t["name"], "arguments": t["arguments"]}
                    for t in executed_tools
                ]
            return result
        except json.JSONDecodeError:
            # If not valid JSON, wrap the content
            return {
                "answer": content,
                "source": sources[0] if sources else "",
                "tool_calls": [
                    {"name": t["name"], "arguments": t["arguments"]}
                    for t in executed_tools
                ],
            }

    except Exception as e:
        # Return error response if LLM call fails
        return {"answer": f"Error: {str(e)}", "source": "", "tool_calls": []}


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(
            json.dumps({"answer": "No query provided", "source": "", "tool_calls": []})
        )
        return

    query = " ".join(sys.argv[1:])
    result = run_agent(query)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
