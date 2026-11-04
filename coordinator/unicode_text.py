"""Reject invalid Unicode before external JSON reaches persistence or UI state."""
from typing import Any


def require_unicode(value: Any) -> Any:
    pending = [(value, 0)]
    count = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if depth > 64 or count > 100000:
            raise ValueError('JSON structure exceeds the validation limit')
        if isinstance(item, str):
            item.encode('utf-8', errors='strict')
        elif isinstance(item, dict):
            pending.extend((part, depth + 1) for pair in item.items() for part in pair)
        elif isinstance(item, (list, tuple)):
            pending.extend((part, depth + 1) for part in item)
    return value
