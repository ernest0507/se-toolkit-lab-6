# Agent Documentation

## Overview

This is a basic LLM-powered agent for SE Toolkit Lab 6. The agent accepts user queries and returns JSON responses containing an answer and a list of tool calls.

## LLM Provider

### Configuration

The agent uses an **OpenAI-compatible API** endpoint. By default, it is configured to use **Qwen** as the LLM provider.

### Environment Variables

Configure the agent by creating a `.env.agent.secret` file (copy from `.env.agent.example`):

```bash
# Your LLM provider API key
LLM_API_KEY=your-api-key-here

# API base URL (OpenAI-compatible endpoint)
LLM_API_BASE=http://<your-vm-ip>:<qwen-api-port>/v1

# Model name
LLM_MODEL=qwen3-coder-plus
```

### Model

The default model is `qwen3-coder-plus`, which provides strong coding and reasoning capabilities.

## How It Works

### Architecture

```
User Query → agent.py → LLM API → JSON Response → stdout
```

### Components

1. **System Prompt**: Defines the agent's behavior and response format
2. **LLM Client**: OpenAI-compatible client using the `openai` Python library
3. **Main Function**: Handles command-line input and outputs JSON to stdout

### Output Format

The agent outputs JSON to stdout:

```json
{
  "answer": "The agent's response to the user's query",
  "tool_calls": []
}
```

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

Run the agent with a query as command-line arguments:

```bash
# Activate virtual environment first
source .venv/bin/activate  # On Linux/Mac
# or on Windows:
.venv\Scripts\activate

# Run with a query
python agent.py "What is the capital of France?"
```

### Example Output

```json
{"answer": "The capital of France is Paris.", "tool_calls": []}
```

## Future Extensions

This minimal implementation will be extended in later tasks with:
- Actual tool definitions and execution
- Domain-specific knowledge for the LMS
- More sophisticated prompting strategies
- Integration with the LMS backend API
