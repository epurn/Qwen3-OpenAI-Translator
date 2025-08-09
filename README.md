# Qwen3ToolCallTranslator

Enables Agent mode for Qwen3 in Continue.dev!

## Description
Qwen3ToolCallTranslator is a tool for translating Qwen3 model tool calls.

## Features
- Tool call translation from Qwen3 XML format to OpenAI-compatible JSON
- **Streaming support** for real-time tool call processing
- Compatible with Continue.dev agent mode

## Installation
To install this project perform the following steps:
1. Clone the repo
2. Add your api key and provider base url to a .env file in the root directory as follows:
- API_KEY=<your_key>
- QWEN_BASE_URL=<provider_base_url>
3. Add the following block to the config.yaml file in your .continue folder:
```
  - name: Qwen 3 Coder Agent
    provider: openrouter
    model: <MODEL_ID>
    apiBase: http://<TRANSLATOR_HOST>:<TRANSLATOR_PORT>/v1
    defaultCompletionOptions:
      contextLength: 262144
      stream: true
    capabilities:
      - tool_use
    roles:
      - apply
      - chat
      - edit
```

## Usage
From the base directory, run:
```
uvicorn app.server:app
```
The server runs on http://localhost:8000 by default, this can be modified with uvicorn commands. E.g:
```
uvicorn app.server:app --host <your_host> --port <your_port>
```

For streaming support, make sure to set `stream: true` in your configuration as shown above.

## API Endpoints
- `/v1/chat/completions` - OpenAI-compatible endpoint for non-streaming requests, streaming requests are forwarded to `/v1/chat/completions/stream`
- `/v1/chat/completions/stream` - OpenAI-compatible endpoint for streaming requests
- `/translate` - Direct XML to OpenAI translation endpoint

## Future work
I am hoping Continue will release a version that supports XML based tool calling soon, but in the meantime I will be updating this project. The next updates are:
- Add tests
- Recommend stuff to add and I'll add it asap 😊

## License
This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.
