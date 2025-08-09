from pydantic import BaseModel
from typing import Any, Dict, List, Literal, Optional, Union


class FunctionCall(BaseModel):
    name: str
    arguments: str


class ToolCall(BaseModel):
    type: str = "function"
    function: FunctionCall
    id: Optional[str] = None


class TranslationRequest(BaseModel):
    xml: str


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


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 1.0
    stream: Optional[bool] = False
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Dict[str, Any] | str] = None
    

class ChatCompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[Choice]
    usage: UsageStats

class CompletionRequest(BaseModel):
    model: str
    prompt: Union[str, List[str], None] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = 1.0
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None


class CompletionChoice(BaseModel):
    index: int
    text: str
    finish_reason: Optional[str] = "stop"


class CompletionResponse(BaseModel):
    id: str
    object: Literal["text_completion"] = "text_completion"
    created: int
    model: str
    choices: List[CompletionChoice]
    usage: UsageStats