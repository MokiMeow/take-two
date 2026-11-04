"""Display labels from reviewed fixtures/configuration, never chat text."""
from zoneinfo import ZoneInfo

from coordinator.constraints import Constraints
from coordinator.ui_models import ChangeCommand


ROLE_LABELS = {'actor': 'Actor', 'camera_sound': 'Camera / sound',
               'director': 'Director', 'producer': 'Producer', 'first-ad': '1st AD'}


def role_label(role: str) -> str:
    return ROLE_LABELS.get(role, role.replace('_', ' ').capitalize())


def person_name(identity: str, names: dict[str, str]) -> str:
    return names.get(identity, 'Unrecognized person')


def person_label(identity: str, names: dict[str, str], roles: dict[str, str]) -> str:
    name = person_name(identity, names)
    role = roles.get(identity)
    return f'{name} ({role})' if role else name


def resolved_change_at(command: ChangeCommand, facts: Constraints, fallback: str) -> str:
    """Expose precisely the validated time used by the checker; retain raw value."""
    collection = {'person': 'people', 'location': 'locations'}.get(command.entity)
    if collection and command.field in ('hard_stop', 'light_until', 'available', 'windows', 'window', 'late_by'):
        target = next((row for row in getattr(facts, collection) if row.id == command.target), None)
        field = {'late_by':'available','window':'windows'}.get(command.field,command.field)
        value = getattr(target, field, None)
        if field in ('available', 'windows'):
            value = min((window.start for window in value), default=None) if isinstance(value, list) else None
        if value is not None:
            return value.astimezone(ZoneInfo(facts.timezone)).isoformat()
    return fallback
