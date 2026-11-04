"""The coordinator deliberately has no free-text fact inference."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ChangeCommand(BaseModel):
    model_config = ConfigDict(extra='forbid')
    entity: Literal['location', 'person', 'scene', 'capability']
    target: str = Field(min_length=1, max_length=120)
    field: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=2000)
    reporter: str = Field(min_length=1, max_length=200)


class ParsedReport(BaseModel):
    status: Literal['recorded', 'pending_confirmation', 'rejected']
    command: ChangeCommand | None = None
    text: str = Field(max_length=8192)
    source_message_id: str = Field(max_length=500)
    reporter: str = Field(max_length=200)
    reason: str | None = None


def parse_command(text: str, reporter: str, source_message_id: str) -> ParsedReport:
    """Preserve unstructured reports; only five explicit fields change facts."""
    base = dict(text=text[:8192], reporter=reporter[:200], source_message_id=source_message_id[:500])
    if len(text) > 8192 or len(reporter) > 200 or len(source_message_id) > 500:
        return ParsedReport(**base, status='rejected', reason='Report exceeds the input limit.')
    if not text.startswith('/change'):
        return ParsedReport(**base, status='pending_confirmation')
    parts = text.split(maxsplit=4)
    if len(parts) != 5 or parts[0] != '/change':
        return ParsedReport(**base, status='rejected', reason='Use /change <entity> <target> <field> <value>.')
    try:
        command = ChangeCommand(entity=parts[1], target=parts[2], field=parts[3], value=parts[4], reporter=reporter)
    except ValidationError:
        return ParsedReport(**base, status='rejected', reason='The structured change has invalid fields.')
    return ParsedReport(**base, command=command, status='recorded')
