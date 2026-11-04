"""Canonical schedules, replacement scope and cross-scene feasibility."""
from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
import json
from typing import Any

from coordinator.checker import CheckResult, check_manifest
from coordinator.constraints import Constraints, Manifest


def digest(value: dict[str, Any]) -> str:
    canonical = {k:v for k,v in value.items() if k!='manifest_hash'}
    return 'sha256:'+hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def plans(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    return candidate.get('manifests') or [candidate['manifest']]


def check_schedule(proposed: list[Manifest], constraints: Constraints,
                   retained: list[dict[str, Any]]) -> CheckResult:
    replaced = {m.scene_id for m in proposed}
    current = [m.model_dump(mode='json',exclude={'manifest_hash'}) for m in proposed]
    current += [deepcopy(m) for m in retained if m['scene_id'] not in replaced and m.get('validity') not in ('held','invalid')]
    results = []
    for manifest in proposed:
        facts = constraints.model_dump(mode='json')
        for other in current:
            if other['scene_id']==manifest.scene_id:
                continue
            begin = datetime.fromisoformat(other['start'])-timedelta(minutes=other['setup_min'])
            finish = datetime.fromisoformat(other['end'])+timedelta(minutes=other['wrap_min'])
            facts['commitments'].extend(dict(person_id=p,location=other['location'],start=begin.isoformat(),end=finish.isoformat()) for p in other['people'])
        results.append(check_manifest(manifest,Constraints.model_validate(facts)))
    verdict = 'fail' if any(r.result=='fail' for r in results) else 'needs_verification' if any(r.result=='needs_verification' for r in results) else 'pass'
    reasons = list(dict.fromkeys(reason for r in results for reason in r.reasons))
    return CheckResult(result=verdict,reasons=reasons[:99]+(['Further check reasons omitted.'] if len(reasons)>99 else []))


def retained_plans(workflow: dict[str, Any], state: dict[str, Any]) -> list[dict[str, Any]]:
    valid = {s['id'] for s in state['scenes'] if s['validity']=='valid'}
    return [m for sid,m in workflow.get('plans',{}).items() if sid in valid]


def snapshot(workflow: dict[str, Any], state: dict[str, Any], proposed: list[dict[str, Any]],
             constraints: Constraints) -> dict[str, Any]:
    replacements = {m['scene_id']:m for m in proposed}
    rows = []
    for scene in state['scenes']:
        sid = scene['id']
        if sid in replacements:
            rows.append(deepcopy(replacements[sid]))
        elif scene['validity']=='valid' and sid in workflow.get('plans',{}):
            rows.append(dict(deepcopy(workflow['plans'][sid]),script_rev=constraints.script_rev,constraints_rev=constraints.constraints_rev))
        else:
            rows.append(dict(scene_id=sid,validity='held',hold_reason=scene.get('hold_reason') or 'Awaiting a checked replacement'))
    return dict(script_rev=constraints.script_rev,constraints_rev=constraints.constraints_rev,scenes=rows)
