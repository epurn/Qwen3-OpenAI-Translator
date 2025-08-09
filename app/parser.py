import logging
import re
import json
from typing import Optional
from app.schema import ToolCall, FunctionCall

# Set up logging
logger = logging.getLogger(__name__)

TOOL_CALL_RE = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)
FUNCTION_RE = re.compile(r"<function=(.*?)</function>", re.DOTALL)
PARAM_RE = re.compile(r"<parameter=(.*?)</parameter>", re.DOTALL)


def parse_tool_call_block(block: str) -> Optional[ToolCall]:
    logger.debug(f"Parsing tool call block: {block}")
    
    function_match = FUNCTION_RE.search(block)
    if not function_match:
        logger.warning("No function match found in tool call block")
        return None

    function_str = function_match.group(1)
    function_name_end = function_str.find(">")
    if function_name_end == -1:
        logger.warning("No closing '>' found for function name")
        return None

    function_name = function_str[:function_name_end]
    param_str = function_str[function_name_end + 1:]

    args = {}
    for param_match in PARAM_RE.finditer(param_str):
        param_full = param_match.group(1)
        param_name_end = param_full.find(">")
        if param_name_end == -1:
            logger.warning("No closing '>' found for parameter")
            continue
        param_name = param_full[:param_name_end]
        param_value = param_full[param_name_end + 1:].strip()
        args[param_name] = param_value

    tool_call = ToolCall(
        function=FunctionCall(name=function_name, arguments=json.dumps(args, ensure_ascii=False))
    )
    
    logger.debug(f"Parsed tool call: {tool_call}")
    return tool_call