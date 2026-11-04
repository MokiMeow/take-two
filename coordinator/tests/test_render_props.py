from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from coordinator.render_props import preview_props, callsheet_props
from coordinator.render_schema import PreviewProps, CallSheetProps
from coordinator.render_bridge import RenderBridge, RenderError


def test_preview_uses_trusted_names_and_candidate_identity() -> None:
    candidate = dict(label='Park bench',manifest_hash='sha256:'+'a'*64,
        manifest=dict(scene_id='s3',location='park',start='2026-11-06T16:45:00+05:30',
            end='2026-11-06T18:15:00+05:30',shots=['wide'],people=['maya']))
    props = preview_props(candidate,'B',dict(number=3,title='The confession'),[dict(id='maya',name='Maya',role='actor')])
    PreviewProps.model_validate(props)
    assert props['letter']=='B' and props['label']=='Park bench'
    assert props['people']==[dict(id='maya',name='Maya')]
    assert props['manifest_hash']=='sha256:'+'a'*64
    with pytest.raises((ValueError,KeyError)):
        preview_props(candidate,'B',dict(number=3,title='The confession'),[])


async def test_render_hashes_manifest_writes_props_and_retains_last_error(tmp_path: Path) -> None:
    cli = tmp_path/'fail.mjs'
    cli.write_text('process.stderr.write("noise\\nrender-error: first\\nrender-error: invalid shots\\n");process.exit(1);')
    bridge = RenderBridge(tmp_path,cli=cli)
    with pytest.raises(RenderError,match='invalid shots'):
        await bridge.render('preview',{'scene_id':'s3'}, {'label':'presentation'})
    assert json.loads(next(tmp_path.glob('preview-*.json')).read_text())=={'label':'presentation'}
    result = await RenderBridge(tmp_path,cli=tmp_path/'missing.mjs').render('preview',{'scene_id':'s3'}, {'label':'different'})
    expected = 'sha256:'+hashlib.sha256(b'{"scene_id":"s3"}').hexdigest()
    assert result.manifest_hash==expected


def test_callsheet_complete_and_held_rows_are_strict() -> None:
    envelope = dict(manifest=dict(scenes=[dict(scene_id='s1',location='stairwell',start='2026-11-06T15:00:00+05:30',
        end='2026-11-06T15:15:00+05:30',setup_min=15,wrap_min=0,people=['dev'],shots=['wide'],capabilities=[]),
        dict(scene_id='s3',validity='held',hold_reason='Permission refused')]),
        previous_manifest=None,metadata=dict(production=dict(title='The Last Light',day='Day 1',date='Friday 6 November 2026',timezone='Asia/Kolkata'),
        scenes=[dict(id='s1',number=1,title='The missed call'),dict(id='s3',number=3,title='The confession')],
        crew=[dict(id='maya',name='Maya',role='actor'),dict(id='dev',name='Dev',role='actor')]),
        release=dict(number=2,release_id='r2',manifest_hash='sha256:'+'a'*64,summary='Scene 3 held.',changes=[],created_at='2026-11-06T14:00:00+05:30'))
    props = callsheet_props(envelope)
    CallSheetProps.model_validate(props)
    assert props['scenes'][0]['cast']==['2']
    assert props['scenes'][1]==dict(status='held',number=3,title='The confession',hold_reason='Permission refused',changed=True)
    assert props['crew'][0]['call_time'] is None
    bad = deepcopy(props)
    bad['scenes'][1]['location']='rooftop'
    with pytest.raises(ValidationError):
        CallSheetProps.model_validate(bad)


async def test_generated_props_are_accepted_by_real_zod_schemas(tmp_path: Path) -> None:
    import asyncio
    import shutil
    from coordinator.tests.test_w4_workflow import runtime, initial
    from coordinator.tests.w4_support import preview_payload
    rt=runtime(tmp_path)
    await initial(rt.loop)
    call=callsheet_props(rt.loop.workflow['releases']['r1']['envelope'])
    payload=preview_payload(dict(candidate_id='park',manifest_hash='sha256:'+'a'*64))
    preview=preview_props(payload['candidate'],'B',dict(number=3,title='The confession'),payload['metadata']['crew'])
    root=Path(__file__).resolve().parents[2]
    code="import {previewSchema,callSheetSchema} from './render/src/schema.ts';let data='';for await (const c of process.stdin)data+=c;const p=JSON.parse(data);previewSchema.parse(p.preview);callSheetSchema.parse(p.call);console.log('validated');"
    process=await asyncio.create_subprocess_exec(shutil.which('node'),'--input-type=module','-e',code,cwd=root,
        stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    output,error=await asyncio.wait_for(process.communicate(json.dumps(dict(preview=preview,call=call)).encode()),30)
    assert process.returncode==0,error.decode()
    assert b'validated' in output
    await rt.close()
