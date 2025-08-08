from pprint import pprint
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from app.translator import translate_xml_to_openai
from app.schema import AssistantMessage, ChatCompletionResponse, ChatMessage, Choice, FunctionCall, ToolCall, TranslatedResponse, UsageStats
from dotenv import load_dotenv
import httpx
import os

load_dotenv()
app = FastAPI()

# Add this line at the top (env var or hardcoded)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api"

# ----- Simple health + debug -----

class TranslationRequest(BaseModel):
    xml: str

@app.post("/translate", response_model=TranslatedResponse)
async def translate(request: TranslationRequest):
    return translate_xml_to_openai(request.xml)

@app.post("/health")
async def health():
    return {"status": "ok"}


# ----- OpenAI-compatible endpoint -----

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 1.0
    stream: Optional[bool] = False




@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def openai_compatible(request: ChatCompletionRequest):
    print("Request stream:", request.stream)
    
    request_payload = request.model_dump()
    request_payload["stream"] = False

    async with httpx.AsyncClient(timeout=60.0) as client:
        openrouter_response = await client.post(
            f"{OPENROUTER_BASE_URL}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json=request_payload,
        )

    if not openrouter_response.is_success:
        print("OpenRouter error:", openrouter_response.text)
        return {
            "error": "OpenRouter call failed",
            "status_code": openrouter_response.status_code,
            "body": openrouter_response.text,
        }

    raw_data = openrouter_response.json()
    raw_response = raw_data["choices"][0]["message"]["content"]

    translated = translate_xml_to_openai(raw_response)
    if not translated.content and not translated.tool_calls:
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

    fianl_payload = response_payload.model_dump(exclude_none=True)
    pprint(fianl_payload)
    return fianl_payload