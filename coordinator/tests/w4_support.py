from pathlib import Path
from typing import Any
from copy import deepcopy
from coordinator.runtime import read_yaml
from coordinator.tests.test_w4_workflow import manifest


def metadata() -> dict[str,Any]:
    script=read_yaml('script.yaml')
    return dict(production=dict(title=script['title'],day='Day 1',date='Friday 6 November 2026',timezone='Asia/Kolkata'),
        scenes=script['scenes'],crew=read_yaml('crew.yaml')['crew'])


def release_payload(payload: dict[str,Any]) -> dict[str,Any]:
    result=deepcopy(payload)
    rows=[manifest('s1','stairwell','15:00','15:15'),manifest('s2','courtyard','15:25','15:35'),manifest(location='stairwell',start='16:30',end='17:15')]
    envelope=dict(manifest=dict(scenes=rows),previous_manifest=None,metadata=metadata(),release=dict(
        number=2,release_id='r2',manifest_hash='sha256:'+'a'*64,summary='Scene 3 moves to the stairwell.',changes=[],created_at='2026-11-06T14:00:00+05:30'))
    from coordinator.schedules import digest
    envelope['release']['manifest_hash']=digest(envelope['manifest'])
    result.update(envelope=envelope,manifest=envelope['manifest'],manifest_hash=envelope['release']['manifest_hash'])
    return result


def preview_payload(payload: dict[str,Any]) -> dict[str,Any]:
    result=deepcopy(payload)
    candidate=dict(candidate_id=payload['candidate_id'],manifest=manifest(location='stairwell'),
        manifest_hash=payload['manifest_hash'],letter='A',label='Stairwell')
    result.update(candidate=candidate,metadata=metadata())
    return result
