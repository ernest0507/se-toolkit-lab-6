# Agent Documentation

## Overview

This is a documentation-powered LLM agent for SE Toolkit Lab 6, Task 2 (extended for Task 3). The agent can:
- Read project files (wiki documentation, source code)
- List directory contents
- Query the running LMS API for live data

The agent uses an agentic loop with function calling to interact with tools and answer questions about both project documentation and current system state.

## LLM Provider

### Configuration

The agent uses an **OpenAI-compatible API** endpoint. By default, it is configured to use **Qwen** as the LLM provider.

### Environment Variables

Configure the agent by creating a `.env.agent.secret` file (copy from `.env.agent.example`):

```bash
# Your LLM provider API key
LLM_API_KEY=your-api-key-here


# API base URL (OpenAI-compatible endpoint)
LLM_API_BASE=http://10.93.24.243:42005/v1

# Model name
LLM_MODEL=qwen3-coder-plus
```

### Model

The default model is `qwen3-coder-plus`, which provides strong coding and reasoning capabilities with function calling support.

## Tools

The agent has access to three tools:

### 1. `read_file`

**Purpose**: Read the contents of a file from the project directory.

**Parameters**:
- `path` (string, required): Relative path to the file (e.g., `wiki/git.md`)

**Returns**:
```json
{
  "success": true,
  "content": "file contents here"
}
```

Or on error:
```json
{
  "success": false,
  "error": "error message"
}
```

### 2. `list_files`

**Purpose**: List files in a directory within the project.

**Parameters**:
- `path` (string, required): Relative path to the directory (e.g., `wiki/`)

**Returns**:
```json
{
  "success": true,
  "files": ["file1.md", "file2.md", ...]
}
```

Or on error:
```json
{
  "success": false,
  "error": "error message"
}
```

### 3. `query_api` (Task 3)

**Purpose**: Make an HTTP GET request to query the LMS API endpoints for live data.

**Parameters**:
- `url` (string, required): The URL to request (e.g., `http://localhost:42001/items/`)
- `api_key` (string, optional): API key for authentication (uses Bearer token)

**Returns**:
```json
{
  "success": true,
  "data": { ... }  // JSON response from API
}
```

Or on error:
```json
{
  "success": false,
  "error": "error message"
}
```

**Authentication**: The tool automatically adds `Authorization: Bearer <api_key>` header when an API key is provided.

## Agentic Loop

The agent follows a two-phase agentic loop:

### Phase 1: Initial Query

1. User provides a query via command line
2. Agent calls LLM with:
   - System prompt (defines role and tools)
   - User query
   - Available tool schemas
3. LLM responds with either:
   - Direct answer (no tools needed)
   - Tool calls to execute

### Phase 2: Tool Execution and Final Answer

If LLM requests tool calls:

1. Agent executes each requested tool
2. Tool results are collected
3. Agent sends tool results back to LLM
4. LLM generates final answer based on tool results
5. Agent outputs JSON response

### Flow Diagram

```
User Query
    │
    ▼
┌─────────────────────────┐
│  LLM Call (with tools)  │
└─────────────────────────┘
    │
    ├─── No tool calls ───► Return Answer
    │
    ▼
Tool Calls Requested
    │
    ▼
┌─────────────────────────┐
│   Execute Tools         │
│   - read_file           │
│   - list_files          │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  LLM Call (with results)│
└─────────────────────────┘
    │
    ▼
Return Final Answer
```

## System Prompt Strategy

The system prompt is designed to:

1. **Define the agent's role**: Documentation assistant for the SE Toolkit project
2. **List available tools**: Describe `read_file` and `list_files` and when to use them
3. **Guide behavior**: Instruct the agent to read files before answering
4. **Specify output format**: Require JSON with `answer`, `source`, and `tool_calls` fields

### Key Prompt Elements

```
You are a documentation assistant for the SE Toolkit Lab 6 project.
Your role is to answer questions about the project documentation by reading files from the wiki directory.

You have access to the following tools:
1. read_file(path: str) - Read the contents of a file
2. list_files(path: str) - List files in a directory

When answering questions:
1. First, determine which files might contain the answer
2. Use read_file to read relevant documentation files
3. Use list_files to explore directories if needed
4. Provide a concise answer based on the file contents
```

## Output Format

The agent outputs JSON to stdout with three fields:

```json
{
  "answer": "The agent's response to the user's query",
  "source": "wiki/git.md",
  "tool_calls": [
    {"name": "read_file", "arguments": {"path": "wiki/git.md"}}
  ]
}
```

### Field Descriptions

- **`answer`**: The agent's final response to the query
- **`source`**: Path to the file(s) used to answer the question
- **`tool_calls`**: Array of tool calls made during execution

## Path Security

