"""Process-local state for small, shared values."""
from typing import Optional

_LAST_EDIT_TEXT: Optional[str] = None

def set_last_edit_text(value: Optional[str]) -> None:
    global _LAST_EDIT_TEXT
    _LAST_EDIT_TEXT = value

def get_last_edit_text() -> Optional[str]:
    return _LAST_EDIT_TEXT

def clear_last_edit_text() -> None:
    set_last_edit_text(None)