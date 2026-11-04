"""A single bounded JSON object inside the workers' addressed chat envelope."""
import json
import re
from typing import Any

MAX_REPLY_BYTES = 65536


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def extract_reply(body: str) -> dict[str, Any]:
    if len(body.encode('utf-8')) > MAX_REPLY_BYTES:
        raise ValueError('Worker reply exceeds 64 KiB')
    body = re.sub(r'^(?:\s*@[\w.:-]+\s+)+', '', body).strip()
    if '```' in body:
        match = re.fullmatch(r'([^`]{0,300})```(?:json)?\s*\n(.*?)\n```\s*', body, re.DOTALL)
        if not match or any(c in match[1] for c in '{}'):
            raise ValueError('Expected exactly one JSON fence')
        body = match[2].strip()
    else:
        start = body.find('{')
        if start < 0 or start > 300 or any(c in body[:start] for c in '{}[]'):
            raise ValueError('Expected one JSON object and a short preamble')
        body = body[start:]
    def invalid_constant(_: str) -> None:
        raise ValueError('Nonfinite JSON number')
    try:
        value = json.loads(body, object_pairs_hook=_unique, parse_constant=invalid_constant)
    except (RecursionError, UnicodeError) as exc:
        raise ValueError('Invalid worker JSON') from exc
    if not isinstance(value, dict):
        raise ValueError('Worker reply must be an object')
    return value
