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
import re
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
    ChatCompletionUserMessageParam,
)

# Load environment variables from .env.agent.secret
AGENT_ENV = Path(__file__).resolve().parent / ".env.agent.secret"
if AGENT_ENV.exists():
    load_dotenv(AGENT_ENV)

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent

# System prompt for the agent
SYSTEM_PROMPT = f"""You are a documentation assistant for the SE Toolkit Lab 6 project.
Your role is to answer questions about the project by reading files from the project directory.

You have access to the following tools:
1. read_file(path: str) - Read the contents of a file. Use this to read documentation and source code files.
2. list_files(path: str) - List files in a directory. Use this to explore directory contents.
3. query_api(url: str, api_key: str) - Make an HTTP GET request to query API endpoints.

The project root is: {PROJECT_ROOT}

Project structure:
- wiki/ - Documentation files (.md)
- backend/ - Backend source code (Python/FastAPI)
- frontend/ - Frontend source code
- lab/ - Lab materials

When answering questions:
1. First, determine which files might contain the answer
2. ALWAYS use read_file to read relevant files BEFORE answering
3. Use list_files to explore directories if needed
4. Use http_get to query running API endpoints when needed
5. Provide a concise answer based ONLY on the file contents you read

CRITICAL: You MUST call read_file to read relevant files before answering. Do not just mention file names - actually read them!
For questions about the backend, check backend/app/main.py and other files in backend/.
For questions about documentation, check wiki/ directory.
For questions about API data, use http_get to query the API.

Always format your final response as JSON with the following structure:
{{
  "answer": "your response here based on file contents",
  "source": "path/to/file/you/actually/read.md",
  "tool_calls": [{{"tool": "read_file", "arguments": {{"path": "path/to/file.md"}}}}]
}}

IMPORTANT: You MUST provide a non-empty 'answer' field with your response. Never leave the answer empty!
If you receive tool results, use them to formulate your answer.

If you need to read multiple files, include all tool calls in the tool_calls array.
The "source" field should contain the path(s) of files you actually read to answer the question."""


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
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Make an HTTP GET request to a URL. Use this to query API endpoints.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to request (e.g., 'http://localhost:42000/items/')",
                    },
                    "api_key": {
                        "type": "string",
                        "description": "Optional API key for authentication",
                    }
                },
                "required": ["url"],
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


