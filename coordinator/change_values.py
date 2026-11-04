"""Bounded shoot-day shorthand; authority checks happen before this module runs."""
from datetime import datetime, timedelta
import json
import re
from typing import Any
from zoneinfo import ZoneInfo

from coordinator.constraints import Constraints
from coordinator.ui_models import ChangeCommand


def minute_count(value: str) -> int:
    if not re.fullmatch(r'[0-9]{1,4}', value) or not 0 <= int(value) <= 1440:
        raise ValueError('Minutes must be 0..1440')
    return int(value)


def normalize_change(command: ChangeCommand, constraints: Constraints,
                     plans: dict[str, dict[str, Any]]) -> tuple[str, Any]:
    field, value = command.field, command.value
    if command.entity == 'capability':
        if command.target not in constraints.capabilities:
            raise ValueError('Unknown capability')
        return field, 'refused' if value == 'unavailable' else value
    if command.entity == 'scene' and field == 'overrun':
        scene = next(s for s in constraints.scenes if s.id == command.target)
        plan = plans.get(command.target)
        if not plan or minute_count(value) < scene.overrun:
            raise ValueError('Overrun needs a released plan and cannot undo observed time')
        return field, dict(overrun=minute_count(value),
            overrun_start=scene.overrun_start or plan['start'], overrun_end=scene.overrun_end or plan['end'])
    target = next((p for p in constraints.people if p.id == command.target), None) if command.entity == 'person' else next(
        (p for p in constraints.locations if p.id == command.target), None)
    windows = getattr(target, 'available' if command.entity == 'person' else 'windows', None)
    zone = ZoneInfo(constraints.timezone)
    if field == 'late_by':
        calls = [datetime.fromisoformat(m['start'])-timedelta(minutes=m['setup_min'])
                 for m in plans.values() if command.target in m['people']]
        if not calls:
            raise ValueError('late_by needs a released call time')
        arrival = min(calls)+timedelta(minutes=minute_count(value))
    elif field == 'available' and re.fullmatch(r'\d{2}:\d{2}', value):
        if not isinstance(windows, list) or not windows:
            raise ValueError('Use explicit availability intervals when the day is unknown')
        arrival = datetime.combine(windows[0].start.astimezone(zone).date(), datetime.strptime(value,'%H:%M').time(), zone)
    else:
        arrival = None
    if arrival is not None:
        if not isinstance(windows, list):
            raise ValueError('Cannot extend unknown availability')
        return 'available', [dict(start=max(w.start,arrival).isoformat(),end=w.end.isoformat()) for w in windows if w.end > arrival]
    if field == 'window':
        if not re.fullmatch(r'\d{2}:\d{2}-\d{2}:\d{2}', value) or not isinstance(windows,list) or not windows:
            raise ValueError('Window needs HH:mm-HH:mm and a known shoot day')
        day=windows[0].start.astimezone(zone).date()
        start,end=(datetime.combine(day,datetime.strptime(t,'%H:%M').time(),zone).isoformat() for t in value.split('-'))
        return 'windows', [dict(start=start,end=end)]
    if field in ('available','windows','hard','preferences','verified_facts'):
        return field,json.loads(value)
    return field,value
