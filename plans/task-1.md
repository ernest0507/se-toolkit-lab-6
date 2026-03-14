# Plan: Task 1 - Basic Agent Implementation

## LLM Provider and Model

### Provider: Qwen (OpenAI-compatible API)

I will use Qwen as the LLM provider via an OpenAI-compatible API endpoint. This allows using the standard `openai` Python client library for simplicity.

### Model: `qwen3-coder-plus`

This model provides strong coding and reasoning capabilities suitable for an agent that needs to:
- Understand user queries
- Make tool calls when necessary
- Provide coherent answers

### Configuration

The agent will be configured via environment variables (`.env.agent.secret`):
- `LLM_API_KEY` - secret-api
- `LLM_API_BASE` - http://10.93.24.243:42005/v1
- `LLM_MODEL` - qwen3-coder-plus


## Agent Structure

### Architecture

The agent will follow a simple request-response pattern:

```
User Query → Agent → LLM → Parse Response → JSON Output
```

### Components

1. **System Prompt**: Minimal prompt defining the agent's behavior
   - Instructs the agent to respond with JSON
   - Defines the structure: `{"answer": "...", "tool_calls": [...]}`

2. **LLM Client**: OpenAI-compatible client
   - Uses `openai` Python library
   - Connects to configurable endpoint

3. **Main Function**:
   - Accepts user query via command line argument
   - Calls LLM with system prompt + user query
   - Parses and outputs JSON to stdout

### Output Format

The agent will output JSON to stdout:
```json
{
  "answer": "The agent's response to the user's query",
  "tool_calls": []
}
```

### Future Extensions

This minimal implementation will be extended in later tasks with:
- Actual tool definitions and execution
- Domain-specific knowledge
- More sophisticated prompting
- Tool integration with the LMS backend
