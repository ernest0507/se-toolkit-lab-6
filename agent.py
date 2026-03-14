#!/usr/bin/env python3
"""
Basic LLM Agent for SE Toolkit Lab 6.

This agent accepts a user query and returns a JSON response with:
- answer: The agent's response to the query
- tool_calls: List of tool calls (empty in this minimal implementation)
"""

import json
import os
import sys
from typing import Any

from openai import OpenAI

# System prompt for the agent
SYSTEM_PROMPT = """You are a helpful assistant. Respond to the user's query concisely.

Always format your response as JSON with the following structure:
{
  "answer": "your response here",
  "tool_calls": []
}

The "tool_calls" field should be an empty list for now."""


def get_llm_client() -> OpenAI:
    """Create and return an OpenAI-compatible LLM client."""
    api_key = os.environ.get("LLM_API_KEY", "")
    api_base = os.environ.get("LLM_API_BASE", "http://localhost:8000/v1")

    return OpenAI(api_key=api_key, base_url=api_base)


def run_agent(query: str) -> dict[str, Any]:
    """
    Run the agent with the given query.

    Args:
        query: The user's input query

    Returns:
        A dictionary with 'answer' and 'tool_calls' keys
    """
    client = get_llm_client()
    model = os.environ.get("LLM_MODEL", "qwen3-coder-plus")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            temperature=0.7,
        )

        content = response.choices[0].message.content or ""

        # Try to parse as JSON
        try:
            result: dict[str, Any] = json.loads(content)
            # Ensure required fields exist
            if "answer" not in result:
                result["answer"] = content
            if "tool_calls" not in result:
                result["tool_calls"] = []
            return result
        except json.JSONDecodeError:
            # If not valid JSON, wrap the content
            return {"answer": content, "tool_calls": []}

    except Exception as e:
        # Return error response if LLM call fails
        return {"answer": f"Error: {str(e)}", "tool_calls": []}


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(json.dumps({"answer": "No query provided", "tool_calls": []}))
        return

    query = " ".join(sys.argv[1:])
    result = run_agent(query)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
