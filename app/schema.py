from pydantic import BaseModel, ConfigDict
from typing import Dict, List, Literal, Optional


class FunctionCall(BaseModel):
    name: str
    arguments: str


class ToolCall(BaseModel):
    type: str = "function"
    function: FunctionCall
    id: Optional[str] = None


class TranslatedResponse(BaseModel):
    tool_calls: Optional[List[ToolCall]]
    content: str = ""


class ChatMessage(BaseModel):
    role: Literal["user", "system", "assistant"]
    content: Optional[str]


class AssistantMessage(BaseModel):
    role: str
    content: str
    tool_calls: Optional[List[ToolCall]] = None


class Choice(BaseModel):
    index: int
    message: AssistantMessage
    finish_reason: str


class UsageStats(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_tokens_details: Optional[dict] = None


class ChatCompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[Choice]
    usage: UsageStats