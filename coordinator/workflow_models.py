"""Validated worker wire contracts. Workers never supply feasibility or authority."""
from typing import Annotated, Any
from copy import deepcopy
from contextlib import contextmanager
from collections.abc import Iterator
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from coordinator.constraints import Manifest, Constraints
from coordinator.ui_models import ChangeCommand
from coordinator.checker import CheckResult, check_manifest

IST = ZoneInfo('Asia/Kolkata')

Identifier = Annotated[str, Field(min_length=1, max_length=200)]

class Reply(BaseModel):
    model_config = ConfigDict(extra='forbid',str_max_length=2000)
    job_id: Identifier
    script_rev: int = Field(strict=True, ge=1)
    constraints_rev: int = Field(strict=True, ge=1)
    addressed_to: str | None = None

class SupervisorReply(Reply):
    must_keep: list[Identifier] = Field(min_length=1, max_length=10)
    preferences: list[Identifier] = Field(default_factory=list, max_length=40)
    summary: str = Field(default='',max_length=1000)

class Proposal(BaseModel):
    model_config = ConfigDict(extra='forbid')
    candidate_id: Identifier
    label: str = Field(min_length=1, max_length=80)
    story_cost: str = Field(max_length=400)
    manifest: Manifest | None = None
    manifests: list[Manifest] | None = Field(default=None, min_length=1, max_length=20)

    @model_validator(mode='after')
    def one_schedule(self) -> 'Proposal':
        if (self.manifest is None) == (self.manifests is None):
            raise ValueError('Provide manifest or manifests, exclusively')
        rows = self.plans()
        if len({m.scene_id for m in rows})!=len(rows):
            raise ValueError('Duplicate schedule scene')
        return self

    def plans(self) -> list[Manifest]:
        return self.manifests if self.manifests is not None else [self.manifest]

class ADReply(Reply):
    candidates: list[Proposal] = Field(min_length=1, max_length=3)


def visible_candidate(item: dict[str, Any]) -> dict[str, Any]:
    """Project a checked, revision-bound manifest into the stable UI contract."""
    result = deepcopy(item)
    if result.get('manifests'):
        result['schedule']=[visible_candidate(dict(manifest=m))['manifest'] for m in result['manifests']]
    for key in ('manifests','letter','presentation','presentation_receipt'):
        result.pop(key,None)
    result['manifest'] = {k:v for k,v in result['manifest'].items() if k in
        ('scene_id','location','start','end','setup_min','wrap_min','people','shots','capabilities')}
    for key in ('start','end'):
        result['manifest'][key] = datetime.fromisoformat(result['manifest'][key]).astimezone(ZoneInfo('Asia/Kolkata')).isoformat()
    return result


