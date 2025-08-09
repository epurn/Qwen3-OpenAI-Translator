# app/state.py
"""Process-local state for streaming edit payloads."""
from collections import deque
from typing import Deque, Optional

_EDIT_QUEUE: Deque[str] = deque()

def push_edit(text: str) -> None:
    if text is None:
        return
    _EDIT_QUEUE.append(str(text))

def pop_edit() -> Optional[str]:
    if not _EDIT_QUEUE:
        return None
    return _EDIT_QUEUE.popleft()

def clear_edits() -> None:
    _EDIT_QUEUE.clear()

def has_edits() -> bool:
    return bool(_EDIT_QUEUE)