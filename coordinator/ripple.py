"""Project recorded delays through a bounded, currently released scene order.

This only identifies additional holds. Workers still propose, the checker still
checks the complete replacement, and the named human still decides.
"""
from datetime import datetime, timedelta
from typing import Any

from coordinator.constraints import Constraints


def ripple_holds(plans: dict[str, dict[str, Any]], facts: Constraints) -> set[str]:
    projected: list[dict[str, Any]] = []
    held: set[str] = set()
    scenes = {s.id:s for s in facts.scenes}
    people = {p.id:p for p in facts.people}
    for m in sorted(plans.values(),key=lambda row:(datetime.fromisoformat(row['start']),row['scene_id'])):
        start,end = datetime.fromisoformat(m['start']),datetime.fromisoformat(m['end'])
        begin = start-timedelta(minutes=m['setup_min'])
        earliest = begin
        rule = scenes.get(m['scene_id'])
        for pid in m['people']:
            person = people.get(pid)
            if person and isinstance(person.available,list):
                windows = [w for w in person.available if w.end > begin]
                if windows:
                    earliest=max(earliest,min(w.start for w in windows))
        for pid in m['people']:
            prior=next((p for p in reversed(projected) if pid in p['people']),None)
            if prior:
                travel = 0 if prior['location']==m['location'] else facts.travel_min.get(prior['location']+'->'+m['location'],0)
                earliest=max(earliest,prior['finish']+timedelta(minutes=travel))
        delay=max(timedelta(),earliest-begin)
        finish=end+delay
        if rule and rule.overrun:
            finish=max(finish,rule.overrun_end+timedelta(minutes=rule.overrun))
        if delay or finish > end:
            held.add(m['scene_id'])
        projected.append(dict(people=m['people'],location=m['location'],finish=finish+timedelta(minutes=m['wrap_min'])))
    return held
