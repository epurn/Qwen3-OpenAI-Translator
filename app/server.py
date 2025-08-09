import json
import logging
import time
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Optional, Set
from app.state import get_last_edit_text
from app.streaming_parser import QwenStreamingParser
from app.translator import translate_xml_to_openai
from app.schema import AssistantMessage, ChatCompletionRequest, ChatCompletionResponse, Choice, CompletionChoice, CompletionRequest, CompletionResponse, FunctionCall, ToolCall, TranslatedResponse, TranslationRequest, UsageStats
from dotenv import load_dotenv
import httpx
import os

# Set up logging
logger = logging.getLogger(__name__)
# Create module logger
logger.debug("logger initialized with DEBUG level")

load_dotenv()
app = FastAPI()

# Add this line at the top (env var or hardcoded)
API_KEY = os.getenv("API_KEY")
QWEN_BASE_URL = os.getenv("QWEN_BASE_URL")


# ----- Simple health + debug -----

@app.post("/translate", response_model=TranslatedResponse)
async def translate(request: TranslationRequest):
    logger.debug(f"Translation request: {request.xml}")
    response = translate_xml_to_openai(request.xml)
    logger.debug(f"Translation response: {response}")
    return response

@app.post("/health")
async def health():
    logger.info("Health check endpoint called")
    return {"status": "ok"}


# ----- OpenAI-compatible endpoint -----

@app.post("/v1/completions")
async def legacy_completions(request: CompletionRequest):
    """
    Minimal /v1/completions shim for Continue's edit diff streamer.
    DO NOT send an empty 'text' chunk—doing so wipes the file.
    We emit no data chunks and only [DONE], so Continue falls back
    to the tool call's provided 'text' for applying the edit.
    """
    created = int(time.time())
    if request.stream:
        async def event_stream():
            # single chunk with the full replacement text, then [DONE]
            chunk = {
                "id": "cmp-apply",
                "object": "text_completion",
                "created": created,
                "model": request.model,
                "choices": [{"index": 0, "text": get_last_edit_text(), "finish_reason": None}],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(event_stream(), media_type="text/event-stream")

    # Non-stream fallback: return a harmless whitespace token (not empty)
    return JSONResponse({
        "id": "cmp-legacy",
        "object": "text_completion",
        "created": created,
        "model": request.model,
        "choices": [{"index": 0, "text": " ", "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 1, "total_tokens": 1},
    })

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def openai_compatible(request: ChatCompletionRequest):
    logger.debug(f"Request stream: {request.stream}")
    
    request_payload = request.model_dump(exclude_none=True)

    if request.stream:
        return await stream_chat(request)

    async with httpx.AsyncClient(timeout=60.0) as client:
        openrouter_response = await client.post(
            f"{QWEN_BASE_URL}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json=request_payload,
        )

    if not openrouter_response.is_success:
        logger.error(f"OpenRouter error: {openrouter_response.text}")
        return {
            "error": "OpenRouter call failed",
            "status_code": openrouter_response.status_code,
            "body": openrouter_response.text,
        }

    raw_data = openrouter_response.json()
    logger.debug(f"Raw data from OpenRouter: {raw_data}")
    raw_response = raw_data["choices"][0]["message"]["content"]

    logger.debug("Raw OpenRouter message: %s", raw_data["choices"][0]["message"])
    translated = translate_xml_to_openai(raw_response, tools=request.tools)
    if not translated.tool_calls:
        openai_tool_calls = raw_data["choices"][0]["message"].get("tool_calls")
        if openai_tool_calls:
            tool_calls_list = [ToolCall(**call) for call in openai_tool_calls]
            translated = TranslatedResponse(tool_calls=tool_calls_list, content=raw_response)
    if not translated.content:
        translated.content = raw_response

    tool_calls_list: Optional[List[ToolCall]] = None
    if translated.tool_calls:
        tool_calls_list = [
            ToolCall(
                id=f"call_{i}",
                type=call.type,
                function=FunctionCall(
                    name=call.function.name,
                    arguments=call.function.arguments
                )
            )
            for i, call in enumerate(translated.tool_calls)
        ]

    message_payload = AssistantMessage(
        role="assistant",
        content=translated.content or "",
        tool_calls=tool_calls_list
    )

    response_payload = ChatCompletionResponse(
        id=raw_data["id"],
        object="chat.completion",
        created=raw_data.get("created", 0),
        model=request.model,
        choices=[
            Choice(
                index=0,
                message=message_payload,
                finish_reason="tool_calls" if translated.tool_calls else "stop"
            )
        ],
        usage=UsageStats(**raw_data.get("usage", {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }))
    )

    final_payload = response_payload.model_dump(exclude_none=True)
    logger.debug(f"Final response payload: {final_payload}")
    logger.debug("Final tool calls: %s", tool_calls_list)
    return final_payload


@app.post("/v1/chat/completions/stream")
async def stream_chat(request: ChatCompletionRequest):
    if not request.stream:
        raise ValueError("Set stream=true to use this endpoint.")

    logger.info(f"Streaming request received for model={request.model}")
    logger.debug(f"Messages: {request.messages}")
    logger.debug(f"Tools: {request.tools}")
    logger.debug(f"Tool choice: {request.tool_choice}")

    parser = QwenStreamingParser()
    
    preferred: Set[str] = {t["function"]["name"] for t in (request.tools or []) if t.get("type") == "function"}
    parser = QwenStreamingParser(preferred_names=preferred)

    async def event_stream():
        accumulated = ""
        previous = ""

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{QWEN_BASE_URL}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                },
                json=request.model_dump(exclude_none=True),
            ) as response:
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue

                    if line.strip() == "data: [DONE]":
                        logger.info("Received [DONE] from upstream.")
                        yield "data: [DONE]\n\n"
                        break

                    try:
                        payload = json.loads(line[6:])
                        delta_text = payload["choices"][0]["delta"].get("content", "")
                        # logger.debug(f"Delta text received: {delta_text!r}")

                        current = accumulated + delta_text
                        delta = parser.extract_stream_delta(previous, current, delta_text)

                        if delta:
                            # logger.debug(f"Tool call delta emitted: {json.dumps(delta)}")
                            chunk = {
                                "id": payload.get("id", "stream-id"),
                                "object": "chat.completion.chunk",
                                "created": payload.get("created", 0),
                                "model": request.model,
                                "choices": [{
                                    "index": 0,
                                    "delta": delta,
                                    "finish_reason": None
                                }]
                            }
                            yield f"data: {json.dumps(chunk)}\n\n"

                        previous = current
                        accumulated = current

                    except Exception:
                        logger.exception("Error processing stream chunk")
    return StreamingResponse(event_stream(), media_type="text/event-stream")