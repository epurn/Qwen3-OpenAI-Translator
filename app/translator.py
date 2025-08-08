from typing import List, Optional
from app.parser import TOOL_CALL_RE, parse_tool_call_block
from app.schema import TranslatedResponse, ToolCall


def translate_xml_to_openai(xml_text: str) -> TranslatedResponse:
    """Convert Qwen-style XML tool calls to OpenAI-compatible ToolCall models.

    Args:
        xml_text: Raw assistant text that may contain <tool_call>...</tool_call> blocks.

    Returns:
        TranslatedResponse with a list of ToolCall models and leading plain content.
    """
    if not isinstance(xml_text, str):
        return TranslatedResponse(tool_calls=[], content="")

    # Parse tool calls
    blocks = TOOL_CALL_RE.findall(xml_text)
    tool_calls: List[ToolCall] = [
        call for block in blocks
        if (call := parse_tool_call_block(block)) is not None
    ]

    # Content before the first tool_call (OpenAI expects a string, even if empty)
    first_idx = xml_text.find("<tool_call>")
    content = xml_text[:first_idx].strip() if first_idx != -1 and first_idx > 0 else ""

    # If there are no tool calls and no leading content, fall back to the whole text
    if not tool_calls and not content:
        content = xml_text.strip()

    return TranslatedResponse(tool_calls=tool_calls, content=content)