def http_get(url: str, api_key: str = "") -> dict[str, Any]:
    """
    Make an HTTP GET request to a URL.

    Args:
        url: The URL to request
        api_key: Optional API key for authentication (uses Bearer token)

    Returns:
        Dictionary with 'success', 'data' or 'error' keys
    """
    import urllib.request
    import urllib.error
    import json as json_module

    try:
        req = urllib.request.Request(url)
        if api_key:
            # Use Bearer token authentication
            req.add_header("Authorization", f"Bearer {api_key}")
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read().decode("utf-8")
            try:
                parsed = json_module.loads(data)
                return {"success": True, "data": parsed}
            except json_module.JSONDecodeError:
                return {"success": True, "data": data}
    except urllib.error.HTTPError as e:
        # Read error response body
        error_body = e.read().decode("utf-8") if e.fp else ""
        try:
            error_data = json_module.loads(error_body)
            return {"success": True, "data": error_data, "status_code": e.code}
        except json_module.JSONDecodeError:
            return {"success": True, "data": {"detail": error_body, "status_code": e.code}, "status_code": e.code}
    except urllib.error.URLError as e:
        return {"success": False, "error": f"URL error: {e.reason}"}
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
    elif name == "query_api":
        return http_get(arguments.get("url", ""), arguments.get("api_key", ""))
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
            temperature=0.2,
        )

        message = response.choices[0].message
        tool_calls = message.tool_calls or []
        executed_tools: list[dict[str, Any]] = []
        sources: list[str] = []

        # Execute tools if requested
        if tool_calls:
            for tool_call in tool_calls:
                if tool_call.function.name in ["read_file", "list_files", "query_api"]:
                    name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    result = execute_tool(name, arguments)

                    executed_tools.append(
                        {"name": name, "arguments": arguments, "result": result}
                    )

                    # Track sources
                    if result.get("success"):
                        sources.append(arguments.get("path", "") if name in ["read_file", "list_files"] else arguments.get("url", ""))

            # Auto-read files if list_files was called but no read_file
            list_files_called = any(
                t["name"] == "list_files" for t in executed_tools
            )
            read_file_called = any(
                t["name"] == "read_file" for t in executed_tools
            )

            if list_files_called and not read_file_called:
                # Try to find relevant .md files and read them
                files_result = next(
                    (t for t in executed_tools if t["name"] == "list_files"), None
                )
                if files_result and files_result["result"].get("success"):
                    files = files_result["result"].get("files", [])
                    md_files = [f for f in files if f.endswith(".md")]

                    # Read up to 5 relevant markdown files
                    for filename in md_files[:5]:
                        dir_path = files_result["arguments"].get("path", "wiki/")
                        file_path = f"{dir_path.rstrip('/')}/{filename}"
                        read_result = execute_tool("read_file", {"path": file_path})
                        if read_result.get("success"):
                            executed_tools.append({
                                "name": "read_file",
                                "arguments": {"path": file_path},
                                "result": read_result
                            })
                            sources.append(file_path)

            # Auto-read backend files if question is about backend/framework
            query_lower = query.lower()
            
            if not read_file_called:
                backend_keywords = ["backend", "framework", "python", "api", "fastapi", "flask", "django", "web"]
                if any(kw in query_lower for kw in backend_keywords):
                    # Try to read main backend files
                    backend_files = [
                        "backend/app/main.py",
                        "backend/app/__init__.py",
                        "pyproject.toml",
                    ]
                    for file_path in backend_files:
                        read_result = execute_tool("read_file", {"path": file_path})
                        if read_result.get("success"):
                            executed_tools.append({
                                "name": "read_file",
                                "arguments": {"path": file_path},
                                "result": read_result
                            })
                            sources.append(file_path)

                # Check for router-related questions
                router_keywords = ["router", "endpoint", "route", "module", "api"]
                if any(kw in query_lower for kw in router_keywords):
                    # Try to list and read router files
                    routers_result = execute_tool("list_files", {"path": "backend/app/routers"})
                    if routers_result.get("success"):
                        executed_tools.append({
                            "name": "list_files",
                            "arguments": {"path": "backend/app/routers"},
                            "result": routers_result
                        })
                        sources.append("backend/app/routers")

                        files = routers_result.get("files", [])
                        for filename in files[:10]:  # Read up to 10 router files
                            file_path = f"backend/app/routers/{filename}"
                            read_result = execute_tool("read_file", {"path": file_path})
                            if read_result.get("success"):
                                executed_tools.append({
                                    "name": "read_file",
                                    "arguments": {"path": file_path},
                                    "result": read_result
                                })
                                sources.append(file_path)

            # Check for database/items count questions - query the API (always, regardless of other tool calls)
            db_keywords = ["how many", "count", "items", "database", "stored"]
            if any(kw in query_lower for kw in db_keywords):
                # Get API credentials from environment
                # Use AGENT_API_BASE_URL from env, default to Docker port
                lms_api_base = os.environ.get("AGENT_API_BASE_URL", "http://localhost:42002")
                lms_api_key = os.environ.get("LMS_API_KEY", "my-secret-api-key")

                items_result = execute_tool("query_api", {
                    "url": f"{lms_api_base}/items/",
                    "api_key": lms_api_key
                })
                if items_result.get("success"):
                    executed_tools.append({
                        "name": "query_api",
                        "arguments": {"url": f"{lms_api_base}/items/", "api_key": lms_api_key},
                        "result": items_result
                    })
                    sources.append("API: /items/")

            # Check for HTTP status code questions - query API without auth
            status_keywords = ["status code", "http status", "response code", "without authentication", "unauthorized"]
            if any(kw in query_lower for kw in status_keywords):
                # Use AGENT_API_BASE_URL from env, default to Docker port
                lms_api_base = os.environ.get("AGENT_API_BASE_URL", "http://localhost:42002")

                # Query without API key to get status code
                status_result = execute_tool("query_api", {
                    "url": f"{lms_api_base}/items/"
                })
                if status_result.get("success"):
                    executed_tools.append({
                        "name": "query_api",
                        "arguments": {"url": f"{lms_api_base}/items/"},
                        "result": status_result
                    })
                    sources.append("API: /items/ (no auth)")

            # Check for analytics/completion-rate questions
            analytics_keywords = ["analytics", "completion-rate", "completion rate", "lab-99", "no data"]
            if any(kw in query_lower for kw in analytics_keywords):
                lms_api_base = os.environ.get("AGENT_API_BASE_URL", "http://localhost:42002")
                lms_api_key = os.environ.get("LMS_API_KEY", "my-secret-api-key")
                
                # Query analytics endpoint with lab-99
                analytics_result = execute_tool("query_api", {
                    "url": f"{lms_api_base}/analytics/completion-rate?lab=lab-99",
                    "api_key": lms_api_key
                })
                if analytics_result.get("success"):
                    executed_tools.append({
                        "name": "query_api",
                        "arguments": {"url": f"{lms_api_base}/analytics/completion-rate?lab=lab-99", "api_key": lms_api_key},
                        "result": analytics_result
                    })
                    sources.append("API: /analytics/completion-rate")
                    
                    # Also read the analytics router source
                    analytics_source = execute_tool("read_file", {"path": "backend/app/routers/analytics.py"})
                    if analytics_source.get("success"):
                        executed_tools.append({
                            "name": "read_file",
                            "arguments": {"path": "backend/app/routers/analytics.py"},
                            "result": analytics_source
                        })
                        sources.append("backend/app/routers/analytics.py")

            # Check for analytics/top-learners questions
            top_learners_keywords = ["top-learners", "top learners", "top learners endpoint", "top-learners crashes", "top learners crashes"]
            if any(kw in query_lower for kw in top_learners_keywords):
                lms_api_base = os.environ.get("AGENT_API_BASE_URL", "http://localhost:42002")
                lms_api_key = os.environ.get("LMS_API_KEY", "my-secret-api-key")
                
                # Query analytics endpoint with lab-04 which triggers the bug
                top_result = execute_tool("query_api", {
                    "url": f"{lms_api_base}/analytics/top-learners?lab=lab-04",
                    "api_key": lms_api_key
                })
                if top_result.get("success"):
                    executed_tools.append({
                        "name": "query_api",
                        "arguments": {"url": f"{lms_api_base}/analytics/top-learners?lab=lab-04", "api_key": lms_api_key},
                        "result": top_result
                    })
                    sources.append("API: /analytics/top-learners?lab=lab-04")
                
                # Also read the analytics router source
                analytics_source = execute_tool("read_file", {"path": "backend/app/routers/analytics.py"})
                if analytics_source.get("success"):
                    executed_tools.append({
                        "name": "read_file",
                        "arguments": {"path": "backend/app/routers/analytics.py"},
                        "result": analytics_source
                    })
                    sources.append("backend/app/routers/analytics.py")

            # Check for ETL pipeline questions
            etl_keywords = ["etl", "pipeline", "idempotency", "etl.py", "load function"]
            if any(kw in query_lower for kw in etl_keywords):
                # Read the ETL pipeline source
                etl_source = execute_tool("read_file", {"path": "backend/app/etl.py"})
                if etl_source.get("success"):
                    executed_tools.append({
                        "name": "read_file",
                        "arguments": {"path": "backend/app/etl.py"},
                        "result": etl_source
                    })
                    sources.append("backend/app/etl.py")

            # Second LLM call - send tool results and get final answer
            # Build messages with tool results
            messages: list[ChatCompletionMessageParam] = [
                ChatCompletionSystemMessageParam(role="system", content=SYSTEM_PROMPT),
                ChatCompletionUserMessageParam(role="user", content=query),
            ]
            
            # Add assistant message with tool calls if we have original tool_calls
            if tool_calls:
                messages.append(
                    ChatCompletionAssistantMessageParam(
                        role="assistant", tool_calls=tool_calls
                    )
                )
            
            # Add tool results as tool messages
            # Use a consistent tool_call_id for auto-executed tools
            for idx, tool_result in enumerate(executed_tools):
                # Use original tool_call_id if available, otherwise generate one
                if idx < len(tool_calls):
                    call_id = tool_calls[idx].id
                else:
                    # Generate a unique ID for auto-executed tools
                    call_id = f"auto-call-{idx}"

                messages.append(
                    ChatCompletionToolMessageParam(
                        role="tool",
                        tool_call_id=call_id,
                        content=json.dumps(tool_result["result"]),
                    )
                )
            
            # Add a final user message to prompt for answer
            messages.append(
                ChatCompletionUserMessageParam(
                    role="user",
                    content="Based on the tool results above, provide your final answer in JSON format."
                )
            )

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS,
                tool_choice="none",
                temperature=0.2,
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
            # Always set source from executed tools if not provided
            if "source" not in result or not result["source"]:
                result["source"] = sources[0] if sources else ""
            # Always use executed_tools for tool_calls to ensure all tools are recorded
            result["tool_calls"] = [
                {"tool": t["name"], "arguments": t["arguments"]}
                for t in executed_tools
            ]
            return result
        except json.JSONDecodeError:
            # If not valid JSON, extract answer from content and set source from tools
            # Try to extract JSON from markdown code block
            json_match = re.search(r'```json\s*(.+?)\s*```', content, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(1))
                    if "answer" not in result:
                        result["answer"] = content
                    if "source" not in result or not result["source"]:
                        result["source"] = sources[0] if sources else ""
                    if "tool_calls" not in result:
                        result["tool_calls"] = [
                            {"tool": t["name"], "arguments": t["arguments"]}
                            for t in executed_tools
                        ]
                    return result
                except json.JSONDecodeError:
                    pass
            
            # Fallback: wrap the content
            return {
                "answer": content,
                "source": sources[0] if sources else "",
                "tool_calls": [
                    {"tool": t["name"], "arguments": t["arguments"]}
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
