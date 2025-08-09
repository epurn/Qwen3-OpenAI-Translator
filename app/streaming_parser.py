import re
import json
import uuid
import logging
from typing import Dict, Optional, List, Set, Tuple

from app.state import has_edits, is_in_flight, push_edit, set_in_flight


# Set up logging
logger = logging.getLogger(__name__)

def _gen_id() -> str:
    return f"call{uuid.uuid4().hex[:24]}"

def _strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        return s[1:-1]
    return s

# Strict tool-fence:
# - opening fence on its own line
# - body captured in (?P<body>...)
# - must end with END_ARG immediately before closing fence
TOOL_FENCE_RE = re.compile(
    r"```tool[ \t]*\r?\n"
    r"(?P<body>(?:(?!```)[\s\S])*?^\s*END_ARG\s*\r?\n)"  # include END_ARG
    r"(?=```)",                                          # assert fence is next
    re.DOTALL | re.MULTILINE,
)
# Line-anchored tool name
TOOL_NAME_RE = re.compile(r"^\s*TOOL_NAME\s*:\s*([A-Za-z0-9_\-./]+)\s*$", re.MULTILINE)
# Line-anchored arg blocks
ARG_BLOCK_RE = re.compile(
    r"^BEGIN_ARG:\s*([^\r\n]+)\s*\r?\n"   # arg name on same line
    r"(?P<val>.*?)(?:\r?\n)?"             # lazy value (multiline)
    r"^\s*END_ARG\s*$",                   # until END_ARG on its own line
    re.DOTALL | re.MULTILINE
)

def _parse_tool_blocks(text: str) -> List[Tuple[str, Dict[str, str], str]]:
    results: List[Tuple[str, Dict[str, str], str]] = []
    for m in TOOL_FENCE_RE.finditer(text):
        block_body = m.group("body")
        name_m = TOOL_NAME_RE.search(block_body)
        if not name_m:
            continue
        tool_name = name_m.group(1).strip()

        args: Dict[str, str] = {}
        for arg_name, arg_val in ARG_BLOCK_RE.findall(block_body):
            args[arg_name.strip()] = arg_val.strip()

        fingerprint = f"{tool_name}|{hash(block_body)}"
        results.append((tool_name, args, fingerprint))
    return results


class QwenStreamingParser:
    def __init__(self, preferred_names: Optional[set[str]] = None) -> None:
        self._preferred_names = preferred_names or set()
        self.reset()

    def reset(self) -> None:
        """Clear parser state so it can be reused safely."""
        self._emitted: Set[str] = set()
        self._last_returned_content: str = ""
        self._prev_text: str = ""

    def extract_stream_delta(
        self,
        previous_text: str,
        current_text: str,
        delta_text: str,
    ) -> Optional[dict]:
        """
        previous_text: buffered text before this chunk (unused by this minimal impl)
        current_text:  full text including this chunk
        delta_text:    just the new characters for this chunk

        Returns an OpenAI streaming 'delta' dict or None.
        """
        # 1) On every chunk, check for completed tool fences
        blocks = _parse_tool_blocks(current_text)
        for tool_name, args, fp in blocks:
            if fp in self._emitted:
                continue

            if tool_name in {"edit_file", "edit_existing_file"}:
                if is_in_flight() or has_edits():
                    # Defer; we’ll retry on next buffer growth
                    logger.debug("Deferring edit tool_call because another edit is in flight or queue not empty")
                    continue

                filepath = _strip_quotes(args.get("filepath", "") or "")
                changes = args.get("changes") or args.get("text") or ""
                if not filepath or not str(changes).strip():
                    continue

                # Enqueue the payload and mark as in-flight
                push_edit(str(changes))
                set_in_flight(True)

            arguments = json.dumps(args, ensure_ascii=False)
            logger.debug(f"_____ TOOL CALLS ____\n\tname: {tool_name}\n\t{arguments}")
            self._emitted.add(fp)
            return {
                "tool_calls": [{
                    "index": 0,
                    "id": "call_apply_singleton",   # any placeholder; Continue ignores it
                    "type": "function",
                    "function": {"name": tool_name, "arguments": arguments},
                }]
            }

        # 2) If no tool_call to emit, pass through the raw content delta (if any)
        if delta_text:
            # Avoid re-sending same content if caller retries
            if delta_text != self._last_returned_content:
                self._last_returned_content = delta_text
                return {"content": delta_text}

        return None