# Model Provider Decision and API Credential Setup

This document records the design decision for the model provider in `agent-tui` and details the assumptions and configurations required for the V1 API integration.

## V1 Provider Selection Decision

For V1, the model provider implementation is **deferred to a default OpenAI-compatible adapter**.

Rather than locking the agent into a single proprietary SDK or cloud provider, we implement a standard OpenAI-compatible client interface. This decision provides maximum flexibility:
1. **Direct Compatibility**: Works out-of-the-box with OpenAI's official APIs (e.g. `gpt-4o`, `gpt-4-turbo`).
2. **Local Development / Offline Use**: Seamlessly integrates with local runner engines like Ollama, LocalAI, LM Studio, or vLLM.
3. **Alternative Cloud Providers**: Directly supports alternative endpoints offering the OpenAI schema, such as Groq, Together AI, Anyscale, OpenRouter, and Mistral AI.
4. **Future Extensibility**: By standardizing on the `/chat/completions` API structure, we establish a clean baseline adapter. Specialized adapters for Anthropic (Claude) or Google (Gemini) can be added as distinct modules later if native API features are required.

---

## API Credential Setup & Configuration

The agent loads credentials and configuration using Pydantic Settings from the environment or a `.env` file in the root workspace directory.

### Configuration Fields

| Variable Name | Type | Default | Description |
|---|---|---|---|
| `API_KEY` | String | *Required* | API key for the model provider. Set to any non-empty string for local-only servers (e.g. Ollama). |
| `BASE_URL` | String | `https://api.openai.com/v1` | Base URL of the API endpoint. Overridden for local/alternative providers. |
| `MODEL` | String | *Required* | Model identifier/name to request (e.g. `gpt-4o`, `llama3`). |
| `WORKSPACE` | Path/String | `.` (Current Dir) | Root directory where agent tool operations are isolated. |
| `PROVIDER` | String | `openai` | Name of the provider adapter class to use. |

### Setup Examples

#### 1. Official OpenAI Service
Create a `.env` file in the project root:
```ini
API_KEY=sk-proj-abc123xyz...
MODEL=gpt-4o
BASE_URL=https://api.openai.com/v1
PROVIDER=openai
```

#### 2. Local Ollama Server
Ensure Ollama is running (`ollama run llama3`), then configure:
```ini
API_KEY=ollama  # Any non-empty string is required by the config validator
MODEL=llama3
BASE_URL=http://localhost:11434/v1
PROVIDER=openai
```

#### 3. Groq API
Generate a key from the Groq console, then configure:
```ini
API_KEY=gsk_abc...
MODEL=llama3-70b-8192
BASE_URL=https://api.groq.com/openai/v1
PROVIDER=openai
```

---

## Model API Adapter Assumptions

Before implementing live API calls, the following provider-specific protocol assumptions are established:

### 1. Endpoint Path Suffix
The client will append `/chat/completions` to the configured `base_url`. For example:
- Configured: `https://api.openai.com/v1` -> Final URL: `https://api.openai.com/v1/chat/completions`
- Configured: `http://localhost:11434/v1` -> Final URL: `http://localhost:11434/v1/chat/completions`

### 2. Request Headers
All API calls will use async HTTP POST requests with headers:
- `Authorization: Bearer {API_KEY}` (Note: Local providers may ignore this but the header must still be sent).
- `Content-Type: application/json`

### 3. Request Payload Shape
The JSON payload will structure parameters compatible with the OpenAI API:
```json
{
  "model": "gpt-4o",
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful coding assistant..."
    },
    {
      "role": "user",
      "content": "Hello!"
    }
  ],
  "tools": [],
  "tool_choice": "auto",
  "stream": false
}
```

### 4. Response Parsing (Non-Streaming)
A successful response returns status code `200 OK` and a JSON response body.
The client expects the following format to extract the completion response:
- **Assistant Message Content**: Extracted from `choices[0].message.content`.
- **Tool Calls**: Extracted from `choices[0].message.tool_calls`, where each item is an object with:
  - `id` (string): Unique identifier for the tool run.
  - `type` (string): Expected to be `"function"`.
  - `function` (object): Contains `name` (string) and `arguments` (JSON-formatted string).

### 5. Response Parsing (Streaming)
When `stream: true`, the API returns a `text/event-stream`. The client will parse chunks prefixed with `data: `:
- Each chunk contains a delta: `choices[0].delta` with partial `content` or `tool_calls`.
- The stream terminates when a chunk containing `[DONE]` is received or when the stream closes.
