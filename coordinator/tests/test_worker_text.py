import json

import pytest

from coordinator.worker_text import extract_reply


@pytest.mark.parametrize('prefix', ['', '@take-two-coordinator ', '@take-two-coordinator Here is my answer:\n'])
@pytest.mark.parametrize('fence', ['', 'json'])
def test_real_worker_mention_fence(prefix: str, fence: str) -> None:
    assert extract_reply(prefix + '```' + fence + '\n{"job_id":"j1","must_keep":["private {story}"]}\n```') == {
        'job_id': 'j1', 'must_keep': ['private {story}']}


def test_short_preamble_and_plain_object() -> None:
    assert extract_reply('@take-two-coordinator My answer: {"job_id":"j1"}')['job_id'] == 'j1'


@pytest.mark.parametrize('body', [
    '{} {}', '```json\n{}\n```\n```json\n{}\n```',
    '```json\n{}\n``` trailing instructions', 'x'*301 + '{}',
    '```python\n{}\n```', '[]', '{"a":1,"a":2}', '{"a":NaN}', 'x'*65537,
], ids=['objects', 'fences', 'trailing', 'preamble', 'language', 'array', 'duplicate', 'nonfinite', 'size'])
def test_ambiguous_or_unbounded_reply_is_rejected(body: str) -> None:
    with pytest.raises(ValueError):
        extract_reply(body)