def release_snapshot(state: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    """Keep every unchanged scene in the same complete production snapshot."""
    scenes = []
    for scene in state['scenes']:
        if scene['id'] == manifest['scene_id']:
            scenes.append(deepcopy(manifest))
        elif scene.get('validity') != 'valid':
            scenes.append(dict(scene_id=scene['id'],validity='held',hold_reason=scene.get('hold_reason','Awaiting a checked replacement')))
        elif scene.get('plan'):
            scenes.append(dict(scene_id=scene['id'], unchanged=True, **scene['plan']))
    return dict(scenes=scenes)


def check_candidate(manifest: Manifest, constraints: Constraints, state: dict[str, Any]) -> CheckResult:
    """Unchanged scheduled duties consume time too, including their setup/wrap."""
    facts = constraints.model_dump(mode='json')
    for scene in state['scenes']:
        plan = scene.get('plan')
        if scene['id'] == manifest.scene_id or not plan or scene.get('validity')!='valid':
            continue
        start = datetime.fromisoformat(plan['start']) - timedelta(minutes=plan['setup_min'])
        end = datetime.fromisoformat(plan['end']) + timedelta(minutes=plan['wrap_min'])
        for person in plan['people']:
            facts['commitments'].append(dict(person_id=person,location=plan['location'],start=start.isoformat(),end=end.isoformat()))
    return check_manifest(manifest,Constraints.model_validate(facts))


def normalize_outcome(outcome: Any) -> dict[str, Any]:
    """Read Switch's stored question answer without interpreting human prose."""
    result = outcome.model_dump(mode='json') if hasattr(outcome,'model_dump') else dict(outcome)
    if 'candidate_id' not in result:
        choices = []
        for answer in result.get('answers') or []:
            if answer.get('questionId',answer.get('question_id')) == 'choice':
                choices.extend(answer.get('selectedOptionIds',answer.get('selected_option_ids',[])))
                result['note'] = answer.get('custom_text',answer.get('customText',answer.get('customAnswer',answer.get('custom_answer'))))
        if len(choices)==1:
            result['candidate_id']=choices[0]
        elif not choices and result.get('note'):
            result['candidate_id']='neither'
    return result


@contextmanager
def workflow_transaction(loop: Any) -> Iterator[Any]:
    """SQLite rollback must also restore the coordinator's live revision."""
    saved, facts = deepcopy(loop.workflow), loop.constraints
    try:
        with loop.ledger.transaction() as connection:
            yield connection
    except BaseException:
        loop.workflow, loop.constraints = saved, facts
        raise


def note_constraints(constraints: Constraints, scene_ids: set[str], note: str) -> Constraints:
    """A director's note is a requirement, never self-verifying evidence."""
    facts = constraints.model_dump(mode='json')
    for scene in facts['scenes']:
        if scene['id'] in scene_ids and note not in scene['hard']:
            scene['hard'].append(note)
    facts['constraints_rev'] += 1
    return Constraints.model_validate(facts)


def apply_change(command: ChangeCommand, constraints: Constraints, authorities: dict[str, list[str]], now: datetime) -> tuple[str, str | None, Constraints | None]:
    """Return (status, reason, validated facts); no partial mutations."""
    facts = constraints.model_dump(mode='json')
    role = None
    field = command.field
    if command.entity == 'scene' and field == 'safety':
        if command.target not in {s.id for s in constraints.scenes}:
            return 'rejected', 'Unknown scene', None
        if command.value not in ('hold', 'clear'):
            return 'rejected', 'Safety value must be hold or clear', None
        if command.value == 'clear' and command.reporter not in authorities.get(f'safety:{command.target}', authorities.get('safety', [])):
            return 'pending_confirmation', 'Named safety clearance required', None
        facts['constraints_rev'] += 1
        return 'recorded', None, Constraints.model_validate(facts)
    if command.entity == 'location' and field in ('permission','windows','light_until'):
        role = 'location_permission'
    elif command.entity == 'person' and field in ('hard_stop','available'):
        role = 'availability_confirmation'
    elif command.entity=='scene' and field in ('hard','preferences','verified_facts') or command.entity=='capability':
        role = 'creative' if command.entity == 'scene' else 'capability_verification'
    else:
        return 'rejected', 'Unsupported change field', None
    allowed = authorities.get(role, [])
    if role == 'location_permission':
        location = next((x for x in constraints.locations if x.id == command.target),None)
        named = location.permission_authority if location else None
        allowed = authorities.get(f'location_permission:{command.target}',allowed if named=='producer' else authorities.get(named or '',[named] if named else []))
    if command.reporter not in allowed:
        if command.entity == 'location' and field == 'permission' and command.value in ('refused', 'unknown'):
            target = next((x for x in facts['locations'] if x['id'] == command.target), None)
            if target:
                target.update(permission='unknown', permission_confirmed_by=None)
                facts['constraints_rev'] += 1
                return 'pending_confirmation', 'Named permission confirmation required', Constraints.model_validate(facts)
        return 'pending_confirmation', f'Confirmation required from {role}', None
    value = command.value
    if field in ('hard_stop','light_until') and len(value) in (5,8):
        collection = 'people' if command.entity == 'person' else 'locations'
        target = next((x for x in facts[collection] if x['id'] == command.target), {})
        prior = target.get(field)
        if not prior:
            return 'rejected', 'Use a full timezone-aware timestamp when shoot day is unknown', None
        day = datetime.fromisoformat(prior).astimezone(IST).date().isoformat()
        value = f"{day}T{value}+05:30"
    try:
        if command.entity == 'capability':
            if field != 'status':
                return 'rejected','Capability field must be status',None
            facts['capabilities'][command.target] = value
        else:
            collection = {'location':'locations','person':'people','scene':'scenes'}[command.entity]
            target = next((x for x in facts[collection] if x['id']==command.target),None)
            if target is None:
                return 'rejected','Unknown change target',None
            if field in ('available','windows','hard','preferences','verified_facts'):
                value = json.loads(value)
            target[field] = value
            if field == 'permission':
                # The checker records the named authority; changes retain the
                # exact authenticated Switch reporter identity separately.
                target['permission_confirmed_by'] = target.get('permission_authority')
        facts['constraints_rev'] += 1
        return 'recorded',None,Constraints.model_validate(facts)
    except (ValidationError,ValueError,TypeError):
        return 'rejected','Invalid value for structured change',None

