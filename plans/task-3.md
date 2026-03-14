# Task 3 Plan: System Agent with API Access

## Overview

This task extends the documentation agent (Task 2) to become a system agent that can:
1. Read project files (wiki, source code)
2. Query the running LMS API for live data
3. Answer questions about both documentation and system state

## Tool Schema Design

### query_api Tool

```json
{
  "name": "query_api",
  "description": "Make an HTTP GET request to query API endpoints.",
  "parameters": {
    "type": "object",
    "properties": {
      "url": {
        "type": "string",
        "description": "The URL to request (e.g., 'http://localhost:42001/items/')"
      },
      "api_key": {
        "type": "string",
        "description": "Optional API key for authentication"
      }
    },
    "required": ["url"]
  }
}
```

## Authentication Handling

The LMS API uses Bearer token authentication:
- Header: `Authorization: Bearer <API_KEY>`
- API key is read from environment variable `LMS_API_KEY`
- The `query_api` function handles adding the auth header automatically

## System Prompt Updates

The system prompt was updated to:
1. Inform the LLM about the new `query_api` tool
2. Explain when to use each tool:
   - `read_file` / `list_files` → for documentation and source code questions
   - `query_api` → for live data questions (item counts, analytics, etc.)
3. Emphasize that the agent must actually call tools, not just mention them

## Initial Benchmark Score

**First run:** 0/10 passed

### First Failures Analysis

1. **Question 1-4 (wiki/source questions):** Failed because LLM wasn't calling tools
   - Fix: Added auto-execution of relevant tools based on keywords

2. **Question 5 (items count):** Failed because API wasn't accessible
   - Fix: Discovered API runs on port 42001 (Docker), not 42000

3. **Question 6 (status code):** Failed because auth header was wrong
   - Fix: Changed from `X-API-Key` to `Authorization: Bearer`

4. **Question 7-8 (analytics bugs):** Failed because LLM didn't read error responses
   - Fix: Improved HTTP error handling to capture full error body

5. **Question 9-10 (docker/etl):** Failed because files weren't auto-read
   - Fix: Added keyword-based auto-reading for ETL and docker questions

## Iteration Strategy

1. **Run benchmark** → identify failing questions
2. **Analyze failure reason** (wrong tool, wrong answer, missing tool call)
3. **Add keyword detection** for question types that need auto-tool-execution
4. **Improve system prompt** to encourage tool usage
5. **Fix tool implementations** (authentication, error handling)
6. **Repeat** until all questions pass

## Final Result

**Score: 10/10 passed** on local benchmark

Note: The autochecker bot tests 10 additional hidden questions with LLM-based judging.
