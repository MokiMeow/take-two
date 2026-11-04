"""Deterministic personal duties and differences from explicit confirmations."""
from typing import Any

from coordinator.render_props import call_times, hhmm
from coordinator.presentation import kit_label, role_label


def duties(manifest: dict[str, Any], person: dict[str, Any]) -> dict[str, Any]:
    role = person['role']
    handles_kit = any(word in role.lower() for word in ('camera', 'sound', 'kit'))
    scenes = {}
    for row in manifest['scenes']:
        if person['id'] not in row.get('people', []):
            continue
        scenes[row['scene_id']] = dict(location=row.get('location', 'held'),
            start=row.get('start'), end=row.get('end'), role=role,
            setup_min=row.get('setup_min'), wrap_min=row.get('wrap_min'),
            kit=sorted(row.get('capabilities', [])) if handles_kit else [],
            coverage=sorted(row.get('shots', [])) if handles_kit else [],
            validity=row.get('validity', 'valid'))
    return dict(call=call_times(manifest).get(person['id']), scenes=scenes)


def differences(current: dict[str, Any], baseline: dict[str, Any] | None,
                metadata: dict[str, Any], person: dict[str, Any], prior_person: dict[str, Any] | None = None) -> list[str]:
    new = duties(current, person)
    old = duties(baseline or dict(scenes=[]), prior_person or person)
    if baseline is not None and new == old:
        return []
    numbers = {s['id']: s['number'] for s in metadata['scenes']}
    lines = []
    for sid in sorted(new['scenes'].keys() | old['scenes'].keys()):
        a, b = old['scenes'].get(sid), new['scenes'].get(sid)
        prefix = f'Scene {numbers[sid]}'
        if a == b:
            continue
        if b is None:
            lines.append(f'{prefix}: no longer assigned')
        elif a is None:
            parts = [f"{prefix}: {b['location'].replace('_', ' ').title()}, {hhmm(b['start']) if b['start'] else 'held'}–{hhmm(b['end']) if b['end'] else 'held'}",
                person.get('role_label') or role_label(b['role'])]
            if b['kit']:
                parts.append('kit ' + ', '.join(kit_label(k, metadata) for k in b['kit']))
            lines.append('; '.join(parts))
        else:
            for key, label in (('location', ''), ('start', 'start '), ('end', 'end '),
                    ('role', 'role '), ('kit', 'kit '), ('coverage', 'coverage '),
                    ('setup_min', 'setup minutes '), ('wrap_min', 'wrap minutes '), ('validity', 'status ')):
                if a[key] != b[key]:
                    def display(value: Any) -> str:
                        if key in ('start', 'end') and value:
                            return hhmm(value)
                        if key == 'location':
                            return value.replace('_', ' ').title()
                        if key == 'role':
                            member = person if value == b['role'] else (prior_person or person)
                            return member.get('role_label') or role_label(value)
                        if isinstance(value, list):
                            return ', '.join(kit_label(v, metadata) if key == 'kit' else v.replace('_', ' ') for v in value)
                        return str(value if value is not None else 'none')
                    if key == 'kit' and (not a[key] or not b[key]):
                        action = 'added' if b[key] else 'removed'
                        lines.append(f'{prefix}: kit {action} {display(b[key] or a[key])}')
                        continue
                    lines.append(f'{prefix}: {label}{display(a[key])} → {display(b[key])}')
    call = hhmm(new['call']) if new['call'] else 'held'
    if baseline is None:
        lines.append(f'Call {call}')
    elif new['call'] != old['call']:
        prior = hhmm(old['call']) if old['call'] else 'held'
        lines.append(f'Call {call} (was {prior})')
    return [line[:500] for line in lines]


def personal_changes(state: dict[str, Any], workflow: dict[str, Any], manifest: dict[str, Any],
                     metadata: dict[str, Any]) -> dict[str, list[str]]:
    result = {}
    for person in metadata['crew']:
        confirmed = next((r for r in sorted(state['releases'], key=lambda r: r['number'], reverse=True)
            if any(a['person'] == person['id'] for a in r['acks']['confirmed'])), None)
        confirmed_id = workflow.get('confirmed_releases', {}).get(person['id']) or (confirmed['release_id'] if confirmed else None)
        envelope = workflow['releases'].get(confirmed_id, {}).get('envelope', {})
        baseline = envelope.get('manifest')
        prior_person = next((p for p in envelope.get('metadata', {}).get('crew', []) if p['id'] == person['id']), person)
        result[person['id']] = differences(manifest, baseline, metadata, person, prior_person)
    return result
