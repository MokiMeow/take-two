"""Display labels from reviewed fixtures/configuration, never chat text."""
from zoneinfo import ZoneInfo
from typing import Any

from coordinator.constraints import Constraints
from coordinator.ui_models import ChangeCommand
from coordinator.render_props import hhmm


ROLE_LABELS = {'actor': 'Actor', 'camera_sound': 'Camera / sound',
               'director': 'Director', 'producer': 'Producer', 'first-ad': '1st AD'}


def role_label(role: str) -> str:
    return ROLE_LABELS.get(role, role.replace('_', ' ').capitalize())


def person_name(identity: str, names: dict[str, str]) -> str:
    return names.get(identity, 'Unrecognized person')


def person_label(identity: str, names: dict[str, str], roles: dict[str, str]) -> str:
    name = person_name(identity, names)
    role = roles.get(identity)
    return f'{name} ({role_label(role)})' if role else name


def kit_label(kit: str, metadata: dict[str, Any]) -> str:
    return metadata.get('kit_labels', {}).get(kit, kit.replace('_', ' '))


def scene_details(row: dict[str, Any], metadata: dict[str, Any]) -> str:
    names = {p['id']: p['name'] for p in metadata['crew']}
    text = (f"{row['location'].replace('_', ' ').title()} {hhmm(row['start'])}–{hhmm(row['end'])}; "
        f"setup {row['setup_min']}m, wrap {row['wrap_min']}m; "
        f"people: {', '.join(names[p] for p in row['people'])}; shots: {', '.join(row['shots'])}")
    if row['capabilities']:
        text += '; kit ' + ', '.join(kit_label(k, metadata) for k in row['capabilities'])
    return text


def change_label(command: ChangeCommand, metadata: dict[str, Any]) -> str:
    """Human wording for the validated command; IDs remain in the card record."""
    target = command.target.replace('_', ' ').title()
    if command.entity == 'person':
        target = next(p['name'] for p in metadata['crew'] if p['id'] == command.target)
    elif command.entity == 'scene':
        target = next(f"Scene {s['number']}" for s in metadata['scenes'] if s['id'] == command.target)
    elif command.entity == 'capability':
        target = kit_label(command.target, metadata)
    return f"{target}: {command.field.replace('_', ' ')} {command.value}"


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
