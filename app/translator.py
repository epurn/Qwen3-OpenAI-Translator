import json
import logging
from typing import List, Optional, Dict, Any
from app.parser import TOOL_CALL_RE, parse_tool_call_block
from app.schema import TranslatedResponse, ToolCall

logger = logging.getLogger(__name__)

# Centralized arg alias map for edit tools
_EDIT_ARG_ALIASES: Dict[str, set[str]] = {
    "filepath": {"filepath", "file_path", "path"},
    "changes": {"changes", "diff", "edits", "replacements"},
}

def _normalize_edit_args(raw_args: Dict[str, Any], expected_props: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map common aliases onto the property names the tool actually exposes.
    If the tool expects 'file_path' (not 'filepath'), normalize to 'file_path', etc.
    """
    if not expected_props:
        return raw_args

    # Build reverse map: alias -> expected_key
    alias_to_expected: Dict[str, str] = {}
    # Compute which canonical keys exist in this schema
    expected_keys = set(expected_props.keys())
    for canonical, aliases in _EDIT_ARG_ALIASES.items():
        # If the schema exposes one of these names, prefer that as the target
        target = None
        # Try exact canonical first (e.g., 'filepath') if it exists in schema
        if canonical in expected_keys:
            target = canonical
        else:
            # Otherwise, pick the first alias that is actually in schema (stable order via sorted)
            for alias in sorted(aliases):
                if alias in expected_keys:
                    target = alias
                    break
        # If schema doesn't expose any of these, skip mapping for this group
        if not target:
            continue
        for alias in aliases:
            alias_to_expected[alias] = target

    normalized: Dict[str, Any] = {}
    for k, v in raw_args.items():
        target = alias_to_expected.get(k, k)
        # If collision, favor a value that isn't empty
        if target in normalized and (normalized[target] or not v):
            continue
        normalized[target] = v

    return normalized

def translate_xml_to_openai(xml_text: str, tools: Optional[List[Dict[str, Any]]] = None) -> TranslatedResponse:
    if not isinstance(xml_text, str):
        return TranslatedResponse(tool_calls=[], content="")

    blocks = TOOL_CALL_RE.findall(xml_text)

    # Map tool name -> parameters schema (OpenAI style)
    tool_schemas: Dict[str, Any] = {
        t["function"]["name"]: t["function"].get("parameters")
        for t in (tools or []) if t.get("type") == "function"
    }

    def coerce_arguments(call: ToolCall) -> ToolCall:
        name = call.function.name
        params = tool_schemas.get(name)
        if not params:
            return call

        # Either {"type":"object","properties":{...}} or raw {"prop": {...}}
        props = (params or {}).get("properties", params or {})
        try:
            raw_args: Dict[str, Any] = json.loads(call.function.arguments)
        except Exception:
            logger.debug("Arguments were not valid JSON; leaving as string payload.")
            return call

        # Normalize edit args to match the schema’s property names
        if name in {"edit_file", "edit_existing_file"} and isinstance(props, dict):
            raw_args = _normalize_edit_args(raw_args, props)

        coerced: Dict[str, Any] = {}
        for key, raw in raw_args.items():
            schema = props.get(key, {})
            typ = (schema.get("type") if isinstance(schema, dict) else None) or "string"
            val = raw

            if typ in ("object", "array"):
                # If it's a JSON-encoded string, parse it; if it's already parsed, keep it
                if isinstance(raw, str):
                    try:
                        val = json.loads(raw)
                    except Exception:
                        pass
            elif typ == "integer":
                try:
                    val = int(raw)
                except Exception:
                    pass
            elif typ == "number":
                try:
                    val = float(raw)
                except Exception:
                    pass
            elif typ == "boolean":
                val = str(raw).strip().lower() == "true"

            coerced[key] = val

        call.function.arguments = json.dumps(coerced, ensure_ascii=False)
        return call

    tool_calls: List[ToolCall] = []
    for block in blocks:
        call = parse_tool_call_block(block)
        if not call:
            continue
        call = coerce_arguments(call)
        tool_calls.append(call)

    first_idx = xml_text.find("<tool_call>")
    content = xml_text[:first_idx].strip() if first_idx > 0 else ""
    if not tool_calls and not content:
        content = xml_text.strip()

    return TranslatedResponse(tool_calls=tool_calls, content=content)