To prevent directory traversal attacks, the agent validates all file paths:

1. **Resolve to absolute path**: Convert relative path using project root
2. **Check prefix**: Ensure resolved path starts with project root
3. **Reject `..` segments**: Block paths that could escape project directory
4. **Verify existence**: Check file/directory exists before access

### Security Implementation

```python
def is_safe_path(requested_path: str) -> bool:
    resolved = (PROJECT_ROOT / requested_path).resolve()
    return str(resolved).startswith(str(PROJECT_ROOT.resolve()))
```

## Tool Selection Strategy (Task 3)

The LLM decides which tools to use based on the question type:

### Wiki/Documentation Questions
- **Keywords**: "wiki", "documentation", "how to", "what is", "explain"
- **Tools**: `read_file`, `list_files`
- **Example**: "What files are in the wiki directory?"

### Source Code Questions
- **Keywords**: "backend", "frontend", "source code", "framework", "router", "endpoint"
- **Tools**: `read_file`, `list_files` (targeting `backend/`, `frontend/` directories)
- **Example**: "What Python web framework does the backend use?"

### Live Data Questions
- **Keywords**: "how many", "count", "items", "database", "status code", "analytics"
- **Tools**: `query_api` (often combined with `read_file` for source analysis)
- **Example**: "How many items are currently stored in the database?"

### Auto-Execution Strategy

The agent implements keyword-based auto-execution to ensure relevant tools are called even if the LLM doesn't request them initially:

1. **Backend keywords** → Auto-read `backend/app/main.py`, `pyproject.toml`
2. **Router keywords** → Auto-list and read `backend/app/routers/`
3. **Database/items keywords** → Auto-query `/items/` endpoint
4. **Analytics keywords** → Auto-query analytics endpoints and read `analytics.py`
5. **ETL keywords** → Auto-read `backend/app/etl.py`

## Lessons Learned from Benchmark

### Initial Challenges

1. **LLM Not Calling Tools**: The model would mention file names without actually reading them.
   - **Solution**: Added explicit instructions in system prompt and auto-execution based on keywords.

2. **Wrong API Port**: Initially used port 42000, but Docker runs API on 42001.
   - **Solution**: Updated hardcoded port to match Docker configuration.

3. **Authentication Issues**: Used `X-API-Key` header instead of Bearer token.
   - **Solution**: Changed to `Authorization: Bearer <key>` format.

4. **Empty Answers**: LLM would return empty answers after receiving tool results.
   - **Solution**: Added explicit user message prompting for JSON answer after tool results.

5. **Tool Call Overwrite**: LLM would overwrite auto-executed tool calls in final JSON.
   - **Solution**: Always use `executed_tools` for final `tool_calls` field.

### Key Insights

- **Lower temperature (0.2)** produces more consistent tool usage
- **Explicit instructions** in system prompt are crucial
- **Auto-execution fallback** ensures tools are called even if LLM hesitates
- **Error handling** in `query_api` must capture full HTTP error body for debugging

## Final Evaluation Score

**Local Benchmark: 10/10 PASSED**

All 10 local questions pass successfully:
1. ✅ GitHub branch protection (wiki)
2. ✅ SSH connection steps (wiki)
3. ✅ Backend framework (source code)
4. ✅ API router modules (source code)
5. ✅ Items count in database (API query)
6. ✅ HTTP status code without auth (API query)
7. ✅ Completion-rate error analysis (API + source)
8. ✅ Top-learners crash analysis (API + source)
9. ✅ Docker request journey (docker-compose.yml)
10. ✅ ETL idempotency (etl.py)

**Note**: The autochecker bot tests 10 additional hidden questions with LLM-based judging. The final grade depends on passing both local and hidden questions with a minimum overall threshold.

## How to Run

### Prerequisites

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Configure environment variables:
   ```bash
   cp .env.agent.example .env.agent.secret
   # Edit .env.agent.secret with your LLM credentials
   ```

### Running the Agent

```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac

# Run with a query
python agent.py "How do you resolve a merge conflict?"

# Example: List wiki files
python agent.py "What files are in the wiki directory?"
```

### Example Output

```json
{
  "answer": "To resolve a merge conflict, follow these steps: 1) Identify conflicting files, 2) Open files and locate conflict markers, 3) Edit to resolve conflicts, 4) Stage resolved files, 5) Complete the merge with commit.",
  "source": "wiki/git-workflow.md",
  "tool_calls": [
    {"name": "read_file", "arguments": {"path": "wiki/git-workflow.md"}}
  ]
}
```

## Testing

Run the regression tests:

```bash
pytest test_agent.py -v
```

Tests verify:
- JSON output contains required fields (`answer`, `source`, `tool_calls`)
- Tool calls are executed correctly
- Path security prevents directory traversal
