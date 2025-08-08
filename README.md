# Qwen3ToolCallTranslator

Enables Agent mode for Qwen3 in Continue.dev!

## Description
Qwen3ToolCallTranslator is a tool for translating Qwen3 model tool calls.

## Installation
To install this project perform the following steps:
1. Clone the repo
2. Add your openrouter api key to a .env file in the root directory as follows:
    OPENROUTER_API_KEY=<your_key>
3. Add the following block to the config.yaml file in your .continue folder:
```
  - name: TEST - Qwen 3 Coder Agent
    provider: openrouter
    model: qwen/qwen3-coder
    apiBase: http://localhost:8000/v1
    defaultCompletionOptions:
      contextLength: 262144
      stream: false
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
Currently the server runs on http://localhost:8000, this will be changed in a future version or easily changed by you!

## Future work
I am hoping Continue will release a version that supports XML based tool calling soon, but in the meantime I will be updating this project. The next updates are:
- Allow dynamic qwen provider - currently hardcoded to openrouter
- Allow different hostname/port - currently hardcoded to http://localhost:8000
- ADD STREAMING SUPPORT
- Add tests
- Recommend stuff to add and I'll add it asap 😊

## License
This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.
