# Plan: Task 2 - Tools and Agentic Loop

## Tool Schemas

I will define two tools as function-calling schemas for the LLM:

### 1. `read_file`

**Purpose**: Read the contents of a file from the project.

**Schema**:
```json
{
  "name": "read_file",
  "description": "Read the contents of a file from the project directory",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Relative path to the file (e.g., 'wiki/git.md')"
      }
    },
    "required": ["path"]
  }
}
```

### 2. `list_files`

**Purpose**: List files in a directory.

**Schema**:
```json
{
  "name": "list_files",
  "description": "List files in a directory within the project",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Relative path to the directory (e.g., 'wiki/')"
      }
    },
    "required": ["path"]
  }
}
```

## Agentic Loop Implementation

The agent will follow this loop:

1. **Receive user query** from command line
2. **Call LLM** with system prompt, tools, and user query
3. **Parse response**:
   - If LLM requests tool calls → execute tools, collect results
   - If LLM provides final answer → return JSON
4. **Execute tools** (if any):
   - Call `read_file` or `list_files` with provided arguments
   - Store tool results
5. **Second LLM call** (if tools were executed):
   - Send tool results back to LLM
   - Get final answer
6. **Output JSON** with `answer`, `source`, and `tool_calls` fields

### Flow Diagram

```
User Query → LLM (with tools) → Tool Calls?
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                   No                              Yes
                    │                               │
                    ▼                               ▼
            Return Answer                    Execute Tools
                    │                               │
                    │                               ▼
                    │                       Collect Results
                    │                               │
                    │                               ▼
                    └───────────────←───────────────┘
                                    │
                                    ▼
                            LLM (with tool results)
                                    │
                                    ▼
                            Return Final Answer
```

## Path Security

To prevent directory traversal attacks, I will implement path validation:

### Security Measures

1. **Resolve to absolute path**: Convert relative path to absolute using project root
2. **Check prefix**: Ensure resolved path starts with project root
3. **Reject `..` segments**: Block paths containing `..` that could escape project directory
4. **File existence check**: Verify file exists before reading

### Implementation

```python
def is_safe_path(project_root: Path, requested_path: str) -> bool:
    """Check if the requested path is within the project directory."""
    # Resolve to absolute path
    resolved = (project_root / requested_path).resolve()
    # Check it's within project root
    return str(resolved).startswith(str(project_root.resolve()))
```

## Output Format

The agent will output JSON with three fields:

```json
{
  "answer": "The agent's response to the user's query",
  "source": "Path to the file(s) used as source (e.g., 'wiki/git.md')",
  "tool_calls": [
    {"name": "read_file", "arguments": {"path": "wiki/git.md"}}
  ]
}
```

## System Prompt Strategy

The system prompt will:
1. Define the agent's role as a documentation assistant
2. List available tools and their purposes
3. Instruct to always use tools when answering questions about project files
4. Specify the required JSON output format
